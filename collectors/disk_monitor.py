import psutil
import time
from threading import Thread
from dataclasses import dataclass
from typing import List

@dataclass
class DiskPartitionData:
    device: str
    mountpoint: str
    fstype: str
    total: float  # GB
    used: float  # GB
    free: float  # GB
    usage: float  # %

@dataclass
class DiskIOData:
    read_count: int
    write_count: int
    read_bytes: float  # MB
    write_bytes: float  # MB
    read_time: int
    write_time: int

@dataclass
class DiskData:
    partitions: List[DiskPartitionData]
    io: DiskIOData
    timestamp: float

class DiskMonitor:
    def __init__(self):
        self.running = False
        self.data = None
        self.thread = None
        self.update_interval = 2  # 每2秒更新一次
        self.gb_conversion = 1024 ** 3  # 转换为GB的系数
        self.mb_conversion = 1024 ** 2  # 转换为MB的系数
        self.last_io = None
    
    def start(self):
        """启动磁盘监控"""
        self.running = True
        self.thread = Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        # 初始化IO数据
        self.last_io = psutil.disk_io_counters()
    
    def stop(self):
        """停止磁盘监控"""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def get_latest_data(self) -> DiskData:
        """获取最新的磁盘数据"""
        return self.data
    
    def _get_partition_data(self) -> List[DiskPartitionData]:
        """获取磁盘分区数据"""
        partitions = []
        for part in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(part.mountpoint)
                partitions.append(DiskPartitionData(
                    device=part.device,
                    mountpoint=part.mountpoint,
                    fstype=part.fstype,
                    total=round(usage.total / self.gb_conversion, 2),
                    used=round(usage.used / self.gb_conversion, 2),
                    free=round(usage.free / self.gb_conversion, 2),
                    usage=usage.percent
                ))
            except PermissionError:
                continue  # 跳过无权限访问的分区
        return partitions
    
    def _get_io_data(self) -> DiskIOData:
        """获取磁盘IO数据"""
        current_io = psutil.disk_io_counters()
        
        if not self.last_io:
            self.last_io = current_io
            return DiskIOData(0, 0, 0, 0, 0, 0)
        
        # 计算两次采集之间的差值
        read_count = current_io.read_count - self.last_io.read_count
        write_count = current_io.write_count - self.last_io.write_count
        read_bytes = round((current_io.read_bytes - self.last_io.read_bytes) / self.mb_conversion, 2)
        write_bytes = round((current_io.write_bytes - self.last_io.write_bytes) / self.mb_conversion, 2)
        read_time = current_io.read_time - self.last_io.read_time
        write_time = current_io.write_time - self.last_io.write_time
        
        # 更新上次IO数据
        self.last_io = current_io
        
        return DiskIOData(
            read_count=read_count,
            write_count=write_count,
            read_bytes=read_bytes,
            write_bytes=write_bytes,
            read_time=read_time,
            write_time=write_time
        )
    
    def _monitor_loop(self):
        """监控循环，持续采集磁盘数据"""
        while self.running:
            # 获取磁盘分区数据
            partitions = self._get_partition_data()
            
            # 获取磁盘IO数据
            io_data = self._get_io_data()
            
            # 存储数据
            self.data = DiskData(
                partitions=partitions,
                io=io_data,
                timestamp=time.time()
            )
            
            # 等待下一次采集
            time.sleep(self.update_interval)
