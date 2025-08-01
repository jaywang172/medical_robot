"""
事件總線實現
提供事件發佈、訂閱和分發機制
"""

import asyncio
import weakref
from typing import Dict, List, Callable, Optional, Set, Any
from collections import defaultdict, deque
from loguru import logger

from .events import RobotEvent, EventType


class EventBus:
    """
    異步事件總線
    
    功能：
    - 事件發佈和訂閱
    - 異步事件處理
    - 事件過濾和路由
    - 事件歷史記錄
    - 性能監控
    """
    
    def __init__(self, max_history: int = 1000):
        # 訂閱者管理：event_type -> [handler_function]
        self._subscribers: Dict[EventType, List[Callable]] = defaultdict(list)
        
        # 事件佇列：用於異步處理
        self._event_queue: asyncio.Queue = asyncio.Queue()
        
        # 事件歷史：用於除錯和分析
        self._event_history: deque = deque(maxlen=max_history)
        
        # 統計資料
        self._stats: Dict[str, int] = defaultdict(int)
        
        # 事件處理任務
        self._processor_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        # 弱引用訂閱者（防止記憶體洩漏）
        self._weak_subscribers: Dict[EventType, Set[Any]] = defaultdict(set)
        
        logger.info("🚌 事件總線已初始化")
    
    async def start(self):
        """啟動事件總線"""
        if self._is_running:
            return
        
        self._is_running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("🚀 事件總線已啟動")
    
    async def stop(self):
        """停止事件總線"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 事件總線已停止")
    
    def subscribe(self, event_type: EventType, handler: Callable, weak_ref: bool = False):
        """
        訂閱事件
        
        Args:
            event_type: 事件類型
            handler: 處理函數
            weak_ref: 是否使用弱引用（防止記憶體洩漏）
        """
        if weak_ref:
            self._weak_subscribers[event_type].add(weakref.ref(handler))
        else:
            self._subscribers[event_type].append(handler)
        
        logger.debug(f"📋 已訂閱事件類型: {event_type.value}")
    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """取消訂閱事件"""
        if handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)
            logger.debug(f"📋 已取消訂閱事件類型: {event_type.value}")
    
    async def publish(self, event: RobotEvent, priority: int = 0):
        """
        發佈事件
        
        Args:
            event: 事件對象
            priority: 優先級（數字越小優先級越高）
        """
        # 將事件加入佇列
        await self._event_queue.put((priority, event))
        
        # 更新統計
        self._stats['events_published'] += 1
        self._stats[f'events_{event.event_type.value}'] += 1
        
        logger.debug(f"📤 已發佈事件: {event.event_type.value} from {event.source}")
    
    async def publish_sync(self, event: RobotEvent):
        """同步發佈事件（立即處理）"""
        await self._handle_event(event)
    
    async def _process_events(self):
        """事件處理循環"""
        while self._is_running:
            try:
                # 獲取事件（優先級排序）
                priority, event = await self._event_queue.get()
                
                # 處理事件
                await self._handle_event(event)
                
                # 標記任務完成
                self._event_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ 事件處理異常: {e}")
                await asyncio.sleep(0.1)
    
    async def _handle_event(self, event: RobotEvent):
        """處理單個事件"""
        try:
            # 記錄事件歷史
            self._event_history.append({
                'timestamp': event.timestamp,
                'event_type': event.event_type.value,
                'source': event.source,
                'event_id': event.event_id
            })
            
            # 獲取訂閱者
            handlers = self._subscribers.get(event.event_type, [])
            
            # 清理弱引用訂閱者
            weak_handlers = []
            if event.event_type in self._weak_subscribers:
                for weak_ref in list(self._weak_subscribers[event.event_type]):
                    handler = weak_ref()
                    if handler is None:
                        # 物件已被垃圾回收
                        self._weak_subscribers[event.event_type].remove(weak_ref)
                    else:
                        weak_handlers.append(handler)
            
            all_handlers = handlers + weak_handlers
            
            if not all_handlers:
                logger.debug(f"⚠️ 沒有訂閱者處理事件: {event.event_type.value}")
                return
            
            # 異步並行處理所有訂閱者
            tasks = []
            for handler in all_handlers:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(asyncio.create_task(handler(event)))
                else:
                    # 同步函數，在執行器中運行
                    tasks.append(asyncio.create_task(
                        asyncio.get_event_loop().run_in_executor(None, handler, event)
                    ))
            
            # 等待所有處理器完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 檢查結果
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"❌ 事件處理器異常: {result}")
            
            # 更新統計
            self._stats['events_processed'] += 1
            
            logger.debug(f"✅ 事件已處理: {event.event_type.value}, {len(all_handlers)}個處理器")
            
        except Exception as e:
            logger.error(f"❌ 事件處理失敗: {e}")
    
    def get_subscribers_count(self, event_type: EventType) -> int:
        """獲取特定事件類型的訂閱者數量"""
        normal_count = len(self._subscribers.get(event_type, []))
        weak_count = len(self._weak_subscribers.get(event_type, set()))
        return normal_count + weak_count
    
    def get_stats(self) -> Dict[str, Any]:
        """獲取事件總線統計資料"""
        return {
            'is_running': self._is_running,
            'queue_size': self._event_queue.qsize(),
            'history_size': len(self._event_history),
            'subscribers_by_type': {
                event_type.value: self.get_subscribers_count(event_type)
                for event_type in EventType
            },
            'stats': dict(self._stats)
        }
    
    def get_recent_events(self, limit: int = 10) -> List[Dict]:
        """獲取最近的事件歷史"""
        return list(self._event_history)[-limit:]
    
    def clear_history(self):
        """清空事件歷史"""
        self._event_history.clear()
        logger.info("🗑️ 事件歷史已清空")


# 全域事件總線實例
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """獲取全域事件總線實例"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


async def initialize_event_bus():
    """初始化全域事件總線"""
    bus = get_event_bus()
    await bus.start()
    return bus


async def shutdown_event_bus():
    """關閉全域事件總線"""
    global _global_event_bus
    if _global_event_bus:
        await _global_event_bus.stop()
        _global_event_bus = None