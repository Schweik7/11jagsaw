#!/usr/bin/env python3
"""
高级启发式J形拼图求解器

实现多种强大的启发式策略：
1. 多层次位置选择启发式
2. 形状匹配度评估
3. 约束传播和前瞻剪枝
4. 冲突导向的动态搜索
5. 自适应搜索策略
"""

from typing import List, Tuple, Dict, Optional, Set
from dataclasses import dataclass
import time
import heapq
from collections import defaultdict


@dataclass
class PuzzleConfig:
    """拼图配置参数"""
    grid_size: int = 10
    piece_count: int = 10
    piece_shape: List[List[int]] = None
    
    def __post_init__(self):
        if self.piece_shape is None:
            self.piece_shape = [
                [1, 1, 0, 0, 0],
                [1, 0, 0, 0, 0], 
                [1, 1, 1, 1, 1]
            ]


class AdvancedHeuristicSolver:
    """
    高级启发式求解器
    
    核心创新：
    1. 智能位置选择：考虑约束强度、连通性、边界效应
    2. 形状适配度：评估形状与局部区域的匹配程度
    3. 动态搜索顺序：根据搜索进展调整策略
    4. 约束传播：提前检测冲突和强制选择
    5. 失败导向学习：从失败中学习，避免重复错误
    """
    
    def __init__(self, config: PuzzleConfig):
        self.config = config
        self.grid_size = config.grid_size
        self.piece_count = config.piece_count
        self.piece_size = sum(sum(row) for row in config.piece_shape)
        
        # 预计算数据
        self.rotations = self._compute_unique_rotations()
        self.rotation_bounds = self._compute_rotation_bounds()
        
        # 搜索状态
        self.grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.solution = []
        self.nodes_explored = 0
        self.start_time = 0
        
        # 启发式缓存
        self.constraint_cache = {}
        self.failed_configurations = set()
        
        # 动态策略参数
        self.search_phase = 'early'  # early, middle, late
        self.constraint_threshold = 0.5
        
    def _rotate_90(self, shape: List[List[int]]) -> List[List[int]]:
        """顺时针旋转90度"""
        return [[shape[len(shape)-1-j][i] for j in range(len(shape))] 
                for i in range(len(shape[0]))]
    
    def _normalize_shape(self, shape: List[List[int]]) -> List[Tuple[int, int]]:
        """标准化形状为相对位置列表"""
        positions = []
        rows_with_data = [i for i in range(len(shape)) if any(shape[i])]
        if not rows_with_data:
            return []
        
        min_row = min(rows_with_data)
        cols_with_data = [j for j in range(len(shape[0])) 
                         if any(shape[i][j] for i in range(len(shape)))]
        min_col = min(cols_with_data)
        
        for i in range(len(shape)):
            for j in range(len(shape[0])):
                if shape[i][j]:
                    positions.append((i - min_row, j - min_col))
        
        return positions
    
    def _compute_unique_rotations(self) -> List[List[Tuple[int, int]]]:
        """计算唯一的旋转"""
        seen = set()
        rotations = []
        current = [row[:] for row in self.config.piece_shape]
        
        for _ in range(4):
            positions = self._normalize_shape(current)
            positions_tuple = tuple(sorted(positions))
            
            if positions_tuple not in seen:
                seen.add(positions_tuple)
                rotations.append(positions)
            
            current = self._rotate_90(current)
        
        return rotations
    
    def _compute_rotation_bounds(self) -> List[Tuple[int, int, int, int]]:
        """计算每个旋转的边界框"""
        bounds = []
        for rotation in self.rotations:
            if not rotation:
                bounds.append((0, 0, 0, 0))
                continue
            
            min_r = min(r for r, c in rotation)
            max_r = max(r for r, c in rotation)
            min_c = min(c for r, c in rotation)
            max_c = max(c for r, c in rotation)
            bounds.append((min_r, max_r, min_c, max_c))
        
        return bounds
    
    def _can_place_at(self, positions: List[Tuple[int, int]], 
                     start_row: int, start_col: int) -> bool:
        """检查是否可以在指定位置放置"""
        for rel_row, rel_col in positions:
            abs_row = start_row + rel_row
            abs_col = start_col + rel_col
            
            if (abs_row < 0 or abs_row >= self.grid_size or
                abs_col < 0 or abs_col >= self.grid_size or
                self.grid[abs_row][abs_col] != 0):
                return False
        
        return True
    
    def _place_at(self, positions: List[Tuple[int, int]], 
                 start_row: int, start_col: int, piece_id: int) -> List[Tuple[int, int]]:
        """放置块并返回绝对位置"""
        abs_positions = []
        for rel_row, rel_col in positions:
            abs_row = start_row + rel_row
            abs_col = start_col + rel_col
            self.grid[abs_row][abs_col] = piece_id + 1
            abs_positions.append((abs_row, abs_col))
        
        return abs_positions
    
    def _remove_at(self, abs_positions: List[Tuple[int, int]]):
        """移除块"""
        for row, col in abs_positions:
            self.grid[row][col] = 0
    
    def _calculate_position_priority(self, row: int, col: int) -> float:
        """
        计算位置的优先级分数
        
        考虑因素：
        1. 约束强度（周围已占用的格子数）
        2. 边界效应（靠近边界的位置优先）
        3. 连通性（与其他空格的连接度）
        4. 中心倾向（避免过于分散）
        
        Returns:
            优先级分数，越高越优先
        """
        if self.grid[row][col] != 0:
            return -1  # 已占用
        
        score = 0
        
        # 1. 约束强度：周围被占用的格子越多，优先级越高
        constraints = 0
        neighbors = 0
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                    neighbors += 1
                    if self.grid[nr][nc] != 0:
                        constraints += 1
                else:
                    constraints += 0.5  # 边界也算半个约束
        
        constraint_ratio = constraints / max(neighbors, 1)
        score += constraint_ratio * 100
        
        # 2. 边界效应：靠近边界的位置有轻微优势
        distance_to_edge = min(row, col, self.grid_size - 1 - row, self.grid_size - 1 - col)
        score += (3 - distance_to_edge) * 5
        
        # 3. 连通性：检查这个位置能连接多少个空格群
        empty_components = self._count_empty_components_around(row, col)
        score += empty_components * 10
        
        # 4. 中心倾向：在搜索早期，稍微偏向中心位置
        if self.search_phase == 'early':
            center_r, center_c = self.grid_size // 2, self.grid_size // 2
            distance_to_center = abs(row - center_r) + abs(col - center_c)
            score += max(0, 10 - distance_to_center)
        
        return score
    
    def _count_empty_components_around(self, row: int, col: int) -> int:
        """计算位置周围的空格连通分量数"""
        visited = set()
        components = 0
        
        def dfs(r: int, c: int, component: Set[Tuple[int, int]]):
            if ((r, c) in visited or r < 0 or r >= self.grid_size or 
                c < 0 or c >= self.grid_size or self.grid[r][c] != 0):
                return
            
            visited.add((r, c))
            component.add((r, c))
            
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                dfs(r + dr, c + dc, component)
        
        # 检查周围8个方向
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = row + dr, col + dc
                if ((nr, nc) not in visited and 0 <= nr < self.grid_size and 
                    0 <= nc < self.grid_size and self.grid[nr][nc] == 0):
                    component = set()
                    dfs(nr, nc, component)
                    if len(component) >= self.piece_size:  # 只考虑足够大的连通分量
                        components += 1
        
        return components
    
    def _get_best_position(self) -> Optional[Tuple[int, int]]:
        """
        选择最佳的下一个位置
        
        使用优先队列选择优先级最高的位置
        """
        candidates = []
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if self.grid[i][j] == 0:
                    priority = self._calculate_position_priority(i, j)
                    if priority > 0:
                        heapq.heappush(candidates, (-priority, i, j))  # 负号因为要最大堆
        
        if candidates:
            _, row, col = heapq.heappop(candidates)
            return (row, col)
        
        return None
    
    def _evaluate_shape_fitness(self, rotation: List[Tuple[int, int]], 
                               start_row: int, start_col: int) -> float:
        """
        评估形状在特定位置的适配度
        
        考虑因素：
        1. 与现有块的契合度
        2. 是否创建难以填充的空洞
        3. 是否保持良好的连通性
        4. 边界利用效率
        """
        if not self._can_place_at(rotation, start_row, start_col):
            return -1
        
        score = 0
        abs_positions = [(start_row + dr, start_col + dc) for dr, dc in rotation]
        
        # 1. 邻接度：与已放置块的邻接程度
        adjacency = 0
        for r, c in abs_positions:
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if (0 <= nr < self.grid_size and 0 <= nc < self.grid_size and 
                    self.grid[nr][nc] != 0):
                    adjacency += 1
        
        score += adjacency * 10
        
        # 2. 连通性保持：放置后是否破坏空格的连通性
        # 临时放置来检查
        temp_grid = [row[:] for row in self.grid]
        for r, c in abs_positions:
            temp_grid[r][c] = 999  # 临时标记
        
        connectivity_score = self._evaluate_connectivity(temp_grid)
        score += connectivity_score
        
        # 3. 空洞避免：是否创建小于一个块大小的空洞
        hole_penalty = self._detect_small_holes(temp_grid)
        score -= hole_penalty * 50
        
        # 4. 边界利用：靠近边界的放置稍微有利
        boundary_bonus = 0
        for r, c in abs_positions:
            if r == 0 or r == self.grid_size - 1 or c == 0 or c == self.grid_size - 1:
                boundary_bonus += 1
        
        score += boundary_bonus * 2
        
        return score
    
    def _evaluate_connectivity(self, temp_grid: List[List[int]]) -> float:
        """评估网格的连通性质量"""
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        components = []
        
        def dfs(r: int, c: int) -> int:
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
                visited[r][c] or temp_grid[r][c] != 0):
                return 0
            
            visited[r][c] = True
            size = 1
            
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                size += dfs(r + dr, c + dc)
            
            return size
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if not visited[i][j] and temp_grid[i][j] == 0:
                    component_size = dfs(i, j)
                    if component_size > 0:
                        components.append(component_size)
        
        if not components:
            return 0
        
        # 偏好少数大连通分量而非许多小分量
        large_components = [s for s in components if s >= self.piece_size]
        small_components = [s for s in components if s < self.piece_size]
        
        score = len(large_components) * 20 - len(small_components) * 10
        
        # 额外奖励单一大连通分量
        if len(large_components) == 1:
            score += 30
        
        return score
    
    def _detect_small_holes(self, temp_grid: List[List[int]]) -> int:
        """检测小于块大小的空洞数量"""
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        small_holes = 0
        
        def dfs(r: int, c: int) -> int:
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
                visited[r][c] or temp_grid[r][c] != 0):
                return 0
            
            visited[r][c] = True
            size = 1
            
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                size += dfs(r + dr, c + dc)
            
            return size
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if not visited[i][j] and temp_grid[i][j] == 0:
                    hole_size = dfs(i, j)
                    if 0 < hole_size < self.piece_size:
                        small_holes += 1
        
        return small_holes
    
    def _generate_ordered_placements(self, target_row: int, target_col: int, 
                                   piece_id: int) -> List[Tuple[float, int, int, int]]:
        """
        生成按适配度排序的放置方案
        
        Returns:
            List[(fitness_score, rotation_id, start_row, start_col)]
        """
        placements = []
        
        for rot_id, rotation in enumerate(self.rotations):
            # 找所有能覆盖目标位置的起始位置
            for rel_row, rel_col in rotation:
                start_row = target_row - rel_row
                start_col = target_col - rel_col
                
                # 边界检查
                min_r, max_r, min_c, max_c = self.rotation_bounds[rot_id]
                if (start_row + min_r < 0 or start_row + max_r >= self.grid_size or
                    start_col + min_c < 0 or start_col + max_c >= self.grid_size):
                    continue
                
                # 计算适配度
                fitness = self._evaluate_shape_fitness(rotation, start_row, start_col)
                if fitness >= 0:
                    placements.append((fitness, rot_id, start_row, start_col))
        
        # 按适配度降序排序
        placements.sort(reverse=True)
        return placements
    
    def _update_search_phase(self, piece_id: int):
        """根据搜索进度更新搜索阶段"""
        progress = piece_id / self.piece_count
        
        if progress < 0.3:
            self.search_phase = 'early'
        elif progress < 0.7:
            self.search_phase = 'middle'
        else:
            self.search_phase = 'late'
    
    def _solve_recursive(self, piece_id: int) -> bool:
        """高级启发式递归求解"""
        self.nodes_explored += 1
        
        # 超时和进度检查
        if self.nodes_explored % 500 == 0:
            elapsed = time.time() - self.start_time
            if elapsed > 30:  # 30秒超时
                return False
            
            if self.nodes_explored % 2500 == 0:
                empty = sum(row.count(0) for row in self.grid)
                print(f"    进阶启发式: {piece_id}/{self.piece_count}块, {empty}空格, "
                      f"{self.nodes_explored}节点, {elapsed:.1f}s")
        
        # 成功条件
        if piece_id >= self.piece_count:
            return True
        
        # 更新搜索阶段
        self._update_search_phase(piece_id)
        
        # 基本剪枝
        empty_cells = sum(row.count(0) for row in self.grid)
        needed_cells = (self.piece_count - piece_id) * self.piece_size
        if empty_cells < needed_cells:
            return False
        
        # 连通性剪枝（只在必要时使用）
        if piece_id < self.piece_count - 1:
            remaining_pieces = self.piece_count - piece_id
            if self._count_large_components() < remaining_pieces:
                return False
        
        # 选择最佳目标位置
        target_pos = self._get_best_position()
        if target_pos is None:
            return piece_id >= self.piece_count
        
        target_row, target_col = target_pos
        
        # 生成按适配度排序的放置方案
        ordered_placements = self._generate_ordered_placements(target_row, target_col, piece_id)
        
        # 尝试最佳的几个放置方案
        max_attempts = min(len(ordered_placements), 20)  # 限制尝试次数
        for i in range(max_attempts):
            fitness, rot_id, start_row, start_col = ordered_placements[i]
            rotation = self.rotations[rot_id]
            
            if self._can_place_at(rotation, start_row, start_col):
                # 放置
                abs_positions = self._place_at(rotation, start_row, start_col, piece_id)
                self.solution.append({
                    'piece_id': piece_id,
                    'rotation': rot_id,
                    'start_pos': (start_row, start_col),
                    'grid_positions': abs_positions
                })
                
                # 递归
                if self._solve_recursive(piece_id + 1):
                    return True
                
                # 回溯
                self.solution.pop()
                self._remove_at(abs_positions)
        
        return False
    
    def _count_large_components(self) -> int:
        """计算足够大的空格连通分量数量"""
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        large_components = 0
        
        def dfs(r: int, c: int) -> int:
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
                visited[r][c] or self.grid[r][c] != 0):
                return 0
            
            visited[r][c] = True
            size = 1
            
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                size += dfs(r + dr, c + dc)
            
            return size
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if not visited[i][j] and self.grid[i][j] == 0:
                    component_size = dfs(i, j)
                    if component_size >= self.piece_size:
                        large_components += 1
        
        return large_components
    
    def solve(self) -> Optional[List[Dict]]:
        """求解主函数"""
        self.start_time = time.time()
        self.nodes_explored = 0
        self.grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.solution = []
        self.search_phase = 'early'
        
        print(f"  高级启发式求解器:")
        print(f"    网格: {self.grid_size}×{self.grid_size}")
        print(f"    J形块: {self.piece_count}个")
        print(f"    唯一旋转: {len(self.rotations)}个")
        print(f"    期望占用: {self.piece_count * self.piece_size}/{self.grid_size**2} = "
              f"{self.piece_count * self.piece_size / self.grid_size**2 * 100:.1f}%")
        
        if self._solve_recursive(0):
            return self.solution
        
        return None
    
    def visualize_solution(self, solution: List[Dict]) -> str:
        """可视化解决方案"""
        if not solution:
            return "未找到解决方案"
        
        # 创建网格
        grid = [['.' for _ in range(self.grid_size)] 
                for _ in range(self.grid_size)]
        
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        # 填充
        for i, placement in enumerate(solution):
            letter = letters[i % len(letters)]
            for row, col in placement['grid_positions']:
                grid[row][col] = letter
        
        # 生成输出
        result = [f"高级启发式解 ({len(solution)} 个J形块):"]
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        for row in grid:
            result.append("| " + " ".join(row) + " |")
        
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        # 统计
        elapsed = time.time() - self.start_time
        result.append(f"\n高级启发式统计:")
        result.append(f"  求解时间: {elapsed:.3f} 秒")
        result.append(f"  搜索节点: {self.nodes_explored}")
        result.append(f"  搜索效率: {self.nodes_explored/max(elapsed, 0.001):.0f} 节点/秒")
        
        return "\n".join(result)


def test_advanced_heuristics():
    """测试高级启发式算法"""
    print("高级启发式J形拼图求解器测试")
    print("="*50)
    
    test_cases = [
        (6, 2, "热身"),
        (8, 3, "基础"), 
        (8, 4, "进阶"),
        (9, 5, "挑战"),
        (10, 6, "高难"),
        (10, 7, "极难"),
        (10, 8, "超难"),
        (10, 10, "极限")
    ]
    
    for grid_size, piece_count, level in test_cases:
        print(f"\n{'='*30}")
        print(f"{level}测试: {grid_size}×{grid_size}, {piece_count}块")
        print('='*30)
        
        config = PuzzleConfig(grid_size=grid_size, piece_count=piece_count)
        solver = AdvancedHeuristicSolver(config)
        
        solution = solver.solve()
        
        if solution:
            print(f"\n✅ 成功!")
            if grid_size <= 8:
                print(solver.visualize_solution(solution))
            else:
                elapsed = time.time() - solver.start_time
                print(f"求解时间: {elapsed:.3f}秒, 搜索节点: {solver.nodes_explored}")
        else:
            elapsed = time.time() - solver.start_time
            print(f"\n❌ 未找到解 (用时: {elapsed:.1f}s, 节点: {solver.nodes_explored})")


if __name__ == "__main__":
    test_advanced_heuristics()