#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
樹莓派智能送貨機器人 - 主程序入口
主要功能：
- 初始化硬體模組
- 啟動AI視覺系統
- 開啟Web API服務
- 協調各模組運作
"""

import asyncio
import signal
import sys
from pathlib import Path
from loguru import logger
from contextlib import asynccontextmanager

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


class RobotSystem:
    """機器人系統主控制類"""
    
    def __init__(self):
        self.config = RobotConfig()
        self.motor_controller = None
        self.sensor_manager = None
        self.vision_system = None
        self.path_planner = None
        self.is_running = False
        
        # 設置日誌
        setup_logger(self.config.log_level)
        logger.info("🤖 初始化機器人系統...")
    
    async def initialize(self):
        """初始化所有系統組件"""
        try:
            logger.info("📡 初始化硬體控制模組...")
            self.motor_controller = MotorController(self.config.motor_config)
            await self.motor_controller.initialize()
            
            logger.info("🔍 初始化感測器管理器...")
            self.sensor_manager = SensorManager(self.config.sensor_config)
            await self.sensor_manager.initialize()
            
            logger.info("👁️ 初始化AI視覺系統...")
            self.vision_system = VisionSystem(self.config.vision_config)
            await self.vision_system.initialize()
            
            logger.info("🗺️ 初始化路徑規劃器...")
            self.path_planner = PathPlanner(self.config.navigation_config)
            await self.path_planner.initialize()
            
            # 引用地圖管理器
            self.map_manager = self.path_planner.map_manager
            
            self.is_running = True
            logger.success("✅ 所有系統組件初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 系統初始化失敗: {e}")
            raise
    
    async def start_main_loop(self):
        """啟動主控制循環"""
        logger.info("🚀 啟動機器人主控制循環...")
        
        while self.is_running:
            try:
                # 獲取感測器數據
                sensor_data = await self.sensor_manager.get_all_data()
                
                # 處理視覺數據
                vision_data = await self.vision_system.process_frame()
                
                # 更新路徑規劃
                if vision_data.get('obstacles'):
                    await self.path_planner.update_obstacles(vision_data['obstacles'])
                
                # 執行導航決策
                navigation_command = await self.path_planner.get_next_move(
                    sensor_data, vision_data
                )
                
                # 執行電機控制
                if navigation_command:
                    await self.motor_controller.execute_command(navigation_command)
                
                # 控制循環頻率
                await asyncio.sleep(self.config.main_loop_interval)
                
            except Exception as e:
                logger.error(f"⚠️ 主控制循環異常: {e}")
                await asyncio.sleep(1.0)
    
    async def shutdown(self):
        """優雅關閉系統"""
        logger.info("🛑 正在關閉機器人系統...")
        self.is_running = False
        
        if self.motor_controller:
            await self.motor_controller.stop_all()
            
        if self.sensor_manager:
            await self.sensor_manager.cleanup()
            
        if self.vision_system:
            await self.vision_system.cleanup()
            
        logger.info("✅ 系統已安全關閉")


@asynccontextmanager
async def lifespan(app):
    """應用生命周期管理"""
    # 啟動
    robot = RobotSystem()
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
        # 創建機器人系統
        robot = RobotSystem()
        
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
    logger.info("🤖 啟動樹莓派智能送貨機器人系統")
    asyncio.run(main()) 