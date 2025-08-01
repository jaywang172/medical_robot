# 🎯 Polycam + 機器人系統整合指南

## 📱 使用Polycam進行環境掃描

### 步驟1：下載安裝Polycam
- 在App Store搜索並下載 **Polycam**
- 確保你的設備支援LiDAR（iPad Pro 2020及以後版本）

### 步驟2：環境掃描
1. **開啟Polycam應用**
2. **選擇LiDAR模式**（推薦用於室內環境）
3. **開始掃描**：
   - 慢慢移動設備，覆蓋整個環境
   - 保持穩定的移動速度
   - 確保充足的光線
   - 多角度掃描複雜區域

### 步驟3：導出地圖數據

#### 🎯 推薦格式
| 格式 | 適用場景 | 檔案大小 | 處理速度 |
|------|----------|----------|----------|
| `.ply` | 高質量點雲，包含顏色 | 大 | 快 |
| `.obj` | 詳細網格幾何 | 中 | 中 |
| `.xyz` | 簡單點雲 | 小 | 最快 |

#### 📂 支援的所有格式
- **網格格式**：`.obj`, `.glb`, `.usdz`, `.dae`, `.stl`
- **點雲格式**：`.ply`, `.las`, `.xyz`, `.pts`
- **平面圖格式**：`.dxf`, `.dae`

## 🤖 上傳到機器人系統

### 方法1：Web界面上傳
1. 打開機器人控制界面：`http://機器人IP:8000`
2. 進入「地圖管理」頁面
3. 點擊「上傳地圖」
4. 選擇Polycam導出的文件
5. 輸入地圖名稱
6. 點擊上傳

### 方法2：API直接上傳
```bash
curl -X POST "http://機器人IP:8000/api/maps/upload" \
  -F "file=@你的地圖文件.ply" \
  -F "name=客廳地圖" \
  -F "source=polycam"
```

### 方法3：自動處理（高級）
```python
import requests

# 上傳Polycam文件
with open('room_scan.ply', 'rb') as f:
    files = {'file': f}
    data = {'name': '房間掃描', 'source': 'polycam'}
    response = requests.post(
        'http://192.168.1.100:8000/api/maps/upload',
        files=files, 
        data=data
    )
    
result = response.json()
if result['success']:
    print(f"地圖上傳成功！ID: {result['map_id']}")
```

## ⚙️ 系統配置

### 安裝必要依賴
```bash
pip install trimesh open3d ezdxf laspy opencv-python
```

### 檢查依賴狀態
```bash
curl http://機器人IP:8000/api/polycam/dependencies
```

### 獲取使用指南
```bash
curl http://機器人IP:8000/api/polycam/guide
```

## 🎯 最佳實踐

### 掃描技巧
- **充足光線**：確保環境有足夠照明
- **穩定移動**：避免快速或抖動的動作
- **完整覆蓋**：確保所有區域都被掃描到
- **多角度**：從不同高度和角度掃描

### 質量優化
- **解析度設置**：建議5cm解析度平衡質量和性能
- **文件大小**：PLY格式提供最好的質量，XYZ格式最小
- **處理時間**：點雲格式處理最快，網格格式更詳細

### 環境準備
- **移除反光物體**：鏡子、玻璃可能影響掃描
- **固定位置**：確保掃描期間物體不移動
- **標記重要區域**：在機器人需要精確導航的區域多掃描

## 🔧 故障排除

### 常見問題

#### 1. 上傳失敗
```
錯誤: "不支持的文件格式"
解決: 確保文件格式在支援列表中
```

#### 2. 處理失敗
```
錯誤: "需要安裝3D處理庫"
解決: pip install trimesh open3d
```

#### 3. 地圖質量差
```
問題: 地圖有很多洞或不準確
解決: 重新掃描，確保完整覆蓋和穩定移動
```

### 依賴問題解決
```bash
# 安裝所有依賴
pip install trimesh open3d ezdxf laspy opencv-python

# 如果有編譯問題，使用預編譯版本
pip install --only-binary=all trimesh open3d

# macOS用戶可能需要
brew install pkg-config
```

## 📊 性能指標

### 文件大小參考
| 房間大小 | PLY文件 | OBJ文件 | XYZ文件 |
|----------|---------|---------|---------|
| 小房間(3x3m) | 5-15MB | 10-30MB | 1-3MB |
| 中房間(5x5m) | 15-50MB | 30-100MB | 3-10MB |
| 大房間(10x10m) | 50-200MB | 100-500MB | 10-50MB |

### 處理時間參考
| 文件類型 | 小文件(<10MB) | 中文件(10-50MB) | 大文件(>50MB) |
|----------|---------------|-----------------|---------------|
| XYZ | 1-5秒 | 5-15秒 | 15-30秒 |
| PLY | 2-10秒 | 10-30秒 | 30-60秒 |
| OBJ | 5-20秒 | 20-60秒 | 1-3分鐘 |

## 🚀 高級功能

### 自動監控文件夾
```python
import watchdog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class PolycamHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(('.ply', '.obj', '.xyz')):
            # 自動上傳到機器人
            upload_to_robot(event.src_path)

# 監控下載文件夾
observer = Observer()
observer.schedule(PolycamHandler(), path='/Users/用戶名/Downloads')
observer.start()
```

### 批量處理
```python
import glob
import asyncio

async def batch_upload_maps():
    files = glob.glob('*.ply')
    for file in files:
        print(f"上傳 {file}...")
        # 上傳邏輯
        await upload_map(file)

asyncio.run(batch_upload_maps())
```

## 🎉 完整工作流程

1. **📱 Polycam掃描** → 2-10分鐘
2. **💾 導出文件** → 1-5分鐘  
3. **📤 上傳到機器人** → 10-60秒
4. **⚡ 自動處理** → 10-120秒
5. **🗺️ 激活地圖** → 即時
6. **🤖 開始導航** → 即時

整個流程從掃描到機器人可用，通常在15分鐘內完成！

---

💡 **提示**：建議先掃描一個小區域測試整個流程，確認一切正常後再掃描整個環境。 