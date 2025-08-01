#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
機器人系統配置文件
包含所有硬體、AI模型、網路等配置參數
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from pathlib import Path


@dataclass
class MotorConfig:
    """電機控制配置"""
    # PWM腳位配置
    left_motor_pins: Tuple[int, int] = (18, 19)  # (速度, 方向)
    right_motor_pins: Tuple[int, int] = (20, 21)
    
    # 電機參數
    max_speed: float = 100.0  # 最大速度 (%)
    min_speed: float = 20.0   # 最小啟動速度
    acceleration: float = 5.0  # 加速度
    pwm_frequency: int = 1000  # PWM頻率
    
    # 編碼器配置 (如果有)
    encoder_enabled: bool = False
    encoder_pins: Tuple[int, int] = (22, 23)
    pulses_per_revolution: int = 360


@dataclass
class SensorConfig:
    """感測器配置"""
    # 超聲波感測器
    ultrasonic_enabled: bool = True
    ultrasonic_pins: Dict[str, Tuple[int, int]] = field(default_factory=lambda: {
        'front': (24, 25),  # (trig, echo)
        'left': (26, 27),
        'right': (28, 29),
        'back': (30, 31)
    })
    
    # 陀螺儀/加速度計
    imu_enabled: bool = True
    imu_i2c_address: int = 0x68
    
    # GPS模組
    gps_enabled: bool = False
    gps_serial_port: str = "/dev/ttyUSB0"
    gps_baud_rate: int = 9600
    
    # 感測器讀取頻率
    sensor_update_rate: float = 10.0  # Hz


@dataclass
class VisionConfig:
    """視覺系統配置"""
    # 相機設置
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    camera_fps: int = 30
    
    # YOLO模型配置
    yolo_model_path: str = "models/yolov8n.pt"
    confidence_threshold: float = 0.5
    iou_threshold: float = 0.45
    
    # 檢測類別 (COCO數據集)
    target_classes: List[str] = field(default_factory=lambda: [
        'person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck',
        'traffic light', 'stop sign', 'chair', 'potted plant'
    ])
    
    # 視覺處理參數
    frame_skip: int = 1  # 每隔幾幀處理一次
    max_detection_distance: float = 5.0  # 最大檢測距離(米)


@dataclass
class NavigationConfig:
    """導航配置"""
    # 路徑規劃參數
    grid_size: float = 0.1  # 網格大小(米)
    planning_range: float = 10.0  # 規劃範圍(米)
    obstacle_inflation: float = 0.3  # 障礙物膨脹半徑(米)
    
    # 安全距離
    min_obstacle_distance: float = 0.5  # 最小安全距離(米)
    emergency_stop_distance: float = 0.2  # 緊急停止距離(米)
    
    # 移動參數
    max_linear_speed: float = 0.5  # 最大線速度(m/s)
    max_angular_speed: float = 1.0  # 最大角速度(rad/s)
    goal_tolerance: float = 0.1  # 目標容許誤差(米)
    
    # A*算法參數
    heuristic_weight: float = 1.0
    max_iterations: int = 1000


@dataclass
class ApiConfig:
    """API服務配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    
    # CORS設置
    cors_origins: List[str] = field(default_factory=lambda: [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://192.168.1.*"
    ])
    
    # WebSocket設置
    websocket_heartbeat: int = 30  # 心跳間隔(秒)
    max_connections: int = 10
    
    # 文件上傳
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    upload_dir: str = "uploads"


@dataclass
class DatabaseConfig:
    """資料庫配置"""
    database_url: str = "sqlite:///robot_data.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


class RobotConfig:
    """機器人主配置類"""
    
    def __init__(self):
        # 環境變數
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        
        # 項目路徑
        self.project_root = Path(__file__).parent.parent
        self.models_dir = self.project_root / "models"
        self.logs_dir = self.project_root / "logs"
        self.data_dir = self.project_root / "data"
        
        # 確保目錄存在
        self.models_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        
        # 各模組配置
        self.motor_config = MotorConfig()
        self.sensor_config = SensorConfig()
        self.vision_config = VisionConfig()
        self.navigation_config = NavigationConfig()
        self.api_config = ApiConfig()
        self.database_config = DatabaseConfig()
        
        # 系統參數
        self.main_loop_interval = 0.05  # 主循環間隔(秒) - 20Hz
        self.is_simulation = os.getenv("SIMULATION", "false").lower() == "true"
        
        # 如果是模擬模式，調整某些設置
        if self.is_simulation:
            self.sensor_config.ultrasonic_enabled = False
            self.sensor_config.imu_enabled = False
            self.sensor_config.gps_enabled = False
    
    def get_model_path(self, model_name: str) -> Path:
        """獲取模型文件路徑"""
        return self.models_dir / model_name
    
    def get_log_path(self, log_name: str) -> Path:
        """獲取日誌文件路徑"""
        return self.logs_dir / log_name
    
    def to_dict(self) -> Dict:
        """轉換為字典格式，用於API返回"""
        return {
            "debug": self.debug,
            "simulation": self.is_simulation,
            "motor": {
                "max_speed": self.motor_config.max_speed,
                "acceleration": self.motor_config.acceleration
            },
            "vision": {
                "camera_resolution": f"{self.vision_config.camera_width}x{self.vision_config.camera_height}",
                "confidence_threshold": self.vision_config.confidence_threshold
            },
            "navigation": {
                "max_speed": self.navigation_config.max_linear_speed,
                "safety_distance": self.navigation_config.min_obstacle_distance
            }
        } 