import React, { useState, useEffect } from 'react';
import { Layout, Menu, theme, message, Badge } from 'antd';
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  DashboardOutlined,
  ControlOutlined,
  EyeOutlined,
  SettingOutlined,
  ApiOutlined,
  SafetyCertificateOutlined
} from '@ant-design/icons';

import Dashboard from './components/Dashboard';
import ManualControl from './components/ManualControl';
import VisionMonitor from './components/VisionMonitor';
import NavigationPlanner from './components/NavigationPlanner';
import SystemSettings from './components/SystemSettings';
import EmergencyPanel from './components/EmergencyPanel';
import { RobotApiService } from './services/RobotApiService';
import { WebSocketService } from './services/WebSocketService';
import { RobotStatus } from './types/RobotTypes';

import './App.css';

const { Header, Content, Sider } = Layout;

// 導航項目配置
const navigationItems = [
  {
    key: '/',
    icon: <DashboardOutlined />,
    label: <Link to="/">儀表板</Link>,
  },
  {
    key: '/control',
    icon: <ControlOutlined />,
    label: <Link to="/control">手動控制</Link>,
  },
  {
    key: '/vision',
    icon: <EyeOutlined />,
    label: <Link to="/vision">視覺監控</Link>,
  },
  {
    key: '/navigation',
    icon: <ApiOutlined />,
    label: <Link to="/navigation">路徑規劃</Link>,
  },
  {
    key: '/settings',
    icon: <SettingOutlined />,
    label: <Link to="/settings">系統設置</Link>,
  },
];

function AppContent() {
  const [collapsed, setCollapsed] = useState(false);
  const [robotStatus, setRobotStatus] = useState<RobotStatus | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'connecting'>('disconnected');
  const [emergencyMode, setEmergencyMode] = useState(false);
  const location = useLocation();

  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  // 初始化服務連接
  useEffect(() => {
    const initializeServices = async () => {
      try {
        setConnectionStatus('connecting');
        
        // 初始化WebSocket連接
        const wsService = WebSocketService.getInstance();
        
        wsService.onStatusUpdate = (status: RobotStatus) => {
          setRobotStatus(status);
        };
        
        wsService.onConnectionChange = (connected: boolean) => {
          setConnectionStatus(connected ? 'connected' : 'disconnected');
          if (connected) {
            message.success('已連接到機器人系統');
          } else {
            message.warning('與機器人系統連接中斷');
          }
        };
        
        await wsService.connect();
        
        // 獲取初始狀態
        const initialStatus = await RobotApiService.getStatus();
        setRobotStatus(initialStatus);
        
      } catch (error) {
        console.error('初始化服務失敗:', error);
        message.error('無法連接到機器人系統');
        setConnectionStatus('disconnected');
      }
    };

    initializeServices();

    // 清理函數
    return () => {
      WebSocketService.getInstance().disconnect();
    };
  }, []);

  // 監控緊急狀態
  useEffect(() => {
    if (robotStatus?.motor?.emergency_stop) {
      setEmergencyMode(true);
      message.error('機器人處於緊急停止狀態！', 5);
    } else {
      setEmergencyMode(false);
    }
  }, [robotStatus?.motor?.emergency_stop]);

  // 緊急停止處理
  const handleEmergencyStop = async () => {
    try {
      await RobotApiService.emergencyStop();
      message.warning('緊急停止已激活');
    } catch (error) {
      message.error('緊急停止失敗');
    }
  };

  // 重置緊急停止
  const handleResetEmergency = async () => {
    try {
      await RobotApiService.resetEmergencyStop();
      message.success('緊急停止已重置');
    } catch (error) {
      message.error('重置緊急停止失敗');
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider 
        collapsible 
        collapsed={collapsed} 
        onCollapse={setCollapsed}
        theme="light"
        width={250}
      >
        <div className="logo-container">
          <h2 style={{ 
            padding: '16px', 
            margin: 0, 
            textAlign: 'center',
            fontSize: collapsed ? '14px' : '16px',
            transition: 'all 0.3s'
          }}>
            {collapsed ? '🤖' : '🤖 送貨機器人'}
          </h2>
        </div>
        
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={navigationItems}
          style={{ borderRight: 0 }}
        />
        
        {/* 緊急控制面板 */}
        <div style={{ position: 'absolute', bottom: 20, left: 16, right: 16 }}>
          <EmergencyPanel
            emergencyMode={emergencyMode}
            onEmergencyStop={handleEmergencyStop}
            onResetEmergency={handleResetEmergency}
            collapsed={collapsed}
          />
        </div>
      </Sider>

      <Layout>
        <Header 
          style={{ 
            padding: '0 24px', 
            background: colorBgContainer,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
          }}
        >
          <h1 style={{ margin: 0, fontSize: '18px', fontWeight: 'bold' }}>
            樹莓派智能送貨機器人控制系統
          </h1>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {/* 連接狀態指示器 */}
            <Badge
              status={
                connectionStatus === 'connected' ? 'success' :
                connectionStatus === 'connecting' ? 'processing' : 'error'
              }
              text={
                connectionStatus === 'connected' ? '已連接' :
                connectionStatus === 'connecting' ? '連接中' : '已斷開'
              }
            />
            
            {/* 機器人狀態摘要 */}
            {robotStatus && (
              <div style={{ display: 'flex', gap: 12, fontSize: '12px' }}>
                <span>
                  <SafetyCertificateOutlined style={{ color: emergencyMode ? '#ff4d4f' : '#52c41a' }} />
                  {emergencyMode ? ' 緊急' : ' 正常'}
                </span>
                <span>
                  導航: {robotStatus.navigation?.state || '未知'}
                </span>
                <span>
                  檢測: {robotStatus.vision?.last_detections || 0} 個物體
                </span>
              </div>
            )}
          </div>
        </Header>

        <Content
          style={{
            margin: '16px',
            padding: 24,
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
            overflow: 'auto'
          }}
        >
          <Routes>
            <Route path="/" element={<Dashboard robotStatus={robotStatus} />} />
            <Route path="/control" element={<ManualControl robotStatus={robotStatus} />} />
            <Route path="/vision" element={<VisionMonitor robotStatus={robotStatus} />} />
            <Route path="/navigation" element={<NavigationPlanner robotStatus={robotStatus} />} />
            <Route path="/settings" element={<SystemSettings robotStatus={robotStatus} />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App; 