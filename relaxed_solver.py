#!/usr/bin/env python3
"""
宽松剪枝的求解器

减少过度剪枝，使用更简单但可靠的策略
"""

from typing import List, Tuple, Optional
import time
import random


class RelaxedSolver:
    """宽松剪枝求解器"""
    
    def __init__(self, grid_size: int = 10, piece_count: int = 11):
        self.grid_size = grid_size
        self.piece_count = piece_count
        
        # 生成J形块的旋转
        self.shapes = self._generate_shapes()
        self.shape_size = 8
        
        # 生成所有放置
        self.placements = self._generate_placements()
        
        # 搜索状态
        self.nodes = 0
        self.start_time = 0
        
        print(f"宽松求解器:")
        print(f"  形状数: {len(self.shapes)}")
        print(f"  放置数: {len(self.placements)}")
    
    def _generate_shapes(self) -> List[List[Tuple[int, int]]]:
        """生成J形块的旋转"""
        base = [
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0], 
            [1, 1, 1, 1, 1]
        ]
        
        def get_positions(shape):
            positions = []
            for i in range(len(shape)):
                for j in range(len(shape[0])):
                    if shape[i][j]:
                        positions.append((i, j))
            return positions
        
        def rotate_90(shape):
            rows, cols = len(shape), len(shape[0])
            return [[shape[rows-1-j][i] for j in range(rows)] for i in range(cols)]
        
        def normalize(positions):
            if not positions:
                return []
            min_r = min(r for r, c in positions)
            min_c = min(c for r, c in positions)
            return [(r - min_r, c - min_c) for r, c in positions]
        
        shapes = []
        seen = set()
        current = base
        
        for _ in range(4):
            pos = normalize(get_positions(current))
            key = tuple(sorted(pos))
            if key not in seen:
                seen.add(key)
                shapes.append(pos)
            current = rotate_90(current)
        
        return shapes
    
    def _generate_placements(self) -> List[List[Tuple[int, int]]]:
        """生成所有放置"""
        placements = []
        
        for shape in self.shapes:
            for r in range(self.grid_size):
                for c in range(self.grid_size):
                    positions = [(r + dr, c + dc) for dr, dc in shape]
                    
                    if all(0 <= nr < self.grid_size and 0 <= nc < self.grid_size 
                          for nr, nc in positions):
                        placements.append(positions)
        
        return placements
    
    def _can_place(self, grid: List[List[int]], positions: List[Tuple[int, int]]) -> bool:
        """检查是否可放置"""
        return all(grid[r][c] == 0 for r, c in positions)
    
    def _place(self, grid: List[List[int]], positions: List[Tuple[int, int]], piece_id: int):
        """放置"""
        for r, c in positions:
            grid[r][c] = piece_id
    
    def _remove(self, grid: List[List[int]], positions: List[Tuple[int, int]]):
        """移除"""
        for r, c in positions:
            grid[r][c] = 0
    
    def _minimal_pruning(self, grid: List[List[int]], remaining_pieces: int) -> bool:
        """最小化剪枝 - 只做基本检查"""
        if remaining_pieces == 0:
            return True
        
        # 只做最基本的空间检查
        empty_cells = sum(1 for row in grid for cell in row if cell == 0)
        min_needed = remaining_pieces * self.shape_size
        
        # 允许一些浪费空间
        return empty_cells >= min_needed - 8
    
    def _get_next_position(self, grid: List[List[int]]) -> Optional[Tuple[int, int]]:
        """获取下一个要填充的位置 - 简单的从左上角开始"""
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if grid[i][j] == 0:
                    return (i, j)
        return None
    
    def _get_placements_containing(self, target_pos: Tuple[int, int]) -> List[List[Tuple[int, int]]]:
        """获取包含目标位置的放置"""
        result = []
        for positions in self.placements:
            if target_pos in positions:
                result.append(positions)
        return result
    
    def _solve_recursive(self, grid: List[List[int]], piece_id: int) -> bool:
        """递归求解"""
        self.nodes += 1
        
        # 进度报告
        if self.nodes % 50000 == 0:
            elapsed = time.time() - self.start_time
            empty = sum(1 for row in grid for cell in row if cell == 0)
            print(f"  节点: {self.nodes}, 块: {piece_id}, 空格: {empty}, 时间: {elapsed:.1f}s")
        
        # 超时检查
        if self.nodes % 10000 == 0:
            if time.time() - self.start_time > 300:  # 5分钟超时
                return False
        
        # 成功条件
        if piece_id > self.piece_count:
            return True
        
        # 最小剪枝
        remaining = self.piece_count - piece_id + 1
        if not self._minimal_pruning(grid, remaining):
            return False
        
        # 选择下一个位置
        target_pos = self._get_next_position(grid)
        if target_pos is None:
            return piece_id > self.piece_count
        
        # 获取包含该位置的放置
        candidate_placements = self._get_placements_containing(target_pos)
        
        # 随机化顺序
        random.shuffle(candidate_placements)
        
        # 尝试放置
        for positions in candidate_placements:
            if self._can_place(grid, positions):
                self._place(grid, positions, piece_id)
                
                if self._solve_recursive(grid, piece_id + 1):
                    return True
                
                self._remove(grid, positions)
        
        return False
    
    def solve(self, max_attempts: int = 10) -> Optional[List[List[int]]]:
        """多次尝试求解"""
        print(f"开始求解，最多 {max_attempts} 次尝试...")
        
        for attempt in range(max_attempts):
            print(f"\n--- 尝试 {attempt + 1} ---")
            
            self.start_time = time.time()
            self.nodes = 0
            
            # 不同的随机种子
            random.seed(100 + attempt * 7)
            
            grid = [[0] * self.grid_size for _ in range(self.grid_size)]
            
            if self._solve_recursive(grid, 1):
                elapsed = time.time() - self.start_time
                print(f"✓ 成功! 用时: {elapsed:.2f}s, 节点: {self.nodes}")
                return grid
            else:
                elapsed = time.time() - self.start_time
                print(f"✗ 失败. 用时: {elapsed:.2f}s, 节点: {self.nodes}")
        
        return None
    
    def visualize(self, grid: List[List[int]]) -> str:
        """可视化"""
        if not grid:
            return "未找到解"
        
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        result = []
        result.append("✓ 找到解决方案！")
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
        
        # 统计
        occupied = sum(1 for row in grid for cell in row if cell > 0)
        result.append(f"\n占用格子: {occupied}, 空闲格子: {100 - occupied}")
        
        return "\n".join(result)


def main():
    """主函数"""
    print("宽松剪枝J形拼图求解器")
    print("=" * 40)
    
    solver = RelaxedSolver(10, 11)
    solution = solver.solve(max_attempts=5)
    
    print("\n" + "=" * 40)
    print(solver.visualize(solution))


if __name__ == "__main__":
    main()