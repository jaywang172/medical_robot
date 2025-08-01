#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
樹莓派智能送貨機器人 - 改進版主程序
採用事件驅動架構、中央狀態機和精確里程計

主要改進：
1. 事件驅動架構：解耦模組間依賴
2. 中央狀態機：統一狀態管理
3. 精確里程計：閉環位姿估計
4. 感測器融合：提高定位精度
"""

import asyncio
import signal
import sys
from pathlib import Path
from loguru import logger
from contextlib import asynccontextmanager
from typing import Optional

# 添加項目根路徑到Python路徑
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from robot_core.config import RobotConfig
from robot_core.hardware.motor_controller import MotorController
from robot_core.hardware.sensor_manager import SensorManager
from robot_core.ai.vision_system import VisionSystem
from robot_core.navigation.path_planner import PathPlanner
from robot_core.api.server import create_app
from robot_core.utils.logger import setup_logger

# 新架構組件
from robot_core.events import (
    EventBus, initialize_event_bus, shutdown_event_bus,
    EventType, create_system_state_event, create_emergency_event,
    create_motor_status_event, create_sensor_data_event, create_navigation_event
)
from robot_core.state_machine import (
    RobotStateMachine, RobotState, StateChangeReason
)
from robot_core.localization import (
    Odometry, SensorFusion, EncoderReader, EncoderConfig
)


class ImprovedRobotSystem:
    """
    改進版機器人系統主控制類
    
    新特性：
    - 事件驅動的模組通訊
    - 中央狀態機管理
    - 精確里程計和感測器融合
    - 解耦的架構設計
    """
    
    def __init__(self):
        self.config = RobotConfig()
        
        # 核心組件
        self.event_bus: Optional[EventBus] = None
        self.state_machine: Optional[RobotStateMachine] = None
        
        # 硬體模組
        self.motor_controller: Optional[MotorController] = None
        self.sensor_manager: Optional[SensorManager] = None
        self.vision_system: Optional[VisionSystem] = None
        self.path_planner: Optional[PathPlanner] = None
        
        # 定位模組
        self.odometry: Optional[Odometry] = None
        self.sensor_fusion: Optional[SensorFusion] = None
        
        # 控制變量
        self.is_running = False
        self.emergency_stop_active = False
        
        # 設置日誌
        setup_logger(self.config.log_level)
        logger.info("🤖 初始化改進版機器人系統...")
    
    async def initialize(self):
        """初始化所有系統組件"""
        try:
            # 1. 初始化事件總線
            logger.info("🚌 初始化事件總線...")
            self.event_bus = await initialize_event_bus()
            
            # 2. 初始化狀態機
            logger.info("🔄 初始化狀態機...")
            self.state_machine = RobotStateMachine()
            await self._setup_state_machine_callbacks()
            
            # 3. 初始化硬體模組
            await self._initialize_hardware()
            
            # 4. 初始化定位系統
            await self._initialize_localization()
            
            # 5. 初始化AI系統
            await self._initialize_ai_systems()
            
            # 6. 設置事件訂閱
            await self._setup_event_subscriptions()
            
            # 7. 轉換到空閒狀態
            await self.state_machine.transition_to(
                RobotState.IDLE, 
                StateChangeReason.SYSTEM_INIT
            )
            
            self.is_running = True
            logger.success("✅ 改進版機器人系統初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 系統初始化失敗: {e}")
            await self.state_machine.transition_to(
                RobotState.ERROR, 
                StateChangeReason.SYSTEM_INIT
            )
            raise
    
    async def _initialize_hardware(self):
        """初始化硬體模組"""
        logger.info("⚙️ 初始化硬體模組...")
        
        # 電機控制器
        self.motor_controller = MotorController(self.config.motor_config)
        await self.motor_controller.initialize()
        
        # 感測器管理器
        self.sensor_manager = SensorManager(self.config.sensor_config)
        await self.sensor_manager.initialize()
        
        logger.success("✅ 硬體模組初始化完成")
    
    async def _initialize_localization(self):
        """初始化定位系統"""
        logger.info("📍 初始化定位系統...")
        
        # 編碼器配置
        encoder_config = EncoderConfig(
            pulses_per_revolution=self.config.motor_config.pulses_per_revolution,
            wheel_radius=self.config.motor_config.wheel_radius,
            wheel_base=self.config.motor_config.wheel_base
        )
        
        # 里程計
        self.odometry = Odometry(encoder_config)
        await self.odometry.initialize()
        await self.odometry.start()
        
        # 感測器融合
        self.sensor_fusion = SensorFusion(self.odometry)
        await self.sensor_fusion.start()
        
        logger.success("✅ 定位系統初始化完成")
    
    async def _initialize_ai_systems(self):
        """初始化AI系統"""
        logger.info("🧠 初始化AI系統...")
        
        # 視覺系統
        self.vision_system = VisionSystem(self.config.vision_config)
        await self.vision_system.initialize()
        
        # 路徑規劃器
        self.path_planner = PathPlanner(self.config.navigation_config)
        await self.path_planner.initialize()
        
        logger.success("✅ AI系統初始化完成")
    
    async def _setup_state_machine_callbacks(self):
        """設置狀態機回調函數"""
        
        # 進入緊急停止狀態的回調
        async def on_emergency_stop_enter(state):
            logger.warning("🚨 進入緊急停止狀態")
            self.emergency_stop_active = True
            if self.motor_controller:
                await self.motor_controller.emergency_stop()
        
        # 退出緊急停止狀態的回調
        async def on_emergency_stop_exit(state):
            logger.info("✅ 退出緊急停止狀態")
            self.emergency_stop_active = False
        
        # 進入導航狀態的回調
        async def on_navigating_enter(state):
            logger.info("🧭 開始導航")
            # 可以在這裡執行導航開始的準備工作
        
        # 進入充電狀態的回調
        async def on_charging_enter(state):
            logger.info("🔋 開始充電")
            # 停止所有運動
            if self.motor_controller:
                await self.motor_controller.stop_all()
        
        # 註冊回調
        self.state_machine.on_state_enter(RobotState.EMERGENCY_STOP, on_emergency_stop_enter)
        self.state_machine.on_state_exit(RobotState.EMERGENCY_STOP, on_emergency_stop_exit)
        self.state_machine.on_state_enter(RobotState.NAVIGATING, on_navigating_enter)
        self.state_machine.on_state_enter(RobotState.CHARGING, on_charging_enter)
        
        # 狀態驗證器
        async def validate_navigation_state(state, data):
            """驗證是否可以進入導航狀態"""
            if self.emergency_stop_active:
                return False
            if self.sensor_manager:
                sensor_data = await self.sensor_manager.get_all_data()
                if hasattr(sensor_data, 'battery_voltage') and sensor_data.battery_voltage < 10.0:
                    return False
            return True
        
        self.state_machine.add_state_validator(RobotState.NAVIGATING, validate_navigation_state)
    
    async def _setup_event_subscriptions(self):
        """設置事件訂閱"""
        
        # 訂閱緊急事件
        async def handle_emergency_event(event):
            logger.warning(f"🚨 收到緊急事件: {event.emergency_type}")
            await self.state_machine.transition_to(
                RobotState.EMERGENCY_STOP,
                StateChangeReason.EMERGENCY_BUTTON,
                {'emergency_type': event.emergency_type}
            )
        
        # 訂閱感測器數據事件
        async def handle_sensor_data_event(event):
            # 更新感測器融合系統
            if hasattr(event, 'imu_data') and event.imu_data and self.sensor_fusion:
                # 這裡需要將event中的IMU數據轉換為IMUData格式
                pass
            
            # 檢查低電量
            if hasattr(event, 'battery_voltage') and event.battery_voltage < 10.0:
                await self.state_machine.transition_to(
                    RobotState.CHARGING,
                    StateChangeReason.LOW_BATTERY
                )
        
        # 訂閱導航事件
        async def handle_navigation_event(event):
            # 更新路徑規劃器的位姿信息
            if (hasattr(event, 'current_position') and 
                event.current_position and self.path_planner):
                position = event.current_position
                self.path_planner.update_pose(
                    position['x'], 
                    position['y'], 
                    position['theta']
                )
        
        # 註冊事件訂閱
        self.event_bus.subscribe(EventType.EMERGENCY, handle_emergency_event)
        self.event_bus.subscribe(EventType.SENSOR_DATA, handle_sensor_data_event)
        self.event_bus.subscribe(EventType.NAVIGATION, handle_navigation_event)
    
    async def start_main_loop(self):
        """啟動主控制循環"""
        logger.info("🚀 啟動改進版主控制循環...")
        
        while self.is_running:
            try:
                current_state = self.state_machine.current_state
                
                # 根據狀態執行相應的行為
                if current_state == RobotState.IDLE:
                    await self._handle_idle_state()
                    
                elif current_state == RobotState.NAVIGATING:
                    await self._handle_navigating_state()
                    
                elif current_state == RobotState.MAPPING:
                    await self._handle_mapping_state()
                    
                elif current_state == RobotState.CHARGING:
                    await self._handle_charging_state()
                    
                elif current_state == RobotState.EMERGENCY_STOP:
                    await self._handle_emergency_state()
                    
                elif current_state == RobotState.ERROR:
                    await self._handle_error_state()
                
                # 控制循環頻率
                await asyncio.sleep(self.config.main_loop_interval)
                
            except Exception as e:
                logger.error(f"⚠️ 主控制循環異常: {e}")
                await self.state_machine.transition_to(
                    RobotState.ERROR,
                    StateChangeReason.SYSTEM_INIT,
                    {'error': str(e)}
                )
                await asyncio.sleep(1.0)
    
    async def _handle_idle_state(self):
        """處理空閒狀態"""
        # 在空閒狀態下，主要是數據收集和狀態監控
        await self._collect_sensor_data()
        await self._publish_status_events()
    
    async def _handle_navigating_state(self):
        """處理導航狀態"""
        # 獲取感測器數據
        sensor_data = await self.sensor_manager.get_all_data()
        
        # 處理視覺數據
        vision_data = await self.vision_system.process_frame()
        
        # 更新路徑規劃器的障礙物信息
        if vision_data.get('obstacles'):
            await self.path_planner.update_obstacles(vision_data['obstacles'])
        
        # 獲取融合後的位姿
        fused_pose = self.sensor_fusion.get_fused_pose()
        
        # 更新路徑規劃器的位姿
        self.path_planner.update_pose(
            fused_pose.pose.x,
            fused_pose.pose.y, 
            fused_pose.pose.theta
        )
        
        # 執行導航決策
        navigation_command = await self.path_planner.get_next_move(
            sensor_data, vision_data
        )
        
        # 執行電機控制
        if navigation_command and not self.emergency_stop_active:
            await self.motor_controller.execute_command(navigation_command)
        
        # 檢查是否到達目標
        if self.path_planner.navigation_state.value == "reached_goal":
            await self.state_machine.transition_to(
                RobotState.IDLE,
                StateChangeReason.TASK_COMPLETED
            )
    
    async def _handle_mapping_state(self):
        """處理地圖構建狀態"""
        # 類似導航狀態，但專注於地圖構建
        await self._collect_sensor_data()
        vision_data = await self.vision_system.process_frame()
        
        # 更新地圖
        if self.path_planner.map_manager:
            # 這裡可以添加地圖更新邏輯
            pass
    
    async def _handle_charging_state(self):
        """處理充電狀態"""
        # 在充電狀態下保持靜止，監控電池狀態
        sensor_data = await self.sensor_manager.get_all_data()
        
        # 檢查是否充電完成
        if hasattr(sensor_data, 'battery_voltage') and sensor_data.battery_voltage > 12.0:
            await self.state_machine.transition_to(
                RobotState.IDLE,
                StateChangeReason.TASK_COMPLETED
            )
    
    async def _handle_emergency_state(self):
        """處理緊急停止狀態"""
        # 確保電機停止
        if self.motor_controller:
            await self.motor_controller.emergency_stop()
        
        # 等待手動恢復或自動恢復條件
        # 這裡可以添加自動恢復邏輯
    
    async def _handle_error_state(self):
        """處理錯誤狀態"""
        # 嘗試診斷和恢復
        logger.info("🔧 嘗試從錯誤狀態恢復...")
        
        # 簡單的恢復邏輯
        await asyncio.sleep(5.0)
        
        await self.state_machine.transition_to(
            RobotState.IDLE,
            StateChangeReason.AUTO_RECOVERY
        )
    
    async def _collect_sensor_data(self):
        """收集並發佈感測器數據"""
        try:
            sensor_data = await self.sensor_manager.get_all_data()
            
            # 創建並發佈感測器數據事件
            event = create_sensor_data_event(
                source="SensorManager",
                battery_voltage=getattr(sensor_data, 'battery_voltage', 0.0),
                temperature=getattr(sensor_data, 'temperature', 0.0)
            )
            
            if hasattr(sensor_data, 'ultrasonic_distances'):
                event.ultrasonic_distances = sensor_data.ultrasonic_distances
            
            if hasattr(sensor_data, 'imu_data'):
                event.imu_data = sensor_data.imu_data
                # 更新感測器融合系統
                # self.sensor_fusion.update_imu_data(sensor_data.imu_data)
            
            await self.event_bus.publish(event)
            
        except Exception as e:
            logger.error(f"❌ 感測器數據收集失敗: {e}")
    
    async def _publish_status_events(self):
        """發佈系統狀態事件"""
        try:
            # 發佈電機狀態事件
            if self.motor_controller:
                motor_status = self.motor_controller.get_status()
                event = create_motor_status_event(
                    source="MotorController",
                    is_moving=motor_status.get('is_moving', False),
                    emergency_stop=motor_status.get('emergency_stop', False)
                )
                await self.event_bus.publish(event)
            
        except Exception as e:
            logger.error(f"❌ 狀態事件發佈失敗: {e}")
    
    async def shutdown(self):
        """優雅關閉系統"""
        logger.info("🛑 正在關閉改進版機器人系統...")
        
        # 轉換到關閉狀態
        if self.state_machine:
            await self.state_machine.transition_to(
                RobotState.SHUTTING_DOWN,
                StateChangeReason.SYSTEM_SHUTDOWN
            )
        
        self.is_running = False
        
        # 關閉各個組件
        if self.sensor_fusion:
            await self.sensor_fusion.stop()
        
        if self.odometry:
            await self.odometry.stop()
            await self.odometry.cleanup()
        
        if self.motor_controller:
            await self.motor_controller.stop_all()
        
        if self.sensor_manager:
            await self.sensor_manager.cleanup()
        
        if self.vision_system:
            await self.vision_system.cleanup()
        
        # 關閉事件總線
        await shutdown_event_bus()
        
        # 最終狀態
        if self.state_machine:
            await self.state_machine.transition_to(
                RobotState.SHUTDOWN,
                StateChangeReason.SYSTEM_SHUTDOWN
            )
        
        logger.info("✅ 改進版系統已安全關閉")
    
    # API接口方法（用於外部控制）
    async def set_navigation_goal(self, x: float, y: float):
        """設置導航目標"""
        if self.path_planner and self.state_machine.can_transition_to(RobotState.NAVIGATING):
            from robot_core.navigation.path_planner import Point
            goal = Point(x, y)
            success = await self.path_planner.set_goal(goal)
            
            if success:
                await self.state_machine.transition_to(
                    RobotState.NAVIGATING,
                    StateChangeReason.NEW_TASK_ASSIGNED,
                    {'goal': {'x': x, 'y': y}}
                )
                return True
        return False
    
    async def emergency_stop(self):
        """緊急停止"""
        event = create_emergency_event(
            source="UserInterface",
            emergency_type="manual_stop",
            severity="high",
            description="用戶觸發緊急停止"
        )
        await self.event_bus.publish(event, priority=0)  # 最高優先級
    
    async def resume_from_emergency(self):
        """從緊急停止恢復"""
        if self.state_machine.current_state == RobotState.EMERGENCY_STOP:
            await self.state_machine.transition_to(
                RobotState.IDLE,
                StateChangeReason.MANUAL_RECOVERY
            )
    
    def get_system_status(self):
        """獲取系統完整狀態"""
        status = {
            'system_state': self.state_machine.current_state.value if self.state_machine else 'unknown',
            'is_running': self.is_running,
            'emergency_stop_active': self.emergency_stop_active
        }
        
        if self.sensor_fusion:
            status['localization'] = self.sensor_fusion.get_status()
        
        if self.state_machine:
            status['state_machine'] = self.state_machine.get_status()
        
        if self.event_bus:
            status['event_bus'] = self.event_bus.get_stats()
        
        return status


@asynccontextmanager
async def lifespan(app):
    """應用生命周期管理"""
    # 啟動
    robot = ImprovedRobotSystem()
    await robot.initialize()
    
    # 在背景啟動主控制循環
    main_task = asyncio.create_task(robot.start_main_loop())
    
    app.state.robot = robot
    
    yield
    
    # 關閉
    await robot.shutdown()
    main_task.cancel()
    try:
        await main_task
    except asyncio.CancelledError:
        pass


async def main():
    """主函數"""
    try:
        # 創建改進版機器人系統
        robot = ImprovedRobotSystem()
        
        # 設置信號處理
        def signal_handler(signum, frame):
            logger.info(f"收到信號 {signum}，準備關閉...")
            asyncio.create_task(robot.shutdown())
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # 初始化系統
        await robot.initialize()
        
        # 創建並啟動Web服務
        app = create_app(robot)
        
        # 啟動主控制循環和Web服務
        await asyncio.gather(
            robot.start_main_loop(),
            # uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
        )
        
    except KeyboardInterrupt:
        logger.info("用戶中斷，正在關閉...")
    except Exception as e:
        logger.error(f"系統運行異常: {e}")
    finally:
        if 'robot' in locals():
            await robot.shutdown()


if __name__ == "__main__":
    logger.info("🤖 啟動改進版樹莓派智能送貨機器人系統")
    asyncio.run(main())