# 🍓 樹莓派5部署指南

## 🚀 快速部署 (從GitHub)

### 步驟1: 在樹莓派上克隆最新代碼

```bash
# 如果已有舊版本，先備份
if [ -d "medical_robot" ]; then
    mv medical_robot medical_robot_backup_$(date +%Y%m%d_%H%M%S)
fi

# 克隆最新代碼
git clone https://github.com/jaywang172/medical_robot.git
cd medical_robot
```

### 步驟2: 運行自動化設置

```bash
# 給腳本執行權限
chmod +x raspberry_pi5_setup.sh

# 運行設置腳本（會自動檢測樹莓派5）
./raspberry_pi5_setup.sh
```

設置腳本會自動：
- ✅ 檢測樹莓派5並安裝專用GPIO庫
- ✅ 安裝攝像頭支持 (picamera2, libcamera)
- ✅ 創建Python虛擬環境
- ✅ 安裝所有依賴
- ✅ 配置權限和系統設置
- ✅ 創建測試腳本

### 步驟3: 診斷和測試

```bash
# 激活虛擬環境
source /home/$USER/robot_project/venv/bin/activate

# 進入項目目錄
cd /home/$USER/robot_project

# 複製項目文件
cp -r ~/medical_robot/* .

# 運行攝像頭診斷
python3 fix_camera_pi5.py

# 測試GPIO庫
python3 test_gpio.py

# 測試攝像頭功能
python3 test_camera_functionality.py
```

### 步驟4: 啟動服務

```bash
# 啟動機器人服務器
python3 simple_car_server.py --hardware
```

如果一切正常，你應該看到：

```
✅ 使用 lgpio 庫 - Pi 5 兼容模式
✅ GPIO初始化成功 - 使用 lgpio  
🚗 車輛控制器已初始化 - 硬件模式 (lgpio)
📹 正在初始化攝像頭...
✅ picamera2 啟動成功
🚀 應用啟動中...
INFO:     Started server process [1234]
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 🔧 手動步驟 (如果自動化失敗)

### 1. 更新系統和依賴

```bash
sudo apt update && sudo apt upgrade -y

# 樹莓派5專用GPIO庫
sudo apt install -y python3-lgpio python3-rpi-lgpio

# 通用GPIO庫（備用）
sudo apt install -y python3-gpiozero python3-rpi.gpio

# 攝像頭支持
sudo apt install -y python3-picamera2 libcamera-apps

# Web框架
pip3 install fastapi uvicorn websockets aiofiles pydantic
```

### 2. 配置攝像頭

```bash
# 檢查攝像頭配置
sudo nano /boot/firmware/config.txt
# 確保包含: camera_auto_detect=1

# 添加用戶到video組
sudo usermod -a -G video $USER

# 重啟
sudo reboot
```

### 3. 測試攝像頭

```bash
# 檢測攝像頭
libcamera-hello --list-cameras

# 測試拍照
libcamera-still -o test.jpg
```

## 📱 前端訪問

服務器啟動後，可以通過以下方式訪問：

```bash
# 獲取樹莓派IP地址
hostname -I

# 瀏覽器訪問:
# http://樹莓派IP:8000/docs    - API文檔
# http://樹莓派IP:8000/api/vision/stream - 視頻流測試
```

## 🎯 開機自啟動 (可選)

```bash
# 安裝系統服務
sudo cp robot_control.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable robot_control

# 服務管理命令
sudo systemctl start robot_control    # 啟動服務
sudo systemctl stop robot_control     # 停止服務  
sudo systemctl status robot_control   # 查看狀態
sudo systemctl restart robot_control  # 重啟服務
```

## ⚠️ 常見問題

### Q1: 仍然出現 "Cannot determine SOC peripheral base address"

**A1:** 確保安裝了正確的GPIO庫：
```bash
sudo apt install python3-lgpio python3-rpi-lgpio -y
pip3 install rpi-lgpio
```

### Q2: 攝像頭無法初始化

**A2:** 檢查攝像頭連接和配置：
```bash
# 檢查攝像頭檢測
libcamera-hello --list-cameras

# 檢查配置文件
grep camera /boot/firmware/config.txt

# 重新配置
sudo raspi-config
# -> Interface Options -> Camera -> Enable
```

### Q3: 權限問題

**A3:** 確保用戶在正確的組中：
```bash
# 檢查用戶組
groups $USER

# 添加到必要的組
sudo usermod -a -G video,gpio $USER
sudo reboot
```

## 🎉 部署完成！

現在你的樹莓派5機器人應該可以正常運行了！

- 🌐 **Web界面**: http://樹莓派IP:8000
- 📊 **API文檔**: http://樹莓派IP:8000/docs  
- 📹 **視頻流**: http://樹莓派IP:8000/api/vision/stream

享受你的樹莓派5機器人吧！ 🤖
