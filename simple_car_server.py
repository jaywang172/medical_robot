#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡化版車輛控制服務器
只保留核心車輛控制功能，用於前端測試
"""

import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from robot_core.hardware.car_run_turn import create_car_controller, CarRunTurnController
from typing import Optional

# 請求模型
class CarControlRequest(BaseModel):
    action: str  # forward, backward, turn_left, turn_right, stop, emergency_stop
    duration: float = 0.5

class CarStatusResponse(BaseModel):
    is_moving: bool
    current_direction: str
    last_command_time: float
    emergency_stop: bool
    simulation_mode: bool

# 創建FastAPI應用
app = FastAPI(
    title="🚗 簡化版樹莓派車輛控制API",
    description="核心車輛控制和前端測試",
    version="1.0.0"
)

# CORS設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全域車輛控制器
car_controller: Optional[CarRunTurnController] = None

@app.on_event("startup")
async def startup_event():
    """啟動時初始化車輛控制器"""
    global car_controller
    
    # 檢查是否有 --hardware 參數來決定模式
    import sys
    simulation_mode = "--hardware" not in sys.argv
    
    car_controller = await create_car_controller(simulation=simulation_mode)
    print(f"🚗 車輛控制器已初始化 - {'硬件模式' if not simulation_mode else '模擬模式'}")

@app.on_event("shutdown")
async def shutdown_event():
    """關閉時清理資源"""
    if car_controller:
        car_controller.cleanup()
        print("🧹 車輛控制器已清理")

@app.get("/")
async def root():
    """根端點"""
    return {
        "message": "🚗 簡化版樹莓派車輛控制API",
        "status": "running",
        "mode": "hardware" if car_controller and not car_controller.simulation else "simulation"
    }

@app.post("/api/car/control")
async def car_control(request: CarControlRequest):
    """核心車輛控制API"""
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
        print(f"❌ 車輛控制失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/car/status")
async def get_car_status():
    """獲取車輛狀態"""
    if not car_controller:
        raise HTTPException(status_code=503, detail="車輛控制器未初始化")
    
    try:
        status = car_controller.get_status()
        return CarStatusResponse(**status)
    except Exception as e:
        print(f"❌ 獲取車輛狀態失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/car/emergency_reset")
async def reset_car_emergency():
    """重置緊急停止狀態"""
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
        print(f"❌ 重置緊急停止失敗: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/car/test")
async def test_car_controller():
    """測試車輛控制器"""
    if not car_controller:
        raise HTTPException(status_code=503, detail="車輛控制器未初始化")
    
    try:
        print("🔧 開始車輛控制器測試序列")
        
        # 簡單測試序列
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
        print(f"❌ 車輛控制器測試失敗: {e}")
        # 確保測試失敗時停止
        if car_controller:
            await car_controller.emergency_stop()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import sys
    
    print("🚗 啟動簡化版樹莓派車輛控制服務器")
    print("💡 使用方式:")
    print("   模擬模式: python simple_car_server.py")
    print("   硬件模式: python simple_car_server.py --hardware")
    print("📡 API地址: http://localhost:8000")
    print("📊 API文檔: http://localhost:8000/docs")
    
    # 運行服務器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
