import React from 'react';
import { RobotComponentProps } from '../types/RobotTypes';

const ManualControl: React.FC<RobotComponentProps> = ({ robotStatus }) => {
  return (
    <div>
      <h1>手動控制</h1>
      <p>機器人手動控制界面</p>
      {robotStatus ? (
        <p>機器人狀態: {robotStatus.system.is_running ? '運行中' : '停止'}</p>
      ) : (
        <p>載入中...</p>
      )}
    </div>
  );
};

export default ManualControl; 