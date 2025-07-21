#!/usr/bin/env python3
"""
终极启发式J形拼图求解器

实现最先进的启发式函数集合：
1. 多维度评估函数
2. 预测性约束传播
3. 智能回溯策略
4. 自适应搜索参数
5. 形状语义理解
"""

from typing import List, Tuple, Optional, Dict, Set
import time
import math
from dataclasses import dataclass
from collections import defaultdict
import heapq


@dataclass
class HeuristicWeights:
    """启发式权重配置"""
    shape_fitness: float = 2.0
    constraint_propagation: float = 3.0
    deadlock_avoidance: float = 4.0
    connectivity_preservation: float = 2.5
    boundary_utilization: float = 1.0
    spatial_balance: float = 1.5
    future_flexibility: float = 2.0


@dataclass
class PlacementEvaluation:
    """放置评估结果"""
    total_score: float
    shape_fitness: float
    constraint_propagation: float
    deadlock_risk: float
    connectivity: float
    boundary_score: float
    spatial_balance: float
    future_flexibility: float
    
    def __repr__(self):
        return f"Score({self.total_score:.2f})"


class UltimateHeuristicSolver:
    """终极启发式求解器"""
    
    def __init__(self, grid_size: int = 10, piece_count: int = 11):
        self.grid_size = grid_size
        self.piece_count = piece_count
        self.shape_size = 8
        
        # 预计算J形块的所有变体
        self.shapes = self._generate_shape_variants()
        self.shape_signatures = self._compute_shape_signatures()
        
        # 启发式权重（可动态调整）
        self.weights = HeuristicWeights()
        
        # 搜索状态
        self.grid = [[0] * grid_size for _ in range(grid_size)]
        self.nodes = 0
        self.start_time = 0
        self.depth_stats = defaultdict(int)
        
        # 预计算的启发式数据
        self.position_priorities = self._precompute_position_priorities()
        self.shape_compatibility = self._precompute_shape_compatibility()
        
        print(f"终极启发式求解器初始化:")
        print(f"  网格: {grid_size}×{grid_size}")
        print(f"  块数: {piece_count}")
        print(f"  形状变体: {len(self.shapes)}")
        print(f"  形状签名: {len(self.shape_signatures)}")
    
    def _generate_shape_variants(self) -> List[List[Tuple[int, int]]]:
        """生成J形块的所有变体（包括镜像）"""
        base = [
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0], 
            [1, 1, 1, 1, 1]
        ]
        
        def extract_positions(shape):
            return [(i, j) for i in range(len(shape)) 
                    for j in range(len(shape[0])) if shape[i][j]]
        
        def rotate_90(shape):
            rows, cols = len(shape), len(shape[0])
            return [[shape[rows-1-j][i] for j in range(rows)] for i in range(cols)]
        
        def flip_horizontal(shape):
            return [row[::-1] for row in shape]
        
        def normalize(positions):
            if not positions:
                return []
            min_r = min(r for r, c in positions)
            min_c = min(c for r, c in positions)
            return [(r - min_r, c - min_c) for r, c in positions]
        
        variants = []
        seen = set()
        
        # 生成旋转和镜像的所有组合
        for flip in [False, True]:
            current = base
            if flip:
                current = flip_horizontal(current)
            
            for _ in range(4):  # 4个旋转
                pos = normalize(extract_positions(current))
                key = tuple(sorted(pos))
                
                if key not in seen:
                    seen.add(key)
                    variants.append(pos)
                
                current = rotate_90(current)
        
        return variants
    
    def _compute_shape_signatures(self) -> List[Dict]:
        """计算形状的几何签名"""
        signatures = []
        
        for shape in self.shapes:
            # 计算形状的几何特征
            if not shape:
                signatures.append({})
                continue
            
            # 边界框
            min_r = min(r for r, c in shape)
            max_r = max(r for r, c in shape)
            min_c = min(c for r, c in shape)
            max_c = max(c for r, c in shape)
            
            # 重心
            center_r = sum(r for r, c in shape) / len(shape)
            center_c = sum(c for r, c in shape) / len(shape)
            
            # 紧密度（边界框填充率）
            bbox_area = (max_r - min_r + 1) * (max_c - min_c + 1)
            compactness = len(shape) / bbox_area
            
            # 边界复杂度（周长）
            perimeter = 0
            for r, c in shape:
                for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    if (r + dr, c + dc) not in shape:
                        perimeter += 1
            
            signatures.append({
                'bbox': (min_r, max_r, min_c, max_c),
                'center': (center_r, center_c),
                'compactness': compactness,
                'perimeter': perimeter,
                'aspect_ratio': (max_r - min_r + 1) / (max_c - min_c + 1)
            })
        
        return signatures
    
    def _precompute_position_priorities(self) -> List[List[float]]:
        """预计算位置的基础优先级"""
        priorities = [[0.0] * self.grid_size for _ in range(self.grid_size)]
        
        center_r, center_c = self.grid_size // 2, self.grid_size // 2
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                # 距离边界的距离
                edge_dist = min(i, j, self.grid_size - 1 - i, self.grid_size - 1 - j)
                
                # 距离中心的距离
                center_dist = abs(i - center_r) + abs(j - center_c)
                
                # 角落加分
                corner_bonus = 0
                if (i, j) in [(0, 0), (0, self.grid_size-1), 
                             (self.grid_size-1, 0), (self.grid_size-1, self.grid_size-1)]:
                    corner_bonus = 2.0
                elif edge_dist == 0:
                    corner_bonus = 1.0
                
                # 综合优先级
                priority = (edge_dist * 0.5 + 
                           (self.grid_size - center_dist) * 0.3 + 
                           corner_bonus)
                
                priorities[i][j] = priority
        
        return priorities
    
    def _precompute_shape_compatibility(self) -> Dict[Tuple[int, int], List[int]]:
        """预计算形状与位置的兼容性"""
        compatibility = {}
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                compatible_shapes = []
                
                for shape_id, shape in enumerate(self.shapes):
                    # 检查这个形状是否可能放在这个位置
                    can_fit = False
                    
                    for rel_r, rel_c in shape:
                        start_r = i - rel_r
                        start_c = j - rel_c
                        
                        # 检查边界
                        if all(0 <= start_r + r < self.grid_size and 
                              0 <= start_c + c < self.grid_size 
                              for r, c in shape):
                            can_fit = True
                            break
                    
                    if can_fit:
                        compatible_shapes.append(shape_id)
                
                compatibility[(i, j)] = compatible_shapes
        
        return compatibility
    
    def _shape_fitness_score(self, shape: List[Tuple[int, int]], 
                           start_r: int, start_c: int) -> float:
        """形状适应度评分"""
        if not self._can_place(shape, start_r, start_c):
            return -float('inf')
        
        score = 0.0
        positions = [(start_r + dr, start_c + dc) for dr, dc in shape]
        
        # 1. 与现有块的邻接度
        adjacency = 0
        for r, c in positions:
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if (0 <= nr < self.grid_size and 0 <= nc < self.grid_size and 
                    self.grid[nr][nc] > 0):
                    adjacency += 1
        
        score += adjacency * 2.0
        
        # 2. 位置基础优先级
        base_priority = sum(self.position_priorities[r][c] for r, c in positions)
        score += base_priority * 0.5
        
        # 3. 形状紧密度奖励
        bbox_r_min = min(r for r, c in positions)
        bbox_r_max = max(r for r, c in positions)
        bbox_c_min = min(c for r, c in positions)
        bbox_c_max = max(c for r, c in positions)
        
        bbox_area = (bbox_r_max - bbox_r_min + 1) * (bbox_c_max - bbox_c_min + 1)
        compactness = len(positions) / bbox_area
        score += compactness * 3.0
        
        return score
    
    def _constraint_propagation_score(self, shape: List[Tuple[int, int]], 
                                    start_r: int, start_c: int, 
                                    remaining_pieces: int) -> float:
        """约束传播评分"""
        if remaining_pieces == 0:
            return 10.0
        
        # 模拟放置
        temp_grid = [row[:] for row in self.grid]
        positions = [(start_r + dr, start_c + dc) for dr, dc in shape]
        
        for r, c in positions:
            temp_grid[r][c] = 999
        
        # 计算剩余空间的可用性
        remaining_space = sum(1 for row in temp_grid for cell in row if cell == 0)
        needed_space = remaining_pieces * self.shape_size
        
        if remaining_space < needed_space:
            return -10.0
        
        # 计算放置的灵活性
        flexibility = 0
        for other_shape in self.shapes:
            for r in range(self.grid_size):
                for c in range(self.grid_size):
                    if self._can_place_on_grid(other_shape, r, c, temp_grid):
                        flexibility += 1
        
        # 平均每个剩余块的可用放置数
        avg_flexibility = flexibility / max(remaining_pieces, 1)
        
        if avg_flexibility < 1:
            return -8.0
        elif avg_flexibility < 3:
            return -4.0
        else:
            return min(avg_flexibility / 10, 3.0)
    
    def _deadlock_avoidance_score(self, shape: List[Tuple[int, int]], 
                                 start_r: int, start_c: int) -> float:
        """死锁避免评分"""
        # 模拟放置
        temp_grid = [row[:] for row in self.grid]
        positions = [(start_r + dr, start_c + dc) for dr, dc in shape]
        
        for r, c in positions:
            temp_grid[r][c] = 999
        
        # 检查是否创建了无法填充的小空间
        small_spaces = self._count_small_spaces(temp_grid)
        
        if small_spaces > 3:
            return -15.0
        elif small_spaces > 1:
            return -8.0
        elif small_spaces > 0:
            return -3.0
        else:
            return 2.0
    
    def _count_small_spaces(self, grid: List[List[int]]) -> int:
        """计算小于一个块大小的空间数"""
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        small_spaces = 0
        
        def dfs(r, c):
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
                visited[r][c] or grid[r][c] != 0):
                return 0
            
            visited[r][c] = True
            size = 1
            
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                size += dfs(r + dr, c + dc)
            
            return size
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if not visited[i][j] and grid[i][j] == 0:
                    space_size = dfs(i, j)
                    if 0 < space_size < self.shape_size:
                        small_spaces += 1
        
        return small_spaces
    
    def _connectivity_preservation_score(self, shape: List[Tuple[int, int]], 
                                       start_r: int, start_c: int) -> float:
        """连通性保持评分"""
        # 模拟放置
        temp_grid = [row[:] for row in self.grid]
        positions = [(start_r + dr, start_c + dc) for dr, dc in shape]
        
        for r, c in positions:
            temp_grid[r][c] = 999
        
        # 分析连通分量
        components = self._analyze_connected_components(temp_grid)
        
        if not components:
            return 0.0
        
        # 偏好少数大组件
        large_components = [size for size in components if size >= self.shape_size]
        small_components = [size for size in components if size < self.shape_size]
        
        score = len(large_components) * 3.0 - len(small_components) * 2.0
        
        # 单一大组件奖励
        if len(large_components) == 1:
            score += 5.0
        
        return score
    
    def _analyze_connected_components(self, grid: List[List[int]]) -> List[int]:
        """分析连通分量"""
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        components = []
        
        def dfs(r, c):
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
                visited[r][c] or grid[r][c] != 0):
                return 0
            
            visited[r][c] = True
            size = 1
            
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                size += dfs(r + dr, c + dc)
            
            return size
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if not visited[i][j] and grid[i][j] == 0:
                    component_size = dfs(i, j)
                    if component_size > 0:
                        components.append(component_size)
        
        return components
    
    def _boundary_utilization_score(self, shape: List[Tuple[int, int]], 
                                   start_r: int, start_c: int) -> float:
        """边界利用评分"""
        positions = [(start_r + dr, start_c + dc) for dr, dc in shape]
        boundary_count = 0
        
        for r, c in positions:
            if (r == 0 or r == self.grid_size - 1 or 
                c == 0 or c == self.grid_size - 1):
                boundary_count += 1
        
        return boundary_count * 1.0
    
    def _spatial_balance_score(self, shape: List[Tuple[int, int]], 
                              start_r: int, start_c: int) -> float:
        """空间平衡评分"""
        positions = [(start_r + dr, start_c + dc) for dr, dc in shape]
        
        # 计算放置后的空间分布
        center_r, center_c = self.grid_size // 2, self.grid_size // 2
        
        # 计算与中心的距离
        avg_dist_to_center = sum(abs(r - center_r) + abs(c - center_c) 
                                for r, c in positions) / len(positions)
        
        # 偏好适中的距离
        ideal_dist = self.grid_size // 3
        balance_score = 1.0 - abs(avg_dist_to_center - ideal_dist) / ideal_dist
        
        return balance_score * 2.0
    
    def _future_flexibility_score(self, shape: List[Tuple[int, int]], 
                                 start_r: int, start_c: int, 
                                 remaining_pieces: int) -> float:
        """未来灵活性评分"""
        if remaining_pieces <= 1:
            return 0.0
        
        # 模拟放置
        temp_grid = [row[:] for row in self.grid]
        positions = [(start_r + dr, start_c + dc) for dr, dc in shape]
        
        for r, c in positions:
            temp_grid[r][c] = 999
        
        # 计算剩余位置的选择多样性
        empty_positions = [(i, j) for i in range(self.grid_size) 
                          for j in range(self.grid_size) if temp_grid[i][j] == 0]
        
        if not empty_positions:
            return 0.0
        
        # 计算空间的多样性（分散度）
        diversity = 0.0
        for i, pos1 in enumerate(empty_positions):
            for pos2 in empty_positions[i+1:]:
                dist = abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
                diversity += min(dist, 5)  # 限制最大距离贡献
        
        # 标准化
        max_diversity = len(empty_positions) * (len(empty_positions) - 1) * 2.5
        if max_diversity > 0:
            diversity /= max_diversity
        
        return diversity * 3.0
    
    def _comprehensive_evaluation(self, shape: List[Tuple[int, int]], 
                                 start_r: int, start_c: int, 
                                 remaining_pieces: int) -> PlacementEvaluation:
        """综合评估放置方案"""
        if not self._can_place(shape, start_r, start_c):
            return PlacementEvaluation(
                total_score=-float('inf'),
                shape_fitness=0, constraint_propagation=0, deadlock_risk=0,
                connectivity=0, boundary_score=0, spatial_balance=0,
                future_flexibility=0
            )
        
        # 计算各个维度的分数
        shape_fitness = self._shape_fitness_score(shape, start_r, start_c)
        constraint_prop = self._constraint_propagation_score(shape, start_r, start_c, remaining_pieces)
        deadlock_risk = self._deadlock_avoidance_score(shape, start_r, start_c)
        connectivity = self._connectivity_preservation_score(shape, start_r, start_c)
        boundary_score = self._boundary_utilization_score(shape, start_r, start_c)
        spatial_balance = self._spatial_balance_score(shape, start_r, start_c)
        future_flexibility = self._future_flexibility_score(shape, start_r, start_c, remaining_pieces)
        
        # 加权总分
        total_score = (shape_fitness * self.weights.shape_fitness +
                      constraint_prop * self.weights.constraint_propagation +
                      deadlock_risk * self.weights.deadlock_avoidance +
                      connectivity * self.weights.connectivity_preservation +
                      boundary_score * self.weights.boundary_utilization +
                      spatial_balance * self.weights.spatial_balance +
                      future_flexibility * self.weights.future_flexibility)
        
        return PlacementEvaluation(
            total_score=total_score,
            shape_fitness=shape_fitness,
            constraint_propagation=constraint_prop,
            deadlock_risk=deadlock_risk,
            connectivity=connectivity,
            boundary_score=boundary_score,
            spatial_balance=spatial_balance,
            future_flexibility=future_flexibility
        )
    
    def _can_place(self, shape: List[Tuple[int, int]], start_r: int, start_c: int) -> bool:
        """检查是否可以放置"""
        for dr, dc in shape:
            r, c = start_r + dr, start_c + dc
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
                self.grid[r][c] != 0):
                return False
        return True
    
    def _can_place_on_grid(self, shape: List[Tuple[int, int]], start_r: int, start_c: int, 
                          grid: List[List[int]]) -> bool:
        """在指定网格上检查是否可以放置"""
        for dr, dc in shape:
            r, c = start_r + dr, start_c + dc
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
                grid[r][c] != 0):
                return False
        return True
    
    def _place(self, shape: List[Tuple[int, int]], start_r: int, start_c: int, piece_id: int):
        """放置块"""
        for dr, dc in shape:
            r, c = start_r + dr, start_c + dc
            self.grid[r][c] = piece_id
    
    def _remove(self, shape: List[Tuple[int, int]], start_r: int, start_c: int):
        """移除块"""
        for dr, dc in shape:
            r, c = start_r + dr, start_c + dc
            self.grid[r][c] = 0
    
    def _get_best_candidates(self, remaining_pieces: int, max_candidates: int = 8) -> List[Tuple[float, int, int, int]]:
        """获取最佳候选放置"""
        candidates = []
        
        for shape_id, shape in enumerate(self.shapes):
            for r in range(self.grid_size):
                for c in range(self.grid_size):
                    if self._can_place(shape, r, c):
                        evaluation = self._comprehensive_evaluation(shape, r, c, remaining_pieces)
                        
                        if evaluation.total_score > -float('inf'):
                            candidates.append((evaluation.total_score, shape_id, r, c))
        
        # 排序并返回最佳候选
        candidates.sort(reverse=True)
        return candidates[:max_candidates]
    
    def _adaptive_weight_adjustment(self, depth: int):
        """自适应权重调整"""
        progress = depth / self.piece_count
        
        if progress < 0.3:
            # 早期：偏重形状适应度和空间平衡
            self.weights.shape_fitness = 2.5
            self.weights.spatial_balance = 2.0
            self.weights.deadlock_avoidance = 3.0
        elif progress < 0.7:
            # 中期：偏重约束传播和连通性
            self.weights.constraint_propagation = 4.0
            self.weights.connectivity_preservation = 3.0
            self.weights.deadlock_avoidance = 5.0
        else:
            # 后期：极度偏重死锁避免
            self.weights.deadlock_avoidance = 8.0
            self.weights.constraint_propagation = 6.0
            self.weights.future_flexibility = 3.0
    
    def _solve_recursive(self, piece_id: int) -> bool:
        """递归求解"""
        self.nodes += 1
        self.depth_stats[piece_id] += 1
        
        # 进度检查
        if self.nodes % 5000 == 0:
            elapsed = time.time() - self.start_time
            if elapsed > 180:  # 3分钟超时
                return False
            
            if self.nodes % 25000 == 0:
                empty = sum(1 for row in self.grid for cell in row if cell == 0)
                print(f"  终极启发式: 深度{piece_id}, 空格{empty}, 节点{self.nodes}, 时间{elapsed:.1f}s")
        
        # 成功条件
        if piece_id >= self.piece_count:
            return True
        
        # 自适应权重调整
        self._adaptive_weight_adjustment(piece_id)
        
        # 基本剪枝
        empty_cells = sum(1 for row in self.grid for cell in row if cell == 0)
        needed_cells = (self.piece_count - piece_id) * self.shape_size
        if empty_cells < needed_cells:
            return False
        
        # 获取最佳候选
        remaining_pieces = self.piece_count - piece_id
        candidates = self._get_best_candidates(remaining_pieces, max_candidates=6)
        
        if not candidates:
            return False
        
        # 调试输出
        if piece_id <= 2:
            print(f"    深度{piece_id}最佳候选: {candidates[0][0]:.2f}")
        
        # 尝试最佳候选
        for score, shape_id, r, c in candidates:
            if score < -5.0:  # 分数太低的候选直接跳过
                continue
            
            shape = self.shapes[shape_id]
            self._place(shape, r, c, piece_id + 1)
            
            if self._solve_recursive(piece_id + 1):
                return True
            
            self._remove(shape, r, c)
        
        return False
    
    def solve(self) -> Optional[List[List[int]]]:
        """求解主函数"""
        print("开始终极启发式搜索...")
        
        self.start_time = time.time()
        self.nodes = 0
        self.depth_stats.clear()
        
        if self._solve_recursive(0):
            return self.grid
        else:
            return None
    
    def visualize(self, grid: List[List[int]]) -> str:
        """可视化结果"""
        if not grid:
            return "未找到解"
        
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        result = []
        result.append("✓ 终极启发式找到解决方案！")
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        for row in grid:
            line = "| "
            for cell in row:
                if cell == 0:
                    line += "· "
                else:
                    line += letters[(cell - 1) % len(letters)] + " "
            line += "|"
            result.append(line)
        
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        # 详细统计
        elapsed = time.time() - self.start_time
        result.append(f"\n终极启发式统计:")
        result.append(f"  用时: {elapsed:.2f} 秒")
        result.append(f"  节点: {self.nodes}")
        result.append(f"  效率: {self.nodes/elapsed:.0f} 节点/秒")
        result.append(f"  深度分布: {dict(self.depth_stats)}")
        
        occupied = sum(1 for row in grid for cell in row if cell > 0)
        result.append(f"  占用格子: {occupied}")
        result.append(f"  空闲格子: {100 - occupied}")
        
        return "\n".join(result)


def main():
    """主函数"""
    print("终极启发式J形拼图求解器")
    print("=" * 50)
    
    solver = UltimateHeuristicSolver(10, 11)
    solution = solver.solve()
    
    print("\n" + "=" * 50)
    print(solver.visualize(solution))


if __name__ == "__main__":
    main()