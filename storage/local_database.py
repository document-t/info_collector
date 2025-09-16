import sqlite3
import os
import time
from pathlib import Path
from dataclasses import asdict
from typing import List, Dict, Any, Optional
from storage.encryptor import DataEncryptor

class LocalDatabase:
    def __init__(self, db_name: str = "system_monitor.db", encryptor: DataEncryptor = None):
        """初始化本地数据库
        
        Args:
            db_name: 数据库文件名
            encryptor: 数据加密器，为None则不加密
        """
        self.encryptor = encryptor
        self.db_path = self._get_db_path(db_name)
        self.connection = None
        self._initialize_db()
    
    def _get_db_path(self, db_name: str) -> Path:
        """获取数据库文件的存储路径"""
        # 在不同系统上使用适当的应用数据目录
        if os.name == 'nt':  # Windows
            appdata = Path(os.environ.get("APPDATA", ""))
            app_dir = appdata / "LocalInfoCollector"
        else:  # Unix-like systems
            home = Path.home()
            app_dir = home / ".local_info_collector"
        
        # 确保目录存在
        app_dir.mkdir(parents=True, exist_ok=True)
        return app_dir / db_name
    
    def _initialize_db(self):
        """初始化数据库表结构"""
        self.connection = sqlite3.connect(str(self.db_path))
        cursor = self.connection.cursor()
        
        # 创建系统数据记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            cpu_data TEXT,
            memory_data TEXT,
            disk_data TEXT
        )
        ''')
        
        # 创建应用数据记录表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            pid INTEGER NOT NULL,
            name TEXT NOT NULL,
            executable TEXT,
            window_title TEXT,
            start_time REAL,
            active_time REAL,
            cpu_usage REAL,
            memory_usage REAL
        )
        ''')
        
        # 创建应用事件表（启动、关闭等）
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            pid INTEGER NOT NULL,
            name TEXT NOT NULL,
            event_type TEXT NOT NULL,  -- "start", "close", "focus", "blur"
            details TEXT
        )
        ''')
        
        # 创建系统事件表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS system_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL NOT NULL,
            event_type TEXT NOT NULL,
            details TEXT
        )
        ''')
        
        self.connection.commit()
    
    def _encrypt_data(self, data: Dict[str, Any]) -> str:
        """加密数据（如果加密器已配置）"""
        if self.encryptor:
            return self.encryptor.encrypt(data)
        return str(data)
    
    def _decrypt_data(self, encrypted_data: str) -> Dict[str, Any]:
        """解密数据（如果加密器已配置）"""
        if self.encryptor and encrypted_data:
            return self.encryptor.decrypt(encrypted_data)
        try:
            # 尝试将字符串转换回字典（未加密的情况）
            import ast
            return ast.literal_eval(encrypted_data)
        except:
            return {"raw_data": encrypted_data}
    
    def insert_system_data(self, system_data) -> int:
        """插入系统数据记录
        
        Args:
            system_data: SystemData对象
            
        Returns:
            插入记录的ID
        """
        if not self.connection:
            self._initialize_db()
            
        cursor = self.connection.cursor()
        
        # 转换数据为字典并加密
        cpu_data = self._encrypt_data(asdict(system_data.cpu)) if system_data.cpu else None
        memory_data = self._encrypt_data(asdict(system_data.memory)) if system_data.memory else None
        disk_data = self._encrypt_data(asdict(system_data.disk)) if system_data.disk else None
        
        cursor.execute('''
        INSERT INTO system_data (timestamp, cpu_data, memory_data, disk_data)
        VALUES (?, ?, ?, ?)
        ''', (system_data.timestamp, cpu_data, memory_data, disk_data))
        
        self.connection.commit()
        return cursor.lastrowid
    
    def insert_app_data(self, app_info) -> int:
        """插入应用数据记录
        
        Args:
            app_info: AppInfo对象
            
        Returns:
            插入记录的ID
        """
        if not self.connection:
            self._initialize_db()
            
        cursor = self.connection.cursor()
        
        cursor.execute('''
        INSERT INTO app_data 
        (timestamp, pid, name, executable, window_title, start_time, active_time, cpu_usage, memory_usage)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            time.time(),
            app_info.pid,
            app_info.name,
            app_info.executable,
            app_info.window_title,
            app_info.start_time,
            app_info.active_time,
            app_info.cpu_usage,
            app_info.memory_usage
        ))
        
        self.connection.commit()
        return cursor.lastrowid
    
    def log_app_event(self, pid: int, name: str, event_type: str, details: str = "") -> int:
        """记录应用事件
        
        Args:
            pid: 进程ID
            name: 应用名称
            event_type: 事件类型
            details: 事件详情
            
        Returns:
            插入记录的ID
        """
        if not self.connection:
            self._initialize_db()
            
        cursor = self.connection.cursor()
        
        cursor.execute('''
        INSERT INTO app_events (timestamp, pid, name, event_type, details)
        VALUES (?, ?, ?, ?, ?)
        ''', (time.time(), pid, name, event_type, details))
        
        self.connection.commit()
        return cursor.lastrowid
    
    def log_system_event(self, event_type: str, details: str = "") -> int:
        """记录系统事件
        
        Args:
            event_type: 事件类型
            details: 事件详情
            
        Returns:
            插入记录的ID
        """
        if not self.connection:
            self._initialize_db()
            
        cursor = self.connection.cursor()
        
        cursor.execute('''
        INSERT INTO system_events (timestamp, event_type, details)
        VALUES (?, ?, ?)
        ''', (time.time(), event_type, details))
        
        self.connection.commit()
        return cursor.lastrowid
    
    def get_recent_system_data(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的系统数据
        
        Args:
            limit: 要获取的记录数量
            
        Returns:
            系统数据记录列表
        """
        if not self.connection:
            self._initialize_db()
            
        cursor = self.connection.cursor()
        
        cursor.execute('''
        SELECT * FROM system_data
        ORDER BY timestamp DESC
        LIMIT ?
        ''', (limit,))
        
        columns = [desc[0] for desc in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            
            # 解密数据
            if record['cpu_data']:
                record['cpu_data'] = self._decrypt_data(record['cpu_data'])
            if record['memory_data']:
                record['memory_data'] = self._decrypt_data(record['memory_data'])
            if record['disk_data']:
                record['disk_data'] = self._decrypt_data(record['disk_data'])
                
            results.append(record)
        
        # 按时间升序返回
        return sorted(results, key=lambda x: x['timestamp'])
    
    def get_app_events(self, pid: int = None, start_time: float = None, end_time: float = None) -> List[Dict[str, Any]]:
        """获取应用事件记录
        
        Args:
            pid: 可选的进程ID筛选
            start_time: 可选的开始时间筛选
            end_time: 可选的结束时间筛选
            
        Returns:
            应用事件记录列表
        """
        if not self.connection:
            self._initialize_db()
            
        cursor = self.connection.cursor()
        query = "SELECT * FROM app_events WHERE 1=1"
        params = []
        
        if pid is not None:
            query += " AND pid = ?"
            params.append(pid)
        if start_time is not None:
            query += " AND timestamp >= ?"
            params.append(start_time)
        if end_time is not None:
            query += " AND timestamp <= ?"
            params.append(end_time)
            
        query += " ORDER BY timestamp ASC"
        
        cursor.execute(query, params)
        
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> int:
        """清理旧数据
        
        Args:
            days_to_keep: 保留最近多少天的数据
            
        Returns:
            删除的记录总数
        """
        if not self.connection:
            self._initialize_db()
            
        cutoff_time = time.time() - (days_to_keep * 24 * 60 * 60)
        total_deleted = 0
        cursor = self.connection.cursor()
        
        # 删除系统数据
        cursor.execute("DELETE FROM system_data WHERE timestamp < ?", (cutoff_time,))
        total_deleted += cursor.rowcount
        
        # 删除应用数据
        cursor.execute("DELETE FROM app_data WHERE timestamp < ?", (cutoff_time,))
        total_deleted += cursor.rowcount
        
        # 保留所有事件记录，不删除
        
        self.connection.commit()
        return total_deleted
    
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def __del__(self):
        """对象销毁时关闭数据库连接"""
        self.close()
