import SwiftUI
import ARKit
import RealityKit
import SceneKit

struct LiDARScanView: View {
    @ObservedObject var robotConnection: RobotConnectionManager
    @StateObject private var arViewModel = ARScanViewModel()
    @State private var showingSaveDialog = false
    @State private var mapName = ""
    @State private var showingAlert = false
    @State private var alertMessage = ""
    
    var body: some View {
        ZStack {
            // AR視圖
            ARScanViewRepresentable(viewModel: arViewModel)
                .ignoresSafeArea()
            
            // 覆蓋層UI
            VStack {
                // 頂部狀態欄
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("LiDAR掃描")
                            .font(.headline)
                            .foregroundColor(.white)
                        
                        Text(arViewModel.scanningState.description)
                            .font(.caption)
                            .foregroundColor(.white.opacity(0.8))
                        
                        if arViewModel.isScanning {
                            Text("點數: \(arViewModel.pointCount)")
                                .font(.caption)
                                .foregroundColor(.white.opacity(0.8))
                        }
                    }
                    
                    Spacer()
                    
                    // LiDAR可用性指示器
                    VStack {
                        Image(systemName: arViewModel.isLiDARAvailable ? "camera.metering.spot" : "camera.metering.unknown")
                            .foregroundColor(arViewModel.isLiDARAvailable ? .green : .red)
                        Text(arViewModel.isLiDARAvailable ? "LiDAR" : "不可用")
                            .font(.caption)
                            .foregroundColor(.white)
                    }
                }
                .padding()
                .background(Color.black.opacity(0.7))
                .cornerRadius(10)
                .padding()
                
                Spacer()
                
                // 底部控制按鈕
                HStack(spacing: 20) {
                    // 開始/停止掃描按鈕
                    Button(action: {
                        if arViewModel.isScanning {
                            arViewModel.stopScanning()
                        } else {
                            arViewModel.startScanning()
                        }
                    }) {
                        VStack {
                            Image(systemName: arViewModel.isScanning ? "stop.circle.fill" : "play.circle.fill")
                                .font(.system(size: 50))
                            Text(arViewModel.isScanning ? "停止" : "開始")
                                .font(.caption)
                        }
                        .foregroundColor(arViewModel.isScanning ? .red : .green)
                    }
                    .disabled(!arViewModel.isLiDARAvailable)
                    
                    // 重置按鈕
                    Button(action: {
                        arViewModel.resetSession()
                    }) {
                        VStack {
                            Image(systemName: "arrow.clockwise.circle.fill")
                                .font(.system(size: 40))
                            Text("重置")
                                .font(.caption)
                        }
                        .foregroundColor(.orange)
                    }
                    
                    // 保存按鈕
                    Button(action: {
                        if arViewModel.hasScannedData {
                            showingSaveDialog = true
                        }
                    }) {
                        VStack {
                            Image(systemName: "square.and.arrow.down.fill")
                                .font(.system(size: 40))
                            Text("保存")
                                .font(.caption)
                        }
                        .foregroundColor(.blue)
                    }
                    .disabled(!arViewModel.hasScannedData)
                    
                    // 上傳按鈕
                    Button(action: {
                        uploadCurrentMap()
                    }) {
                        VStack {
                            Image(systemName: "icloud.and.arrow.up.fill")
                                .font(.system(size: 40))
                            Text("上傳")
                                .font(.caption)
                        }
                        .foregroundColor(.purple)
                    }
                    .disabled(!arViewModel.hasScannedData || !robotConnection.isConnected)
                }
                .padding()
                .background(Color.black.opacity(0.7))
                .cornerRadius(15)
                .padding()
            }
        }
        .alert("保存地圖", isPresented: $showingSaveDialog) {
            TextField("地圖名稱", text: $mapName)
            Button("取消", role: .cancel) { }
            Button("保存") {
                saveMap()
            }
        } message: {
            Text("請輸入地圖名稱")
        }
        .alert("提示", isPresented: $showingAlert) {
            Button("確定") { }
        } message: {
            Text(alertMessage)
        }
        .onAppear {
            arViewModel.startARSession()
        }
        .onDisappear {
            arViewModel.stopARSession()
        }
    }
    
    private func saveMap() {
        Task {
            let success = await arViewModel.saveMap(name: mapName)
            DispatchQueue.main.async {
                if success {
                    alertMessage = "地圖已成功保存"
                    mapName = ""
                } else {
                    alertMessage = "保存地圖失敗"
                }
                showingAlert = true
            }
        }
    }
    
    private func uploadCurrentMap() {
        Task {
            let success = await arViewModel.uploadMapToRobot(robotConnection: robotConnection)
            DispatchQueue.main.async {
                if success {
                    alertMessage = "地圖已成功上傳到機器人"
                } else {
                    alertMessage = "上傳地圖失敗"
                }
                showingAlert = true
            }
        }
    }
}

// MARK: - AR View Model

class ARScanViewModel: NSObject, ObservableObject {
    @Published var isScanning = false
    @Published var isLiDARAvailable = false
    @Published var scanningState: ScanningState = .idle
    @Published var pointCount = 0
    @Published var hasScannedData = false
    
    private var arView: ARSCNView?
    private var sceneReconstructor: ARSceneReconstructor?
    private var meshAnchors: [ARMeshAnchor] = []
    
    enum ScanningState {
        case idle
        case initializing
        case scanning
        case processing
        case completed
        
        var description: String {
            switch self {
            case .idle: return "準備就緒"
            case .initializing: return "初始化中..."
            case .scanning: return "掃描中..."
            case .processing: return "處理中..."
            case .completed: return "掃描完成"
            }
        }
    }
    
    override init() {
        super.init()
        checkLiDARAvailability()
    }
    
    private func checkLiDARAvailability() {
        isLiDARAvailable = ARWorldTrackingConfiguration.supportsSceneReconstruction(.mesh)
    }
    
    func startARSession() {
        guard isLiDARAvailable else { return }
        scanningState = .initializing
        
        // AR會話將在ARSCNView中配置
    }
    
    func stopARSession() {
        arView?.session.pause()
        scanningState = .idle
        isScanning = false
    }
    
    func startScanning() {
        guard isLiDARAvailable else { return }
        isScanning = true
        scanningState = .scanning
        
        // 配置場景重建
        if let arView = arView {
            let configuration = ARWorldTrackingConfiguration()
            configuration.sceneReconstruction = .mesh
            configuration.environmentTexturing = .automatic
            
            arView.session.run(configuration)
        }
    }
    
    func stopScanning() {
        isScanning = false
        scanningState = .processing
        
        // 處理掃描數據
        processScanData()
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            self.scanningState = .completed
            self.hasScannedData = !self.meshAnchors.isEmpty
        }
    }
    
    func resetSession() {
        meshAnchors.removeAll()
        pointCount = 0
        hasScannedData = false
        scanningState = .idle
        isScanning = false
        
        if let arView = arView {
            let configuration = ARWorldTrackingConfiguration()
            arView.session.run(configuration, options: [.resetTracking, .removeExistingAnchors])
        }
    }
    
    private func processScanData() {
        // 計算點雲數量
        var totalPoints = 0
        for anchor in meshAnchors {
            totalPoints += anchor.geometry.vertices.count
        }
        pointCount = totalPoints
    }
    
    func saveMap(name: String) async -> Bool {
        guard hasScannedData else { return false }
        
        return await withCheckedContinuation { continuation in
            // 轉換為點雲數據
            let mapData = generateMapData()
            
            // 生成預覽圖
            let preview = generatePreviewImage()
            
            // 保存到本地
            if let savedMap = MapDataManager.shared.saveMap(mapData, name: name, preview: preview) {
                continuation.resume(returning: true)
            } else {
                continuation.resume(returning: false)
            }
        }
    }
    
    func uploadMapToRobot(robotConnection: RobotConnectionManager) async -> Bool {
        guard hasScannedData else { return false }
        
        let mapData = generateMapData()
        
        return await withCheckedContinuation { continuation in
            // 使用機器人API上傳地圖
            RobotAPIService.shared.uploadMap(mapData) { success in
                continuation.resume(returning: success)
            }
        }
    }
    
    private func generateMapData() -> Data {
        // 將mesh anchors轉換為標準格式
        var pointCloud: [Point3D] = []
        
        for anchor in meshAnchors {
            let vertices = anchor.geometry.vertices
            let transform = anchor.transform
            
            for i in 0..<vertices.count {
                let vertex = vertices[i]
                let worldPos = transform * SIMD4<Float>(vertex.x, vertex.y, vertex.z, 1.0)
                
                pointCloud.append(Point3D(
                    x: Double(worldPos.x),
                    y: Double(worldPos.y),
                    z: Double(worldPos.z)
                ))
            }
        }
        
        // 轉換為適合機器人的2D地圖格式
        let map2D = MapProcessor.convertTo2DMap(pointCloud: pointCloud)
        
        do {
            return try JSONEncoder().encode(map2D)
        } catch {
            print("Error encoding map data: \(error)")
            return Data()
        }
    }
    
    private func generatePreviewImage() -> UIImage? {
        guard let arView = arView else { return nil }
        
        // 渲染當前AR視圖為圖像
        UIGraphicsBeginImageContextWithOptions(arView.bounds.size, false, UIScreen.main.scale)
        arView.drawHierarchy(in: arView.bounds, afterScreenUpdates: true)
        let image = UIGraphicsGetImageFromCurrentImageContext()
        UIGraphicsEndImageContext()
        
        return image
    }
    
    func setARView(_ arView: ARSCNView) {
        self.arView = arView
    }
    
    func addMeshAnchor(_ anchor: ARMeshAnchor) {
        meshAnchors.append(anchor)
        if isScanning {
            processScanData()
        }
    }
    
    func updateMeshAnchor(_ anchor: ARMeshAnchor) {
        if let index = meshAnchors.firstIndex(where: { $0.identifier == anchor.identifier }) {
            meshAnchors[index] = anchor
            if isScanning {
                processScanData()
            }
        }
    }
    
    func removeMeshAnchor(_ anchor: ARMeshAnchor) {
        meshAnchors.removeAll { $0.identifier == anchor.identifier }
        if isScanning {
            processScanData()
        }
    }
}

// MARK: - AR View Representable

struct ARScanViewRepresentable: UIViewRepresentable {
    @ObservedObject var viewModel: ARScanViewModel
    
    func makeUIView(context: Context) -> ARSCNView {
        let arView = ARSCNView()
        
        arView.delegate = context.coordinator
        arView.session.delegate = context.coordinator
        
        // 配置AR會話
        let configuration = ARWorldTrackingConfiguration()
        arView.session.run(configuration)
        
        // 設置場景
        arView.scene = SCNScene()
        arView.autoenablesDefaultLighting = true
        arView.automaticallyUpdatesLighting = true
        
        viewModel.setARView(arView)
        
        return arView
    }
    
    func updateUIView(_ uiView: ARSCNView, context: Context) {
        // 根據需要更新視圖
    }
    
    func makeCoordinator() -> Coordinator {
        Coordinator(viewModel)
    }
    
    class Coordinator: NSObject, ARSCNViewDelegate, ARSessionDelegate {
        let viewModel: ARScanViewModel
        
        init(_ viewModel: ARScanViewModel) {
            self.viewModel = viewModel
        }
        
        // MARK: - ARSessionDelegate
        
        func session(_ session: ARSession, didAdd anchors: [ARAnchor]) {
            for anchor in anchors {
                if let meshAnchor = anchor as? ARMeshAnchor {
                    viewModel.addMeshAnchor(meshAnchor)
                }
            }
        }
        
        func session(_ session: ARSession, didUpdate anchors: [ARAnchor]) {
            for anchor in anchors {
                if let meshAnchor = anchor as? ARMeshAnchor {
                    viewModel.updateMeshAnchor(meshAnchor)
                }
            }
        }
        
        func session(_ session: ARSession, didRemove anchors: [ARAnchor]) {
            for anchor in anchors {
                if let meshAnchor = anchor as? ARMeshAnchor {
                    viewModel.removeMeshAnchor(meshAnchor)
                }
            }
        }
        
        // MARK: - ARSCNViewDelegate
        
        func renderer(_ renderer: SCNSceneRenderer, nodeFor anchor: ARAnchor) -> SCNNode? {
            guard let meshAnchor = anchor as? ARMeshAnchor else { return nil }
            
            // 創建網格節點用於可視化
            let meshNode = SCNNode()
            
            // 創建幾何體
            let vertices = meshAnchor.geometry.vertices
            let faces = meshAnchor.geometry.faces
            
            let geometry = SCNGeometry.fromARMeshGeometry(meshAnchor.geometry)
            meshNode.geometry = geometry
            
            // 設置材質
            let material = SCNMaterial()
            material.fillMode = .lines
            material.diffuse.contents = UIColor.cyan.withAlphaComponent(0.7)
            geometry?.materials = [material]
            
            return meshNode
        }
        
        func renderer(_ renderer: SCNSceneRenderer, didUpdate node: SCNNode, for anchor: ARAnchor) {
            guard let meshAnchor = anchor as? ARMeshAnchor else { return }
            
            // 更新網格幾何體
            let geometry = SCNGeometry.fromARMeshGeometry(meshAnchor.geometry)
            node.geometry = geometry
        }
    }
}

// MARK: - Supporting Types

struct Point3D: Codable {
    let x: Double
    let y: Double
    let z: Double
}

// SCNGeometry擴展用於從AR網格創建幾何體
extension SCNGeometry {
    static func fromARMeshGeometry(_ geometry: ARMeshGeometry) -> SCNGeometry? {
        let vertices = geometry.vertices
        let faces = geometry.faces
        
        var scnVertices: [SCNVector3] = []
        for i in 0..<vertices.count {
            let vertex = vertices[i]
            scnVertices.append(SCNVector3(vertex.x, vertex.y, vertex.z))
        }
        
        var indices: [Int32] = []
        for i in 0..<faces.count {
            let face = faces[i]
            // 假設是三角形面
            indices.append(Int32(face[0]))
            indices.append(Int32(face[1]))
            indices.append(Int32(face[2]))
        }
        
        let geometrySource = SCNGeometrySource(vertices: scnVertices)
        let geometryElement = SCNGeometryElement(indices: indices, primitiveType: .triangles)
        
        return SCNGeometry(sources: [geometrySource], elements: [geometryElement])
    }
}

#Preview {
    LiDARScanView(robotConnection: RobotConnectionManager())
} 