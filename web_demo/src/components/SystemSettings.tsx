import React from 'react';
import { RobotComponentProps } from '../types/RobotTypes';

const SystemSettings: React.FC<RobotComponentProps> = ({ robotStatus }) => {
  return (
    <div>
      <h1>系統設置</h1>
      <p>機器人系統配置界面</p>
    </div>
  );
};

export default SystemSettings; 