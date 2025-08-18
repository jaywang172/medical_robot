#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡化網絡連接測試 - 不依賴外部庫
"""

import socket
import sys
import time

def test_port_connection(host, port, timeout=3):
    """測試端口連接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def scan_network():
    """掃描網絡尋找可能的樹莓派"""
    print("🔍 掃描本地網絡...")
    
    try:
        # 獲取本地IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        network_base = '.'.join(local_ip.split('.')[:-1])
        
        print(f"📡 本機IP: {local_ip}")
        print(f"🌐 掃描網段: {network_base}.x:8000")
        
        found = []
        for i in range(1, 255):
            test_ip = f"{network_base}.{i}"
            if test_ip == local_ip:
                continue
            
            if test_port_connection(test_ip, 8000, 0.1):
                print(f"🎯 發現服務器: {test_ip}:8000")
                found.append(test_ip)
        
        return found
        
    except Exception as e:
        print(f"❌ 掃描失敗: {e}")
        return []

def main():
    print("🧪 樹莓派連接測試工具 (簡化版)")
    print("=" * 45)
    
    # 檢查參數
    if len(sys.argv) > 1:
        target_ip = sys.argv[1]
    else:
        # 自動掃描
        found_servers = scan_network()
        
        if not found_servers:
            print("❌ 未發現可用服務器")
            print("\n💡 使用方法:")
            print("  python simple_test_connection.py [樹莓派IP]")
            return
        
        if len(found_servers) == 1:
            target_ip = found_servers[0]
            print(f"\n🎯 自動選擇: {target_ip}")
        else:
            print(f"\n✅ 發現 {len(found_servers)} 個服務器:")
            for i, ip in enumerate(found_servers):
                print(f"  {i+1}. {ip}")
            
            try:
                choice = int(input("請選擇 (輸入數字): ")) - 1
                target_ip = found_servers[choice]
            except (ValueError, IndexError):
                target_ip = found_servers[0]
                print(f"使用第一個: {target_ip}")
    
    print(f"\n🎯 測試目標: {target_ip}:8000")
    print("=" * 45)
    
    # 基本連接測試
    print("🔗 測試端口連接...")
    if test_port_connection(target_ip, 8000):
        print("✅ 端口 8000 可達")
    else:
        print("❌ 端口 8000 不可達")
        print("請檢查:")
        print("1. 樹莓派服務器是否運行")
        print("2. 網絡連接是否正常")
        print("3. 防火牆設置")
        return
    
    # 性能測試
    print("\n⚡ 測試連接性能...")
    times = []
    for i in range(5):
        start = time.time()
        connected = test_port_connection(target_ip, 8000, 1)
        duration = (time.time() - start) * 1000
        
        if connected:
            times.append(duration)
            print(f"  測試 {i+1}: {duration:.1f}ms")
        else:
            print(f"  測試 {i+1}: 失敗")
    
    if times:
        avg = sum(times) / len(times)
        print(f"✅ 平均延遲: {avg:.1f}ms")
    
    # 生成配置
    print("\n📝 前端配置信息:")
    print("=" * 45)
    print("創建 web_demo/.env.local 文件，內容如下:")
    print()
    print(f"REACT_APP_API_BASE_URL=http://{target_ip}:8000")
    print(f"REACT_APP_WS_HOST={target_ip}:8000")
    print()
    print("然後重啟前端開發服務器:")
    print("  cd web_demo")
    print("  npm start")
    print()
    print("🌐 測試URL:")
    print(f"  API文檔: http://{target_ip}:8000/docs")
    print(f"  API狀態: http://{target_ip}:8000/api/status")
    print(f"  前端界面: http://localhost:3000")

if __name__ == "__main__":
    main()
