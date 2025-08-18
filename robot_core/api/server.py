#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FastAPI服務器模組
提供機器人控制和監控的Web API介面
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
import base64
import cv2
import numpy as np
import io

from fastapi import FastAPI, WebSocket, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn

from robot_core.utils.logger import ContextualLogger
from robot_core.navigation.path_planner import Point, NavigationCommand
from robot_core.hardware.motor_controller import MotorCommand
from robot_core.navigation.polycam_processor import PolycamProcessor
from robot_core.hardware.car_run_turn import CarRunTurnController, create_car_controller


# 數據模型
class GoalRequest(BaseModel):
    x: float
    y: float


class ManualControlRequest(BaseModel):
    linear_speed: float  # -1.0 到 1.0
    angular_speed: float  # -1.0 到 1.0
    duration: float = 0.0


class CarControlRequest(BaseModel):
    """核心車輛控制請求"""
    action: str  # forward, backward, turn_left, turn_right, stop, emergency_stop
    duration: float = 0.5  # 持續時間


class CarStatusResponse(BaseModel):
    """車輛狀態響應"""
    is_moving: bool
    current_direction: str
    last_command_time: float
    emergency_stop: bool
    simulation_mode: bool


class ConfigUpdateRequest(BaseModel):
    section: str
    key: str
    value: float


class MapUploadResponse(BaseModel):
    success: bool
    message: str
    map_id: Optional[str] = None

class MapListResponse(BaseModel):
    maps: list
    count: int

class MapSelectionRequest(BaseModel):
    map_id: str


class WebSocketManager:
    """WebSocket連接管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.robot_system = None
        self.logger = ContextualLogger("WebSocketManager")
    
    async def connect(self, websocket: WebSocket):
        """接受WebSocket連接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.logger.info(f"WebSocket連接建立，當前連接數: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """斷開WebSocket連接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.logger.info(f"WebSocket連接斷開，當前連接數: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """發送個人消息"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            self.logger.warning(f"發送個人消息失敗: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """廣播消息給所有連接"""
        if not self.active_connections:
            return
        
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                self.logger.warning(f"廣播消息失敗: {e}")
                disconnected.append(connection)
        
        # 清理斷開的連接
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_json(self, data: dict):
        """廣播JSON數據"""
        await self.broadcast(json.dumps(data))

    def set_robot_system(self, robot_system):
        self.robot_system = robot_system


def create_app(robot_system=None):
    """創建FastAPI應用"""
    
    app = FastAPI(
        title="樹莓派智能送貨機器人API",
        description="機器人控制和監控API",
        version="1.0.0"
    )
    
    # CORS中間件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生產環境中應該限制具體域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # WebSocket管理器
    websocket_manager = WebSocketManager()
    websocket_manager.set_robot_system(robot_system)
    
    # 核心車輛控制器實例
    car_controller: Optional[CarRunTurnController] = None
    
    # 靜態文件
    # app.mount("/static", StaticFiles(directory="web_demo/build"), name="static")
    
    logger = ContextualLogger("APIServer")
    
    # 後台任務：定期廣播機器人狀態
    async def broadcast_robot_status():
        """定期廣播機器人狀態"""
        while True:
            try:
                if robot_system and websocket_manager.active_connections:
                    status_data = await get_robot_status()
                    await websocket_manager.broadcast_json({
                        "type": "status_update",
                        "data": status_data
                    })
                
                await asyncio.sleep(1.0)  # 每秒更新一次
                
            except Exception as e:
                logger.error(f"廣播狀態失敗: {e}")
                await asyncio.sleep(5.0)
    
    # 啟動後台任務
    @app.on_event("startup")
    async def startup_event():
        # 初始化車輛控制器
        nonlocal car_controller
        simulation_mode = not robot_system or getattr(robot_system.config, 'simulation', False)
        car_controller = await create_car_controller(simulation=simulation_mode)
        logger.info(f"車輛控制器已初始化 - {'模擬模式' if simulation_mode else '硬件模式'}")
        
        # 啟動狀態廣播
        asyncio.create_task(broadcast_robot_status())
    
    @app.on_event("shutdown")
    async def shutdown_event():
        # 清理車輛控制器
        if car_controller:
            car_controller.cleanup()
            logger.info("車輛控制器已清理")
    
    # WebSocket端點
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket_manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 處理不同類型的WebSocket消息
                if message.get("type") == "ping":
                    await websocket_manager.send_personal_message(
                        json.dumps({"type": "pong"}), websocket
                    )
                elif message.get("type") == "manual_control":
                    # 手動控制
                    if robot_system and robot_system.motor_controller:
                        cmd_data = message.get("data", {})
                        command = MotorCommand(
                            left_speed=cmd_data.get("left_speed", 0) * 100,
                            right_speed=cmd_data.get("right_speed", 0) * 100,
                            duration=cmd_data.get("duration", 0)
                        )
                        await robot_system.motor_controller.execute_command(command)
                
        except Exception as e:
            logger.warning(f"WebSocket錯誤: {e}")
        finally:
            websocket_manager.disconnect(websocket)
    
    # API端點
    @app.get("/")
    async def read_root():
        """根端點"""
        return {"message": "樹莓派智能送貨機器人API", "status": "running"}
    
    async def get_robot_status():
        """獲取機器人綜合狀態"""
        if not robot_system:
            return {"error": "機器人系統未初始化"}
        
        try:
            status = {
                "timestamp": time.time(),
                "system": {
                    "is_running": robot_system.is_running,
                    "main_loop_interval": robot_system.config.main_loop_interval
                }
            }
            
            # 電機狀態
            if robot_system.motor_controller:
                status["motor"] = robot_system.motor_controller.get_status()
            
            # 感測器狀態
            if robot_system.sensor_manager:
                status["sensors"] = robot_system.sensor_manager.get_status()
            
            # 視覺系統狀態
            if robot_system.vision_system:
                status["vision"] = robot_system.vision_system.get_status()
            
            # 導航狀態
            if robot_system.path_planner:
                status["navigation"] = robot_system.path_planner.get_status()
            
            return status
            
        except Exception as e:
            logger.error(f"獲取機器人狀態失敗: {e}")
            return {"error": str(e)}
    
    @app.get("/api/status")
    async def api_get_status():
        """獲取機器人狀態"""
        status = await get_robot_status()
        return JSONResponse(status)
    
    @app.get("/api/config")
    async def get_config():
        """獲取機器人配置"""
        if not robot_system:
            raise HTTPException(status_code=503, detail="機器人系統未初始化")
        
        return JSONResponse(robot_system.config.to_dict())
    
    @app.post("/api/navigation/goal")
    async def set_navigation_goal(goal: GoalRequest):
        """設置導航目標"""
        if not robot_system or not robot_system.path_planner:
            raise HTTPException(status_code=503, detail="導航系統未初始化")
        
        try:
            target_point = Point(goal.x, goal.y)
            success = await robot_system.path_planner.set_goal(target_point)
            
            if success:
                return {"success": True, "message": f"目標設置成功: ({goal.x}, {goal.y})"}
            else:
                return {"success": False, "message": "路徑規劃失敗"}
                
        except Exception as e:
            logger.error(f"設置導航目標失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/control/manual")
    async def manual_control(control: ManualControlRequest):
        """手動控制機器人"""
        if not robot_system or not robot_system.motor_controller:
            raise HTTPException(status_code=503, detail="電機控制系統未初始化")
        
        try:
            # 轉換為電機命令
            left_speed = control.linear_speed * 100 + control.angular_speed * 50
            right_speed = control.linear_speed * 100 - control.angular_speed * 50
            
            command = MotorCommand(left_speed, right_speed, control.duration)
            await robot_system.motor_controller.execute_command(command)
            
            return {"success": True, "message": "手動控制命令已執行"}
            
        except Exception as e:
            logger.error(f"手動控制失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/control/stop")
    async def stop_robot():
        """停止機器人"""
        if not robot_system or not robot_system.motor_controller:
            raise HTTPException(status_code=503, detail="電機控制系統未初始化")
        
        try:
            await robot_system.motor_controller.stop_all()
            return {"success": True, "message": "機器人已停止"}
            
        except Exception as e:
            logger.error(f"停止機器人失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/control/emergency_stop")
    async def emergency_stop():
        """緊急停止"""
        if not robot_system or not robot_system.motor_controller:
            raise HTTPException(status_code=503, detail="電機控制系統未初始化")
        
        try:
            await robot_system.motor_controller.emergency_stop_all()
            return {"success": True, "message": "緊急停止已激活"}
            
        except Exception as e:
            logger.error(f"緊急停止失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/control/reset_emergency")
    async def reset_emergency_stop():
        """重置緊急停止"""
        if not robot_system or not robot_system.motor_controller:
            raise HTTPException(status_code=503, detail="電機控制系統未初始化")
        
        try:
            robot_system.motor_controller.reset_emergency_stop()
            return {"success": True, "message": "緊急停止已重置"}
            
        except Exception as e:
            logger.error(f"重置緊急停止失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/vision/stream")
    async def get_vision_stream():
        """獲取視覺流（當前幀的base64編碼）"""
        if not robot_system or not robot_system.vision_system:
            raise HTTPException(status_code=503, detail="視覺系統未初始化")
        
        try:
            vision_data = robot_system.vision_system.last_vision_data
            
            if not vision_data or vision_data.processed_frame is None:
                raise HTTPException(status_code=404, detail="無可用影像")
            
            # 編碼圖像為JPEG
            _, buffer = cv2.imencode('.jpg', vision_data.processed_frame)
            img_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return {
                "image": f"data:image/jpeg;base64,{img_base64}",
                "timestamp": vision_data.timestamp,
                "detections": len(vision_data.detections),
                "obstacles": len(vision_data.obstacles),
                "processing_time": vision_data.processing_time
            }
            
        except Exception as e:
            logger.error(f"獲取視覺流失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/sensors/distances")
    async def get_sensor_distances():
        """獲取感測器距離數據"""
        if not robot_system or not robot_system.sensor_manager:
            raise HTTPException(status_code=503, detail="感測器系統未初始化")
        
        try:
            distances = await robot_system.sensor_manager.get_obstacle_distances()
            return {"distances": distances, "timestamp": time.time()}
            
        except Exception as e:
            logger.error(f"獲取感測器數據失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/navigation/path")
    async def get_current_path():
        """獲取當前路徑"""
        if not robot_system or not robot_system.path_planner:
            raise HTTPException(status_code=503, detail="導航系統未初始化")
        
        try:
            path = robot_system.path_planner.current_path
            path_data = [{"x": p.x, "y": p.y} for p in path] if path else []
            
            return {
                "path": path_data,
                "current_index": robot_system.path_planner.path_index,
                "total_points": len(path_data),
                "state": robot_system.path_planner.navigation_state.value
            }
            
        except Exception as e:
            logger.error(f"獲取路徑失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/config/update")
    async def update_config(config_update: ConfigUpdateRequest):
        """更新配置參數"""
        if not robot_system:
            raise HTTPException(status_code=503, detail="機器人系統未初始化")
        
        try:
            # 這裡可以添加配置更新邏輯
            # 暫時返回成功消息
            return {
                "success": True, 
                "message": f"配置 {config_update.section}.{config_update.key} 已更新為 {config_update.value}"
            }
            
        except Exception as e:
            logger.error(f"更新配置失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/system/shutdown")
    async def shutdown_system():
        """關閉系統"""
        if not robot_system:
            raise HTTPException(status_code=503, detail="機器人系統未初始化")
        
        try:
            # 觸發系統關閉
            asyncio.create_task(robot_system.shutdown())
            return {"success": True, "message": "系統正在安全關閉..."}
            
        except Exception as e:
            logger.error(f"關閉系統失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 測試端點
    @app.get("/api/test/motor")
    async def test_motor():
        """測試電機"""
        if not robot_system or not robot_system.motor_controller:
            raise HTTPException(status_code=503, detail="電機控制系統未初始化")
        
        try:
            # 執行簡單的測試序列
            await robot_system.motor_controller.move_forward(30, 1.0)
            await asyncio.sleep(0.5)
            await robot_system.motor_controller.turn_left(30, 1.0)
            await asyncio.sleep(0.5)
            await robot_system.motor_controller.move_backward(30, 1.0)
            await asyncio.sleep(0.5)
            await robot_system.motor_controller.turn_right(30, 1.0)
            await asyncio.sleep(0.5)
            await robot_system.motor_controller.stop_all()
            
            return {"success": True, "message": "電機測試完成"}
            
        except Exception as e:
            logger.error(f"電機測試失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # 核心車輛控制API端點
    @app.post("/api/car/control")
    async def car_control(request: CarControlRequest):
        """
        核心車輛控制 - 直接GPIO控制
        支援的動作: forward, backward, turn_left, turn_right, stop, emergency_stop
        """
        if not car_controller:
            raise HTTPException(status_code=503, detail="車輛控制器未初始化")
        
        try:
            action = request.action.lower()
            duration = request.duration
            
            if action == "forward":
                await car_controller.forward(duration)
                message = f"前進 {duration}秒"
            elif action == "backward":
                await car_controller.backward(duration)
                message = f"後退 {duration}秒"
            elif action == "turn_left":
                await car_controller.turn_left(duration)
                message = f"左轉 {duration}秒"
            elif action == "turn_right":
                await car_controller.turn_right(duration)
                message = f"右轉 {duration}秒"
            elif action == "stop":
                await car_controller.stop()
                message = "停止"
            elif action == "emergency_stop":
                await car_controller.emergency_stop()
                message = "緊急停止"
            else:
                raise HTTPException(status_code=400, detail=f"不支援的動作: {action}")
            
            return {
                "success": True, 
                "message": message,
                "status": car_controller.get_status()
            }
            
        except Exception as e:
            logger.error(f"車輛控制失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/car/status")
    async def get_car_status():
        """獲取車輛控制器狀態"""
        if not car_controller:
            raise HTTPException(status_code=503, detail="車輛控制器未初始化")
        
        try:
            status = car_controller.get_status()
            return CarStatusResponse(**status)
        except Exception as e:
            logger.error(f"獲取車輛狀態失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/car/emergency_reset")
    async def reset_car_emergency():
        """重置車輛緊急停止狀態"""
        if not car_controller:
            raise HTTPException(status_code=503, detail="車輛控制器未初始化")
        
        try:
            car_controller.reset_emergency_stop()
            return {
                "success": True,
                "message": "緊急停止狀態已重置",
                "status": car_controller.get_status()
            }
        except Exception as e:
            logger.error(f"重置緊急停止失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/car/test")
    async def test_car_controller():
        """測試核心車輛控制器"""
        if not car_controller:
            raise HTTPException(status_code=503, detail="車輛控制器未初始化")
        
        try:
            logger.info("開始車輛控制器測試序列")
            
            # 執行測試序列
            await car_controller.forward(0.5)
            await asyncio.sleep(0.2)
            await car_controller.turn_right(0.5)
            await asyncio.sleep(0.2)
            await car_controller.backward(0.5)
            await asyncio.sleep(0.2)
            await car_controller.turn_left(0.5)
            await asyncio.sleep(0.2)
            await car_controller.stop()
            
            return {
                "success": True,
                "message": "車輛控制器測試完成",
                "status": car_controller.get_status()
            }
            
        except Exception as e:
            logger.error(f"車輛控制器測試失敗: {e}")
            # 確保測試失敗時停止
            if car_controller:
                await car_controller.emergency_stop()
            raise HTTPException(status_code=500, detail=str(e))
    
    # 地圖管理API
    @app.post("/api/maps/upload")
    async def upload_map(file: UploadFile = File(...), name: str = Form(...), source: str = Form("polycam")):
        """上傳地圖數據（支持Polycam格式）"""
        if not robot_system:
            raise HTTPException(status_code=503, detail="機器人系統未初始化")
        
        try:
            # 檢查文件類型
            file_extension = file.filename.lower().split('.')[-1] if file.filename else ""
            
            if source == "polycam" and file_extension in ['ply', 'obj', 'xyz', 'pts', 'dxf', 'las', 'glb', 'usdz', 'dae', 'stl']:
                # 使用Polycam處理器處理文件
                polycam_processor = PolycamProcessor()
                
                # 保存臨時文件
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=f'.{file_extension}', delete=False) as tmp_file:
                    content = await file.read()
                    tmp_file.write(content)
                    tmp_file_path = tmp_file.name
                
                try:
                    # 處理Polycam文件
                    occupancy_map = await polycam_processor.process_polycam_file(tmp_file_path)
                    
                    # 將處理後的地圖保存到系統
                    map_data = {
                        "width": occupancy_map.width,
                        "height": occupancy_map.height,
                        "resolution": occupancy_map.resolution,
                        "origin": {"x": occupancy_map.origin_x, "y": occupancy_map.origin_y},
                        "data": occupancy_map.data.flatten().tolist(),
                        "metadata": occupancy_map.metadata
                    }
                    
                    map_bytes = json.dumps(map_data).encode('utf-8')
                    map_id = await robot_system.map_manager.save_map(map_bytes, name, source)
                    
                finally:
                    # 清理臨時文件
                    import os
                    if os.path.exists(tmp_file_path):
                        os.unlink(tmp_file_path)
                
            else:
                # 傳統JSON格式處理
                content = await file.read()
                map_id = await robot_system.map_manager.save_map(content, name, source)
            
            return MapUploadResponse(
                success=True,
                message="地圖上傳成功",
                map_id=map_id
            )
            
        except Exception as e:
            logger.error(f"地圖上傳失敗: {e}")
            return MapUploadResponse(
                success=False,
                message=f"地圖上傳失敗: {str(e)}"
            )
    
    @app.get("/api/maps")
    async def list_maps():
        """獲取地圖列表"""
        if not robot_system:
            raise HTTPException(status_code=503, detail="機器人系統未初始化")
        
        try:
            maps = await robot_system.map_manager.list_maps()
            return MapListResponse(maps=maps, count=len(maps))
        except Exception as e:
            logger.error(f"獲取地圖列表失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/maps/select")
    async def select_map(request: MapSelectionRequest):
        """選擇活動地圖"""
        if not robot_system:
            raise HTTPException(status_code=503, detail="機器人系統未初始化")
        
        try:
            success = await robot_system.map_manager.load_map(request.map_id)
            if success:
                # 更新路徑規劃器使用新地圖
                await robot_system.path_planner.update_map()
                return {"success": True, "message": f"地圖 {request.map_id} 已激活"}
            else:
                return {"success": False, "message": "地圖加載失敗"}
        except Exception as e:
            logger.error(f"選擇地圖失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.delete("/api/maps/{map_id}")
    async def delete_map(map_id: str):
        """刪除地圖"""
        if not robot_system:
            raise HTTPException(status_code=503, detail="機器人系統未初始化")
        
        try:
            success = await robot_system.map_manager.delete_map(map_id)
            if success:
                return {"success": True, "message": f"地圖 {map_id} 已刪除"}
            else:
                return {"success": False, "message": "地圖刪除失敗"}
        except Exception as e:
            logger.error(f"刪除地圖失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/maps/{map_id}/preview")
    async def get_map_preview(map_id: str):
        """獲取地圖預覽"""
        if not robot_system:
            raise HTTPException(status_code=503, detail="機器人系統未初始化")
        
        try:
            preview_data = await robot_system.map_manager.get_map_preview(map_id)
            if preview_data:
                return StreamingResponse(
                    io.BytesIO(preview_data),
                    media_type="image/png"
                )
            else:
                raise HTTPException(status_code=404, detail="地圖預覽不存在")
        except Exception as e:
            logger.error(f"獲取地圖預覽失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/polycam/guide")
    async def get_polycam_guide():
        """獲取Polycam使用指南"""
        try:
            guide = PolycamProcessor.get_polycam_workflow_guide()
            return guide
        except Exception as e:
            logger.error(f"獲取Polycam指南失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/polycam/dependencies")
    async def check_polycam_dependencies():
        """檢查Polycam處理所需的依賴"""
        try:
            from ..navigation.polycam_processor import check_dependencies, install_missing_dependencies
            
            deps = check_dependencies()
            missing_install_cmd = install_missing_dependencies()
            
            return {
                "dependencies": deps,
                "all_installed": all(deps.values()),
                "install_command": missing_install_cmd
            }
        except Exception as e:
            logger.error(f"檢查依賴失敗: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app


def run_server(robot_system=None, host="0.0.0.0", port=8000):
    """運行API服務器"""
    app = create_app(robot_system)
    
    config = uvicorn.Config(
        app, 
        host=host, 
        port=port, 
        log_level="info",
        access_log=True
    )
    
    server = uvicorn.Server(config)
    return server 