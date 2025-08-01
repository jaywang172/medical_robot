import React from 'react';
import { RobotComponentProps } from '../types/RobotTypes';

const VisionMonitor: React.FC<RobotComponentProps> = ({ robotStatus }) => {
  return (
    <div>
      <h1>視覺監控</h1>
      <p>機器人視覺系統監控界面</p>
    </div>
  );
};

export default VisionMonitor; 