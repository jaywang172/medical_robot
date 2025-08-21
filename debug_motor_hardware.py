#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
硬件調試腳本 - 系統性排查電機不動的問題
"""

import time
import sys

def test_lgpio_basic():
    """測試 lgpio 基本功能"""
    print("🔧 測試 lgpio 基本功能...")
    
    try:
        import lgpio
        
        # 打開GPIO芯片
        h = lgpio.gpiochip_open(0)
        print(f"✅ GPIO芯片打開成功，句柄: {h}")
        
        # 測試引腳配置
        test_pin = 16  # Motor_R1_Pin
        lgpio.gpio_claim_output(h, test_pin, 0)
        print(f"✅ 引腳 {test_pin} 配置為輸出成功")
        
        # 測試引腳輸出
        print(f"🔄 測試引腳 {test_pin} 輸出...")
        for i in range(5):
            lgpio.gpio_write(h, test_pin, 1)
            print(f"   引腳 {test_pin} = HIGH")
            time.sleep(0.5)
            lgpio.gpio_write(h, test_pin, 0)
            print(f"   引腳 {test_pin} = LOW")
            time.sleep(0.5)
        
        # 清理
        lgpio.gpio_free(h, test_pin)
        lgpio.gpiochip_close(h)
        print("✅ lgpio 基本功能測試完成")
        return True
        
    except Exception as e:
        print(f"❌ lgpio 測試失敗: {e}")
        return False

def test_all_motor_pins():
    """測試所有電機引腳"""
    print("\n🔧 測試所有電機引腳...")
    
    try:
        import lgpio
        
        # 電機引腳
        pins = {
            16: "Motor_R1 (右電機正轉)",
            18: "Motor_R2 (右電機反轉)",
            11: "Motor_L1 (左電機正轉)",
            13: "Motor_L2 (左電機反轉)"
        }
        
        h = lgpio.gpiochip_open(0)
        
        # 配置所有引腳
        for pin in pins.keys():
            lgpio.gpio_claim_output(h, pin, 0)
            print(f"✅ 配置引腳 {pin} ({pins[pin]})")
        
        # 逐個測試引腳
        for pin, name in pins.items():
            print(f"\n🔄 測試 {name} (GPIO{pin})...")
            print("   請用萬用表測量該引腳電壓")
            
            # 輸出HIGH
            lgpio.gpio_write(h, pin, 1)
            print(f"   引腳 {pin} 設為 HIGH (應該測到 3.3V)")
            input("   按Enter確認測量完成...")
            
            # 輸出LOW
            lgpio.gpio_write(h, pin, 0)
            print(f"   引腳 {pin} 設為 LOW (應該測到 0V)")
            input("   按Enter繼續下一個引腳...")
        
        # 清理
        for pin in pins.keys():
            lgpio.gpio_free(h, pin)
        lgpio.gpiochip_close(h)
        
        print("✅ 所有引腳測試完成")
        return True
        
    except Exception as e:
        print(f"❌ 引腳測試失敗: {e}")
        return False

def test_motor_combinations():
    """測試電機組合動作"""
    print("\n🔧 測試電機組合動作...")
    
    try:
        import lgpio
        
        pins = [16, 18, 11, 13]  # R1, R2, L1, L2
        h = lgpio.gpiochip_open(0)
        
        for pin in pins:
            lgpio.gpio_claim_output(h, pin, 0)
        
        def set_motors(r1, r2, l1, l2):
            lgpio.gpio_write(h, 16, r1)
            lgpio.gpio_write(h, 18, r2)
            lgpio.gpio_write(h, 11, l1)
            lgpio.gpio_write(h, 13, l2)
            print(f"   R1={r1}, R2={r2}, L1={l1}, L2={l2}")
        
        def stop_all():
            set_motors(0, 0, 0, 0)
        
        print("🚗 測試電機動作 (每個動作持續3秒)...")
        
        # 前進
        print("\n1. 前進 (R1=1, L1=1)")
        set_motors(1, 0, 1, 0)
        time.sleep(3)
        stop_all()
        input("   電機有動作嗎？按Enter繼續...")
        
        # 後退
        print("\n2. 後退 (R2=1, L2=1)")
        set_motors(0, 1, 0, 1)
        time.sleep(3)
        stop_all()
        input("   電機有動作嗎？按Enter繼續...")
        
        # 右轉
        print("\n3. 右轉 (R1=1, L1=0)")
        set_motors(1, 0, 0, 0)
        time.sleep(3)
        stop_all()
        input("   電機有動作嗎？按Enter繼續...")
        
        # 左轉
        print("\n4. 左轉 (R1=0, L1=1)")
        set_motors(0, 0, 1, 0)
        time.sleep(3)
        stop_all()
        input("   電機有動作嗎？按Enter繼續...")
        
        # 清理
        for pin in pins:
            lgpio.gpio_free(h, pin)
        lgpio.gpiochip_close(h)
        
        print("✅ 電機組合測試完成")
        return True
        
    except Exception as e:
        print(f"❌ 電機組合測試失敗: {e}")
        return False

def check_hardware_connections():
    """檢查硬件連接指南"""
    print("\n📋 硬件連接檢查清單:")
    print("=" * 50)
    
    print("\n🔌 樹莓派到L298N連接:")
    print("   GPIO16 (物理針腳36) → L298N IN1")
    print("   GPIO18 (物理針腳12) → L298N IN2") 
    print("   GPIO11 (物理針腳23) → L298N IN3")
    print("   GPIO13 (物理針腳33) → L298N IN4")
    print("   5V (物理針腳2或4)  → L298N VCC")
    print("   GND (任意GND針腳)   → L298N GND")
    
    print("\n🔋 L298N到電機和電源:")
    print("   L298N OUT1, OUT2 → 右電機")
    print("   L298N OUT3, OUT4 → 左電機") 
    print("   12V電池正極      → L298N VIN")
    print("   12V電池負極      → L298N GND")
    
    print("\n⚠️  常見問題:")
    print("   1. L298N的ENA, ENB跳線帽是否插上？")
    print("   2. 12V電源是否有電？(用萬用表測量)")
    print("   3. 所有GND是否連接在一起？")
    print("   4. L298N指示燈是否亮？")
    print("   5. 電機連接是否牢固？")
    
    print("\n🧪 排查步驟:")
    print("   1. 先用萬用表測量GPIO引腳電壓")
    print("   2. 測量L298N的IN1-IN4引腳電壓")
    print("   3. 測量L298N的OUT1-OUT4引腳電壓")
    print("   4. 測量L298N的VIN引腳電壓(應該是12V)")
    print("   5. 直接用12V電源測試電機是否能轉")

def main():
    """主測試函數"""
    print("🔧 電機硬件調試工具")
    print("=" * 50)
    
    while True:
        print("\n請選擇測試項目:")
        print("1. 測試lgpio基本功能")
        print("2. 測試所有電機引腳(需要萬用表)")
        print("3. 測試電機組合動作")
        print("4. 顯示硬件連接檢查清單")
        print("5. 退出")
        
        choice = input("\n輸入選項 (1-5): ").strip()
        
        if choice == '1':
            test_lgpio_basic()
        elif choice == '2':
            test_all_motor_pins()
        elif choice == '3':
            test_motor_combinations()
        elif choice == '4':
            check_hardware_connections()
        elif choice == '5':
            print("退出調試工具")
            break
        else:
            print("無效選項，請重新選擇")

if __name__ == "__main__":
    main()
