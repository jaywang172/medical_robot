#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YOLO視覺系統模組
負責物體檢測、障礙物識別和視覺導航輔助
"""

import asyncio
import time
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import threading
from queue import Queue

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

from robot_core.utils.logger import ContextualLogger, log_ai_detection, log_performance


@dataclass
class Detection:
    """檢測結果"""
    class_id: int
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2)
    center: Tuple[int, int]  # (x, y)
    distance: Optional[float] = None  # 估計距離 (米)
    angle: Optional[float] = None     # 相對角度 (弧度)


@dataclass
class VisionData:
    """視覺數據"""
    detections: List[Detection]
    obstacles: List[Detection]  # 障礙物檢測
    frame: Optional[np.ndarray] = None
    processed_frame: Optional[np.ndarray] = None
    timestamp: float = 0.0
    processing_time: float = 0.0


class CameraManager:
    """相機管理器"""
    
    def __init__(self, camera_index: int = 0, width: int = 640, height: int = 480, fps: int = 30):
        self.logger = ContextualLogger("Camera")
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        
        self.cap = None
        self.is_opened = False
        self.frame_queue = Queue(maxsize=2)
        self.capture_thread = None
        self.stop_capture = False
        
    def initialize(self) -> bool:
        """初始化相機"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            
            if not self.cap.isOpened():
                self.logger.error(f"無法打開相機 {self.camera_index}")
                return False
            
            # 設置相機參數
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # 驗證設置
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            self.logger.info(f"相機初始化成功: {actual_width}x{actual_height}@{actual_fps:.1f}fps")
            
            self.is_opened = True
            return True
            
        except Exception as e:
            self.logger.error(f"相機初始化失敗: {e}")
            return False
    
    def start_capture(self):
        """開始捕獲線程"""
        if not self.is_opened:
            return False
        
        self.stop_capture = False
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
        self.logger.info("相機捕獲線程已啟動")
        return True
    
    def _capture_loop(self):
        """相機捕獲循環"""
        while not self.stop_capture and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            
            if ret:
                # 如果隊列滿了，丟棄舊幀
                if self.frame_queue.full():
                    try:
                        self.frame_queue.get_nowait()
                    except:
                        pass
                
                self.frame_queue.put(frame)
            else:
                self.logger.warning("相機讀取失敗")
                time.sleep(0.1)
    
    def get_frame(self) -> Optional[np.ndarray]:
        """獲取最新幀"""
        try:
            return self.frame_queue.get_nowait()
        except:
            return None
    
    def stop_capture_thread(self):
        """停止捕獲線程"""
        self.stop_capture = True
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
    
    def cleanup(self):
        """清理資源"""
        self.stop_capture_thread()
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.is_opened = False
        self.logger.info("相機資源已清理")


class YOLODetector:
    """YOLO檢測器"""
    
    def __init__(self, model_path: str, confidence_threshold: float = 0.5, iou_threshold: float = 0.45):
        self.logger = ContextualLogger("YOLO")
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.iou_threshold = iou_threshold
        
        self.model = None
        self.is_loaded = False
        
        # COCO類別名稱
        self.class_names = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck',
            'boat', 'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench',
            'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra',
            'giraffe', 'backpack', 'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee',
            'skis', 'snowboard', 'sports ball', 'kite', 'baseball bat', 'baseball glove',
            'skateboard', 'surfboard', 'tennis racket', 'bottle', 'wine glass', 'cup',
            'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple', 'sandwich', 'orange',
            'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair', 'couch',
            'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse',
            'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
            'toothbrush'
        ]
        
        # 障礙物類別
        self.obstacle_classes = {
            'person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck', 'chair', 'couch',
            'potted plant', 'bench', 'stop sign', 'fire hydrant'
        }
    
    def load_model(self) -> bool:
        """載入YOLO模型"""
        if not YOLO_AVAILABLE:
            self.logger.error("YOLO庫不可用，請安裝 ultralytics")
            return False
        
        try:
            model_path = Path(self.model_path)
            
            if not model_path.exists():
                self.logger.warning(f"模型文件不存在: {model_path}")
                self.logger.info("嘗試下載預訓練模型...")
                # 使用預訓練模型
                self.model = YOLO('yolov8n.pt')
            else:
                self.model = YOLO(str(model_path))
            
            # 測試模型
            dummy_input = np.zeros((640, 640, 3), dtype=np.uint8)
            _ = self.model(dummy_input, verbose=False)
            
            self.is_loaded = True
            self.logger.info(f"YOLO模型載入成功: {self.model_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"載入YOLO模型失敗: {e}")
            return False
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """執行物體檢測"""
        if not self.is_loaded or frame is None:
            return []
        
        try:
            start_time = time.time()
            
            # 執行推理
            results = self.model(
                frame,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                verbose=False
            )
            
            detections = []
            if results and len(results) > 0:
                result = results[0]
                
                if result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    class_ids = result.boxes.cls.cpu().numpy().astype(int)
                    
                    for i, (box, conf, class_id) in enumerate(zip(boxes, confidences, class_ids)):
                        x1, y1, x2, y2 = box.astype(int)
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2
                        
                        class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"unknown_{class_id}"
                        
                        # 估計距離 (簡單的基於框大小的估計)
                        box_area = (x2 - x1) * (y2 - y1)
                        estimated_distance = self._estimate_distance(box_area, class_name)
                        
                        # 計算相對角度
                        frame_center_x = frame.shape[1] // 2
                        angle = self._calculate_angle(center_x - frame_center_x, frame.shape[1])
                        
                        detection = Detection(
                            class_id=class_id,
                            class_name=class_name,
                            confidence=float(conf),
                            bbox=(x1, y1, x2, y2),
                            center=(center_x, center_y),
                            distance=estimated_distance,
                            angle=angle
                        )
                        
                        detections.append(detection)
            
            processing_time = time.time() - start_time
            
            # 記錄檢測結果
            log_ai_detection("YOLOv8", [
                {"class": d.class_name, "confidence": d.confidence} 
                for d in detections
            ], processing_time)
            
            return detections
            
        except Exception as e:
            self.logger.error(f"YOLO檢測失敗: {e}")
            return []
    
    def _estimate_distance(self, box_area: float, class_name: str) -> float:
        """估計物體距離"""
        # 這是一個簡化的距離估計，實際應用中需要校準
        # 基於物體類別和框大小的經驗公式
        
        reference_areas = {
            'person': 50000,    # 1米距離時的大概面積
            'chair': 30000,
            'car': 80000,
            'bicycle': 40000
        }
        
        reference_area = reference_areas.get(class_name, 40000)
        
        if box_area > 0:
            # 簡單的反比例關係
            distance = (reference_area / box_area) ** 0.5
            return max(0.3, min(10.0, distance))  # 限制在合理範圍內
        
        return 5.0  # 默認距離
    
    def _calculate_angle(self, x_offset: int, frame_width: int) -> float:
        """計算相對角度"""
        # 假設相機視角為60度
        fov = np.radians(60)
        angle = (x_offset / frame_width) * fov
        return angle


class VisionSystem:
    """視覺系統主控制類"""
    
    def __init__(self, config):
        self.config = config
        self.logger = ContextualLogger("VisionSystem")
        
        # 初始化組件
        self.camera = CameraManager(
            config.camera_index,
            config.camera_width,
            config.camera_height,
            config.camera_fps
        )
        
        self.detector = YOLODetector(
            config.yolo_model_path,
            config.confidence_threshold,
            config.iou_threshold
        )
        
        self.frame_skip_counter = 0
        self.last_vision_data = None
        
    async def initialize(self):
        """初始化視覺系統"""
        start_time = time.time()
        
        try:
            # 初始化相機
            if not self.camera.initialize():
                raise Exception("相機初始化失敗")
            
            # 載入YOLO模型
            if not self.detector.load_model():
                raise Exception("YOLO模型載入失敗")
            
            # 開始相機捕獲
            if not self.camera.start_capture():
                raise Exception("相機捕獲啟動失敗")
            
            # 等待第一幀
            await asyncio.sleep(0.5)
            
            self.logger.info("視覺系統初始化成功")
            
        except Exception as e:
            self.logger.error(f"視覺系統初始化失敗: {e}")
            raise
        
        finally:
            duration = time.time() - start_time
            log_performance("vision_system_init", duration)
    
    async def process_frame(self) -> VisionData:
        """處理一幀圖像"""
        start_time = time.time()
        timestamp = time.time()
        
        try:
            # 獲取最新幀
            frame = self.camera.get_frame()
            
            if frame is None:
                # 返回上次的數據
                if self.last_vision_data:
                    return self.last_vision_data
                else:
                    return VisionData([], [], timestamp=timestamp)
            
            # 跳幀處理
            self.frame_skip_counter += 1
            if self.frame_skip_counter < self.config.frame_skip:
                if self.last_vision_data:
                    return self.last_vision_data
                else:
                    return VisionData([], [], frame=frame, timestamp=timestamp)
            
            self.frame_skip_counter = 0
            
            # 執行檢測
            detections = self.detector.detect(frame)
            
            # 篩選障礙物
            obstacles = [
                det for det in detections 
                if det.class_name in self.detector.obstacle_classes
            ]
            
            # 繪製檢測結果
            processed_frame = self._draw_detections(frame.copy(), detections)
            
            processing_time = time.time() - start_time
            
            vision_data = VisionData(
                detections=detections,
                obstacles=obstacles,
                frame=frame,
                processed_frame=processed_frame,
                timestamp=timestamp,
                processing_time=processing_time
            )
            
            self.last_vision_data = vision_data
            return vision_data
            
        except Exception as e:
            self.logger.error(f"圖像處理失敗: {e}")
            return VisionData([], [], timestamp=timestamp)
    
    def _draw_detections(self, frame: np.ndarray, detections: List[Detection]) -> np.ndarray:
        """在圖像上繪製檢測結果"""
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            
            # 選擇顏色
            if detection.class_name in self.detector.obstacle_classes:
                color = (0, 0, 255)  # 紅色 - 障礙物
            else:
                color = (0, 255, 0)  # 綠色 - 其他物體
            
            # 繪製邊界框
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            
            # 繪製標籤
            label = f"{detection.class_name}: {detection.confidence:.2f}"
            if detection.distance:
                label += f" ({detection.distance:.1f}m)"
            
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(frame, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), color, -1)
            cv2.putText(frame, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
            # 繪製中心點
            cv2.circle(frame, detection.center, 3, color, -1)
        
        # 繪製十字線
        height, width = frame.shape[:2]
        cv2.line(frame, (width//2, 0), (width//2, height), (255, 255, 255), 1)
        cv2.line(frame, (0, height//2), (width, height//2), (255, 255, 255), 1)
        
        return frame
    
    def get_obstacles_in_path(self, path_width: float = 0.5) -> List[Detection]:
        """獲取路徑中的障礙物"""
        if not self.last_vision_data:
            return []
        
        obstacles_in_path = []
        for obstacle in self.last_vision_data.obstacles:
            # 檢查是否在前進路徑中
            if obstacle.angle is not None and abs(obstacle.angle) < np.radians(30):
                if obstacle.distance is not None and obstacle.distance < 3.0:
                    obstacles_in_path.append(obstacle)
        
        return obstacles_in_path
    
    def get_status(self) -> Dict:
        """獲取視覺系統狀態"""
        return {
            "camera": {
                "is_opened": self.camera.is_opened,
                "resolution": f"{self.camera.width}x{self.camera.height}",
                "fps": self.camera.fps
            },
            "detector": {
                "is_loaded": self.detector.is_loaded,
                "model_path": self.detector.model_path,
                "confidence_threshold": self.detector.confidence_threshold
            },
            "last_detections": len(self.last_vision_data.detections) if self.last_vision_data else 0,
            "last_obstacles": len(self.last_vision_data.obstacles) if self.last_vision_data else 0,
            "last_processing_time": self.last_vision_data.processing_time if self.last_vision_data else 0
        }
    
    async def cleanup(self):
        """清理資源"""
        self.camera.cleanup()
        self.logger.info("視覺系統已清理") 