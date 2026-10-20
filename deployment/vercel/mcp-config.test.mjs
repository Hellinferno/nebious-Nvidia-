import assert from 'node:assert/strict';
import { test } from 'node:test';
import { mcpConfig } from './mcp-config.mjs';

const connection = { id: 'docs', name: 'Docs', url: 'https://example.org/mcp', tools: ['read_guide'] };
const environment = (overrides = {}) => ({ BENCHPROOF_MCP_CONNECTIONS: JSON.stringify([connection]), BENCHPROOF_MCP_QUERIES_PER_DAY: '5', ...overrides });

test('MCP deployment defaults to disabled and only packages dedicated credentials', () => {
  assert.deepEqual(mcpConfig({}), { connections: [], queries_per_day: 0, credentials: {} });
  const configured = { ...connection, token_env: 'BENCHPROOF_MCP_TOKEN_DOCS' };
  const result = mcpConfig(environment({ BENCHPROOF_MCP_CONNECTIONS: JSON.stringify([configured]), BENCHPROOF_MCP_TOKEN_DOCS: 'synthetic-docs-token', NEBIUS_API_KEY: 'must-not-be-copied' }));
  assert.deepEqual(result.credentials, { BENCHPROOF_MCP_TOKEN_DOCS: 'synthetic-docs-token' });
  assert.equal(JSON.stringify(result).includes('must-not-be-copied'), false);
});

test('MCP deployment refuses unsafe endpoints, quota and arbitrary environment references', () => {
  for (const url of ['http://example.org/mcp', 'https://user:pass@example.org/mcp', 'https://example.org/mcp?token=private', 'https://example.org:444/mcp']) {
    assert.throws(() => mcpConfig(environment({ BENCHPROOF_MCP_CONNECTIONS: JSON.stringify([{ ...connection, url }]) })));
  }
  for (const quota of ['0', '21', '-1', '1.5']) assert.throws(() => mcpConfig(environment({ BENCHPROOF_MCP_QUERIES_PER_DAY: quota })));
  for (const token_env of ['NEBIUS_API_KEY', 'PATH', 'BENCHPROOF_MCP_TOKEN_DOCS']) assert.throws(() => mcpConfig(environment({ BENCHPROOF_MCP_CONNECTIONS: JSON.stringify([{ ...connection, token_env }]) })));
  assert.throws(() => mcpConfig(environment({ BENCHPROOF_MCP_CONNECTIONS: JSON.stringify([connection, connection]) })));
});
