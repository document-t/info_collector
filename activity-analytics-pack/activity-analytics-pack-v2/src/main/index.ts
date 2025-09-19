import { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage, shell } from 'electron';
import { join } from 'path';
import { startPipeServer } from './pipeServer';
import { SystemController } from './systemController';
import { CloudUploader } from './cloud/uploader';
import { features } from '../config';
import { getAppDataPath, resolvePath } from './utils/paths';
import fs from 'fs/promises';
import fsSync from 'fs';
import { exec } from 'child_process';

// 全局变量
let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let cloudUploader: CloudUploader | null = null;
let syncInterval: NodeJS.Timeout | null = null;
let dllProcess: any = null;

// 确保应用单实例运行
const lock = app.requestSingleInstanceLock();
if (!lock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

// 创建主窗口
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    show: false,
    frame: true,
    title: 'Activity Analytics',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
  });

  // 加载前端页面
  if (app.isPackaged) {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'));
  } else {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  }

  // 窗口准备好后显示
  mainWindow.on('ready-to-show', () => {
    mainWindow?.show();
  });

  // 窗口关闭事件
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // 阻止默认菜单
  mainWindow.removeMenu();
}

// 创建系统托盘
function createTray() {
  const iconPath = join(__dirname, '../../resources/icon.ico');
  const icon = nativeImage.createFromPath(iconPath);
  
  tray = new Tray(icon);
  
  // 创建托盘菜单
  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
        } else {
          createWindow();
        }
      }
    },
    {
      label: '开始/停止监控',
      click: () => {
        mainWindow?.webContents.send('toggle-monitor');
      }
    },
    {
      label: '开始/停止录屏',
      click: () => {
        if (features.enableRecording) {
          mainWindow?.webContents.send('toggle-recording');
        }
      },
      enabled: features.enableRecording
    },
    {
      type: 'separator'
    },
    {
      label: '退出',
      click: () => {
        // 停止DLL进程
        if (dllProcess) {
          dllProcess.kill();
        }
        
        // 清除同步定时器
        if (syncInterval) {
          clearInterval(syncInterval);
        }
        
        app.quit();
      }
    }
  ]);
  
  tray.setToolTip('Activity Analytics');
  tray.setContextMenu(contextMenu);
  
  // 点击托盘图标显示/隐藏窗口
  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
      }
    } else {
      createWindow();
    }
  });
}

// 启动DLL进程
function startDllProcess() {
  const dllPath = join(__dirname, '../../native/Release/monitor.exe');
  
  // 检查DLL是否存在
  if (!fsSync.existsSync(dllPath)) {
    console.error('DLL文件不存在:', dllPath);
    return;
  }
  
  // 启动DLL进程
  dllProcess = exec(`"${dllPath}"`, (error, stdout, stderr) => {
    if (error) {
      console.error('DLL进程错误:', error);
      return;
    }
    if (stderr) {
      console.error('DLL错误输出:', stderr);
      return;
    }
    console.log('DLL输出:', stdout);
  });
  
  // 监听进程退出
  dllProcess.on('exit', (code: number) => {
    console.log(`DLL进程已退出，代码: ${code}`);
    // 如果不是正常退出，尝试重启
    if (code !== 0 && app.isReady()) {
      console.log('尝试重启DLL进程...');
      setTimeout(startDllProcess, 5000);
    }
  });
}

// 初始化目录
async function initializeDirectories() {
  const paths = [
    resolvePath(features.paths.recordings),
    resolvePath(features.paths.ocrCache),
    path.dirname(resolvePath(features.paths.database))
  ];
  
  for (const path of paths) {
    if (!fsSync.existsSync(path)) {
      await fs.mkdir(path, { recursive: true });
      console.log(`创建目录: ${path}`);
    }
  }
}

// 应用就绪
app.whenReady().then(async () => {
  // 初始化目录
  await initializeDirectories();
  
  // 创建窗口和托盘
  createWindow();
  createTray();
  
  // 初始化系统控制器
  const systemController = new SystemController();
  
  // 启动管道服务器
  startPipeServer(systemController);
  
  // 启动DLL进程
  startDllProcess();
  
  // 如果启用了云同步，初始化上传器
  if (features.enableCloud) {
    cloudUploader = new CloudUploader();
    syncInterval = cloudUploader.startAutoSync();
  }
  
  // 监听渲染进程消息
  ipcMain.on('toggle-monitor', (_, enable) => {
    systemController.toggleMonitoring(enable);
  });
  
  ipcMain.on('toggle-recording', (_, enable) => {
    if (enable) {
      systemController.startRecording();
      // 录屏时改变托盘图标颜色为红色
      tray?.setToolTip('Activity Analytics - 正在录屏');
    } else {
      systemController.stopRecording();
      tray?.setToolTip('Activity Analytics');
    }
  });
  
  ipcMain.handle('get-historical-data', async (_, startTime, endTime) => {
    return await systemController.getHistoricalData(startTime, endTime);
  });
  
  ipcMain.handle('get-features-status', () => {
    return {
      enableRecording: features.enableRecording,
      enableOCR: features.enableOCR,
      enableCloud: features.enableCloud
    };
  });
  
  // 监听窗口关闭事件
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// 所有窗口关闭时退出
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// 应用退出前清理
app.on('will-quit', () => {
  if (dllProcess) {
    dllProcess.kill();
  }
  
  if (syncInterval) {
    clearInterval(syncInterval);
  }
});
    