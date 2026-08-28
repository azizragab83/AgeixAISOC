/* Insert the SOAR workflow into n8n SQLite in FK-safe order. */
const { DatabaseSync } = require('node:sqlite');
const crypto = require('crypto');

const wf = JSON.parse(require('fs').readFileSync('/tmp/ageix_soar.json', 'utf8'));
const db = new DatabaseSync('/home/node/.n8n/database.sqlite');

const id = crypto.randomBytes(8).toString('hex').toUpperCase().slice(0, 16);
const versionId = crypto.randomUUID();
const now = new Date().toISOString();
const settings = JSON.stringify({ executionOrder: 'v1', binaryMode: 'separate', availableInMCP: false });

db.prepare('DELETE FROM shared_workflow WHERE workflowId IN (SELECT id FROM workflow_entity WHERE name = ?)').run(wf.name);
db.prepare('DELETE FROM workflow_history WHERE workflowId IN (SELECT id FROM workflow_entity WHERE name = ?)').run(wf.name);
db.prepare('DELETE FROM workflow_entity WHERE name = ?').run(wf.name);

// 1) entity with activeVersionId NULL (FK satisfied later)
db.prepare(`INSERT INTO workflow_entity
  (id, name, active, nodes, connections, settings, staticData, pinData, versionId,
   triggerCount, meta, parentFolderId, createdAt, updatedAt, isArchived, versionCounter,
   description, activeVersionId)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, 0, 1, NULL, NULL)`)
  .run(id, wf.name, 1, JSON.stringify(wf.nodes), JSON.stringify(wf.connections || {}),
       settings, '{}', '{}', versionId, 1, '{}', now, now);
console.log('INSERTED workflow_entity id=' + id);

// 2) history row
db.prepare(`INSERT INTO workflow_history (versionId, workflowId, nodes, connections, name, data, createdAt, updatedAt)
            VALUES (?, ?, ?, ?, ?, NULL, ?, ?)`)
  .run(versionId, id, JSON.stringify(wf.nodes), JSON.stringify(wf.connections || {}), wf.name, now, now);
console.log('INSERTED workflow_history');

// 3) link active version
db.prepare('UPDATE workflow_entity SET activeVersionId = ? WHERE id = ?').run(versionId, id);
console.log('LINKED activeVersionId');

// 4) ownership via existing project
const proj = db.prepare('SELECT projectId FROM shared_workflow LIMIT 1').get();
if (proj) {
  db.prepare('INSERT INTO shared_workflow (workflowId, projectId, role, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?)')
    .run(id, proj.projectId, 'workflow:owner', now, now);
  console.log('INSERTED shared_workflow owner project=' + proj.projectId);
}

db.close();
console.log('DONE');