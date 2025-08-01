import React from 'react';
import { Card, Row, Col, Statistic, Progress, Alert, Spin } from 'antd';
import {
  RobotOutlined,
  EyeOutlined,
  EnvironmentOutlined,
  ThunderboltOutlined,
  SafetyCertificateOutlined,
  SignalFilled
} from '@ant-design/icons';
import { RobotComponentProps } from '../types/RobotTypes';

const Dashboard: React.FC<RobotComponentProps> = ({ robotStatus }) => {
  if (!robotStatus) {
    return (
      <div style={{ textAlign: 'center', padding: '50px' }}>
        <Spin size="large" />
        <p style={{ marginTop: 16 }}>載入機器人狀態中...</p>
      </div>
    );
  }

  // 計算系統健康度
  const calculateSystemHealth = () => {
    let health = 100;
    
    if (robotStatus.motor?.emergency_stop) health -= 50;
    if ((robotStatus.sensors?.consecutive_failures ?? 0) > 0) health -= 20;
    if (!robotStatus.vision?.camera.is_opened) health -= 15;
    if (!robotStatus.vision?.detector.is_loaded) health -= 15;
    
    return Math.max(0, health);
  };

  const systemHealth = calculateSystemHealth();

  return (
    <div>
      {/* 系統狀態警告 */}
      {robotStatus.motor?.emergency_stop && (
        <Alert
          message="緊急停止狀態"
          description="機器人目前處於緊急停止狀態，請檢查安全情況後重置"
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 系統概覽統計 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="系統健康度"
              value={systemHealth}
              suffix="%"
              valueStyle={{ 
                color: systemHealth > 80 ? '#3f8600' : systemHealth > 50 ? '#fa8c16' : '#cf1322' 
              }}
              prefix={<SafetyCertificateOutlined />}
            />
            <Progress 
              percent={systemHealth} 
              size="small" 
              strokeColor={
                systemHealth > 80 ? '#3f8600' : systemHealth > 50 ? '#fa8c16' : '#cf1322'
              }
              showInfo={false}
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="檢測物體"
              value={robotStatus.vision?.last_detections || 0}
              suffix="個"
              prefix={<EyeOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="移動速度"
              value={Math.abs(robotStatus.motor?.pose.linear_velocity || 0)}
              suffix="m/s"
              precision={2}
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="導航狀態"
              value={robotStatus.navigation?.state || '未知'}
              prefix={<EnvironmentOutlined />}
              valueStyle={{ 
                color: robotStatus.navigation?.state === 'following_path' ? '#52c41a' : '#8c8c8c',
                fontSize: '16px'
              }}
            />
          </Card>
        </Col>
      </Row>

      {/* 詳細狀態卡片 */}
      <Row gutter={[16, 16]}>
        {/* 電機狀態 */}
        <Col xs={24} lg={12}>
          <Card 
            title="電機狀態" 
            extra={<RobotOutlined />}
            className="robot-status-card"
          >
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="左輪速度"
                  value={robotStatus.motor?.left_motor.speed || 0}
                  suffix="%"
                  precision={1}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="右輪速度"
                  value={robotStatus.motor?.right_motor.speed || 0}
                  suffix="%"
                  precision={1}
                />
              </Col>
            </Row>
            
            <div style={{ marginTop: 16 }}>
              <p><strong>位置:</strong> 
                X: {robotStatus.motor?.pose.x.toFixed(2) || '0.00'}m, 
                Y: {robotStatus.motor?.pose.y.toFixed(2) || '0.00'}m
              </p>
              <p><strong>朝向:</strong> {((robotStatus.motor?.pose.theta || 0) * 180 / Math.PI).toFixed(1)}°</p>
              <p><strong>移動狀態:</strong> 
                <span style={{ 
                  color: robotStatus.motor?.is_moving ? '#52c41a' : '#8c8c8c',
                  marginLeft: 8 
                }}>
                  {robotStatus.motor?.is_moving ? '移動中' : '靜止'}
                </span>
              </p>
            </div>
          </Card>
        </Col>

        {/* 感測器狀態 */}
        <Col xs={24} lg={12}>
          <Card 
            title="感測器狀態" 
            extra={<SignalFilled />}
            className="robot-status-card"
          >
            {/* 超聲波感測器 */}
            <div style={{ marginBottom: 16 }}>
              <h4>超聲波感測器</h4>
              {robotStatus.sensors?.ultrasonic && Object.entries(robotStatus.sensors.ultrasonic).map(([id, sensor]) => (
                <div key={id} style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span>{id}:</span>
                  <span style={{ 
                    color: sensor.available ? '#52c41a' : '#ff4d4f',
                    fontWeight: 'bold'
                  }}>
                    {sensor.available 
                      ? `${(sensor.last_distance || 0).toFixed(2)}m` 
                      : '離線'
                    }
                  </span>
                </div>
              ))}
            </div>

            {/* IMU狀態 */}
            <div>
              <h4>慣性測量單元 (IMU)</h4>
              <p>狀態: 
                <span style={{ 
                  color: robotStatus.sensors?.imu?.available ? '#52c41a' : '#ff4d4f',
                  marginLeft: 8 
                }}>
                  {robotStatus.sensors?.imu?.available ? '在線' : '離線'}
                </span>
              </p>
              {robotStatus.sensors?.imu?.available && robotStatus.sensors?.imu?.last_reading && (
                <p>溫度: {robotStatus.sensors.imu.last_reading.temperature?.toFixed(1) || 'N/A'}°C</p>
              )}
            </div>
          </Card>
        </Col>

        {/* 視覺系統狀態 */}
        <Col xs={24} lg={12}>
          <Card 
            title="視覺系統" 
            extra={<EyeOutlined />}
            className="robot-status-card"
          >
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="檢測物體"
                  value={robotStatus.vision?.last_detections || 0}
                  suffix="個"
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="障礙物"
                  value={robotStatus.vision?.last_obstacles || 0}
                  suffix="個"
                />
              </Col>
            </Row>
            
            <div style={{ marginTop: 16 }}>
              <p><strong>相機狀態:</strong> 
                <span style={{ 
                  color: robotStatus.vision?.camera.is_opened ? '#52c41a' : '#ff4d4f',
                  marginLeft: 8 
                }}>
                  {robotStatus.vision?.camera.is_opened ? '運行中' : '離線'}
                </span>
              </p>
              <p><strong>解析度:</strong> {robotStatus.vision?.camera.resolution || 'N/A'}</p>
              <p><strong>AI模型:</strong> 
                <span style={{ 
                  color: robotStatus.vision?.detector.is_loaded ? '#52c41a' : '#ff4d4f',
                  marginLeft: 8 
                }}>
                  {robotStatus.vision?.detector.is_loaded ? '已載入' : '未載入'}
                </span>
              </p>
              <p><strong>處理時間:</strong> {(robotStatus.vision?.last_processing_time || 0).toFixed(3)}s</p>
            </div>
          </Card>
        </Col>

        {/* 導航系統狀態 */}
        <Col xs={24} lg={12}>
          <Card 
            title="導航系統" 
            extra={<EnvironmentOutlined />}
            className="robot-status-card"
          >
            <div style={{ marginBottom: 16 }}>
              <p><strong>狀態:</strong> 
                <span style={{ 
                  color: robotStatus.navigation?.state === 'following_path' ? '#52c41a' : '#8c8c8c',
                  marginLeft: 8 
                }}>
                  {robotStatus.navigation?.state || '未知'}
                </span>
              </p>
              
              {robotStatus.navigation?.current_goal && (
                <p><strong>目標位置:</strong> 
                  ({robotStatus.navigation.current_goal.x.toFixed(2)}, {robotStatus.navigation.current_goal.y.toFixed(2)})
                </p>
              )}
              
              <p><strong>檢測障礙物:</strong> {robotStatus.navigation?.obstacles || 0} 個</p>
            </div>

            {/* 路徑進度 */}
            {robotStatus.navigation?.path_progress && robotStatus.navigation.path_progress.total_points > 0 && (
              <div>
                <p><strong>路徑進度:</strong></p>
                <Progress 
                  percent={robotStatus.navigation.path_progress.progress} 
                  size="small"
                  strokeColor="#1890ff"
                />
                <p style={{ fontSize: '12px', color: '#8c8c8c', marginTop: 4 }}>
                  {robotStatus.navigation.path_progress.current_index} / {robotStatus.navigation.path_progress.total_points} 路徑點
                </p>
              </div>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard; 