# 🍓 樹莓派機器人控制系統完整配置指南

> **本指南適合零經驗的初學者**，將帶您從頭開始完成樹莓派與車輛控制系統的完整配置。

## 📋 目錄

1. [硬件準備清單](#1-硬件準備清單)
2. [樹莓派系統安裝](#2-樹莓派系統安裝)
3. [基礎系統配置](#3-基礎系統配置)
4. [硬件連接指南](#4-硬件連接指南)
5. [軟件環境安裝](#5-軟件環境安裝)
6. [項目代碼部署](#6-項目代碼部署)
7. [網絡配置設置](#7-網絡配置設置)
8. [測試與驗證](#8-測試與驗證)
9. [故障排除指南](#9-故障排除指南)
10. [進階配置](#10-進階配置)

---

## 1. 硬件準備清單

### 🛒 必需硬件清單

| 項目 | 規格建議 | 數量 | 估價 | 購買鏈接建議 |
|------|----------|------|------|-------------|
| **樹莓派4B** | 4GB RAM 版本 | 1 | $75 | 官方經銷商 |
| **micro SD卡** | 32GB+ Class 10 (建議64GB) | 1 | $15 | SanDisk Ultra |
| **電源供應器** | 5V 3A USB-C (官方推薦) | 1 | $10 | 樹莓派官方 |
| **HDMI線** | micro HDMI 轉 HDMI | 1 | $8 | 任何品牌 |
| **鍵盤滑鼠** | USB接口 | 1套 | $20 | 任何品牌 |
| **網線** | CAT5e 或更好 | 1 | $5 | 任何品牌 |
| **散熱片套裝** | 包含風扇 | 1 | $10 | 官方套裝 |
| **保護殼** | 透明壓克力或ABS | 1 | $8 | 任何品牌 |

### ⚙️ 車輛控制硬件 (可選)

| 項目 | 規格建議 | 數量 | 估價 | 說明 |
|------|----------|------|------|-----|
| **電機驅動板** | L298N 或 DRV8833 | 1 | $5 | 雙電機驅動 |
| **直流電機** | 12V 減速電機 | 2 | $30 | 左右輪驅動 |
| **超聲波感測器** | HC-SR04 | 4 | $8 | 前後左右避障 |
| **陀螺儀模組** | MPU6050 (I2C) | 1 | $3 | 姿態檢測 |
| **跳線** | 杜邦線 公母各一套 | 1 | $5 | 連接用 |
| **麵包板** | 半尺寸或全尺寸 | 1 | $3 | 原型開發 |
| **12V電池** | 鋰電池 3000mAh+ | 1 | $25 | 電機供電 |
| **降壓模組** | LM2596 (12V→5V) | 1 | $3 | 電壓轉換 |

### 🔧 工具準備

- 螺絲刀套裝 (十字、一字)
- 剝線鉗
- 萬用電表 (建議)
- 熱縮管和打火機 (可選)

**總預算估算**: 基礎配置 ~$150，完整配置 ~$220

---

## 2. 樹莓派系統安裝

### 📱 下載 Raspberry Pi Imager

1. **訪問官方網站**：
   - 前往 https://www.raspberrypi.org/software/
   - 下載適合您操作系統的 Raspberry Pi Imager

2. **安裝 Imager**：
   ```bash
   # Windows: 運行下載的 .exe 文件
   # macOS: 拖拽到應用程序文件夾
   # Linux: 
   sudo apt update
   sudo apt install rpi-imager
   ```

### 💾 準備 SD 卡

1. **格式化 SD 卡**：
   - 將 SD 卡插入電腦
   - 使用 SD Card Formatter 格式化（推薦）
   - 或在 Imager 中直接格式化

2. **燒錄系統**：
   - 啟動 Raspberry Pi Imager
   - 選擇作業系統：`Raspberry Pi OS (64-bit)` **推薦**
   - 選擇儲存裝置：您的 SD 卡
   - 點擊齒輪圖標進行高級設置

### ⚙️ 高級設置 (重要!)

在燒錄前，**務必**配置以下設置：

```
✅ 啟用 SSH
   用戶名: pi
   密碼: [設置一個強密碼，記住它！]

✅ 設置 WiFi (如果要用無線)
   SSID: [您的WiFi名稱]
   密碼: [您的WiFi密碼]
   國家: TW (台灣)

✅ 設置地區
   時區: Asia/Taipei
   鍵盤: US (English)

✅ 啟用 SSH
   使用密碼認證

✅ 播放完成提示音
```

3. **開始燒錄**：
   - 確認所有設置無誤後，點擊「燒錄」
   - 等待燒錄完成（約 5-10 分鐘）
   - 燒錄完成後，安全移除 SD 卡

---

## 3. 基礎系統配置

### 🔌 首次啟動

1. **硬件連接**：
   ```
   SD卡 → 樹莓派
   HDMI → 顯示器 (首次設置需要)
   鍵盤 → USB
   網線 → 路由器 (或使用WiFi)
   電源 → 最後連接
   ```

2. **啟動系統**：
   - 連接電源，看到紅燈亮起
   - 綠燈閃爍表示系統正在啟動
   - 等待桌面出現（約 1-2 分鐘）

### 🌐 網絡配置

#### 方法 1: 有線連接 (推薦)
```bash
# 檢查網絡狀態
ifconfig
# 應該看到 eth0 有 IP 地址

# 測試網絡
ping google.com
```

#### 方法 2: WiFi 連接
```bash
# 如果之前沒設置WiFi，現在設置
sudo raspi-config

# 選擇: 2 Network Options
# 選擇: N2 WiFi
# 輸入 SSID 和密碼
```

### 🔧 系統基礎設置

開啟終端機，執行以下命令：

```bash
# 1. 更新系統
sudo apt update
sudo apt upgrade -y

# 2. 啟用必要接口
sudo raspi-config
```

在 `raspi-config` 中設置：
```
1. Interface Options
   - SSH: Enable (如果還沒啟用)
   - I2C: Enable (感測器需要)
   - SPI: Enable (可選)
   - Camera: Enable (如果有相機)

2. Advanced Options
   - Memory Split: 128 (如果使用相機)

3. System Options
   - Boot / Auto Login: Console (無桌面啟動，節省資源)
```

設置完成後重啟：
```bash
sudo reboot
```

### 📡 SSH 連接設置

重啟後，您可以使用 SSH 遠程連接：

```bash
# 在您的電腦上執行
ssh pi@[樹莓派IP地址]

# 例如：
ssh pi@192.168.1.100
```

**如何找到樹莓派 IP 地址：**

方法 1: 在樹莓派上執行
```bash
hostname -I
```

方法 2: 在路由器管理界面查看

方法 3: 網絡掃描
```bash
# 在您的電腦上 (Linux/Mac)
nmap -sn 192.168.1.0/24 | grep -B 2 "Raspberry"

# Windows 可用 Advanced IP Scanner
```

---

## 4. 硬件連接指南

### 🔌 GPIO 針腳圖

```
樹莓派 4B GPIO 針腳圖：

     3V3  (1) (2)  5V
   GPIO2  (3) (4)  5V
   GPIO3  (5) (6)  GND
   GPIO4  (7) (8)  GPIO14
     GND  (9) (10) GPIO15
  GPIO17 (11) (12) GPIO18
  GPIO27 (13) (14) GND
  GPIO22 (15) (16) GPIO23
     3V3 (17) (18) GPIO24
  GPIO10 (19) (20) GND
   GPIO9 (21) (22) GPIO25
  GPIO11 (23) (24) GPIO8
     GND (25) (26) GPIO7
   GPIO0 (27) (28) GPIO1
   GPIO5 (29) (30) GND
   GPIO6 (31) (32) GPIO12
  GPIO13 (33) (34) GND
  GPIO19 (35) (36) GPIO16
  GPIO26 (37) (38) GPIO20
     GND (39) (40) GPIO21
```

### ⚙️ 電機驅動連接

#### L298N 電機驅動板連接

```
樹莓派 → L298N 電機驅動板：

GPIO 針腳 → L298N 針腳
-----------------
GPIO 16  → IN1 (右電機正轉)  [car_run_turn.py 中的 Motor_R1_Pin]
GPIO 18  → IN2 (右電機反轉)  [car_run_turn.py 中的 Motor_R2_Pin]
GPIO 11  → IN3 (左電機正轉)  [car_run_turn.py 中的 Motor_L1_Pin]
GPIO 13  → IN4 (左電機反轉)  [car_run_turn.py 中的 Motor_L2_Pin]
5V       → VCC (邏輯電源)
GND      → GND (公共地線)

L298N → 電機：
-----------
OUT1, OUT2 → 右電機
OUT3, OUT4 → 左電機

L298N → 電池：
-----------
VIN, GND → 12V 電池正負極
```

**重要安全提醒：**
- 🔥 **電源分離**：邏輯電路(5V)和電機電源(12V)要分開
- ⚡ **共地連接**：所有地線(GND)必須連在一起
- 🔋 **電流保護**：建議加保險絲(5A)

### 📡 感測器連接 (可選)

#### 超聲波感測器 HC-SR04

```
樹莓派 → HC-SR04 (前方)：
GPIO 23 → Trig
GPIO 24 → Echo
5V      → VCC
GND     → GND

樹莓派 → HC-SR04 (後方)：
GPIO 25 → Trig
GPIO 8  → Echo
5V      → VCC
GND     → GND

(左方和右方感測器類似，使用其他 GPIO)
```

#### IMU 陀螺儀 MPU6050

```
樹莓派 → MPU6050：
GPIO 2 (SDA) → SDA
GPIO 3 (SCL) → SCL
3V3          → VCC
GND          → GND
```

### 🔋 電源系統連接

```
電源分配建議：

12V 電池 →
├── L298N (電機驅動)
└── LM2596 降壓模組 →
    └── 樹莓派 (通過 GPIO 或 USB-C)

備註：
- 樹莓派可用 5V 2.5A+ 電源
- 電機需要 12V 電源
- 降壓模組將 12V 轉為 5V
```

### ⚠️ 連接檢查清單

在通電前，請檢查：

- [ ] 所有地線(GND)都連接到一起
- [ ] 5V 和 3.3V 沒有短路
- [ ] 電機驅動板的電源連接正確
- [ ] GPIO 針腳連接無誤
- [ ] 沒有裸露的金屬線碰觸
- [ ] 電池電壓正確 (12V ±1V)

---

## 5. 軟件環境安裝

### 🐍 Python 環境設置

```bash
# 1. 檢查 Python 版本
python3 --version
# 應該顯示 Python 3.9+ 

# 2. 安裝 pip 和虛擬環境
sudo apt install -y python3-pip python3-venv

# 3. 安裝系統依賴
sudo apt install -y git cmake build-essential
sudo apt install -y python3-dev python3-setuptools
sudo apt install -y libffi-dev libssl-dev

# 4. 安裝 GPIO 相關套件
sudo apt install -y python3-gpiozero python3-rpi.gpio
```

### 📦 專案依賴安裝

```bash
# 1. 創建專案目錄
mkdir -p /home/pi/robot_project
cd /home/pi/robot_project

# 2. 創建虛擬環境
python3 -m venv venv
source venv/bin/activate

# 3. 升級 pip
pip install --upgrade pip

# 4. 安裝核心依賴
pip install fastapi uvicorn websockets aiofiles pydantic

# 5. 安裝 GPIO 控制套件
pip install RPi.GPIO gpiozero

# 6. 安裝其他有用套件
pip install requests psutil  # 系統監控
```

### 🔧 可選依賴 (視需求安裝)

```bash
# 如果需要完整功能 (會比較慢)
pip install opencv-python-headless  # 影像處理
pip install numpy pillow           # 數值計算
pip install matplotlib             # 圖表顯示

# 如果需要資料庫
pip install sqlite3

# 如果需要機器學習
pip install scikit-learn
```

### ⚡ 系統優化

```bash
# 1. 增加 swap 空間 (如果記憶體不足)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 2. 設置開機自動激活 swap
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 3. 設置 GPU 記憶體分配
sudo raspi-config
# Advanced Options → Memory Split → 64 (如果不用圖形界面)

# 4. 禁用不需要的服務
sudo systemctl disable bluetooth
sudo systemctl disable hciuart  # 如果不用藍牙
```

---

## 6. 項目代碼部署

### 📁 獲取專案代碼

#### 方法 1: 從您的電腦傳輸

```bash
# 在您的電腦上 (專案目錄)
scp -r . pi@[樹莓派IP]:/home/pi/robot_project/

# 例如：
scp -r /Users/jaywang/Desktop/poster pi@192.168.1.100:/home/pi/robot_project/
```

#### 方法 2: 使用 Git (如果代碼在 Git 倉庫)

```bash
# 在樹莓派上
cd /home/pi/robot_project
git clone [您的倉庫地址] .

# 或者如果已經有本地檔案
git init
git remote add origin [倉庫地址]
git pull origin main
```

#### 方法 3: 使用 USB 隨身碟

```bash
# 1. 將隨身碟插入樹莓派
# 2. 掛載隨身碟
sudo mkdir /mnt/usb
sudo mount /dev/sda1 /mnt/usb

# 3. 複製檔案
cp -r /mnt/usb/poster/* /home/pi/robot_project/

# 4. 卸載隨身碟
sudo umount /mnt/usb
```

### 📂 項目結構檢查

確認以下檔案存在：

```bash
cd /home/pi/robot_project
ls -la

# 應該看到：
robot_core/
├── state_machine/
│   └── car_run_turn.py          # 核心控制檔案
├── api/
│   └── server.py                # API 服務器
└── ...

start_pi_server.py              # 樹莓派啟動腳本
pi_setup.sh                     # 設置腳本
requirements.txt                # 依賴清單
```

### 🔧 檔案權限設置

```bash
# 1. 設置執行權限
chmod +x pi_setup.sh
chmod +x start_pi_server.py

# 2. 設置 Python 檔案權限
chmod +r robot_core/state_machine/car_run_turn.py
chmod +r robot_core/api/server.py

# 3. 檢查檔案完整性
python3 -m py_compile robot_core/state_machine/car_run_turn.py
echo "✅ car_run_turn.py 語法正確"
```

### 🧪 基礎功能測試

```bash
# 1. 測試核心控制器 (模擬模式)
cd /home/pi/robot_project
python3 robot_core/state_machine/car_run_turn.py --sim

# 應該看到：
# CarRunTurnController 初始化完成 - 模擬模式
# 車輛控制器測試程序
# 指令: f=前進, b=後退, r=右轉, l=左轉, s=停止, e=緊急停止, x=重置緊急停止, q=退出

# 測試幾個指令，然後輸入 'q' 退出
```

---

## 7. 網絡配置設置

### 🌐 固定 IP 設置 (建議)

為了方便連接，建議設置固定 IP：

```bash
# 1. 編輯網絡配置
sudo nano /etc/dhcpcd.conf

# 2. 在檔案末尾添加 (根據您的網絡調整)：
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8 8.8.4.4

# 3. 儲存並退出 (Ctrl+X, Y, Enter)

# 4. 重啟網絡服務
sudo systemctl restart dhcpcd

# 5. 檢查新 IP
hostname -I
```

### 🔥 防火牆設置

```bash
# 1. 安裝 ufw 防火牆
sudo apt install ufw

# 2. 設置基本規則
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 3. 允許必要服務
sudo ufw allow ssh
sudo ufw allow 8000/tcp    # API 服務器
sudo ufw allow 3000/tcp    # 前端 (如果在樹莓派上運行)

# 4. 啟用防火牆
sudo ufw enable

# 5. 檢查狀態
sudo ufw status verbose
```

### 📡 服務器啟動測試

```bash
# 1. 啟動服務器
cd /home/pi/robot_project
python3 start_pi_server.py

# 應該看到類似輸出：
# 🍓 樹莓派機器人控制服務器
# 📁 項目路徑: /home/pi/robot_project
# ✅ FastAPI 和 uvicorn 可用
# ✅ 樹莓派 GPIO 可用  (或 ⚠️ 運行在模擬模式)
# ✅ 車輛控制器已初始化 - 硬件模式
# 🌐 主機名: raspberrypi
# 🌐 本地IP: 192.168.1.100
# 🚀 啟動服務器...
# 📡 API地址: http://192.168.1.100:8000
```

### 🧪 網絡連接測試

在另一個終端或您的電腦上測試：

```bash
# 1. 基本連接測試
curl http://192.168.1.100:8000/

# 應該返回：
# {"message":"樹莓派機器人控制API","status":"running","mode":"hardware"}

# 2. 狀態測試
curl http://192.168.1.100:8000/api/status

# 3. 車輛控制測試 (安全的停止命令)
curl -X POST "http://192.168.1.100:8000/api/car/control?action=stop"
```

---

## 8. 測試與驗證

### 🔍 系統健康檢查

創建系統檢查腳本：

```bash
# 1. 創建檢查腳本
nano /home/pi/robot_project/health_check.py
```

```python
#!/usr/bin/env python3
"""系統健康檢查腳本"""

import subprocess
import sys
import os

def check_system():
    print("🍓 樹莓派系統健康檢查")
    print("="*40)
    
    # CPU 溫度
    try:
        temp = subprocess.check_output("vcgencmd measure_temp", shell=True).decode()
        print(f"🌡️  CPU溫度: {temp.strip()}")
    except:
        print("❌ 無法讀取CPU溫度")
    
    # 記憶體使用
    try:
        mem = subprocess.check_output("free -h", shell=True).decode()
        print(f"💾 記憶體狀態:")
        print(mem.split('\n')[1])  # 顯示記憶體行
    except:
        print("❌ 無法讀取記憶體狀態")
    
    # 磁碟空間
    try:
        disk = subprocess.check_output("df -h /", shell=True).decode()
        print(f"💽 磁碟空間:")
        print(disk.split('\n')[1])  # 顯示根目錄
    except:
        print("❌ 無法讀取磁碟狀態")
    
    # GPIO 測試
    try:
        import RPi.GPIO as GPIO
        print("✅ GPIO 可用")
        GPIO.setmode(GPIO.BCM)
        GPIO.cleanup()
    except Exception as e:
        print(f"❌ GPIO 不可用: {e}")
    
    # 網絡測試
    try:
        result = subprocess.run(["ping", "-c", "1", "8.8.8.8"], 
                              capture_output=True, timeout=5)
        if result.returncode == 0:
            print("✅ 網絡連接正常")
        else:
            print("❌ 網絡連接異常")
    except:
        print("❌ 網絡測試失敗")

if __name__ == "__main__":
    check_system()
```

執行健康檢查：

```bash
chmod +x health_check.py
python3 health_check.py
```

### ⚡ 電機安全測試

**⚠️ 警告：確保電機沒有接觸任何東西，或先斷開電機連線進行測試**

```bash
# 1. 進入測試模式
cd /home/pi/robot_project
python3 robot_core/state_machine/car_run_turn.py

# 如果是真實硬件，不加 --sim 參數
# 如果要安全測試，加 --sim 參數

# 2. 按照提示測試各個方向：
# f - 前進
# b - 後退  
# l - 左轉
# r - 右轉
# s - 停止
# e - 緊急停止
# q - 退出

# 3. 觀察電機反應是否正確
```

### 🌐 前端連接測試

在您的電腦上：

```bash
# 1. 進入前端目錄
cd /path/to/poster/web_demo

# 2. 創建環境配置
echo "REACT_APP_API_BASE_URL=http://192.168.1.100:8000" > .env.local
echo "REACT_APP_WS_HOST=192.168.1.100:8000" >> .env.local

# 3. 安裝依賴 (如果還沒有)
npm install

# 4. 啟動前端
npm start

# 5. 打開瀏覽器訪問 http://localhost:3000
# 6. 進入「手動控制」頁面
# 7. 啟用「核心車輛控制」開關
# 8. 測試控制按鈕
```

### 📱 移動設備測試

1. **確保設備在同一網絡**
2. **在手機瀏覽器訪問**：`http://192.168.1.100:3000`
3. **測試觸控操作**
4. **檢查響應速度**

---

## 9. 故障排除指南

### 🚨 常見問題與解決方案

#### 問題 1: SSH 連接被拒絕

```bash
# 症狀：ssh: connect to host 192.168.1.100 port 22: Connection refused

# 解決方案：
# 1. 檢查樹莓派是否開機
# 2. 檢查 SSH 是否啟用
sudo raspi-config
# Interface Options → SSH → Enable

# 3. 重啟 SSH 服務
sudo systemctl restart ssh
sudo systemctl enable ssh

# 4. 檢查防火牆
sudo ufw status
sudo ufw allow ssh
```

#### 問題 2: GPIO 權限錯誤

```bash
# 症狀：RuntimeError: No access to /dev/mem

# 解決方案：
# 1. 將用戶加入 gpio 群組
sudo usermod -a -G gpio pi

# 2. 重新登入或重啟
sudo reboot

# 3. 或者使用 sudo 運行
sudo python3 start_pi_server.py
```

#### 問題 3: 模組導入失敗

```bash
# 症狀：ModuleNotFoundError: No module named 'xxx'

# 解決方案：
# 1. 確認虛擬環境已激活
source venv/bin/activate

# 2. 重新安裝依賴
pip install -r requirements.txt

# 3. 檢查 Python 路徑
python3 -c "import sys; print(sys.path)"
```

#### 問題 4: 電機不響應

```bash
# 檢查清單：
# 1. 電源供應是否足夠
# 2. 接線是否正確
# 3. 電機驅動板是否正常
# 4. GPIO 針腳是否對應

# 調試步驟：
# 1. 用萬用電表檢查電壓
# 2. 檢查接線圖對照
# 3. 測試單一電機
# 4. 檢查驅動板LED狀態
```

#### 問題 5: 網絡連接不穩定

```bash
# 1. 檢查信號強度 (WiFi)
iwconfig wlan0

# 2. 重啟網絡服務
sudo systemctl restart dhcpcd

# 3. 使用有線連接 (更穩定)

# 4. 檢查路由器設置
```

#### 問題 6: 系統過熱

```bash
# 1. 檢查溫度
vcgencmd measure_temp

# 2. 如果超過 70°C：
# - 加裝散熱片和風扇
# - 降低 CPU 頻率
# - 改善通風

# 3. 設置溫度監控
watch -n 2 vcgencmd measure_temp
```

### 🔧 調試工具

```bash
# 1. 系統日誌
sudo journalctl -f  # 即時日誌
sudo dmesg          # 開機訊息

# 2. GPIO 狀態檢查
gpio readall        # 顯示所有 GPIO 狀態

# 3. 進程監控
htop                # 系統監控
ps aux | grep python # Python 進程

# 4. 網絡診斷
netstat -tlnp       # 端口監聽狀態
ss -tlnp            # 現代版本

# 5. 硬體狀態
vcgencmd version    # 韌體版本
vcgencmd get_config int # 配置查看
```

---

## 10. 進階配置

### 🔄 開機自動啟動

創建 systemd 服務：

```bash
# 1. 創建服務文件
sudo nano /etc/systemd/system/robot-control.service
```

```ini
[Unit]
Description=Robot Control Server
After=network.target

[Service]
Type=simple
User=pi
Group=pi
WorkingDirectory=/home/pi/robot_project
Environment=PATH=/home/pi/robot_project/venv/bin
ExecStart=/home/pi/robot_project/venv/bin/python start_pi_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# 2. 啟用服務
sudo systemctl enable robot-control
sudo systemctl start robot-control

# 3. 檢查服務狀態
sudo systemctl status robot-control

# 4. 查看日誌
sudo journalctl -u robot-control -f
```

### 📊 系統監控

安裝監控工具：

```bash
# 1. 安裝監控套件
pip install psutil flask

# 2. 創建監控頁面
nano /home/pi/robot_project/monitor.py
```

```python
#!/usr/bin/env python3
"""系統監控頁面"""

from flask import Flask, jsonify, render_template_string
import psutil
import subprocess

app = Flask(__name__)

@app.route('/monitor')
def monitor():
    # 獲取系統資訊
    cpu_temp = subprocess.check_output("vcgencmd measure_temp", shell=True).decode().strip()
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return jsonify({
        'cpu_temp': cpu_temp,
        'cpu_percent': cpu_percent,
        'memory_percent': memory.percent,
        'disk_percent': disk.percent,
        'timestamp': time.time()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### 🔒 安全加固

```bash
# 1. 更改默認密碼
passwd

# 2. 禁用 root 登入
sudo passwd -l root

# 3. 設置 SSH 金鑰認證
ssh-keygen -t rsa -b 4096
# 將公鑰上傳到樹莓派

# 4. 限制 SSH 訪問
sudo nano /etc/ssh/sshd_config
# 修改：
# PermitRootLogin no
# PasswordAuthentication no (使用金鑰後)
# Port 2222 (更改默認端口)

# 5. 安裝 fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### 📦 系統備份

```bash
# 1. 創建系統映像檔 (在另一台電腦上)
sudo dd if=/dev/sdX of=robot_backup.img bs=4M status=progress

# 2. 壓縮備份
gzip robot_backup.img

# 3. 定期備份專案檔案
tar -czf robot_project_$(date +%Y%m%d).tar.gz /home/pi/robot_project
```

### 🚀 性能優化

```bash
# 1. 調整 GPU 記憶體分配
sudo raspi-config
# Advanced Options → Memory Split → 16 (無圖形界面時)

# 2. 禁用不需要的服務
sudo systemctl disable bluetooth
sudo systemctl disable hciuart
sudo systemctl disable triggerhappy

# 3. 調整 swap 設置
sudo nano /etc/dphys-swapfile
# 修改 CONF_SWAPSIZE=1024

# 4. 優化 SD 卡性能
sudo nano /boot/cmdline.txt
# 添加：fsck.mode=skip noswap

# 5. 設置 CPU 頻率
echo 'arm_freq=1500' | sudo tee -a /boot/config.txt
```

---

## 📞 完成檢查清單

完成所有設置後，請確認以下項目：

### ✅ 硬件檢查
- [ ] 樹莓派正常開機，綠燈閃爍
- [ ] 網絡連接正常，可 SSH 登入
- [ ] GPIO 針腳連接正確
- [ ] 電機電源供應充足
- [ ] 所有接線牢固，無短路

### ✅ 軟件檢查
- [ ] Python 環境正常
- [ ] 所有依賴套件已安裝
- [ ] 專案代碼已部署
- [ ] 核心控制器測試通過
- [ ] API 服務器可正常啟動

### ✅ 網絡檢查
- [ ] 樹莓派 IP 地址固定
- [ ] 防火牆設置正確
- [ ] API 端點可正常訪問
- [ ] WebSocket 連接正常

### ✅ 功能檢查
- [ ] 電機控制指令響應正確
- [ ] 緊急停止功能正常
- [ ] 前端界面可正常連接
- [ ] 移動設備可正常訪問

### ✅ 安全檢查
- [ ] SSH 密碼已更改
- [ ] 防火牆已啟用
- [ ] 系統已更新到最新版本
- [ ] 備份已完成

---

## 🎉 恭喜完成！

如果您已經完成上述所有步驟，您的樹莓派機器人控制系統就已經完全配置好了！

### 🚀 接下來您可以：

1. **開始控制機器人**：使用前端界面控制車輛移動
2. **擴展功能**：添加感測器、相機等設備
3. **開發自動化**：編寫自動導航和避障程序
4. **分享經驗**：將您的專案分享給其他人

### 📚 進一步學習資源：

- [樹莓派官方文檔](https://www.raspberrypi.org/documentation/)
- [GPIO 針腳說明](https://pinout.xyz/)
- [Python GPIO 教學](https://gpiozero.readthedocs.io/)
- [FastAPI 文檔](https://fastapi.tiangolo.com/)

### 🆘 需要幫助？

如果遇到任何問題，請提供：
1. 錯誤訊息的完整內容
2. 執行的具體步驟
3. 硬件連接圖片 (如果相關)
4. 系統資訊 (`uname -a`, `python3 --version`)

**祝您的機器人專案成功！** 🤖🎊
