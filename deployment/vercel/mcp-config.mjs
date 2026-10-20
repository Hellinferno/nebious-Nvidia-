export function mcpConfig(env = process.env) {
  const raw = env.BENCHPROOF_MCP_CONNECTIONS ?? '[]';
  if (raw.length > 16384) throw new Error('MCP connection configuration exceeds its bound');
  let connections;
  try { connections = JSON.parse(raw); } catch { throw new Error('Invalid MCP connection configuration'); }
  if (!Array.isArray(connections) || connections.length > 5) throw new Error('Invalid MCP connection configuration');
  const credentials = {};
  const identifiers = new Set();
  for (const connection of connections) {
    if (!connection || typeof connection !== 'object' || Array.isArray(connection) || Object.keys(connection).some(key => !['id', 'name', 'url', 'tools', 'token_env'].includes(key))) throw new Error('Invalid MCP connection fields');
    if (typeof connection.id !== 'string' || !/^[a-z0-9_-]{1,40}$/.test(connection.id) || identifiers.has(connection.id)) throw new Error('Invalid MCP connection identity');
    identifiers.add(connection.id);
    if (typeof connection.name !== 'string' || connection.name.length < 1 || connection.name.length > 80 || typeof connection.url !== 'string' || connection.url.length > 500) throw new Error('Invalid MCP connection metadata');
    let target;
    try { target = new URL(connection.url); } catch { throw new Error('Invalid MCP connection endpoint'); }
    if (target.protocol !== 'https:' || !target.hostname || target.port || target.username || target.password || target.search || target.hash) throw new Error('MCP requires a credential-free HTTPS/443 endpoint');
    if (!Array.isArray(connection.tools) || connection.tools.length < 1 || connection.tools.length > 10 || new Set(connection.tools).size !== connection.tools.length || connection.tools.some(name => typeof name !== 'string' || name.length < 1 || name.length > 100)) throw new Error('Invalid MCP tool allowlist');
    if (connection.token_env != null) {
      if (typeof connection.token_env !== 'string' || !/^BENCHPROOF_MCP_TOKEN_[A-Z0-9_]+$/.test(connection.token_env)) throw new Error('Invalid dedicated MCP credential reference');
      const token = env[connection.token_env];
      if (typeof token !== 'string' || token.length < 1 || token.length > 8192 || /[\r\n]/.test(token)) throw new Error('Dedicated MCP credential is unavailable');
      credentials[connection.token_env] = token;
    }
  }
  const allowance = Number(env.BENCHPROOF_MCP_QUERIES_PER_DAY ?? 0);
  if (!Number.isInteger(allowance) || allowance < 0 || allowance > 20 || (connections.length && allowance === 0)) throw new Error('Configure an MCP daily allowance from 1 to 20 for approved connections');
  return { connections, queries_per_day: allowance, credentials };
}
