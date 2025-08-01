#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日誌系統配置
提供統一的日誌記錄功能
"""

import sys
from pathlib import Path
from loguru import logger
from datetime import datetime


def setup_logger(log_level: str = "INFO", log_dir: Path = None):
    """
    設置日誌系統
    
    Args:
        log_level: 日誌等級 (DEBUG, INFO, WARNING, ERROR)
        log_dir: 日誌文件目錄
    """
    
    # 移除默認處理器
    logger.remove()
    
    # 設置日誌目錄
    if log_dir is None:
        log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # 控制台輸出格式
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 文件輸出格式
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # 添加控制台處理器
    logger.add(
        sys.stderr,
        format=console_format,
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # 添加一般日誌文件處理器
    today = datetime.now().strftime("%Y%m%d")
    logger.add(
        log_dir / f"robot_{today}.log",
        format=file_format,
        level="DEBUG",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        encoding="utf-8"
    )
    
    # 添加錯誤日誌文件處理器
    logger.add(
        log_dir / f"robot_error_{today}.log",
        format=file_format,
        level="ERROR",
        rotation="1 day",
        retention="90 days",
        compression="zip",
        encoding="utf-8"
    )
    
    # 設置性能日誌
    logger.add(
        log_dir / f"robot_performance_{today}.log",
        format=file_format,
        level="INFO",
        rotation="1 day",
        retention="7 days",
        filter=lambda record: "PERF" in record["message"],
        encoding="utf-8"
    )
    
    logger.info(f"📝 日誌系統已初始化，等級: {log_level}")


def get_logger(name: str):
    """
    獲取指定名稱的日誌記錄器
    
    Args:
        name: 日誌記錄器名稱
        
    Returns:
        loguru.Logger: 日誌記錄器實例
    """
    return logger.bind(name=name)


def log_performance(func_name: str, duration: float, **kwargs):
    """
    記錄性能日誌
    
    Args:
        func_name: 函數名稱
        duration: 執行時間(秒)
        **kwargs: 額外參數
    """
    extra_info = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"PERF | {func_name} | {duration:.4f}s | {extra_info}")


def log_system_status(component: str, status: str, **details):
    """
    記錄系統狀態日誌
    
    Args:
        component: 組件名稱
        status: 狀態 (ONLINE, OFFLINE, ERROR, WARNING)
        **details: 詳細信息
    """
    detail_str = " | ".join([f"{k}={v}" for k, v in details.items()])
    logger.info(f"STATUS | {component} | {status} | {detail_str}")


def log_hardware_event(device: str, event: str, value=None, unit: str = ""):
    """
    記錄硬體事件日誌
    
    Args:
        device: 設備名稱
        event: 事件類型
        value: 數值
        unit: 單位
    """
    value_str = f" | {value}{unit}" if value is not None else ""
    logger.info(f"HARDWARE | {device} | {event}{value_str}")


def log_ai_detection(model: str, detections: list, processing_time: float):
    """
    記錄AI檢測日誌
    
    Args:
        model: 模型名稱
        detections: 檢測結果列表
        processing_time: 處理時間
    """
    detection_count = len(detections)
    detection_types = [d.get('class', 'unknown') for d in detections]
    logger.info(f"AI | {model} | {detection_count} detections | {processing_time:.3f}s | {detection_types}")


def log_navigation_event(event_type: str, position=None, target=None, **params):
    """
    記錄導航事件日誌
    
    Args:
        event_type: 事件類型 (MOVE, STOP, TURN, AVOID, ARRIVE)
        position: 當前位置
        target: 目標位置
        **params: 其他參數
    """
    pos_str = f" | pos={position}" if position else ""
    target_str = f" | target={target}" if target else ""
    param_str = " | ".join([f"{k}={v}" for k, v in params.items()])
    logger.info(f"NAV | {event_type}{pos_str}{target_str} | {param_str}")


class ContextualLogger:
    """上下文日誌記錄器"""
    
    def __init__(self, component: str):
        self.component = component
        self.logger = logger.bind(component=component)
    
    def debug(self, message: str, **kwargs):
        self.logger.debug(f"[{self.component}] {message}", **kwargs)
    
    def info(self, message: str, **kwargs):
        self.logger.info(f"[{self.component}] {message}", **kwargs)
    
    def warning(self, message: str, **kwargs):
        self.logger.warning(f"[{self.component}] {message}", **kwargs)
    
    def error(self, message: str, **kwargs):
        self.logger.error(f"[{self.component}] {message}", **kwargs)
    
    def critical(self, message: str, **kwargs):
        self.logger.critical(f"[{self.component}] {message}", **kwargs) 