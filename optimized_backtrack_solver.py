#!/usr/bin/env python3
"""
优化的回溯算法J形拼图求解器

核心优化策略：
1. 智能位置选择：优先选择约束最强的位置
2. 高效约束检查：使用位集合加速冲突检测
3. 连通性剪枝：确保剩余空间能容纳剩余块
4. 形状去重：避免重复搜索相同旋转
5. 提前终止：多层剪枝条件
"""

from typing import List, Tuple, Dict, Set, Optional
import time


class OptimizedBacktrackSolver:
    """优化的回溯求解器"""
    
    def __init__(self, grid_size: int = 10, piece_count: int = 11):
        self.grid_size = grid_size
        self.piece_count = piece_count
        
        # J形块标准形状
        self.base_shape = [
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0], 
            [1, 1, 1, 1, 1]
        ]
        
        # 预计算数据
        self.shapes = self._generate_unique_shapes()
        self.shape_size = self._count_shape_cells()
        self.all_placements = self._precompute_placements()
        
        # 搜索统计
        self.nodes_visited = 0
        self.start_time = 0
        
        print(f"初始化完成:")
        print(f"  网格: {grid_size}×{grid_size}")
        print(f"  块数: {piece_count}")
        print(f"  唯一形状: {len(self.shapes)}")
        print(f"  总放置方案: {len(self.all_placements)}")
    
    def _rotate_90(self, shape: List[List[int]]) -> List[List[int]]:
        """顺时针旋转90度"""
        rows, cols = len(shape), len(shape[0])
        return [[shape[rows-1-j][i] for j in range(rows)] for i in range(cols)]
    
    def _normalize_shape(self, shape: List[List[int]]) -> List[List[int]]:
        """标准化形状：移除空边界"""
        # 找到有效行和列的范围
        valid_rows = [i for i in range(len(shape)) if any(shape[i])]
        if not valid_rows:
            return [[]]
        
        min_row, max_row = min(valid_rows), max(valid_rows)
        valid_cols = [j for j in range(len(shape[0])) 
                     if any(shape[i][j] for i in range(len(shape)))]
        min_col, max_col = min(valid_cols), max(valid_cols)
        
        return [[shape[i][j] for j in range(min_col, max_col + 1)] 
                for i in range(min_row, max_row + 1)]
    
    def _generate_unique_shapes(self) -> List[List[List[int]]]:
        """生成所有唯一的旋转形状"""
        shapes = []
        seen = set()
        current = [row[:] for row in self.base_shape]
        
        for _ in range(4):  # 4个旋转方向
            normalized = self._normalize_shape(current)
            shape_key = tuple(tuple(row) for row in normalized)
            
            if shape_key not in seen:
                seen.add(shape_key)
                shapes.append(normalized)
            
            current = self._rotate_90(current)
        
        return shapes
    
    def _count_shape_cells(self) -> int:
        """计算J形块包含的格子数"""
        return sum(sum(row) for row in self.base_shape)
    
    def _get_shape_positions(self, shape: List[List[int]]) -> List[Tuple[int, int]]:
        """获取形状中所有1的相对位置"""
        return [(i, j) for i in range(len(shape)) 
                for j in range(len(shape[0])) if shape[i][j]]
    
    def _precompute_placements(self) -> List[Tuple[List[Tuple[int, int]], int]]:
        """预计算所有有效的放置方案"""
        placements = []
        
        for shape_id, shape in enumerate(self.shapes):
            positions = self._get_shape_positions(shape)
            
            # 尝试所有可能的起始位置
            for start_row in range(self.grid_size):
                for start_col in range(self.grid_size):
                    # 计算实际网格位置
                    grid_positions = [(start_row + dr, start_col + dc) 
                                    for dr, dc in positions]
                    
                    # 检查边界
                    if all(0 <= r < self.grid_size and 0 <= c < self.grid_size 
                          for r, c in grid_positions):
                        placements.append((grid_positions, shape_id))
        
        return placements
    
    def _can_place(self, grid: List[List[bool]], positions: List[Tuple[int, int]]) -> bool:
        """快速检查是否可以放置"""
        return all(not grid[r][c] for r, c in positions)
    
    def _place_piece(self, grid: List[List[bool]], positions: List[Tuple[int, int]], 
                     piece_id: int, placement_grid: List[List[int]]):
        """放置块"""
        for r, c in positions:
            grid[r][c] = True
            placement_grid[r][c] = piece_id + 1
    
    def _remove_piece(self, grid: List[List[bool]], positions: List[Tuple[int, int]], 
                      placement_grid: List[List[int]]):
        """移除块"""
        for r, c in positions:
            grid[r][c] = False
            placement_grid[r][c] = 0
    
    def _count_reachable_cells(self, grid: List[List[bool]], start_r: int, start_c: int) -> int:
        """从指定位置开始DFS计算连通的空格数"""
        if (start_r < 0 or start_r >= self.grid_size or 
            start_c < 0 or start_c >= self.grid_size or grid[start_r][start_c]):
            return 0
        
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        stack = [(start_r, start_c)]
        count = 0
        
        while stack:
            r, c = stack.pop()
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or 
                visited[r][c] or grid[r][c]):
                continue
            
            visited[r][c] = True
            count += 1
            
            # 添加相邻的空格
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                stack.append((r + dr, c + dc))
        
        return count
    
    def _check_connectivity_constraint(self, grid: List[List[bool]], remaining_pieces: int) -> bool:
        """检查连通性约束：剩余连通区域能否容纳剩余块"""
        if remaining_pieces == 0:
            return True
        
        min_cells_needed = remaining_pieces * self.shape_size
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        total_valid_cells = 0
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if not grid[i][j] and not visited[i][j]:
                    # 计算这个连通分量的大小
                    component_size = self._count_reachable_cells_with_visited(
                        grid, i, j, visited)
                    
                    # 只有足够大的连通分量才有用
                    if component_size >= self.shape_size:
                        total_valid_cells += component_size
        
        return total_valid_cells >= min_cells_needed
    
    def _count_reachable_cells_with_visited(self, grid: List[List[bool]], 
                                          start_r: int, start_c: int, 
                                          visited: List[List[bool]]) -> int:
        """带visited数组的DFS"""
        if (start_r < 0 or start_r >= self.grid_size or 
            start_c < 0 or start_c >= self.grid_size or 
            visited[start_r][start_c] or grid[start_r][start_c]):
            return 0
        
        stack = [(start_r, start_c)]
        count = 0
        
        while stack:
            r, c = stack.pop()
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or 
                visited[r][c] or grid[r][c]):
                continue
            
            visited[r][c] = True
            count += 1
            
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                stack.append((r + dr, c + dc))
        
        return count
    
    def _find_most_constrained_position(self, grid: List[List[bool]]) -> Optional[Tuple[int, int]]:
        """寻找最受约束的空位置（周围被占用格子最多的位置）"""
        best_pos = None
        max_constraints = -1
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if not grid[i][j]:  # 空位置
                    # 计算约束数（相邻被占用的格子数 + 边界约束）
                    constraints = 0
                    
                    for di, dj in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                        ni, nj = i + di, j + dj
                        if (ni < 0 or ni >= self.grid_size or 
                            nj < 0 or nj >= self.grid_size or grid[ni][nj]):
                            constraints += 1
                    
                    if constraints > max_constraints:
                        max_constraints = constraints
                        best_pos = (i, j)
        
        return best_pos
    
    def _get_valid_placements_for_position(self, target_pos: Tuple[int, int]) -> List[Tuple[List[Tuple[int, int]], int]]:
        """获取包含目标位置的所有有效放置方案"""
        target_r, target_c = target_pos
        valid_placements = []
        
        for positions, shape_id in self.all_placements:
            if (target_r, target_c) in positions:
                valid_placements.append((positions, shape_id))
        
        return valid_placements
    
    def _backtrack(self, grid: List[List[bool]], placement_grid: List[List[int]], 
                   piece_id: int) -> bool:
        """优化的回溯搜索"""
        self.nodes_visited += 1
        
        # 定期检查超时
        if self.nodes_visited % 1000 == 0:
            if time.time() - self.start_time > 60:  # 60秒超时
                return False
        
        # 成功条件
        if piece_id >= self.piece_count:
            return True
        
        # 连通性剪枝
        remaining_pieces = self.piece_count - piece_id
        if not self._check_connectivity_constraint(grid, remaining_pieces):
            return False
        
        # 选择最受约束的位置
        target_pos = self._find_most_constrained_position(grid)
        if target_pos is None:
            return piece_id >= self.piece_count
        
        # 获取包含目标位置的所有放置方案
        valid_placements = self._get_valid_placements_for_position(target_pos)
        
        # 尝试所有有效放置
        for positions, shape_id in valid_placements:
            if self._can_place(grid, positions):
                # 放置块
                self._place_piece(grid, positions, piece_id, placement_grid)
                
                # 递归搜索
                if self._backtrack(grid, placement_grid, piece_id + 1):
                    return True
                
                # 回溯
                self._remove_piece(grid, positions, placement_grid)
        
        return False
    
    def solve(self) -> Optional[List[List[int]]]:
        """求解主函数"""
        self.start_time = time.time()
        self.nodes_visited = 0
        
        print("开始优化回溯搜索...")
        
        # 初始化网格
        grid = [[False] * self.grid_size for _ in range(self.grid_size)]
        placement_grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        
        if self._backtrack(grid, placement_grid, 0):
            return placement_grid
        
        return None
    
    def visualize_solution(self, grid: List[List[int]]) -> str:
        """可视化解决方案"""
        if not grid:
            return "未找到解"
        
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        result = []
        result.append(f"找到解! ({self.piece_count} 个J形块)")
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
        
        # 统计信息
        elapsed = time.time() - self.start_time
        result.append(f"\n搜索统计:")
        result.append(f"  用时: {elapsed:.2f} 秒")
        result.append(f"  搜索节点: {self.nodes_visited}")
        result.append(f"  搜索速度: {self.nodes_visited/elapsed:.0f} 节点/秒")
        
        # 验证
        occupied_cells = sum(1 for row in grid for cell in row if cell > 0)
        result.append(f"  占用格子: {occupied_cells}")
        result.append(f"  空闲格子: {self.grid_size**2 - occupied_cells}")
        
        return "\n".join(result)


def main():
    """主函数"""
    print("优化回溯算法 J形拼图求解器")
    print("=" * 50)
    
    solver = OptimizedBacktrackSolver(grid_size=10, piece_count=11)
    solution = solver.solve()
    
    if solution:
        print(solver.visualize_solution(solution))
    else:
        elapsed = time.time() - solver.start_time
        print(f"在 {elapsed:.1f} 秒内未找到解")
        print(f"搜索了 {solver.nodes_visited} 个节点")


if __name__ == "__main__":
    main()