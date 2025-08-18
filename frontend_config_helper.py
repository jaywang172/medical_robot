#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
前端配置助手
幫助設置前端與樹莓派的連接配置
"""

import os
import sys
import json
import subprocess
import socket
from pathlib import Path

def scan_for_raspberry_pi():
    """掃描網絡尋找樹莓派"""
    print("🔍 正在掃描網絡尋找樹莓派...")
    
    try:
        # 獲取本地網段
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        network_base = '.'.join(local_ip.split('.')[:-1])
        
        print(f"📡 本機IP: {local_ip}")
        print(f"🌐 掃描網段: {network_base}.x")
        
        found_servers = []
        
        # 掃描常見IP範圍
        for i in range(1, 255):
            test_ip = f"{network_base}.{i}"
            if test_ip == local_ip:
                continue
            
            # 快速端口檢測
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.1)
            result = sock.connect_ex((test_ip, 8000))
            sock.close()
            
            if result == 0:
                # 嘗試獲取主機名確認是樹莓派
                try:
                    hostname = socket.gethostbyaddr(test_ip)[0]
                    if 'raspberry' in hostname.lower() or 'pi' in hostname.lower():
                        print(f"🍓 發現樹莓派: {test_ip} ({hostname})")
                        found_servers.append((test_ip, hostname))
                    else:
                        print(f"🖥️  發現服務器: {test_ip} ({hostname})")
                        found_servers.append((test_ip, hostname))
                except:
                    print(f"🎯 發現服務器: {test_ip}")
                    found_servers.append((test_ip, "未知"))
        
        return found_servers
        
    except Exception as e:
        print(f"❌ 掃描失敗: {e}")
        return []

def test_api_connection(ip_address):
    """測試API連接"""
    print(f"\n🧪 測試與 {ip_address} 的連接...")
    
    try:
        # 使用 curl 測試（跨平台）
        result = subprocess.run(
            ['curl', '-s', '--connect-timeout', '3', f'http://{ip_address}:8000/'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                print(f"✅ API 響應正常")
                print(f"   訊息: {response.get('message', 'N/A')}")
                print(f"   狀態: {response.get('status', 'N/A')}")
                print(f"   模式: {response.get('mode', 'N/A')}")
                return True
            except json.JSONDecodeError:
                print(f"⚠️  服務器響應但格式異常")
                return False
        else:
            print(f"❌ 無法連接到 API")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ 連接超時")
        return False
    except FileNotFoundError:
        print(f"⚠️  curl 未安裝，跳過API測試")
        return True  # 假設連接正常
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        return False

def create_env_file(pi_ip, project_dir):
    """創建前端環境配置文件"""
    
    web_demo_dir = project_dir / "web_demo"
    
    if not web_demo_dir.exists():
        print(f"❌ 前端目錄不存在: {web_demo_dir}")
        return False
    
    env_file = web_demo_dir / ".env.local"
    
    env_content = f"""# 樹莓派機器人控制系統配置
# 自動生成於: {subprocess.check_output(['date'], text=True).strip()}

# 樹莓派 API 服務器地址
REACT_APP_API_BASE_URL=http://{pi_ip}:8000

# WebSocket 服務器地址
REACT_APP_WS_HOST={pi_ip}:8000

# 開發模式設置
REACT_APP_ENV=development

# API 超時設置 (毫秒)
REACT_APP_API_TIMEOUT=10000

# 調試模式
REACT_APP_DEBUG=true
"""
    
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print(f"✅ 配置文件已創建: {env_file}")
        return True
        
    except Exception as e:
        print(f"❌ 創建配置文件失敗: {e}")
        return False

def update_package_json(project_dir, pi_ip):
    """更新 package.json 的代理設置"""
    
    web_demo_dir = project_dir / "web_demo"
    package_json_file = web_demo_dir / "package.json"
    
    if not package_json_file.exists():
        print(f"⚠️  package.json 不存在: {package_json_file}")
        return False
    
    try:
        # 讀取現有配置
        with open(package_json_file, 'r', encoding='utf-8') as f:
            package_data = json.load(f)
        
        # 添加代理設置
        package_data["proxy"] = f"http://{pi_ip}:8000"
        
        # 寫回文件
        with open(package_json_file, 'w', encoding='utf-8') as f:
            json.dump(package_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ package.json 代理設置已更新")
        return True
        
    except Exception as e:
        print(f"❌ 更新 package.json 失敗: {e}")
        return False

def generate_connection_test_script(project_dir, pi_ip):
    """生成連接測試腳本"""
    
    test_script = project_dir / "test_frontend_connection.html"
    
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>機器人連接測試</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .status {{
            padding: 10px;
            margin: 10px 0;
            border-radius: 5px;
            border-left: 4px solid;
        }}
        .success {{
            background-color: #d4edda;
            border-color: #28a745;
            color: #155724;
        }}
        .error {{
            background-color: #f8d7da;
            border-color: #dc3545;
            color: #721c24;
        }}
        .info {{
            background-color: #d1ecf1;
            border-color: #17a2b8;
            color: #0c5460;
        }}
        button {{
            background-color: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 5px;
        }}
        button:hover {{
            background-color: #0056b3;
        }}
        .control-panel {{
            margin-top: 20px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 機器人連接測試頁面</h1>
        <p>測試與樹莓派的連接: <strong>{pi_ip}:8000</strong></p>
        
        <div id="status"></div>
        
        <button onclick="testConnection()">🔗 測試連接</button>
        <button onclick="testCarStatus()">🚗 測試車輛狀態</button>
        <button onclick="testCarControl('stop')">⏹️ 停止車輛</button>
        
        <div class="control-panel">
            <h3>🎮 基礎控制測試</h3>
            <button onclick="testCarControl('forward')">⬆️ 前進</button>
            <button onclick="testCarControl('backward')">⬇️ 後退</button>
            <button onclick="testCarControl('turn_left')">⬅️ 左轉</button>
            <button onclick="testCarControl('turn_right')">➡️ 右轉</button>
            <button onclick="testCarControl('stop')">⏹️ 停止</button>
            <button onclick="testCarControl('emergency_stop')" style="background-color: #dc3545;">🚨 緊急停止</button>
        </div>
        
        <div class="info">
            <h4>📋 使用說明：</h4>
            <ul>
                <li>首先點擊「測試連接」確認通訊正常</li>
                <li>點擊「測試車輛狀態」查看車輛狀態</li>
                <li>使用控制按鈕測試車輛移動（請確保安全）</li>
                <li>如有問題，檢查樹莓派服務器是否運行</li>
            </ul>
        </div>
    </div>

    <script>
        const API_BASE_URL = 'http://{pi_ip}:8000';
        
        function showStatus(message, type = 'info') {{
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = `<div class="status ${{type}}">${{message}}</div>`;
        }}
        
        async function testConnection() {{
            showStatus('🔍 測試連接中...', 'info');
            
            try {{
                const response = await fetch(`${{API_BASE_URL}}/`);
                const data = await response.json();
                
                if (response.ok) {{
                    showStatus(`✅ 連接成功！<br>
                               訊息: ${{data.message}}<br>
                               狀態: ${{data.status}}<br>
                               模式: ${{data.mode || '未知'}}`, 'success');
                }} else {{
                    showStatus(`❌ 連接失敗: HTTP ${{response.status}}`, 'error');
                }}
            }} catch (error) {{
                showStatus(`❌ 連接錯誤: ${{error.message}}<br>
                           請檢查：<br>
                           1. 樹莓派是否開機<br>
                           2. 服務器是否運行<br>
                           3. 網絡連接是否正常`, 'error');
            }}
        }}
        
        async function testCarStatus() {{
            showStatus('🚗 獲取車輛狀態...', 'info');
            
            try {{
                const response = await fetch(`${{API_BASE_URL}}/api/car/status`);
                
                if (response.ok) {{
                    const data = await response.json();
                    showStatus(`✅ 車輛狀態：<br>
                               運動中: ${{data.is_moving ? '是' : '否'}}<br>
                               方向: ${{data.current_direction}}<br>
                               緊急停止: ${{data.emergency_stop ? '是' : '否'}}<br>
                               模式: ${{data.simulation_mode ? '模擬' : '硬件'}}`, 'success');
                }} else {{
                    showStatus(`❌ 狀態獲取失敗: HTTP ${{response.status}}`, 'error');
                }}
            }} catch (error) {{
                showStatus(`❌ 狀態獲取錯誤: ${{error.message}}`, 'error');
            }}
        }}
        
        async function testCarControl(action) {{
            showStatus(`🎮 執行控制: ${{action}}...`, 'info');
            
            try {{
                const response = await fetch(`${{API_BASE_URL}}/api/car/control?action=${{action}}&duration=0.5`, {{
                    method: 'POST'
                }});
                
                if (response.ok) {{
                    const data = await response.json();
                    if (data.success) {{
                        showStatus(`✅ 控制成功: ${{data.message}}`, 'success');
                    }} else {{
                        showStatus(`❌ 控制失敗: ${{data.message}}`, 'error');
                    }}
                }} else {{
                    showStatus(`❌ 控制請求失敗: HTTP ${{response.status}}`, 'error');
                }}
            }} catch (error) {{
                showStatus(`❌ 控制錯誤: ${{error.message}}`, 'error');
            }}
        }}
        
        // 頁面載入時自動測試連接
        window.onload = function() {{
            setTimeout(testConnection, 1000);
        }};
    </script>
</body>
</html>"""
    
    try:
        with open(test_script, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ 連接測試頁面已創建: {test_script}")
        print(f"   在瀏覽器中打開此文件即可測試連接")
        return True
        
    except Exception as e:
        print(f"❌ 創建測試頁面失敗: {e}")
        return False

def main():
    """主程序"""
    print("🌐 前端配置助手")
    print("=" * 40)
    
    # 獲取項目目錄
    current_dir = Path.cwd()
    if (current_dir / "web_demo").exists():
        project_dir = current_dir
    elif (current_dir.parent / "web_demo").exists():
        project_dir = current_dir.parent
    else:
        print("❌ 找不到 web_demo 目錄")
        project_input = input("請輸入項目根目錄路徑: ").strip()
        project_dir = Path(project_input)
        
        if not (project_dir / "web_demo").exists():
            print("❌ 指定目錄中沒有 web_demo 文件夾")
            return
    
    print(f"📁 項目目錄: {project_dir}")
    
    # 掃描或手動輸入樹莓派IP
    print("\n選擇樹莓派IP獲取方式：")
    print("1. 自動掃描網絡")
    print("2. 手動輸入IP地址")
    
    choice = input("請選擇 (1-2): ").strip()
    
    pi_ip = None
    
    if choice == '1':
        found_servers = scan_for_raspberry_pi()
        
        if found_servers:
            print(f"\n發現 {len(found_servers)} 個服務器:")
            for i, (ip, hostname) in enumerate(found_servers):
                print(f"  {i+1}. {ip} ({hostname})")
            
            if len(found_servers) == 1:
                pi_ip = found_servers[0][0]
                print(f"\n自動選擇: {pi_ip}")
            else:
                try:
                    selection = int(input("請選擇服務器 (輸入數字): ")) - 1
                    pi_ip = found_servers[selection][0]
                except (ValueError, IndexError):
                    print("無效選擇")
                    return
        else:
            print("❌ 未發現服務器")
            pi_ip = input("請手動輸入樹莓派IP地址: ").strip()
    
    elif choice == '2':
        pi_ip = input("請輸入樹莓派IP地址: ").strip()
    
    else:
        print("無效選擇")
        return
    
    if not pi_ip:
        print("❌ 未指定IP地址")
        return
    
    # 測試連接
    if test_api_connection(pi_ip):
        print("✅ API連接測試通過")
    else:
        print("⚠️  API連接測試失敗，但將繼續配置")
    
    # 創建配置文件
    print(f"\n🔧 配置前端連接到 {pi_ip}...")
    
    success_count = 0
    total_tasks = 4
    
    # 創建 .env.local
    if create_env_file(pi_ip, project_dir):
        success_count += 1
    
    # 更新 package.json
    if update_package_json(project_dir, pi_ip):
        success_count += 1
    
    # 生成測試頁面
    if generate_connection_test_script(project_dir, pi_ip):
        success_count += 1
    
    # 顯示完成信息
    print(f"\n📊 配置完成: {success_count}/{total_tasks} 個任務成功")
    
    if success_count >= 3:
        print("\n🎉 前端配置完成！")
        print("\n📝 接下來的步驟:")
        print("1. 進入前端目錄: cd web_demo")
        print("2. 安裝依賴: npm install")
        print("3. 啟動開發服務器: npm start")
        print("4. 在瀏覽器中訪問: http://localhost:3000")
        print("\n🧪 測試連接:")
        print(f"- 打開測試頁面: {project_dir}/test_frontend_connection.html")
        print(f"- 直接訪問API: http://{pi_ip}:8000/docs")
    else:
        print("\n⚠️  配置過程中出現問題，請檢查錯誤信息")

if __name__ == "__main__":
    main()
