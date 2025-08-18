// 機器人狀態相關類型定義

export interface RobotStatus {
  timestamp: number;
  system: SystemStatus;
  motor?: MotorStatus;
  sensors?: SensorStatus;
  vision?: VisionStatus;
  navigation?: NavigationStatus;
}

export interface SystemStatus {
  is_running: boolean;
  main_loop_interval: number;
}

export interface MotorStatus {
  left_motor: {
    speed: number;
    direction: string;
  };
  right_motor: {
    speed: number;
    direction: string;
  };
  is_moving: boolean;
  emergency_stop: boolean;
  pose: {
    x: number;
    y: number;
    theta: number;
    linear_velocity: number;
    angular_velocity: number;
  };
}

export interface SensorStatus {
  ultrasonic: {
    [sensorId: string]: {
      available: boolean;
      last_distance: number | null;
    };
  };
  imu: {
    available: boolean;
    last_reading: {
      acceleration: [number, number, number] | null;
      gyroscope: [number, number, number] | null;
      temperature: number | null;
    } | null;
  } | null;
  consecutive_failures: number;
  last_update: number | null;
}

export interface VisionStatus {
  camera: {
    is_opened: boolean;
    resolution: string;
    fps: number;
  };
  detector: {
    is_loaded: boolean;
    model_path: string;
    confidence_threshold: number;
  };
  last_detections: number;
  last_obstacles: number;
  last_processing_time: number;
}

export interface NavigationStatus {
  state: string;
  current_position: {
    x: number;
    y: number;
    theta: number;
  };
  current_goal: {
    x: number;
    y: number;
  } | null;
  path_progress: {
    total_points: number;
    current_index: number;
    progress: number;
  };
  obstacles: number;
  grid: {
    width: number;
    height: number;
    resolution: number;
  };
}

// API請求和響應類型
export interface GoalRequest {
  x: number;
  y: number;
}

export interface ManualControlRequest {
  linear_speed: number;
  angular_speed: number;
  duration?: number;
}

// 核心車輛控制類型
export interface CarControlRequest {
  action: 'forward' | 'backward' | 'turn_left' | 'turn_right' | 'stop' | 'emergency_stop';
  duration?: number;
}

export interface CarStatus {
  is_moving: boolean;
  current_direction: string;
  last_command_time: number;
  emergency_stop: boolean;
  simulation_mode: boolean;
}

export interface ApiResponse<T = any> {
  success: boolean;
  message?: string;
  data?: T;
}

// 視覺數據類型
export interface VisionStreamData {
  image: string; // base64編碼的圖像
  timestamp: number;
  detections: number;
  obstacles: number;
  processing_time: number;
}

export interface Detection {
  class_id: number;
  class_name: string;
  confidence: number;
  bbox: [number, number, number, number]; // [x1, y1, x2, y2]
  center: [number, number]; // [x, y]
  distance?: number;
  angle?: number;
}

// 路徑規劃類型
export interface PathPoint {
  x: number;
  y: number;
}

export interface PathData {
  path: PathPoint[];
  current_index: number;
  total_points: number;
  state: string;
}

// 感測器數據類型
export interface SensorDistances {
  distances: {
    [sensorId: string]: number;
  };
  timestamp: number;
}

// WebSocket消息類型
export interface WebSocketMessage {
  type: string;
  data?: any;
}

export interface StatusUpdateMessage extends WebSocketMessage {
  type: 'status_update';
  data: RobotStatus;
}

export interface ManualControlMessage extends WebSocketMessage {
  type: 'manual_control';
  data: {
    left_speed: number;
    right_speed: number;
    duration?: number;
  };
}

// 配置類型
export interface RobotConfig {
  debug: boolean;
  simulation: boolean;
  motor: {
    max_speed: number;
    acceleration: number;
  };
  vision: {
    camera_resolution: string;
    confidence_threshold: number;
  };
  navigation: {
    max_speed: number;
    safety_distance: number;
  };
}

// 圖表數據類型
export interface ChartDataPoint {
  timestamp: number;
  value: number;
  label?: string;
}

export interface SensorChartData {
  front: ChartDataPoint[];
  left: ChartDataPoint[];
  right: ChartDataPoint[];
  back: ChartDataPoint[];
}

// 組件屬性類型
export interface RobotComponentProps {
  robotStatus: RobotStatus | null;
}

// 緊急控制面板屬性
export interface EmergencyPanelProps {
  emergencyMode: boolean;
  onEmergencyStop: () => void;
  onResetEmergency: () => void;
  collapsed: boolean;
}

// 手動控制器屬性
export interface ManualControllerProps {
  onControlChange: (linear: number, angular: number) => void;
  disabled?: boolean;
  emergencyMode?: boolean;
}

// 地圖組件屬性
export interface NavigationMapProps {
  robotPosition: { x: number; y: number; theta: number };
  goalPosition?: { x: number; y: number };
  obstacles: { x: number; y: number; radius: number }[];
  path: PathPoint[];
  onGoalSet: (x: number, y: number) => void;
  mapSize: { width: number; height: number };
}

// 統計卡片屬性
export interface StatCardProps {
  title: string;
  value: string | number;
  unit?: string;
  trend?: 'up' | 'down' | 'stable';
  color?: string;
  icon?: JSX.Element;
}

// 實時圖表屬性
export interface RealtimeChartProps {
  data: ChartDataPoint[];
  title: string;
  color?: string;
  unit?: string;
  maxDataPoints?: number;
} 