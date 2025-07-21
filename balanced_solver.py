#!/usr/bin/env python3
"""
平衡高效J形拼图求解器

平衡搜索效率和解的完整性：
1. 适度的剪枝策略
2. 智能的搜索顺序
3. 增量约束检查
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


class BalancedSolver:
    """平衡高效求解器"""
    
    def __init__(self, config: PuzzleConfig):
        self.config = config
        self.grid_size = config.grid_size
        self.piece_count = config.piece_count
        self.piece_size = sum(sum(row) for row in config.piece_shape)
        
        # 预计算
        self.rotations = self._generate_rotations()
        self.all_placements = self._generate_all_placements()
        
        # 统计
        self.nodes_explored = 0
        self.start_time = 0
        
    def _rotate_90(self, matrix: List[List[int]]) -> List[List[int]]:
        """顺时针旋转90度"""
        rows, cols = len(matrix), len(matrix[0])
        return [[matrix[rows-1-j][i] for j in range(rows)] for i in range(cols)]
    
    def _normalize_shape(self, shape: List[List[int]]) -> List[List[int]]:
        """标准化形状"""
        # 找到边界
        occupied_rows = [i for i in range(len(shape)) if any(shape[i])]
        if not occupied_rows:
            return [[]]
        
        min_row, max_row = min(occupied_rows), max(occupied_rows)
        occupied_cols = [j for j in range(len(shape[0])) 
                        if any(shape[i][j] for i in range(len(shape)))]
        min_col, max_col = min(occupied_cols), max(occupied_cols)
        
        return [[shape[i][j] for j in range(min_col, max_col + 1)] 
                for i in range(min_row, max_row + 1)]
    
    def _generate_rotations(self) -> List[List[List[int]]]:
        """生成所有旋转(去重)"""
        seen = set()
        rotations = []
        current = [row[:] for row in self.config.piece_shape]
        
        for _ in range(4):
            normalized = self._normalize_shape(current)
            key = tuple(tuple(row) for row in normalized)
            
            if key not in seen:
                seen.add(key)
                rotations.append(normalized)
            
            current = self._rotate_90(current)
        
        return rotations
    
    def _get_shape_cells(self, shape: List[List[int]]) -> List[Tuple[int, int]]:
        """获取形状的相对位置"""
        return [(i, j) for i in range(len(shape)) 
                for j in range(len(shape[0])) if shape[i][j] == 1]
    
    def _generate_all_placements(self) -> List[Tuple[int, int, List[Tuple[int, int]]]]:
        """生成所有可能的放置方案"""
        placements = []
        
        for rot_id, rotation in enumerate(self.rotations):
            shape_cells = self._get_shape_cells(rotation)
            
            for start_row in range(self.grid_size):
                for start_col in range(self.grid_size):
                    # 计算绝对位置
                    abs_positions = [(start_row + dr, start_col + dc) 
                                   for dr, dc in shape_cells]
                    
                    # 检查边界
                    if all(0 <= r < self.grid_size and 0 <= c < self.grid_size 
                           for r, c in abs_positions):
                        placements.append((rot_id, start_row, start_col, abs_positions))
        
        return placements
    
    def _can_place(self, grid: List[List[int]], positions: List[Tuple[int, int]]) -> bool:
        """检查是否可以放置"""
        return all(grid[r][c] == 0 for r, c in positions)
    
    def _place_piece(self, grid: List[List[int]], positions: List[Tuple[int, int]], piece_id: int):
        """放置棋子"""
        for r, c in positions:
            grid[r][c] = piece_id + 1
    
    def _remove_piece(self, grid: List[List[int]], positions: List[Tuple[int, int]]):
        """移除棋子"""
        for r, c in positions:
            grid[r][c] = 0
    
    def _count_empty_cells(self, grid: List[List[int]]) -> int:
        """计算空格数量"""
        return sum(row.count(0) for row in grid)
    
    def _get_most_constrained_cell(self, grid: List[List[int]]) -> Optional[Tuple[int, int]]:
        """找到最受约束的空格子"""
        best_cell = None
        min_freedom = float('inf')
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if grid[i][j] == 0:
                    # 计算这个位置的"自由度"(可以被多少种放置方案覆盖)
                    freedom = 0
                    for _, _, _, positions in self.all_placements:
                        if (i, j) in positions and self._can_place(grid, positions):
                            freedom += 1
                    
                    if freedom < min_freedom:
                        min_freedom = freedom
                        best_cell = (i, j)
        
        return best_cell
    
    def _solve_recursive(self, grid: List[List[int]], piece_id: int, 
                        placed_positions: List[List[Tuple[int, int]]]) -> bool:
        """递归求解"""
        self.nodes_explored += 1
        
        # 超时检查
        if self.nodes_explored % 500 == 0:
            elapsed = time.time() - self.start_time
            if elapsed > 30:  # 30秒超时
                return False
            
            # 进度报告
            if self.nodes_explored % 5000 == 0:
                print(f"  已搜索 {self.nodes_explored} 节点, 已放置 {piece_id} 块, 用时 {elapsed:.1f}s")
        
        # 完成检查
        if piece_id >= self.piece_count:
            return True
        
        # 空间检查：剩余空间是否足够
        empty_cells = self._count_empty_cells(grid)
        needed_cells = (self.piece_count - piece_id) * self.piece_size
        if empty_cells < needed_cells:
            return False
        
        # 找到最受约束的位置
        target_cell = self._get_most_constrained_cell(grid)
        if target_cell is None:
            return piece_id >= self.piece_count
        
        target_r, target_c = target_cell
        
        # 尝试所有包含目标位置的放置方案
        attempted = 0
        for rot_id, start_row, start_col, positions in self.all_placements:
            if (target_r, target_c) in positions:
                if self._can_place(grid, positions):
                    attempted += 1
                    
                    # 放置
                    self._place_piece(grid, positions, piece_id)
                    placed_positions.append(positions)
                    
                    # 递归
                    if self._solve_recursive(grid, piece_id + 1, placed_positions):
                        return True
                    
                    # 回溯
                    placed_positions.pop()
                    self._remove_piece(grid, positions)
        
        return False
    
    def solve(self) -> Optional[List[Dict]]:
        """求解主函数"""
        self.start_time = time.time()
        self.nodes_explored = 0
        
        print(f"平衡求解器初始化:")
        print(f"  网格大小: {self.grid_size}×{self.grid_size}")
        print(f"  J形块数量: {self.piece_count}")
        print(f"  唯一旋转数: {len(self.rotations)}")
        print(f"  总放置方案: {len(self.all_placements)}")
        print(f"  理论占用率: {self.piece_count * self.piece_size / (self.grid_size**2) * 100:.1f}%")
        print()
        
        grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        placed_positions = []
        
        print("开始搜索...")
        success = self._solve_recursive(grid, 0, placed_positions)
        
        if success:
            # 构建解决方案
            solution = []
            for i, positions in enumerate(placed_positions):
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
        result = [f"找到解决方案! ({len(solution)} 个J形块)"]
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        for row in grid:
            result.append("| " + " ".join(row) + " |")
        
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        # 统计信息
        elapsed = time.time() - self.start_time
        occupied = len(solution) * self.piece_size
        total = self.grid_size * self.grid_size
        
        result.append(f"\\n求解统计:")
        result.append(f"  用时: {elapsed:.2f} 秒")
        result.append(f"  搜索节点: {self.nodes_explored}")
        result.append(f"  搜索效率: {self.nodes_explored/elapsed:.0f} 节点/秒")
        result.append(f"  占用格子: {occupied}/{total} ({occupied/total*100:.1f}%)")
        
        return "\n".join(result)


def main():
    """主函数：逐步测试"""
    print("平衡高效J形拼图求解器")
    print("="*50)
    
    # 从小规模开始测试
    test_cases = [
        (6, 2, "热身: 6×6放2块"),
        (7, 3, "小试: 7×7放3块"), 
        (8, 4, "进阶: 8×8放4块"),
        (9, 6, "挑战: 9×9放6块"),
        (10, 8, "高难: 10×10放8块"),
        (10, 10, "极限: 10×10放10块")
    ]
    
    for grid_size, piece_count, desc in test_cases:
        print(f"\n{'-'*30}")
        print(f"{desc}")
        print('-'*30)
        
        config = PuzzleConfig(grid_size=grid_size, piece_count=piece_count)
        solver = BalancedSolver(config)
        
        solution = solver.solve()
        
        if solution:
            print(solver.visualize_solution(solution))
            
            # 对于大问题，找到解就够了
            if grid_size >= 9:
                print(f"\n成功解决 {grid_size}×{grid_size} 放置 {piece_count} 块的问题!")
                break
        else:
            elapsed = time.time() - solver.start_time
            print(f"在 {elapsed:.1f} 秒内未找到解")
            print(f"搜索了 {solver.nodes_explored} 个节点")


if __name__ == "__main__":
    main()