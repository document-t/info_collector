import tkinter as tk
from tkinter import messagebox
import sys
import os
from collectors.system_monitor import SystemMonitor
from storage.key_manager import KeyManager
from storage.encryptor import DataEncryptor
from storage.local_database import LocalDatabase
from log.log_manager import LogManager
from ui.dashboard import Dashboard
from ui.login_dialog import LoginDialog

class Application:
    def __init__(self):
        """初始化应用程序"""
        self.root = tk.Tk()
        self.root.withdraw()  # 先隐藏主窗口，等待登录
        
        self.key_manager = KeyManager()
        self.encryptor = None
        self.db = None
        self.log_manager = None
        self.system_monitor = None
        self.dashboard = None
        
        # 检查是否有加密密钥
        self._setup_encryption()
        
        # 设置数据库
        self._setup_database()
        
        # 设置日志系统
        self._setup_logging()
        
        # 初始化系统监控器
        self.system_monitor = SystemMonitor()
        
        # 记录系统启动事件
        if self.log_manager:
            logger = self.log_manager.get_logger("Application")
            logger.info("系统启动")
        
        # 显示主界面
        self._show_main_ui()
        
    def _setup_encryption(self):
        """设置加密系统"""
        try:
            # 检查是否已有密钥
            if self.key_manager.has_key():
                # 显示登录对话框获取密码
                login_dialog = LoginDialog(self.root, "解锁数据")
                self.root.wait_window(login_dialog.top)
                
                if not login_dialog.success:
                    messagebox.showerror("错误", "密码验证失败，程序将退出")
                    sys.exit(1)
                
                # 使用密码加载密钥
                key = self.key_manager.load_key(login_dialog.password)
                self.encryptor = DataEncryptor(key)
            else:
                # 创建新密钥
                messagebox.showinfo("首次运行", "检测到首次运行，将创建新的加密密钥")
                
                # 让用户设置密码
                login_dialog = LoginDialog(self.root, "设置密码", is_new=True)
                self.root.wait_window(login_dialog.top)
                
                if not login_dialog.success:
                    messagebox.showerror("错误", "密码设置失败，程序将退出")
                    sys.exit(1)
                
                # 创建并保存密钥
                key = self.key_manager.create_and_save_key(login_dialog.password)
                self.encryptor = DataEncryptor(key)
                
                messagebox.showinfo("成功", "加密密钥创建成功，程序将继续运行")
        except Exception as e:
            messagebox.showerror("加密设置失败", f"无法设置加密系统: {str(e)}")
            sys.exit(1)
    
    def _setup_database(self):
        """设置数据库"""
        try:
            self.db = LocalDatabase(encryptor=self.encryptor)
            
            # 清理30天前的旧数据
            deleted = self.db.cleanup_old_data(30)
            if deleted > 0 and self.log_manager:
                logger = self.log_manager.get_logger("Database")
                logger.info(f"清理了 {deleted} 条旧数据")
        except Exception as e:
            messagebox.showerror("数据库设置失败", f"无法初始化数据库: {str(e)}")
            sys.exit(1)
    
    def _setup_logging(self):
        """设置日志系统"""
        try:
            self.log_manager = LogManager(encryptor=self.encryptor)
        except Exception as e:
            messagebox.showerror("日志系统设置失败", f"无法初始化日志系统: {str(e)}")
            # 日志系统失败不退出程序，但记录到控制台
            print(f"日志系统初始化失败: {str(e)}")
    
    def _show_main_ui(self):
        """显示主界面"""
        self.root.deiconify()  # 显示主窗口
        self.dashboard = Dashboard(self.root, self)
        
        # 开始监控
        self.system_monitor.start_monitoring()
        
        # 设置窗口关闭事件处理
        self.root.protocol("WM_DELETE_WINDOW", self._on_exit)
    
    def _on_exit(self):
        """处理程序退出"""
        if messagebox.askyesno("退出", "确定要退出系统吗？"):
            # 停止监控
            if self.system_monitor:
                self.system_monitor.stop_monitoring()
            
            # 记录系统关闭事件
            if self.log_manager:
                logger = self.log_manager.get_logger("Application")
                logger.info("系统关闭")
            
            # 关闭数据库连接
            if self.db:
                self.db.close()
            
            self.root.destroy()
    
    def run(self):
        """运行应用程序主循环"""
        self.root.mainloop()

if __name__ == "__main__":
    # 确保中文显示正常
    app = Application()
    app.run()
