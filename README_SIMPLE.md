# 🚗 樹莓派車輛控制系統

<div align="center">

![Robot](https://img.shields.io/badge/Robot-Car%20Control-blue)
![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%204B-red)
![Language](https://img.shields.io/badge/Language-Python%203.8+-yellow)
![Frontend](https://img.shields.io/badge/Frontend-React%2018-cyan)
![API](https://img.shields.io/badge/API-FastAPI-green)
![Status](https://img.shields.io/badge/Status-Core%20Complete-brightgreen)

**基於樹莓派的車輛控制系統，支援Web前端控制和API操作**

[🚀 快速開始](#-快速開始) • [🎮 控制方式](#-控制方式) • [🔧 API文檔](#-api文檔) • [📁 項目結構](#-項目結構)

</div>

---

## ✨ 核心功能

### 🎮 車輛控制
- **⬆️ 前進/後退** - 精確的方向控制
- **↔️ 左轉/右轉** - 靈活的轉向操作  
- **⏹️ 即時停止** - 立即停止功能
- **🚨 緊急停止** - 安全保護機制

### 🌐 多種控制方式
- **📱 Web前端界面** - React + Ant Design響應式界面
- **📡 REST API** - 完整的HTTP API支援
- **⌨️ 鍵盤控制** - WASD或方向鍵操作
- **🖱️ 點擊控制** - 直觀的按鈕操作

### 🔧 系統特性
- **💻 雙模式運行** - 支援模擬和硬件模式
- **🚨 安全機制** - 緊急停止和狀態監控
- **📊 實時狀態** - 即時回饋車輛狀態
- **🏗️ 模組化設計** - 易於擴展和維護

---

## 🚀 快速開始

### 1️⃣ 安裝依賴
```bash
# Python依賴
pip install fastapi uvicorn requests pydantic

# 前端依賴（可選）
cd web_demo
npm install
```

### 2️⃣ 啟動服務器

#### 模擬模式（推薦測試）
```bash
python simple_car_server.py
```

#### 硬件模式（樹莓派上）
```bash
python simple_car_server.py --hardware
```

### 3️⃣ 選擇控制方式

📋 **詳細步驟請參考：[QUICK_START.md](QUICK_START.md)**

---

## 🎮 控制方式

### 方式1: Web界面 ⭐ 推薦
```bash
cd web_demo && npm start
# 瀏覽器訪問: http://localhost:3000
```

### 方式2: Python測試腳本
```bash
python test_simple_car.py
```

### 方式3: HTML測試頁面
```bash
# 直接打開
open test_car_control.html
```

### 方式4: API直接調用
```bash
# 前進
curl -X POST "http://localhost:8000/api/car/control" \
  -H "Content-Type: application/json" \
  -d '{"action": "forward", "duration": 0.5}'
```

---

## 🔧 API文檔

### 核心端點

| 方法 | 端點 | 功能 | 參數 |
|------|------|------|------|
| GET | `/` | 服務器狀態 | - |
| POST | `/api/car/control` | 車輛控制 | `action`, `duration` |
| GET | `/api/car/status` | 獲取狀態 | - |
| POST | `/api/car/emergency_reset` | 重置緊急停止 | - |
| GET | `/api/car/test` | 測試序列 | - |

### 控制指令

| 指令 | 動作 | 鍵盤快捷鍵 |
|------|------|------------|
| `forward` | 前進 | W / ↑ |
| `backward` | 後退 | S / ↓ |
| `turn_left` | 左轉 | A / ← |
| `turn_right` | 右轉 | D / → |
| `stop` | 停止 | X / 空格 |
| `emergency_stop` | 緊急停止 | E / ESC |

### 請求範例

```json
{
  "action": "forward",
  "duration": 0.5
}
```

### 響應範例

```json
{
  "success": true,
  "message": "前進 0.5秒",
  "status": {
    "is_moving": false,
    "current_direction": "stop",
    "last_command_time": 1234567890.123,
    "emergency_stop": false,
    "simulation_mode": true
  }
}
```

---

## 📁 項目結構

```
poster/
├── 🚗 simple_car_server.py          # 簡化版API服務器
├── 🧪 test_simple_car.py            # Python測試腳本  
├── 🌐 test_car_control.html         # HTML測試頁面
├── 📋 QUICK_START.md                # 詳細啟動指南
│
├── robot_core/                      # 核心控制模組
│   ├── hardware/
│   │   └── car_run_turn.py          # 車輛控制邏輯
│   └── api/
│       └── server.py                # 完整版API服務器
│
└── web_demo/                        # React前端界面
    ├── src/
    ├── package.json
    └── ...
```

---

## 🛠️ 硬件需求

### 基本配置
- **樹莓派 4B** (2GB+)
- **SD卡** (16GB+, Class 10)
- **電機驅動板** (L298N推薦)
- **直流電機** x2
- **電源** (7-12V)

### GPIO接線
```
電機驅動引腳配置：
- 右電機正轉: GPIO 16
- 右電機反轉: GPIO 18  
- 左電機正轉: GPIO 11
- 左電機反轉: GPIO 13
```

💡 **注意**: 模擬模式下不需要硬件，可直接測試

---

## 🔍 故障排除

### 常見問題

#### 1. 服務器無法啟動
```bash
# 檢查端口占用
lsof -i :8000

# 終止占用進程
kill -9 <PID>
```

#### 2. 前端無法連接
```bash
# 檢查代理設置
cat web_demo/package.json | grep proxy

# 應該顯示: "proxy": "http://localhost:8000"
```

#### 3. 硬件模式錯誤
```bash
# 檢查GPIO權限
sudo usermod -a -G gpio $USER

# 重新登入後測試
```

### 測試連接
```bash
# 基本連接測試
curl http://localhost:8000/

# 預期回應: {"message":"🚗 簡化版樹莓派車輛控制API","status":"running","mode":"simulation"}
```

---

## 🚧 開發計劃

### ✅ 已完成
- [x] 核心車輛控制功能
- [x] Web前端控制界面  
- [x] REST API接口
- [x] 模擬/硬件雙模式
- [x] 緊急停止機制

### 🔄 待加入（團隊協作）
- [ ] AI視覺系統 (YOLO物體檢測)
- [ ] 感測器融合 (超聲波、IMU)
- [ ] 路徑規劃 (A*算法)
- [ ] 地圖建構 (SLAM)
- [ ] LiDAR支援 (Polycam)

### 🎯 擴展計劃
- [ ] 手機APP控制
- [ ] 語音控制
- [ ] 自動巡航
- [ ] 遠程監控

---

## 📞 支援

- **文檔**: [QUICK_START.md](QUICK_START.md)
- **API文檔**: http://localhost:8000/docs (服務器運行時)
- **測試頁面**: [test_car_control.html](test_car_control.html)

---

<div align="center">

**🚗 讓我們一起打造智能車輛控制系統！**

Made with ❤️ for Raspberry Pi

</div>
