#!/bin/bash
# 樹莓派全自動設置腳本
# 使用方法: chmod +x auto_setup_raspberry_pi.sh && ./auto_setup_raspberry_pi.sh

set -e  # 遇到錯誤就停止

# 顏色設置
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 輔助函數
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# 檢查是否為樹莓派
check_raspberry_pi() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        warn "這個腳本是為樹莓派設計的，但可以在其他 Linux 系統上運行"
        read -p "是否繼續? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
}

# 系統更新
update_system() {
    log "正在更新系統..."
    sudo apt update -qq
    sudo apt upgrade -y -qq
    log "系統更新完成"
}

# 安裝基礎套件
install_base_packages() {
    log "安裝基礎套件..."
    
    local packages=(
        "python3-pip"
        "python3-venv" 
        "python3-dev"
        "git"
        "cmake"
        "build-essential"
        "curl"
        "wget"
        "nano"
        "htop"
        "tree"
        "ufw"
        "fail2ban"
    )
    
    for package in "${packages[@]}"; do
        if ! dpkg -l | grep -q "^ii  $package "; then
            info "安裝 $package..."
            sudo apt install -y "$package" -qq
        else
            info "$package 已安裝"
        fi
    done
    
    log "基礎套件安裝完成"
}

# 安裝樹莓派專用套件
install_pi_packages() {
    log "安裝樹莓派專用套件..."
    
    if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        local pi_packages=(
            "python3-rpi.gpio"
            "python3-gpiozero"
            "i2c-tools"
            "python3-smbus"
        )
        
        for package in "${pi_packages[@]}"; do
            if ! dpkg -l | grep -q "^ii  $package "; then
                info "安裝 $package..."
                sudo apt install -y "$package" -qq
            else
                info "$package 已安裝"
            fi
        done
    fi
    
    log "樹莓派套件安裝完成"
}

# 設置 Python 虛擬環境
setup_python_env() {
    log "設置 Python 虛擬環境..."
    
    local project_dir="/home/$USER/robot_project"
    
    # 創建專案目錄
    if [ ! -d "$project_dir" ]; then
        mkdir -p "$project_dir"
        log "創建專案目錄: $project_dir"
    fi
    
    cd "$project_dir"
    
    # 創建虛擬環境
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log "創建 Python 虛擬環境"
    fi
    
    # 激活虛擬環境並安裝套件
    source venv/bin/activate
    pip install --upgrade pip -q
    
    # 安裝核心依賴
    local pip_packages=(
        "fastapi"
        "uvicorn[standard]"
        "websockets"
        "aiofiles"
        "pydantic"
        "requests"
        "psutil"
    )
    
    for package in "${pip_packages[@]}"; do
        info "安裝 Python 套件: $package"
        pip install "$package" -q
    done
    
    # 樹莓派 GPIO 套件
    if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        pip install RPi.GPIO gpiozero -q
        log "安裝樹莓派 GPIO 套件"
    fi
    
    log "Python 環境設置完成"
}

# 啟用系統接口
enable_interfaces() {
    if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        log "啟用樹莓派接口..."
        
        # 檢查並啟用 I2C
        if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt; then
            echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt > /dev/null
            info "啟用 I2C 接口"
        fi
        
        # 檢查並啟用 SPI
        if ! grep -q "^dtparam=spi=on" /boot/config.txt; then
            echo "dtparam=spi=on" | sudo tee -a /boot/config.txt > /dev/null
            info "啟用 SPI 接口"
        fi
        
        # GPIO
        if ! grep -q "^dtparam=gpio=on" /boot/config.txt; then
            echo "dtparam=gpio=on" | sudo tee -a /boot/config.txt > /dev/null
            info "啟用 GPIO"
        fi
        
        log "接口設置完成"
    fi
}

# 設置防火牆
setup_firewall() {
    log "設置防火牆..."
    
    # 設置 UFW 規則
    sudo ufw --force reset > /dev/null
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # 允許 SSH
    sudo ufw allow ssh
    info "允許 SSH (端口 22)"
    
    # 允許 API 端口
    sudo ufw allow 8000/tcp
    info "允許 API 端口 8000"
    
    # 允許前端端口 (開發用)
    sudo ufw allow 3000/tcp
    info "允許前端端口 3000"
    
    # 啟用防火牆
    sudo ufw --force enable > /dev/null
    
    log "防火牆設置完成"
}

# 設置開機服務
setup_service() {
    log "設置開機服務..."
    
    local service_file="/etc/systemd/system/robot-control.service"
    local project_dir="/home/$USER/robot_project"
    
    # 創建服務文件
    sudo tee "$service_file" > /dev/null << EOF
[Unit]
Description=Robot Control Server
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$project_dir
Environment=PATH=$project_dir/venv/bin
ExecStart=$project_dir/venv/bin/python start_pi_server.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    
    # 重新加載 systemd
    sudo systemctl daemon-reload
    
    info "服務文件已創建"
    log "開機服務設置完成"
}

# 網絡配置
setup_network() {
    log "檢查網絡配置..."
    
    # 獲取當前 IP
    local current_ip=$(hostname -I | awk '{print $1}')
    info "當前 IP 地址: $current_ip"
    
    # 詢問是否設置固定 IP
    echo
    read -p "是否要設置固定 IP 地址? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "請輸入固定 IP 地址 (例如: 192.168.1.100): " fixed_ip
        read -p "請輸入路由器 IP (例如: 192.168.1.1): " router_ip
        
        if [[ $fixed_ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
            # 備份原配置
            sudo cp /etc/dhcpcd.conf /etc/dhcpcd.conf.backup
            
            # 添加固定 IP 配置
            sudo tee -a /etc/dhcpcd.conf > /dev/null << EOF

# Robot Project Static IP Configuration
interface eth0
static ip_address=$fixed_ip/24
static routers=$router_ip
static domain_name_servers=8.8.8.8 8.8.4.4
EOF
            
            info "固定 IP 配置已添加: $fixed_ip"
            warn "重啟後生效"
        else
            warn "IP 地址格式無效，跳過設置"
        fi
    fi
    
    log "網絡配置完成"
}

# 創建測試文件
create_test_files() {
    log "創建測試文件..."
    
    local project_dir="/home/$USER/robot_project"
    cd "$project_dir"
    
    # 創建系統檢查腳本
    tee "system_check.py" > /dev/null << 'EOF'
#!/usr/bin/env python3
"""系統健康檢查"""

import subprocess
import sys
import os
import time

def check_system():
    print("🍓 樹莓派系統檢查")
    print("="*40)
    
    # CPU 溫度
    try:
        temp = subprocess.check_output("vcgencmd measure_temp", shell=True).decode()
        print(f"🌡️  CPU溫度: {temp.strip()}")
    except:
        print("❌ 無法讀取CPU溫度")
    
    # 記憶體使用
    try:
        import psutil
        mem = psutil.virtual_memory()
        print(f"💾 記憶體使用: {mem.percent:.1f}%")
    except ImportError:
        print("⚠️  psutil 未安裝")
    
    # 磁碟空間
    try:
        disk = subprocess.check_output("df -h /", shell=True).decode()
        print(f"💽 磁碟使用:")
        print("   " + disk.split('\n')[1])
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
EOF
    
    chmod +x system_check.py
    
    # 創建快速啟動腳本
    tee "start_robot.sh" > /dev/null << 'EOF'
#!/bin/bash
# 機器人控制系統快速啟動腳本

echo "🤖 啟動機器人控制系統..."

# 進入專案目錄
cd "$(dirname "$0")"

# 激活虛擬環境
source venv/bin/activate

# 啟動服務器
python3 start_pi_server.py
EOF
    
    chmod +x start_robot.sh
    
    info "測試文件創建完成"
    log "所有設置腳本已準備好"
}

# 顯示完成信息
show_completion_info() {
    log "設置完成！"
    echo
    echo "📋 設置摘要:"
    echo "============"
    echo "專案目錄: /home/$USER/robot_project"
    echo "Python 環境: /home/$USER/robot_project/venv"
    echo "系統服務: robot-control.service"
    echo
    echo "🚀 接下來的步驟:"
    echo "================"
    echo "1. 上傳您的專案代碼到: /home/$USER/robot_project"
    echo "2. 測試系統: cd /home/$USER/robot_project && python3 system_check.py"
    echo "3. 啟動服務: ./start_robot.sh"
    echo "4. 啟用開機啟動: sudo systemctl enable robot-control"
    echo
    echo "📱 訪問地址:"
    echo "==========="
    local current_ip=$(hostname -I | awk '{print $1}')
    echo "API 文檔: http://$current_ip:8000/docs"
    echo "API 狀態: http://$current_ip:8000/api/status"
    echo
    echo "🔧 實用命令:"
    echo "==========="
    echo "系統檢查: python3 system_check.py"
    echo "查看日誌: sudo journalctl -u robot-control -f"
    echo "重啟服務: sudo systemctl restart robot-control"
    echo
    
    if grep -q "static ip_address=" /etc/dhcpcd.conf; then
        warn "固定 IP 已設置，請重啟系統使其生效: sudo reboot"
    fi
}

# 主程序
main() {
    echo "🍓 樹莓派機器人控制系統自動設置"
    echo "=================================="
    echo
    
    # 檢查執行環境
    check_raspberry_pi
    
    # 執行設置步驟
    update_system
    install_base_packages
    install_pi_packages
    setup_python_env
    enable_interfaces
    setup_firewall
    setup_service
    setup_network
    create_test_files
    
    # 顯示完成信息
    show_completion_info
    
    echo
    log "🎉 自動設置完成！"
}

# 執行主程序
main "$@"
