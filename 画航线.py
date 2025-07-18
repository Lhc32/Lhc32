#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TSSLPT航线规划模块

该模块用于处理TSSLPT（交通分离方案分离线点）数据，生成推荐的船舶航线。
主要功能包括：
1. 计算航段的入口和出口中点
2. 基于航段信息规划完整航线连接
3. 提供优化的路径规划算法

Author: Refactored for better maintainability
"""

import math
from typing import Dict, List, Tuple, Any, Optional, Set


def calculate_angle_between_points(point1: List[float], point2: List[float]) -> float:
    """
    计算两点之间的角度（方位角）
    
    Args:
        point1: 起点坐标 [lon, lat]
        point2: 终点坐标 [lon, lat]
        
    Returns:
        float: 方位角（度数，0-360）
    """
    try:
        lon1, lat1 = point1
        lon2, lat2 = point2
        
        # 转换为弧度
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lon_rad = math.radians(lon2 - lon1)
        
        # 计算方位角
        y = math.sin(delta_lon_rad) * math.cos(lat2_rad)
        x = (math.cos(lat1_rad) * math.sin(lat2_rad) - 
             math.sin(lat1_rad) * math.cos(lat2_rad) * math.cos(delta_lon_rad))
        
        angle_rad = math.atan2(y, x)
        angle_deg = math.degrees(angle_rad)
        
        # 转换为0-360度范围
        return (angle_deg + 360) % 360
    except (ValueError, TypeError) as e:
        raise ValueError(f"计算角度时出错: {e}")


def calculate_distance_between_points(point1: List[float], point2: List[float]) -> float:
    """
    计算两点之间的距离（海里）
    
    Args:
        point1: 起点坐标 [lon, lat]
        point2: 终点坐标 [lon, lat]
        
    Returns:
        float: 距离（海里）
    """
    try:
        lon1, lat1 = point1
        lon2, lat2 = point2
        
        # 地球半径（海里）
        R = 3440.065
        
        # 转换为弧度
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)
        
        # Haversine公式
        a = (math.sin(delta_lat / 2) ** 2 + 
             math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    except (ValueError, TypeError) as e:
        raise ValueError(f"计算距离时出错: {e}")


def calculate_geometric_center(coordinates: List[List[float]]) -> List[float]:
    """
    计算多边形的几何中心
    
    Args:
        coordinates: 坐标点列表 [[lon, lat], ...]
        
    Returns:
        List[float]: 几何中心坐标 [lon, lat]
    """
    if not coordinates:
        raise ValueError("坐标列表不能为空")
    
    try:
        total_lon = sum(coord[0] for coord in coordinates)
        total_lat = sum(coord[1] for coord in coordinates)
        count = len(coordinates)
        
        return [total_lon / count, total_lat / count]
    except (IndexError, TypeError) as e:
        raise ValueError(f"计算几何中心时出错: {e}")


def calculate_midpoint_from_center(center: List[float], coordinates: List[List[float]], 
                                 orient: float, is_entry: bool = True) -> List[float]:
    """
    基于几何中心和方向计算入口或出口中点
    
    Args:
        center: 几何中心坐标 [lon, lat]
        coordinates: 航段坐标列表
        orient: 方向角度
        is_entry: True为入口中点，False为出口中点
        
    Returns:
        List[float]: 中点坐标 [lon, lat]
    """
    try:
        if not coordinates:
            return center.copy()
        
        # 根据方向和入口/出口确定偏移方向
        offset_angle = orient if is_entry else (orient + 180) % 360
        
        # 计算与中心最近和最远的点
        distances = [calculate_distance_between_points(center, coord) for coord in coordinates]
        
        if is_entry:
            # 入口中点：选择与预期方向最接近的点
            target_idx = 0
            min_angle_diff = float('inf')
            for i, coord in enumerate(coordinates):
                angle = calculate_angle_between_points(center, coord)
                angle_diff = abs(angle - offset_angle)
                if angle_diff > 180:
                    angle_diff = 360 - angle_diff
                if angle_diff < min_angle_diff:
                    min_angle_diff = angle_diff
                    target_idx = i
        else:
            # 出口中点：选择距离最远的点
            target_idx = distances.index(max(distances))
        
        return coordinates[target_idx]
    except (IndexError, ValueError) as e:
        # 如果计算失败，返回几何中心
        return center.copy()


def calculate_segment_midpoints(geometries: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    计算TSSLPT航段的入口和出口中点
    
    该函数处理TSSLPT数据，合并指定的RCID组，计算每个航段的几何中心，
    并使用ORIENT方向计算入口和出口中点。
    
    Args:
        geometries: 包含TSSLPT数据的几何对象字典
                   格式: {rcid: {geometry: {...}, properties: {ORIENT: ...}}}
        
    Returns:
        dict: 航段信息字典，格式为 {rcid: {center, coords, orient, entry_mid, exit_mid}}
              - center: 几何中心坐标
              - coords: 原始坐标列表
              - orient: 方向角度
              - entry_mid: 入口中点坐标
              - exit_mid: 出口中点坐标
    
    Raises:
        ValueError: 当输入数据格式不正确时
        KeyError: 当必要的数据字段缺失时
    """
    if not geometries:
        raise ValueError("geometries参数不能为空")
    
    segment_info = {}
    
    try:
        for rcid, geo_data in geometries.items():
            if not isinstance(geo_data, dict):
                continue
                
            # 提取几何坐标
            geometry = geo_data.get('geometry', {})
            coordinates = geometry.get('coordinates', [])
            
            if not coordinates:
                continue
            
            # 扁平化坐标（处理多层嵌套）
            flat_coords = []
            for coord in coordinates:
                if isinstance(coord[0], list):
                    flat_coords.extend(coord)
                else:
                    flat_coords.append(coord)
            
            if len(flat_coords) < 2:
                continue
            
            # 提取方向信息
            properties = geo_data.get('properties', {})
            orient = properties.get('ORIENT', 0)
            
            try:
                orient = float(orient)
            except (ValueError, TypeError):
                orient = 0.0
            
            # 计算几何中心
            center = calculate_geometric_center(flat_coords)
            
            # 计算入口和出口中点
            entry_mid = calculate_midpoint_from_center(center, flat_coords, orient, True)
            exit_mid = calculate_midpoint_from_center(center, flat_coords, orient, False)
            
            # 存储航段信息
            segment_info[rcid] = {
                'center': center,
                'coords': flat_coords,
                'orient': orient,
                'entry_mid': entry_mid,
                'exit_mid': exit_mid,
                'properties': properties
            }
            
    except Exception as e:
        raise ValueError(f"处理TSSLPT数据时出错: {e}")
    
    return segment_info


def is_point_in_segment(point: List[float], segment_coords: List[List[float]], 
                       tolerance: float = 0.01) -> bool:
    """
    判断点是否在航段范围内
    
    Args:
        point: 待检查的点坐标 [lon, lat]
        segment_coords: 航段坐标列表
        tolerance: 容差范围（度）
        
    Returns:
        bool: 如果点在航段内返回True
    """
    try:
        if not segment_coords:
            return False
        
        # 简单的边界框检查
        lons = [coord[0] for coord in segment_coords]
        lats = [coord[1] for coord in segment_coords]
        
        min_lon, max_lon = min(lons) - tolerance, max(lons) + tolerance
        min_lat, max_lat = min(lats) - tolerance, max(lats) + tolerance
        
        return (min_lon <= point[0] <= max_lon and 
                min_lat <= point[1] <= max_lat)
    except (IndexError, TypeError):
        return False


def find_optimal_path(start_point: List[float], end_point: List[float], 
                     available_segments: Dict[str, Dict[str, Any]]) -> Tuple[List[List[float]], Set[str]]:
    """
    寻找从起点到终点的最优路径
    
    Args:
        start_point: 起点坐标
        end_point: 终点坐标
        available_segments: 可用航段信息
        
    Returns:
        Tuple[List[List[float]], Set[str]]: (路径点列表, 使用的航段集合)
    """
    if not available_segments:
        return [start_point, end_point], set()
    
    try:
        route_points = [start_point]
        used_segments = set()
        
        # 简化的路径规划：选择距离起点最近的航段开始
        current_point = start_point
        remaining_segments = available_segments.copy()
        
        while remaining_segments:
            # 找到距离当前点最近的航段
            min_distance = float('inf')
            best_segment_id = None
            best_connection_point = None
            
            for seg_id, seg_info in remaining_segments.items():
                # 计算到入口和出口中点的距离
                entry_dist = calculate_distance_between_points(current_point, seg_info['entry_mid'])
                exit_dist = calculate_distance_between_points(current_point, seg_info['exit_mid'])
                
                if entry_dist < min_distance:
                    min_distance = entry_dist
                    best_segment_id = seg_id
                    best_connection_point = seg_info['entry_mid']
                
                if exit_dist < min_distance:
                    min_distance = exit_dist
                    best_segment_id = seg_id
                    best_connection_point = seg_info['exit_mid']
            
            if best_segment_id is None:
                break
            
            # 添加到路径
            route_points.append(best_connection_point)
            used_segments.add(best_segment_id)
            current_point = best_connection_point
            
            # 移除已使用的航段
            del remaining_segments[best_segment_id]
            
            # 检查是否已经接近终点
            if calculate_distance_between_points(current_point, end_point) < 10:  # 10海里内
                break
        
        # 添加终点
        route_points.append(end_point)
        
        return route_points, used_segments
        
    except Exception as e:
        # 如果路径规划失败，返回直接连接
        return [start_point, end_point], set()


def plan_route_connection(start_point: List[float], end_point: List[float], 
                         segment_centers: Dict[str, Dict[str, Any]]) -> Tuple[List[List[float]], Set[str]]:
    """
    基于航段中点信息规划航线连接
    
    该函数接收起点、终点和航段信息，判断起点和终点是否在航段内，
    使用优化的路径规划算法连接各航段，返回完整的航线点列表。
    
    Args:
        start_point: 起点坐标 [lon, lat]
        end_point: 终点坐标 [lon, lat] 
        segment_centers: 航段信息字典，来自calculate_segment_midpoints的输出
        
    Returns:
        tuple: (route_points, used_segments)
            - route_points: 航线点列表 [[lon, lat], ...]
            - used_segments: 使用的航段集合 {rcid1, rcid2, ...}
    
    Raises:
        ValueError: 当输入参数不正确时
    """
    # 输入验证
    if not start_point or len(start_point) != 2:
        raise ValueError("start_point必须是包含两个元素的列表 [lon, lat]")
    
    if not end_point or len(end_point) != 2:
        raise ValueError("end_point必须是包含两个元素的列表 [lon, lat]")
    
    if not isinstance(segment_centers, dict):
        raise ValueError("segment_centers必须是字典类型")
    
    try:
        # 检查起点和终点是否在任何航段内
        start_in_segment = None
        end_in_segment = None
        
        for rcid, seg_info in segment_centers.items():
            coords = seg_info.get('coords', [])
            
            if is_point_in_segment(start_point, coords):
                start_in_segment = rcid
            
            if is_point_in_segment(end_point, coords):
                end_in_segment = rcid
        
        # 过滤可用的航段
        available_segments = {}
        for rcid, seg_info in segment_centers.items():
            # 确保航段有必要的信息
            if all(key in seg_info for key in ['center', 'entry_mid', 'exit_mid']):
                available_segments[rcid] = seg_info
        
        # 如果起点和终点都在同一航段内，直接连接
        if start_in_segment and start_in_segment == end_in_segment:
            return [start_point, end_point], {start_in_segment}
        
        # 如果没有可用航段，直接连接
        if not available_segments:
            return [start_point, end_point], set()
        
        # 使用路径规划算法找到最优路径
        route_points, used_segments = find_optimal_path(start_point, end_point, available_segments)
        
        return route_points, used_segments
        
    except Exception as e:
        raise ValueError(f"规划航线连接时出错: {e}")


def get_recommended_route_from_tsslpt(geometries: Dict[str, Any], 
                                    start_point: List[float], 
                                    end_point: List[float]) -> Tuple[List[List[float]], Dict[str, Dict[str, Any]]]:
    """
    从TSSLPT数据生成推荐航线（重构版本）
    
    这是主要的函数，它将复杂的路径规划任务分解为两个步骤：
    1. 计算航段中点信息
    2. 基于中点信息规划航线连接
    
    Args:
        geometries: 包含TSSLPT数据的几何对象字典
                   格式: {rcid: {geometry: {...}, properties: {ORIENT: ...}}}
        start_point: 起点坐标 [lon, lat]
        end_point: 终点坐标 [lon, lat]
        
    Returns:
        tuple: (route_points, segment_centers)
            - route_points: 推荐的航线点列表 [[lon, lat], ...]
            - segment_centers: 航段中点信息字典（用于调试和进一步处理）
    
    Raises:
        ValueError: 当输入参数不正确或处理过程中出错时
    
    Example:
        >>> geometries = {
        ...     'RCID_001': {
        ...         'geometry': {'coordinates': [[120.0, 30.0], [120.1, 30.1]]},
        ...         'properties': {'ORIENT': 45}
        ...     }
        ... }
        >>> start = [119.9, 29.9]
        >>> end = [120.2, 30.2]
        >>> route_points, segments = get_recommended_route_from_tsslpt(geometries, start, end)
    """
    try:
        # 步骤1：计算航段中点
        print("正在计算航段中点信息...")
        segment_centers = calculate_segment_midpoints(geometries)
        print(f"成功处理 {len(segment_centers)} 个航段")
        
        # 步骤2：规划航线连接
        print("正在规划航线连接...")
        route_points, used_segments = plan_route_connection(start_point, end_point, segment_centers)
        print(f"航线规划完成，使用了 {len(used_segments)} 个航段")
        
        # 输出统计信息
        total_distance = 0
        for i in range(len(route_points) - 1):
            distance = calculate_distance_between_points(route_points[i], route_points[i + 1])
            total_distance += distance
        
        print(f"总航程: {total_distance:.2f} 海里")
        print(f"航路点数: {len(route_points)}")
        
        return route_points, segment_centers
        
    except Exception as e:
        raise ValueError(f"生成推荐航线时出错: {e}")


# 测试和示例代码
if __name__ == "__main__":
    # 示例TSSLPT数据
    sample_geometries = {
        'RCID_001': {
            'geometry': {
                'coordinates': [[120.0, 30.0], [120.05, 30.05], [120.1, 30.1]]
            },
            'properties': {
                'ORIENT': 45
            }
        },
        'RCID_002': {
            'geometry': {
                'coordinates': [[120.15, 30.15], [120.2, 30.2], [120.25, 30.25]]
            },
            'properties': {
                'ORIENT': 135
            }
        }
    }
    
    # 测试数据
    start_point = [119.95, 29.95]
    end_point = [120.3, 30.3]
    
    try:
        print("=" * 50)
        print("TSSLPT航线规划系统测试")
        print("=" * 50)
        
        # 测试航段中点计算
        print("\n1. 测试航段中点计算:")
        segment_info = calculate_segment_midpoints(sample_geometries)
        for rcid, info in segment_info.items():
            print(f"  {rcid}:")
            print(f"    几何中心: {info['center']}")
            print(f"    方向: {info['orient']}°")
            print(f"    入口中点: {info['entry_mid']}")
            print(f"    出口中点: {info['exit_mid']}")
        
        # 测试完整航线规划
        print("\n2. 测试完整航线规划:")
        route_points, segments = get_recommended_route_from_tsslpt(
            sample_geometries, start_point, end_point
        )
        
        print(f"\n推荐航线点:")
        for i, point in enumerate(route_points):
            print(f"  {i + 1}. [{point[0]:.6f}, {point[1]:.6f}]")
        
        print("\n测试完成！")
        
    except Exception as e:
        print(f"测试失败: {e}")