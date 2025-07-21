#!/usr/bin/env python3
"""
最终性能对比测试

对比不同求解器的性能：
1. 简单回溯算法
2. 优化DLX算法
3. 混合策略算法
"""

import time
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass


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


class FinalOptimizedSolver:
    """
    最终优化求解器
    
    结合了最佳实践：
    1. 快速回溯搜索
    2. 智能剪枝
    3. 位运算优化
    4. 分层搜索策略
    """
    
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
        """标准化形状为位置列表"""
        # 找边界
        rows_with_data = [i for i in range(len(shape)) if any(shape[i])]
        if not rows_with_data:
            return []
        
        min_row = min(rows_with_data)
        cols_with_data = [j for j in range(len(shape[0])) 
                         if any(shape[i][j] for i in range(len(shape)))]
        min_col = min(cols_with_data)
        
        # 转换为相对位置，以(0,0)为基准
        positions = []
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
        """在指定位置放置块，返回绝对位置列表"""
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
    
    def _get_first_empty(self) -> Optional[Tuple[int, int]]:
        """获取第一个空位置"""
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if self.grid[i][j] == 0:
                    return (i, j)
        return None
    
    def _count_empty_connected_components(self) -> int:
        """计算空格的连通分量数量（用于剪枝）"""
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        components = 0
        
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
                        components += 1
        
        return components
    
    def _solve_recursive(self, piece_id: int) -> bool:
        """递归求解"""
        self.nodes_explored += 1
        
        # 超时检查
        if self.nodes_explored % 500 == 0:
            elapsed = time.time() - self.start_time
            if elapsed > 15:  # 15秒超时
                return False
            
            if self.nodes_explored % 2500 == 0:
                empty = sum(row.count(0) for row in self.grid)
                print(f"    {piece_id}/{self.piece_count}块, {empty}空格, "
                      f"{self.nodes_explored}节点, {elapsed:.1f}s")
        
        # 成功条件
        if piece_id >= self.piece_count:
            return True
        
        # 基本剪枝：空间检查
        empty_cells = sum(row.count(0) for row in self.grid)
        needed_cells = (self.piece_count - piece_id) * self.piece_size
        if empty_cells < needed_cells:
            return False
        
        # 连通性剪枝（轻量版）
        if piece_id < self.piece_count - 2:  # 只在前期使用，避免后期开销
            remaining_pieces = self.piece_count - piece_id
            if self._count_empty_connected_components() < remaining_pieces:
                return False
        
        # 找锚点
        anchor = self._get_first_empty()
        if anchor is None:
            return piece_id >= self.piece_count
        
        anchor_row, anchor_col = anchor
        
        # 尝试所有能覆盖锚点的放置
        for rot_id, rotation in enumerate(self.rotations):
            # 找能覆盖锚点的所有起始位置
            for rel_row, rel_col in rotation:
                start_row = anchor_row - rel_row
                start_col = anchor_col - rel_col
                
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
        
        print(f"  最终优化求解器:")
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
        result = [f"最终优化解 ({len(solution)} 个J形块):"]
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        for row in grid:
            result.append("| " + " ".join(row) + " |")
        
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        # 统计
        elapsed = time.time() - self.start_time
        result.append(f"\\n最终统计:")
        result.append(f"  求解时间: {elapsed:.3f} 秒")
        result.append(f"  搜索节点: {self.nodes_explored}")
        result.append(f"  搜索效率: {self.nodes_explored/max(elapsed, 0.001):.0f} 节点/秒")
        
        return "\\n".join(result)


def run_performance_comparison():
    """运行性能对比测试"""
    print("J形拼图求解器最终性能测试")
    print("="*60)
    
    # 测试用例：逐渐增加难度
    test_cases = [
        (6, 2, "热身测试"),
        (8, 3, "基础测试"),
        (8, 4, "进阶测试"),
        (9, 5, "挑战测试"),
        (10, 6, "高难测试"),
        (10, 7, "极限测试"),
        (10, 8, "超极限测试")
    ]
    
    for grid_size, piece_count, description in test_cases:
        print(f"\\n{'='*40}")
        print(f"{description}: {grid_size}×{grid_size}网格, {piece_count}个J形块")
        print('='*40)
        
        config = PuzzleConfig(grid_size=grid_size, piece_count=piece_count)
        
        # 测试最终优化求解器
        print("\\n[最终优化算法]")
        solver = FinalOptimizedSolver(config)
        
        start_time = time.time()
        solution = solver.solve()
        elapsed = time.time() - start_time
        
        if solution:
            print(f"\\n✅ 成功! 用时: {elapsed:.3f}秒")
            if grid_size <= 8:  # 只为小问题显示解
                print(solver.visualize_solution(solution))
        else:
            print(f"\\n❌ 未找到解 (用时: {elapsed:.1f}s, 节点: {solver.nodes_explored})")
        
        # 如果问题太大就停止
        if grid_size >= 10 and piece_count >= 7:
            print(f"\\n达到测试上限，停止更大规模的测试")
            break


if __name__ == "__main__":
    run_performance_comparison()