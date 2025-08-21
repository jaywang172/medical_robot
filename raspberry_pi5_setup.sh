#!/bin/bash
# 樹莓派5專用環境設置腳本
# 解決GPIO和攝像頭兼容性問題

echo "🍓 樹莓派5機器人控制系統設置"
echo "===================================="

# 檢查是否為樹莓派5
echo "📋 檢查系統信息..."
if command -v raspi-config >/dev/null 2>&1; then
    echo "✅ 檢測到樹莓派系統"
    # 檢查樹莓派版本
    if grep -q "Raspberry Pi 5" /proc/cpuinfo; then
        echo "🎯 確認為樹莓派5 - 使用專用配置"
        PI5_DETECTED=true
    else
        echo "📱 檢測到其他樹莓派版本"
        PI5_DETECTED=false
    fi
else
    echo "⚠️  非樹莓派系統，使用通用配置"
    PI5_DETECTED=false
fi

# 更新系統
echo "📦 更新系統套件..."
sudo apt update
sudo apt upgrade -y

# 安裝基礎依賴
echo "🔧 安裝基礎依賴..."
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    cmake \
    build-essential \
    libffi-dev \
    libssl-dev

# 樹莓派5專用GPIO庫安裝
if [ "$PI5_DETECTED" = true ]; then
    echo "🎯 安裝樹莓派5專用GPIO庫..."
    
    # 安裝 lgpio (樹莓派5推薦)
    echo "📌 安裝 lgpio..."
    sudo apt install -y python3-lgpio || {
        echo "⚠️  系統套件安裝失敗，嘗試從源碼安裝..."
        cd /tmp
        wget https://github.com/joan2937/lg/archive/master.zip
        unzip master.zip
        cd lg-master
        make
        sudo make install
        cd ..
        rm -rf lg-master master.zip
    }
    
    # 安裝 rpi-lgpio (Python綁定)
    echo "📌 安裝 rpi-lgpio..."
    sudo apt install -y python3-rpi-lgpio || pip3 install rpi-lgpio
    
    echo "✅ 樹莓派5 GPIO庫安裝完成"
else
    echo "📱 安裝通用GPIO庫..."
    sudo apt install -y python3-rpi.gpio python3-gpiozero
fi

# 安裝通用GPIO庫作為備用
echo "📌 安裝通用GPIO庫..."
sudo apt install -y python3-gpiozero

# 安裝攝像頭支持
echo "📹 安裝攝像頭支持..."
sudo apt install -y \
    python3-picamera2 \
    python3-opencv \
    python3-pil

# 檢查攝像頭接口
echo "🔍 檢查攝像頭配置..."
if ! grep -q "^camera_auto_detect=1" /boot/firmware/config.txt && ! grep -q "^camera_auto_detect=1" /boot/config.txt; then
    echo "啟用攝像頭自動檢測..."
    if [ -f /boot/firmware/config.txt ]; then
        echo "camera_auto_detect=1" | sudo tee -a /boot/firmware/config.txt
    else
        echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
    fi
fi

# 創建專案目錄
echo "📁 設置專案環境..."
PROJECT_DIR="/home/$USER/robot_project"
mkdir -p "$PROJECT_DIR"
cd "$PROJECT_DIR"

# 創建虛擬環境
echo "🌿 創建Python虛擬環境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 激活虛擬環境並安裝依賴
echo "📦 安裝Python依賴..."
source venv/bin/activate

# 升級pip
pip install --upgrade pip

# 安裝核心依賴
echo "📌 安裝Web框架..."
pip install fastapi uvicorn websockets aiofiles pydantic

# 安裝GPIO庫
echo "📌 安裝GPIO控制庫..."
if [ "$PI5_DETECTED" = true ]; then
    # 樹莓派5優先安裝順序
    pip install rpi-lgpio || echo "⚠️  rpi-lgpio 安裝失敗"
    pip install gpiozero || echo "⚠️  gpiozero 安裝失敗"
    pip install RPi.GPIO || echo "⚠️  RPi.GPIO 安裝失敗"
else
    # 其他樹莓派版本
    pip install RPi.GPIO gpiozero
fi

# 安裝攝像頭庫
echo "📌 安裝攝像頭庫..."
pip install opencv-python-headless pillow numpy

# 安裝其他有用庫
echo "📌 安裝工具庫..."
pip install requests psutil loguru

# 創建測試腳本
echo "🧪 創建測試腳本..."
cat > test_gpio.py << 'EOF'
#!/usr/bin/env python3
"""
樹莓派GPIO測試腳本
測試不同GPIO庫的兼容性
"""
import time

def test_lgpio():
    """測試 lgpio"""
    try:
        import lgpio
        print("✅ lgpio 可用")
        
        # 測試GPIO操作
        handle = lgpio.gpiochip_open(0)
        lgpio.gpiochip_close(handle)
        print("✅ lgpio GPIO操作正常")
        return True
    except ImportError:
        print("❌ lgpio 不可用")
        return False
    except Exception as e:
        print(f"❌ lgpio 錯誤: {e}")
        return False

def test_gpiozero():
    """測試 gpiozero"""
    try:
        from gpiozero import OutputDevice
        print("✅ gpiozero 可用")
        return True
    except ImportError:
        print("❌ gpiozero 不可用")
        return False
    except Exception as e:
        print(f"❌ gpiozero 錯誤: {e}")
        return False

def test_rpi_gpio():
    """測試 RPi.GPIO"""
    try:
        import RPi.GPIO as GPIO
        print("✅ RPi.GPIO 可用")
        return True
    except ImportError:
        print("❌ RPi.GPIO 不可用")
        return False
    except Exception as e:
        print(f"❌ RPi.GPIO 錯誤: {e}")
        return False

def test_camera():
    """測試攝像頭"""
    try:
        from picamera2 import Picamera2
        print("✅ picamera2 可用")
        return True
    except ImportError:
        try:
            import cv2
            print("✅ OpenCV 可用")
            return True
        except ImportError:
            print("❌ 攝像頭庫不可用")
            return False
    except Exception as e:
        print(f"❌ 攝像頭錯誤: {e}")
        return False

if __name__ == "__main__":
    print("🧪 GPIO和攝像頭兼容性測試")
    print("=" * 40)
    
    # 測試GPIO庫
    print("\n📌 GPIO庫測試:")
    lgpio_ok = test_lgpio()
    gpiozero_ok = test_gpiozero()
    rpi_gpio_ok = test_rpi_gpio()
    
    # 測試攝像頭
    print("\n📌 攝像頭測試:")
    camera_ok = test_camera()
    
    # 總結
    print("\n📊 測試結果:")
    if lgpio_ok:
        print("🎯 推薦使用: lgpio (樹莓派5最佳)")
    elif gpiozero_ok:
        print("🎯 推薦使用: gpiozero (通用兼容)")
    elif rpi_gpio_ok:
        print("🎯 推薦使用: RPi.GPIO (傳統)")
    else:
        print("❌ 沒有可用的GPIO庫")
    
    if camera_ok:
        print("✅ 攝像頭支持正常")
    else:
        print("❌ 攝像頭支持有問題")
EOF

chmod +x test_gpio.py

# 創建系統服務配置
echo "⚙️  創建系統服務配置..."
cat > robot_control.service << EOF
[Unit]
Description=Robot Control Server for Raspberry Pi
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_DIR
Environment=PATH=$PROJECT_DIR/venv/bin
ExecStart=$PROJECT_DIR/venv/bin/python simple_car_server.py --hardware
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 顯示網絡信息
echo ""
echo "🌐 網絡配置信息:"
echo "主機名: $(hostname)"
echo "IP地址: $(hostname -I | awk '{print $1}')"

# 完成信息
echo ""
echo "🎉 樹莓派5設置完成！"
echo "=" * 40
echo "📁 專案目錄: $PROJECT_DIR"
echo "🐍 虛擬環境: $PROJECT_DIR/venv"
echo "🧪 測試腳本: $PROJECT_DIR/test_gpio.py"
echo ""
echo "🔧 下一步操作:"
echo "1. 將專案文件複製到 $PROJECT_DIR"
echo "2. 激活虛擬環境: source $PROJECT_DIR/venv/bin/activate"
echo "3. 運行測試: python test_gpio.py"
echo "4. 啟動服務器: python simple_car_server.py --hardware"
echo ""
echo "⚠️  重要提醒:"
echo "- 某些GPIO操作可能需要重新啟動才能生效"
echo "- 如果遇到權限問題，請將用戶加入gpio組: sudo usermod -a -G gpio $USER"
echo "- 樹莓派5可能需要最新的內核和固件"

# 可選：設置服務自動啟動
echo ""
read -p "是否要設置機器人服務開機自啟動？(y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sudo cp robot_control.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable robot_control
    echo "✅ 服務已設置為開機自啟動"
    echo "   啟動服務: sudo systemctl start robot_control"
    echo "   查看狀態: sudo systemctl status robot_control"
    echo "   停止服務: sudo systemctl stop robot_control"
fi

echo ""
echo "🎯 設置完成！請重新啟動樹莓派以確保所有更改生效。"
