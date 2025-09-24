import { parentPort } from 'worker_threads';
import Database from 'better-sqlite3';

let db: Database.Database;

/* ---------- 1. 初始化 ---------- */
parentPort!.once('message', (msg) => {
  if (msg.type === 'init') {
    db = new Database(msg.dbPath);

    // 建表 + 索引
    db.prepare(`
      CREATE TABLE IF NOT EXISTS system_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp INTEGER NOT NULL,
        pid INTEGER NOT NULL,
        title TEXT,
        exe TEXT,
        cpu REAL,
        mem REAL,
        kb INTEGER,
        mouse INTEGER,
        dB REAL
      )
    `)。run();
    db.prepare(`CREATE INDEX IF NOT EXISTS idx_timestamp ON system_data(timestamp)`).run();

    parentPort!.postMessage('ready');
  }
});

/* ---------- 2. 批量插入 ---------- */
parentPort!.on('message', (rows: any[]) => {
  if (!db || !Array.isArray(rows)) return;

  const stmt = db.prepare(`INSERT INTO system_data (timestamp, pid, title, exe, cpu, mem, kb, mouse, dB) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`);
  const tx = db.transaction((list: any[]) => {
    for (const r of list) stmt.run(r.timestamp, r.pid, r.title, r.exe, r.cpu, r.mem, r.kb, r.mouse, r.dB);
  });
  tx(rows);
});

/* ---------- 3. 查询历史 ---------- */
parentPort!.on('message', (msg, transfer) => {
  if (msg.type === 'query' && transfer && transfer[0]) {
    const port = transfer[0];
    const rows = db
      .prepare(`SELECT * FROM system_data WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp`)
      .all(msg.start, msg.end);
    port.postMessage(rows);
  }
});
