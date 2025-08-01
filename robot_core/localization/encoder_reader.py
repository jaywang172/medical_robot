"""
編碼器數據讀取模組
處理輪式編碼器的脈衝計數和速度計算
"""

import asyncio
import time
import threading
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

try:
    import RPi.GPIO as GPIO
except ImportError:
    # 在非樹莓派環境下的模擬實現
    class MockGPIO:
        BCM = "BCM"
        IN = "IN"
        PUD_UP = "PUD_UP"
        RISING = "RISING"
        FALLING = "FALLING"
        
        @staticmethod
        def setmode(mode): pass
        @staticmethod
        def setup(pin, mode, pull_up_down=None): pass
        @staticmethod
        def add_event_detect(pin, edge, callback=None, bouncetime=None): pass
        @staticmethod
        def cleanup(): pass
    
    GPIO = MockGPIO()


@dataclass
class EncoderConfig:
    """編碼器配置"""
    # 左輪編碼器引腳
    left_encoder_pin_a: int = 18
    left_encoder_pin_b: int = 19
    
    # 右輪編碼器引腳  
    right_encoder_pin_a: int = 20
    right_encoder_pin_b: int = 21
    
    # 編碼器參數
    pulses_per_revolution: int = 1000  # 每轉脈衝數
    wheel_radius: float = 0.05         # 輪子半徑(米)
    wheel_base: float = 0.2            # 軸距(米)
    
    # 去抖動時間
    debounce_time: int = 1  # 毫秒


@dataclass
class EncoderData:
    """編碼器數據"""
    left_pulses: int = 0
    right_pulses: int = 0
    left_velocity: float = 0.0  # 米/秒
    right_velocity: float = 0.0  # 米/秒
    timestamp: float = 0.0


class EncoderReader:
    """
    編碼器讀取器
    
    功能：
    - 讀取左右輪編碼器脈衝
    - 計算輪子速度
    - 提供增量式里程計數據
    """
    
    def __init__(self, config: EncoderConfig):
        self.config = config
        
        # 脈衝計數器
        self._left_pulse_count = 0
        self._right_pulse_count = 0
        
        # 上次讀取時的脈衝數（用於計算增量）
        self._last_left_pulses = 0
        self._last_right_pulses = 0
        
        # 速度計算相關
        self._velocity_window_size = 10
        self._left_pulse_times = []
        self._right_pulse_times = []
        
        # 線程安全鎖
        self._lock = threading.Lock()
        
        # 初始化狀態
        self._initialized = False
        self._last_update_time = 0.0
        
        logger.info("🔢 編碼器讀取器已初始化")
    
    async def initialize(self):
        """初始化編碼器GPIO"""
        try:
            # 設置GPIO模式
            GPIO.setmode(GPIO.BCM)
            
            # 設置編碼器引腳
            GPIO.setup(self.config.left_encoder_pin_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.config.left_encoder_pin_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.config.right_encoder_pin_a, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.config.right_encoder_pin_b, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # 設置中斷回調
            GPIO.add_event_detect(
                self.config.left_encoder_pin_a, 
                GPIO.RISING,
                callback=self._left_encoder_callback,
                bouncetime=self.config.debounce_time
            )
            
            GPIO.add_event_detect(
                self.config.right_encoder_pin_a,
                GPIO.RISING, 
                callback=self._right_encoder_callback,
                bouncetime=self.config.debounce_time
            )
            
            self._initialized = True
            self._last_update_time = time.time()
            
            logger.success("✅ 編碼器GPIO初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 編碼器初始化失敗: {e}")
            raise
    
    def _left_encoder_callback(self, channel):
        """左輪編碼器中斷回調"""
        current_time = time.time()
        
        with self._lock:
            self._left_pulse_count += 1
            
            # 記錄脈衝時間用於速度計算
            self._left_pulse_times.append(current_time)
            if len(self._left_pulse_times) > self._velocity_window_size:
                self._left_pulse_times.pop(0)
    
    def _right_encoder_callback(self, channel):
        """右輪編碼器中斷回調"""
        current_time = time.time()
        
        with self._lock:
            self._right_pulse_count += 1
            
            # 記錄脈衝時間用於速度計算
            self._right_pulse_times.append(current_time)
            if len(self._right_pulse_times) > self._velocity_window_size:
                self._right_pulse_times.pop(0)
    
    def get_encoder_data(self) -> EncoderData:
        """獲取當前編碼器數據"""
        current_time = time.time()
        
        with self._lock:
            # 獲取當前脈衝數
            left_pulses = self._left_pulse_count
            right_pulses = self._right_pulse_count
            
            # 計算速度
            left_velocity = self._calculate_velocity(self._left_pulse_times, current_time)
            right_velocity = self._calculate_velocity(self._right_pulse_times, current_time)
        
        return EncoderData(
            left_pulses=left_pulses,
            right_pulses=right_pulses,
            left_velocity=left_velocity,
            right_velocity=right_velocity,
            timestamp=current_time
        )
    
    def get_incremental_data(self) -> Tuple[int, int, float]:
        """
        獲取增量編碼器數據
        
        Returns:
            Tuple[int, int, float]: (左輪增量脈衝, 右輪增量脈衝, 時間間隔)
        """
        current_time = time.time()
        
        with self._lock:
            # 計算脈衝增量
            left_delta = self._left_pulse_count - self._last_left_pulses
            right_delta = self._right_pulse_count - self._last_right_pulses
            
            # 計算時間間隔
            dt = current_time - self._last_update_time
            
            # 更新上次讀取值
            self._last_left_pulses = self._left_pulse_count
            self._last_right_pulses = self._right_pulse_count
            self._last_update_time = current_time
        
        return left_delta, right_delta, dt
    
    def _calculate_velocity(self, pulse_times: list, current_time: float) -> float:
        """
        根據脈衝時間計算速度
        
        Args:
            pulse_times: 脈衝時間列表
            current_time: 當前時間
            
        Returns:
            float: 輪子線速度 (米/秒)
        """
        if len(pulse_times) < 2:
            return 0.0
        
        # 移除過舊的數據（超過1秒的）
        valid_times = [t for t in pulse_times if current_time - t <= 1.0]
        
        if len(valid_times) < 2:
            return 0.0
        
        # 計算時間間隔內的脈衝數
        time_span = valid_times[-1] - valid_times[0]
        if time_span <= 0:
            return 0.0
        
        pulse_count = len(valid_times) - 1
        
        # 計算轉速 (轉/秒)
        rps = pulse_count / self.config.pulses_per_revolution / time_span
        
        # 轉換為線速度 (米/秒)
        linear_velocity = rps * 2 * 3.14159 * self.config.wheel_radius
        
        return linear_velocity
    
    def reset_counters(self):
        """重置脈衝計數器"""
        with self._lock:
            self._left_pulse_count = 0
            self._right_pulse_count = 0
            self._last_left_pulses = 0
            self._last_right_pulses = 0
            self._left_pulse_times.clear()
            self._right_pulse_times.clear()
            self._last_update_time = time.time()
        
        logger.info("🔄 編碼器計數器已重置")
    
    def get_pulses_per_meter(self) -> float:
        """獲取每米的脈衝數"""
        wheel_circumference = 2 * 3.14159 * self.config.wheel_radius
        return self.config.pulses_per_revolution / wheel_circumference
    
    def pulses_to_distance(self, pulses: int) -> float:
        """將脈衝數轉換為距離（米）"""
        wheel_circumference = 2 * 3.14159 * self.config.wheel_radius
        return (pulses / self.config.pulses_per_revolution) * wheel_circumference
    
    async def cleanup(self):
        """清理資源"""
        if self._initialized:
            try:
                GPIO.cleanup()
                logger.info("🧹 編碼器GPIO已清理")
            except Exception as e:
                logger.error(f"❌ 編碼器清理失敗: {e}")
    
    def get_status(self) -> Dict:
        """獲取編碼器狀態"""
        data = self.get_encoder_data()
        
        return {
            'initialized': self._initialized,
            'left_pulses': data.left_pulses,
            'right_pulses': data.right_pulses,
            'left_velocity': round(data.left_velocity, 3),
            'right_velocity': round(data.right_velocity, 3),
            'pulses_per_meter': round(self.get_pulses_per_meter(), 2),
            'config': {
                'wheel_radius': self.config.wheel_radius,
                'wheel_base': self.config.wheel_base,
                'pulses_per_revolution': self.config.pulses_per_revolution
            }
        }