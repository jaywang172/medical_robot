// WebSocket服務，用於實時通訊
import { RobotStatus, WebSocketMessage, StatusUpdateMessage } from '../types/RobotTypes';

export class WebSocketService {
  private static instance: WebSocketService;
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 3000; // 3秒
  private pingInterval: NodeJS.Timeout | null = null;
  private isConnecting = false;

  // 回調函數
  public onStatusUpdate: ((status: RobotStatus) => void) | null = null;
  public onConnectionChange: ((connected: boolean) => void) | null = null;
  public onError: ((error: Event) => void) | null = null;

  private constructor() {}

  // 單例模式
  public static getInstance(): WebSocketService {
    if (!WebSocketService.instance) {
      WebSocketService.instance = new WebSocketService();
    }
    return WebSocketService.instance;
  }

  // 連接WebSocket
  public async connect(): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      console.log('WebSocket already connected');
      return;
    }

    if (this.isConnecting) {
      console.log('WebSocket connection already in progress');
      return;
    }

    this.isConnecting = true;
    const wsUrl = this.getWebSocketUrl();
    
    console.log(`Connecting to WebSocket: ${wsUrl}`);

    try {
      this.ws = new WebSocket(wsUrl);
      this.setupEventHandlers();
      
      // 等待連接建立
      await new Promise<void>((resolve, reject) => {
        if (!this.ws) {
          reject(new Error('WebSocket instance is null'));
          return;
        }

        const timeout = setTimeout(() => {
          reject(new Error('WebSocket connection timeout'));
        }, 10000);

        this.ws.onopen = () => {
          clearTimeout(timeout);
          resolve();
        };

        this.ws.onerror = (error) => {
          clearTimeout(timeout);
          reject(error);
        };
      });

    } catch (error) {
      this.isConnecting = false;
      console.error('WebSocket connection failed:', error);
      this.handleReconnect();
      throw error;
    }
  }

  // 設置事件處理器
  private setupEventHandlers(): void {
    if (!this.ws) return;

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.isConnecting = false;
      this.reconnectAttempts = 0;
      
      // 開始心跳
      this.startPing();
      
      // 通知連接狀態
      if (this.onConnectionChange) {
        this.onConnectionChange(true);
      }
    };

    this.ws.onmessage = (event) => {
      this.handleMessage(event.data);
    };

    this.ws.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      this.isConnecting = false;
      
      // 停止心跳
      this.stopPing();
      
      // 通知連接狀態
      if (this.onConnectionChange) {
        this.onConnectionChange(false);
      }

      // 如果不是主動關閉，嘗試重連
      if (event.code !== 1000) {
        this.handleReconnect();
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      this.isConnecting = false;
      
      if (this.onError) {
        this.onError(error);
      }
    };
  }

  // 處理接收到的消息
  private handleMessage(data: string): void {
    try {
      const message: WebSocketMessage = JSON.parse(data);
      
      switch (message.type) {
        case 'status_update':
          const statusMessage = message as StatusUpdateMessage;
          if (this.onStatusUpdate && statusMessage.data) {
            this.onStatusUpdate(statusMessage.data);
          }
          break;
          
        case 'pong':
          // 心跳響應
          console.log('Received pong from server');
          break;
          
        default:
          console.log('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  // 發送消息
  public sendMessage(message: WebSocketMessage): boolean {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('WebSocket is not connected');
      return false;
    }

    try {
      this.ws.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error('Error sending WebSocket message:', error);
      return false;
    }
  }

  // 發送手動控制命令
  public sendManualControl(leftSpeed: number, rightSpeed: number, duration?: number): boolean {
    return this.sendMessage({
      type: 'manual_control',
      data: {
        left_speed: leftSpeed,
        right_speed: rightSpeed,
        duration
      }
    });
  }

  // 開始心跳
  private startPing(): void {
    this.stopPing(); // 確保沒有重複的定時器
    
    this.pingInterval = setInterval(() => {
      this.sendMessage({ type: 'ping' });
    }, 30000); // 每30秒發送一次心跳
  }

  // 停止心跳
  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  // 處理重連
  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts++;
    console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    setTimeout(() => {
      this.connect().catch(error => {
        console.error('Reconnection failed:', error);
      });
    }, this.reconnectInterval);
  }

  // 獲取WebSocket URL
  private getWebSocketUrl(): string {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = process.env.REACT_APP_WS_HOST || window.location.host;
    return `${protocol}//${host}/ws`;
  }

  // 斷開連接
  public disconnect(): void {
    this.stopPing();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnecting');
      this.ws = null;
    }
    
    this.reconnectAttempts = 0;
    this.isConnecting = false;
  }

  // 獲取連接狀態
  public isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  // 獲取連接狀態字符串
  public getConnectionState(): string {
    if (!this.ws) return 'disconnected';
    
    switch (this.ws.readyState) {
      case WebSocket.CONNECTING:
        return 'connecting';
      case WebSocket.OPEN:
        return 'connected';
      case WebSocket.CLOSING:
        return 'closing';
      case WebSocket.CLOSED:
        return 'disconnected';
      default:
        return 'unknown';
    }
  }

  // 重置重連計數
  public resetReconnectAttempts(): void {
    this.reconnectAttempts = 0;
  }

  // 設置最大重連次數
  public setMaxReconnectAttempts(attempts: number): void {
    this.maxReconnectAttempts = Math.max(0, attempts);
  }

  // 設置重連間隔
  public setReconnectInterval(interval: number): void {
    this.reconnectInterval = Math.max(1000, interval);
  }
}

export default WebSocketService; 