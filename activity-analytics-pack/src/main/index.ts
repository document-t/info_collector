import { app, BrowserWindow, ipcMain } from 'electron';
import { join } from 'path';
import { startPipeServer } from './pipeServer';
import { SystemController } from './systemController';
import * as childProcess from 'child_process';
import * as path from 'path';
import log from 'electron-log';

// 配置日志
log.transports.file.level = 'info';

let mainWindow: BrowserWindow | null = null;
let monitorProcess: childProcess.ChildProcess | null = null;
const systemController = new SystemController();

// 启动监控DLL进程
function startMonitorProcess() {
  const dllPath = process.env.NODE_ENV === 'development'
    ? path.join(__dirname, '../../native/x64/Release/monitor.exe')
    : path.join(process.resourcesPath, 'native/x64/Release/monitor.exe');
  
  log.info(`Starting monitor process from: ${dllPath}`);
  
  monitorProcess = childProcess.spawn(dllPath);
  
  monitorProcess.on('error', (err) => {
    log.error('Failed to start monitor process:', err);
  });
  
  monitorProcess.on('exit', (code) => {
    log.info(`Monitor process exited with code: ${code}`);
    // 如果不是主动关闭，尝试重启
    if (code !== 0 && !app.isQuitting) {
      setTimeout(startMonitorProcess, 1000);
    }
  });
}

// 停止监控进程
function stopMonitorProcess() {
  if (monitorProcess) {
    log.info('Stopping monitor process');
    monitorProcess.kill();
    monitorProcess = null;
  }
}

// 创建主窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      nodeIntegration: false,
      contextIsolation: true
    },
    title: 'Activity Analytics'
  });

  // 加载渲染进程
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'));
  }

  // 窗口关闭事件
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // 注册IPC事件
  ipcMain.on('toggle-monitor', (_, enable: boolean) => {
    if (enable && !monitorProcess) {
      startMonitorProcess();
    } else if (!enable && monitorProcess) {
      stopMonitorProcess();
    }
  });
}

// 应用就绪后创建窗口
app.whenReady().then(() => {
  createWindow();
  
  // 启动管道服务器
  startPipeServer(systemController);
  
  // 当系统准备就绪且窗口未创建时创建窗口
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
  
  // 启动监控进程
  startMonitorProcess();
});

// 所有窗口关闭时退出应用
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    stopMonitorProcess();
    app.quit();
  }
});

// 应用退出前清理
app.on('before-quit', () => {
  app.isQuitting = true;
  stopMonitorProcess();
  systemController.closeDatabase();
});

// 转发数据到渲染进程
systemController.on('data', (data) => {
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('realtime', data);
  }
});
