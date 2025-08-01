"""
感測器融合模組
結合里程計和IMU數據提供更精確的位姿估計
"""

import math
import time
import asyncio
import numpy as np
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from loguru import logger

from .odometry import Odometry, Pose2D, OdometryData
from robot_core.events.event_bus import get_event_bus
from robot_core.events.events import create_navigation_event


@dataclass
class IMUData:
    """IMU數據結構"""
    acceleration_x: float = 0.0     # 加速度 X軸 (m/s²)
    acceleration_y: float = 0.0     # 加速度 Y軸 (m/s²)
    acceleration_z: float = 0.0     # 加速度 Z軸 (m/s²)
    
    angular_velocity_x: float = 0.0  # 角速度 X軸 (rad/s)
    angular_velocity_y: float = 0.0  # 角速度 Y軸 (rad/s) 
    angular_velocity_z: float = 0.0  # 角速度 Z軸 (rad/s)
    
    magnetic_x: float = 0.0         # 磁力計 X軸
    magnetic_y: float = 0.0         # 磁力計 Y軸
    magnetic_z: float = 0.0         # 磁力計 Z軸
    
    timestamp: float = 0.0


@dataclass
class FusedPose:
    """融合後的位姿數據"""
    pose: Pose2D
    
    # 速度信息
    linear_velocity: float = 0.0
    angular_velocity: float = 0.0
    
    # 加速度信息
    linear_acceleration: float = 0.0
    angular_acceleration: float = 0.0
    
    # 置信度
    position_confidence: float = 1.0
    orientation_confidence: float = 1.0
    
    # 各感測器權重
    odometry_weight: float = 0.7
    imu_weight: float = 0.3


class ExtendedKalmanFilter:
    """
    擴展卡爾曼濾波器
    用於融合里程計和IMU數據
    """
    
    def __init__(self):
        # 狀態向量 [x, y, theta, vx, vy, omega]
        self.state = np.zeros(6)
        
        # 狀態協方差矩陣
        self.P = np.eye(6) * 0.1
        
        # 過程噪聲協方差
        self.Q = np.diag([0.01, 0.01, 0.01, 0.1, 0.1, 0.1])
        
        # 觀測噪聲協方差
        self.R_odometry = np.diag([0.1, 0.1, 0.1])      # 里程計噪聲
        self.R_imu = np.diag([0.05, 0.05, 0.01])        # IMU噪聲
        
        self.last_update_time = time.time()
    
    def predict(self, dt: float):
        """預測步驟"""
        # 狀態轉移矩陣
        F = np.array([
            [1, 0, 0, dt, 0,  0],
            [0, 1, 0, 0,  dt, 0],
            [0, 0, 1, 0,  0,  dt],
            [0, 0, 0, 1,  0,  0],
            [0, 0, 0, 0,  1,  0],
            [0, 0, 0, 0,  0,  1]
        ])
        
        # 預測狀態
        self.state = F @ self.state
        
        # 預測協方差
        self.P = F @ self.P @ F.T + self.Q * dt
    
    def update_odometry(self, pose: Pose2D, linear_vel: float, angular_vel: float):
        """使用里程計數據更新"""
        # 觀測向量 [x, y, theta]
        z = np.array([pose.x, pose.y, pose.theta])
        
        # 觀測矩陣
        H = np.array([
            [1, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0]
        ])
        
        # 創新（觀測殘差）
        y = z - H @ self.state
        
        # 處理角度差異
        while y[2] > math.pi:
            y[2] -= 2 * math.pi
        while y[2] < -math.pi:
            y[2] += 2 * math.pi
        
        # 創新協方差
        S = H @ self.P @ H.T + self.R_odometry
        
        # 卡爾曼增益
        K = self.P @ H.T @ np.linalg.inv(S)
        
        # 更新狀態
        self.state = self.state + K @ y
        
        # 更新協方差
        I = np.eye(6)
        self.P = (I - K @ H) @ self.P
        
        # 更新速度
        self.state[3] = linear_vel * math.cos(self.state[2])
        self.state[4] = linear_vel * math.sin(self.state[2])
        self.state[5] = angular_vel
    
    def update_imu(self, imu_data: IMUData):
        """使用IMU數據更新"""
        # 使用角速度更新方向
        z = np.array([
            imu_data.angular_velocity_z,  # 繞Z軸角速度
            imu_data.acceleration_x,      # X軸加速度
            imu_data.acceleration_y       # Y軸加速度
        ])
        
        # 觀測矩陣（簡化）
        H = np.array([
            [0, 0, 0, 0, 0, 1],  # 角速度
            [0, 0, 0, 1, 0, 0],  # X軸加速度對應vx的變化率
            [0, 0, 0, 0, 1, 0]   # Y軸加速度對應vy的變化率
        ])
        
        # 創新
        y = z - H @ self.state
        
        # 創新協方差
        S = H @ self.P @ H.T + self.R_imu
        
        # 卡爾曼增益
        K = self.P @ H.T @ np.linalg.inv(S)
        
        # 更新狀態
        self.state = self.state + K @ y
        
        # 更新協方差
        I = np.eye(6)
        self.P = (I - K @ H) @ self.P
    
    def get_pose(self) -> Pose2D:
        """獲取當前位姿"""
        return Pose2D(
            x=float(self.state[0]),
            y=float(self.state[1]),
            theta=float(self.state[2]),
            timestamp=time.time()
        )
    
    def get_velocities(self) -> Tuple[float, float]:
        """獲取線速度和角速度"""
        vx, vy = self.state[3], self.state[4]
        linear_vel = math.sqrt(vx*vx + vy*vy)
        angular_vel = float(self.state[5])
        return linear_vel, angular_vel


class SensorFusion:
    """
    感測器融合系統
    
    功能：
    - 融合里程計和IMU數據
    - 提供更精確的位姿估計
    - 檢測和處理感測器故障
    - 自適應權重調整
    """
    
    def __init__(self, odometry: Odometry):
        self.odometry = odometry
        
        # 卡爾曼濾波器
        self.ekf = ExtendedKalmanFilter()
        
        # 融合後的位姿
        self._fused_pose = FusedPose(pose=Pose2D())
        
        # IMU數據緩存
        self._imu_data: Optional[IMUData] = None
        self._imu_data_timeout = 1.0  # IMU數據超時時間
        
        # 感測器健康狀態
        self._odometry_healthy = True
        self._imu_healthy = True
        
        # 自適應權重
        self._adaptive_weights = True
        
        # 更新頻率控制
        self._update_interval = 0.02  # 50Hz
        self._last_update_time = 0.0
        
        # 事件總線
        self._event_bus = get_event_bus()
        
        # 融合任務
        self._fusion_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        logger.info("🔀 感測器融合系統已初始化")
    
    async def start(self):
        """啟動感測器融合"""
        if self._is_running:
            return
        
        self._is_running = True
        self._fusion_task = asyncio.create_task(self._fusion_loop())
        logger.info("🚀 感測器融合循環已啟動")
    
    async def stop(self):
        """停止感測器融合"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._fusion_task:
            self._fusion_task.cancel()
            try:
                await self._fusion_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 感測器融合循環已停止")
    
    async def _fusion_loop(self):
        """感測器融合循環"""
        while self._is_running:
            try:
                current_time = time.time()
                
                if current_time - self._last_update_time >= self._update_interval:
                    await self.update()
                    self._last_update_time = current_time
                
                await asyncio.sleep(0.005)  # 5ms
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 感測器融合異常: {e}")
                await asyncio.sleep(0.1)
    
    async def update(self):
        """更新感測器融合"""
        try:
            current_time = time.time()
            dt = current_time - self.ekf.last_update_time
            
            if dt <= 0:
                return
            
            # 預測步驟
            self.ekf.predict(dt)
            
            # 檢查感測器健康狀態
            self._check_sensor_health()
            
            # 里程計更新
            if self._odometry_healthy:
                odometry_data = self.odometry.get_odometry_data()
                self.ekf.update_odometry(
                    odometry_data.pose,
                    odometry_data.linear_velocity,
                    odometry_data.angular_velocity
                )
            
            # IMU更新
            if self._imu_healthy and self._imu_data:
                if current_time - self._imu_data.timestamp <= self._imu_data_timeout:
                    self.ekf.update_imu(self._imu_data)
            
            # 生成融合結果
            self._generate_fused_pose()
            
            # 發佈融合結果事件
            await self._publish_fused_pose_event()
            
            self.ekf.last_update_time = current_time
            
        except Exception as e:
            logger.error(f"❌ 感測器融合更新失敗: {e}")
    
    def _check_sensor_health(self):
        """檢查感測器健康狀態"""
        current_time = time.time()
        
        # 檢查里程計健康狀態
        odometry_data = self.odometry.get_odometry_data()
        self._odometry_healthy = (
            odometry_data.confidence > 0.5 and
            current_time - odometry_data.pose.timestamp <= 1.0
        )
        
        # 檢查IMU健康狀態
        if self._imu_data:
            self._imu_healthy = (
                current_time - self._imu_data.timestamp <= self._imu_data_timeout
            )
        else:
            self._imu_healthy = False
    
    def _generate_fused_pose(self):
        """生成融合後的位姿"""
        # 從卡爾曼濾波器獲取位姿
        fused_pose_2d = self.ekf.get_pose()
        linear_vel, angular_vel = self.ekf.get_velocities()
        
        # 計算置信度
        position_confidence = self._calculate_position_confidence()
        orientation_confidence = self._calculate_orientation_confidence()
        
        # 計算權重
        if self._adaptive_weights:
            odometry_weight, imu_weight = self._calculate_adaptive_weights()
        else:
            odometry_weight, imu_weight = 0.7, 0.3
        
        # 更新融合位姿
        self._fused_pose = FusedPose(
            pose=fused_pose_2d,
            linear_velocity=linear_vel,
            angular_velocity=angular_vel,
            position_confidence=position_confidence,
            orientation_confidence=orientation_confidence,
            odometry_weight=odometry_weight,
            imu_weight=imu_weight
        )
    
    def _calculate_position_confidence(self) -> float:
        """計算位置置信度"""
        # 基於卡爾曼濾波器的協方差矩陣
        position_variance = self.ekf.P[0, 0] + self.ekf.P[1, 1]
        max_variance = 1.0
        return max(0.0, 1.0 - position_variance / max_variance)
    
    def _calculate_orientation_confidence(self) -> float:
        """計算方向置信度"""
        # 基於卡爾曼濾波器的角度方差
        angle_variance = self.ekf.P[2, 2]
        max_variance = 0.1  # 約6度
        return max(0.0, 1.0 - angle_variance / max_variance)
    
    def _calculate_adaptive_weights(self) -> Tuple[float, float]:
        """計算自適應權重"""
        # 基於感測器健康狀態和置信度
        odometry_score = 1.0 if self._odometry_healthy else 0.0
        imu_score = 1.0 if self._imu_healthy else 0.0
        
        # 如果有里程計數據，加入置信度
        if self._odometry_healthy:
            odometry_data = self.odometry.get_odometry_data()
            odometry_score *= odometry_data.confidence
        
        total_score = odometry_score + imu_score
        
        if total_score > 0:
            odometry_weight = odometry_score / total_score
            imu_weight = imu_score / total_score
        else:
            # 默認權重
            odometry_weight, imu_weight = 0.7, 0.3
        
        return odometry_weight, imu_weight
    
    async def _publish_fused_pose_event(self):
        """發佈融合位姿事件"""
        try:
            event = create_navigation_event(
                source="SensorFusion",
                current_position={
                    'x': self._fused_pose.pose.x,
                    'y': self._fused_pose.pose.y,
                    'theta': self._fused_pose.pose.theta
                },
                navigation_state="pose_fused"
            )
            
            event.data.update({
                'linear_velocity': self._fused_pose.linear_velocity,
                'angular_velocity': self._fused_pose.angular_velocity,
                'position_confidence': self._fused_pose.position_confidence,
                'orientation_confidence': self._fused_pose.orientation_confidence,
                'sensor_weights': {
                    'odometry': self._fused_pose.odometry_weight,
                    'imu': self._fused_pose.imu_weight
                },
                'sensor_health': {
                    'odometry': self._odometry_healthy,
                    'imu': self._imu_healthy
                }
            })
            
            await self._event_bus.publish(event, priority=0)  # 高優先級
            
        except Exception as e:
            logger.error(f"❌ 發佈融合位姿事件失敗: {e}")
    
    def update_imu_data(self, imu_data: IMUData):
        """更新IMU數據"""
        self._imu_data = imu_data
    
    def get_fused_pose(self) -> FusedPose:
        """獲取融合後的位姿"""
        return self._fused_pose
    
    def reset_fusion(self, pose: Optional[Pose2D] = None):
        """重置融合系統"""
        if pose:
            self.ekf.state[0] = pose.x
            self.ekf.state[1] = pose.y
            self.ekf.state[2] = pose.theta
            self.ekf.state[3:] = 0.0
        else:
            self.ekf.state = np.zeros(6)
        
        self.ekf.P = np.eye(6) * 0.1
        logger.info("🔄 感測器融合已重置")
    
    def get_status(self) -> Dict[str, Any]:
        """獲取融合系統狀態"""
        return {
            'is_running': self._is_running,
            'fused_pose': self._fused_pose.pose.to_dict(),
            'velocities': {
                'linear': round(self._fused_pose.linear_velocity, 3),
                'angular': round(self._fused_pose.angular_velocity, 3)
            },
            'confidence': {
                'position': round(self._fused_pose.position_confidence, 3),
                'orientation': round(self._fused_pose.orientation_confidence, 3)
            },
            'sensor_weights': {
                'odometry': round(self._fused_pose.odometry_weight, 3),
                'imu': round(self._fused_pose.imu_weight, 3)
            },
            'sensor_health': {
                'odometry': self._odometry_healthy,
                'imu': self._imu_healthy
            },
            'adaptive_weights': self._adaptive_weights
        }