import { EventEmitter } from 'events';
import { join } from 'path';
import { app } from 'electron';
import { Worker } from 'worker_threads';
import log from 'electron-log';

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
  private dbPath = join(app.getPath('userData'), 'activity.db');
  private worker = new Worker(join(__dirname, 'worker/dataWorker.js'));
  private saveQueue: SystemData[] = [];
  public getSaveQueue() { return this.saveQueue.splice(0);
   }
  constructor() {
    super();
    this.worker.once('message', () => log.info('Worker ready'));
    this.worker.on('message', (rows) => this.emit('data', rows));
    this.worker.postMessage({ type: 'init', dbPath: this.dbPath });
    setInterval(() => this.flushQueue(), 300);
  }

  handleRealtimeData(data: Partial<SystemData>) {
    const systemData: SystemData = {
      timestamp: Date.now(),
      pid: Number(data.pid) || 0,
      title: data.title || '',
      exe: data.exe || '',
      cpu: Number(data.cpu) || 0,
      mem: Number(data.mem) || 0,
      kb: Number(data.kb) || 0,
      mouse: Number(data.mouse) || 0,
      dB: Number(data.dB) || 0,
    };
    this.saveQueue.push(systemData);
    this.emit('data', [systemData]);
  }

  private flushQueue() {
    if (!this.saveQueue.length) return;
    this.worker.postMessage(this.saveQueue.splice(0));
  }

  closeDatabase() {
    this.worker.terminate();
    log.info('Worker terminated');
  }
}
