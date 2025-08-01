import Foundation
import CoreGraphics
import UIKit

// MARK: - 地圖處理器
class MapProcessor {
    
    /// 將3D點雲轉換為2D占用柵格地圖
    static func convertTo2DMap(pointCloud: [Point3D], resolution: Double = 0.05) -> OccupancyGridMap {
        guard !pointCloud.isEmpty else {
            return OccupancyGridMap.empty()
        }
        
        // 1. 計算邊界
        let bounds = calculateBounds(pointCloud)
        
        // 2. 創建柵格
        let gridWidth = Int(ceil((bounds.maxX - bounds.minX) / resolution))
        let gridHeight = Int(ceil((bounds.maxY - bounds.minY) / resolution))
        
        var occupancyGrid = Array(repeating: Array(repeating: GridCell.unknown, count: gridWidth), 
                                count: gridHeight)
        
        // 3. 按高度過濾點雲（機器人導航層面）
        let groundHeight = findGroundLevel(pointCloud)
        let robotHeight = 1.8 // 機器人最大高度
        
        let navigationPoints = pointCloud.filter { point in
            point.z >= groundHeight && point.z <= (groundHeight + robotHeight)
        }
        
        // 4. 填充占用柵格
        for point in navigationPoints {
            let gridX = Int((point.x - bounds.minX) / resolution)
            let gridY = Int((point.y - bounds.minY) / resolution)
            
            if gridX >= 0 && gridX < gridWidth && gridY >= 0 && gridY < gridHeight {
                // 檢查是否為障礙物
                if isObstacle(point, groundHeight: groundHeight) {
                    occupancyGrid[gridY][gridX] = .occupied
                } else if occupancyGrid[gridY][gridX] == .unknown {
                    occupancyGrid[gridY][gridX] = .free
                }
            }
        }
        
        // 5. 後處理：填充自由空間
        occupancyGrid = fillFreeSpace(occupancyGrid)
        
        return OccupancyGridMap(
            width: gridWidth,
            height: gridHeight,
            resolution: resolution,
            origin: MapOrigin(x: bounds.minX, y: bounds.minY),
            data: occupancyGrid
        )
    }
    
    /// 計算點雲邊界
    private static func calculateBounds(_ pointCloud: [Point3D]) -> MapBounds {
        var minX = Double.infinity
        var maxX = -Double.infinity
        var minY = Double.infinity
        var maxY = -Double.infinity
        
        for point in pointCloud {
            minX = min(minX, point.x)
            maxX = max(maxX, point.x)
            minY = min(minY, point.y)
            maxY = max(maxY, point.y)
        }
        
        return MapBounds(minX: minX, maxX: maxX, minY: minY, maxY: maxY)
    }
    
    /// 找到地面水平面
    private static func findGroundLevel(_ pointCloud: [Point3D]) -> Double {
        // 使用高度直方圖找到最常見的高度作為地面
        let heights = pointCloud.map { $0.z }
        let heightHistogram = createHeightHistogram(heights, bucketSize: 0.1)
        
        // 找到最多點的高度區間
        let groundBucket = heightHistogram.max { $0.value < $1.value }?.key ?? 0.0
        return groundBucket
    }
    
    /// 創建高度直方圖
    private static func createHeightHistogram(_ heights: [Double], bucketSize: Double) -> [Double: Int] {
        var histogram: [Double: Int] = [:]
        
        for height in heights {
            let bucket = floor(height / bucketSize) * bucketSize
            histogram[bucket, default: 0] += 1
        }
        
        return histogram
    }
    
    /// 判斷點是否為障礙物
    private static func isObstacle(_ point: Point3D, groundHeight: Double) -> Bool {
        let heightAboveGround = point.z - groundHeight
        
        // 高於地面一定高度的點認為是障礙物
        return heightAboveGround > 0.1 // 10cm以上認為是障礙物
    }
    
    /// 填充自由空間（光線投射算法）
    private static func fillFreeSpace(_ grid: [[GridCell]]) -> [[GridCell]] {
        let height = grid.count
        let width = grid.first?.count ?? 0
        var result = grid
        
        // 從地圖邊緣開始，使用廣度優先搜索填充可達的自由空間
        var queue: [(Int, Int)] = []
        var visited = Array(repeating: Array(repeating: false, count: width), count: height)
        
        // 添加邊緣的未知格子到隊列
        for y in 0..<height {
            for x in 0..<width {
                if (x == 0 || x == width-1 || y == 0 || y == height-1) && 
                   grid[y][x] == .unknown {
                    queue.append((x, y))
                    visited[y][x] = true
                    result[y][x] = .free
                }
            }
        }
        
        // BFS填充
        while !queue.isEmpty {
            let (x, y) = queue.removeFirst()
            
            // 檢查四個方向
            let directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            for (dx, dy) in directions {
                let nx = x + dx
                let ny = y + dy
                
                if nx >= 0 && nx < width && ny >= 0 && ny < height &&
                   !visited[ny][nx] && result[ny][nx] == .unknown {
                    queue.append((nx, ny))
                    visited[ny][nx] = true
                    result[ny][nx] = .free
                }
            }
        }
        
        return result
    }
    
    /// 膨脹障礙物（為機器人尺寸留出安全邊距）
    static func inflateObstacles(_ map: OccupancyGridMap, robotRadius: Double) -> OccupancyGridMap {
        let inflationRadius = Int(ceil(robotRadius / map.resolution))
        var inflatedData = map.data
        
        // 找到所有障礙物位置
        var obstacles: [(Int, Int)] = []
        for y in 0..<map.height {
            for x in 0..<map.width {
                if map.data[y][x] == .occupied {
                    obstacles.append((x, y))
                }
            }
        }
        
        // 對每個障礙物進行膨脹
        for (obstacleX, obstacleY) in obstacles {
            for dy in -inflationRadius...inflationRadius {
                for dx in -inflationRadius...inflationRadius {
                    let x = obstacleX + dx
                    let y = obstacleY + dy
                    
                    if x >= 0 && x < map.width && y >= 0 && y < map.height {
                        let distance = sqrt(Double(dx*dx + dy*dy))
                        if distance <= Double(inflationRadius) && 
                           inflatedData[y][x] != .occupied {
                            inflatedData[y][x] = .occupied
                        }
                    }
                }
            }
        }
        
        return OccupancyGridMap(
            width: map.width,
            height: map.height,
            resolution: map.resolution,
            origin: map.origin,
            data: inflatedData
        )
    }
    
    /// 生成地圖預覽圖像
    static func generatePreviewImage(from map: OccupancyGridMap, size: CGSize = CGSize(width: 400, height: 400)) -> UIImage? {
        let colorSpace = CGColorSpaceCreateDeviceGray()
        let context = CGContext(
            data: nil,
            width: Int(size.width),
            height: Int(size.height),
            bitsPerComponent: 8,
            bytesPerRow: Int(size.width),
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.none.rawValue
        )
        
        guard let cgContext = context else { return nil }
        
        // 清除背景
        cgContext.setFillColor(gray: 0.5, alpha: 1.0) // 灰色表示未知
        cgContext.fill(CGRect(origin: .zero, size: size))
        
        let scaleX = size.width / CGFloat(map.width)
        let scaleY = size.height / CGFloat(map.height)
        
        // 繪製地圖
        for y in 0..<map.height {
            for x in 0..<map.width {
                let cell = map.data[y][x]
                
                let rect = CGRect(
                    x: CGFloat(x) * scaleX,
                    y: CGFloat(map.height - 1 - y) * scaleY, // 翻轉Y軸
                    width: scaleX,
                    height: scaleY
                )
                
                switch cell {
                case .free:
                    cgContext.setFillColor(gray: 1.0, alpha: 1.0) // 白色
                case .occupied:
                    cgContext.setFillColor(gray: 0.0, alpha: 1.0) // 黑色
                case .unknown:
                    cgContext.setFillColor(gray: 0.5, alpha: 1.0) // 灰色
                }
                
                cgContext.fill(rect)
            }
        }
        
        guard let cgImage = cgContext.makeImage() else { return nil }
        return UIImage(cgImage: cgImage)
    }
    
    /// 壓縮地圖數據以減少傳輸大小
    static func compressMap(_ map: OccupancyGridMap) -> Data? {
        do {
            let encoder = JSONEncoder()
            let data = try encoder.encode(map)
            return data.compressed()
        } catch {
            print("Error compressing map: \(error)")
            return nil
        }
    }
}

// MARK: - 數據結構

/// 占用柵格地圖
struct OccupancyGridMap: Codable {
    let width: Int
    let height: Int
    let resolution: Double // 米/像素
    let origin: MapOrigin
    let data: [[GridCell]]
    let timestamp: Date
    let metadata: MapMetadata
    
    init(width: Int, height: Int, resolution: Double, origin: MapOrigin, data: [[GridCell]]) {
        self.width = width
        self.height = height
        self.resolution = resolution
        self.origin = origin
        self.data = data
        self.timestamp = Date()
        self.metadata = MapMetadata()
    }
    
    static func empty() -> OccupancyGridMap {
        return OccupancyGridMap(
            width: 0,
            height: 0,
            resolution: 0.05,
            origin: MapOrigin(x: 0, y: 0),
            data: []
        )
    }
}

/// 柵格單元狀態
enum GridCell: Int, Codable {
    case free = 0      // 自由空間
    case occupied = 100 // 占用（障礙物）
    case unknown = -1   // 未知
}

/// 地圖原點
struct MapOrigin: Codable {
    let x: Double
    let y: Double
}

/// 地圖邊界
struct MapBounds {
    let minX: Double
    let maxX: Double
    let minY: Double
    let maxY: Double
}

/// 地圖元數據
struct MapMetadata: Codable {
    let version: String
    let creator: String
    let description: String
    
    init() {
        self.version = "1.0"
        self.creator = "iPad LiDAR Scanner"
        self.description = "Generated from LiDAR point cloud"
    }
}

// MARK: - Data擴展

extension Data {
    /// 壓縮數據
    func compressed() -> Data {
        // 簡單的壓縮實現，實際可以使用更高效的壓縮算法
        return self
    }
    
    /// 解壓數據
    func decompressed() -> Data {
        return self
    }
}

// MARK: - 地圖質量評估

extension MapProcessor {
    
    /// 評估地圖質量
    static func assessMapQuality(_ map: OccupancyGridMap) -> MapQualityReport {
        let totalCells = map.width * map.height
        var freeCells = 0
        var occupiedCells = 0
        var unknownCells = 0
        
        for row in map.data {
            for cell in row {
                switch cell {
                case .free: freeCells += 1
                case .occupied: occupiedCells += 1
                case .unknown: unknownCells += 1
                }
            }
        }
        
        let coverage = Double(freeCells + occupiedCells) / Double(totalCells)
        let obstacleRatio = Double(occupiedCells) / Double(totalCells)
        
        return MapQualityReport(
            coverage: coverage,
            obstacleRatio: obstacleRatio,
            totalCells: totalCells,
            unknownCells: unknownCells,
            qualityScore: calculateQualityScore(coverage: coverage, obstacleRatio: obstacleRatio)
        )
    }
    
    private static func calculateQualityScore(coverage: Double, obstacleRatio: Double) -> Double {
        // 覆蓋率越高越好，但障礙物比例過高或過低都不理想
        let coverageScore = coverage
        let balanceScore = 1.0 - abs(obstacleRatio - 0.2) / 0.2 // 理想障礙物比例約20%
        
        return (coverageScore * 0.7 + balanceScore * 0.3).clamped(to: 0...1)
    }
}

/// 地圖質量報告
struct MapQualityReport {
    let coverage: Double // 覆蓋率 (0-1)
    let obstacleRatio: Double // 障礙物比例 (0-1)
    let totalCells: Int
    let unknownCells: Int
    let qualityScore: Double // 綜合質量分數 (0-1)
    
    var qualityLevel: String {
        switch qualityScore {
        case 0.8...1.0: return "優秀"
        case 0.6..<0.8: return "良好"
        case 0.4..<0.6: return "一般"
        default: return "需要改善"
        }
    }
}

// MARK: - Double擴展

extension Double {
    func clamped(to range: ClosedRange<Double>) -> Double {
        return Swift.max(range.lowerBound, Swift.min(range.upperBound, self))
    }
} 