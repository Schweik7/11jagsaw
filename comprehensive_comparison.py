#!/usr/bin/env python3
"""
全面算法对比测试

对比不同求解策略的效果：
1. 基本回溯（之前成功的版本）
2. 改进启发式
3. 混合策略

目标：找出启发式的问题，并提供最佳解决方案
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


class BasicBacktrackSolver:
    """基本回溯求解器（成功版本的重现）"""
    
    def __init__(self, config: PuzzleConfig):
        self.config = config
        self.grid_size = config.grid_size
        self.piece_count = config.piece_count
        self.piece_size = sum(sum(row) for row in config.piece_shape)
        
        self.rotations = self._compute_unique_rotations()
        self.grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.solution = []
        self.nodes_explored = 0
        self.start_time = 0
        
    def _rotate_90(self, shape: List[List[int]]) -> List[List[int]]:
        return [[shape[len(shape)-1-j][i] for j in range(len(shape))] 
                for i in range(len(shape[0]))]
    
    def _normalize_shape(self, shape: List[List[int]]) -> List[Tuple[int, int]]:
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
        abs_positions = []
        for rel_row, rel_col in positions:
            abs_row = start_row + rel_row
            abs_col = start_col + rel_col
            self.grid[abs_row][abs_col] = piece_id + 1
            abs_positions.append((abs_row, abs_col))
        
        return abs_positions
    
    def _remove_at(self, abs_positions: List[Tuple[int, int]]):
        for row, col in abs_positions:
            self.grid[row][col] = 0
    
    def _get_first_empty(self) -> Optional[Tuple[int, int]]:
        """最简单的位置选择：第一个空格"""
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if self.grid[i][j] == 0:
                    return (i, j)
        return None
    
    def _solve_recursive(self, piece_id: int) -> bool:
        self.nodes_explored += 1
        
        if self.nodes_explored % 1000 == 0:
            elapsed = time.time() - self.start_time
            if elapsed > 30:
                return False
            
            if self.nodes_explored % 5000 == 0:
                empty = sum(row.count(0) for row in self.grid)
                print(f"      基本回溯: {piece_id}/{self.piece_count}块, {empty}空格, "
                      f"{self.nodes_explored}节点, {elapsed:.1f}s")
        
        if piece_id >= self.piece_count:
            return True
        
        # 简单剪枝
        empty_cells = sum(row.count(0) for row in self.grid)
        needed_cells = (self.piece_count - piece_id) * self.piece_size
        if empty_cells < needed_cells:
            return False
        
        # 选择第一个空格
        anchor = self._get_first_empty()
        if anchor is None:
            return piece_id >= self.piece_count
        
        anchor_row, anchor_col = anchor
        
        # 尝试所有能覆盖锚点的放置
        for rot_id, rotation in enumerate(self.rotations):
            for rel_row, rel_col in rotation:
                start_row = anchor_row - rel_row
                start_col = anchor_col - rel_col
                
                if self._can_place_at(rotation, start_row, start_col):
                    abs_positions = self._place_at(rotation, start_row, start_col, piece_id)
                    self.solution.append({
                        'piece_id': piece_id,
                        'rotation': rot_id,
                        'start_pos': (start_row, start_col),
                        'grid_positions': abs_positions
                    })
                    
                    if self._solve_recursive(piece_id + 1):
                        return True
                    
                    self.solution.pop()
                    self._remove_at(abs_positions)
        
        return False
    
    def solve(self) -> Optional[List[Dict]]:
        self.start_time = time.time()
        self.nodes_explored = 0
        self.grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.solution = []
        
        if self._solve_recursive(0):
            return self.solution
        return None


class ImprovedHeuristicSolver:
    """改进的启发式求解器"""
    
    def __init__(self, config: PuzzleConfig):
        self.config = config
        self.grid_size = config.grid_size
        self.piece_count = config.piece_count
        self.piece_size = sum(sum(row) for row in config.piece_shape)
        
        self.rotations = self._compute_unique_rotations()
        self.grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.solution = []
        self.nodes_explored = 0
        self.start_time = 0
        
    def _rotate_90(self, shape: List[List[int]]) -> List[List[int]]:
        return [[shape[len(shape)-1-j][i] for j in range(len(shape))] 
                for i in range(len(shape[0]))]
    
    def _normalize_shape(self, shape: List[List[int]]) -> List[Tuple[int, int]]:
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
        abs_positions = []
        for rel_row, rel_col in positions:
            abs_row = start_row + rel_row
            abs_col = start_col + rel_col
            self.grid[abs_row][abs_col] = piece_id + 1
            abs_positions.append((abs_row, abs_col))
        
        return abs_positions
    
    def _remove_at(self, abs_positions: List[Tuple[int, int]]):
        for row, col in abs_positions:
            self.grid[row][col] = 0
    
    def _get_best_position(self) -> Optional[Tuple[int, int]]:
        """改进的位置选择：约束强度 + 边界偏好"""
        best_pos = None
        best_score = -1
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if self.grid[i][j] == 0:
                    score = 0
                    
                    # 计算约束强度
                    constraints = 0
                    for di in [-1, 0, 1]:
                        for dj in [-1, 0, 1]:
                            if di == 0 and dj == 0:
                                continue
                            ni, nj = i + di, j + dj
                            if 0 <= ni < self.grid_size and 0 <= nj < self.grid_size:
                                if self.grid[ni][nj] != 0:
                                    constraints += 1
                            else:
                                constraints += 0.5  # 边界约束
                    
                    score = constraints
                    
                    # 轻微的边界偏好
                    if (i == 0 or i == self.grid_size - 1 or 
                        j == 0 or j == self.grid_size - 1):
                        score += 0.5
                    
                    if score > best_score:
                        best_score = score
                        best_pos = (i, j)
        
        return best_pos
    
    def _solve_recursive(self, piece_id: int) -> bool:
        self.nodes_explored += 1
        
        if self.nodes_explored % 1000 == 0:
            elapsed = time.time() - self.start_time
            if elapsed > 30:
                return False
            
            if self.nodes_explored % 5000 == 0:
                empty = sum(row.count(0) for row in self.grid)
                print(f"      改进启发式: {piece_id}/{self.piece_count}块, {empty}空格, "
                      f"{self.nodes_explored}节点, {elapsed:.1f}s")
        
        if piece_id >= self.piece_count:
            return True
        
        # 基本剪枝
        empty_cells = sum(row.count(0) for row in self.grid)
        needed_cells = (self.piece_count - piece_id) * self.piece_size
        if empty_cells < needed_cells:
            return False
        
        # 选择最佳位置
        anchor = self._get_best_position()
        if anchor is None:
            return piece_id >= self.piece_count
        
        anchor_row, anchor_col = anchor
        
        # 尝试所有能覆盖锚点的放置（但限制数量）
        attempts = 0
        max_attempts = 30  # 限制尝试次数
        
        for rot_id, rotation in enumerate(self.rotations):
            for rel_row, rel_col in rotation:
                if attempts >= max_attempts:
                    break
                
                start_row = anchor_row - rel_row
                start_col = anchor_col - rel_col
                
                if self._can_place_at(rotation, start_row, start_col):
                    attempts += 1
                    abs_positions = self._place_at(rotation, start_row, start_col, piece_id)
                    self.solution.append({
                        'piece_id': piece_id,
                        'rotation': rot_id,
                        'start_pos': (start_row, start_col),
                        'grid_positions': abs_positions
                    })
                    
                    if self._solve_recursive(piece_id + 1):
                        return True
                    
                    self.solution.pop()
                    self._remove_at(abs_positions)
            
            if attempts >= max_attempts:
                break
        
        return False
    
    def solve(self) -> Optional[List[Dict]]:
        self.start_time = time.time()
        self.nodes_explored = 0
        self.grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        self.solution = []
        
        if self._solve_recursive(0):
            return self.solution
        return None


def visualize_solution(solution: List[Dict], grid_size: int, title: str) -> str:
    """通用的解决方案可视化"""
    if not solution:
        return f"{title}: 未找到解决方案"
    
    grid = [['.' for _ in range(grid_size)] for _ in range(grid_size)]
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    
    for i, placement in enumerate(solution):
        letter = letters[i % len(letters)]
        for row, col in placement['grid_positions']:
            grid[row][col] = letter
    
    result = [f"{title} ({len(solution)} 个J形块):"]
    result.append("+" + "-" * (grid_size * 2 + 1) + "+")
    
    for row in grid:
        result.append("| " + " ".join(row) + " |")
    
    result.append("+" + "-" * (grid_size * 2 + 1) + "+")
    
    return "\n".join(result)


def comprehensive_comparison():
    """全面对比测试"""
    print("J形拼图求解器全面对比测试")
    print("="*60)
    
    test_cases = [
        (6, 2, "热身测试"),
        (8, 3, "基础测试"),
        (8, 4, "进阶测试"),
        (10, 6, "挑战测试"),
        (10, 8, "高难测试")
    ]
    
    for grid_size, piece_count, description in test_cases:
        print(f"\n{'='*50}")
        print(f"{description}: {grid_size}×{grid_size}网格, {piece_count}个J形块")
        print('='*50)
        
        config = PuzzleConfig(grid_size=grid_size, piece_count=piece_count)
        
        results = {}
        
        # 测试基本回溯
        print("\n[基本回溯算法]")
        solver1 = BasicBacktrackSolver(config)
        start_time = time.time()
        solution1 = solver1.solve()
        elapsed1 = time.time() - start_time
        
        results['基本回溯'] = (solution1, elapsed1, solver1.nodes_explored)
        
        if solution1:
            print(f"✅ 成功! 用时: {elapsed1:.3f}秒, 节点: {solver1.nodes_explored}")
        else:
            print(f"❌ 失败 (用时: {elapsed1:.1f}s, 节点: {solver1.nodes_explored})")
        
        # 测试改进启发式
        print("\n[改进启发式算法]")
        solver2 = ImprovedHeuristicSolver(config)
        start_time = time.time()
        solution2 = solver2.solve()
        elapsed2 = time.time() - start_time
        
        results['改进启发式'] = (solution2, elapsed2, solver2.nodes_explored)
        
        if solution2:
            print(f"✅ 成功! 用时: {elapsed2:.3f}秒, 节点: {solver2.nodes_explored}")
        else:
            print(f"❌ 失败 (用时: {elapsed2:.1f}s, 节点: {solver2.nodes_explored})")
        
        # 显示结果对比
        print(f"\n📊 对比结果:")
        for name, (solution, elapsed, nodes) in results.items():
            status = "成功" if solution else "失败"
            print(f"  {name}: {status}, {elapsed:.3f}s, {nodes}节点")
        
        # 显示解决方案（仅对小问题）
        if grid_size <= 8:
            for name, (solution, _, _) in results.items():
                if solution:
                    print(f"\n{visualize_solution(solution, grid_size, name)}")
        
        # 如果两个算法都失败，可能问题确实无解或很困难
        if not any(solution for solution, _, _ in results.values()):
            print(f"\n⚠️  所有算法都未找到解，可能问题无解或极其困难")


if __name__ == "__main__":
    comprehensive_comparison()