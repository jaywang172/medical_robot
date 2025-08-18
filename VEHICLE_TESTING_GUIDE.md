# 🚗 機器人車輛測試完整指南

> **安全第一！** 請務必按照步驟進行，確保測試過程安全可控

## 📋 測試前準備檢查清單

### ⚡ 電源系統檢查
- [ ] 樹莓派電源連接正常 (5V 3A)
- [ ] 電機電源電壓正確 (12V ±1V)
- [ ] 所有電源連接牢固
- [ ] 電池電量充足 (>50%)
- [ ] 保險絲已安裝且完好

### 🔌 硬件連接檢查
- [ ] GPIO 針腳連接正確
- [ ] 電機驅動板 (L298N) 指示燈正常
- [ ] 所有接地線 (GND) 連接正確
- [ ] 電機線材連接牢固
- [ ] 沒有短路或裸露線材

### 💻 軟件環境檢查
- [ ] 樹莓派正常開機
- [ ] SSH 連接正常
- [ ] Python 環境可用
- [ ] 項目代碼已部署
- [ ] 服務器可以啟動

---

## 🧪 第一階段：基礎軟件測試

### 1. 系統健康檢查

```bash
# SSH 連接到樹莓派
ssh pi@樹莓派IP

# 進入項目目錄
cd /home/pi/robot_project

# 執行系統檢查
python3 system_check.py
```

**預期結果：**
```
🍓 樹莓派系統檢查
========================================
🌡️  CPU溫度: temp=45.2'C
💾 記憶體使用: 35.2%
💽 磁碟使用: /dev/root  15G  4.2G  9.8G  30% /
✅ GPIO 可用
✅ 網絡連接正常
```

### 2. 核心控制器測試 (模擬模式)

```bash
# 運行模擬測試 - 這是安全的，不會控制真實電機
python3 robot_core/state_machine/car_run_turn.py --sim
```

**測試步驟：**
1. 輸入 `f` (前進) - 檢查模擬輸出
2. 輸入 `b` (後退) - 檢查模擬輸出  
3. 輸入 `l` (左轉) - 檢查模擬輸出
4. 輸入 `r` (右轉) - 檢查模擬輸出
5. 輸入 `s` (停止) - 檢查模擬輸出
6. 輸入 `e` (緊急停止) - 檢查安全機制
7. 輸入 `x` (重置) - 檢查重置功能
8. 輸入 `q` (退出)

**預期輸出：**
```
運行在模擬模式 - 樹莓派GPIO不可用
CarRunTurnController 初始化完成 - 模擬模式
車輛控制器測試程序

請輸入指令: f
前進 0.5秒
模擬電機控制: R1=True, R2=False, L1=True, L2=False
模擬電機控制: R1=False, R2=False, L1=False, L2=False
電機已停止
```

### 3. API 服務器測試

```bash
# 啟動服務器
python3 start_pi_server.py
```

在另一個終端測試 API：
```bash
# 基礎連接測試
curl http://localhost:8000/

# 車輛狀態測試
curl http://localhost:8000/api/car/status

# 安全控制測試 (停止命令)
curl -X POST "http://localhost:8000/api/car/control?action=stop"
```

---

## ⚙️ 第二階段：硬件連接測試

### ⚠️ 安全警告
> **在進行硬件測試前，請確保：**
> - 電機已從輪子上拆下，或車輛已架空
> - 周圍沒有障礙物
> - 有緊急斷電方式
> - 有人在現場監控

### 1. GPIO 基礎測試

```bash
# 創建 GPIO 測試腳本
cat > gpio_test.py << 'EOF'
#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

# 設置 GPIO 模式
GPIO.setmode(GPIO.BOARD)

# 測試針腳 (對應 car_run_turn.py 的設置)
test_pins = [16, 18, 11, 13]  # Motor_R1, R2, L1, L2

try:
    # 設置為輸出
    for pin in test_pins:
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        print(f"設置針腳 {pin} 為輸出")
    
    # 逐一測試每個針腳
    for pin in test_pins:
        print(f"測試針腳 {pin}...")
        GPIO.output(pin, GPIO.HIGH)
        time.sleep(0.5)
        GPIO.output(pin, GPIO.LOW)
        time.sleep(0.5)
        print(f"針腳 {pin} 測試完成")
    
    print("✅ 所有 GPIO 針腳測試完成")
    
except Exception as e:
    print(f"❌ GPIO 測試失敗: {e}")
    
finally:
    GPIO.cleanup()
    print("GPIO 清理完成")
EOF

# 執行測試
python3 gpio_test.py
```

### 2. 電機驅動測試 (無負載)

**⚠️ 確保電機沒有連接到輪子或負載**

```bash
# 運行真實硬件測試
python3 robot_core/state_machine/car_run_turn.py
```

**測試步驟：**
1. 輸入 `f` - **觀察電機是否正轉**
2. 立即輸入 `s` - **確保能停止**
3. 輸入 `b` - **觀察電機是否反轉**
4. 立即輸入 `s` - **確保能停止**
5. 測試 `l`, `r` - **檢查左右電機**
6. 測試 `e` - **驗證緊急停止**

**檢查要點：**
- [ ] 電機轉動方向正確
- [ ] 停止命令響應及時
- [ ] 緊急停止功能正常
- [ ] 無異常聲音或發熱
- [ ] L298N 指示燈正常

### 3. 電流和電壓測試

使用萬用電表檢查：
```
電池電壓: 12V ±1V
5V 供電: 4.9-5.1V
3.3V 供電: 3.2-3.4V
電機無負載電流: <500mA
```

---

## 🚗 第三階段：車輛運動測試

### ⚠️ 安全準備
- 在空曠平坦的地面進行
- 準備緊急斷電開關
- 設置安全邊界
- 有人在場監控

### 1. 靜態測試

將車輛放在地面，但用手扶住：

```bash
# 啟動 API 服務器
python3 start_pi_server.py &

# 使用 curl 進行精確控制
curl -X POST "http://localhost:8000/api/car/control?action=forward&duration=0.1"
```

**檢查項目：**
- [ ] 前進方向正確
- [ ] 左右轉向正確
- [ ] 後退方向正確
- [ ] 動力輸出適中

### 2. 低速動態測試

```bash
# 短時間、低功率測試
curl -X POST "http://localhost:8000/api/car/control?action=forward&duration=0.5"

# 等待停止後再進行下一個測試
sleep 2

curl -X POST "http://localhost:8000/api/car/control?action=backward&duration=0.5"
```

### 3. 轉向測試

```bash
# 左轉測試
curl -X POST "http://localhost:8000/api/car/control?action=turn_left&duration=0.3"

sleep 2

# 右轉測試  
curl -X POST "http://localhost:8000/api/car/control?action=turn_right&duration=0.3"
```

---

## 🌐 第四階段：前端控制測試

### 1. 前端配置

```bash
# 在您的電腦上運行
python3 frontend_config_helper.py

# 啟動前端
cd web_demo
npm start
```

### 2. Web 界面測試

1. **打開瀏覽器** → `http://localhost:3000`
2. **進入手動控制頁面**
3. **啟用核心車輛控制開關**
4. **測試控制按鈕：**
   - 點擊「前進」按鈕
   - 點擊「停止」按鈕
   - 測試其他方向
   - 測試緊急停止

### 3. 移動設備測試

1. **手機連接同一WiFi**
2. **訪問** → `http://樹莓派IP:3000`
3. **測試觸控操作**
4. **檢查響應延遲**

---

## 🧪 第五階段：進階功能測試

### 1. 連續運動測試

```python
# 創建連續運動測試腳本
cat > continuous_test.py << 'EOF'
#!/usr/bin/env python3
import requests
import time

API_BASE = "http://localhost:8000"

def test_sequence():
    print("🚗 開始連續運動測試...")
    
    # 測試序列
    actions = [
        ("forward", 1.0),
        ("turn_right", 0.5), 
        ("forward", 1.0),
        ("turn_right", 0.5),
        ("forward", 1.0),
        ("turn_right", 0.5),
        ("forward", 1.0),
        ("turn_right", 0.5),
        ("stop", 0)
    ]
    
    for action, duration in actions:
        print(f"執行: {action} ({duration}s)")
        
        response = requests.post(
            f"{API_BASE}/api/car/control",
            params={"action": action, "duration": duration}
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result.get('message', '成功')}")
        else:
            print(f"❌ 失敗: {response.status_code}")
            break
        
        time.sleep(duration + 0.5)  # 等待完成
    
    print("🎉 測試序列完成")

if __name__ == "__main__":
    test_sequence()
EOF

python3 continuous_test.py
```

### 2. 性能測試

```bash
# 創建性能測試腳本
cat > performance_test.py << 'EOF'
#!/usr/bin/env python3
import requests
import time

API_BASE = "http://localhost:8000"

def performance_test():
    print("⚡ 開始性能測試...")
    
    # 測試響應時間
    times = []
    for i in range(10):
        start = time.time()
        
        response = requests.post(
            f"{API_BASE}/api/car/control",
            params={"action": "stop"}
        )
        
        end = time.time()
        duration = (end - start) * 1000
        times.append(duration)
        
        print(f"請求 {i+1}: {duration:.2f}ms")
        time.sleep(0.1)
    
    avg_time = sum(times) / len(times)
    print(f"平均響應時間: {avg_time:.2f}ms")
    
    if avg_time < 100:
        print("✅ 性能良好")
    elif avg_time < 500:
        print("⚠️ 性能一般")
    else:
        print("❌ 性能較差，檢查網絡")

if __name__ == "__main__":
    performance_test()
EOF

python3 performance_test.py
```

---

## 🔍 故障排除指南

### 電機不轉動
```bash
# 檢查步驟
1. 檢查電源: vcgencmd measure_temp
2. 檢查接線: python3 gpio_test.py  
3. 檢查驅動: 觀察 L298N LED
4. 檢查電機: 直接接電池測試
```

### 網絡連接問題
```bash
# 測試連接
python3 test_connection.py 樹莓派IP

# 檢查防火牆
sudo ufw status

# 重啟服務
sudo systemctl restart robot-control
```

### 控制延遲問題
```bash
# 檢查系統負載
htop

# 檢查網絡延遲
ping 樹莓派IP

# 檢查服務器日誌
sudo journalctl -u robot-control -f
```

---

## 🎯 測試完成檢查清單

### ✅ 基礎功能
- [ ] 四個方向運動正常
- [ ] 停止功能響應及時
- [ ] 緊急停止可靠運作
- [ ] 狀態反饋準確

### ✅ 網絡功能  
- [ ] API 端點正常響應
- [ ] Web 界面控制正常
- [ ] 移動設備可訪問
- [ ] 實時狀態更新

### ✅ 安全功能
- [ ] 緊急停止可靠
- [ ] 過熱保護正常
- [ ] 電源保護有效
- [ ] 異常恢復正常

### ✅ 性能指標
- [ ] 響應時間 < 100ms
- [ ] 控制精度良好
- [ ] 運行穩定無崩潰
- [ ] 電池續航合理

---

## 🎉 恭喜測試完成！

如果所有測試都通過，您的機器人車輛已經準備好了！

### 🚀 接下來您可以：
1. **開發自動功能** - 添加感測器和自動駕駛
2. **擴展控制邏輯** - 實現更複雜的運動模式
3. **整合AI功能** - 添加視覺識別和路徑規劃
4. **分享您的成果** - 展示給朋友或社群

**祝您的機器人項目成功！** 🤖🎊
