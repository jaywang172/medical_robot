"""
機器人系統事件定義
所有事件都繼承自RobotEvent基類
"""

import time
from abc import ABC
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from enum import Enum


class EventType(Enum):
    """事件類型枚舉"""
    MOTOR_STATUS = "motor_status"
    SENSOR_DATA = "sensor_data"
    NAVIGATION = "navigation"
    VISION = "vision"
    SYSTEM_STATE = "system_state"
    EMERGENCY = "emergency"


@dataclass
class RobotEvent(ABC):
    """機器人事件基類"""
    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    source: str = "unknown"
    data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """事件創建後的處理"""
        if not hasattr(self, 'event_id'):
            self.event_id = f"{self.event_type.value}_{int(self.timestamp * 1000)}"


@dataclass
class MotorStatusEvent(RobotEvent):
    """電機狀態事件"""
    event_type: EventType = field(default=EventType.MOTOR_STATUS, init=False)
    
    # 電機狀態數據
    left_motor_speed: float = 0.0
    right_motor_speed: float = 0.0
    left_motor_position: float = 0.0
    right_motor_position: float = 0.0
    is_moving: bool = False
    emergency_stop: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'left_motor_speed': self.left_motor_speed,
            'right_motor_speed': self.right_motor_speed,
            'left_motor_position': self.left_motor_position,
            'right_motor_position': self.right_motor_position,
            'is_moving': self.is_moving,
            'emergency_stop': self.emergency_stop
        })


@dataclass
class SensorDataEvent(RobotEvent):
    """感測器數據事件"""
    event_type: EventType = field(default=EventType.SENSOR_DATA, init=False)
    
    # 感測器數據
    ultrasonic_distances: Dict[str, float] = field(default_factory=dict)
    imu_data: Optional[Dict[str, float]] = None
    battery_voltage: float = 0.0
    temperature: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'ultrasonic_distances': self.ultrasonic_distances,
            'imu_data': self.imu_data,
            'battery_voltage': self.battery_voltage,
            'temperature': self.temperature
        })


@dataclass
class NavigationEvent(RobotEvent):
    """導航事件"""
    event_type: EventType = field(default=EventType.NAVIGATION, init=False)
    
    # 導航數據
    current_position: Optional[Dict[str, float]] = None
    target_position: Optional[Dict[str, float]] = None
    navigation_state: str = "idle"
    path_progress: float = 0.0
    obstacles_detected: int = 0
    
    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'current_position': self.current_position,
            'target_position': self.target_position,
            'navigation_state': self.navigation_state,
            'path_progress': self.path_progress,
            'obstacles_detected': self.obstacles_detected
        })


@dataclass
class VisionEvent(RobotEvent):
    """視覺系統事件"""
    event_type: EventType = field(default=EventType.VISION, init=False)
    
    # 視覺數據
    objects_detected: int = 0
    obstacles: list = field(default_factory=list)
    confidence_scores: list = field(default_factory=list)
    processing_time: float = 0.0
    
    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'objects_detected': self.objects_detected,
            'obstacles': self.obstacles,
            'confidence_scores': self.confidence_scores,
            'processing_time': self.processing_time
        })


@dataclass 
class SystemStateEvent(RobotEvent):
    """系統狀態事件"""
    event_type: EventType = field(default=EventType.SYSTEM_STATE, init=False)
    
    # 系統狀態
    old_state: str = "unknown"
    new_state: str = "unknown"
    reason: str = ""
    
    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'old_state': self.old_state,
            'new_state': self.new_state,
            'reason': self.reason
        })


@dataclass
class EmergencyEvent(RobotEvent):
    """緊急事件"""
    event_type: EventType = field(default=EventType.EMERGENCY, init=False)
    
    # 緊急情況數據
    emergency_type: str = "unknown"
    severity: str = "medium"  # low, medium, high, critical
    description: str = ""
    auto_recovery: bool = False
    
    def __post_init__(self):
        super().__post_init__()
        self.data.update({
            'emergency_type': self.emergency_type,
            'severity': self.severity,
            'description': self.description,
            'auto_recovery': self.auto_recovery
        })


# 事件工廠函數，方便創建事件
def create_motor_status_event(source: str, **kwargs) -> MotorStatusEvent:
    """創建電機狀態事件"""
    return MotorStatusEvent(source=source, **kwargs)


def create_sensor_data_event(source: str, **kwargs) -> SensorDataEvent:
    """創建感測器數據事件"""
    return SensorDataEvent(source=source, **kwargs)


def create_navigation_event(source: str, **kwargs) -> NavigationEvent:
    """創建導航事件"""
    return NavigationEvent(source=source, **kwargs)


def create_vision_event(source: str, **kwargs) -> VisionEvent:
    """創建視覺事件"""
    return VisionEvent(source=source, **kwargs)


def create_system_state_event(source: str, **kwargs) -> SystemStateEvent:
    """創建系統狀態事件"""
    return SystemStateEvent(source=source, **kwargs)


def create_emergency_event(source: str, **kwargs) -> EmergencyEvent:
    """創建緊急事件"""
    return EmergencyEvent(source=source, **kwargs)