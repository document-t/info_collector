import psutil
import time
from threading import Thread
from dataclasses import dataclass

@dataclass
class MemoryData:
    total: float  # 总内存(GB)
    available: float  # 可用内存(GB)
    used: float  # 已用内存(GB)
    usage: float  # 使用率(%)
    timestamp: float

class MemoryMonitor:
    def __init__(self):
        self.running = False
        self.data = None
        self.thread = None
        self.update_interval = 1  # 每秒更新一次
        self.gb_conversion = 1024 ** 3  # 转换为GB的系数
    
    def start(self):
        """启动内存监控"""
        self.running = True
        self.thread = Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """停止内存监控"""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def get_latest_data(self) -> MemoryData:
        """获取最新的内存数据"""
        return self.data
    
    def _monitor_loop(self):
        """监控循环，持续采集内存数据"""
        while self.running:
            # 获取内存信息
            mem = psutil.virtual_memory()
            
            # 转换为GB并保留两位小数
            total = round(mem.total / self.gb_conversion, 2)
            available = round(mem.available / self.gb_conversion, 2)
            used = round(mem.used / self.gb_conversion, 2)
            
            # 存储数据
            self.data = MemoryData(
                total=total,
                available=available,
                used=used,
                usage=mem.percent,
                timestamp=time.time()
            )
            
            # 等待下一次采集
            time.sleep(self.update_interval)
