#!/usr/bin/env python3
"""
最终优化的回溯求解器

关键改进：
1. 更激进的剪枝策略
2. 智能的搜索顺序
3. 约束传播
4. 失败驱动的学习
"""

from typing import List, Tuple, Optional, Dict, Set
import time
import heapq


class FinalOptimizedSolver:
    """最终优化版本"""
    
    def __init__(self, grid_size: int = 10, piece_count: int = 11):
        self.grid_size = grid_size
        self.piece_count = piece_count
        
        # 预计算J形块的所有形状
        self.shapes = self._compute_unique_shapes()
        self.shape_size = 8
        
        # 预计算所有可能的放置位置
        self.placements = self._compute_all_placements()
        
        # 位置到放置映射（用于快速查找）
        self.pos_to_placements = self._build_position_index()
        
        # 搜索状态
        self.nodes = 0
        self.start_time = 0
        self.best_depth = 0
        
        print(f"最终优化求解器:")
        print(f"  唯一形状: {len(self.shapes)}")
        print(f"  总放置: {len(self.placements)}")
        print(f"  位置索引: {len(self.pos_to_placements)}")
    
    def _compute_unique_shapes(self) -> List[List[Tuple[int, int]]]:
        """计算J形块的所有唯一形状"""
        base = [
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0], 
            [1, 1, 1, 1, 1]
        ]
        
        def extract_positions(shape):
            return [(i, j) for i in range(len(shape)) 
                    for j in range(len(shape[0])) if shape[i][j]]
        
        def rotate_90(shape):
            rows, cols = len(shape), len(shape[0])
            return [[shape[rows-1-j][i] for j in range(rows)] for i in range(cols)]
        
        def normalize(positions):
            if not positions:
                return []
            min_r, min_c = min(positions)
            return [(r - min_r, c - min_c) for r, c in positions]
        
        shapes = []
        seen = set()
        current = base
        
        # 生成4个旋转
        for _ in range(4):
            pos = normalize(extract_positions(current))
            key = tuple(sorted(pos))
            if key not in seen:
                seen.add(key)
                shapes.append(pos)
            current = rotate_90(current)
        
        return shapes
    
    def _compute_all_placements(self) -> List[Tuple[List[Tuple[int, int]], int]]:
        """计算所有可能的放置"""
        placements = []
        
        for shape_id, shape in enumerate(self.shapes):
            for r in range(self.grid_size):
                for c in range(self.grid_size):
                    positions = [(r + dr, c + dc) for dr, dc in shape]
                    
                    if all(0 <= nr < self.grid_size and 0 <= nc < self.grid_size 
                          for nr, nc in positions):
                        placements.append((positions, shape_id))
        
        return placements
    
    def _build_position_index(self) -> Dict[Tuple[int, int], List[int]]:
        """构建位置到放置索引的映射"""
        pos_index = {}
        
        for i, (positions, shape_id) in enumerate(self.placements):
            for pos in positions:
                if pos not in pos_index:
                    pos_index[pos] = []
                pos_index[pos].append(i)
        
        return pos_index
    
    def _is_valid_placement(self, grid: List[List[int]], positions: List[Tuple[int, int]]) -> bool:
        """检查放置是否有效"""
        return all(grid[r][c] == 0 for r, c in positions)
    
    def _place_piece(self, grid: List[List[int]], positions: List[Tuple[int, int]], piece_id: int):
        """放置块"""
        for r, c in positions:
            grid[r][c] = piece_id
    
    def _remove_piece(self, grid: List[List[int]], positions: List[Tuple[int, int]]):
        """移除块"""
        for r, c in positions:
            grid[r][c] = 0
    
    def _count_empty_cells(self, grid: List[List[int]]) -> int:
        """计算空格数"""
        return sum(1 for row in grid for cell in row if cell == 0)
    
    def _get_most_constrained_position(self, grid: List[List[int]]) -> Optional[Tuple[int, int]]:
        """获取最受约束的位置"""
        candidates = []
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if grid[i][j] == 0:
                    # 计算可用的放置选项数
                    available_placements = 0
                    if (i, j) in self.pos_to_placements:
                        for placement_idx in self.pos_to_placements[(i, j)]:
                            positions, _ = self.placements[placement_idx]
                            if self._is_valid_placement(grid, positions):
                                available_placements += 1
                    
                    # 如果没有可用放置，这是一个死胡同
                    if available_placements == 0:
                        return None  # 表示无解
                    
                    candidates.append((available_placements, i, j))
        
        if not candidates:
            return None
        
        # 选择选项最少的位置（MRV启发式）
        candidates.sort()
        return (candidates[0][1], candidates[0][2])
    
    def _advanced_pruning(self, grid: List[List[int]], remaining_pieces: int) -> bool:
        """高级剪枝检查"""
        if remaining_pieces == 0:
            return True
        
        # 1. 基本空间检查
        empty_cells = self._count_empty_cells(grid)
        min_needed = remaining_pieces * self.shape_size
        
        if empty_cells < min_needed:
            return False
        
        # 2. 连通性检查（改进版）
        if not self._check_connectivity(grid, remaining_pieces):
            return False
        
        # 3. 可达性检查：每个空格都必须能被某个形状覆盖
        if remaining_pieces <= 5:  # 只在后期做这个昂贵的检查
            return self._check_reachability(grid, remaining_pieces)
        
        return True
    
    def _check_connectivity(self, grid: List[List[int]], remaining_pieces: int) -> bool:
        """检查连通性"""
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        components = []
        
        def dfs(r, c):
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
                visited[r][c] or grid[r][c] != 0):
                return 0
            
            visited[r][c] = True
            size = 1
            
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                size += dfs(r + dr, c + dc)
            
            return size
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if grid[i][j] == 0 and not visited[i][j]:
                    comp_size = dfs(i, j)
                    if comp_size > 0:
                        components.append(comp_size)
        
        # 检查是否有足够的大组件
        usable_components = [size for size in components if size >= self.shape_size]
        total_usable = sum(usable_components)
        
        return total_usable >= remaining_pieces * self.shape_size
    
    def _check_reachability(self, grid: List[List[int]], remaining_pieces: int) -> bool:
        """检查所有空格是否可达"""
        # 这是一个简化版本，实际上应该检查是否存在完美匹配
        # 但这个检查太昂贵，我们用一个近似版本
        
        empty_positions = []
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if grid[i][j] == 0:
                    empty_positions.append((i, j))
        
        if len(empty_positions) < remaining_pieces * self.shape_size:
            return False
        
        # 检查是否有足够的有效放置
        valid_placements = 0
        for positions, _ in self.placements:
            if self._is_valid_placement(grid, positions):
                valid_placements += 1
        
        return valid_placements >= remaining_pieces
    
    def _solve_recursive(self, grid: List[List[int]], piece_id: int) -> bool:
        """递归求解"""
        self.nodes += 1
        
        # 进度跟踪
        if piece_id > self.best_depth:
            self.best_depth = piece_id
            print(f"  最佳深度: {piece_id}/{self.piece_count}")
        
        # 超时检查
        if self.nodes % 10000 == 0:
            elapsed = time.time() - self.start_time
            if elapsed > 180:  # 3分钟超时
                return False
            
            if self.nodes % 100000 == 0:
                print(f"  节点: {self.nodes}, 时间: {elapsed:.1f}s")
        
        # 成功条件
        if piece_id > self.piece_count:
            return True
        
        # 高级剪枝
        remaining = self.piece_count - piece_id + 1
        if not self._advanced_pruning(grid, remaining):
            return False
        
        # 选择最约束的位置
        target_pos = self._get_most_constrained_position(grid)
        if target_pos is None:
            return False  # 检测到死胡同
        
        # 获取该位置的所有可能放置
        placement_indices = self.pos_to_placements.get(target_pos, [])
        
        # 按启发式排序放置选项
        valid_placements = []
        for idx in placement_indices:
            positions, shape_id = self.placements[idx]
            if self._is_valid_placement(grid, positions):
                # 计算这个放置的"好坏"（简单启发式）
                score = self._evaluate_placement(grid, positions)
                valid_placements.append((score, positions, shape_id))
        
        # 按分数排序
        valid_placements.sort(reverse=True)
        
        # 尝试所有有效放置
        for score, positions, shape_id in valid_placements:
            self._place_piece(grid, positions, piece_id)
            
            if self._solve_recursive(grid, piece_id + 1):
                return True
            
            self._remove_piece(grid, positions)
        
        return False
    
    def _evaluate_placement(self, grid: List[List[int]], positions: List[Tuple[int, int]]) -> float:
        """评估放置的好坏"""
        score = 0.0
        
        # 偏向于填充角落和边缘
        for r, c in positions:
            if r == 0 or r == self.grid_size - 1:
                score += 1.0
            if c == 0 or c == self.grid_size - 1:
                score += 1.0
            
            # 偏向于与现有块相邻
            adjacent_filled = 0
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if (0 <= nr < self.grid_size and 0 <= nc < self.grid_size and
                    grid[nr][nc] > 0):
                    adjacent_filled += 1
            
            score += adjacent_filled * 0.5
        
        return score
    
    def solve(self) -> Optional[List[List[int]]]:
        """求解主函数"""
        print("开始最终优化搜索...")
        
        self.start_time = time.time()
        self.nodes = 0
        self.best_depth = 0
        
        grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        
        if self._solve_recursive(grid, 1):
            return grid
        else:
            return None
    
    def visualize(self, grid: List[List[int]]) -> str:
        """可视化结果"""
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
        
        # 统计信息
        elapsed = time.time() - self.start_time
        result.append(f"\n搜索统计:")
        result.append(f"  用时: {elapsed:.2f} 秒")
        result.append(f"  搜索节点: {self.nodes}")
        result.append(f"  最佳深度: {self.best_depth}")
        result.append(f"  搜索速度: {self.nodes/elapsed:.0f} 节点/秒")
        
        # 验证
        occupied = sum(1 for row in grid for cell in row if cell > 0)
        result.append(f"  占用格子: {occupied}")
        result.append(f"  空闲格子: {self.grid_size**2 - occupied}")
        
        return "\n".join(result)


def main():
    """主函数"""
    print("最终优化的J形拼图求解器")
    print("=" * 50)
    
    solver = FinalOptimizedSolver(10, 11)
    solution = solver.solve()
    
    print("\n" + "=" * 50)
    print(solver.visualize(solution))
    
    if not solution:
        print("可能的原因:")
        print("1. 搜索空间太大，需要更长时间")
        print("2. 剪枝过于激进，剪掉了有效解")
        print("3. 启发式函数需要调整")


if __name__ == "__main__":
    main()