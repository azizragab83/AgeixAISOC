/* Fix webhook path definitively: must be bare 'execute-soar'. */
const { DatabaseSync } = require('node:sqlite');
const db = new DatabaseSync('/home/node/.n8n/database.sqlite');
for (const t of ['workflow_entity', 'workflow_history']) {
  const rows = db.prepare('SELECT versionId, nodes FROM ' + t + " WHERE nodes LIKE '%execute-soar%'").all();
  for (const r of rows) {
    const nodes = JSON.parse(r.nodes);
    let changed = false;
    for (const nd of nodes) {
      if (nd.type === 'n8n-nodes-base.webhook') {
        let p = String(nd.parameters.path);
        p = p.replace(/^\/+/, '').replace(/^webhook\//, '');
        if (p !== nd.parameters.path) { nd.parameters.path = p; changed = true; }
      }
    }
    if (changed) {
      db.prepare('UPDATE ' + t + ' SET nodes=? WHERE versionId=?').run(JSON.stringify(nodes), r.versionId);
      console.log('FIXED path in ' + t);
    }
  }
}
db.prepare('DELETE FROM webhook_entity').run();
console.log('CLEARED webhook_entity for re-registration');
db.close();
console.log('DONE');