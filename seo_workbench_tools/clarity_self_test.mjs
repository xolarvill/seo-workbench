import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
const runner = fileURLToPath(new URL('./clarity_mcp_runner.mjs', import.meta.url));
function call(input) {
  const result = spawnSync(process.execPath, [runner], { input: JSON.stringify(input), encoding: 'utf8', timeout: 15000 });
  assert.equal(result.status, 0);
  return JSON.parse(result.stdout);
}
const discovery = call({ tool: 'discover' });
assert.equal(discovery.result.tools.length, 3);
assert.equal(discovery.result.server_version, '2.0.1');
const missing = call({ tool: 'query-analytics-dashboard', arguments: { query: 'sessions' } });
assert.match(missing.result.content[0].text, /No Clarity API token/);
console.log('Clarity MCP: actual stdio handshake, schema discovery, call, missing-auth response and shutdown passed.');
