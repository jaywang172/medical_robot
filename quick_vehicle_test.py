#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚗 快速車輛測試工具
提供安全、分步驟的車輛測試流程
"""

import os
import sys
import time
import subprocess
import json
from pathlib import Path

# 顏色設置
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def print_colored(text, color):
    print(f"{color}{text}{Colors.NC}")

def print_header(title):
    print("\n" + "="*60)
    print_colored(f"🚗 {title}", Colors.CYAN)
    print("="*60)

def print_step(step, description):
    print_colored(f"\n📋 步驟 {step}: {description}", Colors.BLUE)

def print_success(message):
    print_colored(f"✅ {message}", Colors.GREEN)

def print_warning(message):
    print_colored(f"⚠️  {message}", Colors.YELLOW)

def print_error(message):
    print_colored(f"❌ {message}", Colors.RED)

def get_user_input(prompt, options=None):
    """獲取用戶輸入"""
    if options:
        option_str = "/".join(options)
        prompt = f"{prompt} ({option_str}): "
    
    while True:
        response = input(prompt).strip().lower()
        
        if options:
            if response in [opt.lower() for opt in options]:
                return response
            else:
                print_error(f"請輸入 {option_str} 之一")
        else:
            return response

def check_environment():
    """檢查測試環境"""
    print_header("環境檢查")
    
    checks = [
        ("Python 3", lambda: sys.version_info >= (3, 6)),
        ("項目目錄", lambda: Path("robot_core").exists()),
        ("car_run_turn.py", lambda: Path("robot_core/state_machine/car_run_turn.py").exists()),
        ("start_pi_server.py", lambda: Path("start_pi_server.py").exists()),
    ]
    
    all_passed = True
    
    for name, check_func in checks:
        try:
            if check_func():
                print_success(f"{name} ✓")
            else:
                print_error(f"{name} ✗")
                all_passed = False
        except Exception as e:
            print_error(f"{name} ✗ - {e}")
            all_passed = False
    
    return all_passed

def safety_briefing():
    """安全說明"""
    print_header("安全說明")
    
    safety_points = [
        "確保車輛在安全的測試環境中",
        "準備好緊急斷電方式",
        "測試時有人在場監控",
        "從模擬模式開始測試",
        "逐步進行，不要跳過步驟"
    ]
    
    for i, point in enumerate(safety_points, 1):
        print_colored(f"{i}. {point}", Colors.YELLOW)
    
    print("\n" + "⚠️ "*20)
    response = get_user_input("您已閱讀並理解安全說明嗎？", ["y", "n"])
    
    if response == 'n':
        print_error("請先閱讀安全說明再進行測試")
        return False
    
    return True

def test_simulation_mode():
    """測試模擬模式"""
    print_header("模擬模式測試")
    
    print_step(1, "啟動模擬測試")
    print("這將測試軟件邏輯，不會控制真實硬件")
    
    try:
        # 檢查文件存在
        car_control_file = Path("robot_core/state_machine/car_run_turn.py")
        if not car_control_file.exists():
            print_error("找不到 car_run_turn.py 文件")
            return False
        
        print_colored("正在啟動模擬測試...", Colors.BLUE)
        print("您將看到模擬的電機控制輸出")
        print("請在程序中測試所有方向：f, b, l, r, s, e, x, q")
        print()
        
        response = get_user_input("按 Enter 繼續，或輸入 'skip' 跳過")
        
        if response != 'skip':
            # 運行模擬測試
            cmd = [sys.executable, str(car_control_file), "--sim"]
            result = subprocess.run(cmd, cwd=Path.cwd())
            
            if result.returncode == 0:
                print_success("模擬測試完成")
            else:
                print_error("模擬測試失敗")
                return False
        
        return True
        
    except Exception as e:
        print_error(f"模擬測試錯誤: {e}")
        return False

def test_api_server():
    """測試 API 服務器"""
    print_header("API 服務器測試")
    
    print_step(1, "準備啟動服務器")
    print("這將啟動 Web API 服務器以供前端連接")
    
    # 檢查端口
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 8000))
        sock.close()
        
        if result == 0:
            print_warning("端口 8000 已被占用")
            response = get_user_input("是否繼續？", ["y", "n"])
            if response == 'n':
                return False
    except Exception:
        pass
    
    print("服務器將在背景運行")
    print("您可以訪問 http://localhost:8000/docs 查看 API 文檔")
    print()
    
    response = get_user_input("按 Enter 啟動服務器，或輸入 'skip' 跳過")
    
    if response != 'skip':
        try:
            print_colored("正在啟動 API 服務器...", Colors.BLUE)
            
            # 啟動服務器（背景運行）
            server_file = Path("start_pi_server.py")
            if server_file.exists():
                # 不等待，讓用戶手動測試
                print("請在另一個終端運行：")
                print_colored(f"python3 {server_file}", Colors.CYAN)
                print("\n然後測試以下 URL：")
                print_colored("http://localhost:8000/", Colors.CYAN)
                print_colored("http://localhost:8000/api/car/status", Colors.CYAN)
                print_colored("http://localhost:8000/docs", Colors.CYAN)
                
                input("\n測試完成後按 Enter 繼續...")
                print_success("API 服務器測試完成")
            else:
                print_error("找不到 start_pi_server.py 文件")
                return False
                
        except Exception as e:
            print_error(f"API 服務器測試錯誤: {e}")
            return False
    
    return True

def test_hardware_connections():
    """測試硬件連接"""
    print_header("硬件連接測試")
    
    print_step(1, "硬件檢查清單")
    
    hardware_checks = [
        "樹莓派正常開機（紅燈亮，綠燈閃爍）",
        "電源供應充足（5V 3A 用於樹莓派）",
        "電機電源正確（12V 用於電機驅動）",
        "GPIO 接線正確（參考接線圖）",
        "L298N 驅動板指示燈正常",
        "所有接地線連接正確",
        "沒有短路或裸露線材",
    ]
    
    print("請確認以下硬件狀態：\n")
    
    all_ok = True
    for i, check in enumerate(hardware_checks, 1):
        print(f"{i}. {check}")
        response = get_user_input("   確認", ["y", "n"])
        if response == 'n':
            print_error(f"   硬件檢查失敗：{check}")
            all_ok = False
    
    if not all_ok:
        print_error("請先解決硬件問題再繼續")
        return False
    
    print_step(2, "GPIO 基礎測試")
    
    # 詢問是否要進行 GPIO 測試
    print("這將測試 GPIO 針腳輸出功能")
    response = get_user_input("是否進行 GPIO 測試？", ["y", "n"])
    
    if response == 'y':
        gpio_test_code = '''
import RPi.GPIO as GPIO
import time

# GPIO 針腳 (對應 car_run_turn.py)
pins = [16, 18, 11, 13]

try:
    GPIO.setmode(GPIO.BOARD)
    
    for pin in pins:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        print(f"設置針腳 {pin}")
    
    print("開始測試...")
    for pin in pins:
        print(f"測試針腳 {pin}")
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(0.5)
    
    print("GPIO 測試完成")
    
except Exception as e:
    print(f"GPIO 測試失敗: {e}")
    
finally:
    GPIO.cleanup()
'''
        
        # 創建臨時測試文件
        test_file = Path("temp_gpio_test.py")
        
        try:
            with open(test_file, 'w') as f:
                f.write(gpio_test_code)
            
            print_colored("運行 GPIO 測試...", Colors.BLUE)
            result = subprocess.run([sys.executable, str(test_file)])
            
            if result.returncode == 0:
                print_success("GPIO 測試完成")
            else:
                print_error("GPIO 測試失敗")
                return False
                
        except Exception as e:
            print_error(f"GPIO 測試錯誤: {e}")
            return False
        finally:
            # 清理臨時文件
            if test_file.exists():
                test_file.unlink()
    
    return True

def test_motor_control():
    """測試電機控制"""
    print_header("電機控制測試")
    
    print_step(1, "安全準備")
    
    safety_items = [
        "電機已從輪子拆下，或車輛已架空",
        "周圍沒有障礙物",
        "準備好緊急斷電開關",
        "有人在現場監控"
    ]
    
    print("⚠️  在進行電機測試前，請確認：\n")
    
    for i, item in enumerate(safety_items, 1):
        print(f"{i}. {item}")
        response = get_user_input("   確認", ["y", "n"])
        if response == 'n':
            print_error("請先完成安全準備")
            return False
    
    print_step(2, "電機功能測試")
    
    print("現在將進行實際電機控制測試")
    print("⚠️  請密切監控電機運行，如有異常立即斷電")
    
    response = get_user_input("確認開始電機測試？", ["y", "n"])
    
    if response == 'y':
        try:
            car_control_file = Path("robot_core/state_machine/car_run_turn.py")
            
            print_colored("啟動電機控制程序...", Colors.BLUE)
            print("測試順序：")
            print("1. 輸入 'f' 測試前進（觀察電機轉動）")
            print("2. 立即輸入 's' 測試停止")
            print("3. 輸入 'b' 測試後退")
            print("4. 輸入 'l' 和 'r' 測試轉向")
            print("5. 輸入 'e' 測試緊急停止")
            print("6. 輸入 'q' 退出")
            print()
            
            # 運行硬件測試
            result = subprocess.run([sys.executable, str(car_control_file)])
            
            if result.returncode == 0:
                print_success("電機控制測試完成")
            else:
                print_warning("電機控制程序異常退出")
                
        except Exception as e:
            print_error(f"電機控制測試錯誤: {e}")
            return False
    
    return True

def test_vehicle_movement():
    """測試車輛運動"""
    print_header("車輛運動測試")
    
    print_step(1, "最終安全確認")
    
    final_safety = [
        "車輛在平坦安全的地面上",
        "測試區域沒有障礙物",
        "有足夠的活動空間",
        "緊急停止方式已準備",
        "監控人員就位"
    ]
    
    print("🚨 最終安全檢查：\n")
    
    for i, item in enumerate(final_safety, 1):
        print(f"{i}. {item}")
        response = get_user_input("   確認", ["y", "n"])
        if response == 'n':
            print_error("請先完成安全準備")
            return False
    
    print_step(2, "車輛運動測試")
    
    print("建議的測試順序：")
    print("1. 短時間前進測試 (0.5秒)")
    print("2. 短時間後退測試 (0.5秒)")  
    print("3. 左轉和右轉測試")
    print("4. 緊急停止測試")
    print("5. 如果一切正常，可以進行更長時間的測試")
    print()
    
    response = get_user_input("準備開始車輛運動測試？", ["y", "n"])
    
    if response == 'y':
        print_colored("請使用以下方式控制車輛：", Colors.BLUE)
        print("方式1: 直接運行車輛控制程序")
        print("方式2: 使用 Web 界面控制")
        print("方式3: 使用 API 命令控制")
        print()
        
        control_method = get_user_input("選擇控制方式", ["1", "2", "3"])
        
        if control_method == "1":
            print_colored("啟動車輛控制程序...", Colors.BLUE)
            car_control_file = Path("robot_core/state_machine/car_run_turn.py")
            subprocess.run([sys.executable, str(car_control_file)])
            
        elif control_method == "2":
            print_colored("請使用 Web 界面控制：", Colors.BLUE)
            print("1. 啟動 API 服務器：python3 start_pi_server.py")
            print("2. 啟動前端：cd web_demo && npm start")
            print("3. 訪問：http://localhost:3000")
            
        elif control_method == "3":
            print_colored("API 控制命令範例：", Colors.BLUE)
            print("前進：curl -X POST 'http://localhost:8000/api/car/control?action=forward&duration=0.5'")
            print("停止：curl -X POST 'http://localhost:8000/api/car/control?action=stop'")
            print("緊急停止：curl -X POST 'http://localhost:8000/api/car/control?action=emergency_stop'")
        
        input("\n測試完成後按 Enter 繼續...")
        print_success("車輛運動測試完成")
    
    return True

def generate_test_report():
    """生成測試報告"""
    print_header("測試完成")
    
    print_colored("🎉 恭喜！車輛測試流程已完成", Colors.GREEN)
    
    print("\n📋 建議的後續步驟：")
    next_steps = [
        "微調車輛參數（速度、轉向角度等）",
        "添加感測器（超聲波、攝像頭等）",
        "開發自動駕駛功能",
        "整合前端控制界面",
        "添加更多安全機制",
        "分享您的項目成果"
    ]
    
    for i, step in enumerate(next_steps, 1):
        print(f"{i}. {step}")
    
    print(f"\n📝 完整的測試指南請參考：VEHICLE_TESTING_GUIDE.md")
    print(f"🛠️ 硬件接線指南：python3 hardware_wiring_guide.py")
    print(f"🌐 網絡配置助手：python3 frontend_config_helper.py")
    
    print_colored("\n🤖 祝您的機器人項目成功！", Colors.PURPLE)

def main():
    """主程序"""
    print_colored("🚗 機器人車輛快速測試工具", Colors.CYAN)
    print_colored("="*50, Colors.CYAN)
    
    # 測試步驟
    test_steps = [
        ("環境檢查", check_environment),
        ("安全說明", safety_briefing),
        ("模擬模式測試", test_simulation_mode),
        ("API 服務器測試", test_api_server),
        ("硬件連接測試", test_hardware_connections),
        ("電機控制測試", test_motor_control),
        ("車輛運動測試", test_vehicle_movement),
    ]
    
    completed_steps = 0
    
    for step_name, step_func in test_steps:
        print(f"\n🔄 準備執行：{step_name}")
        response = get_user_input("是否執行此步驟？", ["y", "n", "skip"])
        
        if response == "n":
            print_warning("測試中止")
            break
        elif response == "skip":
            print_warning(f"跳過：{step_name}")
            continue
        
        try:
            if step_func():
                print_success(f"✅ {step_name} 完成")
                completed_steps += 1
            else:
                print_error(f"❌ {step_name} 失敗")
                response = get_user_input("是否繼續其他測試？", ["y", "n"])
                if response == "n":
                    break
        except Exception as e:
            print_error(f"❌ {step_name} 發生錯誤: {e}")
            response = get_user_input("是否繼續其他測試？", ["y", "n"])
            if response == "n":
                break
    
    # 生成報告
    print(f"\n📊 測試總結：完成 {completed_steps}/{len(test_steps)} 個步驟")
    
    if completed_steps >= len(test_steps) - 1:
        generate_test_report()
    else:
        print_warning("部分測試未完成，請檢查問題後重新測試")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_colored("\n\n👋 測試中斷，再見！", Colors.YELLOW)
    except Exception as e:
        print_error(f"\n💥 程序錯誤: {e}")
        sys.exit(1)
