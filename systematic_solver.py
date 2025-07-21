#!/usr/bin/env python3
"""
系统性的求解器 - 更仔细的调试和搜索
"""

from typing import List, Tuple, Optional
import time


class SystematicSolver:
    """系统性求解器"""
    
    def __init__(self, grid_size: int = 10, piece_count: int = 11):
        self.grid_size = grid_size
        self.piece_count = piece_count
        
        # 生成J形块的所有旋转
        self.shapes = self._generate_shapes()
        self.shape_size = 8
        
        # 生成所有放置
        self.placements = self._generate_placements()
        
        # 调试信息
        self.nodes = 0
        self.start_time = 0
        self.max_depth = 0
        
        print(f"系统性求解器初始化:")
        print(f"  形状数: {len(self.shapes)}")
        print(f"  放置数: {len(self.placements)}")
        self._print_shapes()
    
    def _generate_shapes(self) -> List[List[Tuple[int, int]]]:
        """生成J形块的所有旋转"""
        base = [
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0], 
            [1, 1, 1, 1, 1]
        ]
        
        def get_positions(shape):
            return [(i, j) for i in range(len(shape)) 
                    for j in range(len(shape[0])) if shape[i][j]]
        
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
        
        for rotation in range(4):
            pos = normalize(get_positions(current))
            key = tuple(sorted(pos))
            if key not in seen:
                seen.add(key)
                shapes.append(pos)
            current = rotate_90(current)
        
        return shapes
    
    def _print_shapes(self):
        """打印所有形状"""
        print("  所有形状:")
        for i, shape in enumerate(self.shapes):
            print(f"    形状 {i}: {shape}")
            
            # 可视化
            max_r = max(r for r, c in shape)
            max_c = max(c for r, c in shape)
            
            for r in range(max_r + 1):
                line = "      "
                for c in range(max_c + 1):
                    if (r, c) in shape:
                        line += "█"
                    else:
                        line += "·"
                print(line)
            print()
    
    def _generate_placements(self) -> List[Tuple[List[Tuple[int, int]], int]]:
        """生成所有放置"""
        placements = []
        
        for shape_id, shape in enumerate(self.shapes):
            for r in range(self.grid_size):
                for c in range(self.grid_size):
                    positions = [(r + dr, c + dc) for dr, dc in shape]
                    
                    # 检查边界
                    if all(0 <= nr < self.grid_size and 0 <= nc < self.grid_size 
                          for nr, nc in positions):
                        placements.append((positions, shape_id))
        
        return placements
    
    def _can_place(self, grid: List[List[int]], positions: List[Tuple[int, int]]) -> bool:
        """检查是否可以放置"""
        for r, c in positions:
            if grid[r][c] != 0:
                return False
        return True
    
    def _place(self, grid: List[List[int]], positions: List[Tuple[int, int]], piece_id: int):
        """放置块"""
        for r, c in positions:
            grid[r][c] = piece_id
    
    def _remove(self, grid: List[List[int]], positions: List[Tuple[int, int]]):
        """移除块"""
        for r, c in positions:
            grid[r][c] = 0
    
    def _print_grid(self, grid: List[List[int]], title: str = ""):
        """打印网格"""
        if title:
            print(f"  {title}:")
        for row in grid:
            line = "    "
            for cell in row:
                if cell == 0:
                    line += "·"
                else:
                    line += str(cell % 10)
            print(line)
        print()
    
    def _basic_pruning(self, grid: List[List[int]], remaining_pieces: int) -> bool:
        """基本剪枝"""
        if remaining_pieces == 0:
            return True
        
        # 计算空格数
        empty_cells = sum(1 for row in grid for cell in row if cell == 0)
        min_needed = remaining_pieces * self.shape_size
        
        if empty_cells < min_needed:
            return False
        
        # 非常宽松的检查
        return True
    
    def _solve_recursive(self, grid: List[List[int]], piece_id: int, depth: int = 0) -> bool:
        """递归求解"""
        self.nodes += 1
        
        # 更新最大深度
        if depth > self.max_depth:
            self.max_depth = depth
            print(f"  新的最大深度: {depth}, 已放置块: {piece_id - 1}")
            if depth <= 3:  # 只在前几层显示网格
                self._print_grid(grid, f"深度 {depth} 的网格")
        
        # 进度报告
        if self.nodes % 100000 == 0:
            elapsed = time.time() - self.start_time
            empty = sum(1 for row in grid for cell in row if cell == 0)
            print(f"  节点: {self.nodes}, 深度: {depth}, 空格: {empty}, 时间: {elapsed:.1f}s")
        
        # 超时检查
        if time.time() - self.start_time > 600:  # 10分钟超时
            return False
        
        # 成功条件
        if piece_id > self.piece_count:
            return True
        
        # 基本剪枝
        remaining = self.piece_count - piece_id + 1
        if not self._basic_pruning(grid, remaining):
            return False
        
        # 尝试所有可能的放置
        valid_placements = 0
        for positions, shape_id in self.placements:
            if self._can_place(grid, positions):
                valid_placements += 1
                
                # 放置
                self._place(grid, positions, piece_id)
                
                # 递归
                if self._solve_recursive(grid, piece_id + 1, depth + 1):
                    return True
                
                # 回溯
                self._remove(grid, positions)
        
        # 如果没有有效放置，记录
        if valid_placements == 0:
            print(f"  深度 {depth}: 没有有效放置，回溯")
        
        return False
    
    def solve(self) -> Optional[List[List[int]]]:
        """求解"""
        print("开始系统性搜索...")
        
        self.start_time = time.time()
        self.nodes = 0
        self.max_depth = 0
        
        grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        
        # 显示初始状态
        self._print_grid(grid, "初始空网格")
        
        if self._solve_recursive(grid, 1):
            return grid
        else:
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
        elapsed = time.time() - self.start_time
        result.append(f"\n搜索统计:")
        result.append(f"  用时: {elapsed:.2f} 秒")
        result.append(f"  节点: {self.nodes}")
        result.append(f"  最大深度: {self.max_depth}")
        
        occupied = sum(1 for row in grid for cell in row if cell > 0)
        result.append(f"  占用格子: {occupied}")
        result.append(f"  空闲格子: {100 - occupied}")
        
        return "\n".join(result)


def main():
    """主函数"""
    print("系统性J形拼图求解器")
    print("=" * 40)
    
    solver = SystematicSolver(10, 11)
    solution = solver.solve()
    
    print("\n" + "=" * 40)
    print(solver.visualize(solution))


if __name__ == "__main__":
    main()