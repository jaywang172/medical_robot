#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
整合測試腳本
測試 car_run_turn 核心控制器與系統的整合
"""

import asyncio
import sys
import os

# 添加項目路徑
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def test_car_controller():
    """測試車輛控制器"""
    print("🚗 測試核心車輛控制器整合...")
    
    try:
        # 導入車輛控制器
        from robot_core.state_machine.car_run_turn import CarRunTurnController, create_car_controller
        
        print("✅ 成功導入 CarRunTurnController")
        
        # 創建控制器實例（模擬模式）
        controller = await create_car_controller(duration=0.2, simulation=True)
        print("✅ 成功創建車輛控制器實例")
        
        # 測試基本功能
        print("\n📋 執行基本功能測試...")
        
        # 1. 獲取初始狀態
        status = controller.get_status()
        print(f"📊 初始狀態: {status}")
        
        # 2. 測試前進
        print("⬆️  測試前進...")
        await controller.forward(0.1)
        
        # 3. 測試右轉
        print("➡️ 測試右轉...")
        await controller.turn_right(0.1)
        
        # 4. 測試後退
        print("⬇️  測試後退...")
        await controller.backward(0.1)
        
        # 5. 測試左轉
        print("⬅️ 測試左轉...")
        await controller.turn_left(0.1)
        
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
        
        # 10. 清理資源
        controller.cleanup()
        print("✅ 資源清理完成")
        
        print("\n🎉 車輛控制器測試全部通過！")
        return True
        
    except Exception as e:
        print(f"❌ 車輛控制器測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_integration():
    """測試API整合"""
    print("\n🌐 測試API整合...")
    
    try:
        # 檢查API模型定義
        from robot_core.api.server import CarControlRequest, CarStatusResponse
        print("✅ 成功導入API模型")
        
        # 測試模型實例化
        request = CarControlRequest(action="forward", duration=0.5)
        print(f"✅ 成功創建控制請求: {request}")
        
        # 測試響應模型
        response_data = {
            "is_moving": True,
            "current_direction": "forward",
            "last_command_time": 1234567890.0,
            "emergency_stop": False,
            "simulation_mode": True
        }
        
        response = CarStatusResponse(**response_data)
        print(f"✅ 成功創建狀態響應: {response}")
        
        print("🎉 API整合測試通過！")
        return True
        
    except Exception as e:
        print(f"❌ API整合測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_file_structure():
    """測試文件結構"""
    print("\n📁 檢查文件結構...")
    
    files_to_check = [
        "robot_core/state_machine/car_run_turn.py",
        "robot_core/api/server.py",
        "web_demo/src/components/ManualControl.tsx",
        "web_demo/src/services/RobotApiService.ts",
        "web_demo/src/types/RobotTypes.ts"
    ]
    
    all_exist = True
    for file_path in files_to_check:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 文件不存在")
            all_exist = False
    
    if all_exist:
        print("🎉 所有核心文件都存在！")
    else:
        print("⚠️  某些文件缺失")
    
    return all_exist


async def main():
    """主測試函數"""
    print("🔄 開始整合測試...")
    print("=" * 50)
    
    # 測試結果
    results = []
    
    # 1. 檢查文件結構
    results.append(("文件結構", test_file_structure()))
    
    # 2. 測試車輛控制器
    results.append(("車輛控制器", await test_car_controller()))
    
    # 3. 測試API整合
    results.append(("API整合", await test_api_integration()))
    
    # 輸出測試結果
    print("\n" + "=" * 50)
    print("📊 測試結果總結:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name:15} : {status}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"總計: {passed}/{total} 測試通過")
    
    if passed == total:
        print("🎉 所有測試都通過！整合成功！")
        print("\n📝 接下來您可以:")
        print("   1. 啟動後端服務: python robot_core/api/server.py")
        print("   2. 啟動前端服務: cd web_demo && npm start")
        print("   3. 在瀏覽器中訪問手動控制頁面")
        print("   4. 測試核心車輛控制功能")
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
