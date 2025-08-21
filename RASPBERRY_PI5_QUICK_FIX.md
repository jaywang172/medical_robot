# 🍓 樹莓派5快速修復指南

## 問題描述

你遇到的問題是典型的樹莓派5兼容性問題：

1. **GPIO初始化失敗**: `Cannot determine SOC peripheral base address`
2. **攝像頭無法工作**: picamera2 初始化問題
3. **FastAPI警告**: 使用了已棄用的事件處理方式

## 🚀 快速解決方案

### 步驟1: 下載修復腳本到樹莓派

```bash
# 下載設置腳本
wget https://raw.githubusercontent.com/your-repo/poster/main/raspberry_pi5_setup.sh
chmod +x raspberry_pi5_setup.sh

# 下載攝像頭修復腳本  
wget https://raw.githubusercontent.com/your-repo/poster/main/fix_camera_pi5.py
chmod +x fix_camera_pi5.py
```

### 步驟2: 運行設置腳本

```bash
# 運行樹莓派5設置腳本
./raspberry_pi5_setup.sh
```

這個腳本會：
- ✅ 自動檢測樹莓派5
- ✅ 安裝 `lgpio` (樹莓派5專用GPIO庫)
- ✅ 安裝 `picamera2` 和相關依賴
- ✅ 配置攝像頭接口
- ✅ 創建測試腳本

### 步驟3: 運行攝像頭診斷

```bash
# 運行攝像頭診斷工具
python3 fix_camera_pi5.py
```

### 步驟4: 更新你的代碼

將修復後的代碼文件複製到樹莓派：

```bash
# 複製修復後的文件
scp robot_core/hardware/car_run_turn.py pi@your-pi-ip:/home/pi/robot_project/robot_core/hardware/
scp simple_car_server.py pi@your-pi-ip:/home/pi/robot_project/
```

### 步驟5: 測試運行

```bash
cd /home/pi/robot_project
source venv/bin/activate

# 測試GPIO
python test_gpio.py

# 測試攝像頭
python test_camera_functionality.py

# 啟動服務器
python simple_car_server.py --hardware
```

## 🔧 手動修復步驟 (如果自動腳本失敗)

### 1. 安裝樹莓派5 GPIO庫

```bash
# 更新系統
sudo apt update && sudo apt upgrade -y

# 安裝 lgpio (樹莓派5推薦)
sudo apt install -y python3-lgpio python3-rpi-lgpio

# 備用GPIO庫
sudo apt install -y python3-gpiozero python3-rpi.gpio
```

### 2. 修復攝像頭支持

```bash
# 安裝攝像頭庫
sudo apt install -y python3-picamera2 libcamera-apps

# 檢查攝像頭配置
sudo nano /boot/firmware/config.txt
# 確保包含: camera_auto_detect=1

# 將用戶加入video組
sudo usermod -a -G video $USER

# 重啟系統
sudo reboot
```

### 3. 測試攝像頭

```bash
# 使用libcamera測試
libcamera-hello --list-cameras

# 拍攝測試照片
libcamera-still -o test.jpg
```

## 🐛 常見問題解決

### 問題1: "Cannot determine SOC peripheral base address"

**原因**: 樹莓派5使用新的硬件架構，舊的GPIO庫不兼容

**解決方案**:
```bash
# 安裝新的GPIO庫
sudo apt install python3-lgpio python3-rpi-lgpio
pip install rpi-lgpio
```

### 問題2: 攝像頭無法初始化

**原因**: picamera2配置問題或權限問題

**解決方案**:
```bash
# 檢查攝像頭檢測
libcamera-hello --list-cameras

# 檢查權限
groups $USER  # 應該包含 video

# 如果沒有video組
sudo usermod -a -G video $USER
sudo reboot
```

### 問題3: FastAPI Deprecation Warnings

**原因**: 使用了舊的事件處理方式

**解決方案**: 已在修復的代碼中使用新的 `lifespan` 方式

## 📋 驗證修復結果

運行以下命令驗證一切正常：

```bash
cd /home/pi/robot_project
source venv/bin/activate

# 1. 測試GPIO庫
python -c "
try:
    import lgpio
    print('✅ lgpio 可用')
except:
    print('❌ lgpio 不可用')

try:
    from gpiozero import OutputDevice
    print('✅ gpiozero 可用')
except:
    print('❌ gpiozero 不可用')
"

# 2. 測試攝像頭
python -c "
try:
    from picamera2 import Picamera2
    print('✅ picamera2 可用')
except:
    print('❌ picamera2 不可用')
"

# 3. 啟動服務器
python simple_car_server.py --hardware
```

如果看到類似以下輸出，說明修復成功：

```
✅ 使用 lgpio 庫 - Pi 5 兼容模式
✅ GPIO初始化成功 - 使用 lgpio
🚗 車輛控制器已初始化 - 硬件模式 (lgpio)
📹 正在初始化攝像頭...
✅ picamera2 啟動成功
🚀 應用啟動中...
INFO:     Started server process [1234]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 🎯 總結

修復的核心變更：

1. **GPIO庫兼容性**: 支持 `lgpio` (Pi5專用) → `gpiozero` (通用) → `RPi.GPIO` (傳統)
2. **攝像頭初始化**: 改進了 `picamera2` 的錯誤處理和降級機制  
3. **FastAPI現代化**: 使用 `lifespan` 替代已棄用的事件處理器

現在你的機器人應該可以在樹莓派5上正常運行了！ 🎉
