// 機器人API服務
import axios from 'axios';
import {
  RobotStatus,
  RobotConfig,
  GoalRequest,
  ManualControlRequest,
  CarControlRequest,
  CarStatus,
  ApiResponse,
  VisionStreamData,
  PathData,
  SensorDistances
} from '../types/RobotTypes';

// 配置axios默認設置
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 請求攔截器
apiClient.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// 響應攔截器
apiClient.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export class RobotApiService {
  // 獲取機器人狀態
  static async getStatus(): Promise<RobotStatus> {
    try {
      const response = await apiClient.get<RobotStatus>('/api/status');
      return response.data;
    } catch (error) {
      console.error('獲取機器人狀態失敗:', error);
      throw new Error('無法獲取機器人狀態');
    }
  }

  // 獲取機器人配置
  static async getConfig(): Promise<RobotConfig> {
    try {
      const response = await apiClient.get<RobotConfig>('/api/config');
      return response.data;
    } catch (error) {
      console.error('獲取機器人配置失敗:', error);
      throw new Error('無法獲取機器人配置');
    }
  }

  // 設置導航目標
  static async setNavigationGoal(goal: GoalRequest): Promise<ApiResponse> {
    try {
      const response = await apiClient.post<ApiResponse>('/api/navigation/goal', goal);
      return response.data;
    } catch (error) {
      console.error('設置導航目標失敗:', error);
      throw new Error('無法設置導航目標');
    }
  }

  // 手動控制機器人
  static async manualControl(control: ManualControlRequest): Promise<ApiResponse> {
    try {
      const response = await apiClient.post<ApiResponse>('/api/control/manual', control);
      return response.data;
    } catch (error) {
      console.error('手動控制失敗:', error);
      throw new Error('無法執行手動控制');
    }
  }

  // 停止機器人
  static async stopRobot(): Promise<ApiResponse> {
    try {
      const response = await apiClient.post<ApiResponse>('/api/control/stop');
      return response.data;
    } catch (error) {
      console.error('停止機器人失敗:', error);
      throw new Error('無法停止機器人');
    }
  }

  // 緊急停止
  static async emergencyStop(): Promise<ApiResponse> {
    try {
      const response = await apiClient.post<ApiResponse>('/api/control/emergency_stop');
      return response.data;
    } catch (error) {
      console.error('緊急停止失敗:', error);
      throw new Error('無法執行緊急停止');
    }
  }

  // 重置緊急停止
  static async resetEmergencyStop(): Promise<ApiResponse> {
    try {
      const response = await apiClient.post<ApiResponse>('/api/control/reset_emergency');
      return response.data;
    } catch (error) {
      console.error('重置緊急停止失敗:', error);
      throw new Error('無法重置緊急停止');
    }
  }

  // 獲取視覺流
  static async getVisionStream(): Promise<VisionStreamData> {
    try {
      const response = await apiClient.get<VisionStreamData>('/api/vision/stream');
      return response.data;
    } catch (error) {
      console.error('獲取視覺流失敗:', error);
      throw new Error('無法獲取視覺流');
    }
  }

  // 獲取感測器距離數據
  static async getSensorDistances(): Promise<SensorDistances> {
    try {
      const response = await apiClient.get<SensorDistances>('/api/sensors/distances');
      return response.data;
    } catch (error) {
      console.error('獲取感測器數據失敗:', error);
      throw new Error('無法獲取感測器數據');
    }
  }

  // 獲取當前路徑
  static async getCurrentPath(): Promise<PathData> {
    try {
      const response = await apiClient.get<PathData>('/api/navigation/path');
      return response.data;
    } catch (error) {
      console.error('獲取路徑數據失敗:', error);
      throw new Error('無法獲取路徑數據');
    }
  }

  // 更新配置
  static async updateConfig(section: string, key: string, value: number): Promise<ApiResponse> {
    try {
      const response = await apiClient.post<ApiResponse>('/api/config/update', {
        section,
        key,
        value
      });
      return response.data;
    } catch (error) {
      console.error('更新配置失敗:', error);
      throw new Error('無法更新配置');
    }
  }

  // 系統關閉
  static async shutdownSystem(): Promise<ApiResponse> {
    try {
      const response = await apiClient.post<ApiResponse>('/api/system/shutdown');
      return response.data;
    } catch (error) {
      console.error('系統關閉失敗:', error);
      throw new Error('無法關閉系統');
    }
  }

  // 測試電機
  static async testMotor(): Promise<ApiResponse> {
    try {
      const response = await apiClient.get<ApiResponse>('/api/test/motor');
      return response.data;
    } catch (error) {
      console.error('測試電機失敗:', error);
      throw new Error('無法測試電機');
    }
  }

  // 健康檢查
  static async healthCheck(): Promise<boolean> {
    try {
      const response = await apiClient.get('/');
      return response.status === 200;
    } catch (error) {
      console.error('健康檢查失敗:', error);
      return false;
    }
  }

  // 核心車輛控制API
  static async carControl(request: CarControlRequest): Promise<ApiResponse> {
    try {
      const response = await apiClient.post<ApiResponse>('/api/car/control', request);
      return response.data;
    } catch (error) {
      console.error('車輛控制失敗:', error);
      throw new Error('無法執行車輛控制');
    }
  }

  // 獲取車輛狀態
  static async getCarStatus(): Promise<CarStatus> {
    try {
      const response = await apiClient.get<CarStatus>('/api/car/status');
      return response.data;
    } catch (error) {
      console.error('獲取車輛狀態失敗:', error);
      throw new Error('無法獲取車輛狀態');
    }
  }

  // 重置車輛緊急停止
  static async resetCarEmergency(): Promise<ApiResponse> {
    try {
      const response = await apiClient.post<ApiResponse>('/api/car/emergency_reset');
      return response.data;
    } catch (error) {
      console.error('重置車輛緊急停止失敗:', error);
      throw new Error('無法重置車輛緊急停止');
    }
  }

  // 測試車輛控制器
  static async testCarController(): Promise<ApiResponse> {
    try {
      const response = await apiClient.get<ApiResponse>('/api/car/test');
      return response.data;
    } catch (error) {
      console.error('測試車輛控制器失敗:', error);
      throw new Error('無法測試車輛控制器');
    }
  }

  // 通用錯誤處理
  static handleApiError(error: any): string {
    if (error.response) {
      // 服務器響應的錯誤
      const status = error.response.status;
      const message = error.response.data?.detail || error.response.data?.message || '未知錯誤';
      
      switch (status) {
        case 400:
          return `請求錯誤: ${message}`;
        case 401:
          return '未授權訪問';
        case 403:
          return '禁止訪問';
        case 404:
          return '請求的資源不存在';
        case 500:
          return `服務器內部錯誤: ${message}`;
        case 503:
          return `服務不可用: ${message}`;
        default:
          return `請求失敗 (${status}): ${message}`;
      }
    } else if (error.request) {
      // 網路錯誤
      return '網路連接失敗，請檢查網路設置';
    } else {
      // 其他錯誤
      return `錯誤: ${error.message}`;
    }
  }
}

export default RobotApiService; 