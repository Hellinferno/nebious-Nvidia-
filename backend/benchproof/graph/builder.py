"""Engineering-state graph builder from Python AST and declared contracts (B-07)."""

from __future__ import annotations

import ast
from pathlib import Path

from benchproof.constraints import list_constraints
from benchproof.domain import EdgeProvenance, GraphEdge, GraphSnapshot
from benchproof.fixtures import source_hash_for_dir

# Declared fixture contract-to-symbol mappings for development-v2
# Maps contract_id -> list of symbol names (e.g. "app.money:compute_total")
DECLARED_CONTRACT_SYMBOLS: dict[str, list[str]] = {
    "C-API": [
        "app.schemas:ReceiptResponse",
        "app.schemas:InvoiceRequest",
        "app.routes:submit_invoice",
    ],
    "C-AMOUNT": [
        "app.money:compute_total",
        "app.services:process_invoice",
        "app.worker:handle_invoice_job",
    ],
    "C-INTEGRITY": [
        "app.worker:handle_invoice_job",
        "app.services:process_invoice",
    ],
    "C-IDEMPOTENCY": [
        "app.services:process_invoice",
        "app.repository:save_receipt",
        "app.repository:get_receipt",
    ],
}

DYNAMIC_CALLS = {"eval", "exec", "getattr", "setattr", "delattr", "__import__"}
DYNAMIC_MODULES = {"importlib", "inspect", "sys"}


class ASTVisitor(ast.NodeVisitor):
    def __init__(self, mod_name: str, file_rel: str) -> None:
        self.mod_name = mod_name
        self.file_rel = file_rel
        self.symbols: dict[str, str] = {}  # symbol_id -> source_span
        self.imports: dict[str, str] = {}  # local_name -> qualified_target
        self.calls: list[tuple[str, str, str]] = []  # (caller_sym, callee_name, span)
        self.dynamic_features: list[str] = []
        self._current_symbol: str | None = None

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local = alias.asname or alias.name
            target = alias.name
            if target in DYNAMIC_MODULES:
                self.dynamic_features.append(f"Dynamic module import: {target} at L{node.lineno}")
            self.imports[local] = target
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = node.module or ""
        # Handle relative imports inside app
        if node.level > 0:
            # relative within app
            prefix = "app"
            mod_part = f"{prefix}.{mod}" if mod else prefix
        else:
            mod_part = mod

        if any(d in mod_part for d in DYNAMIC_MODULES):
            self.dynamic_features.append(f"Dynamic import from: {mod_part} at L{node.lineno}")

        for alias in node.names:
            local = alias.asname or alias.name
            target = f"{mod_part}.{alias.name}" if mod_part else alias.name
            self.imports[local] = target
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        sym_name = f"{self.mod_name}:{node.name}"
        span = f"L{node.lineno}-L{node.end_lineno or node.lineno}"
        self.symbols[sym_name] = span

        prev = self._current_symbol
        self._current_symbol = sym_name
        self.generic_visit(node)
        self._current_symbol = prev

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        sym_name = f"{self.mod_name}:{node.name}"
        span = f"L{node.lineno}-L{node.end_lineno or node.lineno}"
        self.symbols[sym_name] = span

        prev = self._current_symbol
        self._current_symbol = sym_name
        self.generic_visit(node)
        self._current_symbol = prev

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        sym_name = f"{self.mod_name}:{node.name}"
        span = f"L{node.lineno}-L{node.end_lineno or node.lineno}"
        self.symbols[sym_name] = span

        prev = self._current_symbol
        self._current_symbol = sym_name
        for stmt in node.body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                m_sym = f"{self.mod_name}:{node.name}.{stmt.name}"
                m_span = f"L{stmt.lineno}-L{stmt.end_lineno or stmt.lineno}"
                self.symbols[m_sym] = m_span
        self.generic_visit(node)
        self._current_symbol = prev

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._current_symbol is None:
            # Top-level assignment, e.g. router = APIRouter(), _store = {}
            for target in node.targets:
                if isinstance(target, ast.Name):
                    sym_name = f"{self.mod_name}:{target.id}"
                    span = f"L{node.lineno}-L{node.end_lineno or node.lineno}"
                    self.symbols[sym_name] = span
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        callee_name = ""
        span = f"L{node.lineno}"
        if isinstance(node.func, ast.Name):
            callee_name = node.func.id
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            callee_name = f"{node.func.value.id}.{node.func.attr}"

        if callee_name in DYNAMIC_CALLS:
            self.dynamic_features.append(f"Dynamic call: {callee_name} at L{node.lineno}")

        if self._current_symbol and callee_name:
            self.calls.append((self._current_symbol, callee_name, span))
        self.generic_visit(node)


class GraphBuilder:
    """Constructs a deterministic engineering-state graph for an app directory."""

    def __init__(self, app_dir: Path, contract_hash_val: str) -> None:
        self.app_dir = app_dir
        self.contract_hash = contract_hash_val
        self.source_hash = source_hash_for_dir(app_dir)

    def build(self) -> GraphSnapshot:
        nodes: set[str] = set()
        edges: list[GraphEdge] = []
        unresolved_items: list[str] = []
        dynamic_features: list[str] = []

        all_symbols: dict[str, str] = {}  # sym_id -> span
        file_to_symbols: dict[str, list[str]] = {}
        all_imports: dict[str, dict[str, str]] = {}  # mod_name -> {local: target}
        raw_calls: list[tuple[str, str, str, str]] = []  # (mod_name, caller_sym, callee_name, span)

        py_files = sorted(p for p in self.app_dir.rglob("*.py") if "__pycache__" not in p.parts)

        # 1. Parse AST for each python file
        for fpath in py_files:
            rel = fpath.relative_to(self.app_dir.parent).as_posix()
            file_node = f"file:{rel}"
            nodes.add(file_node)

            # Module name e.g. "app.routes"
            parts = fpath.relative_to(self.app_dir.parent).with_suffix("").parts
            mod_name = ".".join(parts)

            try:
                tree = ast.parse(fpath.read_text(encoding="utf-8"), filename=str(fpath))
            except SyntaxError as e:
                unresolved_items.append(f"Syntax error parsing {rel}: {e}")
                continue

            visitor = ASTVisitor(mod_name, rel)
            visitor.visit(tree)

            all_imports[mod_name] = visitor.imports
            dynamic_features.extend(visitor.dynamic_features)

            file_symbols: list[str] = []
            for sym, span in visitor.symbols.items():
                sym_node = f"symbol:{sym}"
                nodes.add(sym_node)
                all_symbols[sym] = span
                file_symbols.append(sym_node)

                # Edge: defines (File -> Symbol)
                edges.append(
                    GraphEdge(
                        from_node=file_node,
                        to_node=sym_node,
                        edge_type="defines",
                        provenance=EdgeProvenance.OBSERVED,
                        source_span=span,
                    )
                )

            file_to_symbols[file_node] = file_symbols

            # Record calls for resolution
            for caller_sym, callee, span in visitor.calls:
                raw_calls.append((mod_name, caller_sym, callee, span))

        # 2. Record import edges (File/Symbol -> Symbol/File)
        for mod_name, imports in all_imports.items():
            for target in imports.values():
                sym_cand = None
                if "." in target:
                    m, s = target.rsplit(".", 1)
                    if f"{m}:{s}" in all_symbols:
                        sym_cand = f"{m}:{s}"
                if not sym_cand and target in all_symbols:
                    sym_cand = target

                if sym_cand:
                    edges.append(
                        GraphEdge(
                            from_node=f"file:{mod_name.replace('.', '/')}.py",
                            to_node=f"symbol:{sym_cand}",
                            edge_type="imports",
                            provenance=EdgeProvenance.OBSERVED,
                        )
                    )

        # 3. Resolve direct calls (Symbol -> Symbol)
        for mod_name, caller_sym, callee_name, span in raw_calls:
            caller_node = f"symbol:{caller_sym}"
            resolved_target: str | None = None

            # Is callee in imports?
            if callee_name in all_imports.get(mod_name, {}):
                target = all_imports[mod_name][callee_name]
                if "." in target:
                    m, s = target.rsplit(".", 1)
                    if f"{m}:{s}" in all_symbols:
                        resolved_target = f"symbol:{m}:{s}"
                if not resolved_target and target in all_symbols:
                    resolved_target = f"symbol:{target}"
            elif "." in callee_name:
                base, attr = callee_name.split(".", 1)
                if base in all_imports.get(mod_name, {}):
                    mod_target = all_imports[mod_name][base]
                    cand = f"{mod_target}:{attr}"
                    if cand in all_symbols:
                        resolved_target = f"symbol:{cand}"
            else:
                # Same module call
                same_mod_sym = f"{mod_name}:{callee_name}"
                if same_mod_sym in all_symbols:
                    resolved_target = f"symbol:{same_mod_sym}"

            if resolved_target:
                edges.append(
                    GraphEdge(
                        from_node=caller_node,
                        to_node=resolved_target,
                        edge_type="calls",
                        provenance=EdgeProvenance.INFERRED,
                        source_span=span,
                    )
                )

        # 4. Declared Contracts and Tests
        constraints = list_constraints()
        for c in constraints:
            c_node = f"contract:{c.constraint_id}"
            nodes.add(c_node)

            # Contract -> Tests (protected_by)
            for check_id in c.protected_check_ids:
                t_node = f"test:{check_id}"
                nodes.add(t_node)
                edges.append(
                    GraphEdge(
                        from_node=c_node,
                        to_node=t_node,
                        edge_type="protected_by",
                        provenance=EdgeProvenance.DECLARED,
                        manifest_ref=c.constraint_id,
                    )
                )

            # Symbols -> Contract (implements)
            declared_syms = DECLARED_CONTRACT_SYMBOLS.get(c.constraint_id, [])
            for sym_name in declared_syms:
                sym_node = f"symbol:{sym_name}"
                if sym_name in all_symbols:
                    edges.append(
                        GraphEdge(
                            from_node=sym_node,
                            to_node=c_node,
                            edge_type="implements",
                            provenance=EdgeProvenance.DECLARED,
                            manifest_ref=c.constraint_id,
                        )
                    )
                else:
                    unresolved_items.append(
                        f"Missing declared symbol for contract {c.constraint_id}: {sym_name}"
                    )

        # 5. Determine Coverage
        unresolved_items.extend(dynamic_features)
        if unresolved_items:
            coverage_status = "PARTIAL"
        else:
            coverage_status = "COMPLETE_FOR_DECLARED_SCOPE"

        coverage = {
            "status": coverage_status,
            "total_files": len(py_files),
            "total_symbols": len(all_symbols),
            "total_edges": len(edges),
            "dynamic_features_detected": len(dynamic_features),
            "missing_mappings": len([u for u in unresolved_items if "Missing declared" in u]),
        }

        # Deduplicate and sort edges deterministically
        seen_edges: set[tuple[str, str, str, str | None]] = set()
        deduped_edges: list[GraphEdge] = []
        for e in edges:
            key = (e.from_node, e.to_node, e.edge_type, e.source_span)
            if key not in seen_edges:
                seen_edges.add(key)
                deduped_edges.append(e)

        deduped_edges.sort(key=lambda x: (x.from_node, x.to_node, x.edge_type, x.source_span or ""))
        sorted_nodes = sorted(nodes)

        graph_id = f"graph-{self.source_hash[:12]}"
        snapshot = GraphSnapshot(
            graph_id=graph_id,
            source_hash=self.source_hash,
            contract_hash=self.contract_hash,
            builder_version="0.2.0",
            nodes=sorted_nodes,
            edges=deduped_edges,
            coverage=coverage,
            unresolved_items=unresolved_items,
        )
        snapshot.compute_hash()
        return snapshot


def build_state_graph(app_dir: Path, contract_hash_val: str) -> GraphSnapshot:
    """Build canonical graph snapshot for given app dir and contract hash."""
    return GraphBuilder(app_dir, contract_hash_val).build()
