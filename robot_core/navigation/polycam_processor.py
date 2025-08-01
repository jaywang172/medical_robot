#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import tempfile
import zipfile
import shutil

# 3D文件處理庫
try:
    import trimesh
    import open3d as o3d
    HAS_3D_LIBS = True
except ImportError:
    HAS_3D_LIBS = False
    print("警告: 未安裝3D處理庫，請運行: pip install trimesh open3d")

from ..utils.logger import get_logger
from .map_manager import OccupancyGridMap, MapManager

logger = get_logger(__name__)

class PolycamProcessor:
    """Polycam文件處理器"""
    
    SUPPORTED_MESH_FORMATS = ['.obj', '.glb', '.usdz', '.dae', '.stl']
    SUPPORTED_POINTCLOUD_FORMATS = ['.ply', '.las', '.xyz', '.pts']
    SUPPORTED_FLOORPLAN_FORMATS = ['.dxf', '.dae']
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
        
        if not HAS_3D_LIBS:
            self.logger.warning("3D處理庫未安裝，部分功能將不可用")
    
    async def process_polycam_file(self, file_path: str, file_type: str = "auto") -> OccupancyGridMap:
        """
        處理Polycam導出的文件
        
        Args:
            file_path: 文件路徑
            file_type: 文件類型 ("mesh", "pointcloud", "floorplan", "auto")
            
        Returns:
            OccupancyGridMap: 處理後的占用柵格地圖
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            # 自動檢測文件類型
            if file_type == "auto":
                file_type = self._detect_file_type(file_path)
            
            self.logger.info(f"處理Polycam文件: {file_path.name} (類型: {file_type})")
            
            # 根據文件類型選擇處理方法
            if file_type == "mesh":
                return await self._process_mesh_file(file_path)
            elif file_type == "pointcloud":
                return await self._process_pointcloud_file(file_path)
            elif file_type == "floorplan":
                return await self._process_floorplan_file(file_path)
            else:
                raise ValueError(f"不支持的文件類型: {file_type}")
                
        except Exception as e:
            self.logger.error(f"處理Polycam文件失敗: {e}")
            raise
    
    def _detect_file_type(self, file_path: Path) -> str:
        """自動檢測文件類型"""
        suffix = file_path.suffix.lower()
        
        if suffix in self.SUPPORTED_MESH_FORMATS:
            return "mesh"
        elif suffix in self.SUPPORTED_POINTCLOUD_FORMATS:
            return "pointcloud"
        elif suffix in self.SUPPORTED_FLOORPLAN_FORMATS:
            return "floorplan"
        else:
            raise ValueError(f"不支持的文件格式: {suffix}")
    
    async def _process_mesh_file(self, file_path: Path) -> OccupancyGridMap:
        """處理網格文件 (.obj, .glb, .usdz, .dae, .stl)"""
        if not HAS_3D_LIBS:
            raise RuntimeError("需要安裝3D處理庫: pip install trimesh open3d")
        
        try:
            # 使用trimesh載入網格
            mesh = trimesh.load(str(file_path))
            
            if isinstance(mesh, trimesh.Scene):
                # 如果是場景，合併所有幾何體
                mesh = mesh.dump().sum()
            
            # 從網格生成點雲
            points = self._mesh_to_pointcloud(mesh)
            
            # 轉換為占用柵格地圖
            return self._pointcloud_to_occupancy_grid(points)
            
        except Exception as e:
            self.logger.error(f"處理網格文件失敗: {e}")
            raise
    
    async def _process_pointcloud_file(self, file_path: Path) -> OccupancyGridMap:
        """處理點雲文件 (.ply, .las, .xyz, .pts)"""
        if not HAS_3D_LIBS:
            raise RuntimeError("需要安裝3D處理庫: pip install trimesh open3d")
        
        try:
            suffix = file_path.suffix.lower()
            
            if suffix == '.ply':
                points = self._load_ply_file(file_path)
            elif suffix == '.xyz':
                points = self._load_xyz_file(file_path)
            elif suffix == '.pts':
                points = self._load_pts_file(file_path)
            elif suffix == '.las':
                points = self._load_las_file(file_path)
            else:
                raise ValueError(f"不支持的點雲格式: {suffix}")
            
            # 轉換為占用柵格地圖
            return self._pointcloud_to_occupancy_grid(points)
            
        except Exception as e:
            self.logger.error(f"處理點雲文件失敗: {e}")
            raise
    
    async def _process_floorplan_file(self, file_path: Path) -> OccupancyGridMap:
        """處理平面圖文件 (.dxf, .dae)"""
        try:
            suffix = file_path.suffix.lower()
            
            if suffix == '.dxf':
                return self._process_dxf_floorplan(file_path)
            elif suffix == '.dae':
                return await self._process_dae_floorplan(file_path)
            else:
                raise ValueError(f"不支持的平面圖格式: {suffix}")
                
        except Exception as e:
            self.logger.error(f"處理平面圖失敗: {e}")
            raise
    
    def _mesh_to_pointcloud(self, mesh: 'trimesh.Trimesh', density: int = 10000) -> np.ndarray:
        """從網格生成點雲"""
        try:
            # 在網格表面採樣點
            points, _ = trimesh.sample.sample_surface(mesh, density)
            return points
            
        except Exception as e:
            self.logger.error(f"網格轉點雲失敗: {e}")
            raise
    
    def _load_ply_file(self, file_path: Path) -> np.ndarray:
        """載入PLY點雲文件"""
        try:
            pcd = o3d.io.read_point_cloud(str(file_path))
            return np.asarray(pcd.points)
        except Exception as e:
            self.logger.error(f"載入PLY文件失敗: {e}")
            raise
    
    def _load_xyz_file(self, file_path: Path) -> np.ndarray:
        """載入XYZ點雲文件"""
        try:
            # XYZ格式通常是每行一個點 (x y z)
            points = []
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        coords = line.split()
                        if len(coords) >= 3:
                            x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
                            points.append([x, y, z])
            
            return np.array(points)
        except Exception as e:
            self.logger.error(f"載入XYZ文件失敗: {e}")
            raise
    
    def _load_pts_file(self, file_path: Path) -> np.ndarray:
        """載入PTS點雲文件"""
        try:
            # PTS格式類似XYZ，但可能包含顏色信息
            points = []
            with open(file_path, 'r') as f:
                # 跳過頭部（如果有）
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        coords = line.split()
                        if len(coords) >= 3:
                            x, y, z = float(coords[0]), float(coords[1]), float(coords[2])
                            points.append([x, y, z])
            
            return np.array(points)
        except Exception as e:
            self.logger.error(f"載入PTS文件失敗: {e}")
            raise
    
    def _load_las_file(self, file_path: Path) -> np.ndarray:
        """載入LAS點雲文件"""
        try:
            # LAS需要專門的庫
            try:
                import laspy
            except ImportError:
                raise ImportError("需要安裝laspy庫: pip install laspy")
            
            las_file = laspy.read(file_path)
            points = np.vstack((las_file.x, las_file.y, las_file.z)).transpose()
            return points
            
        except Exception as e:
            self.logger.error(f"載入LAS文件失敗: {e}")
            raise
    
    def _process_dxf_floorplan(self, file_path: Path) -> OccupancyGridMap:
        """處理DXF平面圖"""
        try:
            # DXF處理需要專門的庫
            try:
                import ezdxf
            except ImportError:
                raise ImportError("需要安裝ezdxf庫: pip install ezdxf")
            
            doc = ezdxf.readfile(file_path)
            msp = doc.modelspace()
            
            # 提取線條和多邊形作為障礙物
            obstacles = []
            
            for entity in msp:
                if entity.dxftype() == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    obstacles.append([(start.x, start.y), (end.x, end.y)])
                elif entity.dxftype() == 'POLYLINE':
                    points = [(vertex.dxf.location.x, vertex.dxf.location.y) 
                             for vertex in entity.vertices]
                    obstacles.append(points)
            
            # 轉換為占用柵格地圖
            return self._lines_to_occupancy_grid(obstacles)
            
        except Exception as e:
            self.logger.error(f"處理DXF平面圖失敗: {e}")
            raise
    
    async def _process_dae_floorplan(self, file_path: Path) -> OccupancyGridMap:
        """處理DAE平面圖"""
        try:
            # DAE是3D格式，當作mesh處理
            return await self._process_mesh_file(file_path)
        except Exception as e:
            self.logger.error(f"處理DAE平面圖失敗: {e}")
            raise
    
    def _pointcloud_to_occupancy_grid(self, points: np.ndarray, 
                                    resolution: float = 0.05,
                                    height_threshold: Tuple[float, float] = (0.1, 2.0)) -> OccupancyGridMap:
        """將點雲轉換為占用柵格地圖"""
        try:
            if len(points) == 0:
                raise ValueError("點雲為空")
            
            # 過濾高度範圍內的點（機器人導航層面）
            min_height, max_height = height_threshold
            ground_level = np.percentile(points[:, 2], 10)  # 假設10%的點是地面
            
            filtered_points = points[
                (points[:, 2] >= ground_level + min_height) & 
                (points[:, 2] <= ground_level + max_height)
            ]
            
            if len(filtered_points) == 0:
                self.logger.warning("沒有在指定高度範圍內找到點")
                filtered_points = points
            
            # 計算邊界
            min_x, min_y = np.min(filtered_points[:, :2], axis=0)
            max_x, max_y = np.max(filtered_points[:, :2], axis=0)
            
            # 創建柵格
            width = int(np.ceil((max_x - min_x) / resolution))
            height = int(np.ceil((max_y - min_y) / resolution))
            
            # 初始化為自由空間
            grid_data = np.zeros((height, width), dtype=np.int8)
            
            # 將點雲投影到2D柵格
            grid_x = ((filtered_points[:, 0] - min_x) / resolution).astype(int)
            grid_y = ((filtered_points[:, 1] - min_y) / resolution).astype(int)
            
            # 限制在柵格範圍內
            valid_indices = (
                (grid_x >= 0) & (grid_x < width) & 
                (grid_y >= 0) & (grid_y < height)
            )
            
            grid_x = grid_x[valid_indices]
            grid_y = grid_y[valid_indices]
            
            # 標記占用的格子
            grid_data[grid_y, grid_x] = 100
            
            # 應用形態學操作來填充小洞和平滑邊界
            grid_data = self._post_process_grid(grid_data)
            
            return OccupancyGridMap(
                width=width,
                height=height,
                resolution=resolution,
                origin_x=min_x,
                origin_y=min_y,
                data=grid_data,
                timestamp=datetime.now(),
                metadata={
                    "source": "polycam",
                    "original_points": len(points),
                    "filtered_points": len(filtered_points),
                    "ground_level": float(ground_level),
                    "height_range": height_threshold
                }
            )
            
        except Exception as e:
            self.logger.error(f"點雲轉占用柵格失敗: {e}")
            raise
    
    def _lines_to_occupancy_grid(self, obstacles: List[List[Tuple[float, float]]], 
                                resolution: float = 0.05) -> OccupancyGridMap:
        """將線條/多邊形轉換為占用柵格地圖"""
        try:
            if not obstacles:
                raise ValueError("沒有障礙物數據")
            
            # 計算所有點的邊界
            all_points = []
            for obstacle in obstacles:
                all_points.extend(obstacle)
            
            all_points = np.array(all_points)
            min_x, min_y = np.min(all_points, axis=0)
            max_x, max_y = np.max(all_points, axis=0)
            
            # 創建柵格
            width = int(np.ceil((max_x - min_x) / resolution))
            height = int(np.ceil((max_y - min_y) / resolution))
            
            # 初始化為自由空間
            grid_data = np.zeros((height, width), dtype=np.int8)
            
            # 繪製障礙物線條
            for obstacle in obstacles:
                self._draw_line_on_grid(grid_data, obstacle, min_x, min_y, resolution)
            
            return OccupancyGridMap(
                width=width,
                height=height,
                resolution=resolution,
                origin_x=min_x,
                origin_y=min_y,
                data=grid_data,
                timestamp=datetime.now(),
                metadata={
                    "source": "polycam_floorplan",
                    "obstacles_count": len(obstacles)
                }
            )
            
        except Exception as e:
            self.logger.error(f"線條轉占用柵格失敗: {e}")
            raise
    
    def _draw_line_on_grid(self, grid_data: np.ndarray, points: List[Tuple[float, float]], 
                          min_x: float, min_y: float, resolution: float):
        """在柵格上繪製線條"""
        try:
            import cv2
            
            # 將世界坐標轉換為柵格坐標
            grid_points = []
            for x, y in points:
                grid_x = int((x - min_x) / resolution)
                grid_y = int((y - min_y) / resolution)
                grid_points.append((grid_x, grid_y))
            
            # 使用OpenCV繪製線條
            for i in range(len(grid_points) - 1):
                pt1 = grid_points[i]
                pt2 = grid_points[i + 1]
                cv2.line(grid_data, pt1, pt2, 100, thickness=2)
            
            # 如果是閉合多邊形，連接最後一點和第一點
            if len(grid_points) > 2:
                cv2.line(grid_data, grid_points[-1], grid_points[0], 100, thickness=2)
                
        except Exception as e:
            self.logger.error(f"繪製線條失敗: {e}")
            # 降級到簡單點標記
            for x, y in points:
                grid_x = int((x - min_x) / resolution)
                grid_y = int((y - min_y) / resolution)
                if (0 <= grid_x < grid_data.shape[1] and 
                    0 <= grid_y < grid_data.shape[0]):
                    grid_data[grid_y, grid_x] = 100
    
    def _post_process_grid(self, grid_data: np.ndarray) -> np.ndarray:
        """後處理柵格地圖"""
        try:
            import cv2
            
            # 形態學閉運算填充小洞
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            processed = cv2.morphologyEx(
                (grid_data > 0).astype(np.uint8) * 100, 
                cv2.MORPH_CLOSE, 
                kernel
            )
            
            return processed.astype(np.int8)
            
        except ImportError:
            # 如果沒有OpenCV，直接返回原數據
            return grid_data
    
    @staticmethod
    def get_polycam_workflow_guide() -> Dict[str, Any]:
        """獲取Polycam工作流程指南"""
        return {
            "steps": [
                {
                    "step": 1,
                    "title": "使用Polycam掃描",
                    "description": "在iPad上打開Polycam，選擇LiDAR模式掃描環境",
                    "tips": [
                        "保持設備穩定移動",
                        "確保充足光線",
                        "覆蓋所有需要的區域"
                    ]
                },
                {
                    "step": 2,
                    "title": "導出合適格式",
                    "description": "選擇適合的導出格式",
                    "formats": {
                        "推薦格式": [
                            ".ply - 高質量點雲，包含顏色信息",
                            ".obj - 網格文件，適合詳細幾何",
                            ".xyz - 簡單點雲格式"
                        ],
                        "支持格式": {
                            "網格": [".obj", ".glb", ".usdz", ".dae", ".stl"],
                            "點雲": [".ply", ".las", ".xyz", ".pts"],
                            "平面圖": [".dxf", ".dae"]
                        }
                    }
                },
                {
                    "step": 3,
                    "title": "上傳到機器人",
                    "description": "將導出的文件上傳到機器人系統",
                    "methods": [
                        "通過Web界面上傳",
                        "API直接上傳",
                        "文件夾監控自動處理"
                    ]
                }
            ],
            "quality_tips": [
                "選擇合適的解析度 (建議5cm)",
                "確保掃描覆蓋完整",
                "避免反光表面",
                "多角度掃描複雜區域"
            ]
        }

# 添加依賴檢查和安裝建議
def check_dependencies() -> Dict[str, bool]:
    """檢查所需依賴"""
    deps = {
        "trimesh": False,
        "open3d": False,
        "ezdxf": False,
        "laspy": False,
        "opencv-python": False
    }
    
    try:
        import trimesh
        deps["trimesh"] = True
    except ImportError:
        pass
    
    try:
        import open3d
        deps["open3d"] = True
    except ImportError:
        pass
    
    try:
        import ezdxf
        deps["ezdxf"] = True
    except ImportError:
        pass
    
    try:
        import laspy
        deps["laspy"] = True
    except ImportError:
        pass
    
    try:
        import cv2
        deps["opencv-python"] = True
    except ImportError:
        pass
    
    return deps

def install_missing_dependencies():
    """安裝缺失的依賴"""
    deps = check_dependencies()
    missing = [name for name, installed in deps.items() if not installed]
    
    if missing:
        install_cmd = f"pip install {' '.join(missing)}"
        print(f"缺失依賴: {missing}")
        print(f"安裝命令: {install_cmd}")
        return install_cmd
    else:
        print("所有依賴已安裝")
        return None 