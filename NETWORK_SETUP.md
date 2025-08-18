# 🌐 樹莓派與 Web Demo 網絡連接設置指南

## 📋 連接架構

```
[您的電腦/手機]  ←→  [路由器/WiFi]  ←→  [樹莓派]
    前端界面                網絡              後端API
   (Port 3000)                            (Port 8000)
```

## 🍓 樹莓派設置步驟

### 1. 上傳代碼到樹莓派

```bash
# 方法1: 使用 scp 上傳
scp -r /path/to/poster pi@樹莓派IP:/home/pi/robot_project

# 方法2: 使用 git 克隆
ssh pi@樹莓派IP
cd /home/pi
git clone <你的倉庫地址> robot_project
cd robot_project
```

### 2. 在樹莓派上執行設置

```bash
# SSH 連接到樹莓派
ssh pi@樹莓派IP

# 進入項目目錄
cd robot_project

# 執行設置腳本
chmod +x pi_setup.sh
./pi_setup.sh
```

### 3. 啟動樹莓派服務器

```bash
# 方法1: 直接運行
python3 start_pi_server.py

# 方法2: 後台運行
nohup python3 start_pi_server.py > server.log 2>&1 &

# 方法3: 使用 systemd 服務 (推薦)
sudo cp robot_control.service /etc/systemd/system/
sudo systemctl enable robot_control
sudo systemctl start robot_control
sudo systemctl status robot_control
```

## 💻 前端配置步驟

### 1. 找到樹莓派IP地址

在樹莓派上執行：
```bash
hostname -I
```
或者
```bash
ifconfig | grep "inet " | grep -v 127.0.0.1
```

假設您的樹莓派IP是：`192.168.1.100`

### 2. 配置前端API地址

創建 `web_demo/.env.local` 文件：
```bash
# 樹莓派 API 服務器地址
REACT_APP_API_BASE_URL=http://192.168.1.100:8000
REACT_APP_WS_HOST=192.168.1.100:8000
```

### 3. 啟動前端開發服務器

```bash
cd web_demo
npm install
npm start
```

## 🔧 網絡故障排除

### 1. 檢查樹莓派服務器狀態

```bash
# 檢查服務器是否運行
curl http://樹莓派IP:8000/

# 檢查API狀態
curl http://樹莓派IP:8000/api/status

# 檢查車輛控制器
curl http://樹莓派IP:8000/api/car/status
```

### 2. 檢查網絡連通性

```bash
# 從您的電腦 ping 樹莓派
ping 樹莓派IP

# 檢查端口是否開放
telnet 樹莓派IP 8000
```

### 3. 常見問題解決

#### 問題1: 前端無法連接到後端
- 檢查樹莓派防火牆設置：`sudo ufw status`
- 如果防火牆開啟，允許端口：`sudo ufw allow 8000`
- 檢查`.env.local`中的IP地址是否正確

#### 問題2: CORS 錯誤
- 確保後端已正確設置 CORS
- 檢查前端請求的域名是否正確

#### 問題3: GPIO 權限錯誤
```bash
# 將用戶加入 gpio 群組
sudo usermod -a -G gpio $USER

# 重新登錄或重啟樹莓派
sudo reboot
```

## 📱 移動設備訪問

如果您想在手機或平板上控制機器人：

1. 確保移動設備與樹莓派在同一WiFi網絡
2. 在移動設備瀏覽器中訪問：`http://樹莓派IP:3000`
3. 響應式界面會自動適配移動設備

## 🔒 安全建議

### 生產環境設置

1. **更改默認密碼**
```bash
passwd  # 更改 pi 用戶密碼
```

2. **設置防火牆**
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 8000
```

3. **使用HTTPS**（可選）
```bash
# 安裝 Let's Encrypt
sudo apt install certbot
# 配置 SSL 證書
```

4. **限制 CORS 域名**
修改 `start_pi_server.py` 中的 CORS 設置：
```python
allow_origins=["http://您的前端域名:3000"],
```

## 🎯 測試連接

### 完整測試流程

1. **樹莓派端測試**：
```bash
# 測試本地API
curl http://localhost:8000/api/status

# 測試車輛控制
curl -X POST "http://localhost:8000/api/car/control?action=forward&duration=0.1"
```

2. **前端測試**：
- 打開瀏覽器訪問 `http://localhost:3000`
- 進入「手動控制」頁面
- 啟用「核心車輛控制」開關
- 測試各種控制按鈕

3. **跨設備測試**：
- 在其他設備上訪問 `http://樹莓派IP:3000`
- 確保所有功能正常工作

## 📞 獲取幫助

如果遇到問題，請提供以下信息：

1. 樹莓派型號和系統版本：`cat /etc/os-release`
2. Python 版本：`python3 --version`
3. 網絡配置：`ifconfig`
4. 服務器日誌：`tail -f server.log`
5. 瀏覽器控制台錯誤信息

成功連接後，您就可以享受完整的機器人控制體驗了！🎉
