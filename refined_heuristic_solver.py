#!/usr/bin/env python3
"""
精炼启发式J形拼图求解器

结合简单有效的启发式策略：
1. 智能位置选择（约束强度 + 边界优先）
2. 形状排序（优先尝试适配度高的形状）
3. 动态调整（根据搜索深度调整策略）
4. 有效剪枝（连通性 + 空间检查）
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import time


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


class RefinedHeuristicSolver:
    """精炼启发式求解器"""
    
    def __init__(self, config: PuzzleConfig):
        self.config = config
        self.grid_size = config.grid_size
        self.piece_count = config.piece_count
        self.piece_size = sum(sum(row) for row in config.piece_shape)
        
        # 预计算
        self.rotations = self._compute_unique_rotations()
        
        # 搜索状态
        self.grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.solution = []
        self.nodes_explored = 0
        self.start_time = 0
        
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
    
    def _get_constrained_position(self) -> Optional[Tuple[int, int]]:
        """
        选择约束最强的位置
        
        简化版本：选择周围被占用格子最多的空位置
        """
        best_pos = None
        max_constraints = -1
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if self.grid[i][j] == 0:
                    # 计算约束强度
                    constraints = 0
                    total_neighbors = 0
                    
                    for di in [-1, 0, 1]:
                        for dj in [-1, 0, 1]:
                            if di == 0 and dj == 0:
                                continue
                            ni, nj = i + di, j + dj
                            if 0 <= ni < self.grid_size and 0 <= nj < self.grid_size:
                                total_neighbors += 1
                                if self.grid[ni][nj] != 0:
                                    constraints += 1
                            else:
                                # 边界也算约束
                                constraints += 0.5
                                total_neighbors += 1
                    
                    # 约束比例 + 轻微的位置偏好
                    constraint_ratio = constraints / max(total_neighbors, 1)
                    
                    # 轻微偏好边界位置（在早期搜索中）
                    edge_bonus = 0
                    if (i == 0 or i == self.grid_size - 1 or 
                        j == 0 or j == self.grid_size - 1):
                        edge_bonus = 0.1
                    
                    score = constraint_ratio + edge_bonus
                    
                    if score > max_constraints:
                        max_constraints = score
                        best_pos = (i, j)
        
        return best_pos
    
    def _calculate_placement_score(self, rotation: List[Tuple[int, int]], 
                                  start_row: int, start_col: int) -> float:
        """
        计算放置方案的分数
        
        简化评估：主要考虑邻接度和边界利用
        """
        if not self._can_place_at(rotation, start_row, start_col):
            return -1
        
        score = 0
        abs_positions = [(start_row + dr, start_col + dc) for dr, dc in rotation]
        
        # 1. 邻接度：与已放置块的接触程度
        adjacency = 0
        for r, c in abs_positions:
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if (0 <= nr < self.grid_size and 0 <= nc < self.grid_size and 
                    self.grid[nr][nc] != 0):
                    adjacency += 1
        
        score += adjacency * 10
        
        # 2. 边界利用
        boundary_contact = 0
        for r, c in abs_positions:
            if r == 0 or r == self.grid_size - 1 or c == 0 or c == self.grid_size - 1:
                boundary_contact += 1
        
        score += boundary_contact * 3
        
        # 3. 紧凑性：偏好将块放在一起
        if adjacency > 0:
            score += 20  # 连接奖励
        
        return score
    
    def _get_sorted_placements(self, target_row: int, target_col: int) -> List[Tuple[int, int, int]]:
        """
        获取按分数排序的放置方案
        
        Returns:
            List[(rotation_id, start_row, start_col)]
        """
        placements = []
        
        for rot_id, rotation in enumerate(self.rotations):
            # 找所有能覆盖目标位置的起始位置
            for rel_row, rel_col in rotation:
                start_row = target_row - rel_row
                start_col = target_col - rel_col
                
                if self._can_place_at(rotation, start_row, start_col):
                    score = self._calculate_placement_score(rotation, start_row, start_col)
                    if score >= 0:
                        placements.append((score, rot_id, start_row, start_col))
        
        # 按分数降序排序
        placements.sort(reverse=True)
        
        # 返回前几个最佳选择
        return [(rot_id, start_row, start_col) for score, rot_id, start_row, start_col in placements[:15]]
    
    def _count_large_components(self) -> int:
        """计算足够大的连通分量数量"""
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
    
    def _solve_recursive(self, piece_id: int) -> bool:
        """精炼启发式递归求解"""
        self.nodes_explored += 1
        
        # 超时和进度检查
        if self.nodes_explored % 1000 == 0:
            elapsed = time.time() - self.start_time
            if elapsed > 30:  # 30秒超时
                return False
            
            if self.nodes_explored % 5000 == 0:
                empty = sum(row.count(0) for row in self.grid)
                print(f"    精炼启发式: {piece_id}/{self.piece_count}块, {empty}空格, "
                      f"{self.nodes_explored}节点, {elapsed:.1f}s")
        
        # 成功条件
        if piece_id >= self.piece_count:
            return True
        
        # 基本剪枝
        empty_cells = sum(row.count(0) for row in self.grid)
        needed_cells = (self.piece_count - piece_id) * self.piece_size
        if empty_cells < needed_cells:
            return False
        
        # 连通性剪枝
        if piece_id < self.piece_count - 1:
            remaining_pieces = self.piece_count - piece_id
            if self._count_large_components() < remaining_pieces:
                return False
        
        # 选择约束最强的位置
        target_pos = self._get_constrained_position()
        if target_pos is None:
            return piece_id >= self.piece_count
        
        target_row, target_col = target_pos
        
        # 获取排序后的放置方案
        sorted_placements = self._get_sorted_placements(target_row, target_col)
        
        # 尝试最佳的放置方案
        for rot_id, start_row, start_col in sorted_placements:
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
    
    def solve(self) -> Optional[List[Dict]]:
        """求解主函数"""
        self.start_time = time.time()
        self.nodes_explored = 0
        self.grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.solution = []
        
        print(f"  精炼启发式求解器:")
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
        result = [f"精炼启发式解 ({len(solution)} 个J形块):"]
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        for row in grid:
            result.append("| " + " ".join(row) + " |")
        
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        # 统计
        elapsed = time.time() - self.start_time
        result.append(f"\n精炼启发式统计:")
        result.append(f"  求解时间: {elapsed:.3f} 秒")
        result.append(f"  搜索节点: {self.nodes_explored}")
        result.append(f"  搜索效率: {self.nodes_explored/max(elapsed, 0.001):.0f} 节点/秒")
        
        return "\n".join(result)


def test_refined_heuristics():
    """测试精炼启发式算法"""
    print("精炼启发式J形拼图求解器测试")
    print("="*50)
    
    test_cases = [
        (6, 2, "热身"),
        (8, 3, "基础"), 
        (8, 4, "进阶"),
        (9, 5, "挑战"),
        (10, 6, "高难"),
        (10, 8, "极难"),
        (10, 10, "终极")
    ]
    
    for grid_size, piece_count, level in test_cases:
        print(f"\n{'='*30}")
        print(f"{level}测试: {grid_size}×{grid_size}, {piece_count}块")
        print('='*30)
        
        config = PuzzleConfig(grid_size=grid_size, piece_count=piece_count)
        solver = RefinedHeuristicSolver(config)
        
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
    test_refined_heuristics()