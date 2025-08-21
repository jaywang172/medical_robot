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

# 樹莓派5兼容的GPIO導入
GPIO_LIB = None
PI_AVAILABLE = False
GPIO_BACKEND = "simulation"

# 嘗試導入GPIO庫，按優先級
try:
    # 首先嘗試 lgpio (樹莓派5推薦)
    import lgpio
    GPIO_LIB = "lgpio"
    PI_AVAILABLE = True
    GPIO_BACKEND = "lgpio"
    print("✅ 使用 lgpio 庫 - Pi 5 兼容模式")
except ImportError:
    try:
        # 嘗試 gpiozero (跨平台兼容)
        from gpiozero import OutputDevice
        GPIO_LIB = "gpiozero"
        PI_AVAILABLE = True
        GPIO_BACKEND = "gpiozero"
        print("✅ 使用 gpiozero 庫 - 通用兼容模式")
    except ImportError:
        try:
            # 最後嘗試傳統的 RPi.GPIO
            import RPi.GPIO as GPIO
            GPIO_LIB = "RPi.GPIO"
            PI_AVAILABLE = True
            GPIO_BACKEND = "RPi.GPIO"
            print("✅ 使用 RPi.GPIO 庫 - 傳統模式")
        except ImportError:
            # 模擬模式，用於開發測試
            PI_AVAILABLE = False
            GPIO_BACKEND = "simulation"
            print("⚠️ 運行在模擬模式 - 樹莓派GPIO不可用")

# 電機引腳配置 (BOARD編號)
Motor_R1_Pin = 16  # 右電機正轉 (BOARD 36, BCM 16)
Motor_R2_Pin = 18  # 右電機反轉 (BOARD 12, BCM 18) 
Motor_L1_Pin = 11  # 左電機正轉 (BOARD 23, BCM 11)
Motor_L2_Pin = 13  # 左電機反轉 (BOARD 33, BCM 13)
DEFAULT_DURATION = 0.5  # 默認運動時間

# BCM模式下的引腳映射 (用於 gpiozero 和 lgpio)
BCM_Motor_R1_Pin = 16  # GPIO16
BCM_Motor_R2_Pin = 18  # GPIO18
BCM_Motor_L1_Pin = 11  # GPIO11 
BCM_Motor_L2_Pin = 13  # GPIO13


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
    核心車輛控制器 - 樹莓派5兼容版
    提供基礎運動控制，支持多種GPIO庫
    """
    
    def __init__(self, duration: float = DEFAULT_DURATION, simulation: bool = False):
        self.duration = duration
        self.simulation = simulation or not PI_AVAILABLE
        self.status = MotorStatus()
        self.gpio_backend = GPIO_BACKEND
        
        # GPIO相關變量
        self.gpio_handle = None
        self.motor_pins = {}
        
        # 初始化GPIO（如果在真實硬件上）
        if not self.simulation:
            try:
                self._initialize_gpio()
                print(f"✅ GPIO初始化成功 - 使用 {self.gpio_backend}")
            except Exception as e:
                print(f"❌ GPIO 初始化失敗: {e}")
                print("⚠️ 切換到模擬模式")
                self.simulation = True
                self.gpio_backend = "simulation"
        
        print(f"CarRunTurnController 初始化完成 - {'模擬模式' if self.simulation else '硬件模式'} ({self.gpio_backend})")
    
    def _initialize_gpio(self):
        """初始化GPIO設置 - 支持多種GPIO庫"""
        if self.simulation:
            return
        
        if self.gpio_backend == "lgpio":
            self._initialize_lgpio()
        elif self.gpio_backend == "gpiozero":
            self._initialize_gpiozero()
        elif self.gpio_backend == "RPi.GPIO":
            self._initialize_rpi_gpio()
        else:
            raise RuntimeError(f"不支持的GPIO後端: {self.gpio_backend}")
    
    def _initialize_lgpio(self):
        """使用 lgpio 初始化 (樹莓派5推薦)"""
        import lgpio
        
        # 打開GPIO芯片
        self.gpio_handle = lgpio.gpiochip_open(0)
        
        # 設置引腳為輸出模式
        pins = [BCM_Motor_R1_Pin, BCM_Motor_R2_Pin, BCM_Motor_L1_Pin, BCM_Motor_L2_Pin]
        for pin in pins:
            lgpio.gpio_claim_output(self.gpio_handle, pin, 0)  # 0 = 初始為LOW
        
        print("lgpio GPIO 初始化完成")
    
    def _initialize_gpiozero(self):
        """使用 gpiozero 初始化 (通用兼容)"""
        from gpiozero import OutputDevice
        
        # 創建輸出設備
        self.motor_pins = {
            'r1': OutputDevice(BCM_Motor_R1_Pin, active_high=True, initial_value=False),
            'r2': OutputDevice(BCM_Motor_R2_Pin, active_high=True, initial_value=False),
            'l1': OutputDevice(BCM_Motor_L1_Pin, active_high=True, initial_value=False),
            'l2': OutputDevice(BCM_Motor_L2_Pin, active_high=True, initial_value=False)
        }
        
        print("gpiozero GPIO 初始化完成")
    
    def _initialize_rpi_gpio(self):
        """使用 RPi.GPIO 初始化 (傳統模式)"""
        import RPi.GPIO as GPIO
        
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(Motor_R1_Pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(Motor_R2_Pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(Motor_L1_Pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(Motor_L2_Pin, GPIO.OUT, initial=GPIO.LOW)
        
        print("RPi.GPIO 初始化完成")


    def _set_motor_pins(self, r1: bool, r2: bool, l1: bool, l2: bool):
        """設置電機引腳狀態 - 支持多種GPIO庫"""
        if self.simulation:
            print(f"模擬電機控制: R1={r1}, R2={r2}, L1={l1}, L2={l2}")
            return
        
        try:
            if self.gpio_backend == "lgpio":
                self._set_pins_lgpio(r1, r2, l1, l2)
            elif self.gpio_backend == "gpiozero":
                self._set_pins_gpiozero(r1, r2, l1, l2)
            elif self.gpio_backend == "RPi.GPIO":
                self._set_pins_rpi_gpio(r1, r2, l1, l2)
        except Exception as e:
            print(f"❌ GPIO控制錯誤: {e}")
    
    def _set_pins_lgpio(self, r1: bool, r2: bool, l1: bool, l2: bool):
        """使用 lgpio 設置引腳"""
        import lgpio
        
        if self.gpio_handle is None:
            return
        
        pins_values = [
            (BCM_Motor_R1_Pin, int(r1)),
            (BCM_Motor_R2_Pin, int(r2)),
            (BCM_Motor_L1_Pin, int(l1)),
            (BCM_Motor_L2_Pin, int(l2))
        ]
        
        for pin, value in pins_values:
            lgpio.gpio_write(self.gpio_handle, pin, value)
    
    def _set_pins_gpiozero(self, r1: bool, r2: bool, l1: bool, l2: bool):
        """使用 gpiozero 設置引腳"""
        if not self.motor_pins:
            return
        
        if r1:
            self.motor_pins['r1'].on()
        else:
            self.motor_pins['r1'].off()
        
        if r2:
            self.motor_pins['r2'].on()
        else:
            self.motor_pins['r2'].off()
        
        if l1:
            self.motor_pins['l1'].on()
        else:
            self.motor_pins['l1'].off()
        
        if l2:
            self.motor_pins['l2'].on()
        else:
            self.motor_pins['l2'].off()
    
    def _set_pins_rpi_gpio(self, r1: bool, r2: bool, l1: bool, l2: bool):
        """使用 RPi.GPIO 設置引腳"""
        import RPi.GPIO as GPIO
        
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
        """清理資源 - 支持多種GPIO庫"""
        if self.simulation:
            print("CarRunTurnController 資源已清理 (模擬模式)")
            return
        
        try:
            if self.gpio_backend == "lgpio" and self.gpio_handle is not None:
                import lgpio
                # 釋放所有引腳
                pins = [BCM_Motor_R1_Pin, BCM_Motor_R2_Pin, BCM_Motor_L1_Pin, BCM_Motor_L2_Pin]
                for pin in pins:
                    try:
                        lgpio.gpio_free(self.gpio_handle, pin)
                    except:
                        pass
                # 關閉GPIO芯片
                lgpio.gpiochip_close(self.gpio_handle)
                self.gpio_handle = None
                
            elif self.gpio_backend == "gpiozero" and self.motor_pins:
                # gpiozero 會自動清理
                for pin_device in self.motor_pins.values():
                    try:
                        pin_device.close()
                    except:
                        pass
                self.motor_pins = {}
                
            elif self.gpio_backend == "RPi.GPIO":
                import RPi.GPIO as GPIO
                GPIO.cleanup()
                
        except Exception as e:
            print(f"❌ GPIO清理錯誤: {e}")
        
        print(f"CarRunTurnController 資源已清理 ({self.gpio_backend})")


# 為了向後兼容，保留原始函數接口
# 注意：這些函數僅支持 RPi.GPIO，建議使用 CarRunTurnController 類
def stop():
    """向後兼容的停止函數 (僅限RPi.GPIO)"""
    if PI_AVAILABLE and GPIO_BACKEND == "RPi.GPIO":
        import RPi.GPIO as GPIO
        GPIO.output(Motor_R1_Pin, False)
        GPIO.output(Motor_R2_Pin, False)
        GPIO.output(Motor_L1_Pin, False)
        GPIO.output(Motor_L2_Pin, False)
    else:
        print("⚠️ 向後兼容函數僅支持 RPi.GPIO，請使用 CarRunTurnController 類")


def forward():
    """向後兼容的前進函數 (僅限RPi.GPIO)"""
    if PI_AVAILABLE and GPIO_BACKEND == "RPi.GPIO":
        import RPi.GPIO as GPIO
        GPIO.output(Motor_R1_Pin, True)
        GPIO.output(Motor_R2_Pin, False)
        GPIO.output(Motor_L1_Pin, True)
        GPIO.output(Motor_L2_Pin, False)
        time.sleep(DEFAULT_DURATION)
        stop()
    else:
        print("⚠️ 向後兼容函數僅支持 RPi.GPIO，請使用 CarRunTurnController 類")


def backward():
    """向後兼容的後退函數 (僅限RPi.GPIO)"""
    if PI_AVAILABLE and GPIO_BACKEND == "RPi.GPIO":
        import RPi.GPIO as GPIO
        GPIO.output(Motor_R1_Pin, False)
        GPIO.output(Motor_R2_Pin, True)
        GPIO.output(Motor_L1_Pin, False)
        GPIO.output(Motor_L2_Pin, True)
        time.sleep(DEFAULT_DURATION)
        stop()
    else:
        print("⚠️ 向後兼容函數僅支持 RPi.GPIO，請使用 CarRunTurnController 類")


def turnRight():
    """向後兼容的右轉函數 (僅限RPi.GPIO)"""
    if PI_AVAILABLE and GPIO_BACKEND == "RPi.GPIO":
        import RPi.GPIO as GPIO
        GPIO.output(Motor_R1_Pin, False)
        GPIO.output(Motor_R2_Pin, False)
        GPIO.output(Motor_L1_Pin, True)
        GPIO.output(Motor_L2_Pin, False)
        time.sleep(DEFAULT_DURATION)
        stop()
    else:
        print("⚠️ 向後兼容函數僅支持 RPi.GPIO，請使用 CarRunTurnController 類")


def turnLeft():
    """向後兼容的左轉函數 (僅限RPi.GPIO)"""
    if PI_AVAILABLE and GPIO_BACKEND == "RPi.GPIO":
        import RPi.GPIO as GPIO
        GPIO.output(Motor_R1_Pin, True)
        GPIO.output(Motor_R2_Pin, False)
        GPIO.output(Motor_L1_Pin, False)
        GPIO.output(Motor_L2_Pin, False)
        time.sleep(DEFAULT_DURATION)
        stop()
    else:
        print("⚠️ 向後兼容函數僅支持 RPi.GPIO，請使用 CarRunTurnController 類")


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