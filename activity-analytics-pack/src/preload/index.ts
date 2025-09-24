import { contextBridge, ipcRenderer } from 'electron';


interface ElectronAPI {
  onRealtime: (callback: (data: any) => void) => void;
  toggleMonitor: (enable: boolean) => void;
  getHistoricalData: (startTime: number, endTime: number) => Promise<any[]>;
}

// 安全地暴露API到全局
contextBridge。exposeInMainWorld('electronAPI', {
  onRealtime: (callback) => {
    ipcRenderer.on('realtime', (_, data) => callback(data));
  },
  toggleMonitor: (enable) => {
    ipcRenderer.send('toggle-monitor', enable);
  },
  getHistoricalData: (startTime, endTime) => {
    return ipcRenderer.invoke('get-historical-data', startTime, endTime);
  }
} as ElectronAPI);
