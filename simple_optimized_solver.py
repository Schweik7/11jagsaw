#!/usr/bin/env python3
"""
简化但高效的回溯算法

专注于核心优化：
1. 最小剩余值启发式（MRV）
2. 简单连通性检查
3. 高效的约束传播
"""

from typing import List, Tuple, Optional
import time


class SimpleOptimizedSolver:
    """简化的高效求解器"""
    
    def __init__(self, grid_size: int = 10, piece_count: int = 11):
        self.grid_size = grid_size
        self.piece_count = piece_count
        
        # J形块的四个旋转
        self.shapes = self._get_rotations()
        self.shape_size = 8  # J形块包含8个格子
        
        # 预计算所有可能的放置
        self.placements = self._generate_placements()
        
        # 统计
        self.nodes = 0
        self.start_time = 0
        
        print(f"简化求解器初始化:")
        print(f"  网格: {grid_size}×{grid_size}")
        print(f"  形状数: {len(self.shapes)}")
        print(f"  放置数: {len(self.placements)}")
    
    def _get_rotations(self) -> List[List[Tuple[int, int]]]:
        """获取J形块的四个旋转，每个表示为位置列表"""
        base_shape = [
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
        
        def normalize(shape):
            positions = get_positions(shape)
            if not positions:
                return []
            min_r = min(r for r, c in positions)
            min_c = min(c for r, c in positions)
            return [(r - min_r, c - min_c) for r, c in positions]
        
        rotations = []
        seen = set()
        current = base_shape
        
        for _ in range(4):
            norm_pos = normalize(current)
            key = tuple(sorted(norm_pos))
            if key not in seen:
                seen.add(key)
                rotations.append(norm_pos)
            current = rotate_90(current)
        
        return rotations
    
    def _generate_placements(self) -> List[List[Tuple[int, int]]]:
        """生成所有有效放置"""
        placements = []
        
        for shape in self.shapes:
            for r in range(self.grid_size):
                for c in range(self.grid_size):
                    positions = [(r + dr, c + dc) for dr, dc in shape]
                    
                    # 检查边界
                    if all(0 <= nr < self.grid_size and 0 <= nc < self.grid_size 
                          for nr, nc in positions):
                        placements.append(positions)
        
        return placements
    
    def _can_place(self, grid: List[List[int]], positions: List[Tuple[int, int]]) -> bool:
        """检查是否可以放置"""
        return all(grid[r][c] == 0 for r, c in positions)
    
    def _place(self, grid: List[List[int]], positions: List[Tuple[int, int]], piece_id: int):
        """放置块"""
        for r, c in positions:
            grid[r][c] = piece_id
    
    def _remove(self, grid: List[List[int]], positions: List[Tuple[int, int]]):
        """移除块"""
        for r, c in positions:
            grid[r][c] = 0
    
    def _count_empty_cells(self, grid: List[List[int]]) -> int:
        """计算空格数"""
        return sum(1 for row in grid for cell in row if cell == 0)
    
    def _find_corner_cell(self, grid: List[List[int]]) -> Optional[Tuple[int, int]]:
        """找到最受约束的空格（角落优先）"""
        candidates = []
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if grid[i][j] == 0:
                    # 计算约束度（相邻占用格子数）
                    constraints = 0
                    for di, dj in [(0,1), (0,-1), (1,0), (-1,0)]:
                        ni, nj = i + di, j + dj
                        if (ni < 0 or ni >= self.grid_size or 
                            nj < 0 or nj >= self.grid_size or grid[ni][nj] != 0):
                            constraints += 1
                    
                    candidates.append((constraints, i, j))
        
        if not candidates:
            return None
        
        # 选择约束最多的位置
        candidates.sort(reverse=True)
        return (candidates[0][1], candidates[0][2])
    
    def _simple_connectivity_check(self, grid: List[List[int]], remaining_pieces: int) -> bool:
        """简单连通性检查"""
        if remaining_pieces == 0:
            return True
        
        empty_cells = self._count_empty_cells(grid)
        min_needed = remaining_pieces * self.shape_size
        
        # 基本空间检查
        if empty_cells < min_needed:
            return False
        
        # 简单连通性：如果剩余空间太分散，可能无法放置
        if remaining_pieces <= 3:
            return True  # 少量剩余块时不做严格检查
        
        # 检查是否有太多孤立的小区域
        return self._has_large_connected_regions(grid, remaining_pieces)
    
    def _has_large_connected_regions(self, grid: List[List[int]], remaining_pieces: int) -> bool:
        """检查是否有足够大的连通区域"""
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        large_regions = 0
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if grid[i][j] == 0 and not visited[i][j]:
                    size = self._dfs_count(grid, i, j, visited)
                    if size >= self.shape_size:
                        large_regions += 1
        
        # 至少需要足够的大区域来容纳剩余块
        return large_regions >= max(1, remaining_pieces // 2)
    
    def _dfs_count(self, grid: List[List[int]], r: int, c: int, visited: List[List[bool]]) -> int:
        """DFS计算连通区域大小"""
        if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
            visited[r][c] or grid[r][c] != 0):
            return 0
        
        visited[r][c] = True
        size = 1
        
        for dr, dc in [(0,1), (0,-1), (1,0), (-1,0)]:
            size += self._dfs_count(grid, r + dr, c + dc, visited)
        
        return size
    
    def _solve(self, grid: List[List[int]], piece_id: int) -> bool:
        """回溯求解"""
        self.nodes += 1
        
        # 超时检查
        if self.nodes % 10000 == 0:
            if time.time() - self.start_time > 30:
                return False
        
        # 完成检查
        if piece_id > self.piece_count:
            return True
        
        # 连通性剪枝
        remaining = self.piece_count - piece_id + 1
        if not self._simple_connectivity_check(grid, remaining):
            return False
        
        # 选择最约束的位置
        target = self._find_corner_cell(grid)
        if target is None:
            return piece_id > self.piece_count
        
        target_r, target_c = target
        
        # 尝试所有包含目标位置的放置
        for positions in self.placements:
            if (target_r, target_c) in positions and self._can_place(grid, positions):
                # 放置
                self._place(grid, positions, piece_id)
                
                # 递归
                if self._solve(grid, piece_id + 1):
                    return True
                
                # 回溯
                self._remove(grid, positions)
        
        return False
    
    def solve(self) -> Optional[List[List[int]]]:
        """求解主函数"""
        self.start_time = time.time()
        self.nodes = 0
        
        print("开始简化回溯搜索...")
        
        grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        
        if self._solve(grid, 1):
            return grid
        else:
            return None
    
    def visualize(self, grid: List[List[int]]) -> str:
        """可视化结果"""
        if not grid:
            return "未找到解"
        
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        result = []
        result.append("找到解决方案！")
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
        result.append(f"\n统计信息:")
        result.append(f"  用时: {elapsed:.2f} 秒")
        result.append(f"  搜索节点: {self.nodes}")
        result.append(f"  速度: {self.nodes/elapsed:.0f} 节点/秒")
        
        occupied = sum(1 for row in grid for cell in row if cell > 0)
        result.append(f"  占用格子: {occupied}")
        result.append(f"  空闲格子: {self.grid_size**2 - occupied}")
        
        return "\n".join(result)


def main():
    """主函数"""
    print("简化优化回溯求解器")
    print("=" * 40)
    
    solver = SimpleOptimizedSolver(10, 11)
    solution = solver.solve()
    
    print(solver.visualize(solution))


if __name__ == "__main__":
    main()