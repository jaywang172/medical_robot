#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
樹莓派服務器啟動腳本
解決模組導入問題並提供完整的服務器功能
"""

import sys
import os
import asyncio
from pathlib import Path

# 添加項目根目錄到 Python 路徑
PROJECT_ROOT = Path(__file__).parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

print(f"🍓 樹莓派機器人控制服務器")
print(f"📁 項目路徑: {PROJECT_ROOT}")

try:
    # 嘗試導入必要的模組
    import uvicorn
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    print("✅ FastAPI 和 uvicorn 可用")
except ImportError as e:
    print(f"❌ 缺少必要依賴: {e}")
    print("請執行: pip install fastapi uvicorn websockets aiofiles pydantic")
    sys.exit(1)

# 檢查樹莓派 GPIO
try:
    import RPi.GPIO as GPIO
    PI_AVAILABLE = True
    print("✅ 樹莓派 GPIO 可用")
except ImportError:
    PI_AVAILABLE = False
    print("⚠️  運行在模擬模式 (非樹莓派環境)")

async def create_minimal_app():
    """創建最小化的 FastAPI 應用"""
    
    app = FastAPI(
        title="樹莓派機器人控制API",
        description="車輛控制和監控API",
        version="1.0.0"
    )
    
    # CORS 設置
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生產環境中應限制具體域名
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 導入車輛控制器
    try:
        from robot_core.state_machine.car_run_turn import CarRunTurnController
        car_controller = CarRunTurnController(simulation=not PI_AVAILABLE)
        print(f"✅ 車輛控制器已初始化 - {'硬件模式' if PI_AVAILABLE else '模擬模式'}")
    except Exception as e:
        print(f"❌ 車輛控制器初始化失敗: {e}")
        # 創建備用控制器
        car_controller = None
    
    @app.get("/")
    async def root():
        return {
            "message": "樹莓派機器人控制API",
            "status": "running",
            "mode": "hardware" if PI_AVAILABLE else "simulation",
            "car_controller": "available" if car_controller else "unavailable"
        }
    
    @app.get("/api/status")
    async def get_status():
        return {
            "system": {
                "is_running": True,
                "mode": "hardware" if PI_AVAILABLE else "simulation"
            },
            "car_controller": {
                "available": car_controller is not None,
                "status": car_controller.get_status() if car_controller else None
            }
        }
    
    # 車輛控制端點
    @app.post("/api/car/control")
    async def car_control(action: str, duration: float = 0.5):
        if not car_controller:
            return {"success": False, "message": "車輛控制器不可用"}
        
        try:
            if action == "forward":
                await car_controller.forward(duration)
            elif action == "backward":
                await car_controller.backward(duration)
            elif action == "turn_left":
                await car_controller.turn_left(duration)
            elif action == "turn_right":
                await car_controller.turn_right(duration)
            elif action == "stop":
                await car_controller.stop()
            elif action == "emergency_stop":
                await car_controller.emergency_stop()
            else:
                return {"success": False, "message": f"不支援的動作: {action}"}
            
            return {
                "success": True,
                "message": f"動作 {action} 執行成功",
                "status": car_controller.get_status()
            }
        except Exception as e:
            return {"success": False, "message": f"執行失敗: {str(e)}"}
    
    @app.get("/api/car/status")
    async def get_car_status():
        if not car_controller:
            return {"error": "車輛控制器不可用"}
        return car_controller.get_status()
    
    @app.post("/api/car/emergency_reset")
    async def reset_emergency():
        if not car_controller:
            return {"success": False, "message": "車輛控制器不可用"}
        
        car_controller.reset_emergency_stop()
        return {
            "success": True,
            "message": "緊急停止已重置",
            "status": car_controller.get_status()
        }
    
    return app

def main():
    """主程序"""
    
    # 顯示網絡信息
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"🌐 主機名: {hostname}")
        print(f"🌐 本地IP: {local_ip}")
    except Exception:
        print("🌐 無法獲取網絡信息")
    
    # 檢查端口
    port = 8000
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        if result == 0:
            print(f"⚠️  端口 {port} 已被占用")
            port = 8001
            print(f"🔄 改用端口 {port}")
    except Exception:
        pass
    
    print(f"\n🚀 啟動服務器...")
    print(f"📡 API地址: http://localhost:{port}")
    print(f"📡 API地址: http://{local_ip if 'local_ip' in locals() else '樹莓派IP'}:{port}")
    print(f"📖 API文檔: http://localhost:{port}/docs")
    print("\n按 Ctrl+C 停止服務器")
    
    # 創建並運行應用
    app = asyncio.run(create_minimal_app())
    
    # 啟動服務器
    uvicorn.run(
        app,
        host="0.0.0.0",  # 允許外部連接
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 服務器已停止")
    except Exception as e:
        print(f"\n💥 啟動失敗: {e}")
        import traceback
        traceback.print_exc()
