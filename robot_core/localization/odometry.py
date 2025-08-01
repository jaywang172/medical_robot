"""
機器人里程計實現
基於差速驅動運動學模型計算機器人位姿
"""

import math
import time
import asyncio
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass, field
from loguru import logger

from .encoder_reader import EncoderReader, EncoderConfig, EncoderData
from robot_core.events.event_bus import get_event_bus
from robot_core.events.events import create_navigation_event


@dataclass
class Pose2D:
    """2D位姿（位置和方向）"""
    x: float = 0.0      # X座標 (米)
    y: float = 0.0      # Y座標 (米)  
    theta: float = 0.0  # 方向角 (弧度)
    timestamp: float = field(default_factory=time.time)
    
    def __post_init__(self):
        """標準化角度到 [-π, π]"""
        self.normalize_angle()
    
    def normalize_angle(self):
        """將角度標準化到 [-π, π] 範圍"""
        while self.theta > math.pi:
            self.theta -= 2 * math.pi
        while self.theta < -math.pi:
            self.theta += 2 * math.pi
    
    def distance_to(self, other: 'Pose2D') -> float:
        """計算到另一個位姿的歐氏距離"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def angle_to(self, other: 'Pose2D') -> float:
        """計算到另一個位姿的角度"""
        return math.atan2(other.y - self.y, other.x - self.x)
    
    def copy(self) -> 'Pose2D':
        """創建副本"""
        return Pose2D(self.x, self.y, self.theta, self.timestamp)
    
    def to_dict(self) -> Dict[str, float]:
        """轉換為字典格式"""
        return {
            'x': self.x,
            'y': self.y, 
            'theta': self.theta,
            'timestamp': self.timestamp
        }


@dataclass
class OdometryData:
    """里程計數據"""
    pose: Pose2D
    linear_velocity: float = 0.0   # 線速度 (米/秒)
    angular_velocity: float = 0.0  # 角速度 (弧度/秒)
    left_wheel_velocity: float = 0.0
    right_wheel_velocity: float = 0.0
    total_distance: float = 0.0    # 總行駛距離
    confidence: float = 1.0        # 位姿置信度


class Odometry:
    """
    機器人里程計系統
    
    功能：
    - 基於輪式編碼器計算位姿
    - 差速驅動運動學模型
    - 位姿誤差估計
    - 里程計重置和校準
    """
    
    def __init__(self, encoder_config: EncoderConfig):
        self.config = encoder_config
        
        # 編碼器讀取器
        self.encoder_reader = EncoderReader(encoder_config)
        
        # 當前位姿
        self._current_pose = Pose2D()
        
        # 上一次更新的位姿（用於計算增量）
        self._last_pose = Pose2D()
        
        # 運動狀態
        self._linear_velocity = 0.0
        self._angular_velocity = 0.0
        self._left_wheel_velocity = 0.0
        self._right_wheel_velocity = 0.0
        
        # 累積距離
        self._total_distance = 0.0
        
        # 位姿協方差（簡化的誤差模型）
        self._position_variance = 0.001  # 位置方差 (米²)
        self._angle_variance = 0.001     # 角度方差 (弧度²)
        
        # 運動學參數
        self._wheel_base = encoder_config.wheel_base
        self._wheel_radius = encoder_config.wheel_radius
        
        # 更新頻率控制
        self._update_interval = 0.02  # 50Hz
        self._last_update_time = 0.0
        
        # 事件總線
        self._event_bus = get_event_bus()
        
        # 里程計任務
        self._odometry_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        logger.info("📍 里程計系統已初始化")
    
    async def initialize(self):
        """初始化里程計系統"""
        try:
            # 初始化編碼器
            await self.encoder_reader.initialize()
            
            # 重置位姿
            self.reset_pose()
            
            logger.success("✅ 里程計系統初始化完成")
            
        except Exception as e:
            logger.error(f"❌ 里程計初始化失敗: {e}")
            raise
    
    async def start(self):
        """啟動里程計更新循環"""
        if self._is_running:
            return
        
        self._is_running = True
        self._odometry_task = asyncio.create_task(self._update_loop())
        logger.info("🚀 里程計更新循環已啟動")
    
    async def stop(self):
        """停止里程計更新循環"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._odometry_task:
            self._odometry_task.cancel()
            try:
                await self._odometry_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 里程計更新循環已停止")
    
    async def _update_loop(self):
        """里程計更新循環"""
        while self._is_running:
            try:
                current_time = time.time()
                
                # 控制更新頻率
                if current_time - self._last_update_time >= self._update_interval:
                    await self.update()
                    self._last_update_time = current_time
                
                # 避免過度佔用CPU
                await asyncio.sleep(0.005)  # 5ms
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 里程計更新異常: {e}")
                await asyncio.sleep(0.1)
    
    async def update(self):
        """更新里程計"""
        try:
            # 獲取編碼器增量數據
            left_delta, right_delta, dt = self.encoder_reader.get_incremental_data()
            
            if dt <= 0:
                return
            
            # 計算輪子移動距離
            left_distance = self.encoder_reader.pulses_to_distance(left_delta)
            right_distance = self.encoder_reader.pulses_to_distance(right_delta)
            
            # 計算輪子速度
            encoder_data = self.encoder_reader.get_encoder_data()
            self._left_wheel_velocity = encoder_data.left_velocity
            self._right_wheel_velocity = encoder_data.right_velocity
            
            # 使用差速驅動運動學模型更新位姿
            self._update_pose_with_kinematics(left_distance, right_distance, dt)
            
            # 發佈位姿更新事件
            await self._publish_pose_event()
            
        except Exception as e:
            logger.error(f"❌ 里程計更新失敗: {e}")
    
    def _update_pose_with_kinematics(self, left_distance: float, right_distance: float, dt: float):
        """
        使用差速驅動運動學模型更新位姿
        
        Args:
            left_distance: 左輪移動距離 (米)
            right_distance: 右輪移動距離 (米) 
            dt: 時間間隔 (秒)
        """
        # 計算機器人中心的移動距離和轉角
        center_distance = (left_distance + right_distance) / 2.0
        delta_theta = (right_distance - left_distance) / self._wheel_base
        
        # 更新累積距離
        self._total_distance += abs(center_distance)
        
        # 計算速度
        self._linear_velocity = center_distance / dt if dt > 0 else 0.0
        self._angular_velocity = delta_theta / dt if dt > 0 else 0.0
        
        # 保存當前位姿作為上一個位姿
        self._last_pose = self._current_pose.copy()
        
        # 更新位姿
        if abs(delta_theta) < 1e-6:
            # 直線運動
            self._current_pose.x += center_distance * math.cos(self._current_pose.theta)
            self._current_pose.y += center_distance * math.sin(self._current_pose.theta)
        else:
            # 圓弧運動
            radius = center_distance / delta_theta
            
            # 計算圓弧運動的位姿變化
            dx = radius * (math.sin(self._current_pose.theta + delta_theta) - math.sin(self._current_pose.theta))
            dy = radius * (math.cos(self._current_pose.theta) - math.cos(self._current_pose.theta + delta_theta))
            
            self._current_pose.x += dx
            self._current_pose.y += dy
        
        # 更新方向角
        self._current_pose.theta += delta_theta
        self._current_pose.normalize_angle()
        
        # 更新時間戳
        self._current_pose.timestamp = time.time()
        
        # 更新位姿協方差（簡化模型）
        distance_factor = abs(center_distance)
        rotation_factor = abs(delta_theta)
        
        self._position_variance += distance_factor * 0.001 + rotation_factor * 0.0001
        self._angle_variance += rotation_factor * 0.001 + distance_factor * 0.0001
    
    async def _publish_pose_event(self):
        """發佈位姿更新事件"""
        try:
            event = create_navigation_event(
                source="Odometry",
                current_position={
                    'x': self._current_pose.x,
                    'y': self._current_pose.y,
                    'theta': self._current_pose.theta
                },
                navigation_state="pose_updated"
            )
            
            event.data.update({
                'linear_velocity': self._linear_velocity,
                'angular_velocity': self._angular_velocity,
                'total_distance': self._total_distance,
                'confidence': self.get_confidence()
            })
            
            await self._event_bus.publish(event, priority=1)
            
        except Exception as e:
            logger.error(f"❌ 發佈位姿事件失敗: {e}")
    
    def get_pose(self) -> Pose2D:
        """獲取當前位姿"""
        return self._current_pose.copy()
    
    def get_odometry_data(self) -> OdometryData:
        """獲取完整的里程計數據"""
        return OdometryData(
            pose=self._current_pose.copy(),
            linear_velocity=self._linear_velocity,
            angular_velocity=self._angular_velocity,
            left_wheel_velocity=self._left_wheel_velocity,
            right_wheel_velocity=self._right_wheel_velocity,
            total_distance=self._total_distance,
            confidence=self.get_confidence()
        )
    
    def get_confidence(self) -> float:
        """
        獲取位姿置信度
        
        Returns:
            float: 置信度 (0.0-1.0)
        """
        # 簡化的置信度模型：基於累積誤差
        max_variance = 1.0  # 最大可接受的方差
        position_confidence = max(0.0, 1.0 - self._position_variance / max_variance)
        angle_confidence = max(0.0, 1.0 - self._angle_variance / max_variance)
        
        return min(position_confidence, angle_confidence)
    
    def reset_pose(self, pose: Optional[Pose2D] = None):
        """
        重置位姿
        
        Args:
            pose: 新的位姿，如果為None則重置為原點
        """
        if pose is None:
            self._current_pose = Pose2D()
        else:
            self._current_pose = pose.copy()
        
        self._last_pose = self._current_pose.copy()
        
        # 重置誤差
        self._position_variance = 0.001
        self._angle_variance = 0.001
        
        # 重置編碼器
        self.encoder_reader.reset_counters()
        
        # 重置距離
        self._total_distance = 0.0
        
        logger.info(f"🔄 位姿已重置: ({self._current_pose.x:.3f}, {self._current_pose.y:.3f}, {self._current_pose.theta:.3f})")
    
    def set_pose(self, x: float, y: float, theta: float):
        """設置位姿（例如從外部定位系統獲得）"""
        self._current_pose.x = x
        self._current_pose.y = y
        self._current_pose.theta = theta
        self._current_pose.normalize_angle()
        self._current_pose.timestamp = time.time()
        
        # 重置誤差（因為有了新的參考）
        self._position_variance = 0.001
        self._angle_variance = 0.001
        
        logger.info(f"📍 位姿已設置: ({x:.3f}, {y:.3f}, {theta:.3f})")
    
    def get_motion_since_last_update(self) -> Tuple[float, float, float]:
        """
        獲取自上次更新以來的運動
        
        Returns:
            Tuple[float, float, float]: (dx, dy, dtheta)
        """
        dx = self._current_pose.x - self._last_pose.x
        dy = self._current_pose.y - self._last_pose.y
        dtheta = self._current_pose.theta - self._last_pose.theta
        
        # 處理角度跳躍
        while dtheta > math.pi:
            dtheta -= 2 * math.pi
        while dtheta < -math.pi:
            dtheta += 2 * math.pi
        
        return dx, dy, dtheta
    
    async def cleanup(self):
        """清理資源"""
        await self.stop()
        await self.encoder_reader.cleanup()
        logger.info("🧹 里程計系統已清理")
    
    def get_status(self) -> Dict[str, Any]:
        """獲取里程計狀態"""
        odometry_data = self.get_odometry_data()
        
        return {
            'is_running': self._is_running,
            'current_pose': odometry_data.pose.to_dict(),
            'velocities': {
                'linear': round(odometry_data.linear_velocity, 3),
                'angular': round(odometry_data.angular_velocity, 3),
                'left_wheel': round(odometry_data.left_wheel_velocity, 3),
                'right_wheel': round(odometry_data.right_wheel_velocity, 3)
            },
            'total_distance': round(odometry_data.total_distance, 3),
            'confidence': round(odometry_data.confidence, 3),
            'encoder_status': self.encoder_reader.get_status()
        }