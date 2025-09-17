import os
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from log.logger import LogLevel, Logger
from storage.encryptor import DataEncryptor

class LogManager:
    def __init__(self, log_dir: str = None, encryptor: DataEncryptor = None):
        """初始化日志管理器
        
        Args:
            log_dir: 日志存储目录，为None则使用默认目录
            encryptor: 日志加密器，为None则不加密
        """
        self.encryptor = encryptor
        
        # 确定日志目录
        if log_dir:
            self.log_dir = Path(log_dir)
        else:
            # 使用默认目录
            if os.name == 'nt':  # Windows
                appdata = Path(os.environ.get("APPDATA", ""))
                self.log_dir = appdata / "LocalInfoCollector" / "logs"
            else:  # Unix-like systems
                home = Path.home()
                self.log_dir = home / ".local_info_collector" / "logs"
        
        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 模块日志器缓存
        self.loggers = {}
    
    def get_logger(self, module_name: str) -> Logger:
        """获取指定模块的日志器
        
        Args:
            module_name: 模块名称
            
        Returns:
            日志器实例
        """
        if module_name not in self.loggers:
            self.loggers[module_name] = Logger(
                module_name=module_name,
                log_dir=str(self.log_dir),
                encryptor=self.encryptor
            )
        return self.loggers[module_name]
    
    def get_log_files(self) -> List[Path]:
        """获取所有日志文件
        
        Returns:
            日志文件路径列表（按日期排序）
        """
        log_files = [f for f in self.log_dir.glob("*.log") if f.is_file()]
        # 按修改时间排序，最新的在前
        return sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def read_log_file(self, file_path: Path) -> List[Dict[str, Any]]:
        """读取日志文件内容
        
        Args:
            file_path: 日志文件路径
            
        Returns:
            日志条目列表
        """
        logs = []
        
        if not file_path.exists() or not file_path.is_file():
            return logs
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                        
                    try:
                        # 解密日志（如果需要）
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
                            "module": "LogManager",
                            "message": "无法解析的日志行",
                            "data": {"raw_line": line, "file": str(file_path)}
                        })
            
            # 按时间戳排序
            return sorted(logs, key=lambda x: x.get("timestamp", ""))
            
        except Exception as e:
            return [{
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "level": "ERROR",
                "module": "LogManager",
                "message": f"读取日志文件失败: {str(e)}",
                "data": {"file": str(file_path)}
            }]
    
    def search_logs(
        self,
        query: str = None,
        level: LogLevel = None,
        module: str = None,
        start_time: str = None,
        end_time: str = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """搜索日志
        
        Args:
            query: 搜索关键词
            level: 日志级别筛选
            module: 模块名称筛选
            start_time: 开始时间（格式：YYYY-MM-DD HH:MM:SS）
            end_time: 结束时间（格式：YYYY-MM-DD HH:MM:SS）
            limit: 最大结果数量
            
        Returns:
            符合条件的日志条目列表
        """
        matching_logs = []
        log_files = self.get_log_files()
        
        # 遍历所有日志文件
        for log_file in log_files:
            # 如果已经找到足够的结果，停止搜索
            if len(matching_logs) >= limit:
                break
                
            # 读取日志文件
            logs = self.read_log_file(log_file)
            
            # 筛选日志
            for log in logs:
                # 检查是否符合所有筛选条件
                if self._log_matches_filters(log, query, level, module, start_time, end_time):
                    matching_logs.append(log)
                    
                    # 如果达到结果上限，停止
                    if len(matching_logs) >= limit:
                        break
        
        # 按时间戳排序（最新的在前）
        return sorted(
            matching_logs, 
            key=lambda x: x.get("timestamp", ""), 
            reverse=True
        )
    
    def _log_matches_filters(
        self,
        log: Dict[str, Any],
        query: str = None,
        level: LogLevel = None,
        module: str = None,
        start_time: str = None,
        end_time: str = None
    ) -> bool:
        """检查日志是否符合筛选条件
        
        Args:
            log: 日志条目
            query: 搜索关键词
            level: 日志级别筛选
            module: 模块名称筛选
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            如果符合条件则为True，否则为False
        """
        # 检查日志级别
        if level and log.get("level") != level.value:
            return False
            
        # 检查模块
        if module and log.get("module") != module:
            return False
            
        # 检查时间范围
        log_time = log.get("timestamp", "")
        if start_time and log_time < start_time:
            return False
        if end_time and log_time > end_time:
            return False
            
        # 检查搜索关键词
        if query:
            query_lower = query.lower()
            # 检查消息中是否包含关键词
            if query_lower not in log.get("message", "").lower():
                # 检查数据中是否包含关键词
                data_str = str(log.get("data", "")).lower()
                if query_lower not in data_str:
                    return False
                    
        return True
    
    def export_logs(
        self,
        output_file: str,
        **search_kwargs
    ) -> bool:
        """导出日志
        
        Args:
            output_file: 输出文件路径
           ** search_kwargs: 搜索参数（与search_logs相同）
            
        Returns:
            如果导出成功则为True，否则为False
        """
        try:
            # 搜索符合条件的日志
            logs = self.search_logs(**search_kwargs)
            
            # 写入到输出文件
            with open(output_file, "w", encoding="utf-8") as f:
                # 如果有加密器，导出时使用明文
                json.dump(logs, f, indent=2, ensure_ascii=False)
                
            return True
        except Exception as e:
            # 记录导出失败的日志
            logger = self.get_logger("LogManager")
            logger.error(f"导出日志失败: {str(e)}", {"output_file": output_file})
            return False
    
    def delete_old_logs(self, days_to_keep: int = 30) -> Tuple[int, List[str]]:
        """删除旧日志
        
        Args:
            days_to_keep: 保留最近多少天的日志
            
        Returns:
            (删除的文件数量, 删除的文件路径列表)
        """
        deleted_count = 0
        deleted_files = []
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        
        for log_file in self.get_log_files():
            # 检查文件修改时间
            if log_file.stat().st_mtime < cutoff_time:
                try:
                    log_file.unlink()
                    deleted_count += 1
                    deleted_files.append(str(log_file))
                except Exception as e:
                    # 记录删除失败的日志
                    logger = self.get_logger("LogManager")
                    logger.error(f"删除日志文件失败: {str(e)}", {"file": str(log_file)})
        
        return deleted_count, deleted_files
