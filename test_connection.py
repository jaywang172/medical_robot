#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
網絡連接測試腳本
用於測試樹莓派與前端的連接狀況
"""

import requests
import json
import time
import sys
from urllib.parse import urljoin

def test_api_connection(base_url):
    """測試API連接"""
    print(f"🔗 測試API連接: {base_url}")
    
    try:
        # 測試根端點
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 根端點響應: {data}")
            return True
        else:
            print(f"❌ 根端點錯誤: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ 無法連接到 {base_url}")
        return False
    except requests.exceptions.Timeout:
        print(f"❌ 連接超時: {base_url}")
        return False
    except Exception as e:
        print(f"❌ 連接錯誤: {e}")
        return False

def test_car_api(base_url):
    """測試車輛控制API"""
    print(f"\n🚗 測試車輛控制API...")
    
    try:
        # 測試狀態端點
        response = requests.get(f"{base_url}/api/car/status", timeout=5)
        if response.status_code == 200:
            status = response.json()
            print(f"✅ 車輛狀態: {status}")
        else:
            print(f"❌ 狀態端點錯誤: {response.status_code}")
            return False
        
        # 測試控制端點 (停止命令，安全)
        response = requests.post(
            f"{base_url}/api/car/control",
            params={"action": "stop"},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 控制測試: {result}")
            return True
        else:
            print(f"❌ 控制端點錯誤: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ 車輛API測試失敗: {e}")
        return False

def test_cors(base_url):
    """測試CORS設置"""
    print(f"\n🌐 測試CORS設置...")
    
    try:
        headers = {
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'GET'
        }
        response = requests.options(f"{base_url}/api/status", headers=headers, timeout=5)
        
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
        }
        
        print(f"✅ CORS 響應頭: {cors_headers}")
        return True
        
    except Exception as e:
        print(f"❌ CORS測試失敗: {e}")
        return False

def test_performance(base_url):
    """測試API性能"""
    print(f"\n⚡ 測試API性能...")
    
    try:
        times = []
        for i in range(5):
            start_time = time.time()
            response = requests.get(f"{base_url}/api/status", timeout=5)
            end_time = time.time()
            
            if response.status_code == 200:
                duration = (end_time - start_time) * 1000
                times.append(duration)
                print(f"  請求 {i+1}: {duration:.2f}ms")
            else:
                print(f"  請求 {i+1}: 失敗")
        
        if times:
            avg_time = sum(times) / len(times)
            print(f"✅ 平均響應時間: {avg_time:.2f}ms")
            return avg_time < 1000  # 小於1秒算正常
        else:
            return False
            
    except Exception as e:
        print(f"❌ 性能測試失敗: {e}")
        return False

def scan_network_for_pi():
    """掃描網絡尋找樹莓派"""
    print(f"\n🔍 掃描網絡尋找樹莓派...")
    
    import socket
    import subprocess
    
    try:
        # 獲取本地網段
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        network_base = '.'.join(local_ip.split('.')[:-1])
        
        print(f"📡 本地IP: {local_ip}")
        print(f"🌐 掃描網段: {network_base}.x")
        
        found_servers = []
        
        # 掃描常見IP範圍
        for i in range(1, 255):
            test_ip = f"{network_base}.{i}"
            if test_ip == local_ip:
                continue
                
            try:
                # 快速端口檢測
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.1)
                result = sock.connect_ex((test_ip, 8000))
                sock.close()
                
                if result == 0:
                    print(f"🎯 發現服務器: {test_ip}:8000")
                    found_servers.append(test_ip)
                    
            except Exception:
                pass
        
        return found_servers
        
    except Exception as e:
        print(f"❌ 網絡掃描失敗: {e}")
        return []

def main():
    """主測試程序"""
    print("🧪 樹莓派連接測試工具")
    print("=" * 40)
    
    # 檢查命令行參數
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
        if not base_url.startswith('http'):
            base_url = f"http://{base_url}:8000"
    else:
        print("🔍 未指定服務器地址，開始自動掃描...")
        found_servers = scan_network_for_pi()
        
        if found_servers:
            print(f"\n✅ 發現 {len(found_servers)} 個可能的服務器:")
            for i, server in enumerate(found_servers):
                print(f"  {i+1}. http://{server}:8000")
            
            if len(found_servers) == 1:
                base_url = f"http://{found_servers[0]}:8000"
                print(f"\n🎯 自動選擇: {base_url}")
            else:
                try:
                    choice = int(input("\n請選擇服務器 (輸入數字): ")) - 1
                    base_url = f"http://{found_servers[choice]}:8000"
                except (ValueError, IndexError):
                    print("❌ 無效選擇")
                    return
        else:
            print("❌ 未發現可用的服務器")
            print("\n💡 使用方法:")
            print("  python test_connection.py [樹莓派IP地址]")
            print("  例如: python test_connection.py 192.168.1.100")
            return
    
    print(f"\n🎯 測試目標: {base_url}")
    print("=" * 40)
    
    # 執行測試
    tests = [
        ("基礎連接", lambda: test_api_connection(base_url)),
        ("車輛控制API", lambda: test_car_api(base_url)),
        ("CORS設置", lambda: test_cors(base_url)),
        ("API性能", lambda: test_performance(base_url))
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 測試異常: {e}")
            results.append((test_name, False))
    
    # 總結結果
    print("\n" + "=" * 40)
    print("📊 測試結果總結:")
    print("=" * 40)
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name:15} : {status}")
        if result:
            passed += 1
    
    print("=" * 40)
    print(f"總計: {passed}/{len(results)} 項測試通過")
    
    if passed == len(results):
        print("\n🎉 所有測試通過！")
        print("您的樹莓派已準備好與前端連接。")
        print(f"\n📝 前端配置:")
        print(f"在 web_demo/.env.local 中設置:")
        print(f"REACT_APP_API_BASE_URL={base_url}")
        print(f"REACT_APP_WS_HOST={base_url.replace('http://', '').replace('https://', '')}")
    else:
        print("\n⚠️ 某些測試失敗，請檢查:")
        print("1. 樹莓派服務器是否正在運行")
        print("2. 網絡連接是否正常")
        print("3. 防火牆設置是否正確")

if __name__ == "__main__":
    main()
