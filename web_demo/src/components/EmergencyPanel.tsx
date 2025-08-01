import React from 'react';
import { EmergencyPanelProps } from '../types/RobotTypes';

const EmergencyPanel: React.FC<EmergencyPanelProps> = ({ 
  emergencyMode, 
  onEmergencyStop, 
  onResetEmergency, 
  collapsed 
}) => {
  return (
    <div>
      <button onClick={onEmergencyStop} style={{ 
        backgroundColor: '#ff4d4f', 
        color: 'white', 
        border: 'none', 
        padding: '8px 16px', 
        borderRadius: '4px',
        cursor: 'pointer',
        marginBottom: '8px',
        width: '100%'
      }}>
        {collapsed ? '🚨' : '🚨 緊急停止'}
      </button>
      
      {emergencyMode && (
        <button onClick={onResetEmergency} style={{ 
          backgroundColor: '#52c41a', 
          color: 'white', 
          border: 'none', 
          padding: '8px 16px', 
          borderRadius: '4px',
          cursor: 'pointer',
          width: '100%'
        }}>
          {collapsed ? '✅' : '✅ 重置'}
        </button>
      )}
    </div>
  );
};

export default EmergencyPanel; 