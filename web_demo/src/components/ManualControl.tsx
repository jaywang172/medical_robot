import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Button, 
  Row, 
  Col, 
  Space, 
  Slider, 
  Switch,
  Badge,
  Typography,
  message,
  Statistic,
  Divider,
  Alert
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  ArrowLeftOutlined,
  ArrowRightOutlined,
  StopOutlined,
  WarningOutlined,
  ReloadOutlined,

  BugOutlined
} from '@ant-design/icons';
import { RobotComponentProps, CarStatus, CarControlRequest } from '../types/RobotTypes';
import RobotApiService from '../services/RobotApiService';

const { Title, Text } = Typography;

const ManualControl: React.FC<RobotComponentProps> = ({ robotStatus }) => {
  const [carStatus, setCarStatus] = useState<CarStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [duration, setDuration] = useState(0.5);
  const [isCarControlEnabled, setIsCarControlEnabled] = useState(false);
  const [lastAction, setLastAction] = useState<string>('無');

  // 獲取車輛狀態
  const fetchCarStatus = async () => {
    try {
      const status = await RobotApiService.getCarStatus();
      setCarStatus(status);
    } catch (error) {
      console.error('獲取車輛狀態失敗:', error);
    }
  };

  // 定期更新車輛狀態
  useEffect(() => {
    if (isCarControlEnabled) {
      fetchCarStatus();
      const interval = setInterval(fetchCarStatus, 1000);
      return () => clearInterval(interval);
    }
  }, [isCarControlEnabled]);

  // 執行車輛控制命令
  const executeCarControl = async (action: CarControlRequest['action']) => {
    if (!isCarControlEnabled) {
      message.warning('請先啟用核心車輛控制');
      return;
    }

    setLoading(true);
    try {
      const request: CarControlRequest = {
        action,
        duration: action === 'stop' || action === 'emergency_stop' ? undefined : duration
      };

      const response = await RobotApiService.carControl(request);
      
      if (response.success) {
        message.success(response.message);
        setLastAction(getActionDisplayName(action));
        await fetchCarStatus();
      } else {
        message.error(response.message || '控制失敗');
      }
    } catch (error) {
      message.error('控制命令執行失敗');
      console.error('車輛控制錯誤:', error);
    } finally {
      setLoading(false);
    }
  };

  // 重置緊急停止
  const resetEmergency = async () => {
    setLoading(true);
    try {
      const response = await RobotApiService.resetCarEmergency();
      if (response.success) {
        message.success('緊急停止已重置');
        await fetchCarStatus();
      } else {
        message.error('重置失敗');
      }
    } catch (error) {
      message.error('重置緊急停止失敗');
      console.error('重置錯誤:', error);
    } finally {
      setLoading(false);
    }
  };

  // 測試車輛控制器
  const testCarController = async () => {
    setLoading(true);
    try {
      message.info('開始執行測試序列...');
      const response = await RobotApiService.testCarController();
      if (response.success) {
        message.success('測試完成！');
        await fetchCarStatus();
      } else {
        message.error('測試失敗');
      }
    } catch (error) {
      message.error('測試執行失敗');
      console.error('測試錯誤:', error);
    } finally {
      setLoading(false);
    }
  };

  // 獲取動作顯示名稱
  const getActionDisplayName = (action: string): string => {
    const actionMap: { [key: string]: string } = {
      forward: '前進',
      backward: '後退',
      turn_left: '左轉',
      turn_right: '右轉',
      stop: '停止',
      emergency_stop: '緊急停止'
    };
    return actionMap[action] || action;
  };

  // 格式化時間
  const formatTime = (timestamp: number): string => {
    if (!timestamp) return '無';
    return new Date(timestamp * 1000).toLocaleTimeString();
  };

  return (
    <div style={{ padding: '20px' }}>
      <Title level={2}>🎮 手動控制 - 核心車輛控制整合</Title>
      
      {/* 系統狀態卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '20px' }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="機器人系統"
              value={robotStatus?.system.is_running ? '運行中' : '停止'}
              valueStyle={{ color: robotStatus?.system.is_running ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="車輛控制器"
              value={carStatus ? (carStatus.simulation_mode ? '模擬模式' : '硬件模式') : '未知'}
              valueStyle={{ color: carStatus?.simulation_mode ? '#1890ff' : '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="最後動作"
              value={lastAction}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 控制面板 */}
      <Row gutter={[16, 16]}>
        <Col span={16}>
          <Card title="🚗 核心車輛控制" extra={
            <Space>
              <Text>啟用控制:</Text>
              <Switch 
                checked={isCarControlEnabled}
                onChange={setIsCarControlEnabled}
                loading={loading}
              />
            </Space>
          }>
            
            {/* 緊急停止警告 */}
            {carStatus?.emergency_stop && (
              <Alert
                message="🚨 緊急停止狀態"
                description="車輛處於緊急停止狀態，需要重置後才能繼續操作"
                type="error"
                showIcon
                style={{ marginBottom: '16px' }}
                action={
                  <Button 
                    size="small" 
                    danger 
                    onClick={resetEmergency}
                    loading={loading}
                    icon={<ReloadOutlined />}
                  >
                    重置
                  </Button>
                }
              />
            )}

            {/* 持續時間設置 */}
            <div style={{ marginBottom: '16px' }}>
              <Text>動作持續時間: {duration}秒</Text>
              <Slider
                min={0.1}
                max={3.0}
                step={0.1}
                value={duration}
                onChange={setDuration}
                disabled={!isCarControlEnabled || carStatus?.emergency_stop}
              />
            </div>

            {/* 方向控制按鈕 */}
            <div style={{ textAlign: 'center' }}>
              {/* 前進 */}
              <div style={{ marginBottom: '8px' }}>
                <Button
                  type="primary"
                  size="large"
                  icon={<ArrowUpOutlined />}
                  onClick={() => executeCarControl('forward')}
                  disabled={!isCarControlEnabled || carStatus?.emergency_stop}
                  loading={loading}
                  style={{ width: '80px', height: '60px' }}
                >
                  前進
                </Button>
              </div>

              {/* 左轉、停止、右轉 */}
              <div style={{ marginBottom: '8px' }}>
                <Space size={8}>
                  <Button
                    type="primary"
                    size="large"
                    icon={<ArrowLeftOutlined />}
                    onClick={() => executeCarControl('turn_left')}
                    disabled={!isCarControlEnabled || carStatus?.emergency_stop}
                    loading={loading}
                    style={{ width: '80px', height: '60px' }}
                  >
                    左轉
                  </Button>
                  
                  <Button
                    type="default"
                    size="large"
                    icon={<StopOutlined />}
                    onClick={() => executeCarControl('stop')}
                    disabled={!isCarControlEnabled}
                    loading={loading}
                    style={{ width: '80px', height: '60px' }}
                  >
                    停止
                  </Button>
                  
                  <Button
                    type="primary"
                    size="large"
                    icon={<ArrowRightOutlined />}
                    onClick={() => executeCarControl('turn_right')}
                    disabled={!isCarControlEnabled || carStatus?.emergency_stop}
                    loading={loading}
                    style={{ width: '80px', height: '60px' }}
                  >
                    右轉
                  </Button>
                </Space>
              </div>

              {/* 後退 */}
              <div>
                <Button
                  type="primary"
                  size="large"
                  icon={<ArrowDownOutlined />}
                  onClick={() => executeCarControl('backward')}
                  disabled={!isCarControlEnabled || carStatus?.emergency_stop}
                  loading={loading}
                  style={{ width: '80px', height: '60px' }}
                >
                  後退
                </Button>
              </div>
            </div>

            <Divider />

            {/* 緊急和測試控制 */}
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <Button
                  danger
                  type="primary"
                  block
                  size="large"
                  icon={<WarningOutlined />}
                  onClick={() => executeCarControl('emergency_stop')}
                  disabled={!isCarControlEnabled}
                  loading={loading}
                >
                  緊急停止
                </Button>
              </Col>
              <Col span={12}>
                <Button
                  type="dashed"
                  block
                  size="large"
                  icon={<BugOutlined />}
                  onClick={testCarController}
                  disabled={!isCarControlEnabled || carStatus?.emergency_stop}
                  loading={loading}
                >
                  測試序列
                </Button>
              </Col>
            </Row>
          </Card>
        </Col>

        {/* 狀態信息 */}
        <Col span={8}>
          <Card title="📊 車輛狀態">
            {carStatus ? (
              <Space direction="vertical" style={{ width: '100%' }}>
                <div>
                  <Text strong>運動狀態: </Text>
                  <Badge 
                    status={carStatus.is_moving ? 'processing' : 'default'} 
                    text={carStatus.is_moving ? '運動中' : '靜止'} 
                  />
                </div>
                
                <div>
                  <Text strong>當前方向: </Text>
                  <Text code>{getActionDisplayName(carStatus.current_direction)}</Text>
                </div>
                
                <div>
                  <Text strong>緊急停止: </Text>
                  <Badge 
                    status={carStatus.emergency_stop ? 'error' : 'success'} 
                    text={carStatus.emergency_stop ? '啟動' : '正常'} 
                  />
                </div>
                
                <div>
                  <Text strong>最後命令時間: </Text>
                  <Text>{formatTime(carStatus.last_command_time)}</Text>
                </div>
                
                <div>
                  <Text strong>模式: </Text>
                  <Badge 
                    color={carStatus.simulation_mode ? 'blue' : 'green'}
                    text={carStatus.simulation_mode ? '模擬' : '硬件'}
                  />
                </div>
              </Space>
            ) : (
              <Text type="secondary">
                {isCarControlEnabled ? '載入中...' : '請啟用車輛控制以查看狀態'}
              </Text>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default ManualControl; 