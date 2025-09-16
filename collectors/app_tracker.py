import psutil
import time
from threading import Thread, Lock
from dataclasses import dataclass
from typing import Dict, List, Optional
import win32process
import win32gui
import pythoncom
import win32con

@dataclass
class AppInfo:
    pid: int
    name: str
    executable: str
    window_title: str
    start_time: float
    active_time: float  # 应用处于活跃状态的总时间
    last_seen: float
    cpu_usage: float
    memory_usage: float  # MB

class AppTracker:
    def __init__(self):
        self.running = False
        self.apps: Dict[int, AppInfo] = {}  # 以PID为键
        self.thread = None
        self.update_interval = 1  # 每秒更新一次
        self.lock = Lock()
        self.last_active_window = None
        self.last_check_time = time.time()
    
    def start(self):
        """启动应用跟踪"""
        self.running = True
        self.thread = Thread(target=self._tracking_loop, daemon=True)
        self.thread.start()
        self.last_check_time = time.time()
    
    def stop(self):
        """停止应用跟踪"""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def get_running_apps(self) -> List[AppInfo]:
        """获取当前运行的应用列表"""
        with self.lock:
            return list(self.apps.values())
    
    def get_active_app(self) -> Optional[AppInfo]:
        """获取当前活跃的应用"""
        active_window = self._get_active_window_pid()
        if active_window and active_window in self.apps:
            return self.apps[active_window]
        return None
    
    def _get_active_window_pid(self) -> Optional[int]:
        """获取当前活跃窗口的PID"""
        try:
            pythoncom.CoInitialize()
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return None
                
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return pid
        except:
            return None
        finally:
            pythoncom.CoUninitialize()
    
    def _get_window_title(self, pid: int) -> str:
        """根据PID获取窗口标题"""
        try:
            pythoncom.CoInitialize()
            titles = []
            
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                    if window_pid == pid:
                        title = win32gui.GetWindowText(hwnd)
                        if title:
                            titles.append(title)
            
            win32gui.EnumWindows(callback, None)
            return max(titles, key=len) if titles else ""
        except:
            return ""
        finally:
            pythoncom.CoUninitialize()
    
    def _update_app_active_time(self):
        """更新应用的活跃时间"""
        current_time = time.time()
        elapsed = current_time - self.last_check_time
        self.last_check_time = current_time
        
        active_pid = self._get_active_window_pid()
        
        with self.lock:
            # 更新当前活跃应用的活跃时间
            if active_pid in self.apps:
                self.apps[active_pid].active_time += elapsed
                self.apps[active_pid].last_seen = current_time
            
            # 清理已退出的应用（超过5秒未更新）
            to_remove = [pid for pid, app in self.apps.items() 
                        if current_time - app.last_seen > 5]
            for pid in to_remove:
                del self.apps[pid]
    
    def _tracking_loop(self):
        """跟踪循环，持续监控应用状态"""
        while self.running:
            # 更新应用活跃时间
            self._update_app_active_time()
            
            # 获取当前所有进程
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'create_time', 'cpu_percent', 'memory_info']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name'] or "Unknown"
                    executable = proc.info['exe'] or "Unknown"
                    create_time = proc.info['create_time'] or time.time()
                    
                    # 计算内存使用量(MB)
                    memory_usage = round(proc.info['memory_info'].rss / (1024 **2), 2)
                    
                    with self.lock:
                        # 如果是新进程，添加到应用列表
                        if pid not in self.apps:
                            window_title = self._get_window_title(pid)
                            self.apps[pid] = AppInfo(
                                pid=pid,
                                name=name,
                                executable=executable,
                                window_title=window_title,
                                start_time=create_time,
                                active_time=0,
                                last_seen=time.time(),
                                cpu_usage=0,
                                memory_usage=memory_usage
                            )
                        # 更新现有进程信息
                        else:
                            self.apps[pid].name = name
                            self.apps[pid].executable = executable
                            self.apps[pid].cpu_usage = proc.info['cpu_percent'] or 0
                            self.apps[pid].memory_usage = memory_usage
                            self.apps[pid].last_seen = time.time()
                            
                            # 更新窗口标题（定期更新，避免性能问题）
                            if int(time.time()) % 5 == 0:  # 每5秒更新一次
                                self.apps[pid].window_title = self._get_window_title(pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            # 等待下一次更新
            time.sleep(self.update_interval)
