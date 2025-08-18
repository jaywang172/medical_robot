#!/bin/bash
# 樹莓派環境設置腳本

echo "🍓 樹莓派機器人控制系統設置"
echo "=================================="

# 檢查 Python 版本
echo "📋 檢查 Python 環境..."
python3 --version

# 安裝系統依賴
echo "📦 安裝系統依賴..."
sudo apt update
sudo apt install -y python3-pip python3-venv git

# 啟用 I2C 和 GPIO (如果需要)
echo "🔧 檢查硬件接口..."
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
    echo "啟用 I2C 接口..."
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
fi

# 創建虛擬環境
echo "🌿 創建 Python 虛擬環境..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# 激活虛擬環境
echo "✨ 激活虛擬環境..."
source venv/bin/activate

# 安裝 Python 依賴
echo "📦 安裝 Python 依賴..."
pip install --upgrade pip

# 基礎依賴
pip install fastapi uvicorn websockets aiofiles pydantic

# 樹莓派 GPIO 支持
pip install RPi.GPIO gpiozero

# 可選依賴 (如果需要完整功能)
echo "📦 安裝可選依賴 (可能會很慢)..."
pip install opencv-python-headless numpy pillow || echo "⚠️  某些依賴安裝失敗，但核心功能仍可用"

# 設置服務器自動啟動 (可選)
echo "🔧 設置服務..."
cat > robot_control.service << EOF
[Unit]
Description=Robot Control Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python start_pi_server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

echo "📋 服務配置文件已創建: robot_control.service"
echo "要安裝服務，請執行:"
echo "  sudo cp robot_control.service /etc/systemd/system/"
echo "  sudo systemctl enable robot_control"
echo "  sudo systemctl start robot_control"

# 顯示網絡信息
echo ""
echo "🌐 網絡配置信息:"
echo "主機名: $(hostname)"
echo "IP地址: $(hostname -I | awk '{print $1}')"

# 測試服務器
echo ""
echo "🧪 測試服務器啟動..."
python3 start_pi_server.py &
SERVER_PID=$!
sleep 3

if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✅ 服務器啟動成功!"
    kill $SERVER_PID
else
    echo "❌ 服務器啟動失敗"
fi

echo ""
echo "🎉 設置完成!"
echo ""
echo "📝 使用方法:"
echo "1. 手動啟動服務器:"
echo "   python3 start_pi_server.py"
echo ""
echo "2. 在瀏覽器中訪問:"
echo "   http://$(hostname -I | awk '{print $1}'):8000"
echo ""
echo "3. 前端連接配置:"
echo "   將前端的 API_BASE_URL 設置為: http://$(hostname -I | awk '{print $1}'):8000"
