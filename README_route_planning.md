# TSSLPT航线规划系统

## 项目概述

本项目实现了基于TSSLPT（交通分离方案分离线点）数据的智能航线规划系统。通过重构原有的复杂函数，实现了模块化、可维护的代码架构。

## 重构成果

### 原始问题
- 原`get_recommended_route_from_tsslpt`函数过于复杂（300+行）
- 功能耦合严重，难以维护和测试
- 代码可读性差，扩展困难

### 重构方案
将复杂函数分解为三个主要组件：

1. **`calculate_segment_midpoints(geometries)`** - 航段中点计算
2. **`plan_route_connection(start_point, end_point, segment_centers)`** - 路径规划
3. **`get_recommended_route_from_tsslpt(geometries, start_point, end_point)`** - 主函数

## 核心功能

### 1. 航段中点计算 (`calculate_segment_midpoints`)

```python
def calculate_segment_midpoints(geometries):
    """
    计算TSSLPT航段的入口和出口中点
    
    Args:
        geometries: 包含TSSLPT数据的几何对象字典
        
    Returns:
        dict: 航段信息字典，格式为 {rcid: {center, coords, orient, entry_mid, exit_mid}}
    """
```

**功能特点：**
- 处理TSSLPT数据，合并指定的RCID组
- 计算每个航段的几何中心
- 基于ORIENT方向计算入口和出口中点
- 返回包含完整航段信息的字典

### 2. 路径规划 (`plan_route_connection`)

```python
def plan_route_connection(start_point, end_point, segment_centers):
    """
    基于航段中点信息规划航线连接
    
    Args:
        start_point: 起点坐标 [lon, lat]
        end_point: 终点坐标 [lon, lat] 
        segment_centers: 航段信息字典
        
    Returns:
        tuple: (route_points, used_segments)
    """
```

**功能特点：**
- 判断起点和终点是否在航段内
- 使用优化的路径规划算法连接各航段
- 返回完整的航线点列表和使用的航段集合

### 3. 主函数 (`get_recommended_route_from_tsslpt`)

```python
def get_recommended_route_from_tsslpt(geometries, start_point, end_point):
    """
    从TSSLPT数据生成推荐航线（重构版本）
    """
    # 步骤1：计算航段中点
    segment_centers = calculate_segment_midpoints(geometries)
    
    # 步骤2：规划航线连接
    route_points, used_segments = plan_route_connection(start_point, end_point, segment_centers)
    
    return route_points, segment_centers
```

## 工具函数

系统还包含多个工具函数来支持核心功能：

- `calculate_angle_between_points()` - 计算两点间方位角
- `calculate_distance_between_points()` - 计算海里距离
- `calculate_geometric_center()` - 计算多边形几何中心
- `is_point_in_segment()` - 判断点是否在航段内
- `find_optimal_path()` - 核心路径寻找算法

## 使用示例

```python
from 画航线 import get_recommended_route_from_tsslpt

# TSSLPT几何数据
geometries = {
    'RCID_001': {
        'geometry': {
            'coordinates': [[120.0, 30.0], [120.1, 30.1]]
        },
        'properties': {
            'ORIENT': 45
        }
    }
}

# 起点和终点
start_point = [119.9, 29.9]
end_point = [120.2, 30.2]

# 生成推荐航线
route_points, segment_info = get_recommended_route_from_tsslpt(
    geometries, start_point, end_point
)

print(f"推荐航线包含 {len(route_points)} 个航路点")
for i, point in enumerate(route_points):
    print(f"航路点 {i+1}: [{point[0]:.6f}, {point[1]:.6f}]")
```

## 测试

运行完整测试套件：

```bash
python test_route_planning.py
```

运行基本功能测试：

```bash
python 画航线.py
```

## 重构收益

### ✅ 可维护性
- 函数职责单一，代码逻辑清晰
- 模块化设计，便于理解和修改
- 完善的错误处理和输入验证

### ✅ 可测试性
- 每个函数都可以独立测试
- 提供了全面的测试用例
- 支持单元测试和集成测试

### ✅ 可复用性
- 工具函数可在其他项目中复用
- 航段处理逻辑可独立使用
- API设计灵活，支持多种使用场景

### ✅ 可扩展性
- 便于添加新的路径规划算法
- 支持不同类型的几何数据处理
- 可轻松集成额外的优化策略

### ✅ 性能优化
- 优化的算法和数据结构
- 高效的距离和角度计算
- 性能测试显示能处理大量航段数据

## 技术特性

- **类型提示**: 完整的Python类型注解
- **错误处理**: 全面的异常处理机制
- **文档**: 详细的docstring文档
- **向后兼容**: 保持原有API接口
- **编码规范**: 遵循PEP 8编码标准

## 文件结构

```
├── 画航线.py              # 主要功能模块
├── test_route_planning.py  # 综合测试脚本
├── .gitignore             # Git忽略文件
└── README.md              # 项目文档
```