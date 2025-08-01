#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
感測器管理模組
統一管理所有感測器的數據收集和處理
"""

import asyncio
import time
import math
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    import RPi.GPIO as GPIO
    from gpiozero import DistanceSensor
    import board
    import busio
    from adafruit_mpu6050 import MPU6050
    PI_AVAILABLE = True
except ImportError:
    # 模擬模式
    PI_AVAILABLE = False

from robot_core.utils.logger import ContextualLogger, log_hardware_event, log_performance


@dataclass
class UltrasonicReading:
    """超聲波感測器讀數"""
    distance: float  # 距離 (米)
    timestamp: float
    sensor_id: str
    is_valid: bool = True


@dataclass
class IMUReading:
    """慣性測量單元讀數"""
    acceleration: Tuple[float, float, float]  # x, y, z 加速度 (m/s²)
    gyroscope: Tuple[float, float, float]     # x, y, z 角速度 (rad/s)
    temperature: float                        # 溫度 (°C)
    timestamp: float
    is_valid: bool = True


@dataclass
class SensorData:
    """感測器數據集合"""
    ultrasonic: Dict[str, UltrasonicReading]
    imu: Optional[IMUReading]
    timestamp: float
    
    def get_min_distance(self) -> float:
        """獲取最小距離"""
        valid_distances = [
            reading.distance 
            for reading in self.ultrasonic.values() 
            if reading.is_valid
        ]
        return min(valid_distances) if valid_distances else float('inf')
    
    def has_obstacle(self, threshold: float = 0.5) -> bool:
        """檢查是否有障礙物"""
        return self.get_min_distance() < threshold


class UltrasonicSensor:
    """超聲波感測器控制類"""
    
    def __init__(self, trigger_pin: int, echo_pin: int, sensor_id: str):
        self.sensor_id = sensor_id
        self.logger = ContextualLogger(f"Ultrasonic-{sensor_id}")
        
        if PI_AVAILABLE:
            try:
                self.sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin)
                self.is_available = True
            except Exception as e:
                self.logger.error(f"初始化超聲波感測器失敗: {e}")
                self.sensor = None
                self.is_available = False
        else:
            self.sensor = None
            self.is_available = False
            self.logger.warning("運行在模擬模式")
        
        self.last_reading = None
        self.max_distance = 4.0  # 最大測量距離 (米)
        
    async def read_distance(self) -> UltrasonicReading:
        """讀取距離數據"""
        timestamp = time.time()
        
        if not self.is_available:
            # 模擬模式：返回隨機數據
            import random
            distance = random.uniform(0.5, 3.0)
            return UltrasonicReading(distance, timestamp, self.sensor_id, True)
        
        try:
            # 讀取距離
            distance = self.sensor.distance
            
            # 驗證讀數
            is_valid = (0.02 <= distance <= self.max_distance)
            
            if not is_valid:
                distance = self.max_distance  # 超出範圍時設為最大值
            
            reading = UltrasonicReading(distance, timestamp, self.sensor_id, is_valid)
            self.last_reading = reading
            
            log_hardware_event(
                f"Ultrasonic-{self.sensor_id}", 
                "DISTANCE_READ",
                value=distance, unit="m"
            )
            
            return reading
            
        except Exception as e:
            self.logger.error(f"讀取距離失敗: {e}")
            return UltrasonicReading(
                self.max_distance, timestamp, self.sensor_id, False
            )
    
    def cleanup(self):
        """清理資源"""
        if self.sensor and PI_AVAILABLE:
            self.sensor.close()


class IMUSensor:
    """慣性測量單元控制類"""
    
    def __init__(self, i2c_address: int = 0x68):
        self.logger = ContextualLogger("IMU")
        self.i2c_address = i2c_address
        
        if PI_AVAILABLE:
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                self.mpu = MPU6050(i2c, address=i2c_address)
                self.is_available = True
                self.logger.info(f"IMU初始化成功，地址: 0x{i2c_address:02x}")
            except Exception as e:
                self.logger.error(f"IMU初始化失敗: {e}")
                self.mpu = None
                self.is_available = False
        else:
            self.mpu = None
            self.is_available = False
            self.logger.warning("運行在模擬模式")
        
        self.last_reading = None
        
        # 校準偏移值
        self.accel_offset = (0.0, 0.0, 0.0)
        self.gyro_offset = (0.0, 0.0, 0.0)
        
    async def calibrate(self, samples: int = 100):
        """校準IMU感測器"""
        if not self.is_available:
            return
        
        self.logger.info(f"開始IMU校準，採樣數: {samples}")
        
        accel_sum = [0.0, 0.0, 0.0]
        gyro_sum = [0.0, 0.0, 0.0]
        
        for i in range(samples):
            reading = await self.read_imu()
            
            if reading.is_valid:
                for j in range(3):
                    accel_sum[j] += reading.acceleration[j]
                    gyro_sum[j] += reading.gyroscope[j]
            
            await asyncio.sleep(0.01)  # 10ms間隔
        
        # 計算偏移值
        self.accel_offset = tuple(x / samples for x in accel_sum)
        self.gyro_offset = tuple(x / samples for x in gyro_sum)
        
        # 重力補償 (假設z軸向上)
        gravity_offset = (0.0, 0.0, -9.81)
        self.accel_offset = tuple(
            self.accel_offset[i] - gravity_offset[i] for i in range(3)
        )
        
        self.logger.info(f"IMU校準完成")
        self.logger.info(f"加速度偏移: {self.accel_offset}")
        self.logger.info(f"陀螺儀偏移: {self.gyro_offset}")
    
    async def read_imu(self) -> IMUReading:
        """讀取IMU數據"""
        timestamp = time.time()
        
        if not self.is_available:
            # 模擬模式：返回模擬數據
            import random
            accel = (
                random.uniform(-1, 1),
                random.uniform(-1, 1),
                random.uniform(9, 10)
            )
            gyro = (
                random.uniform(-0.1, 0.1),
                random.uniform(-0.1, 0.1),
                random.uniform(-0.1, 0.1)
            )
            temp = random.uniform(20, 30)
            
            return IMUReading(accel, gyro, temp, timestamp, True)
        
        try:
            # 讀取原始數據
            raw_accel = self.mpu.acceleration
            raw_gyro = self.mpu.gyro
            temperature = self.mpu.temperature
            
            # 應用校準偏移
            acceleration = tuple(
                raw_accel[i] - self.accel_offset[i] for i in range(3)
            )
            gyroscope = tuple(
                raw_gyro[i] - self.gyro_offset[i] for i in range(3)
            )
            
            reading = IMUReading(
                acceleration, gyroscope, temperature, timestamp, True
            )
            self.last_reading = reading
            
            log_hardware_event(
                "IMU", "DATA_READ",
                value=f"a={acceleration}, g={gyroscope}, t={temperature:.1f}°C"
            )
            
            return reading
            
        except Exception as e:
            self.logger.error(f"讀取IMU數據失敗: {e}")
            return IMUReading(
                (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.0, timestamp, False
            )


class SensorManager:
    """感測器管理器"""
    
    def __init__(self, config):
        self.config = config
        self.logger = ContextualLogger("SensorManager")
        
        # 初始化超聲波感測器
        self.ultrasonic_sensors = {}
        if config.ultrasonic_enabled:
            for sensor_id, pins in config.ultrasonic_pins.items():
                trigger_pin, echo_pin = pins
                self.ultrasonic_sensors[sensor_id] = UltrasonicSensor(
                    trigger_pin, echo_pin, sensor_id
                )
        
        # 初始化IMU感測器
        self.imu_sensor = None
        if config.imu_enabled:
            self.imu_sensor = IMUSensor(config.imu_i2c_address)
        
        # 數據緩存
        self.last_sensor_data = None
        self.sensor_update_interval = 1.0 / config.sensor_update_rate
        
        # 異常檢測
        self.consecutive_failures = 0
        self.max_failures = 5
        
        self.logger.info("感測器管理器初始化完成")
    
    async def initialize(self):
        """初始化感測器管理器"""
        start_time = time.time()
        
        try:
            # 校準IMU
            if self.imu_sensor and self.imu_sensor.is_available:
                await self.imu_sensor.calibrate()
            
            # 測試所有感測器
            await self.get_all_data()
            
            self.logger.info("感測器管理器初始化成功")
            
        except Exception as e:
            self.logger.error(f"感測器管理器初始化失敗: {e}")
            raise
        
        finally:
            duration = time.time() - start_time
            log_performance("sensor_manager_init", duration)
    
    async def get_all_data(self) -> SensorData:
        """獲取所有感測器數據"""
        start_time = time.time()
        timestamp = time.time()
        
        try:
            # 並行讀取超聲波感測器
            ultrasonic_tasks = [
                sensor.read_distance() 
                for sensor in self.ultrasonic_sensors.values()
            ]
            
            ultrasonic_readings = []
            if ultrasonic_tasks:
                ultrasonic_readings = await asyncio.gather(*ultrasonic_tasks)
            
            # 讀取IMU數據
            imu_reading = None
            if self.imu_sensor:
                imu_reading = await self.imu_sensor.read_imu()
            
            # 組織數據
            ultrasonic_data = {
                reading.sensor_id: reading 
                for reading in ultrasonic_readings
            }
            
            sensor_data = SensorData(ultrasonic_data, imu_reading, timestamp)
            self.last_sensor_data = sensor_data
            
            # 重置失敗計數
            self.consecutive_failures = 0
            
            return sensor_data
            
        except Exception as e:
            self.logger.error(f"讀取感測器數據失敗: {e}")
            self.consecutive_failures += 1
            
            if self.consecutive_failures >= self.max_failures:
                self.logger.warning("感測器連續失敗過多，可能需要檢查硬體")
            
            # 返回上次的數據或空數據
            if self.last_sensor_data:
                return self.last_sensor_data
            else:
                return SensorData({}, None, timestamp)
        
        finally:
            duration = time.time() - start_time
            log_performance("sensor_data_read", duration)
    
    async def get_obstacle_distances(self) -> Dict[str, float]:
        """獲取所有方向的障礙物距離"""
        sensor_data = await self.get_all_data()
        return {
            sensor_id: reading.distance 
            for sensor_id, reading in sensor_data.ultrasonic.items()
            if reading.is_valid
        }
    
    async def check_safety(self, safety_distance: float = 0.3) -> Tuple[bool, List[str]]:
        """
        檢查安全狀態
        
        Returns:
            Tuple[bool, List[str]]: (是否安全, 觸發警告的感測器列表)
        """
        sensor_data = await self.get_all_data()
        
        dangerous_sensors = []
        for sensor_id, reading in sensor_data.ultrasonic.items():
            if reading.is_valid and reading.distance < safety_distance:
                dangerous_sensors.append(sensor_id)
        
        is_safe = len(dangerous_sensors) == 0
        return is_safe, dangerous_sensors
    
    def get_status(self) -> Dict:
        """獲取感測器狀態"""
        ultrasonic_status = {
            sensor_id: {
                "available": sensor.is_available,
                "last_distance": sensor.last_reading.distance if sensor.last_reading else None
            }
            for sensor_id, sensor in self.ultrasonic_sensors.items()
        }
        
        imu_status = {
            "available": self.imu_sensor.is_available if self.imu_sensor else False,
            "last_reading": {
                "acceleration": self.imu_sensor.last_reading.acceleration if self.imu_sensor and self.imu_sensor.last_reading else None,
                "gyroscope": self.imu_sensor.last_reading.gyroscope if self.imu_sensor and self.imu_sensor.last_reading else None,
                "temperature": self.imu_sensor.last_reading.temperature if self.imu_sensor and self.imu_sensor.last_reading else None
            } if self.imu_sensor else None
        }
        
        return {
            "ultrasonic": ultrasonic_status,
            "imu": imu_status,
            "consecutive_failures": self.consecutive_failures,
            "last_update": self.last_sensor_data.timestamp if self.last_sensor_data else None
        }
    
    async def cleanup(self):
        """清理資源"""
        # 清理超聲波感測器
        for sensor in self.ultrasonic_sensors.values():
            sensor.cleanup()
        
        # 清理IMU (如果需要)
        if self.imu_sensor:
            pass  # IMU通常不需要特殊清理
        
        self.logger.info("感測器管理器已清理") 