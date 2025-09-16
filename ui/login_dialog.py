import tkinter as tk
from tkinter import ttk, messagebox

class LoginDialog:
    def __init__(self, parent, title, is_new=False):
        """初始化登录对话框
        
        Args:
            parent: 父窗口
            title: 对话框标题
            is_new: 是否是新用户设置密码
        """
        self.parent = parent
        self.is_new = is_new
        self.success = False
        self.password = ""
        
        # 创建顶层窗口
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.geometry("300x200")
        self.top.resizable(False, False)
        self.top.transient(parent)  # 设置为主窗口的子窗口
        self.top.grab_set()  # 模态窗口，阻止操作其他窗口
        
        # 居中显示
        self.top.update_idletasks()
        width = self.top.winfo_width()
        height = self.top.winfo_height()
        x = (parent.winfo_width() // 2) - (width // 2) + parent.winfo_x()
        y = (parent.winfo_height() // 2) - (height // 2) + parent.winfo_y()
        self.top.geometry(f"+{x}+{y}")
        
        # 创建界面组件
        self._create_widgets()
        
        # 绑定回车键登录
        self.top.bind('<Return>', lambda event: self._on_ok())
    
    def _create_widgets(self):
        """创建对话框组件"""
        # 主框架
        main_frame = ttk.Frame(self.top, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_text = "设置密码以保护您的数据" if self.is_new else "请输入密码解锁数据"
        ttk.Label(
            main_frame, 
            text=title_text, 
            font=("Arial", 10)
        ).pack(pady=(0, 15), anchor=tk.W)
        
        # 密码框
        ttk.Label(main_frame, text="密码:").pack(anchor=tk.W)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            main_frame, 
            textvariable=self.password_var, 
            show="*",
            width=30
        )
        self.password_entry.pack(pady=(5, 10), fill=tk.X)
        self.password_entry.focus()
        
        # 确认密码框（仅新用户需要）
        if self.is_new:
            ttk.Label(main_frame, text="确认密码:").pack(anchor=tk.W)
            self.confirm_var = tk.StringVar()
            self.confirm_entry = ttk.Entry(
                main_frame, 
                textvariable=self.confirm_var, 
                show="*",
                width=30
            )
            self.confirm_entry.pack(pady=(5, 10), fill=tk.X)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=15, fill=tk.X)
        
        ttk.Button(
            button_frame, 
            text="确定", 
            command=self._on_ok
        ).pack(side=tk.RIGHT, padx=(5, 0))
        
        ttk.Button(
            button_frame, 
            text="取消", 
            command=self._on_cancel
        ).pack(side=tk.RIGHT)
    
    def _validate_password(self) -> bool:
        """验证密码
        
        Returns:
            如果密码有效则为True，否则为False
        """
        password = self.password_var.get()
        
        # 检查密码不为空
        if not password:
            messagebox.showerror("错误", "密码不能为空")
            return False
            
        # 新用户需要验证两次输入一致
        if self.is_new:
            confirm = self.confirm_var.get()
            if password != confirm:
                messagebox.showerror("错误", "两次输入的密码不一致")
                return False
                
            # 检查密码强度
            if len(password) < 6:
                messagebox.showerror("错误", "密码长度至少为6位")
                return False
        
        return True
    
    def _on_ok(self):
        """处理确定按钮点击"""
        if self._validate_password():
            self.password = self.password_var.get()
            self.success = True
            self.top.destroy()
    
    def _on_cancel(self):
        """处理取消按钮点击"""
        self.success = False
        self.top.destroy()
