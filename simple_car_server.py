#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡化版車輛控制服務器
只保留核心車輛控制功能，用於前端測試
"""

import asyncio
import uvicorn
import time
import base64
import io
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from robot_core.hardware.car_run_turn import create_car_controller, CarRunTurnController
from typing import Optional

# 嘗試導入圖像處理庫
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 嘗試導入攝像頭庫
try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

# 嘗試導入樹莓派專用攝像頭庫
try:
    from picamera2 import Picamera2
    import numpy as np
    PICAMERA2_AVAILABLE = True
    print("✅ picamera2 可用 - 樹莓派原生攝像頭支持")
except ImportError:
    PICAMERA2_AVAILABLE = False

try:
    import picamera
    import picamera.array
    PICAMERA_AVAILABLE = True
    print("✅ 舊版 picamera 可用")
except ImportError:
    PICAMERA_AVAILABLE = False

# 全域攝像頭實例
camera_cap = None
picam2_instance = None

def initialize_picamera2():
    """初始化 picamera2"""
    global picam2_instance
    
    if not PICAMERA2_AVAILABLE:
        return False
    
    try:
        print("🔍 嘗試初始化 picamera2...")
        picam2_instance = Picamera2()
        
        # 配置攝像頭
        config = picam2_instance.create_still_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        picam2_instance.configure(config)
        
        # 啟動攝像頭
        picam2_instance.start()
        print("✅ picamera2 啟動成功")
        
        # 等待攝像頭穩定
        import time
        time.sleep(2)
        
        # 測試捕獲
        image = picam2_instance.capture_array()
        print(f"✅ picamera2 初始化成功，畫面大小: {image.shape}")
        return True
        
    except Exception as e:
        print(f"❌ picamera2 初始化失敗: {e}")
        if picam2_instance:
            try:
                picam2_instance.stop()
            except:
                pass
            picam2_instance = None
        return False

def initialize_opencv_camera():
    """初始化 OpenCV 攝像頭（降級選項）"""
    global camera_cap
    
    if not OPENCV_AVAILABLE:
        return False
    
    # 嘗試多個攝像頭索引和後端
    camera_indices = [0, 1, 2]
    backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
    
    for backend in backends:
        for index in camera_indices:
            try:
                print(f"🔍 嘗試 OpenCV 攝像頭 {index} (後端: {backend})")
                camera_cap = cv2.VideoCapture(index, backend)
                
                if not camera_cap.isOpened():
                    if camera_cap:
                        camera_cap.release()
                    continue
                
                # 設置攝像頭參數
                camera_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                camera_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                camera_cap.set(cv2.CAP_PROP_FPS, 10)
                camera_cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # 測試捕獲
                import time
                time.sleep(0.5)
                success = False
                for attempt in range(5):
                    ret, frame = camera_cap.read()
                    if ret and frame is not None:
                        print(f"✅ OpenCV 攝像頭 {index} 初始化成功，畫面大小: {frame.shape}")
                        success = True
                        break
                    time.sleep(0.1)
                
                if success:
                    return True
                else:
                    camera_cap.release()
                    camera_cap = None
                
            except Exception as e:
                print(f"❌ OpenCV 攝像頭 {index} 錯誤: {e}")
                if camera_cap:
                    camera_cap.release()
                    camera_cap = None
    
    return False

def initialize_camera():
    """初始化攝像頭 - 按優先級嘗試不同庫"""
    print("📹 正在初始化攝像頭...")
    
    # 優先嘗試 picamera2 (樹莓派官方推薦)
    if initialize_picamera2():
        print("✅ 使用 picamera2 成功")
        return True
    
    # 降級到 OpenCV
    if initialize_opencv_camera():
        print("✅ 使用 OpenCV 成功")
        return True
    
    print("⚠️ 所有攝像頭庫都無法使用，將使用模擬圖像")
    return False

def capture_picamera2_frame():
    """使用 picamera2 捕獲畫面"""
    global picam2_instance
    
    if not picam2_instance:
        return None
    
    try:
        # 捕獲 RGB 陣列
        image = picam2_instance.capture_array()
        
        # 轉換為 JPEG
        if OPENCV_AVAILABLE:
            # 使用 OpenCV 編碼
            _, buffer = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 85])
            img_base64 = base64.b64encode(buffer).decode('utf-8')
        else:
            # 使用 PIL 編碼
            from PIL import Image as PILImage
            pil_image = PILImage.fromarray(image)
            import io
            buffer = io.BytesIO()
            pil_image.save(buffer, format='JPEG', quality=85)
            img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/jpeg;base64,{img_base64}"
        
    except Exception as e:
        print(f"❌ picamera2 捕獲錯誤: {e}")
        return None

def capture_opencv_frame():
    """使用 OpenCV 捕獲畫面"""
    global camera_cap
    
    if not camera_cap:
        return None
    
    try:
        # 嘗試多次捕獲
        for attempt in range(3):
            ret, frame = camera_cap.read()
            if ret and frame is not None:
                # 轉換為base64
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
                _, buffer = cv2.imencode('.jpg', frame, encode_param)
                img_base64 = base64.b64encode(buffer).decode('utf-8')
                return f"data:image/jpeg;base64,{img_base64}"
        
        print("⚠️ OpenCV 攝像頭捕獲失敗")
        return None
        
    except Exception as e:
        print(f"❌ OpenCV 攝像頭捕獲錯誤: {e}")
        return None

def capture_real_camera_frame():
    """從真實攝像頭捕獲畫面 - 自動選擇最佳方法"""
    # 優先使用 picamera2
    if picam2_instance:
        return capture_picamera2_frame()
    
    # 降級到 OpenCV
    if camera_cap:
        return capture_opencv_frame()
    
    return None

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

class VisionStreamResponse(BaseModel):
    image: str  # base64編碼的圖像
    timestamp: float
    detections: int
    obstacles: int
    processing_time: float

# 創建FastAPI應用
app = FastAPI(
    title="🚗 簡化版樹莓派車輛控制API",
    description="核心車輛控制和前端測試",
    version="1.0.0",
    lifespan=lifespan
)

# CORS設置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 創建FastAPI應用 (先定義再使用)
app = None

# 全域車輛控制器
car_controller: Optional[CarRunTurnController] = None

@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    """FastAPI 應用生命周期管理"""
    global car_controller, camera_cap, picam2_instance
    
    # 啟動時初始化
    print("🚀 應用啟動中...")
    
    # 檢查是否有 --hardware 參數來決定模式
    import sys
    simulation_mode = "--hardware" not in sys.argv
    
    try:
        car_controller = await create_car_controller(simulation=simulation_mode)
        print(f"🚗 車輛控制器已初始化 - {'硬件模式' if not simulation_mode else '模擬模式'}")
        
        # 硬件模式下初始化攝像頭
        if not simulation_mode:
            print("📹 正在初始化攝像頭...")
            camera_success = initialize_camera()
            if not camera_success:
                print("⚠️ 攝像頭無法捕獲畫面，將使用模擬圖像")
        else:
            print("⚠️ 攝像頭無法捕獲畫面，將使用模擬圖像")
    except Exception as e:
        print(f"❌ 初始化錯誤: {e}")
    
    yield  # 應用運行期間
    
    # 關閉時清理資源
    print("🛑 應用關閉中...")
    
    if car_controller:
        car_controller.cleanup()
        print("🧹 車輛控制器已清理")
    
    if picam2_instance:
        try:
            picam2_instance.stop()
            print("🧹 picamera2 已清理")
        except:
            pass
        picam2_instance = None
    
    if camera_cap:
        camera_cap.release()
        print("🧹 OpenCV 攝像頭已清理")
        camera_cap = None

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


# ===== 視覺流相關函數 =====

def generate_demo_image():
    """生成攝像頭圖像 - 優先使用真實攝像頭"""
    # 首先嘗試使用真實攝像頭
    real_frame = capture_real_camera_frame()
    if real_frame:
        return real_frame
    
    # 如果真實攝像頭不可用，使用模擬圖像
    if not PIL_AVAILABLE:
        # 如果沒有PIL，創建SVG圖像
        car_status = car_controller.get_status() if car_controller else {}
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        
        svg_content = f'''<svg width="640" height="480" xmlns="http://www.w3.org/2000/svg">
            <rect width="640" height="480" fill="lightblue"/>
            <text x="50" y="50" font-family="Arial" font-size="20" fill="black">🚗 樹莓派車輛攝像頭</text>
            <text x="50" y="80" font-family="Arial" font-size="16" fill="black">⏰ 時間: {current_time}</text>
            <text x="50" y="110" font-family="Arial" font-size="16" fill="black">🎮 狀態: {car_status.get('current_direction', 'stop')}</text>
            <text x="50" y="140" font-family="Arial" font-size="16" fill="black">🚨 緊急停止: {'是' if car_status.get('emergency_stop') else '否'}</text>
            <text x="50" y="170" font-family="Arial" font-size="16" fill="black">💻 模式: {'模擬' if car_status.get('simulation_mode') else '硬件'}</text>
            <text x="50" y="220" font-family="Arial" font-size="18" fill="black">📹 實時視頻流測試</text>
            <text x="50" y="250" font-family="Arial" font-size="16" fill="black">🔧 模擬攝像頭畫面 (SVG版本)</text>
            <rect x="500" y="350" width="100" height="80" fill="none" stroke="black" stroke-width="2"/>
            <text x="520" y="395" font-family="Arial" font-size="30">🤖</text>
        </svg>'''
        
        svg_base64 = base64.b64encode(svg_content.encode()).decode()
        return f"data:image/svg+xml;base64,{svg_base64}"
    
    try:
        # 創建640x480的RGB圖像
        width, height = 640, 480
        image = Image.new('RGB', (width, height), color='lightblue')
        draw = ImageDraw.Draw(image)
        
        # 繪製一些模擬內容
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        car_status = car_controller.get_status() if car_controller else {}
        
        # 嘗試使用默認字體
        try:
            font = ImageFont.load_default()
        except:
            font = None
        
        # 繪製信息
        texts = [
            f"🚗 樹莓派車輛攝像頭",
            f"⏰ 時間: {current_time}",
            f"🎮 狀態: {car_status.get('current_direction', 'unknown')}",
            f"🚨 緊急停止: {'是' if car_status.get('emergency_stop') else '否'}",
            f"💻 模式: {'模擬' if car_status.get('simulation_mode') else '硬件'}",
            "",
            "📹 實時視頻流測試",
            "🔧 模擬攝像頭畫面"
        ]
        
        y_offset = 50
        for text in texts:
            draw.text((50, y_offset), text, fill='black', font=font)
            y_offset += 30
        
        # 繪製一個簡單的機器人圖形
        robot_x, robot_y = width - 150, height - 150
        draw.rectangle([robot_x, robot_y, robot_x + 100, robot_y + 80], outline='black', width=2)
        draw.text((robot_x + 20, robot_y + 30), "🤖", fill='black', font=font)
        
        # 繪製移動方向指示
        direction = car_status.get('current_direction', 'stop')
        if direction == 'forward':
            draw.polygon([(robot_x + 50, robot_y - 20), (robot_x + 30, robot_y), (robot_x + 70, robot_y)], fill='green')
        elif direction == 'backward':
            draw.polygon([(robot_x + 50, robot_y + 100), (robot_x + 30, robot_y + 80), (robot_x + 70, robot_y + 80)], fill='red')
        elif direction == 'turn_left':
            draw.polygon([(robot_x - 20, robot_y + 40), (robot_x, robot_y + 20), (robot_x, robot_y + 60)], fill='blue')
        elif direction == 'turn_right':
            draw.polygon([(robot_x + 120, robot_y + 40), (robot_x + 100, robot_y + 20), (robot_x + 100, robot_y + 60)], fill='blue')
        
        # 轉換為base64
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/jpeg;base64,{img_base64}"
        
    except Exception as e:
        print(f"生成模擬圖像失敗: {e}")
        return None

@app.get("/api/vision/stream")
async def get_vision_stream():
    """獲取視覺流 - 模擬攝像頭"""
    start_time = time.time()
    
    try:
        # 生成模擬圖像
        image_data = generate_demo_image()
        
        if not image_data:
            # 如果無法生成圖像，返回錯誤信息
            raise HTTPException(status_code=503, detail="模擬攝像頭不可用 - 請檢查PIL庫安裝")
        
        processing_time = (time.time() - start_time) * 1000  # 轉換為毫秒
        
        # 模擬檢測結果
        import random
        detections = random.randint(0, 5)
        obstacles = random.randint(0, 2)
        
        return VisionStreamResponse(
            image=image_data,
            timestamp=time.time(),
            detections=detections,
            obstacles=obstacles,
            processing_time=round(processing_time, 2)
        )
        
    except Exception as e:
        print(f"❌ 獲取視覺流失敗: {e}")
        raise HTTPException(status_code=500, detail=f"視覺流錯誤: {str(e)}")


if __name__ == "__main__":
    import sys
    
    print("🚗 啟動簡化版樹莓派車輛控制服務器")
    print("💡 使用方式:")
    print("   模擬模式: python simple_car_server.py")
    print("   硬件模式: python simple_car_server.py --hardware")
    print("📡 API地址: http://localhost:8000")
    print("📊 API文檔: http://localhost:8000/docs")
    print("📹 視覺流: http://localhost:8000/api/vision/stream (模擬攝像頭)")
    
    # 運行服務器
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
