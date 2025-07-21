#!/usr/bin/env python3
"""
简单高效J形拼图求解器

回到基础但高效的回溯算法，专注于：
1. 最小化搜索空间
2. 快速冲突检测
3. 智能的块放置顺序
"""

from typing import List, Tuple, Dict, Set, Optional
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


class SimpleFastSolver:
    """简单高效求解器"""
    
    def __init__(self, config: PuzzleConfig):
        self.config = config
        self.grid_size = config.grid_size
        self.piece_count = config.piece_count
        self.piece_size = sum(sum(row) for row in config.piece_shape)
        
        # 预计算所有可能的J形块放置
        self.piece_placements = self._precompute_placements()
        
        # 搜索统计
        self.nodes_explored = 0
        self.start_time = 0
        
    def _rotate_90(self, matrix: List[List[int]]) -> List[List[int]]:
        """顺时针旋转90度"""
        return [[matrix[len(matrix)-1-j][i] for j in range(len(matrix))] 
                for i in range(len(matrix[0]))]
    
    def _get_piece_cells(self, shape: List[List[int]]) -> List[Tuple[int, int]]:
        """获取形状中所有1的位置"""
        return [(i, j) for i in range(len(shape)) 
                for j in range(len(shape[0])) if shape[i][j] == 1]
    
    def _precompute_placements(self) -> List[List[Tuple[int, int]]]:
        """预计算所有可能的J形块放置位置"""
        placements = []
        
        # 生成4个旋转
        current_shape = [row[:] for row in self.config.piece_shape]
        
        for rotation in range(4):
            shape_cells = self._get_piece_cells(current_shape)
            
            # 尝试所有可能的起始位置
            for start_row in range(self.grid_size):
                for start_col in range(self.grid_size):
                    # 计算绝对位置
                    absolute_positions = []
                    valid = True
                    
                    for rel_row, rel_col in shape_cells:
                        abs_row = start_row + rel_row
                        abs_col = start_col + rel_col
                        
                        # 检查边界
                        if (abs_row < 0 or abs_row >= self.grid_size or
                            abs_col < 0 or abs_col >= self.grid_size):
                            valid = False
                            break
                        
                        absolute_positions.append((abs_row, abs_col))
                    
                    if valid:
                        placements.append(absolute_positions)
            
            # 旋转到下一个方向
            current_shape = self._rotate_90(current_shape)
        
        return placements
    
    def _is_valid_placement(self, grid: List[List[int]], positions: List[Tuple[int, int]]) -> bool:
        """检查位置是否都为空"""
        return all(grid[r][c] == 0 for r, c in positions)
    
    def _place_piece(self, grid: List[List[int]], positions: List[Tuple[int, int]], piece_id: int):
        """在网格上放置块"""
        for r, c in positions:
            grid[r][c] = piece_id + 1
    
    def _remove_piece(self, grid: List[List[int]], positions: List[Tuple[int, int]]):
        """从网格上移除块"""
        for r, c in positions:
            grid[r][c] = 0
    
    def _get_first_empty_cell(self, grid: List[List[int]]) -> Optional[Tuple[int, int]]:
        """获取第一个空格子（按行优先顺序）"""
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if grid[i][j] == 0:
                    return (i, j)
        return None
    
    def _solve_backtrack(self, grid: List[List[int]], piece_id: int, 
                        solution: List[List[Tuple[int, int]]]) -> bool:
        """回溯求解"""
        self.nodes_explored += 1
        
        # 进度报告和超时检查
        if self.nodes_explored % 1000 == 0:
            elapsed = time.time() - self.start_time
            if elapsed > 60:  # 60秒超时
                return False
            
            if self.nodes_explored % 10000 == 0:
                empty_cells = sum(row.count(0) for row in grid)
                print(f"  进度: 已放置{piece_id}块, 剩余{empty_cells}空格, "
                      f"搜索{self.nodes_explored}节点, 用时{elapsed:.1f}s")
        
        # 成功条件
        if piece_id >= self.piece_count:
            return True
        
        # 简单剪枝：检查剩余空间
        empty_cells = sum(row.count(0) for row in grid)
        needed_cells = (self.piece_count - piece_id) * self.piece_size
        if empty_cells < needed_cells:
            return False
        
        # 找到第一个空格作为锚点
        anchor = self._get_first_empty_cell(grid)
        if anchor is None:
            return piece_id >= self.piece_count
        
        anchor_r, anchor_c = anchor
        
        # 尝试所有能覆盖锚点的放置方案
        for positions in self.piece_placements:
            # 必须包含锚点
            if (anchor_r, anchor_c) not in positions:
                continue
            
            # 检查是否可以放置
            if self._is_valid_placement(grid, positions):
                # 放置块
                self._place_piece(grid, positions, piece_id)
                solution.append(positions)
                
                # 递归搜索
                if self._solve_backtrack(grid, piece_id + 1, solution):
                    return True
                
                # 回溯
                solution.pop()
                self._remove_piece(grid, positions)
        
        return False
    
    def solve(self) -> Optional[List[Dict]]:
        """求解主函数"""
        self.start_time = time.time()
        self.nodes_explored = 0
        
        print(f"简单高效求解器:")
        print(f"  网格: {self.grid_size}×{self.grid_size}")
        print(f"  J形块: {self.piece_count}个")
        print(f"  预计算方案: {len(self.piece_placements)}个")
        print(f"  空间利用率: {self.piece_count * self.piece_size}/{self.grid_size**2} = "
              f"{self.piece_count * self.piece_size / self.grid_size**2 * 100:.1f}%")
        print()
        
        grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        solution_positions = []
        
        print("开始搜索...")
        
        if self._solve_backtrack(grid, 0, solution_positions):
            # 转换为标准格式
            solution = []
            for i, positions in enumerate(solution_positions):
                solution.append({
                    'id': i,
                    'piece_id': i,
                    'grid_positions': positions
                })
            return solution
        
        return None
    
    def visualize_solution(self, solution: List[Dict]) -> str:
        """可视化解决方案"""
        if not solution:
            return "未找到解决方案"
        
        # 创建显示网格
        grid = [['.' for _ in range(self.grid_size)] 
                for _ in range(self.grid_size)]
        
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        # 填充解决方案
        for i, placement in enumerate(solution):
            letter = letters[i % len(letters)]
            for row, col in placement['grid_positions']:
                grid[row][col] = letter
        
        # 生成显示文本
        result = [f"解决方案 ({len(solution)} 个J形块):"]
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        for row in grid:
            result.append("| " + " ".join(row) + " |")
        
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        # 添加统计信息
        elapsed = time.time() - self.start_time
        result.append(f"\\n统计信息:")
        result.append(f"  求解时间: {elapsed:.2f} 秒")
        result.append(f"  搜索节点: {self.nodes_explored}")
        result.append(f"  搜索速度: {self.nodes_explored/max(elapsed, 0.001):.0f} 节点/秒")
        
        occupied = len(solution) * self.piece_size
        total = self.grid_size * self.grid_size
        result.append(f"  空间利用: {occupied}/{total} ({occupied/total*100:.1f}%)")
        
        return "\n".join(result)


def main():
    """逐步测试不同规模"""
    print("简单高效J形拼图求解器")
    print("="*60)
    
    # 测试用例：从简单到复杂
    test_cases = [
        (6, 2),   # 简单测试
        (7, 3),   # 中等测试  
        (8, 4),   # 进阶测试
        (10, 6),  # 挑战测试
        (10, 8),  # 高难测试
        (10, 10), # 极限测试
    ]
    
    for grid_size, piece_count in test_cases:
        print(f"\\n{'='*30}")
        print(f"测试: {grid_size}×{grid_size} 网格, {piece_count} 个J形块")
        print('='*30)
        
        config = PuzzleConfig(grid_size=grid_size, piece_count=piece_count)
        solver = SimpleFastSolver(config)
        
        solution = solver.solve()
        
        if solution:
            print("\\n成功找到解!")
            print(solver.visualize_solution(solution))
        else:
            elapsed = time.time() - solver.start_time
            print(f"\\n在 {elapsed:.1f} 秒内未找到解")
            print(f"总共搜索了 {solver.nodes_explored} 个节点")


if __name__ == "__main__":
    main()