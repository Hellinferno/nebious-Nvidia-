"""CLI utility for online database backup, verification, and restore (C-08)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchproof.storage.backup import BackupError, create_backup, restore_backup


def main() -> int:
    parser = argparse.ArgumentParser(description="BenchProof SQLite Backup and Restore Utility")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Backup subcommand
    backup_parser = subparsers.add_parser("backup", help="Create an atomic SQLite backup")
    backup_parser.add_argument("--db", type=Path, required=True, help="Path to source database")
    backup_parser.add_argument("--out", type=Path, required=True, help="Path for backup output")
    backup_parser.add_argument("--no-manifest", action="store_true", help="Do not write manifest JSON")

    # Restore subcommand
    restore_parser = subparsers.add_parser("restore", help="Restore database from a backup")
    restore_parser.add_argument("--backup", type=Path, required=True, help="Path to backup file")
    restore_parser.add_argument("--db", type=Path, required=True, help="Path to target database destination")
    restore_parser.add_argument("--expected-sha256", type=str, default=None, help="Expected SHA-256 checksum")

    args = parser.parse_args()

    try:
        if args.command == "backup":
            manifest = create_backup(args.db, args.out, include_manifest=not args.no_manifest)
            print(json.dumps(manifest, indent=2))
            return 0
        elif args.command == "restore":
            result = restore_backup(args.backup, args.db, expected_sha256=args.expected_sha256)
            print(json.dumps(result, indent=2))
            return 0
    except BackupError as exc:
        print(f"Error [{exc.code}]: {exc.message}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
