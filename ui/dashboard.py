import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import time
import datetime
from threading import Thread
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter

class Dashboard:
    def __init__(self, root, app):
        self.root = root
        self.app = app  # 应用程序主对象
        self.root.title("本地信息收集系统")
        self.root.geometry("1200x800")
        
        # 设置中文字体支持
        plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
        
        self.running = True
        self.data_history = {
            'cpu': {'times': [], 'values': []},
            'memory': {'times': [], 'values': []},
            'disk_io_read': {'times': [], 'values': []},
            'disk_io_write': {'times': [], 'values': []}
        }
        self.history_limit = 60  # 保留60个数据点（约1分钟）
        
        # 创建主布局
        self._create_widgets()
        
        # 启动数据更新线程
        self.update_thread = Thread(target=self._update_data_loop, daemon=True)
        self.update_thread.start()
        
        # 启动数据保存线程
        self.save_thread = Thread(target=self._save_data_loop, daemon=True)
        self.save_thread.start()
    
    def _create_widgets(self):
        """创建界面组件"""
        # 顶部导航栏
        nav_frame = ttk.Frame(self.root, height=50)
        nav_frame.pack(fill=tk.X, padx=10, pady=5)
        nav_frame.pack_propagate(False)  # 保持高度
        
        ttk.Label(nav_frame, text="系统监控仪表盘", font=("Arial", 14, "bold")).pack(side=tk.LEFT, padx=10, pady=10)
        
        # 右侧按钮
        button_frame = ttk.Frame(nav_frame)
        button_frame.pack(side=tk.RIGHT, padx=10, pady=10)
        
        ttk.Button(button_frame, text="系统设置", command=self._open_settings).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="查看日志", command=self._open_log_viewer).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="数据导出", command=self._export_data).pack(side=tk.RIGHT, padx=5)
        
        # 主内容区
        content_frame = ttk.Frame(self.root)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 左侧边栏
        sidebar_frame = ttk.Frame(content_frame, width=200)
        sidebar_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        # 侧边栏按钮
        self.view_buttons = []
        views = ["概览", "CPU监控", "内存监控", "磁盘监控", "应用分析"]
        for view in views:
            btn = ttk.Button(
                sidebar_frame, 
                text=view, 
                command=lambda v=view: self._switch_view(v)
            )
            btn.pack(fill=tk.X, pady=5, padx=5)
            self.view_buttons.append(btn)
        
        # 主视图区域
        self.main_view_frame = ttk.Frame(content_frame)
        self.main_view_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 初始化概览视图
        self._init_overview_view()
    
    def _init_overview_view(self):
        """初始化概览视图"""
        # 清除当前视图
        for widget in self.main_view_frame.winfo_children():
            widget.destroy()
        
        # 创建状态条
        status_frame = ttk.Frame(self.main_view_frame)
        status_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(status_frame, text="系统状态:").pack(side=tk.LEFT)
        self.status_label = ttk.Label(status_frame, text="运行中", foreground="green")
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        self.time_label = ttk.Label(status_frame, text="")
        self.time_label.pack(side=tk.RIGHT)
        
        # 创建指标卡片区域
        metrics_frame = ttk.Frame(self.main_view_frame)
        metrics_frame.pack(fill=tk.X, pady=10)
        
        # 创建四个指标卡片
        card_width = 250
        card_height = 100
        
        # CPU使用率卡片
        self.cpu_card = ttk.LabelFrame(metrics_frame, text="CPU使用率", width=card_width, height=card_height)
        self.cpu_card.pack(side=tk.LEFT, padx=10)
        self.cpu_card.pack_propagate(False)
        self.cpu_label = ttk.Label(self.cpu_card, text="--%", font=("Arial", 24))
        self.cpu_label.pack(pady=30)
        
        # 内存使用率卡片
        self.memory_card = ttk.LabelFrame(metrics_frame, text="内存使用率", width=card_width, height=card_height)
        self.memory_card.pack(side=tk.LEFT, padx=10)
        self.memory_card.pack_propagate(False)
        self.memory_label = ttk.Label(self.memory_card, text="--%", font=("Arial", 24))
        self.memory_label.pack(pady=30)
        
        # 磁盘使用率卡片
        self.disk_card = ttk.LabelFrame(metrics_frame, text="磁盘使用率", width=card_width, height=card_height)
        self.disk_card.pack(side=tk.LEFT, padx=10)
        self.disk_card.pack_propagate(False)
        self.disk_label = ttk.Label(self.disk_card, text="--%", font=("Arial", 24))
        self.disk_label.pack(pady=30)
        
        # 当前应用卡片
        self.app_card = ttk.LabelFrame(metrics_frame, text="当前应用", width=card_width, height=card_height)
        self.app_card.pack(side=tk.LEFT, padx=10)
        self.app_card.pack_propagate(False)
        self.app_label = ttk.Label(self.app_card, text="无", font=("Arial", 12), wraplength=230)
        self.app_label.pack(pady=10)
        
        # 创建图表区域
        charts_frame = ttk.Frame(self.main_view_frame)
        charts_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # CPU和内存趋势图
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
        self.fig.tight_layout(pad=3.0)
        
        # CPU图表
        self.ax1.set_title("CPU使用率趋势")
        self.ax1.set_ylabel("使用率 (%)")
        self.ax1.set_ylim(0, 100)
        self.cpu_line, = self.ax1.plot([], [], 'r-')
        
        # 内存图表
        self.ax2.set_title("内存使用率趋势")
        self.ax2.set_ylabel("使用率 (%)")
        self.ax2.set_xlabel("时间")
        self.ax2.set_ylim(0, 100)
        self.memory_line, = self.ax2.plot([], [], 'b-')
        
        # 添加时间格式化
        self.date_format = DateFormatter('%H:%M:%S')
        self.ax2.xaxis.set_major_formatter(self.date_format)
        
        # 创建画布并显示
        self.canvas = FigureCanvasTkAgg(self.fig, master=charts_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 底部状态栏
        bottom_frame = ttk.Frame(self.main_view_frame)
        bottom_frame.pack(fill=tk.X, pady=5)
        
        self.db_status_label = ttk.Label(bottom_frame, text="数据存储: 未连接")
        self.db_status_label.pack(side=tk.LEFT)
        
        self.data_count_label = ttk.Label(bottom_frame, text="已收集数据: 0条")
        self.data_count_label.pack(side=tk.RIGHT)
    
    def _init_cpu_view(self):
        """初始化CPU监控视图"""
        # 清除当前视图
        for widget in self.main_view_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(
            self.main_view_frame, 
            text="CPU详细监控", 
            font=("Arial", 14, "bold")
        ).pack(pady=10, anchor=tk.W)
        
        # 创建CPU信息框架
        info_frame = ttk.Frame(self.main_view_frame)
        info_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # CPU核心数
        ttk.Label(info_frame, text="CPU核心数:").grid(row=0, column=0, padx=20, pady=5, sticky=tk.W)
        self.cpu_cores_label = ttk.Label(info_frame, text="--")
        self.cpu_cores_label.grid(row=0, column=1, padx=20, pady=5, sticky=tk.W)
        
        # CPU频率
        ttk.Label(info_frame, text="CPU频率:").grid(row=0, column=2, padx=20, pady=5, sticky=tk.W)
        self.cpu_freq_label = ttk.Label(info_frame, text="-- MHz")
        self.cpu_freq_label.grid(row=0, column=3, padx=20, pady=5, sticky=tk.W)
        
        # 创建图表框架
        chart_frame = ttk.Frame(self.main_view_frame)
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # CPU使用率图表
        self.cpu_fig = Figure(figsize=(10, 5))
        self.cpu_ax = self.cpu_fig.add_subplot(111)
        self.cpu_ax.set_title("CPU使用率历史")
        self.cpu_ax.set_ylabel("使用率 (%)")
        self.cpu_ax.set_xlabel("时间")
        self.cpu_ax.set_ylim(0, 100)
        self.cpu_ax.xaxis.set_major_formatter(self.date_format)
        
        self.cpu_chart_line, = self.cpu_ax.plot([], [], 'r-')
        
        self.cpu_canvas = FigureCanvasTkAgg(self.cpu_fig, master=chart_frame)
        self.cpu_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _init_memory_view(self):
        """初始化内存监控视图"""
        # 清除当前视图
        for widget in self.main_view_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(
            self.main_view_frame, 
            text="内存详细监控", 
            font=("Arial", 14, "bold")
        ).pack(pady=10, anchor=tk.W)
        
        # 创建内存信息框架
        info_frame = ttk.Frame(self.main_view_frame)
        info_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # 总内存
        ttk.Label(info_frame, text="总内存:").grid(row=0, column=0, padx=20, pady=5, sticky=tk.W)
        self.total_memory_label = ttk.Label(info_frame, text="-- GB")
        self.total_memory_label.grid(row=0, column=1, padx=20, pady=5, sticky=tk.W)
        
        # 已用内存
        ttk.Label(info_frame, text="已用内存:").grid(row=0, column=2, padx=20, pady=5, sticky=tk.W)
        self.used_memory_label = ttk.Label(info_frame, text="-- GB")
        self.used_memory_label.grid(row=0, column=3, padx=20, pady=5, sticky=tk.W)
        
        # 可用内存
        ttk.Label(info_frame, text="可用内存:").grid(row=1, column=0, padx=20, pady=5, sticky=tk.W)
        self.available_memory_label = ttk.Label(info_frame, text="-- GB")
        self.available_memory_label.grid(row=1, column=1, padx=20, pady=5, sticky=tk.W)
        
        # 创建图表框架
        chart_frame = ttk.Frame(self.main_view_frame)
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 内存使用率图表
        self.memory_fig = Figure(figsize=(10, 5))
        self.memory_ax = self.memory_fig.add_subplot(111)
        self.memory_ax.set_title("内存使用率历史")
        self.memory_ax.set_ylabel("使用率 (%)")
        self.memory_ax.set_xlabel("时间")
        self.memory_ax.set_ylim(0, 100)
        self.memory_ax.xaxis.set_major_formatter(self.date_format)
        
        self.memory_chart_line, = self.memory_ax.plot([], [], 'b-')
        
        self.memory_canvas = FigureCanvasTkAgg(self.memory_fig, master=chart_frame)
        self.memory_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _init_disk_view(self):
        """初始化磁盘监控视图"""
        # 清除当前视图
        for widget in self.main_view_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(
            self.main_view_frame, 
            text="磁盘详细监控", 
            font=("Arial", 14, "bold")
        ).pack(pady=10, anchor=tk.W)
        
        # 创建磁盘分区表格
        ttk.Label(
            self.main_view_frame, 
            text="磁盘分区信息", 
            font=("Arial", 12)
        ).pack(pady=5, anchor=tk.W, padx=10)
        
        columns = ("设备", "挂载点", "文件系统", "总容量(GB)", "已用(GB)", "可用(GB)", "使用率(%)")
        self.disk_tree = ttk.Treeview(self.main_view_frame, columns=columns, show="headings")
        
        # 设置列宽和标题
        for col in columns:
            self.disk_tree.heading(col, text=col)
            width = 100 if col != "设备" and col != "挂载点" else 150
            self.disk_tree.column(col, width=width, anchor=tk.CENTER)
        
        self.disk_tree.pack(fill=tk.X, pady=5, padx=10)
        
        # 创建图表框架
        chart_frame = ttk.Frame(self.main_view_frame)
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 磁盘IO图表
        self.disk_fig = Figure(figsize=(10, 5))
        self.disk_ax = self.disk_fig.add_subplot(111)
        self.disk_ax.set_title("磁盘IO速率 (MB/s)")
        self.disk_ax.set_ylabel("速率 (MB/s)")
        self.disk_ax.set_xlabel("时间")
        self.disk_ax.xaxis.set_major_formatter(self.date_format)
        
        self.disk_read_line, = self.disk_ax.plot([], [], 'g-', label="读取")
        self.disk_write_line, = self.disk_ax.plot([], [], 'r-', label="写入")
        self.disk_ax.legend()
        
        self.disk_canvas = FigureCanvasTkAgg(self.disk_fig, master=chart_frame)
        self.disk_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _init_app_view(self):
        """初始化应用分析视图"""
        # 清除当前视图
        for widget in self.main_view_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(
            self.main_view_frame, 
            text="应用程序分析", 
            font=("Arial", 14, "bold")
        ).pack(pady=10, anchor=tk.W)
        
        # 创建应用列表
        ttk.Label(
            self.main_view_frame, 
            text="当前运行的应用程序", 
            font=("Arial", 12)
        ).pack(pady=5, anchor=tk.W, padx=10)
        
        columns = ("PID", "名称", "CPU使用率(%)", "内存使用(MB)", "活跃时间(秒)")
        self.app_tree = ttk.Treeview(self.main_view_frame, columns=columns, show="headings")
        
        # 设置列宽和标题
        for col in columns:
            self.app_tree.heading(col, text=col)
            width = 80 if col == "PID" else 120 if col in ["CPU使用率(%)", "内存使用(MB)", "活跃时间(秒)"] else 250
            self.app_tree.column(col, width=width, anchor=tk.CENTER)
        
        # 添加滚动条
        app_scrollbar = ttk.Scrollbar(self.main_view_frame, orient="vertical", command=self.app_tree.yview)
        app_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.app_tree.configure(yscrollcommand=app_scrollbar.set)
        
        self.app_tree.pack(fill=tk.BOTH, expand=True, pady=5, padx=10, side=tk.LEFT)
    
    def _switch_view(self, view_name):
        """切换不同的视图"""
        # 更新按钮状态
        for btn in self.view_buttons:
            if btn["text"] == view_name:
                btn.config(state=tk.DISABLED)
            else:
                btn.config(state=tk.NORMAL)
        
        # 切换到相应视图
        if view_name == "概览":
            self._init_overview_view()
        elif view_name == "CPU监控":
            self._init_cpu_view()
        elif view_name == "内存监控":
            self._init_memory_view()
        elif view_name == "磁盘监控":
            self._init_disk_view()
        elif view_name == "应用分析":
            self._init_app_view()
    
    def _update_data_loop(self):
        """循环更新数据的后台线程"""
        data_count = 0
        
        while self.running:
            # 获取最新数据
            system_data = self.app.system_monitor.get_latest_system_data()
            app_data = self.app.system_monitor.get_running_applications()
            active_app = self.app.system_monitor.get_active_application()
            
            # 更新数据计数
            data_count += 1
            
            # 更新UI（需在主线程中执行）
            self.root.after(0, self._update_ui, system_data, app_data, active_app, data_count)
            
            # 每秒更新一次
            time.sleep(1)
    
    def _save_data_loop(self):
        """定期保存数据的后台线程"""
        while self.running:
            # 每30秒保存一次数据
            time.sleep(30)
            
            if self.app.db:
                try:
                    system_data = self.app.system_monitor.get_latest_system_data()
                    if system_data:
                        self.app.db.insert_system_data(system_data)
                        
                        # 记录日志
                        if self.app.log_manager:
                            logger = self.app.log_manager.get_logger("DataCollector")
                            logger.info("系统数据已保存")
                except Exception as e:
                    # 记录错误日志
                    if self.app.log_manager:
                        logger = self.app.log_manager.get_logger("DataCollector")
                        logger.error(f"保存系统数据失败: {str(e)}")
    
    def _update_ui(self, system_data, app_data, active_app, data_count):
        """更新用户界面显示"""
        # 更新时间显示
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_label.config(text=current_time)
        
        # 更新数据库状态
        if self.app.db and self.app.db.connection:
            self.db_status_label.config(text="数据存储: 已连接")
        else:
            self.db_status_label.config(text="数据存储: 未连接", foreground="red")
        
        # 更新数据计数
        self.data_count_label.config(text=f"已收集数据: {data_count}条")
        
        # 更新系统数据
        if system_data:
            # 更新CPU数据
            if system_data.cpu:
                cpu_usage = system_data.cpu.usage
                self.cpu_label.config(text=f"{cpu_usage:.1f}%")
                
                # 更新历史数据
                current_dt = datetime.datetime.fromtimestamp(system_data.timestamp)
                self._update_data_history('cpu', current_dt, cpu_usage)
                
                # 更新图表
                self.cpu_line.set_xdata(self.data_history['cpu']['times'])
                self.cpu_line.set_ydata(self.data_history['cpu']['values'])
                self.ax1.relim()
                self.ax1.autoscale_view()
                
                # 如果CPU视图已初始化，更新它
                if hasattr(self, 'cpu_chart_line'):
                    self.cpu_chart_line.set_xdata(self.data_history['cpu']['times'])
                    self.cpu_chart_line.set_ydata(self.data_history['cpu']['values'])
                    self.cpu_ax.relim()
                    self.cpu_ax.autoscale_view()
                    self.cpu_canvas.draw()
                
                # 更新CPU详细信息
                self.cpu_cores_label.config(text=str(system_data.cpu.cores))
                self.cpu_freq_label.config(text=f"{system_data.cpu.frequency:.1f} MHz")
            
            # 更新内存数据
            if system_data.memory:
                memory_usage = system_data.memory.usage
                self.memory_label.config(text=f"{memory_usage:.1f}%")
                
                # 更新历史数据
                current_dt = datetime.datetime.fromtimestamp(system_data.timestamp)
                self._update_data_history('memory', current_dt, memory_usage)
                
                # 更新图表
                self.memory_line.set_xdata(self.data_history['memory']['times'])
                self.memory_line.set_ydata(self.data_history['memory']['values'])
                self.ax2.relim()
                self.ax2.autoscale_view()
                
                # 如果内存视图已初始化，更新它
                if hasattr(self, 'memory_chart_line'):
                    self.memory_chart_line.set_xdata(self.data_history['memory']['times'])
                    self.memory_chart_line.set_ydata(self.data_history['memory']['values'])
                    self.memory_ax.relim()
                    self.memory_ax.autoscale_view()
                    self.memory_canvas.draw()
                
                # 更新内存详细信息
                self.total_memory_label.config(text=f"{system_data.memory.total:.2f} GB")
                self.used_memory_label.config(text=f"{system_data.memory.used:.2f} GB")
                self.available_memory_label.config(text=f"{system_data.memory.available:.2f} GB")
            
            # 更新磁盘数据
            if system_data.disk:
                # 计算总体磁盘使用率（取第一个分区）
                if system_data.disk.partitions:
                    disk_usage = system_data.disk.partitions[0].usage
                    self.disk_label.config(text=f"{disk_usage:.1f}%")
                
                # 更新磁盘分区表格
                if hasattr(self, 'disk_tree'):
                    # 清空现有数据
                    for item in self.disk_tree.get_children():
                        self.disk_tree.delete(item)
                    
                    # 添加新数据
                    for part in system_data.disk.partitions:
                        self.disk_tree.insert("", tk.END, values=(
                            part.device,
                            part.mountpoint,
                            part.fstype,
                            part.total,
                            part.used,
                            part.free,
                            part.usage
                        ))
                
                # 更新磁盘IO历史数据
                current_dt = datetime.datetime.fromtimestamp(system_data.timestamp)
                self._update_data_history('disk_io_read', current_dt, system_data.disk.io.read_bytes)
                self._update_data_history('disk_io_write', current_dt, system_data.disk.io.write_bytes)
                
                # 更新磁盘IO图表
                if hasattr(self, 'disk_read_line'):
                    self.disk_read_line.set_xdata(self.data_history['disk_io_read']['times'])
                    self.disk_read_line.set_ydata(self.data_history['disk_io_read']['values'])
                    self.disk_write_line.set_xdata(self.data_history['disk_io_write']['times'])
                    self.disk_write_line.set_ydata(self.data_history['disk_io_write']['values'])
                    self.disk_ax.relim()
                    self.disk_ax.autoscale_view()
                    self.disk_canvas.draw()
            
            # 刷新图表
            self.canvas.draw()
        
        # 更新应用数据
        if app_data:
            # 更新当前活跃应用
            if active_app:
                self.app_label.config(text=f"{active_app.name}\n{active_app.window_title}")
            
            # 更新应用表格
            if hasattr(self, 'app_tree'):
                # 清空现有数据
                for item in self.app_tree.get_children():
                    self.app_tree.delete(item)
                
                # 按活跃时间排序
                sorted_apps = sorted(app_data, key=lambda x: x.active_time, reverse=True)
                
                # 添加新数据
                for app in sorted_apps[:20]:  # 只显示前20个
                    self.app_tree.insert("", tk.END, values=(
                        app.pid,
                        app.name,
                        f"{app.cpu_usage:.1f}",
                        f"{app.memory_usage:.2f}",
                        f"{app.active_time:.1f}"
                    ))
    
    def _update_data_history(self, data_type, time, value):
        """更新历史数据，保持固定数量的历史记录"""
        if data_type in self.data_history:
            # 添加新数据
            self.data_history[data_type]['times'].append(time)
            self.data_history[data_type]['values'].append(value)
            
            # 如果超过限制，移除最旧的数据
            if len(self.data_history[data_type]['times']) > self.history_limit:
                self.data_history[data_type]['times'].pop(0)
                self.data_history[data_type]['values'].pop(0)
    
    def _open_settings(self):
        """打开系统设置窗口"""
        messagebox.showinfo("系统设置", "系统设置功能将在这里实现")
    
    def _open_log_viewer(self):
        """打开日志查看窗口"""
        LogViewerDialog(self.root, self.app.log_manager)
    
    def _export_data(self):
        """导出数据"""
        messagebox.showinfo("数据导出", "数据导出功能将在这里实现")
    
    def stop(self):
        """停止所有后台线程"""
        self.running = False
        if self.update_thread.is_alive():
            self.update_thread.join()
        if self.save_thread.is_alive():
            self.save_thread.join()

class LogViewerDialog:
    def __init__(self, parent, log_manager):
        """初始化日志查看器对话框"""
        self.parent = parent
        self.log_manager = log_manager
        
        # 创建顶层窗口
        self.top = tk.Toplevel(parent)
        self.top.title("系统日志查看器")
        self.top.geometry("1000x600")
        self.top.transient(parent)
        self.top.grab_set()
        
        # 创建界面组件
        self._create_widgets()
        
        # 加载最新日志
        self._load_recent_logs()
    
    def _create_widgets(self):
        """创建日志查看器组件"""
        # 搜索框架
        search_frame = ttk.Frame(self.top)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(search_frame, text="搜索:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var, width=50).pack(side=tk.LEFT, padx=5)
        
        ttk.Label(search_frame, text="级别:").pack(side=tk.LEFT, padx=5)
        self.level_var = tk.StringVar(value="所有")
        level_combo = ttk.Combobox(
            search_frame, 
            textvariable=self.level_var,
            values=["所有", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            state="readonly",
            width=10
        )
        level_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(search_frame, text="搜索", command=self._search_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="刷新", command=self._load_recent_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="导出", command=self._export_logs).pack(side=tk.RIGHT, padx=5)
        
        # 日志文本区域
        self.log_text = scrolledtext.ScrolledText(self.top, wrap=tk.WORD, font=("Consolas", 10))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.log_text.config(state=tk.DISABLED)
        
        # 状态栏
        status_frame = ttk.Frame(self.top)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.log_count_label = ttk.Label(status_frame, text="日志条目: 0")
        self.log_count_label.pack(side=tk.LEFT)
    
    def _load_recent_logs(self):
        """加载最近的日志"""
        if not self.log_manager:
            self._display_logs([{"timestamp": time.strftime("%Y-%m-%d %H:%M:%S"), "level": "ERROR", "message": "日志系统未初始化"}])
            return
        
        # 获取最近的1000条日志
        logs = self.log_manager.search_logs(limit=1000)
        self._display_logs(logs)
    
    def _search_logs(self):
        """搜索日志"""
        if not self.log_manager:
            return
        
        query = self.search_var.get()
        level_str = self.level_var.get()
        
        # 转换日志级别
        level = None
        if level_str != "所有":
            try:
                from logging.logger import LogLevel
                level = LogLevel[level_str]
            except:
                pass
        
        # 搜索日志
        logs = self.log_manager.search_logs(
            query=query if query else None,
            level=level,
            limit=1000
        )
        
        self._display_logs(logs)
    
    def _display_logs(self, logs):
        """在文本区域显示日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        
        # 按时间倒序显示（最新的在前）
        for log in reversed(logs):
            timestamp = log.get("timestamp", "未知时间")
            level = log.get("level", "未知级别")
            module = log.get("module", "未知模块")
            message = log.get("message", "")
            
            # 根据日志级别设置颜色
            color = "black"
            if level == "WARNING":
                color = "#FFA500"  # 橙色
            elif level == "ERROR" or level == "CRITICAL":
                color = "red"
            
            # 格式化日志行
            log_line = f"[{timestamp}] [{level}] [{module}] {message}\n"
            
            # 添加到文本区域
            self.log_text.insert(tk.END, log_line)
            
            # 设置颜色
            start_pos = self.log_text.index(f"end-{len(log_line)+1}c")
            end_pos = self.log_text.index("end-1c")
            self.log_text.tag_add(level, start_pos, end_pos)
            self.log_text.tag_config(level, foreground=color)
        
        self.log_text.config(state=tk.DISABLED)
        self.log_count_label.config(text=f"日志条目: {len(logs)}")
    
    def _export_logs(self):
        """导出日志"""
        if not self.log_manager:
            messagebox.showerror("错误", "日志系统未初始化")
            return
        
        from tkinter import filedialog
        import os
        
        # 获取保存路径
        default_filename = f"logs_export_{time.strftime('%Y%m%d_%H%M%S')}.json"
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
            initialfile=default_filename
        )
        
        if not file_path:
            return
        
        # 导出日志
        query = self.search_var.get()
        level_str = self.level_var.get()
        
        # 转换日志级别
        level = None
        if level_str != "所有":
            try:
                from logging.logger import LogLevel
                level = LogLevel[level_str]
            except:
                pass
        
        success = self.log_manager.export_logs(
            file_path,
            query=query if query else None,
            level=level
        )
        
        if success:
            messagebox.showinfo("成功", f"日志已导出到:\n{file_path}")
        else:
            messagebox.showerror("错误", "导出日志失败")
