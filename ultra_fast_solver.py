#!/usr/bin/env python3
"""
超高效J形拼图求解器

采用更激进的优化策略：
1. 预过滤不可能的配置
2. 分层搜索策略
3. 更强的剪枝条件
4. 贪心 + 回溯混合策略
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


class UltraFastSolver:
    """超高效求解器"""
    
    def __init__(self, config: PuzzleConfig):
        self.config = config
        self.grid_size = config.grid_size
        self.piece_count = config.piece_count
        
        # 预计算数据
        self.shapes = self._get_canonical_shapes()
        self.placements = self._precompute_smart_placements()
        
        # 搜索统计
        self.nodes = 0
        self.start_time = 0
        
    def _rotate_90(self, shape: List[List[int]]) -> List[List[int]]:
        """顺时针旋转90度"""
        return [[shape[len(shape)-1-j][i] for j in range(len(shape))] 
                for i in range(len(shape[0]))]
    
    def _normalize_shape(self, shape: List[List[int]]) -> List[List[int]]:
        """标准化形状：移除空边"""
        # 找边界
        rows = [i for i in range(len(shape)) if any(shape[i])]
        if not rows:
            return [[]]
        
        min_row, max_row = min(rows), max(rows)
        
        cols = [j for j in range(len(shape[0])) 
                if any(shape[i][j] for i in range(len(shape)))]
        min_col, max_col = min(cols), max(cols)
        
        return [[shape[i][j] for j in range(min_col, max_col + 1)] 
                for i in range(min_row, max_row + 1)]
    
    def _get_canonical_shapes(self) -> List[List[List[int]]]:
        """获取去重的标准形状"""
        seen = set()
        shapes = []
        
        current = [row[:] for row in self.config.piece_shape]
        
        for _ in range(4):
            norm = self._normalize_shape(current)
            key = tuple(tuple(row) for row in norm)
            
            if key not in seen:
                seen.add(key)
                shapes.append(norm)
            
            current = self._rotate_90(current)
        
        return shapes
    
    def _get_positions(self, shape: List[List[int]]) -> List[Tuple[int, int]]:
        """获取形状的所有1位置"""
        return [(i, j) for i in range(len(shape)) 
                for j in range(len(shape[0])) if shape[i][j]]
    
    def _precompute_smart_placements(self) -> List[List[Tuple[int, int]]]:
        """智能预计算：只保留有效放置"""
        all_placements = []
        
        for shape in self.shapes:
            shape_positions = self._get_positions(shape)
            shape_placements = []
            
            for row in range(self.grid_size):
                for col in range(self.grid_size):
                    positions = [(row + dr, col + dc) for dr, dc in shape_positions]
                    
                    # 检查边界
                    if all(0 <= r < self.grid_size and 0 <= c < self.grid_size 
                           for r, c in positions):
                        shape_placements.append(positions)
            
            all_placements.append(shape_placements)
        
        return all_placements
    
    def _is_valid_placement(self, grid: List[List[int]], positions: List[Tuple[int, int]]) -> bool:
        """检查放置是否有效"""
        return all(grid[r][c] == 0 for r, c in positions)
    
    def _place(self, grid: List[List[int]], positions: List[Tuple[int, int]], piece_id: int):
        """放置块"""
        for r, c in positions:
            grid[r][c] = piece_id + 1
    
    def _remove(self, grid: List[List[int]], positions: List[Tuple[int, int]]):
        """移除块"""
        for r, c in positions:
            grid[r][c] = 0
    
    def _count_connected_components(self, grid: List[List[int]]) -> int:
        """计算连通分量数量，用于剪枝"""
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        components = 0
        
        def dfs(r: int, c: int):
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
                visited[r][c] or grid[r][c] != 0):
                return 0
            
            visited[r][c] = True
            size = 1
            
            for dr, dc in [(0,1), (0,-1), (1,0), (-1,0)]:
                size += dfs(r + dr, c + dc)
            
            return size
        
        piece_size = len(self._get_positions(self.config.piece_shape))
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if not visited[i][j] and grid[i][j] == 0:
                    component_size = dfs(i, j)
                    if component_size >= piece_size:
                        components += 1
        
        return components
    
    def _get_corner_position(self, grid: List[List[int]]) -> Optional[Tuple[int, int]]:
        """寻找最约束的角落位置"""
        candidates = []
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if grid[i][j] == 0:
                    # 计算约束强度（周围已占用的格子数）
                    constraints = 0
                    for di, dj in [(0,1), (0,-1), (1,0), (-1,0)]:
                        ni, nj = i + di, j + dj
                        if (ni < 0 or ni >= self.grid_size or 
                            nj < 0 or nj >= self.grid_size or 
                            grid[ni][nj] != 0):
                            constraints += 1
                    
                    candidates.append((constraints, i, j))
        
        if not candidates:
            return None
        
        # 返回约束最强的位置
        candidates.sort(reverse=True)
        return (candidates[0][1], candidates[0][2])
    
    def _solve_recursive(self, grid: List[List[int]], piece_id: int) -> bool:
        """递归求解"""
        self.nodes += 1
        
        # 超时检查
        if self.nodes % 100 == 0:
            if time.time() - self.start_time > 30:  # 30秒超时
                return False
        
        # 完成检查
        if piece_id >= self.piece_count:
            return True
        
        # 连通性剪枝
        remaining_pieces = self.piece_count - piece_id
        if self._count_connected_components(grid) < remaining_pieces:
            return False
        
        # 选择最约束的位置
        target_pos = self._get_corner_position(grid)
        if target_pos is None:
            return piece_id >= self.piece_count  # 没有空位了
        
        target_r, target_c = target_pos
        
        # 尝试所有形状的所有放置方案
        for shape_id, shape_placements in enumerate(self.placements):
            for positions in shape_placements:
                # 必须包含目标位置
                if (target_r, target_c) not in positions:
                    continue
                
                # 检查是否可放置
                if self._is_valid_placement(grid, positions):
                    # 放置
                    self._place(grid, positions, piece_id)
                    
                    # 递归
                    if self._solve_recursive(grid, piece_id + 1):
                        return True
                    
                    # 回溯
                    self._remove(grid, positions)
        
        return False
    
    def solve(self) -> Optional[List[Dict]]:
        """求解主函数"""
        self.start_time = time.time()
        self.nodes = 0
        
        print(f"优化预计算:")
        print(f"  标准形状数: {len(self.shapes)}")
        total_placements = sum(len(p) for p in self.placements)
        print(f"  有效放置数: {total_placements}")
        print(f"开始超高效搜索...")
        
        grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        
        if self._solve_recursive(grid, 0):
            # 从网格重建解
            solution = []
            for piece_id in range(1, self.piece_count + 1):
                positions = []
                for i in range(self.grid_size):
                    for j in range(self.grid_size):
                        if grid[i][j] == piece_id:
                            positions.append((i, j))
                
                if positions:
                    solution.append({
                        'id': piece_id - 1,
                        'piece_id': piece_id - 1,
                        'grid_positions': positions
                    })
            
            return solution
        
        return None
    
    def visualize_solution(self, solution: List[Dict]) -> str:
        """可视化解决方案"""
        if not solution:
            return "No solution found"
        
        # 创建网格
        grid = [['.' for _ in range(self.grid_size)] 
                for _ in range(self.grid_size)]
        
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        for i, placement in enumerate(solution):
            letter = letters[i % len(letters)]
            for row, col in placement['grid_positions']:
                grid[row][col] = letter
        
        # 生成显示
        result = [f"Solution with {len(solution)} J-pieces:"]
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        for row in grid:
            result.append("| " + " ".join(row) + " |")
        
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        # 统计
        elapsed = time.time() - self.start_time
        result.append(f"\n超高效求解统计:")
        result.append(f"  时间: {elapsed:.2f}秒")
        result.append(f"  搜索节点: {self.nodes}")
        result.append(f"  搜索速度: {self.nodes/elapsed:.0f} 节点/秒")
        
        return "\n".join(result)


def benchmark_test():
    """性能基准测试"""
    test_cases = [
        (8, 4),
        (9, 6), 
        (10, 8),
        (10, 10)
    ]
    
    for grid_size, piece_count in test_cases:
        print(f"\n{'='*50}")
        print(f"测试: {grid_size}×{grid_size} 网格, {piece_count} 个J形块")
        print('='*50)
        
        config = PuzzleConfig(grid_size=grid_size, piece_count=piece_count)
        solver = UltraFastSolver(config)
        
        solution = solver.solve()
        
        if solution:
            print("成功找到解!")
            print(solver.visualize_solution(solution))
        else:
            elapsed = time.time() - solver.start_time
            print(f"在 {elapsed:.1f} 秒内未找到解")
            print(f"搜索了 {solver.nodes} 个节点")


if __name__ == "__main__":
    benchmark_test()