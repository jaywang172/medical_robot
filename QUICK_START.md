# 🚗 樹莓派車輛控制系統 - 快速開始

## 📋 核心功能

這個版本專注於**核心車輛控制**功能，支援前端控制車輛運動。

### ✅ 已實現功能
- 🎮 前後左右車輛控制
- 🚨 緊急停止功能
- 🌐 Web前端控制界面
- 📡 REST API控制
- 💻 模擬/硬件雙模式

## 🚀 快速啟動

### 1. 環境需求
```bash
# Python 3.8+
# 已安裝的套件：fastapi, uvicorn, requests
pip install fastapi uvicorn requests pydantic
```

### 2. 啟動後端服務器

#### 模擬模式（推薦測試）
```bash
python simple_car_server.py
```

#### 硬件模式（樹莓派上）
```bash
python simple_car_server.py --hardware
```

### 3. 測試方法

#### 方法1: Python測試腳本
```bash
python test_simple_car.py
```

#### 方法2: Web控制界面
```bash
# 啟動前端（新終端）
cd web_demo
npm install
npm start

# 瀏覽器訪問: http://localhost:3000
```

#### 方法3: HTML測試頁面
```bash
# 直接打開
open test_car_control.html
```

#### 方法4: API直接調用
```bash
# 前進0.5秒
curl -X POST "http://localhost:8000/api/car/control" \
  -H "Content-Type: application/json" \
  -d '{"action": "forward", "duration": 0.5}'

# 獲取狀態
curl "http://localhost:8000/api/car/status"
```

## 🎮 控制指令

| 動作 | API指令 | 鍵盤快捷鍵 | 說明 |
|------|---------|------------|------|
| 前進 | `forward` | W / ↑ | 車輛向前移動 |
| 後退 | `backward` | S / ↓ | 車輛向後移動 |
| 左轉 | `turn_left` | A / ← | 車輛左轉 |
| 右轉 | `turn_right` | D / → | 車輛右轉 |
| 停止 | `stop` | X / 空格 | 立即停止 |
| 緊急停止 | `emergency_stop` | E / ESC | 緊急停止 |

## 📡 API端點

| 方法 | 端點 | 功能 |
|------|------|------|
| GET | `/` | 服務器狀態 |
| POST | `/api/car/control` | 車輛控制 |
| GET | `/api/car/status` | 獲取車輛狀態 |
| POST | `/api/car/emergency_reset` | 重置緊急停止 |
| GET | `/api/car/test` | 執行測試序列 |

## 🔧 故障排除

### 連接問題
```bash
# 檢查服務器是否運行
curl http://localhost:8000/

# 檢查端口占用
lsof -i :8000
```

### 樹莓派硬件模式
```bash
# 確保GPIO權限
sudo usermod -a -G gpio $USER

# 重新登入後測試
python simple_car_server.py --hardware
```

## 📁 核心檔案結構

```
poster/
├── simple_car_server.py          # 簡化版API服務器
├── test_simple_car.py            # Python測試腳本
├── test_car_control.html         # HTML測試頁面
├── robot_core/
│   └── state_machine/
│       └── car_run_turn.py       # 核心車輛控制邏輯
└── web_demo/                     # React前端控制界面
```

## 🎯 下一步

1. ✅ 測試前端控制功能
2. ✅ 確認車輛運動正常
3. ✅ 上傳到GitHub
4. 🔄 等待團隊成員加入AI功能

## 🐛 已知問題

- ~~web_demo/package.json 的 proxy 配置錯誤~~ ✅ 已修復
- 需要根據實際硬件調整GPIO腳位配置

## 📞 支援

如有問題，請檢查：
1. 服務器日誌輸出
2. 瀏覽器開發者工具
3. 網路連接狀態
