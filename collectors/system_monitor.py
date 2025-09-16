from collectors.cpu_monitor import CpuMonitor, CpuData
from collectors.memory_monitor import MemoryMonitor, MemoryData
from collectors.disk_monitor import DiskMonitor, DiskData
from collectors.app_tracker import AppTracker, AppInfo
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class SystemData:
    cpu: Optional[CpuData]
    memory: Optional[MemoryData]
    disk: Optional[DiskData]
    timestamp: float

class SystemMonitor:
    def __init__(self):
        # 初始化各个监控器
        self.cpu_monitor = CpuMonitor()
        self.memory_monitor = MemoryMonitor()
        self.disk_monitor = DiskMonitor()
        self.app_tracker = AppTracker()
    
    def start_monitoring(self):
        """启动所有监控器"""
        self.cpu_monitor.start()
        self.memory_monitor.start()
        self.disk_monitor.start()
        self.app_tracker.start()
    
    def stop_monitoring(self):
        """停止所有监控器"""
        self.cpu_monitor.stop()
        self.memory_monitor.stop()
        self.disk_monitor.stop()
        self.app_tracker.stop()
    
    def get_latest_system_data(self) -> SystemData:
        """获取最新的系统数据汇总"""
        return SystemData(
            cpu=self.cpu_monitor.get_latest_data(),
            memory=self.memory_monitor.get_latest_data(),
            disk=self.disk_monitor.get_latest_data(),
            timestamp=self._get_latest_timestamp()
        )
    
    def get_running_applications(self) -> List[AppInfo]:
        """获取运行中的应用程序列表"""
        return self.app_tracker.get_running_apps()
    
    def get_active_application(self) -> Optional[AppInfo]:
        """获取当前活跃的应用程序"""
        return self.app_tracker.get_active_app()
    
    def _get_latest_timestamp(self) -> float:
        """获取最新数据的时间戳"""
        timestamps = []
        if self.cpu_monitor.data:
            timestamps.append(self.cpu_monitor.data.timestamp)
        if self.memory_monitor.data:
            timestamps.append(self.memory_monitor.data.timestamp)
        if self.disk_monitor.data:
            timestamps.append(self.disk_monitor.data.timestamp)
        
        return max(timestamps) if timestamps else 0
