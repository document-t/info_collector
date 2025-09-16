import psutil
import time
from threading import Thread
from dataclasses import dataclass

@dataclass
class CpuData:
    usage: float
    cores: int
    frequency: float
    timestamp: float

class CpuMonitor:
    def __init__(self):
        self.running = False
        self.data = None
        self.thread = None
        self.update_interval = 1  # 每秒更新一次
    
    def start(self):
        """启动CPU监控"""
        self.running = True
        self.thread = Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """停止CPU监控"""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def get_latest_data(self) -> CpuData:
        """获取最新的CPU数据"""
        return self.data
    
    def _monitor_loop(self):
        """监控循环，持续采集CPU数据"""
        while self.running:
            # 获取CPU使用率（间隔1秒的平均值）
            usage = psutil.cpu_percent(interval=1)
            
            # 获取CPU核心数
            cores = psutil.cpu_count(logical=False) or 0
            
            # 获取CPU频率
            freq = psutil.cpu_freq()
            frequency = freq.current if freq else 0
            
            # 存储数据
            self.data = CpuData(
                usage=usage,
                cores=cores,
                frequency=frequency,
                timestamp=time.time()
            )
            
            # 等待下一次采集
            time.sleep(self.update_interval)
