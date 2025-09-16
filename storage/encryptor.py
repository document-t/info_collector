import os
import json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64
import hashlib

class DataEncryptor:
    def __init__(self, key: str):
        """初始化加密器
        
        Args:
            key: 加密密钥（将被处理为256位密钥）
        """
        # 使用SHA-256处理密钥，确保得到32字节（256位）的密钥
        self.key = hashlib.sha256(key.encode()).digest()
        self.backend = default_backend()
        self.block_size = algorithms.AES.block_size  # 128位块大小
    
    def encrypt(self, data: dict) -> str:
        """加密数据
        
        Args:
            data: 要加密的字典数据
            
        Returns:
            加密后的字符串
        """
        try:
            # 将字典转换为JSON字符串
            data_str = json.dumps(data)
            data_bytes = data_str.encode('utf-8')
            
            # 生成随机的16字节IV（初始化向量）
            iv = os.urandom(self.block_size // 8)
            
            # 对数据进行填充，使其长度为块大小的倍数
            padder = padding.PKCS7(self.block_size).padder()
            padded_data = padder.update(data_bytes) + padder.finalize()
            
            # 创建AES加密器（CBC模式）
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
            encryptor = cipher.encryptor()
            
            # 加密数据
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # 将IV和加密数据组合，然后进行Base64编码
            combined = iv + encrypted_data
            return base64.b64encode(combined).decode('utf-8')
            
        except Exception as e:
            print(f"加密失败: {str(e)}")
            raise
    
    def decrypt(self, encrypted_str: str) -> dict:
        """解密数据
        
        Args:
            encrypted_str: 加密后的字符串
            
        Returns:
            解密后的字典数据
        """
        try:
            # 解码Base64字符串
            combined = base64.b64decode(encrypted_str.encode('utf-8'))
            
            # 分离IV和加密数据
            iv_length = self.block_size // 8
            iv = combined[:iv_length]
            encrypted_data = combined[iv_length:]
            
            # 创建AES解密器（CBC模式）
            cipher = Cipher(algorithms.AES(self.key), modes.CBC(iv), backend=self.backend)
            decryptor = cipher.decryptor()
            
            # 解密数据
            padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # 移除填充
            unpadder = padding.PKCS7(self.block_size).unpadder()
            data_bytes = unpadder.update(padded_data) + unpadder.finalize()
            
            # 将JSON字符串转换为字典
            return json.loads(data_bytes.decode('utf-8'))
            
        except Exception as e:
            print(f"解密失败: {str(e)}")
            raise
    
    @staticmethod
    def generate_key() -> str:
        """生成随机密钥
        
        Returns:
            随机生成的密钥字符串
        """
        return base64.b64encode(os.urandom(32)).decode('utf-8')
