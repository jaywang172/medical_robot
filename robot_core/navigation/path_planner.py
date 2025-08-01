#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路徑規劃模組
實現A*算法進行路徑規劃和動態障礙規避
"""

import asyncio
import time
import math
import numpy as np
from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum
import heapq
from collections import deque

from robot_core.utils.logger import ContextualLogger, log_navigation_event, log_performance
from robot_core.hardware.motor_controller import MotorCommand
from .map_manager import MapManager, OccupancyGridMap


class NavigationState(Enum):
    """導航狀態"""
    IDLE = "idle"
    PLANNING = "planning"
    FOLLOWING_PATH = "following_path"
    AVOIDING_OBSTACLE = "avoiding_obstacle"
    REACHED_GOAL = "reached_goal"
    FAILED = "failed"


@dataclass
class Point:
    """2D點"""
    x: float
    y: float
    
    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)
    
    def distance_to(self, other) -> float:
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def angle_to(self, other) -> float:
        return math.atan2(other.y - self.y, other.x - self.x)


@dataclass
class Obstacle:
    """障礙物"""
    center: Point
    radius: float
    timestamp: float
    confidence: float = 1.0
    
    def contains_point(self, point: Point) -> bool:
        return self.center.distance_to(point) <= self.radius
    
    def is_expired(self, current_time: float, max_age: float = 5.0) -> bool:
        return (current_time - self.timestamp) > max_age


@dataclass
class NavigationCommand:
    """導航命令"""
    linear_speed: float   # 線速度 (-1.0 到 1.0)
    angular_speed: float  # 角速度 (-1.0 到 1.0)
    command_type: str     # 命令類型
    duration: float = 0.0 # 持續時間


class Grid:
    """柵格地圖"""
    
    def __init__(self, width: float, height: float, resolution: float):
        self.width = width
        self.height = height
        self.resolution = resolution
        
        self.grid_width = int(width / resolution)
        self.grid_height = int(height / resolution)
        
        # 0: 自由空間, 1: 障礙物, 0.5: 未知
        self.data = np.zeros((self.grid_height, self.grid_width), dtype=np.float32)
        
        self.origin = Point(-width/2, -height/2)  # 地圖原點
    
    def world_to_grid(self, point: Point) -> Tuple[int, int]:
        """世界坐標轉換為柵格坐標"""
        x = int((point.x - self.origin.x) / self.resolution)
        y = int((point.y - self.origin.y) / self.resolution)
        return x, y
    
    def grid_to_world(self, grid_x: int, grid_y: int) -> Point:
        """柵格坐標轉換為世界坐標"""
        x = self.origin.x + (grid_x + 0.5) * self.resolution
        y = self.origin.y + (grid_y + 0.5) * self.resolution
        return Point(x, y)
    
    def is_valid_grid(self, grid_x: int, grid_y: int) -> bool:
        """檢查柵格坐標是否有效"""
        return 0 <= grid_x < self.grid_width and 0 <= grid_y < self.grid_height
    
    def is_free(self, grid_x: int, grid_y: int) -> bool:
        """檢查柵格是否為自由空間"""
        if not self.is_valid_grid(grid_x, grid_y):
            return False
        return self.data[grid_y, grid_x] < 0.5
    
    def set_obstacle(self, point: Point, radius: float):
        """在地圖上設置障礙物"""
        center_x, center_y = self.world_to_grid(point)
        
        # 計算影響範圍
        grid_radius = int(radius / self.resolution) + 1
        
        for dy in range(-grid_radius, grid_radius + 1):
            for dx in range(-grid_radius, grid_radius + 1):
                grid_x = center_x + dx
                grid_y = center_y + dy
                
                if self.is_valid_grid(grid_x, grid_y):
                    # 計算實際距離
                    world_point = self.grid_to_world(grid_x, grid_y)
                    distance = point.distance_to(world_point)
                    
                    if distance <= radius:
                        self.data[grid_y, grid_x] = 1.0
    
    def clear_obstacles(self):
        """清除所有障礙物"""
        self.data.fill(0.0)


class AStarPlanner:
    """A*路徑規劃器"""
    
    def __init__(self, grid: Grid):
        self.grid = grid
        self.logger = ContextualLogger("AStarPlanner")
    
    def plan_path(self, start: Point, goal: Point, max_iterations: int = 1000) -> List[Point]:
        """
        使用A*算法規劃路徑
        
        Args:
            start: 起始點
            goal: 目標點
            max_iterations: 最大迭代次數
            
        Returns:
            List[Point]: 路徑點列表
        """
        start_time = time.time()
        
        start_grid = self.grid.world_to_grid(start)
        goal_grid = self.grid.world_to_grid(goal)
        
        # 檢查起始點和目標點是否有效
        if not self.grid.is_free(*start_grid):
            self.logger.warning("起始點被占用")
            return []
        
        if not self.grid.is_free(*goal_grid):
            self.logger.warning("目標點被占用")
            return []
        
        # A*算法
        open_set = []
        heapq.heappush(open_set, (0, start_grid))
        came_from = {}
        
        g_score = {start_grid: 0}
        f_score = {start_grid: self._heuristic(start_grid, goal_grid)}
        
        iteration = 0
        
        while open_set and iteration < max_iterations:
            iteration += 1
            
            current = heapq.heappop(open_set)[1]
            
            if current == goal_grid:
                # 找到路徑
                path = self._reconstruct_path(came_from, current)
                world_path = [self.grid.grid_to_world(gx, gy) for gx, gy in path]
                
                planning_time = time.time() - start_time
                log_performance("a_star_planning", planning_time, 
                              iterations=iteration, path_length=len(world_path))
                
                return world_path
            
            # 檢查鄰居
            for neighbor in self._get_neighbors(current):
                if not self.grid.is_free(*neighbor):
                    continue
                
                tentative_g_score = g_score[current] + self._distance(current, neighbor)
                
                if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g_score
                    f_score[neighbor] = tentative_g_score + self._heuristic(neighbor, goal_grid)
                    
                    heapq.heappush(open_set, (f_score[neighbor], neighbor))
        
        self.logger.warning(f"A*規劃失敗，迭代次數: {iteration}")
        return []
    
    def _get_neighbors(self, grid_pos: Tuple[int, int]) -> List[Tuple[int, int]]:
        """獲取鄰居節點（8連通）"""
        x, y = grid_pos
        neighbors = []
        
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                
                nx, ny = x + dx, y + dy
                if self.grid.is_valid_grid(nx, ny):
                    neighbors.append((nx, ny))
        
        return neighbors
    
    def _distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """計算兩點間距離"""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return math.sqrt(dx*dx + dy*dy)
    
    def _heuristic(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """啟發函數（歐幾里得距離）"""
        return self._distance(pos1, pos2)
    
    def _reconstruct_path(self, came_from: Dict, current: Tuple[int, int]) -> List[Tuple[int, int]]:
        """重建路徑"""
        path = [current]
        while current in came_from:
            current = came_from[current]
            path.append(current)
        return path[::-1]


class DynamicWindowApproach:
    """動態窗口法避障"""
    
    def __init__(self, max_linear_vel: float = 0.5, max_angular_vel: float = 1.0):
        self.max_linear_vel = max_linear_vel
        self.max_angular_vel = max_angular_vel
        self.logger = ContextualLogger("DWA")
        
        # 速度採樣參數
        self.v_resolution = 0.1  # 線速度分辨率
        self.w_resolution = 0.1  # 角速度分辨率
        
        # 評價函數權重
        self.goal_weight = 1.0
        self.obstacle_weight = 2.0
        self.velocity_weight = 0.1
    
    def compute_velocity(self, 
                        current_pos: Point, 
                        current_theta: float,
                        goal: Point, 
                        obstacles: List[Obstacle]) -> Tuple[float, float]:
        """
        計算最優速度
        
        Returns:
            Tuple[float, float]: (線速度, 角速度)
        """
        best_v = 0.0
        best_w = 0.0
        best_score = float('-inf')
        
        # 速度空間採樣
        for v in np.arange(0, self.max_linear_vel + self.v_resolution, self.v_resolution):
            for w in np.arange(-self.max_angular_vel, self.max_angular_vel + self.w_resolution, self.w_resolution):
                
                # 預測軌跡
                trajectory = self._predict_trajectory(current_pos, current_theta, v, w)
                
                # 碰撞檢測
                if self._check_collision(trajectory, obstacles):
                    continue
                
                # 評價函數
                score = self._evaluate_trajectory(trajectory, goal, obstacles, v, w)
                
                if score > best_score:
                    best_score = score
                    best_v = v
                    best_w = w
        
        return best_v, best_w
    
    def _predict_trajectory(self, pos: Point, theta: float, v: float, w: float, 
                           dt: float = 0.1, steps: int = 10) -> List[Point]:
        """預測軌跡"""
        trajectory = []
        x, y, th = pos.x, pos.y, theta
        
        for _ in range(steps):
            x += v * math.cos(th) * dt
            y += v * math.sin(th) * dt
            th += w * dt
            trajectory.append(Point(x, y))
        
        return trajectory
    
    def _check_collision(self, trajectory: List[Point], obstacles: List[Obstacle]) -> bool:
        """檢查軌跡是否與障礙物碰撞"""
        for point in trajectory:
            for obstacle in obstacles:
                if obstacle.contains_point(point):
                    return True
        return False
    
    def _evaluate_trajectory(self, trajectory: List[Point], goal: Point, 
                           obstacles: List[Obstacle], v: float, w: float) -> float:
        """評價軌跡"""
        if not trajectory:
            return float('-inf')
        
        end_point = trajectory[-1]
        
        # 目標項：距離目標越近越好
        goal_dist = end_point.distance_to(goal)
        goal_score = -goal_dist * self.goal_weight
        
        # 障礙物項：距離障礙物越遠越好
        min_obstacle_dist = float('inf')
        for point in trajectory:
            for obstacle in obstacles:
                dist = obstacle.center.distance_to(point) - obstacle.radius
                min_obstacle_dist = min(min_obstacle_dist, dist)
        
        obstacle_score = min_obstacle_dist * self.obstacle_weight
        
        # 速度項：偏好更高的線速度
        velocity_score = v * self.velocity_weight
        
        return goal_score + obstacle_score + velocity_score


class PathPlanner:
    """路徑規劃器主控制類"""
    
    def __init__(self, config):
        self.config = config
        self.logger = ContextualLogger("PathPlanner")
        
        # 創建地圖管理器
        self.map_manager = MapManager()
        
        # 創建柵格地圖（用於動態障礙物和實時規劃）
        self.grid = Grid(
            config.planning_range * 2,  # 以機器人為中心的正方形地圖
            config.planning_range * 2,
            config.grid_size
        )
        
        # 創建規劃器
        self.astar_planner = AStarPlanner(self.grid)
        self.dwa = DynamicWindowApproach(
            config.max_linear_speed,
            config.max_angular_speed
        )
        
        # 狀態變量
        self.navigation_state = NavigationState.IDLE
        self.current_path = []
        self.current_goal = None
        self.current_position = Point(0, 0)
        self.current_theta = 0.0
        
        # 障礙物管理
        self.dynamic_obstacles = []
        self.obstacle_buffer = deque(maxlen=10)
        
        # 路徑跟踪
        self.path_index = 0
        self.lookahead_distance = 0.5  # 前瞻距離
        
        # 預建地圖支持
        self.use_prebuilt_map = False
        self.current_occupancy_map: Optional[OccupancyGridMap] = None
        
    async def initialize(self):
        """初始化路徑規劃器"""
        start_time = time.time()
        
        try:
            # 清空地圖
            self.grid.clear_obstacles()
            
            # 重置狀態
            self.navigation_state = NavigationState.IDLE
            self.current_path = []
            self.dynamic_obstacles = []
            
            # 嘗試加載默認地圖或創建一個
            await self._initialize_default_map()
            
            self.logger.info("路徑規劃器初始化成功")
            
        except Exception as e:
            self.logger.error(f"路徑規劃器初始化失敗: {e}")
            raise
        
        finally:
            duration = time.time() - start_time
            log_performance("path_planner_init", duration)
    
    async def _initialize_default_map(self):
        """初始化默認地圖"""
        try:
            # 檢查是否有可用的地圖
            available_maps = await self.map_manager.list_maps()
            
            if available_maps:
                # 如果有地圖，加載第一個
                first_map = available_maps[0]
                await self.map_manager.load_map(first_map['id'])
                self.current_occupancy_map = self.map_manager.get_current_map()
                self.use_prebuilt_map = True
                self.logger.info(f"加載預建地圖: {first_map['name']}")
            else:
                # 創建默認空地圖
                map_id = await self.map_manager.create_default_map()
                await self.map_manager.load_map(map_id)
                self.current_occupancy_map = self.map_manager.get_current_map()
                self.use_prebuilt_map = True
                self.logger.info("創建並加載默認地圖")
                
        except Exception as e:
            self.logger.error(f"初始化默認地圖失敗: {e}")
            self.use_prebuilt_map = False
    
    async def update_map(self):
        """更新地圖（當選擇新地圖時調用）"""
        try:
            self.current_occupancy_map = self.map_manager.get_current_map()
            if self.current_occupancy_map:
                self.use_prebuilt_map = True
                self.logger.info("地圖更新成功")
                
                # 如果正在導航，重新規劃路徑
                if self.current_goal and self.navigation_state in [
                    NavigationState.FOLLOWING_PATH, 
                    NavigationState.PLANNING
                ]:
                    await self._plan_path()
            else:
                self.use_prebuilt_map = False
                self.logger.warning("無可用地圖，回退到實時建圖模式")
                
        except Exception as e:
            self.logger.error(f"更新地圖失敗: {e}")
    
    def _is_path_valid_on_map(self, path: List[Point]) -> bool:
        """檢查路徑在預建地圖上是否有效"""
        if not self.current_occupancy_map or not path:
            return True  # 沒有預建地圖時視為有效
        
        for point in path:
            if self.current_occupancy_map.is_occupied(point.x, point.y):
                return False
        
        return True
    
    def _integrate_prebuilt_map_obstacles(self):
        """將預建地圖的障礙物整合到柵格地圖中"""
        if not self.current_occupancy_map or not self.use_prebuilt_map:
            return
        
        try:
            # 清空當前柵格地圖的靜態障礙物
            self.grid.clear_obstacles()
            
            # 從預建地圖中添加障礙物
            map_data = self.current_occupancy_map.data
            resolution = self.current_occupancy_map.resolution
            origin_x = self.current_occupancy_map.origin_x
            origin_y = self.current_occupancy_map.origin_y
            
            # 轉換預建地圖到當前柵格座標系統
            for map_y in range(self.current_occupancy_map.height):
                for map_x in range(self.current_occupancy_map.width):
                    if map_data[map_y, map_x] >= 50:  # 占用的格子
                        # 轉換為世界坐標
                        world_x = map_x * resolution + origin_x
                        world_y = map_y * resolution + origin_y
                        
                        # 轉換為當前柵格坐標
                        grid_x = int((world_x + self.config.planning_range) / self.config.grid_size)
                        grid_y = int((world_y + self.config.planning_range) / self.config.grid_size)
                        
                        # 添加到柵格地圖
                        if (0 <= grid_x < self.grid.width and 
                            0 <= grid_y < self.grid.height):
                            self.grid.add_obstacle(grid_x, grid_y)
            
            self.logger.debug("預建地圖障礙物已整合到柵格地圖")
            
        except Exception as e:
            self.logger.error(f"整合預建地圖障礙物失敗: {e}")
    
    async def set_goal(self, goal: Point) -> bool:
        """設置導航目標"""
        self.current_goal = goal
        self.navigation_state = NavigationState.PLANNING
        
        log_navigation_event("SET_GOAL", target=f"({goal.x:.2f}, {goal.y:.2f})")
        
        # 重新規劃路徑
        return await self._plan_path()
    
    async def _plan_path(self) -> bool:
        """規劃路徑"""
        if not self.current_goal:
            return False
        
        self.logger.info(f"規劃從 ({self.current_position.x:.2f}, {self.current_position.y:.2f}) "
                        f"到 ({self.current_goal.x:.2f}, {self.current_goal.y:.2f}) 的路徑")
        
        # 更新地圖障礙物（包含預建地圖和動態障礙物）
        self._update_grid_obstacles()
        
        # 使用A*規劃路徑
        path = self.astar_planner.plan_path(
            self.current_position, 
            self.current_goal,
            self.config.max_iterations
        )
        
        if path:
            self.current_path = path
            self.path_index = 0
            self.navigation_state = NavigationState.FOLLOWING_PATH
            
            log_navigation_event("PATH_PLANNED", 
                               position=f"({self.current_position.x:.2f}, {self.current_position.y:.2f})",
                               target=f"({self.current_goal.x:.2f}, {self.current_goal.y:.2f})",
                               path_length=len(path))
            return True
        else:
            self.navigation_state = NavigationState.FAILED
            self.logger.warning("路徑規劃失敗")
            return False
    
    async def update_obstacles(self, vision_obstacles: List):
        """更新動態障礙物"""
        current_time = time.time()
        
        # 轉換視覺障礙物為導航障礙物
        new_obstacles = []
        for obs in vision_obstacles:
            if hasattr(obs, 'distance') and hasattr(obs, 'angle') and obs.distance:
                # 計算障礙物在機器人坐標系中的位置
                obs_x = self.current_position.x + obs.distance * math.cos(self.current_theta + obs.angle)
                obs_y = self.current_position.y + obs.distance * math.sin(self.current_theta + obs.angle)
                
                obstacle = Obstacle(
                    center=Point(obs_x, obs_y),
                    radius=self.config.obstacle_inflation,
                    timestamp=current_time,
                    confidence=obs.confidence if hasattr(obs, 'confidence') else 1.0
                )
                new_obstacles.append(obstacle)
        
        # 更新障礙物列表
        self.dynamic_obstacles = [
            obs for obs in self.dynamic_obstacles 
            if not obs.is_expired(current_time)
        ]
        self.dynamic_obstacles.extend(new_obstacles)
        
        # 如果有新障礙物且正在跟踪路徑，檢查是否需要重新規劃
        if new_obstacles and self.navigation_state == NavigationState.FOLLOWING_PATH:
            await self._check_path_validity()
    
    async def _check_path_validity(self):
        """檢查當前路徑是否仍然有效"""
        if not self.current_path:
            return
        
        # 檢查路徑上是否有新的障礙物
        for i in range(self.path_index, len(self.current_path)):
            point = self.current_path[i]
            for obstacle in self.dynamic_obstacles:
                if obstacle.contains_point(point):
                    self.logger.info("檢測到路徑上有障礙物，重新規劃")
                    await self._plan_path()
                    return
    
    def _update_grid_obstacles(self):
        """更新柵格地圖中的障礙物"""
        # 清除舊的動態障礙物
        self.grid.clear_obstacles()
        
        # 首先整合預建地圖的障礙物
        self._integrate_prebuilt_map_obstacles()
        
        # 添加當前的動態障礙物
        for obstacle in self.dynamic_obstacles:
            self.grid.set_obstacle(obstacle.center, obstacle.radius)
    
    async def get_next_move(self, sensor_data, vision_data) -> Optional[NavigationCommand]:
        """獲取下一個移動命令"""
        if self.navigation_state == NavigationState.IDLE:
            return None
        
        # 檢查是否到達目標
        if self.current_goal and self.current_position.distance_to(self.current_goal) < self.config.goal_tolerance:
            self.navigation_state = NavigationState.REACHED_GOAL
            log_navigation_event("REACHED_GOAL", 
                               position=f"({self.current_position.x:.2f}, {self.current_position.y:.2f})")
            return NavigationCommand(0, 0, "STOP")
        
        # 檢查緊急停止條件
        if sensor_data and hasattr(sensor_data, 'get_min_distance'):
            min_distance = sensor_data.get_min_distance()
            if min_distance < self.config.emergency_stop_distance:
                log_navigation_event("EMERGENCY_STOP", min_distance=min_distance)
                return NavigationCommand(0, 0, "EMERGENCY_STOP")
        
        # 根據當前狀態決定行為
        if self.navigation_state == NavigationState.FOLLOWING_PATH:
            return await self._follow_path()
        elif self.navigation_state == NavigationState.AVOIDING_OBSTACLE:
            return await self._avoid_obstacles()
        
        return None
    
    async def _follow_path(self) -> Optional[NavigationCommand]:
        """跟踪路徑"""
        if not self.current_path or self.path_index >= len(self.current_path):
            return None
        
        # 尋找前瞻點
        lookahead_point = self._find_lookahead_point()
        
        if not lookahead_point:
            # 沒有找到前瞻點，可能已到達路徑末端
            return NavigationCommand(0, 0, "STOP")
        
        # 檢查是否需要避障
        if self.dynamic_obstacles:
            # 使用動態窗口法
            linear_vel, angular_vel = self.dwa.compute_velocity(
                self.current_position,
                self.current_theta,
                lookahead_point,
                self.dynamic_obstacles
            )
            
            # 轉換為電機命令
            return self._create_navigation_command(linear_vel, angular_vel, "FOLLOW_PATH")
        else:
            # 簡單的純追踪控制器
            return self._pure_pursuit_control(lookahead_point)
    
    def _find_lookahead_point(self) -> Optional[Point]:
        """尋找前瞻點"""
        if not self.current_path:
            return None
        
        # 從當前路徑索引開始尋找
        for i in range(self.path_index, len(self.current_path)):
            point = self.current_path[i]
            distance = self.current_position.distance_to(point)
            
            if distance >= self.lookahead_distance:
                self.path_index = i
                return point
        
        # 如果沒有找到足夠遠的點，返回路徑末端
        if self.current_path:
            return self.current_path[-1]
        
        return None
    
    def _pure_pursuit_control(self, target: Point) -> NavigationCommand:
        """純追踪控制器"""
        # 計算目標方向
        target_angle = self.current_position.angle_to(target)
        angle_error = target_angle - self.current_theta
        
        # 角度標準化到 [-π, π]
        while angle_error > math.pi:
            angle_error -= 2 * math.pi
        while angle_error < -math.pi:
            angle_error += 2 * math.pi
        
        # 計算控制命令
        distance = self.current_position.distance_to(target)
        
        # 線速度：距離越遠速度越快，但要考慮角度誤差
        linear_speed = min(distance * 0.5, self.config.max_linear_speed)
        if abs(angle_error) > math.pi / 4:  # 角度誤差太大時減速
            linear_speed *= 0.5
        
        # 角速度：比例控制
        angular_speed = angle_error * 2.0
        angular_speed = max(-self.config.max_angular_speed, 
                          min(self.config.max_angular_speed, angular_speed))
        
        return self._create_navigation_command(linear_speed, angular_speed, "PURE_PURSUIT")
    
    async def _avoid_obstacles(self) -> Optional[NavigationCommand]:
        """避障行為"""
        if not self.dynamic_obstacles:
            self.navigation_state = NavigationState.FOLLOWING_PATH
            return None
        
        # 使用DWA進行避障
        goal = self.current_goal if self.current_goal else Point(
            self.current_position.x + math.cos(self.current_theta),
            self.current_position.y + math.sin(self.current_theta)
        )
        
        linear_vel, angular_vel = self.dwa.compute_velocity(
            self.current_position,
            self.current_theta,
            goal,
            self.dynamic_obstacles
        )
        
        return self._create_navigation_command(linear_vel, angular_vel, "AVOID_OBSTACLE")
    
    def _create_navigation_command(self, linear_vel: float, angular_vel: float, 
                                 command_type: str) -> NavigationCommand:
        """創建導航命令"""
        # 標準化速度到 [-1, 1] 範圍
        linear_speed = linear_vel / self.config.max_linear_speed
        angular_speed = angular_vel / self.config.max_angular_speed
        
        # 限制範圍
        linear_speed = max(-1.0, min(1.0, linear_speed))
        angular_speed = max(-1.0, min(1.0, angular_speed))
        
        return NavigationCommand(linear_speed, angular_speed, command_type)
    
    def update_pose(self, x: float, y: float, theta: float):
        """更新機器人位姿"""
        self.current_position = Point(x, y)
        self.current_theta = theta
    
    def get_status(self) -> Dict:
        """獲取導航狀態"""
        return {
            "state": self.navigation_state.value,
            "current_position": {
                "x": self.current_position.x,
                "y": self.current_position.y,
                "theta": self.current_theta
            },
            "current_goal": {
                "x": self.current_goal.x,
                "y": self.current_goal.y
            } if self.current_goal else None,
            "path_progress": {
                "total_points": len(self.current_path),
                "current_index": self.path_index,
                "progress": (self.path_index / len(self.current_path) * 100) if self.current_path else 0
            },
            "obstacles": len(self.dynamic_obstacles),
            "grid": {
                "width": self.grid.grid_width,
                "height": self.grid.grid_height,
                "resolution": self.grid.resolution
            }
        } 