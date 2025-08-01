"""
機器人中央狀態機實現
管理機器人的整體狀態和狀態轉換邏輯
"""

import asyncio
import time
from enum import Enum
from typing import Dict, List, Optional, Callable, Set, Any
from dataclasses import dataclass
from loguru import logger

from robot_core.events.event_bus import get_event_bus
from robot_core.events.events import create_system_state_event, EventType


class RobotState(Enum):
    """機器人系統狀態"""
    # 初始化狀態
    INITIALIZING = "initializing"
    
    # 正常運行狀態
    IDLE = "idle"                    # 空閒等待
    NAVIGATING = "navigating"        # 導航移動
    MAPPING = "mapping"              # 地圖構建
    CHARGING = "charging"            # 充電中
    
    # 特殊操作狀態
    MANUAL_CONTROL = "manual_control"  # 手動控制
    CALIBRATING = "calibrating"       # 感測器校準
    UPDATING = "updating"             # 系統更新
    
    # 異常和恢復狀態
    EMERGENCY_STOP = "emergency_stop"  # 緊急停止
    ERROR = "error"                   # 錯誤狀態
    RECOVERING = "recovering"         # 恢復中
    
    # 關閉狀態
    SHUTTING_DOWN = "shutting_down"   # 關閉中
    SHUTDOWN = "shutdown"             # 已關閉


class StateChangeReason(Enum):
    """狀態變化原因"""
    # 系統控制
    SYSTEM_INIT = "system_init"
    SYSTEM_SHUTDOWN = "system_shutdown"
    USER_COMMAND = "user_command"
    
    # 任務相關
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    NEW_TASK_ASSIGNED = "new_task_assigned"
    
    # 安全相關
    OBSTACLE_DETECTED = "obstacle_detected"
    SENSOR_FAILURE = "sensor_failure"
    LOW_BATTERY = "low_battery"
    EMERGENCY_BUTTON = "emergency_button"
    
    # 自動恢復
    AUTO_RECOVERY = "auto_recovery"
    MANUAL_RECOVERY = "manual_recovery"
    
    # 維護
    CALIBRATION_REQUIRED = "calibration_required"
    SYSTEM_UPDATE = "system_update"


@dataclass
class StateTransition:
    """狀態轉換記錄"""
    from_state: RobotState
    to_state: RobotState
    reason: StateChangeReason
    timestamp: float
    data: Dict[str, Any]
    success: bool = True


class RobotStateMachine:
    """
    機器人中央狀態機
    
    職責：
    - 管理系統的全域狀態
    - 控制狀態轉換邏輯
    - 確保狀態一致性
    - 提供狀態查詢和歷史
    """
    
    def __init__(self):
        # 當前狀態
        self._current_state = RobotState.INITIALIZING
        
        # 狀態轉換歷史
        self._state_history: List[StateTransition] = []
        
        # 狀態持續時間
        self._state_start_time = time.time()
        
        # 允許的狀態轉換規則
        self._transition_rules = self._build_transition_rules()
        
        # 狀態進入/退出回調
        self._state_enter_callbacks: Dict[RobotState, List[Callable]] = {}
        self._state_exit_callbacks: Dict[RobotState, List[Callable]] = {}
        
        # 狀態條件檢查器
        self._state_validators: Dict[RobotState, List[Callable]] = {}
        
        # 事件總線
        self._event_bus = get_event_bus()
        
        logger.info("🔄 機器人狀態機已初始化")
    
    def _build_transition_rules(self) -> Dict[RobotState, Set[RobotState]]:
        """定義允許的狀態轉換規則"""
        return {
            # 從初始化可以到任何狀態（系統啟動）
            RobotState.INITIALIZING: {
                RobotState.IDLE,
                RobotState.ERROR,
                RobotState.SHUTTING_DOWN
            },
            
            # 空閒狀態可以到達的狀態
            RobotState.IDLE: {
                RobotState.NAVIGATING,
                RobotState.MAPPING, 
                RobotState.CHARGING,
                RobotState.MANUAL_CONTROL,
                RobotState.CALIBRATING,
                RobotState.UPDATING,
                RobotState.EMERGENCY_STOP,
                RobotState.ERROR,
                RobotState.SHUTTING_DOWN
            },
            
            # 導航狀態轉換
            RobotState.NAVIGATING: {
                RobotState.IDLE,
                RobotState.EMERGENCY_STOP,
                RobotState.ERROR,
                RobotState.CHARGING,
                RobotState.MANUAL_CONTROL
            },
            
            # 地圖構建狀態轉換
            RobotState.MAPPING: {
                RobotState.IDLE,
                RobotState.EMERGENCY_STOP,
                RobotState.ERROR,
                RobotState.NAVIGATING
            },
            
            # 充電狀態轉換
            RobotState.CHARGING: {
                RobotState.IDLE,
                RobotState.EMERGENCY_STOP,
                RobotState.ERROR
            },
            
            # 手動控制狀態轉換
            RobotState.MANUAL_CONTROL: {
                RobotState.IDLE,
                RobotState.EMERGENCY_STOP,
                RobotState.ERROR
            },
            
            # 校準狀態轉換
            RobotState.CALIBRATING: {
                RobotState.IDLE,
                RobotState.ERROR,
                RobotState.EMERGENCY_STOP
            },
            
            # 更新狀態轉換
            RobotState.UPDATING: {
                RobotState.IDLE,
                RobotState.ERROR,
                RobotState.SHUTTING_DOWN
            },
            
            # 緊急停止狀態轉換
            RobotState.EMERGENCY_STOP: {
                RobotState.IDLE,
                RobotState.RECOVERING,
                RobotState.ERROR,
                RobotState.SHUTTING_DOWN
            },
            
            # 錯誤狀態轉換
            RobotState.ERROR: {
                RobotState.RECOVERING,
                RobotState.EMERGENCY_STOP,
                RobotState.SHUTTING_DOWN
            },
            
            # 恢復狀態轉換
            RobotState.RECOVERING: {
                RobotState.IDLE,
                RobotState.ERROR,
                RobotState.EMERGENCY_STOP
            },
            
            # 關閉中狀態轉換
            RobotState.SHUTTING_DOWN: {
                RobotState.SHUTDOWN
            },
            
            # 已關閉狀態（終極狀態）
            RobotState.SHUTDOWN: set()
        }
    
    async def transition_to(self, 
                           new_state: RobotState, 
                           reason: StateChangeReason,
                           data: Optional[Dict[str, Any]] = None) -> bool:
        """
        轉換到新狀態
        
        Args:
            new_state: 目標狀態
            reason: 轉換原因
            data: 附加數據
            
        Returns:
            bool: 轉換是否成功
        """
        if data is None:
            data = {}
        
        # 檢查轉換是否允許
        if not self._is_transition_allowed(self._current_state, new_state):
            logger.warning(f"❌ 不允許的狀態轉換: {self._current_state.value} -> {new_state.value}")
            return False
        
        # 檢查新狀態的前置條件
        if not await self._validate_state_conditions(new_state, data):
            logger.warning(f"❌ 狀態條件不滿足: {new_state.value}")
            return False
        
        old_state = self._current_state
        
        try:
            # 執行狀態退出回調
            await self._execute_exit_callbacks(old_state)
            
            # 記錄狀態轉換
            transition = StateTransition(
                from_state=old_state,
                to_state=new_state,
                reason=reason,
                timestamp=time.time(),
                data=data
            )
            self._state_history.append(transition)
            
            # 更新當前狀態
            self._current_state = new_state
            self._state_start_time = time.time()
            
            # 執行狀態進入回調
            await self._execute_enter_callbacks(new_state)
            
            # 發佈狀態變化事件
            await self._publish_state_change_event(old_state, new_state, reason, data)
            
            logger.info(f"🔄 狀態轉換成功: {old_state.value} -> {new_state.value} ({reason.value})")
            return True
            
        except Exception as e:
            logger.error(f"❌ 狀態轉換失敗: {e}")
            
            # 記錄失敗的轉換
            failed_transition = StateTransition(
                from_state=old_state,
                to_state=new_state,
                reason=reason,
                timestamp=time.time(),
                data=data,
                success=False
            )
            self._state_history.append(failed_transition)
            
            return False
    
    def _is_transition_allowed(self, from_state: RobotState, to_state: RobotState) -> bool:
        """檢查狀態轉換是否允許"""
        allowed_states = self._transition_rules.get(from_state, set())
        return to_state in allowed_states
    
    async def _validate_state_conditions(self, state: RobotState, data: Dict[str, Any]) -> bool:
        """驗證狀態的前置條件"""
        validators = self._state_validators.get(state, [])
        
        for validator in validators:
            try:
                if asyncio.iscoroutinefunction(validator):
                    result = await validator(state, data)
                else:
                    result = validator(state, data)
                
                if not result:
                    return False
            except Exception as e:
                logger.error(f"❌ 狀態驗證器異常: {e}")
                return False
        
        return True
    
    async def _execute_enter_callbacks(self, state: RobotState):
        """執行狀態進入回調"""
        callbacks = self._state_enter_callbacks.get(state, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(state)
                else:
                    callback(state)
            except Exception as e:
                logger.error(f"❌ 狀態進入回調異常: {e}")
    
    async def _execute_exit_callbacks(self, state: RobotState):
        """執行狀態退出回調"""
        callbacks = self._state_exit_callbacks.get(state, [])
        
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(state)
                else:
                    callback(state)
            except Exception as e:
                logger.error(f"❌ 狀態退出回調異常: {e}")
    
    async def _publish_state_change_event(self, 
                                        old_state: RobotState, 
                                        new_state: RobotState,
                                        reason: StateChangeReason,
                                        data: Dict[str, Any]):
        """發佈狀態變化事件"""
        event = create_system_state_event(
            source="RobotStateMachine",
            old_state=old_state.value,
            new_state=new_state.value,
            reason=reason.value
        )
        event.data.update(data)
        
        await self._event_bus.publish(event)
    
    # 回調管理方法
    def on_state_enter(self, state: RobotState, callback: Callable):
        """註冊狀態進入回調"""
        if state not in self._state_enter_callbacks:
            self._state_enter_callbacks[state] = []
        self._state_enter_callbacks[state].append(callback)
    
    def on_state_exit(self, state: RobotState, callback: Callable):
        """註冊狀態退出回調"""
        if state not in self._state_exit_callbacks:
            self._state_exit_callbacks[state] = []
        self._state_exit_callbacks[state].append(callback)
    
    def add_state_validator(self, state: RobotState, validator: Callable):
        """添加狀態驗證器"""
        if state not in self._state_validators:
            self._state_validators[state] = []
        self._state_validators[state].append(validator)
    
    # 查詢方法
    @property
    def current_state(self) -> RobotState:
        """獲取當前狀態"""
        return self._current_state
    
    def get_state_duration(self) -> float:
        """獲取當前狀態持續時間（秒）"""
        return time.time() - self._state_start_time
    
    def get_state_history(self, limit: Optional[int] = None) -> List[StateTransition]:
        """獲取狀態轉換歷史"""
        if limit is None:
            return self._state_history.copy()
        return self._state_history[-limit:]
    
    def is_in_state(self, *states: RobotState) -> bool:
        """檢查是否處於指定狀態之一"""
        return self._current_state in states
    
    def can_transition_to(self, state: RobotState) -> bool:
        """檢查是否可以轉換到指定狀態"""
        return self._is_transition_allowed(self._current_state, state)
    
    def get_available_transitions(self) -> Set[RobotState]:
        """獲取當前狀態可以轉換到的所有狀態"""
        return self._transition_rules.get(self._current_state, set()).copy()
    
    def get_status(self) -> Dict[str, Any]:
        """獲取狀態機完整狀態資訊"""
        return {
            'current_state': self._current_state.value,
            'state_duration': self.get_state_duration(),
            'available_transitions': [s.value for s in self.get_available_transitions()],
            'history_count': len(self._state_history),
            'last_transition': self._state_history[-1].__dict__ if self._state_history else None
        }