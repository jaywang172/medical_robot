#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡化整合測試 - 直接測試 car_run_turn 核心功能
不依賴外部模組，專注測試核心邏輯
"""

import asyncio
import sys
import os
import time

# 添加項目路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_car_controller_standalone():
    """獨立測試車輛控制器"""
    print("🚗 測試 car_run_turn 核心控制器...")
    
    try:
        # 直接導入車輛控制器模塊
        sys.path.append('robot_core/state_machine')
        import car_run_turn
        
        print("✅ 成功導入 car_run_turn 模塊")
        
        # 創建控制器實例（模擬模式）
        controller = car_run_turn.CarRunTurnController(duration=0.1, simulation=True)
        print("✅ 成功創建車輛控制器實例")
        
        # 測試基本功能
        print("\n📋 執行基本功能測試...")
        
        # 1. 獲取初始狀態
        status = controller.get_status()
        print(f"📊 初始狀態: {status}")
        
        # 2. 測試前進
        print("⬆️  測試前進...")
        await controller.forward(0.05)
        await asyncio.sleep(0.1)
        
        # 3. 測試右轉
        print("➡️ 測試右轉...")
        await controller.turn_right(0.05)
        await asyncio.sleep(0.1)
        
        # 4. 測試後退
        print("⬇️  測試後退...")
        await controller.backward(0.05)
        await asyncio.sleep(0.1)
        
        # 5. 測試左轉
        print("⬅️ 測試左轉...")
        await controller.turn_left(0.05)
        await asyncio.sleep(0.1)
        
        # 6. 測試停止
        print("⏹️  測試停止...")
        await controller.stop()
        
        # 7. 測試緊急停止
        print("🚨 測試緊急停止...")
        await controller.emergency_stop()
        
        # 8. 檢查緊急停止狀態
        status = controller.get_status()
        assert status['emergency_stop'], "緊急停止狀態應該為True"
        print("✅ 緊急停止狀態正確")
        
        # 9. 重置緊急停止
        print("🔄 重置緊急停止...")
        controller.reset_emergency_stop()
        
        status = controller.get_status()
        assert not status['emergency_stop'], "重置後緊急停止狀態應該為False"
        print("✅ 緊急停止重置成功")
        
        # 10. 測試向後兼容的函數
        print("🔙 測試向後兼容函數...")
        car_run_turn.forward()
        print("✅ forward() 函數可用")
        
        car_run_turn.backward()
        print("✅ backward() 函數可用")
        
        car_run_turn.turnLeft()
        print("✅ turnLeft() 函數可用")
        
        car_run_turn.turnRight()
        print("✅ turnRight() 函數可用")
        
        car_run_turn.stop()
        print("✅ stop() 函數可用")
        
        # 11. 清理資源
        controller.cleanup()
        print("✅ 資源清理完成")
        
        print("\n🎉 車輛控制器測試全部通過！")
        return True
        
    except Exception as e:
        print(f"❌ 車輛控制器測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_manual_mode():
    """測試原始手動模式"""
    print("\n🎮 測試原始手動控制模式...")
    
    try:
        # 導入模組
        sys.path.append('robot_core/state_machine')
        import car_run_turn
        
        # 測試創建控制器工廠函數
        controller = await car_run_turn.create_car_controller(simulation=True)
        print("✅ create_car_controller 工廠函數正常")
        
        # 測試狀態
        status = controller.get_status()
        expected_keys = ['is_moving', 'current_direction', 'last_command_time', 'emergency_stop', 'simulation_mode']
        
        for key in expected_keys:
            assert key in status, f"狀態中缺少關鍵字段: {key}"
        
        print("✅ 狀態數據結構正確")
        print(f"📊 狀態詳情: {status}")
        
        # 測試枚舉
        direction_enum = car_run_turn.MotorDirection
        print(f"✅ MotorDirection 枚舉可用: {list(direction_enum)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 手動模式測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_gpio_simulation():
    """測試GPIO模擬功能"""
    print("\n🔌 測試GPIO模擬...")
    
    try:
        sys.path.append('robot_core/state_machine')
        import car_run_turn
        
        # 檢查是否正確檢測到模擬模式
        print(f"📡 PI_AVAILABLE: {car_run_turn.PI_AVAILABLE}")
        
        # 在模擬模式下創建控制器
        controller = car_run_turn.CarRunTurnController(simulation=True)
        assert controller.simulation == True, "應該運行在模擬模式"
        print("✅ 模擬模式正確設置")
        
        # 測試引腳配置
        expected_pins = {
            'Motor_R1_Pin': 16,
            'Motor_R2_Pin': 18,
            'Motor_L1_Pin': 11,
            'Motor_L2_Pin': 13
        }
        
        for pin_name, expected_value in expected_pins.items():
            actual_value = getattr(car_run_turn, pin_name)
            assert actual_value == expected_value, f"{pin_name} 應該是 {expected_value}，但實際是 {actual_value}"
        
        print("✅ GPIO引腳配置正確")
        
        return True
        
    except Exception as e:
        print(f"❌ GPIO模擬測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_architecture_integration():
    """檢查架構整合"""
    print("\n🏗️ 檢查系統架構整合...")
    
    files_integration = {
        "核心控制器": "robot_core/state_machine/car_run_turn.py",
        "API服務器": "robot_core/api/server.py", 
        "前端組件": "web_demo/src/components/ManualControl.tsx",
        "API服務": "web_demo/src/services/RobotApiService.ts",
        "類型定義": "web_demo/src/types/RobotTypes.ts"
    }
    
    all_present = True
    integration_points = []
    
    for component, file_path in files_integration.items():
        if os.path.exists(file_path):
            print(f"✅ {component}: {file_path}")
            
            # 檢查關鍵整合點
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                if 'car_run_turn' in content or 'CarControl' in content:
                    integration_points.append(component)
                    
            except Exception:
                pass
                
        else:
            print(f"❌ {component}: {file_path} - 文件不存在")
            all_present = False
    
    print(f"\n🔗 整合點檢測: {integration_points}")
    
    if len(integration_points) >= 3:
        print("✅ 系統整合完整")
    else:
        print("⚠️  系統整合可能不完整")
    
    return all_present and len(integration_points) >= 3


async def main():
    """主測試函數"""
    print("🔄 開始簡化整合測試...")
    print("=" * 60)
    
    # 測試結果
    results = []
    
    # 1. 核心控制器功能測試
    results.append(("核心控制器", await test_car_controller_standalone()))
    
    # 2. 手動模式測試
    results.append(("手動模式", await test_manual_mode()))
    
    # 3. GPIO模擬測試
    results.append(("GPIO模擬", test_gpio_simulation()))
    
    # 4. 架構整合檢查
    results.append(("架構整合", check_architecture_integration()))
    
    # 輸出測試結果
    print("\n" + "=" * 60)
    print("📊 測試結果總結:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name:15} : {status}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"總計: {passed}/{total} 測試通過")
    
    if passed == total:
        print("\n🎉 整合測試全部通過！")
        print("\n📝 整合成功！您的系統現在具備以下能力:")
        print("   ✅ 核心GPIO車輛控制 (car_run_turn)")
        print("   ✅ 現代化Web界面整合")
        print("   ✅ RESTful API支援")
        print("   ✅ 模擬/硬件雙模式")
        print("   ✅ 緊急停止保護")
        print("   ✅ 向後兼容性")
        
        print("\n🚀 下一步操作:")
        print("   1. 安裝依賴: pip install fastapi uvicorn")
        print("   2. 測試核心功能: python robot_core/state_machine/car_run_turn.py --sim")
        print("   3. 在真實硬件上運行: python robot_core/state_machine/car_run_turn.py")
        print("   4. 啟動Web界面進行完整測試")
        
    else:
        print("⚠️  某些測試失敗，請檢查上述錯誤信息")
        return 1
    
    return 0


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚡ 測試被用戶中斷")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 測試過程中發生未預期錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
