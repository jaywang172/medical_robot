import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0
    @State private var robotConnection = RobotConnectionManager()
    
    var body: some View {
        TabView(selection: $selectedTab) {
            // LiDAR掃描頁面
            LiDARScanView(robotConnection: robotConnection)
                .tabItem {
                    Image(systemName: "camera.metering.spot")
                    Text("LiDAR掃描")
                }
                .tag(0)
            
            // 地圖管理頁面
            MapLibraryView(robotConnection: robotConnection)
                .tabItem {
                    Image(systemName: "map")
                    Text("地圖庫")
                }
                .tag(1)
            
            // 機器人控制頁面
            RobotControlView(robotConnection: robotConnection)
                .tabItem {
                    Image(systemName: "gearshape.2")
                    Text("機器人控制")
                }
                .tag(2)
            
            // 設置頁面
            SettingsView(robotConnection: robotConnection)
                .tabItem {
                    Image(systemName: "gear")
                    Text("設置")
                }
                .tag(3)
        }
        .onAppear {
            setupAppearance()
        }
    }
    
    private func setupAppearance() {
        // 設置Tab Bar外觀
        let appearance = UITabBarAppearance()
        appearance.configureWithOpaqueBackground()
        appearance.backgroundColor = UIColor.systemBackground
        
        UITabBar.appearance().standardAppearance = appearance
        UITabBar.appearance().scrollEdgeAppearance = appearance
    }
}

// MARK: - Map Library View
struct MapLibraryView: View {
    @ObservedObject var robotConnection: RobotConnectionManager
    @State private var savedMaps: [SavedMap] = []
    @State private var showingUploadAlert = false
    @State private var uploadProgress: Double = 0
    
    var body: some View {
        NavigationView {
            List {
                Section("已保存的地圖") {
                    if savedMaps.isEmpty {
                        Text("尚未保存任何地圖")
                            .foregroundColor(.secondary)
                            .frame(maxWidth: .infinity, alignment: .center)
                            .padding()
                    } else {
                        ForEach(savedMaps) { map in
                            MapRowView(map: map, robotConnection: robotConnection)
                        }
                        .onDelete(perform: deleteMaps)
                    }
                }
            }
            .navigationTitle("地圖庫")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("重新載入") {
                        loadSavedMaps()
                    }
                }
            }
            .onAppear {
                loadSavedMaps()
            }
        }
    }
    
    private func loadSavedMaps() {
        // 從本地存儲載入保存的地圖
        savedMaps = MapDataManager.shared.getSavedMaps()
    }
    
    private func deleteMaps(at offsets: IndexSet) {
        for index in offsets {
            MapDataManager.shared.deleteMap(savedMaps[index])
        }
        savedMaps.remove(atOffsets: offsets)
    }
}

// MARK: - Robot Control View
struct RobotControlView: View {
    @ObservedObject var robotConnection: RobotConnectionManager
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // 連接狀態
                ConnectionStatusCard(robotConnection: robotConnection)
                
                // 機器人狀態
                if robotConnection.isConnected {
                    RobotStatusCard(robotConnection: robotConnection)
                    
                    // 控制按鈕
                    ControlButtonsView(robotConnection: robotConnection)
                }
                
                Spacer()
            }
            .padding()
            .navigationTitle("機器人控制")
        }
    }
}

// MARK: - Settings View
struct SettingsView: View {
    @ObservedObject var robotConnection: RobotConnectionManager
    @AppStorage("robotServerURL") private var robotServerURL = "http://192.168.1.100:8000"
    @AppStorage("autoUploadMaps") private var autoUploadMaps = true
    @AppStorage("scanQuality") private var scanQuality = "medium"
    
    let scanQualities = ["low", "medium", "high"]
    
    var body: some View {
        NavigationView {
            Form {
                Section("機器人連接") {
                    HStack {
                        Text("服務器地址")
                        Spacer()
                        TextField("IP地址:端口", text: $robotServerURL)
                            .textFieldStyle(RoundedBorderTextFieldStyle())
                            .frame(width: 200)
                    }
                    
                    Button(robotConnection.isConnected ? "斷開連接" : "連接機器人") {
                        if robotConnection.isConnected {
                            robotConnection.disconnect()
                        } else {
                            robotConnection.connect(to: robotServerURL)
                        }
                    }
                    .foregroundColor(robotConnection.isConnected ? .red : .blue)
                }
                
                Section("掃描設置") {
                    Picker("掃描品質", selection: $scanQuality) {
                        ForEach(scanQualities, id: \.self) { quality in
                            Text(quality.capitalized).tag(quality)
                        }
                    }
                    
                    Toggle("自動上傳地圖", isOn: $autoUploadMaps)
                }
                
                Section("應用信息") {
                    HStack {
                        Text("版本")
                        Spacer()
                        Text("1.0.0")
                            .foregroundColor(.secondary)
                    }
                    
                    HStack {
                        Text("LiDAR支持")
                        Spacer()
                        Text(ARWorldTrackingConfiguration.supportsSceneReconstruction(.mesh) ? "支持" : "不支持")
                            .foregroundColor(ARWorldTrackingConfiguration.supportsSceneReconstruction(.mesh) ? .green : .red)
                    }
                }
            }
            .navigationTitle("設置")
        }
    }
}

// MARK: - Helper Views

struct ConnectionStatusCard: View {
    @ObservedObject var robotConnection: RobotConnectionManager
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: robotConnection.isConnected ? "wifi" : "wifi.slash")
                    .foregroundColor(robotConnection.isConnected ? .green : .red)
                Text("連接狀態")
                    .font(.headline)
                Spacer()
                Text(robotConnection.isConnected ? "已連接" : "未連接")
                    .foregroundColor(robotConnection.isConnected ? .green : .red)
            }
            
            if let error = robotConnection.lastError {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(10)
    }
}

struct RobotStatusCard: View {
    @ObservedObject var robotConnection: RobotConnectionManager
    
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("機器人狀態")
                .font(.headline)
            
            if let status = robotConnection.robotStatus {
                HStack {
                    VStack(alignment: .leading) {
                        Text("系統運行: \(status.system.isRunning ? "是" : "否")")
                        Text("緊急停止: \(status.motor?.emergencyStop ?? false ? "是" : "否")")
                            .foregroundColor((status.motor?.emergencyStop ?? false) ? .red : .green)
                    }
                    Spacer()
                    VStack(alignment: .trailing) {
                        Text("位置: (\(String(format: "%.2f", status.motor?.pose.x ?? 0)), \(String(format: "%.2f", status.motor?.pose.y ?? 0)))")
                        Text("速度: \(String(format: "%.2f", status.motor?.pose.linearVelocity ?? 0)) m/s")
                    }
                }
                .font(.caption)
            }
        }
        .padding()
        .background(Color(.systemGray6))
        .cornerRadius(10)
    }
}

struct ControlButtonsView: View {
    @ObservedObject var robotConnection: RobotConnectionManager
    
    var body: some View {
        VStack(spacing: 15) {
            Text("機器人控制")
                .font(.headline)
            
            HStack(spacing: 20) {
                Button("停止") {
                    robotConnection.sendStopCommand()
                }
                .buttonStyle(ControlButtonStyle(color: .red))
                
                Button("緊急停止") {
                    robotConnection.sendEmergencyStop()
                }
                .buttonStyle(ControlButtonStyle(color: .orange))
            }
            
            if robotConnection.robotStatus?.motor?.emergencyStop == true {
                Button("重置緊急停止") {
                    robotConnection.resetEmergencyStop()
                }
                .buttonStyle(ControlButtonStyle(color: .green))
            }
        }
    }
}

struct ControlButtonStyle: ButtonStyle {
    let color: Color
    
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .foregroundColor(.white)
            .padding(.horizontal, 20)
            .padding(.vertical, 10)
            .background(color)
            .cornerRadius(8)
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
    }
}

// MARK: - Supporting Types

import ARKit

// 在其他文件中定義的類型引用
class RobotConnectionManager: ObservableObject {
    @Published var isConnected = false
    @Published var lastError: String?
    @Published var robotStatus: RobotStatus?
    
    func connect(to url: String) {
        // 實現連接邏輯
    }
    
    func disconnect() {
        // 實現斷開連接邏輯
    }
    
    func sendStopCommand() {
        // 發送停止命令
    }
    
    func sendEmergencyStop() {
        // 發送緊急停止命令
    }
    
    func resetEmergencyStop() {
        // 重置緊急停止
    }
}

struct RobotStatus {
    let system: SystemStatus
    let motor: MotorStatus?
    
    struct SystemStatus {
        let isRunning: Bool
    }
    
    struct MotorStatus {
        let emergencyStop: Bool
        let pose: Pose
        
        struct Pose {
            let x: Double
            let y: Double
            let linearVelocity: Double
        }
    }
}

struct SavedMap: Identifiable {
    let id = UUID()
    let name: String
    let date: Date
    let preview: UIImage?
    let fileURL: URL
}

struct MapRowView: View {
    let map: SavedMap
    let robotConnection: RobotConnectionManager
    
    var body: some View {
        HStack {
            // 地圖預覽縮圖
            if let preview = map.preview {
                Image(uiImage: preview)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(width: 60, height: 60)
                    .cornerRadius(8)
            } else {
                Rectangle()
                    .fill(Color.gray.opacity(0.3))
                    .frame(width: 60, height: 60)
                    .cornerRadius(8)
            }
            
            VStack(alignment: .leading) {
                Text(map.name)
                    .font(.headline)
                Text(map.date, style: .date)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            Button("上傳") {
                uploadMap(map)
            }
            .buttonStyle(.bordered)
            .disabled(!robotConnection.isConnected)
        }
    }
    
    private func uploadMap(_ map: SavedMap) {
        // 實現地圖上傳邏輯
    }
}

class MapDataManager {
    static let shared = MapDataManager()
    
    func getSavedMaps() -> [SavedMap] {
        // 實現獲取保存地圖的邏輯
        return []
    }
    
    func deleteMap(_ map: SavedMap) {
        // 實現刪除地圖的邏輯
    }
    
    func saveMap(_ mapData: Data, name: String, preview: UIImage?) -> SavedMap? {
        // 實現保存地圖的邏輯
        return nil
    }
}

#Preview {
    ContentView()
} 