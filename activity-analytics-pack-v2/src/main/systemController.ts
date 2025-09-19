import { ipcMain } from 'electron';
import { Sequelize, Model, DataTypes } from 'sequelize';
import path from 'path';
import { features } from '../config';
import { resolvePath } from './utils/paths';

// 定义数据模型接口
interface SystemData {
  pid: number;
  title: string;
  exe: string;
  cpu: number;
  mem: number;
  kb: number;
  mouse: number;
  dB: number;
  timestamp: number;
}

interface OcrData {
  text: string;
  windowTitle: string;
  timestamp: number;
}

// 初始化数据库
const sequelize = new Sequelize({
  dialect: 'sqlite',
  storage: resolvePath(features.paths.database),
  logging: false // 禁用日志
});

// 系统数据模型
class SystemInfo extends Model<SystemData> implements SystemData {
  public pid!: number;
  public title!: string;
  public exe!: string;
  public cpu!: number;
  public mem!: number;
  public kb!: number;
  public mouse!: number;
  public dB!: number;
  public timestamp!: number;
}

// OCR数据模型
class OcrInfo extends Model<OcrData> implements OcrData {
  public text!: string;
  public windowTitle!: string;
  public timestamp!: number;
}

// 初始化模型
SystemInfo.init({
  pid: { type: DataTypes.INTEGER, allowNull: false },
  title: { type: DataTypes.STRING, allowNull: false },
  exe: { type: DataTypes.STRING, allowNull: false },
  cpu: { type: DataTypes.FLOAT, allowNull: false },
  mem: { type: DataTypes.FLOAT, allowNull: false },
  kb: { type: DataTypes.INTEGER, allowNull: false },
  mouse: { type: DataTypes.INTEGER, allowNull: false },
  dB: { type: DataTypes.FLOAT, allowNull: false },
  timestamp: { type: DataTypes.BIGINT, allowNull: false }
}, { sequelize });

OcrInfo.init({
  text: { type: DataTypes.TEXT, allowNull: false },
  windowTitle: { type: DataTypes.STRING, allowNull: false },
  timestamp: { type: DataTypes.BIGINT, allowNull: false }
}, { sequelize });

// 同步数据库
sequelize.sync();

export class SystemController {
  private isMonitoring: boolean = true;
  private isRecording: boolean = false;
  private lastOcrData: OcrData | null = null;
  
  constructor() {
    // 初始化状态
    this.isMonitoring = true;
  }
  
  // 处理实时数据
  async handleRealtimeData(data: any) {
    if (!this.isMonitoring) return;
    
    try {
      // 发送到前端
      ipcMain.emit('send-to-renderer', null, data);
      
      // 根据数据类型处理
      if (data.type === 'system') {
        // 保存系统信息
        await SystemInfo.create({
          pid: data.pid,
          title: data.title,
          exe: data.exe,
          cpu: data.cpu,
          mem: data.mem,
          kb: data.kb,
          mouse: data.mouse,
          dB: data.dB,
          timestamp: Date.now()
        });
        
        // 限制数据保留时间（30天）
        const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
        await SystemInfo.destroy({
          where: { timestamp: { [Op.lt]: thirtyDaysAgo } }
        });
      } else if (data.type === 'ocr') {
        // 保存OCR数据
        const ocrData: OcrData = {
          text: data.text,
          windowTitle: data.windowTitle || '',
          timestamp: Date.now()
        };
        
        await OcrInfo.create(ocrData);
        this.lastOcrData = ocrData;
        
        // 限制OCR数据保留时间（7天）
        const sevenDaysAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
        await OcrInfo.destroy({
          where: { timestamp: { [Op.lt]: sevenDaysAgo } }
        });
      } else if (data.type === 'recording') {
        // 录屏状态更新
        this.isRecording = data.active;
      }
    } catch (error) {
      console.error('处理实时数据失败:', error);
    }
  }
  
  // 获取历史数据
  async getHistoricalData(startTime: number, endTime: number) {
    try {
      const systemData = await SystemInfo.findAll({
        where: {
          timestamp: {
            [Op.gte]: startTime,
            [Op.lte]: endTime
          }
        },
        order: [['timestamp', 'ASC']]
      });
      
      const ocrData = await OcrInfo.findAll({
        where: {
          timestamp: {
            [Op.gte]: startTime,
            [Op.lte]: endTime
          }
        },
        order: [['timestamp', 'ASC']]
      });
      
      return {
        system: systemData,
        ocr: ocrData
      };
    } catch (error) {
      console.error('获取历史数据失败:', error);
      return { system: [], ocr: [] };
    }
  }
  
  // 切换监控状态
  toggleMonitoring(enable: boolean) {
    this.isMonitoring = enable;
    return this.isMonitoring;
  }
  
  // 开始录屏
  startRecording() {
    if (!features.enableRecording) return false;
    
    this.isRecording = true;
    // 通过管道发送开始录屏命令给DLL
    // 实际实现取决于与DLL的通信机制
    return true;
  }
  
  // 停止录屏
  stopRecording() {
    if (!features.enableRecording) return false;
    
    this.isRecording = false;
    // 通过管道发送停止录屏命令给DLL
    return true;
  }
  
  // 获取录屏状态
  isRecordingActive() {
    return this.isRecording;
  }
  
  // 获取最后一次OCR数据
  getLastOcrData() {
    return this.lastOcrData;
  }
}
    