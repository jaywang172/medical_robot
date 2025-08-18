#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心硬件控制模組 - car_run_turn
提供基礎的機器人運動控制功能，可以獨立運行或整合到更大的系統中
"""

import asyncio
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    import RPi.GPIO as GPIO
    PI_AVAILABLE = True
except ImportError:
    # 模擬模式，用於開發測試
    PI_AVAILABLE = False
    print("運行在模擬模式 - 樹莓派GPIO不可用")

# 電機引腳配置
Motor_R1_Pin = 16  # 右電機正轉
Motor_R2_Pin = 18  # 右電機反轉
Motor_L1_Pin = 11  # 左電機正轉
Motor_L2_Pin = 13  # 左電機反轉
DEFAULT_DURATION = 0.5  # 默認運動時間


class MotorDirection(Enum):
    """電機運動方向"""
    FORWARD = "forward"
    BACKWARD = "backward"
    LEFT = "left"
    RIGHT = "right"
    STOP = "stop"


@dataclass
class MotorStatus:
    """電機狀態"""
    is_moving: bool = False
    current_direction: MotorDirection = MotorDirection.STOP
    last_command_time: float = 0.0
    emergency_stop: bool = False


class CarRunTurnController:
    """
    核心車輛控制器 - 整合版
    提供基礎運動控制，可獨立使用或整合到更大系統
    """
    
    def __init__(self, duration: float = DEFAULT_DURATION, simulation: bool = False):
        self.duration = duration
        self.simulation = simulation or not PI_AVAILABLE
        self.status = MotorStatus()
        
        # 初始化GPIO（如果在真實硬件上）
        if not self.simulation:
            self._initialize_gpio()
        
        print(f"CarRunTurnController 初始化完成 - {'模擬模式' if self.simulation else '硬件模式'}")
    
    def _initialize_gpio(self):
        """初始化GPIO設置"""
        if self.simulation:
            return
            
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(Motor_R1_Pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(Motor_R2_Pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(Motor_L1_Pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(Motor_L2_Pin, GPIO.OUT, initial=GPIO.LOW)
        print("GPIO 初始化完成")


    def _set_motor_pins(self, r1: bool, r2: bool, l1: bool, l2: bool):
        """設置電機引腳狀態"""
        if self.simulation:
            print(f"模擬電機控制: R1={r1}, R2={r2}, L1={l1}, L2={l2}")
            return
            
        GPIO.output(Motor_R1_Pin, r1)
        GPIO.output(Motor_R2_Pin, r2)
        GPIO.output(Motor_L1_Pin, l1)
        GPIO.output(Motor_L2_Pin, l2)
    
    async def stop(self):
        """停止所有電機"""
        if self.status.emergency_stop:
            print("緊急停止狀態中")
            return
            
        self._set_motor_pins(False, False, False, False)
        self.status.is_moving = False
        self.status.current_direction = MotorDirection.STOP
        self.status.last_command_time = time.time()
        print("電機已停止")

    async def forward(self, duration: Optional[float] = None):
        """前進"""
        if self.status.emergency_stop:
            print("緊急停止狀態中，忽略前進命令")
            return
            
        duration = duration or self.duration
        print(f"前進 {duration}秒")
        
        self._set_motor_pins(True, False, True, False)
        self.status.is_moving = True
        self.status.current_direction = MotorDirection.FORWARD
        self.status.last_command_time = time.time()
        
        if duration > 0:
            await asyncio.sleep(duration)
            await self.stop()

    async def backward(self, duration: Optional[float] = None):
        """後退"""
        if self.status.emergency_stop:
            print("緊急停止狀態中，忽略後退命令")
            return
            
        duration = duration or self.duration
        print(f"後退 {duration}秒")
        
        self._set_motor_pins(False, True, False, True)
        self.status.is_moving = True
        self.status.current_direction = MotorDirection.BACKWARD
        self.status.last_command_time = time.time()
        
        if duration > 0:
            await asyncio.sleep(duration)
            await self.stop()

    async def turn_right(self, duration: Optional[float] = None):
        """右轉 - 左輪前進，右輪停止"""
        if self.status.emergency_stop:
            print("緊急停止狀態中，忽略右轉命令")
            return
            
        duration = duration or self.duration
        print(f"右轉 {duration}秒")
        
        self._set_motor_pins(False, False, True, False)
        self.status.is_moving = True
        self.status.current_direction = MotorDirection.RIGHT
        self.status.last_command_time = time.time()
        
        if duration > 0:
            await asyncio.sleep(duration)
            await self.stop()

    async def turn_left(self, duration: Optional[float] = None):
        """左轉 - 右輪前進，左輪停止"""
        if self.status.emergency_stop:
            print("緊急停止狀態中，忽略左轉命令")
            return
            
        duration = duration or self.duration
        print(f"左轉 {duration}秒")
        
        self._set_motor_pins(True, False, False, False)
        self.status.is_moving = True
        self.status.current_direction = MotorDirection.LEFT
        self.status.last_command_time = time.time()
        
        if duration > 0:
            await asyncio.sleep(duration)
            await self.stop()
    
    async def emergency_stop(self):
        """緊急停止"""
        print("🚨 執行緊急停止")
        self.status.emergency_stop = True
        self._set_motor_pins(False, False, False, False)
        self.status.is_moving = False
        self.status.current_direction = MotorDirection.STOP
        self.status.last_command_time = time.time()
    
    def reset_emergency_stop(self):
        """重置緊急停止狀態"""
        print("重置緊急停止狀態")
        self.status.emergency_stop = False
    
    def get_status(self) -> Dict[str, Any]:
        """獲取當前狀態"""
        return {
            "is_moving": self.status.is_moving,
            "current_direction": self.status.current_direction.value,
            "last_command_time": self.status.last_command_time,
            "emergency_stop": self.status.emergency_stop,
            "simulation_mode": self.simulation
        }
    
    def cleanup(self):
        """清理資源"""
        if not self.simulation and PI_AVAILABLE:
            GPIO.cleanup()
        print("CarRunTurnController 資源已清理")


# 為了向後兼容，保留原始函數接口
def stop():
    """向後兼容的停止函數"""
    if PI_AVAILABLE:
        GPIO.output(Motor_R1_Pin, False)
        GPIO.output(Motor_R2_Pin, False)
        GPIO.output(Motor_L1_Pin, False)
        GPIO.output(Motor_L2_Pin, False)


def forward():
    """向後兼容的前進函數"""
    if PI_AVAILABLE:
        GPIO.output(Motor_R1_Pin, True)
        GPIO.output(Motor_R2_Pin, False)
        GPIO.output(Motor_L1_Pin, True)
        GPIO.output(Motor_L2_Pin, False)
        time.sleep(DEFAULT_DURATION)
        stop()


def backward():
    """向後兼容的後退函數"""
    if PI_AVAILABLE:
        GPIO.output(Motor_R1_Pin, False)
        GPIO.output(Motor_R2_Pin, True)
        GPIO.output(Motor_L1_Pin, False)
        GPIO.output(Motor_L2_Pin, True)
        time.sleep(DEFAULT_DURATION)
        stop()


def turnRight():
    """向後兼容的右轉函數"""
    if PI_AVAILABLE:
        GPIO.output(Motor_R1_Pin, False)
        GPIO.output(Motor_R2_Pin, False)
        GPIO.output(Motor_L1_Pin, True)
        GPIO.output(Motor_L2_Pin, False)
        time.sleep(DEFAULT_DURATION)
        stop()


def turnLeft():
    """向後兼容的左轉函數"""
    if PI_AVAILABLE:
        GPIO.output(Motor_R1_Pin, True)
        GPIO.output(Motor_R2_Pin, False)
        GPIO.output(Motor_L1_Pin, False)
        GPIO.output(Motor_L2_Pin, False)
        time.sleep(DEFAULT_DURATION)
        stop()


# 整合API - 提供給主系統使用的接口
async def create_car_controller(duration: float = DEFAULT_DURATION, simulation: bool = False) -> CarRunTurnController:
    """創建車輛控制器實例"""
    return CarRunTurnController(duration=duration, simulation=simulation)


# 主程序 - 可獨立運行進行測試
if __name__ == "__main__":
    import sys
    
    async def main():
        """主測試程序"""
        controller = CarRunTurnController(simulation=('--sim' in sys.argv))
        
        print("車輛控制器測試程序")
        print("指令: f=前進, b=後退, r=右轉, l=左轉, s=停止, e=緊急停止, x=重置緊急停止, q=退出")
        
        try:
            while True:
                try:
                    ch = input('\n請輸入指令: ').lower().strip()
                    
                    if ch == 'f':
                        await controller.forward()
                    elif ch == 'b':
                        await controller.backward()
                    elif ch == 'r':
                        await controller.turn_right()
                    elif ch == 'l':
                        await controller.turn_left()
                    elif ch == 's':
                        await controller.stop()
                    elif ch == 'e':
                        await controller.emergency_stop()
                    elif ch == 'x':
                        controller.reset_emergency_stop()
                    elif ch == 'q':
                        print("\n退出程序")
                        break
                    elif ch == 'status':
                        status = controller.get_status()
                        print(f"狀態: {status}")
                    else:
                        print("無效指令!")
                        
                except KeyboardInterrupt:
                    print("\n檢測到 Ctrl+C，執行緊急停止...")
                    await controller.emergency_stop()
                    break
                    
        finally:
            controller.cleanup()
    
    # 運行主程序
    asyncio.run(main())