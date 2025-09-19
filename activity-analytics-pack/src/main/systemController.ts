import Database from 'better-sqlite3';
import { EventEmitter } from 'events';
import { join } from 'path';
import log from 'electron-log';

// 定义数据接口
export interface SystemData {
  timestamp: number;
  pid: number;
  title: string;
  exe: string;
  cpu: number;
  mem: number;
  kb: number;
  mouse: number;
  dB: number;
}

export class SystemController extends EventEmitter {
  private db: Database.Database | null = null;
  
  constructor() {
    super();
    this.initDatabase();
  }
  
  // 初始化数据库
  private initDatabase() {
    try {
      const dbPath = join(app.getPath('userData'), 'activity.db');
      this.db = new Database(dbPath);
      
      // 创建数据表
      this.db.prepare(`
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
      `).run();
      
      // 创建索引提高查询性能
      this.db.prepare(`
        CREATE INDEX IF NOT EXISTS idx_timestamp ON system_data(timestamp)
      `).run();
      
      log.info(`Database initialized at ${dbPath}`);
    } catch (error) {
      log.error('Failed to initialize database:', error);
      this.db = null;
    }
  }
  
  // 处理实时数据
  handleRealtimeData(data: Partial<SystemData>) {
    // 补充时间戳
    const systemData: SystemData = {
      timestamp: Date.now(),
      pid: data.pid || 0,
      title: data.title || '',
      exe: data.exe || '',
      cpu: data.cpu || 0,
      mem: data.mem || 0,
      kb: data.kb || 0,
      mouse: data.mouse || 0,
      dB: data.dB || 0
    };
    
    // 保存到数据库
    this.saveToDatabase(systemData);
    
    // 发射事件，传递给主进程
    this.emit('data', systemData);
  }
  
  // 保存数据到数据库
  private saveToDatabase(data: SystemData) {
    if (!this.db) return;
    
    try {
      const stmt = this.db.prepare(`
        INSERT INTO system_data (
          timestamp, pid, title, exe, cpu, mem, kb, mouse, dB
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `);
      
      stmt.run(
        data.timestamp,
        data.pid,
        data.title,
        data.exe,
        data.cpu,
        data.mem,
        data.kb,
        data.mouse,
        data.dB
      );
    } catch (error) {
      log.error('Failed to save data to database:', error);
    }
  }
  
  // 获取历史数据
  getHistoricalData(startTime: number, endTime: number): SystemData[] {
    if (!this.db) return [];
    
    try {
      const stmt = this.db.prepare(`
        SELECT * FROM system_data 
        WHERE timestamp BETWEEN ? AND ?
        ORDER BY timestamp ASC
      `);
      
      return stmt.all(startTime, endTime) as SystemData[];
    } catch (error) {
      log.error('Failed to get historical data:', error);
      return [];
    }
  }
  
  // 关闭数据库连接
  closeDatabase() {
    if (this.db) {
      this.db.close();
      this.db = null;
      log.info('Database connection closed');
    }
  }
}
