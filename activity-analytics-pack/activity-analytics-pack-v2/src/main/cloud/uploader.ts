import fs from 'fs/promises';
import fsSync from 'fs';
import path from 'path';
import { createHash } from 'crypto';
import { createCloudProvider, CloudProvider } from './providers';
import { features } from '../../config';
import { getAppDataPath } from '../utils/paths';
import { encryptData, decryptData } from '../utils/encryption';

// 替换路径中的环境变量
function resolvePath(pathStr: string): string {
  return pathStr.replace('%APPDATA%', getAppDataPath());
}

// 获取最新的录像文件
async function getNewestRecording(): Promise<string | null> {
  const recordingDir = resolvePath(features.paths.recordings);
  
  if (!fsSync.existsSync(recordingDir)) {
    return null;
  }
  
  const files = await fs.readdir(recordingDir);
  const mp4Files = files
    .filter(file => file.endsWith('.mp4'))
    .map(file => ({
      name: file,
      path: path.join(recordingDir, file),
      mtime: fsSync.statSync(path.join(recordingDir, file)).mtimeMs
    }))
    .sort((a, b) => b.mtime - a.mtime);
  
  return mp4Files.length > 0 ? mp4Files[0].path : null;
}

// 获取文件哈希
async function getFileHash(filePath: string): Promise<string> {
  const buffer = await fs.readFile(filePath);
  return createHash('sha256').update(buffer).digest('hex');
}

// 本地缓存管理
class SyncCache {
  private cachePath: string;
  private cache: {
    lastDbHash: string;
    lastSyncedFiles: Record<string, string>;
    lastSyncTime: number;
  };
  
  constructor() {
    this.cachePath = path.join(resolvePath(features.paths.ocrCache), 'sync-cache.json');
    this.cache = this.loadCache();
  }
  
  private loadCache(): any {
    if (fsSync.existsSync(this.cachePath)) {
      try {
        return JSON.parse(fsSync.readFileSync(this.cachePath, 'utf8'));
      } catch (error) {
        console.error('加载同步缓存失败:', error);
      }
    }
    
    return {
      lastDbHash: '',
      lastSyncedFiles: {},
      lastSyncTime: 0
    };
  }
  
  save(): void {
    try {
      const dir = path.dirname(this.cachePath);
      if (!fsSync.existsSync(dir)) {
        fsSync.mkdirSync(dir, { recursive: true });
      }
      fsSync.writeFileSync(this.cachePath, JSON.stringify(this.cache, null, 2), 'utf8');
    } catch (error) {
      console.error('保存同步缓存失败:', error);
    }
  }
  
  getLastDbHash(): string {
    return this.cache.lastDbHash;
  }
  
  setLastDbHash(hash: string): void {
    this.cache.lastDbHash = hash;
    this.save();
  }
  
  getFileLastSyncedHash(filePath: string): string | undefined {
    return this.cache.lastSyncedFiles[filePath];
  }
  
  setFileLastSyncedHash(filePath: string, hash: string): void {
    this.cache.lastSyncedFiles[filePath] = hash;
    this.save();
  }
  
  updateLastSyncTime(): void {
    this.cache.lastSyncTime = Date.now();
    this.save();
  }
}

export class CloudUploader {
  private provider: CloudProvider;
  private cache: SyncCache;
  private isSyncing: boolean = false;
  private retryCount: number = 0;
  private maxRetries: number = 3;
  
  constructor() {
    this.provider = createCloudProvider();
    this.cache = new SyncCache();
  }
  
  // 开始增量同步
  async sync(): Promise<boolean> {
    if (this.isSyncing) {
      console.log('同步正在进行中，跳过此次请求');
      return false;
    }
    
    this.isSyncing = true;
    let success = false;
    
    try {
      console.log('开始增量同步...');
      
      // 1. 同步数据库
      await this.syncDatabase();
      
      // 2. 同步最新录像
      await this.syncLatestRecording();
      
      // 3. 同步OCR文本
      await this.syncOcrData();
      
      // 更新最后同步时间
      this.cache.updateLastSyncTime();
      success = true;
      this.retryCount = 0; // 重置重试计数
      console.log('同步完成');
    } catch (error) {
      console.error('同步失败:', error);
      this.retryCount++;
      
      // 如果重试次数未达上限，重试
      if (this.retryCount < this.maxRetries) {
        console.log(`将在5秒后进行第${this.retryCount + 1}次重试...`);
        await new Promise(resolve => setTimeout(resolve, 5000));
        return this.sync();
      } else {
        console.error(`已达到最大重试次数(${this.maxRetries})，同步终止`);
      }
    } finally {
      this.isSyncing = false;
    }
    
    return success;
  }
  
  // 同步数据库
  private async syncDatabase(): Promise<void> {
    const dbPath = resolvePath(features.paths.database);
    
    if (!fsSync.existsSync(dbPath)) {
      console.log('数据库文件不存在，跳过同步');
      return;
    }
    
    const currentHash = await getFileHash(dbPath);
    const lastHash = this.cache.getLastDbHash();
    
    if (currentHash !== lastHash) {
      console.log('数据库有更新，开始同步...');
      
      // 读取并加密数据库
      const dbData = await fs.readFile(dbPath);
      const encryptedData = encryptData(dbData, features.cloud.encryptionKey);
      
      // 上传
      const timestamp = new Date().toISOString().replace(/:/g, '-');
      await this.provider.uploadFile(`database/${timestamp}.db.enc`, encryptedData);
      
      // 更新缓存
      this.cache.setLastDbHash(currentHash);
      console.log('数据库同步完成');
    } else {
      console.log('数据库无更新，跳过同步');
    }
  }
  
  // 同步最新录像
  private async syncLatestRecording(): Promise<void> {
    const recordingPath = await getNewestRecording();
    
    if (!recordingPath) {
      console.log('没有找到录像文件，跳过同步');
      return;
    }
    
    const currentHash = await getFileHash(recordingPath);
    const lastHash = this.cache.getFileLastSyncedHash(recordingPath);
    
    if (currentHash !== lastHash) {
      console.log(`录像文件 ${path.basename(recordingPath)} 有更新，开始同步...`);
      
      // 读取并加密录像
      const videoData = await fs.readFile(recordingPath);
      const encryptedData = encryptData(videoData, features.cloud.encryptionKey);
      
      // 上传
      const fileName = path.basename(recordingPath);
      await this.provider.uploadFile(`recordings/${fileName}.enc`, encryptedData);
      
      // 更新缓存
      this.cache.setFileLastSyncedHash(recordingPath, currentHash);
      console.log('录像同步完成');
    } else {
      console.log(`录像文件 ${path.basename(recordingPath)} 无更新，跳过同步`);
    }
  }
  
  // 同步OCR数据
  private async syncOcrData(): Promise<void> {
    const ocrDir = resolvePath(features.paths.ocrCache);
    
    if (!fsSync.existsSync(ocrDir)) {
      console.log('OCR缓存目录不存在，跳过同步');
      return;
    }
    
    // 获取最近24小时的OCR文件
    const files = await fs.readdir(ocrDir);
    const recentOcrFiles = files
      .filter(file => file.endsWith('.json'))
      .map(file => ({
        name: file,
        path: path.join(ocrDir, file),
        mtime: fsSync.statSync(path.join(ocrDir, file)).mtimeMs
      }))
      .filter(file => Date.now() - file.mtime < 24 * 60 * 60 * 1000) // 24小时内
      .sort((a, b) => b.mtime - a.mtime);
    
    for (const file of recentOcrFiles) {
      const currentHash = await getFileHash(file.path);
      const lastHash = this.cache.getFileLastSyncedHash(file.path);
      
      if (currentHash !== lastHash) {
        console.log(`OCR文件 ${file.name} 有更新，开始同步...`);
        
        // 读取并加密OCR数据
        const ocrData = await fs.readFile(file.path);
        const encryptedData = encryptData(ocrData, features.cloud.encryptionKey);
        
        // 上传
        await this.provider.uploadFile(`ocr/${file.name}.enc`, encryptedData);
        
        // 更新缓存
        this.cache.setFileLastSyncedHash(file.path, currentHash);
      }
    }
    
    console.log('OCR数据同步完成');
  }
  
  // 启动定时同步
  startAutoSync(): NodeJS.Timeout {
    console.log(`启动自动同步，间隔 ${features.cloud.syncIntervalMin} 分钟`);
    
    // 立即执行一次同步
    this.sync();
    
    // 设置定时任务
    return setInterval(() => {
      this.sync();
    }, features.cloud.syncIntervalMin * 60 * 1000);
  }
}
    