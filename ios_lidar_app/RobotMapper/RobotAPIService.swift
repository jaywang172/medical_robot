import Foundation
import Network
import Combine

// MARK: - 機器人API服務
class RobotAPIService: ObservableObject {
    static let shared = RobotAPIService()
    
    @Published var isConnected = false
    @Published var connectionStatus: ConnectionStatus = .disconnected
    @Published var lastError: String?
    
    private var baseURL: String = "http://192.168.1.100:8000"
    private var session: URLSession
    private var webSocketTask: URLSessionWebSocketTask?
    private var cancellables = Set<AnyCancellable>()
    private let monitor = NWPathMonitor()
    private let monitorQueue = DispatchQueue(label: "NetworkMonitor")
    
    enum ConnectionStatus {
        case disconnected
        case connecting
        case connected
        case error(String)
        
        var description: String {
            switch self {
            case .disconnected: return "未連接"
            case .connecting: return "連接中"
            case .connected: return "已連接"
            case .error(let message): return "錯誤: \(message)"
            }
        }
    }
    
    private init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 10.0
        config.timeoutIntervalForResource = 30.0
        self.session = URLSession(configuration: config)
        
        startNetworkMonitoring()
    }
    
    deinit {
        monitor.cancel()
        disconnect()
    }
    
    // MARK: - 網路監控
    
    private func startNetworkMonitoring() {
        monitor.pathUpdateHandler = { [weak self] path in
            DispatchQueue.main.async {
                if path.status == .satisfied {
                    // 網路可用
                } else {
                    self?.handleNetworkUnavailable()
                }
            }
        }
        monitor.start(queue: monitorQueue)
    }
    
    private func handleNetworkUnavailable() {
        isConnected = false
        connectionStatus = .error("網路不可用")
        disconnect()
    }
    
    // MARK: - 連接管理
    
    func connect(to serverURL: String) {
        baseURL = serverURL
        connectionStatus = .connecting
        lastError = nil
        
        // 首先測試HTTP連接
        testConnection { [weak self] success in
            DispatchQueue.main.async {
                if success {
                    self?.connectWebSocket()
                } else {
                    self?.connectionStatus = .error("無法連接到機器人服務器")
                    self?.lastError = "連接失敗"
                }
            }
        }
    }
    
    private func testConnection(completion: @escaping (Bool) -> Void) {
        guard let url = URL(string: "\(baseURL)/api/status") else {
            completion(false)
            return
        }
        
        let task = session.dataTask(with: url) { data, response, error in
            if let error = error {
                print("Connection test failed: \(error)")
                completion(false)
                return
            }
            
            if let httpResponse = response as? HTTPURLResponse,
               httpResponse.statusCode == 200 {
                completion(true)
            } else {
                completion(false)
            }
        }
        
        task.resume()
    }
    
    private func connectWebSocket() {
        guard let wsURL = URL(string: baseURL.replacingOccurrences(of: "http", with: "ws") + "/ws") else {
            connectionStatus = .error("無效的WebSocket URL")
            return
        }
        
        webSocketTask = session.webSocketTask(with: wsURL)
        webSocketTask?.resume()
        
        // 開始接收消息
        receiveMessage()
        
        // 發送ping測試連接
        sendPing()
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 2.0) {
            if self.webSocketTask?.state == .running {
                self.isConnected = true
                self.connectionStatus = .connected
                self.startHeartbeat()
            } else {
                self.connectionStatus = .error("WebSocket連接失敗")
            }
        }
    }
    
    func disconnect() {
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
        isConnected = false
        connectionStatus = .disconnected
        stopHeartbeat()
    }
    
    // MARK: - WebSocket消息處理
    
    private func receiveMessage() {
        webSocketTask?.receive { [weak self] result in
            switch result {
            case .failure(let error):
                print("WebSocket receive error: \(error)")
                DispatchQueue.main.async {
                    self?.handleWebSocketError(error)
                }
            case .success(let message):
                switch message {
                case .string(let text):
                    self?.handleWebSocketMessage(text)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        self?.handleWebSocketMessage(text)
                    }
                @unknown default:
                    break
                }
                
                // 繼續接收下一個消息
                self?.receiveMessage()
            }
        }
    }
    
    private func handleWebSocketMessage(_ message: String) {
        guard let data = message.data(using: .utf8) else { return }
        
        do {
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
               let type = json["type"] as? String {
                
                switch type {
                case "pong":
                    // 心跳響應
                    break
                case "status_update":
                    if let statusData = json["data"] {
                        handleStatusUpdate(statusData)
                    }
                default:
                    print("Unknown message type: \(type)")
                }
            }
        } catch {
            print("Error parsing WebSocket message: \(error)")
        }
    }
    
    private func handleStatusUpdate(_ statusData: Any) {
        // 處理機器人狀態更新
        // 這裡可以發送通知給觀察者
        NotificationCenter.default.post(
            name: .robotStatusUpdated,
            object: statusData
        )
    }
    
    private func handleWebSocketError(_ error: Error) {
        isConnected = false
        connectionStatus = .error(error.localizedDescription)
        lastError = error.localizedDescription
        
        // 嘗試重連
        DispatchQueue.main.asyncAfter(deadline: .now() + 5.0) {
            if self.connectionStatus.description.contains("錯誤") {
                self.connect(to: self.baseURL)
            }
        }
    }
    
    // MARK: - 心跳機制
    
    private var heartbeatTimer: Timer?
    
    private func startHeartbeat() {
        heartbeatTimer = Timer.scheduledTimer(withTimeInterval: 30.0, repeats: true) { [weak self] _ in
            self?.sendPing()
        }
    }
    
    private func stopHeartbeat() {
        heartbeatTimer?.invalidate()
        heartbeatTimer = nil
    }
    
    private func sendPing() {
        let pingMessage = ["type": "ping"]
        sendWebSocketMessage(pingMessage)
    }
    
    private func sendWebSocketMessage(_ message: [String: Any]) {
        guard let data = try? JSONSerialization.data(withJSONObject: message),
              let string = String(data: data, encoding: .utf8) else { return }
        
        webSocketTask?.send(.string(string)) { error in
            if let error = error {
                print("WebSocket send error: \(error)")
            }
        }
    }
    
    // MARK: - API調用
    
    /// 獲取機器人狀態
    func getRobotStatus() -> AnyPublisher<RobotStatusResponse, APIError> {
        return request(endpoint: "/api/status", method: "GET")
    }
    
    /// 上傳地圖
    func uploadMap(_ mapData: Data, completion: @escaping (Bool) -> Void) {
        guard let url = URL(string: "\(baseURL)/api/maps/upload") else {
            completion(false)
            return
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/octet-stream", forHTTPHeaderField: "Content-Type")
        request.httpBody = mapData
        
        let task = session.dataTask(with: request) { data, response, error in
            if let error = error {
                print("Map upload error: \(error)")
                completion(false)
                return
            }
            
            if let httpResponse = response as? HTTPURLResponse {
                completion(httpResponse.statusCode == 200)
            } else {
                completion(false)
            }
        }
        
        task.resume()
    }
    
    /// 設置導航目標
    func setNavigationGoal(x: Double, y: Double) -> AnyPublisher<APIResponse, APIError> {
        let body = ["x": x, "y": y]
        return request(endpoint: "/api/navigation/goal", method: "POST", body: body)
    }
    
    /// 停止機器人
    func stopRobot() -> AnyPublisher<APIResponse, APIError> {
        return request(endpoint: "/api/control/stop", method: "POST")
    }
    
    /// 緊急停止
    func emergencyStop() -> AnyPublisher<APIResponse, APIError> {
        return request(endpoint: "/api/control/emergency_stop", method: "POST")
    }
    
    /// 重置緊急停止
    func resetEmergencyStop() -> AnyPublisher<APIResponse, APIError> {
        return request(endpoint: "/api/control/reset_emergency", method: "POST")
    }
    
    /// 手動控制
    func manualControl(linear: Double, angular: Double, duration: Double = 0) -> AnyPublisher<APIResponse, APIError> {
        let body = [
            "linear_speed": linear,
            "angular_speed": angular,
            "duration": duration
        ]
        return request(endpoint: "/api/control/manual", method: "POST", body: body)
    }
    
    /// 獲取感測器數據
    func getSensorData() -> AnyPublisher<SensorDataResponse, APIError> {
        return request(endpoint: "/api/sensors/distances", method: "GET")
    }
    
    /// 獲取視覺流
    func getVisionStream() -> AnyPublisher<VisionStreamResponse, APIError> {
        return request(endpoint: "/api/vision/stream", method: "GET")
    }
    
    // MARK: - 通用請求方法
    
    private func request<T: Codable>(
        endpoint: String,
        method: String,
        body: [String: Any]? = nil
    ) -> AnyPublisher<T, APIError> {
        
        guard let url = URL(string: baseURL + endpoint) else {
            return Fail(error: APIError.invalidURL)
                .eraseToAnyPublisher()
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        if let body = body {
            do {
                request.httpBody = try JSONSerialization.data(withJSONObject: body)
            } catch {
                return Fail(error: APIError.encodingError)
                    .eraseToAnyPublisher()
            }
        }
        
        return session.dataTaskPublisher(for: request)
            .map(\.data)
            .decode(type: T.self, decoder: JSONDecoder())
            .mapError { error in
                if error is DecodingError {
                    return APIError.decodingError
                } else {
                    return APIError.networkError(error)
                }
            }
            .receive(on: DispatchQueue.main)
            .eraseToAnyPublisher()
    }
}

// MARK: - 數據模型

struct RobotStatusResponse: Codable {
    let timestamp: Double
    let system: SystemStatus
    let motor: MotorStatus?
    let sensors: SensorStatus?
    let vision: VisionStatus?
    let navigation: NavigationStatus?
    
    struct SystemStatus: Codable {
        let isRunning: Bool
        let mainLoopInterval: Double
        
        enum CodingKeys: String, CodingKey {
            case isRunning = "is_running"
            case mainLoopInterval = "main_loop_interval"
        }
    }
    
    struct MotorStatus: Codable {
        let leftMotor: MotorInfo
        let rightMotor: MotorInfo
        let isMoving: Bool
        let emergencyStop: Bool
        let pose: Pose
        
        enum CodingKeys: String, CodingKey {
            case leftMotor = "left_motor"
            case rightMotor = "right_motor"
            case isMoving = "is_moving"
            case emergencyStop = "emergency_stop"
            case pose
        }
        
        struct MotorInfo: Codable {
            let speed: Double
            let direction: String
        }
        
        struct Pose: Codable {
            let x: Double
            let y: Double
            let theta: Double
            let linearVelocity: Double
            let angularVelocity: Double
            
            enum CodingKeys: String, CodingKey {
                case x, y, theta
                case linearVelocity = "linear_velocity"
                case angularVelocity = "angular_velocity"
            }
        }
    }
    
    struct SensorStatus: Codable {
        let ultrasonic: [String: UltrasonicInfo]
        let imu: IMUInfo?
        let consecutiveFailures: Int
        let lastUpdate: Double?
        
        enum CodingKeys: String, CodingKey {
            case ultrasonic, imu
            case consecutiveFailures = "consecutive_failures"
            case lastUpdate = "last_update"
        }
        
        struct UltrasonicInfo: Codable {
            let available: Bool
            let lastDistance: Double?
            
            enum CodingKeys: String, CodingKey {
                case available
                case lastDistance = "last_distance"
            }
        }
        
        struct IMUInfo: Codable {
            let available: Bool
            let lastReading: Reading?
            
            enum CodingKeys: String, CodingKey {
                case available
                case lastReading = "last_reading"
            }
            
            struct Reading: Codable {
                let acceleration: [Double]?
                let gyroscope: [Double]?
                let temperature: Double?
            }
        }
    }
    
    struct VisionStatus: Codable {
        let camera: CameraInfo
        let detector: DetectorInfo
        let lastDetections: Int
        let lastObstacles: Int
        let lastProcessingTime: Double
        
        enum CodingKeys: String, CodingKey {
            case camera, detector
            case lastDetections = "last_detections"
            case lastObstacles = "last_obstacles"
            case lastProcessingTime = "last_processing_time"
        }
        
        struct CameraInfo: Codable {
            let isOpened: Bool
            let resolution: String
            let fps: Int
            
            enum CodingKeys: String, CodingKey {
                case isOpened = "is_opened"
                case resolution, fps
            }
        }
        
        struct DetectorInfo: Codable {
            let isLoaded: Bool
            let modelPath: String
            let confidenceThreshold: Double
            
            enum CodingKeys: String, CodingKey {
                case isLoaded = "is_loaded"
                case modelPath = "model_path"
                case confidenceThreshold = "confidence_threshold"
            }
        }
    }
    
    struct NavigationStatus: Codable {
        let state: String
        let currentPosition: Position
        let currentGoal: Position?
        let pathProgress: PathProgress
        let obstacles: Int
        let grid: GridInfo
        
        enum CodingKeys: String, CodingKey {
            case state
            case currentPosition = "current_position"
            case currentGoal = "current_goal"
            case pathProgress = "path_progress"
            case obstacles, grid
        }
        
        struct Position: Codable {
            let x: Double
            let y: Double
            let theta: Double?
        }
        
        struct PathProgress: Codable {
            let totalPoints: Int
            let currentIndex: Int
            let progress: Double
            
            enum CodingKeys: String, CodingKey {
                case totalPoints = "total_points"
                case currentIndex = "current_index"
                case progress
            }
        }
        
        struct GridInfo: Codable {
            let width: Int
            let height: Int
            let resolution: Double
        }
    }
}

struct APIResponse: Codable {
    let success: Bool
    let message: String?
}

struct SensorDataResponse: Codable {
    let distances: [String: Double]
    let timestamp: Double
}

struct VisionStreamResponse: Codable {
    let image: String
    let timestamp: Double
    let detections: Int
    let obstacles: Int
    let processingTime: Double
    
    enum CodingKeys: String, CodingKey {
        case image, timestamp, detections, obstacles
        case processingTime = "processing_time"
    }
}

// MARK: - 錯誤類型

enum APIError: Error, LocalizedError {
    case invalidURL
    case networkError(Error)
    case encodingError
    case decodingError
    case serverError(Int)
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "無效的URL"
        case .networkError(let error):
            return "網路錯誤: \(error.localizedDescription)"
        case .encodingError:
            return "數據編碼錯誤"
        case .decodingError:
            return "數據解碼錯誤"
        case .serverError(let code):
            return "服務器錯誤: \(code)"
        }
    }
}

// MARK: - 通知名稱

extension Notification.Name {
    static let robotStatusUpdated = Notification.Name("robotStatusUpdated")
    static let robotConnectionChanged = Notification.Name("robotConnectionChanged")
} 