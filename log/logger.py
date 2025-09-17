import os
import time
import json
from pathlib import Path
from enum import Enum
from typing import Dict, Any, Optional
from storage.encryptor import DataEncryptor

class LogLevel(Enum):
    """日志级别枚举"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Logger:
    def __init__(
        self, 
        module_name: str, 
        log_dir: str = None, 
        encryptor: DataEncryptor = None,
        max_log_size: int = 10 * 1024 * 1024,  # 10MB
        max_log_files: int = 30  # 最多保留30个日志文件
    ):
        """初始化日志记录器
        
        Args:
            module_name: 模块名称，用于标识日志来源
            log_dir: 日志存储目录，为None则使用默认目录
            encryptor: 日志加密器，为None则不加密
            max_log_size: 单个日志文件的最大大小（字节）
            max_log_files: 最多保留的日志文件数量
        """
        self.module_name = module_name
        self.encryptor = encryptor
        self.max_log_size = max_log_size
        self.max_log_files = max_log_files
        
        # 确定日志目录
        self.log_dir = self._get_log_dir(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前日志文件路径
        self.current_log_file = self._get_current_log_file()
    
    def _get_log_dir(self, custom_dir: Optional[str]) -> Path:
        """获取日志存储目录"""
        if custom_dir:
            return Path(custom_dir)
            
        # 使用默认目录
        if os.name == 'nt':  # Windows
            appdata = Path(os.environ.get("APPDATA", ""))
            return appdata / "LocalInfoCollector" / "logs"
        else:  # Unix-like systems
            home = Path.home()
            return home / ".local_info_collector" / "logs"
    
    def _get_current_log_file(self) -> Path:
        """获取当前日志文件路径"""
        today = time.strftime("%Y-%m-%d")
        return self.log_dir / f"{today}.log"
    
    def _rotate_logs(self):
        """日志轮转处理"""
        # 检查当前日志文件大小
        if self.current_log_file.exists() and self.current_log_file.stat().st_size >= self.max_log_size:
            # 重命名当前日志文件
            timestamp = time.strftime("%H-%M-%S")
            rotated_file = self.log_dir / f"{self.current_log_file.stem}_{timestamp}.log"
            self.current_log_file.rename(rotated_file)
        
        # 清理旧日志文件
        self._cleanup_old_logs()
        
        # 确保当前日志文件是最新的（按日期）
        current_date_file = self._get_current_log_file()
        if current_date_file != self.current_log_file:
            self.current_log_file = current_date_file
    
    def _cleanup_old_logs(self):
        """清理超过保留数量的旧日志文件"""
        # 获取所有日志文件并按修改时间排序
        log_files = sorted(
            [f for f in self.log_dir.glob("*.log") if f.is_file()],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        # 如果日志文件数量超过最大值，删除最旧的
        if len(log_files) > self.max_log_files:
            for old_file in log_files[self.max_log_files:]:
                try:
                    old_file.unlink()
                except Exception as e:
                    self.error(f"无法删除旧日志文件 {old_file}: {str(e)}")
    
    def _format_log(self, level: LogLevel, message: str, data: Optional[Dict[str, Any]] = None) -> str:
        """格式化日志条目
        
        Args:
            level: 日志级别
            message: 日志消息
            data: 附加数据
            
        Returns:
            格式化的日志字符串
        """
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "level": level.value,
            "module": self.module_name,
            "message": message
        }
        
        if data is not None:
            log_entry["data"] = data
        
        # 如果有加密器，则加密日志内容
        if self.encryptor:
            return self.encryptor.encrypt(log_entry)
        return json.dumps(log_entry)
    
    def log(self, level: LogLevel, message: str, data: Optional[Dict[str, Any]] = None):
        """记录日志
        
        Args:
            level: 日志级别
            message: 日志消息
            data: 附加数据
        """
        try:
            # 处理日志轮转
            self._rotate_logs()
            
            # 格式化日志
            log_line = self._format_log(level, message, data)
            
            # 写入日志文件
            with open(self.current_log_file, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
                
        except Exception as e:
            # 日志记录失败时，尝试打印到控制台
            print(f"日志记录失败: {str(e)}")
            print(f"尝试记录的日志: {level.value} - {message}")
    
    def debug(self, message: str, data: Optional[Dict[str, Any]] = None):
        """记录DEBUG级别的日志"""
        self.log(LogLevel.DEBUG, message, data)
    
    def info(self, message: str, data: Optional[Dict[str, Any]] = None):
        """记录INFO级别的日志"""
        self.log(LogLevel.INFO, message, data)
    
    def warning(self, message: str, data: Optional[Dict[str, Any]] = None):
        """记录WARNING级别的日志"""
        self.log(LogLevel.WARNING, message, data)
    
    def error(self, message: str, data: Optional[Dict[str, Any]] = None):
        """记录ERROR级别的日志"""
        self.log(LogLevel.ERROR, message, data)
    
    def critical(self, message: str, data: Optional[Dict[str, Any]] = None):
        """记录CRITICAL级别的日志"""
        self.log(LogLevel.CRITICAL, message, data)
    
    def get_recent_logs(self, limit: int = 100) -> list:
        """获取最近的日志记录
        
        Args:
            limit: 要获取的日志数量
            
        Returns:
            日志记录列表
        """
        logs = []
        
        try:
            # 如果当前日志文件存在，读取日志
            if self.current_log_file.exists():
                with open(self.current_log_file, "r", encoding="utf-8") as f:
                    # 读取所有日志行
                    lines = f.readlines()
                    
                    # 从最后一行开始，取指定数量的日志
                    start_idx = max(0, len(lines) - limit)
                    for line in lines[start_idx:]:
                        line = line.strip()
                        if not line:
                            continue
                            
                        try:
                            # 如果有加密器，则解密日志
                            if self.encryptor:
                                log_entry = self.encryptor.decrypt(line)
                            else:
                                log_entry = json.loads(line)
                                
                            logs.append(log_entry)
                        except:
                            # 无法解析的日志行
                            logs.append({
                                "timestamp": "unknown",
                                "level": "ERROR",
                                "module": "Logger",
                                "message": "无法解析的日志行",
                                "data": {"raw_line": line}
                            })
            
            # 按时间戳排序（应该已经是按时间排序的，但保险起见）
            logs.sort(key=lambda x: x.get("timestamp", ""))
            return logs
            
        except Exception as e:
            return [{
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "level": "ERROR",
                "module": "Logger",
                "message": f"获取日志失败: {str(e)}"
            }]
