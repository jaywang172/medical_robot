#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
電機控制模組
負責機器人的運動控制，包括前進、後退、轉向等
"""

import asyncio
import time
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum

try:
    import RPi.GPIO as GPIO
    from gpiozero import PWMOutputDevice, DigitalOutputDevice
    PI_AVAILABLE = True
except ImportError:
    # 模擬模式，用於開發測試
    PI_AVAILABLE = False

from robot_core.utils.logger import ContextualLogger, log_hardware_event, log_performance


class MotorDirection(Enum):
    """電機方向枚舉"""
    FORWARD = "forward"
    BACKWARD = "backward"
    STOP = "stop"


@dataclass
class MotorCommand:
    """電機控制命令"""
    left_speed: float  # -100 到 100
    right_speed: float  # -100 到 100
    duration: float = 0  # 持續時間，0表示持續執行
    
    def __post_init__(self):
        # 限制速度範圍
        self.left_speed = max(-100, min(100, self.left_speed))
        self.right_speed = max(-100, min(100, self.right_speed))


@dataclass
class RobotPose:
    """機器人位姿"""
    x: float = 0.0  # 位置 x (米)
    y: float = 0.0  # 位置 y (米)
    theta: float = 0.0  # 朝向角度 (弧度)
    linear_velocity: float = 0.0  # 線速度 (m/s)
    angular_velocity: float = 0.0  # 角速度 (rad/s)


class Motor:
    """單個電機控制類"""
    
    def __init__(self, speed_pin: int, direction_pin: int, name: str):
        self.name = name
        self.logger = ContextualLogger(f"Motor-{name}")
        
        if PI_AVAILABLE:
            self.speed_pwm = PWMOutputDevice(speed_pin, frequency=1000)
            self.direction_pin = DigitalOutputDevice(direction_pin)
        else:
            self.logger.warning("運行在模擬模式")
            self.speed_pwm = None
            self.direction_pin = None
        
        self.current_speed = 0.0
        self.current_direction = MotorDirection.STOP
        
    async def set_speed(self, speed: float):
        """
        設置電機速度
        
        Args:
            speed: 速度值 (-100 到 100)，負值表示反向
        """
        # 限制速度範圍
        speed = max(-100, min(100, speed))
        
        # 確定方向
        if speed > 0:
            direction = MotorDirection.FORWARD
            pwm_value = speed / 100.0
        elif speed < 0:
            direction = MotorDirection.BACKWARD
            pwm_value = abs(speed) / 100.0
        else:
            direction = MotorDirection.STOP
            pwm_value = 0.0
        
        # 更新方向
        if direction != self.current_direction:
            await self._set_direction(direction)
        
        # 更新速度
        if PI_AVAILABLE and self.speed_pwm:
            self.speed_pwm.value = pwm_value
        
        self.current_speed = speed
        
        log_hardware_event(
            self.name, "SPEED_SET", 
            value=speed, unit="%"
        )
    
    async def _set_direction(self, direction: MotorDirection):
        """設置電機方向"""
        if PI_AVAILABLE and self.direction_pin:
            if direction == MotorDirection.FORWARD:
                self.direction_pin.on()
            else:
                self.direction_pin.off()
        
        self.current_direction = direction
        
        log_hardware_event(
            self.name, "DIRECTION_SET", 
            value=direction.value
        )
    
    async def stop(self):
        """停止電機"""
        await self.set_speed(0)
        
    def cleanup(self):
        """清理GPIO資源"""
        if PI_AVAILABLE:
            if self.speed_pwm:
                self.speed_pwm.close()
            if self.direction_pin:
                self.direction_pin.close()


class MotorController:
    """雙輪差動驅動控制器"""
    
    def __init__(self, config):
        self.config = config
        self.logger = ContextualLogger("MotorController")
        
        # 初始化電機
        self.left_motor = Motor(
            config.left_motor_pins[0],
            config.left_motor_pins[1],
            "LeftMotor"
        )
        
        self.right_motor = Motor(
            config.right_motor_pins[0],
            config.right_motor_pins[1],
            "RightMotor"
        )
        
        # 機器人狀態
        self.pose = RobotPose()
        self.is_moving = False
        self.emergency_stop = False
        
        # 編碼器支持 (如果啟用)
        self.encoder_enabled = config.encoder_enabled
        if self.encoder_enabled:
            self._setup_encoders()
        
        # 運動學參數 (需要根據實際機器人調整)
        self.wheel_base = 0.3  # 輪距 (米)
        self.wheel_radius = 0.05  # 輪半徑 (米)
        
        self.logger.info("電機控制器初始化完成")
    
    def _setup_encoders(self):
        """設置編碼器 (如果啟用)"""
        if PI_AVAILABLE and self.encoder_enabled:
            # 這裡可以添加編碼器初始化代碼
            pass
    
    async def initialize(self):
        """初始化電機控制器"""
        start_time = time.time()
        
        try:
            # 停止所有電機
            await self.stop_all()
            
            # 重置姿態
            self.pose = RobotPose()
            
            self.logger.info("電機控制器初始化成功")
            
        except Exception as e:
            self.logger.error(f"電機控制器初始化失敗: {e}")
            raise
        
        finally:
            duration = time.time() - start_time
            log_performance("motor_controller_init", duration)
    
    async def execute_command(self, command: MotorCommand):
        """
        執行電機控制命令
        
        Args:
            command: 電機控制命令
        """
        if self.emergency_stop:
            self.logger.warning("緊急停止狀態，忽略移動命令")
            return
        
        start_time = time.time()
        
        try:
            # 設置電機速度
            await asyncio.gather(
                self.left_motor.set_speed(command.left_speed),
                self.right_motor.set_speed(command.right_speed)
            )
            
            self.is_moving = (command.left_speed != 0 or command.right_speed != 0)
            
            # 更新機器人速度
            linear_vel, angular_vel = self._calculate_velocities(
                command.left_speed, command.right_speed
            )
            self.pose.linear_velocity = linear_vel
            self.pose.angular_velocity = angular_vel
            
            # 如果指定了持續時間
            if command.duration > 0:
                await asyncio.sleep(command.duration)
                await self.stop_all()
            
            self.logger.debug(
                f"執行電機命令: L={command.left_speed:.1f}% "
                f"R={command.right_speed:.1f}% "
                f"持續={command.duration:.1f}s"
            )
            
        except Exception as e:
            self.logger.error(f"執行電機命令失敗: {e}")
            await self.emergency_stop_all()
            
        finally:
            duration = time.time() - start_time
            log_performance("motor_command_execution", duration,
                          left_speed=command.left_speed,
                          right_speed=command.right_speed)
    
    def _calculate_velocities(self, left_speed: float, right_speed: float) -> Tuple[float, float]:
        """
        計算機器人線速度和角速度
        
        Args:
            left_speed: 左輪速度百分比
            right_speed: 右輪速度百分比
            
        Returns:
            Tuple[float, float]: (線速度, 角速度)
        """
        # 將百分比轉換為實際速度 (m/s)
        max_wheel_speed = 1.0  # 最大輪速 m/s (根據實際情況調整)
        
        left_vel = (left_speed / 100.0) * max_wheel_speed
        right_vel = (right_speed / 100.0) * max_wheel_speed
        
        # 差動驅動運動學
        linear_velocity = (left_vel + right_vel) / 2.0
        angular_velocity = (right_vel - left_vel) / self.wheel_base
        
        return linear_velocity, angular_velocity
    
    async def move_forward(self, speed: float = 50.0, duration: float = 0):
        """直線前進"""
        command = MotorCommand(speed, speed, duration)
        await self.execute_command(command)
    
    async def move_backward(self, speed: float = 50.0, duration: float = 0):
        """直線後退"""
        command = MotorCommand(-speed, -speed, duration)
        await self.execute_command(command)
    
    async def turn_left(self, speed: float = 50.0, duration: float = 0):
        """左轉"""
        command = MotorCommand(-speed, speed, duration)
        await self.execute_command(command)
    
    async def turn_right(self, speed: float = 50.0, duration: float = 0):
        """右轉"""
        command = MotorCommand(speed, -speed, duration)
        await self.execute_command(command)
    
    async def pivot_left(self, speed: float = 30.0, duration: float = 0):
        """原地左轉"""
        command = MotorCommand(-speed, speed, duration)
        await self.execute_command(command)
    
    async def pivot_right(self, speed: float = 30.0, duration: float = 0):
        """原地右轉"""
        command = MotorCommand(speed, -speed, duration)
        await self.execute_command(command)
    
    async def stop_all(self):
        """停止所有電機"""
        command = MotorCommand(0, 0)
        await self.execute_command(command)
        self.is_moving = False
    
    async def emergency_stop_all(self):
        """緊急停止"""
        self.emergency_stop = True
        await asyncio.gather(
            self.left_motor.stop(),
            self.right_motor.stop()
        )
        self.is_moving = False
        self.logger.warning("🚨 緊急停止已激活")
    
    def reset_emergency_stop(self):
        """重置緊急停止狀態"""
        self.emergency_stop = False
        self.logger.info("緊急停止已重置")
    
    def get_status(self) -> Dict:
        """獲取電機狀態"""
        return {
            "left_motor": {
                "speed": self.left_motor.current_speed,
                "direction": self.left_motor.current_direction.value
            },
            "right_motor": {
                "speed": self.right_motor.current_speed,
                "direction": self.right_motor.current_direction.value
            },
            "is_moving": self.is_moving,
            "emergency_stop": self.emergency_stop,
            "pose": {
                "x": self.pose.x,
                "y": self.pose.y,
                "theta": self.pose.theta,
                "linear_velocity": self.pose.linear_velocity,
                "angular_velocity": self.pose.angular_velocity
            }
        }
    
    def cleanup(self):
        """清理資源"""
        self.left_motor.cleanup()
        self.right_motor.cleanup()
        
        if PI_AVAILABLE:
            GPIO.cleanup()
        
        self.logger.info("電機控制器已清理") 