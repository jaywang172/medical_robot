#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
樹莓派5攝像頭修復腳本
解決picamera2在樹莓派5上的兼容性問題
"""

import time
import sys
import subprocess
import logging

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_camera_interface():
    """檢查攝像頭接口是否啟用"""
    logger.info("🔍 檢查攝像頭接口配置...")
    
    config_files = ['/boot/firmware/config.txt', '/boot/config.txt']
    camera_enabled = False
    
    for config_file in config_files:
        try:
            with open(config_file, 'r') as f:
                content = f.read()
                if 'camera_auto_detect=1' in content:
                    camera_enabled = True
                    logger.info(f"✅ 攝像頭自動檢測已啟用 ({config_file})")
                    break
        except FileNotFoundError:
            continue
        except PermissionError:
            logger.warning(f"⚠️  無權限讀取 {config_file}")
    
    if not camera_enabled:
        logger.warning("⚠️  攝像頭接口可能未啟用")
        print("請執行以下命令啟用攝像頭：")
        print("sudo raspi-config")
        print("-> Interfacing Options -> Camera -> Yes")
        print("或者手動編輯 /boot/firmware/config.txt 添加:")
        print("camera_auto_detect=1")
    
    return camera_enabled

def check_camera_detection():
    """檢查系統是否檢測到攝像頭"""
    logger.info("🔍 檢查攝像頭硬件檢測...")
    
    try:
        # 檢查 libcamera 檢測
        result = subprocess.run(['libcamera-hello', '--list-cameras'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and 'Available cameras' in result.stdout:
            logger.info("✅ libcamera 檢測到攝像頭")
            print(result.stdout)
            return True
        else:
            logger.warning("⚠️  libcamera 未檢測到攝像頭")
            if result.stderr:
                print(f"錯誤信息: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("❌ libcamera-hello 超時")
        return False
    except FileNotFoundError:
        logger.error("❌ libcamera-hello 未找到，請安裝 libcamera-apps")
        print("安裝命令: sudo apt install libcamera-apps")
        return False
    except Exception as e:
        logger.error(f"❌ 檢查攝像頭時出錯: {e}")
        return False

def test_picamera2():
    """測試 picamera2 庫"""
    logger.info("🧪 測試 picamera2 庫...")
    
    try:
        from picamera2 import Picamera2
        logger.info("✅ picamera2 庫導入成功")
        
        # 嘗試初始化攝像頭
        try:
            logger.info("🔧 嘗試初始化攝像頭...")
            picam2 = Picamera2()
            
            # 獲取攝像頭信息
            camera_properties = picam2.camera_properties
            logger.info(f"📹 攝像頭屬性: {camera_properties}")
            
            # 創建配置
            config = picam2.create_still_configuration(
                main={"size": (640, 480), "format": "RGB888"}
            )
            picam2.configure(config)
            
            logger.info("🚀 啟動攝像頭...")
            picam2.start()
            
            # 等待攝像頭穩定
            time.sleep(2)
            
            # 測試捕獲
            logger.info("📸 測試圖像捕獲...")
            image = picam2.capture_array()
            logger.info(f"✅ 成功捕獲圖像，大小: {image.shape}")
            
            # 停止攝像頭
            picam2.stop()
            picam2.close()
            
            return True, "picamera2 測試成功"
            
        except Exception as e:
            logger.error(f"❌ picamera2 初始化失敗: {e}")
            return False, f"picamera2 初始化錯誤: {e}"
            
    except ImportError as e:
        logger.error(f"❌ picamera2 庫導入失敗: {e}")
        return False, f"picamera2 導入錯誤: {e}"

def test_opencv_camera():
    """測試 OpenCV 攝像頭"""
    logger.info("🧪 測試 OpenCV 攝像頭...")
    
    try:
        import cv2
        logger.info("✅ OpenCV 庫導入成功")
        
        # 測試不同的攝像頭索引
        for index in range(3):
            try:
                logger.info(f"🔧 嘗試攝像頭索引 {index}...")
                cap = cv2.VideoCapture(index)
                
                if cap.isOpened():
                    # 設置攝像頭參數
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    cap.set(cv2.CAP_PROP_FPS, 10)
                    
                    # 測試捕獲
                    ret, frame = cap.read()
                    if ret and frame is not None:
                        logger.info(f"✅ OpenCV 攝像頭 {index} 測試成功，畫面大小: {frame.shape}")
                        cap.release()
                        return True, f"OpenCV 攝像頭 {index} 可用"
                    else:
                        logger.warning(f"⚠️  攝像頭 {index} 無法捕獲畫面")
                
                cap.release()
                
            except Exception as e:
                logger.error(f"❌ OpenCV 攝像頭 {index} 錯誤: {e}")
        
        return False, "所有 OpenCV 攝像頭都無法使用"
        
    except ImportError as e:
        logger.error(f"❌ OpenCV 庫導入失敗: {e}")
        return False, f"OpenCV 導入錯誤: {e}"

def install_missing_packages():
    """安裝缺失的攝像頭套件"""
    logger.info("📦 檢查並安裝缺失的套件...")
    
    packages_to_install = []
    
    # 檢查 picamera2
    try:
        import picamera2
        logger.info("✅ picamera2 已安裝")
    except ImportError:
        packages_to_install.append("python3-picamera2")
    
    # 檢查 OpenCV
    try:
        import cv2
        logger.info("✅ OpenCV 已安裝")
    except ImportError:
        packages_to_install.append("python3-opencv")
    
    # 檢查 libcamera
    try:
        result = subprocess.run(['libcamera-hello', '--version'], 
                              capture_output=True, timeout=5)
        if result.returncode == 0:
            logger.info("✅ libcamera-apps 已安裝")
        else:
            packages_to_install.append("libcamera-apps")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        packages_to_install.append("libcamera-apps")
    
    if packages_to_install:
        logger.info(f"📦 需要安裝: {', '.join(packages_to_install)}")
        print("請執行以下命令安裝缺失的套件：")
        print(f"sudo apt update")
        print(f"sudo apt install -y {' '.join(packages_to_install)}")
        return False
    else:
        logger.info("✅ 所有必需套件都已安裝")
        return True

def fix_permissions():
    """修復攝像頭權限問題"""
    logger.info("🔧 檢查攝像頭權限...")
    
    import os
    import pwd
    
    current_user = pwd.getpwuid(os.getuid()).pw_name
    
    # 檢查用戶是否在 video 組中
    try:
        result = subprocess.run(['groups', current_user], 
                              capture_output=True, text=True)
        if 'video' in result.stdout:
            logger.info("✅ 用戶已在 video 組中")
        else:
            logger.warning("⚠️  用戶不在 video 組中")
            print(f"請執行以下命令將用戶加入 video 組：")
            print(f"sudo usermod -a -G video {current_user}")
            print("然後重新登錄或重啟")
            return False
    except Exception as e:
        logger.error(f"❌ 檢查用戶組時出錯: {e}")
        return False
    
    return True

def create_test_script():
    """創建攝像頭測試腳本"""
    logger.info("📝 創建攝像頭測試腳本...")
    
    test_script = '''#!/usr/bin/env python3
"""
攝像頭功能測試腳本
"""
import time
import base64
import io

def test_picamera2_capture():
    """測試 picamera2 圖像捕獲"""
    try:
        from picamera2 import Picamera2
        import numpy as np
        
        print("🧪 測試 picamera2...")
        picam2 = Picamera2()
        
        config = picam2.create_still_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        picam2.configure(config)
        picam2.start()
        
        time.sleep(2)  # 等待攝像頭穩定
        
        # 捕獲多張圖像
        for i in range(5):
            image = picam2.capture_array()
            print(f"📸 圖像 {i+1}: {image.shape}, 平均亮度: {np.mean(image):.2f}")
            time.sleep(0.5)
        
        picam2.stop()
        print("✅ picamera2 測試完成")
        return True
        
    except Exception as e:
        print(f"❌ picamera2 測試失敗: {e}")
        return False

def test_opencv_capture():
    """測試 OpenCV 圖像捕獲"""
    try:
        import cv2
        import numpy as np
        
        print("🧪 測試 OpenCV...")
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("❌ 無法打開攝像頭")
            return False
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # 捕獲多張圖像
        for i in range(5):
            ret, frame = cap.read()
            if ret:
                print(f"📸 圖像 {i+1}: {frame.shape}, 平均亮度: {np.mean(frame):.2f}")
            else:
                print(f"❌ 圖像 {i+1} 捕獲失敗")
            time.sleep(0.5)
        
        cap.release()
        print("✅ OpenCV 測試完成")
        return True
        
    except Exception as e:
        print(f"❌ OpenCV 測試失敗: {e}")
        return False

if __name__ == "__main__":
    print("🎥 攝像頭功能測試")
    print("=" * 40)
    
    picamera2_ok = test_picamera2_capture()
    opencv_ok = test_opencv_capture()
    
    print("\\n📊 測試結果:")
    if picamera2_ok:
        print("✅ picamera2 功能正常")
    else:
        print("❌ picamera2 功能異常")
    
    if opencv_ok:
        print("✅ OpenCV 功能正常")
    else:
        print("❌ OpenCV 功能異常")
'''
    
    with open('test_camera_functionality.py', 'w') as f:
        f.write(test_script)
    
    import os
    os.chmod('test_camera_functionality.py', 0o755)
    
    logger.info("✅ 測試腳本已創建: test_camera_functionality.py")

def main():
    """主函數"""
    print("🎥 樹莓派5攝像頭診斷和修復工具")
    print("=" * 50)
    
    # 1. 檢查攝像頭接口
    interface_ok = check_camera_interface()
    
    # 2. 檢查套件安裝
    packages_ok = install_missing_packages()
    
    # 3. 檢查權限
    permissions_ok = fix_permissions()
    
    # 4. 檢查硬件檢測
    detection_ok = check_camera_detection()
    
    # 5. 測試 picamera2
    picamera2_ok, picamera2_msg = test_picamera2()
    
    # 6. 測試 OpenCV
    opencv_ok, opencv_msg = test_opencv_camera()
    
    # 7. 創建測試腳本
    create_test_script()
    
    # 總結
    print("\n" + "=" * 50)
    print("📊 診斷總結:")
    print(f"🔧 攝像頭接口: {'✅' if interface_ok else '❌'}")
    print(f"📦 套件安裝: {'✅' if packages_ok else '❌'}")
    print(f"🔐 權限設置: {'✅' if permissions_ok else '❌'}")
    print(f"🔍 硬件檢測: {'✅' if detection_ok else '❌'}")
    print(f"📹 picamera2: {'✅' if picamera2_ok else '❌'} - {picamera2_msg}")
    print(f"🎦 OpenCV: {'✅' if opencv_ok else '❌'} - {opencv_msg}")
    
    if picamera2_ok or opencv_ok:
        print("\n🎉 恭喜！至少有一個攝像頭庫可以正常工作")
    else:
        print("\n⚠️  攝像頭功能可能存在問題，請檢查以下事項：")
        print("1. 攝像頭是否正確連接到 CSI 接口")
        print("2. 攝像頭排線是否插緊")
        print("3. 是否啟用了攝像頭接口")
        print("4. 是否安裝了最新的系統更新")
        print("5. 是否重新啟動過系統")
    
    print(f"\n🧪 可以運行 test_camera_functionality.py 進行更詳細的測試")

if __name__ == "__main__":
    main()
