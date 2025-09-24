import { app, BrowserWindow, ipcMain } from 'electron';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';
import log from 'electron-log';
import { startPipeServer } from './pipeServer';
import { SystemController } from './systemController';
import throttle from 'lodash/throttle';

const __dirname = dirname(fileURLToPath(import.meta.url));
log.transports.file.level = 'info';

let mainWindow: BrowserWindow | null = null;
let monitorProcess: any = null;
const systemController = new SystemController();

app.disableHardwareAcceleration();   // 禁用 GPU 加速
app.commandLine.appendSwitch('disable-gpu-sandbox');
function getMonitorPath() {
  const arch = process.arch === 'x64' ? 'x64' : 'x86';
  return join(__dirname, `../../native/${arch}/Release/monitor.exe`);
}

function startMonitorProcess() {
  const monitorPath = getMonitorPath();
  log.info(`Starting monitor from: ${monitorPath}`);
  monitorProcess = require('child_process').spawn(monitorPath, [], { stdio: 'ignore' });
  monitorProcess.on('error', (err: any) => log.error('Monitor spawn error:', err));
  monitorProcess.on('exit', (code: number | null) => {
    log.info(`Monitor exited: ${code}`);
    if (code !== 0 && !app.isQuitting) {
      setTimeout(startMonitorProcess, 1000);
    }
  });
}

function stopMonitorProcess() {
  if (monitorProcess) {
    monitorProcess.kill();
    monitorProcess = null;
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200, height: 800,
    webPreferences: { preload: join(__dirname, '../preload/index.js'), contextIsolation: true }
  });
  mainWindow.loadURL(process.env.NODE_ENV === 'development' ? 'http://localhost:5173' : join(__dirname, '../renderer/index.html'));
  mainWindow.on('closed', () => (mainWindow = null));
  ipcMain.on('toggle-monitor', (_, enable) => (enable ? startMonitorProcess() : stopMonitorProcess()));
  mainWindow.webContents.once('dom-ready', startMonitorProcess);
}

app.whenReady().then(() => {
  createWindow();
  startPipeServer(systemController);
  app.on('activate', () => !BrowserWindow.getAllWindows().length && createWindow());
});

app.on('window-all-closed', () => (process.platform !== 'darwin' && app.quit()));
app.on('before-quit', () => {
  stopMonitorProcess();
  systemController.closeDatabase();
});

/* 1 秒最多一次转发前端 */
systemController.on('data', throttle((rows) => {
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send('realtime', rows);
}, 1000));