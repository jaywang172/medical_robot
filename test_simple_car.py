#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡單的車輛控制測試腳本
"""

import asyncio
import requests
import json
import time

API_BASE_URL = "http://localhost:8000"

def test_connection():
    """測試連接"""
    print("🔗 測試API連接...")
    try:
        response = requests.get(f"{API_BASE_URL}/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 連接成功！")
            print(f"📡 服務器: {data.get('message', '未知')}")
            print(f"🔧 狀態: {data.get('status', '未知')}")
            print(f"💻 模式: {data.get('mode', '未知')}")
            return True
        else:
            print(f"❌ 連接失敗: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 連接錯誤: {e}")
        return False

def get_car_status():
    """獲取車輛狀態"""
    print("\n📊 獲取車輛狀態...")
    try:
        response = requests.get(f"{API_BASE_URL}/api/car/status")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 車輛狀態：")
            print(f"  🚗 運動狀態: {'🟢 運動中' if data.get('is_moving') else '⚪ 靜止'}")
            print(f"  🧭 當前方向: {data.get('current_direction', '未知')}")
            print(f"  🚨 緊急停止: {'🔴 啟動' if data.get('emergency_stop') else '🟢 正常'}")
            print(f"  💻 運行模式: {'🖥️ 模擬' if data.get('simulation_mode') else '🔧 硬件'}")
            print(f"  ⏰ 最後命令: {time.ctime(data.get('last_command_time', 0))}")
            return True
        else:
            print(f"❌ 狀態獲取失敗: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 狀態獲取錯誤: {e}")
        return False

def car_control(action, duration=0.5):
    """控制車輛"""
    action_names = {
        'forward': '前進',
        'backward': '後退',
        'turn_left': '左轉',
        'turn_right': '右轉',
        'stop': '停止',
        'emergency_stop': '緊急停止'
    }
    
    action_name = action_names.get(action, action)
    print(f"\n🎮 執行: {action_name} ({duration}秒)")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/car/control",
            json={"action": action, "duration": duration}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print(f"✅ {action_name} 執行成功！")
                print(f"📝 {data.get('message', '')}")
                return True
            else:
                print(f"❌ {action_name} 執行失敗: {data.get('message', '')}")
                return False
        else:
            print(f"❌ 控制請求失敗: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 控制錯誤: {e}")
        return False

def test_car_sequence():
    """測試車輛控制序列"""
    print("\n🔧 開始車輛控制測試序列...")
    
    # 測試動作序列
    actions = [
        ('forward', 1.0),
        ('turn_right', 0.5),
        ('backward', 1.0),
        ('turn_left', 0.5),
        ('stop', 0)
    ]
    
    for action, duration in actions:
        if not car_control(action, duration):
            print("❌ 測試序列中斷")
            return False
        time.sleep(0.5)  # 動作間隔
        get_car_status()
    
    print("✅ 測試序列完成！")
    return True

def interactive_control():
    """互動式控制"""
    print("\n🎮 進入互動式控制模式")
    print("指令: w=前進, s=後退, a=左轉, d=右轉, x=停止, e=緊急停止, q=退出")
    
    while True:
        try:
            cmd = input("\n請輸入指令: ").lower().strip()
            
            if cmd == 'q':
                print("👋 退出互動式控制")
                break
            elif cmd == 'w':
                car_control('forward')
            elif cmd == 's':
                car_control('backward')
            elif cmd == 'a':
                car_control('turn_left')
            elif cmd == 'd':
                car_control('turn_right')
            elif cmd == 'x':
                car_control('stop')
            elif cmd == 'e':
                car_control('emergency_stop')
            elif cmd == 'status':
                get_car_status()
            else:
                print("❌ 無效指令")
                
        except KeyboardInterrupt:
            print("\n🚨 檢測到 Ctrl+C，執行緊急停止...")
            car_control('emergency_stop')
            break

def main():
    """主函數"""
    print("🚗 樹莓派車輛控制測試程序")
    print("=" * 50)
    
    # 測試連接
    if not test_connection():
        print("\n❌ 無法連接到服務器，請確保:")
        print("1. 服務器已啟動: python simple_car_server.py")
        print("2. 端口8000未被占用")
        return
    
    # 獲取初始狀態
    get_car_status()
    
    while True:
        print("\n🔧 測試選項:")
        print("1. 測試車輛控制序列")
        print("2. 互動式控制")
        print("3. 獲取車輛狀態")
        print("4. 重置緊急停止")
        print("5. 退出")
        
        try:
            choice = input("請選擇 (1-5): ").strip()
            
            if choice == '1':
                test_car_sequence()
            elif choice == '2':
                interactive_control()
            elif choice == '3':
                get_car_status()
            elif choice == '4':
                print("\n🔄 重置緊急停止...")
                response = requests.post(f"{API_BASE_URL}/api/car/emergency_reset")
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ {data.get('message', '重置成功')}")
                else:
                    print("❌ 重置失敗")
            elif choice == '5':
                print("👋 再見！")
                break
            else:
                print("❌ 無效選擇")
                
        except KeyboardInterrupt:
            print("\n👋 程序中斷，再見！")
            break

if __name__ == "__main__":
    main()
