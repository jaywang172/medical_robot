#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import uuid
import asyncio
import shutil
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
import pickle
import gzip

import numpy as np
import cv2
from PIL import Image

from ..utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class MapInfo:
    """地圖信息"""
    id: str
    name: str
    created_at: datetime
    source: str  # "lidar", "slam", "manual"
    file_path: str
    preview_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "file_path": self.file_path,
            "preview_path": self.preview_path,
            "metadata": self.metadata or {}
        }

@dataclass
class OccupancyGridMap:
    """占用柵格地圖"""
    width: int
    height: int
    resolution: float  # 米/像素
    origin_x: float
    origin_y: float
    data: np.ndarray  # 占用狀態數組 (height, width)
    timestamp: datetime
    metadata: Dict[str, Any]
    
    def get_cell_value(self, x: int, y: int) -> int:
        """獲取指定位置的占用狀態"""
        if 0 <= y < self.height and 0 <= x < self.width:
            return int(self.data[y, x])
        return -1  # 未知
    
    def world_to_grid(self, world_x: float, world_y: float) -> Tuple[int, int]:
        """世界坐標轉柵格坐標"""
        grid_x = int((world_x - self.origin_x) / self.resolution)
        grid_y = int((world_y - self.origin_y) / self.resolution)
        return grid_x, grid_y
    
    def grid_to_world(self, grid_x: int, grid_y: int) -> Tuple[float, float]:
        """柵格坐標轉世界坐標"""
        world_x = grid_x * self.resolution + self.origin_x
        world_y = grid_y * self.resolution + self.origin_y
        return world_x, world_y
    
    def is_free(self, world_x: float, world_y: float) -> bool:
        """檢查世界坐標位置是否自由"""
        grid_x, grid_y = self.world_to_grid(world_x, world_y)
        return self.get_cell_value(grid_x, grid_y) == 0
    
    def is_occupied(self, world_x: float, world_y: float) -> bool:
        """檢查世界坐標位置是否被占用"""
        grid_x, grid_y = self.world_to_grid(world_x, world_y)
        return self.get_cell_value(grid_x, grid_y) > 50

class MapManager:
    """地圖管理器"""
    
    def __init__(self, maps_dir: str = "maps"):
        self.maps_dir = Path(maps_dir)
        self.maps_dir.mkdir(exist_ok=True)
        
        # 創建子目錄
        (self.maps_dir / "data").mkdir(exist_ok=True)
        (self.maps_dir / "previews").mkdir(exist_ok=True)
        (self.maps_dir / "metadata").mkdir(exist_ok=True)
        
        self.current_map: Optional[OccupancyGridMap] = None
        self.available_maps: Dict[str, MapInfo] = {}
        
        # 初始化時載入現有地圖
        asyncio.create_task(self._load_available_maps())
    
    async def _load_available_maps(self):
        """載入可用地圖列表"""
        try:
            metadata_dir = self.maps_dir / "metadata"
            for metadata_file in metadata_dir.glob("*.json"):
                try:
                    with open(metadata_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    map_info = MapInfo(
                        id=data["id"],
                        name=data["name"],
                        created_at=datetime.fromisoformat(data["created_at"]),
                        source=data["source"],
                        file_path=data["file_path"],
                        preview_path=data.get("preview_path"),
                        metadata=data.get("metadata")
                    )
                    
                    self.available_maps[map_info.id] = map_info
                    
                except Exception as e:
                    logger.error(f"載入地圖元數據失敗 {metadata_file}: {e}")
                    
            logger.info(f"載入了 {len(self.available_maps)} 個可用地圖")
            
        except Exception as e:
            logger.error(f"載入可用地圖失敗: {e}")
    
    async def save_map(self, map_data: bytes, name: str, source: str = "lidar") -> str:
        """保存地圖數據"""
        try:
            # 生成唯一ID
            map_id = str(uuid.uuid4())
            
            # 解析地圖數據
            occupancy_map = await self._parse_map_data(map_data)
            
            # 保存地圖文件
            data_path = self.maps_dir / "data" / f"{map_id}.pkl.gz"
            await self._save_map_file(occupancy_map, data_path)
            
            # 生成預覽圖
            preview_path = self.maps_dir / "previews" / f"{map_id}.png"
            await self._generate_preview(occupancy_map, preview_path)
            
            # 創建地圖信息
            map_info = MapInfo(
                id=map_id,
                name=name,
                created_at=datetime.now(),
                source=source,
                file_path=str(data_path),
                preview_path=str(preview_path),
                metadata={
                    "width": occupancy_map.width,
                    "height": occupancy_map.height,
                    "resolution": occupancy_map.resolution,
                    "origin": [occupancy_map.origin_x, occupancy_map.origin_y]
                }
            )
            
            # 保存元數據
            metadata_path = self.maps_dir / "metadata" / f"{map_id}.json"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(map_info.to_dict(), f, indent=2, ensure_ascii=False)
            
            # 加入可用地圖列表
            self.available_maps[map_id] = map_info
            
            logger.info(f"地圖保存成功: {name} (ID: {map_id})")
            return map_id
            
        except Exception as e:
            logger.error(f"保存地圖失敗: {e}")
            raise
    
    async def _parse_map_data(self, map_data: bytes) -> OccupancyGridMap:
        """解析地圖數據"""
        try:
            # 假設數據是JSON格式的占用柵格地圖
            data = json.loads(map_data.decode('utf-8'))
            
            # 提取基本信息
            width = data["width"]
            height = data["height"]
            resolution = data["resolution"]
            origin = data["origin"]
            
            # 轉換地圖數據
            grid_data = np.array(data["data"], dtype=np.int8)
            
            # 處理數據格式
            if grid_data.ndim == 1:
                grid_data = grid_data.reshape(height, width)
            
            # 標準化占用值：0=自由，100=占用，-1=未知
            grid_data = np.where(grid_data == 0, 0, grid_data)  # 自由空間
            grid_data = np.where(grid_data == 100, 100, grid_data)  # 占用空間
            grid_data = np.where((grid_data != 0) & (grid_data != 100), -1, grid_data)  # 未知
            
            return OccupancyGridMap(
                width=width,
                height=height,
                resolution=resolution,
                origin_x=origin["x"],
                origin_y=origin["y"],
                data=grid_data,
                timestamp=datetime.now(),
                metadata=data.get("metadata", {})
            )
            
        except Exception as e:
            logger.error(f"解析地圖數據失敗: {e}")
            raise ValueError(f"無效的地圖數據格式: {e}")
    
    async def _save_map_file(self, occupancy_map: OccupancyGridMap, file_path: Path):
        """保存地圖文件"""
        try:
            with gzip.open(file_path, 'wb') as f:
                pickle.dump(occupancy_map, f)
        except Exception as e:
            logger.error(f"保存地圖文件失敗: {e}")
            raise
    
    async def _generate_preview(self, occupancy_map: OccupancyGridMap, preview_path: Path):
        """生成地圖預覽圖"""
        try:
            # 創建預覽圖像
            preview_size = (400, 400)
            
            # 標準化數據到0-255範圍
            data = occupancy_map.data.copy()
            
            # 映射占用值到顏色
            # -1 (未知) -> 128 (灰色)
            # 0 (自由) -> 255 (白色)  
            # 100 (占用) -> 0 (黑色)
            preview_data = np.zeros_like(data, dtype=np.uint8)
            preview_data[data == -1] = 128  # 未知 - 灰色
            preview_data[data == 0] = 255   # 自由 - 白色
            preview_data[data >= 50] = 0    # 占用 - 黑色
            
            # 調整圖像大小
            image = Image.fromarray(preview_data, mode='L')
            image = image.resize(preview_size, Image.Resampling.NEAREST)
            
            # 保存預覽圖
            image.save(preview_path)
            
        except Exception as e:
            logger.error(f"生成預覽圖失敗: {e}")
            raise
    
    async def load_map(self, map_id: str) -> bool:
        """載入地圖"""
        try:
            if map_id not in self.available_maps:
                logger.error(f"地圖 {map_id} 不存在")
                return False
            
            map_info = self.available_maps[map_id]
            
            # 載入地圖數據
            with gzip.open(map_info.file_path, 'rb') as f:
                self.current_map = pickle.load(f)
            
            logger.info(f"地圖載入成功: {map_info.name}")
            return True
            
        except Exception as e:
            logger.error(f"載入地圖失敗: {e}")
            return False
    
    async def list_maps(self) -> List[Dict[str, Any]]:
        """獲取地圖列表"""
        return [map_info.to_dict() for map_info in self.available_maps.values()]
    
    async def delete_map(self, map_id: str) -> bool:
        """刪除地圖"""
        try:
            if map_id not in self.available_maps:
                return False
            
            map_info = self.available_maps[map_id]
            
            # 刪除相關文件
            if os.path.exists(map_info.file_path):
                os.remove(map_info.file_path)
            
            if map_info.preview_path and os.path.exists(map_info.preview_path):
                os.remove(map_info.preview_path)
            
            metadata_path = self.maps_dir / "metadata" / f"{map_id}.json"
            if metadata_path.exists():
                metadata_path.unlink()
            
            # 從可用地圖中移除
            del self.available_maps[map_id]
            
            # 如果是當前地圖，清空當前地圖
            if self.current_map and hasattr(self.current_map, 'metadata'):
                if self.current_map.metadata.get('map_id') == map_id:
                    self.current_map = None
            
            logger.info(f"地圖刪除成功: {map_id}")
            return True
            
        except Exception as e:
            logger.error(f"刪除地圖失敗: {e}")
            return False
    
    async def get_map_preview(self, map_id: str) -> Optional[bytes]:
        """獲取地圖預覽圖"""
        try:
            if map_id not in self.available_maps:
                return None
            
            map_info = self.available_maps[map_id]
            
            if map_info.preview_path and os.path.exists(map_info.preview_path):
                with open(map_info.preview_path, 'rb') as f:
                    return f.read()
            
            return None
            
        except Exception as e:
            logger.error(f"獲取地圖預覽失敗: {e}")
            return None
    
    def get_current_map(self) -> Optional[OccupancyGridMap]:
        """獲取當前地圖"""
        return self.current_map
    
    async def create_default_map(self) -> str:
        """創建默認空地圖"""
        try:
            # 創建一個10x10米的空地圖
            width = height = 200  # 5cm分辨率下的200x200柵格
            resolution = 0.05
            
            # 全部標記為自由空間
            data = np.zeros((height, width), dtype=np.int8)
            
            occupancy_map = OccupancyGridMap(
                width=width,
                height=height,
                resolution=resolution,
                origin_x=-5.0,
                origin_y=-5.0,
                data=data,
                timestamp=datetime.now(),
                metadata={"type": "default", "description": "默認空地圖"}
            )
            
            # 保存默認地圖
            map_data = {
                "width": width,
                "height": height,
                "resolution": resolution,
                "origin": {"x": -5.0, "y": -5.0},
                "data": data.flatten().tolist(),
                "metadata": {"type": "default"}
            }
            
            map_bytes = json.dumps(map_data).encode('utf-8')
            map_id = await self.save_map(map_bytes, "默認地圖", "default")
            
            return map_id
            
        except Exception as e:
            logger.error(f"創建默認地圖失敗: {e}")
            raise
    
    def inflate_obstacles(self, robot_radius: float = 0.2) -> Optional[OccupancyGridMap]:
        """膨脹當前地圖的障礙物"""
        if not self.current_map:
            return None
        
        try:
            # 計算膨脹半徑（以像素為單位）
            inflation_radius = int(np.ceil(robot_radius / self.current_map.resolution))
            
            # 創建膨脹核
            kernel_size = 2 * inflation_radius + 1
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
            
            # 準備數據
            data = self.current_map.data.copy()
            
            # 找到占用的區域
            occupied_mask = (data >= 50).astype(np.uint8) * 255
            
            # 膨脹操作
            inflated_mask = cv2.dilate(occupied_mask, kernel, iterations=1)
            
            # 更新地圖數據
            inflated_data = data.copy()
            inflated_data[inflated_mask > 0] = 100  # 標記為占用
            
            # 創建新的地圖對象
            inflated_map = OccupancyGridMap(
                width=self.current_map.width,
                height=self.current_map.height,
                resolution=self.current_map.resolution,
                origin_x=self.current_map.origin_x,
                origin_y=self.current_map.origin_y,
                data=inflated_data,
                timestamp=datetime.now(),
                metadata={**self.current_map.metadata, "inflated": True, "robot_radius": robot_radius}
            )
            
            return inflated_map
            
        except Exception as e:
            logger.error(f"膨脹障礙物失敗: {e}")
            return None
    
    def get_map_statistics(self) -> Optional[Dict[str, Any]]:
        """獲取當前地圖統計信息"""
        if not self.current_map:
            return None
        
        try:
            data = self.current_map.data
            total_cells = data.size
            
            free_cells = np.sum(data == 0)
            occupied_cells = np.sum(data >= 50)
            unknown_cells = np.sum(data == -1)
            
            return {
                "total_cells": int(total_cells),
                "free_cells": int(free_cells),
                "occupied_cells": int(occupied_cells),
                "unknown_cells": int(unknown_cells),
                "coverage": float((free_cells + occupied_cells) / total_cells),
                "obstacle_ratio": float(occupied_cells / total_cells),
                "resolution": self.current_map.resolution,
                "size_meters": {
                    "width": self.current_map.width * self.current_map.resolution,
                    "height": self.current_map.height * self.current_map.resolution
                }
            }
            
        except Exception as e:
            logger.error(f"獲取地圖統計失敗: {e}")
            return None 