import React from 'react';
import { RobotComponentProps } from '../types/RobotTypes';

const NavigationPlanner: React.FC<RobotComponentProps> = ({ robotStatus }) => {
  return (
    <div>
      <h1>路徑規劃</h1>
      <p>機器人導航和路徑規劃界面</p>
    </div>
  );
};

export default NavigationPlanner; 