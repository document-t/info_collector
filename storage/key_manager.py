import os
import json
import getpass
from pathlib import Path
import ctypes
import platform

class KeyManager:
    def __init__(self):
        """初始化密钥管理器"""
        self.system = platform.system()
        self.key_file = self._get_key_file_path()
        self.encrypted_key = None
    
    def _get_key_file_path(self) -> Path:
        """获取密钥文件的存储路径"""
        if self.system == "Windows":
            # 在Windows上使用AppData目录
            appdata = Path(os.environ.get("APPDATA", ""))
            app_dir = appdata / "LocalInfoCollector"
        else:
            # 其他系统使用用户主目录下的隐藏文件夹
            home = Path.home()
            app_dir = home / ".local_info_collector"
        
        # 确保目录存在
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / "encryption_key"
    
    def _protect_key(self, key: bytes) -> bytes:
        """使用系统功能保护密钥（Windows专用）"""
        if self.system != "Windows":
            return key
            
        try:
            # 使用Windows的CryptProtectData保护密钥
            import ctypes.wintypes
            
            data_in = key
            data_out = ctypes.create_string_buffer(1024)
            data_out_size = ctypes.wintypes.DWORD(len(data_out))
            
            result = ctypes.windll.crypt32.CryptProtectData(
                ctypes.byref(ctypes.wintypes.DATA_BLOB(len(data_in), ctypes.c_char_p(data_in))),
                None,
                None,
                None,
                None,
                0,
                ctypes.byref(ctypes.wintypes.DATA_BLOB(data_out_size, data_out))
            )
            
            if not result:
                raise Exception("无法加密保护密钥")
                
            return data_out.raw[:data_out_size.value]
        except:
            return key
    
    def _unprotect_key(self, protected_key: bytes) -> bytes:
        """使用系统功能解密受保护的密钥（Windows专用）"""
        if self.system != "Windows":
            return protected_key
            
        try:
            # 使用Windows的CryptUnprotectData解密密钥
            import ctypes.wintypes
            
            data_in = protected_key
            data_out = ctypes.create_string_buffer(1024)
            data_out_size = ctypes.wintypes.DWORD(len(data_out))
            
            result = ctypes.windll.crypt32.CryptUnprotectData(
                ctypes.byref(ctypes.wintypes.DATA_BLOB(len(data_in), ctypes.c_char_p(data_in))),
                None,
                None,
                None,
                None,
                0,
                ctypes.byref(ctypes.wintypes.DATA_BLOB(data_out_size, data_out))
            )
            
            if not result:
                raise Exception("无法解密保护的密钥")
                
            return data_out.raw[:data_out_size.value]
        except:
            return protected_key
    
    def has_key(self) -> bool:
        """检查是否已存在密钥"""
        return self.key_file.exists()
    
    def create_and_save_key(self, password: str = None) -> str:
        """创建并保存新的加密密钥
        
        Args:
            password: 可选密码，用于额外保护密钥
            
        Returns:
            生成的密钥
        """
        from storage.encryptor import DataEncryptor
        
        # 生成新密钥
        key = DataEncryptor.generate_key()
        
        # 保护密钥
        protected_key = self._protect_key(key.encode('utf-8'))
        
        # 如果提供了密码，使用密码再次加密
        if password:
            password_encryptor = DataEncryptor(password)
            protected_key = password_encryptor.encrypt({
                'data': protected_key.hex()
            }).encode('utf-8')
        
        # 保存密钥
        with open(self.key_file, 'wb') as f:
            f.write(protected_key)
        
        self.encrypted_key = key
        return key
    
    def load_key(self, password: str = None) -> str:
        """加载已保存的密钥
        
        Args:
            password: 如果密钥用密码保护，需要提供密码
            
        Returns:
            加载的密钥
        """
        if not self.has_key():
            raise FileNotFoundError("未找到加密密钥")
        
        # 读取受保护的密钥
        with open(self.key_file, 'rb') as f:
            protected_key = f.read()
        
        # 如果提供了密码，先使用密码解密
        if password:
            try:
                password_encryptor = DataEncryptor(password)
                decrypted = password_encryptor.decrypt(protected_key.decode('utf-8'))
                protected_key = bytes.fromhex(decrypted['data'])
            except:
                raise ValueError("密码不正确或密钥已损坏")
        
        # 解除系统保护
        key_bytes = self._unprotect_key(protected_key)
        key = key_bytes.decode('utf-8')
        
        self.encrypted_key = key
        return key
    
    def delete_key(self) -> bool:
        """删除已保存的密钥
        
        Returns:
            如果删除成功则为True，否则为False
        """
        if self.has_key():
            try:
                os.remove(self.key_file)
                self.encrypted_key = None
                return True
            except:
                return False
        return True
