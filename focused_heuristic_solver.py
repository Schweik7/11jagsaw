#!/usr/bin/env python3
"""
专注于11块问题的启发式求解器

基于答案分析的针对性优化：
1. 专门优化的启发式函数
2. 智能的搜索策略
3. 高效的剪枝机制
4. 基于答案模式的指导
"""

from typing import List, Tuple, Optional, Dict, Set
import time
import random
from dataclasses import dataclass


@dataclass
class SearchConfig:
    """搜索配置"""
    max_time: int = 300  # 5分钟
    max_candidates: int = 8
    early_pruning: bool = True
    adaptive_weights: bool = True


class FocusedHeuristicSolver:
    """专注的启发式求解器"""
    
    def __init__(self, grid_size: int = 10, piece_count: int = 11):
        self.grid_size = grid_size
        self.piece_count = piece_count
        self.shape_size = 8
        
        # 生成J形块的旋转
        self.shapes = self._generate_unique_shapes()
        
        # 搜索配置
        self.config = SearchConfig()
        
        # 搜索状态
        self.grid = [[0] * grid_size for _ in range(grid_size)]
        self.nodes = 0
        self.start_time = 0
        self.best_depth = 0
        
        # 启发式权重（动态调整）
        self.weights = {
            'adjacency': 2.0,
            'compactness': 1.5,
            'connectivity': 3.0,
            'deadlock_avoidance': 4.0,
            'corner_preference': 1.0,
            'space_efficiency': 2.5
        }
        
        print(f"专注启发式求解器:")
        print(f"  网格: {grid_size}×{grid_size}")
        print(f"  J形块: {piece_count}个")
        print(f"  形状数: {len(self.shapes)}")
    
    def _generate_unique_shapes(self) -> List[List[Tuple[int, int]]]:
        """生成J形块的唯一旋转"""
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
        
        for _ in range(4):
            pos = normalize(get_positions(current))
            key = tuple(sorted(pos))
            if key not in seen:
                seen.add(key)
                shapes.append(pos)
            current = rotate_90(current)
        
        return shapes
    
    def _can_place(self, shape: List[Tuple[int, int]], start_r: int, start_c: int) -> bool:
        """检查是否可以放置"""
        for dr, dc in shape:
            r, c = start_r + dr, start_c + dc
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
                self.grid[r][c] != 0):
                return False
        return True
    
    def _place(self, shape: List[Tuple[int, int]], start_r: int, start_c: int, piece_id: int):
        """放置块"""
        for dr, dc in shape:
            r, c = start_r + dr, start_c + dc
            self.grid[r][c] = piece_id
    
    def _remove(self, shape: List[Tuple[int, int]], start_r: int, start_c: int):
        """移除块"""
        for dr, dc in shape:
            r, c = start_r + dr, start_c + dc
            self.grid[r][c] = 0
    
    def _adjacency_score(self, shape: List[Tuple[int, int]], start_r: int, start_c: int) -> float:
        """邻接度评分"""
        score = 0.0
        positions = [(start_r + dr, start_c + dc) for dr, dc in shape]
        
        for r, c in positions:
            adjacent_count = 0
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nr, nc = r + dr, c + dc
                if (0 <= nr < self.grid_size and 0 <= nc < self.grid_size):
                    if self.grid[nr][nc] > 0:
                        adjacent_count += 1
                else:
                    adjacent_count += 0.5  # 边界也算半个邻接
            
            score += adjacent_count
        
        return score
    
    def _compactness_score(self, shape: List[Tuple[int, int]], start_r: int, start_c: int) -> float:
        """紧密度评分"""
        positions = [(start_r + dr, start_c + dc) for dr, dc in shape]
        
        if not positions:
            return 0.0
        
        # 计算边界框
        min_r = min(r for r, c in positions)
        max_r = max(r for r, c in positions)
        min_c = min(c for r, c in positions)
        max_c = max(c for r, c in positions)
        
        bbox_area = (max_r - min_r + 1) * (max_c - min_c + 1)
        compactness = len(positions) / bbox_area if bbox_area > 0 else 0
        
        return compactness * 10.0
    
    def _connectivity_score(self, shape: List[Tuple[int, int]], start_r: int, start_c: int) -> float:
        """连通性评分"""
        # 模拟放置
        temp_grid = [row[:] for row in self.grid]
        for dr, dc in shape:
            r, c = start_r + dr, start_c + dc
            temp_grid[r][c] = 999
        
        # 计算连通分量
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        components = []
        
        def dfs(r, c):
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
                visited[r][c] or temp_grid[r][c] != 0):
                return 0
            
            visited[r][c] = True
            size = 1
            
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                size += dfs(r + dr, c + dc)
            
            return size
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if not visited[i][j] and temp_grid[i][j] == 0:
                    comp_size = dfs(i, j)
                    if comp_size > 0:
                        components.append(comp_size)
        
        if not components:
            return 0.0
        
        # 偏好大的连通分量
        large_components = [s for s in components if s >= self.shape_size]
        small_components = [s for s in components if s < self.shape_size]
        
        score = len(large_components) * 5.0 - len(small_components) * 3.0
        
        # 单一大连通分量奖励
        if len(large_components) == 1:
            score += 8.0
        
        return score
    
    def _deadlock_avoidance_score(self, shape: List[Tuple[int, int]], start_r: int, start_c: int) -> float:
        """死锁避免评分"""
        # 模拟放置
        temp_grid = [row[:] for row in self.grid]
        for dr, dc in shape:
            r, c = start_r + dr, start_c + dc
            temp_grid[r][c] = 999
        
        # 计算无法填充的小空间
        visited = [[False] * self.grid_size for _ in range(self.grid_size)]
        small_spaces = 0
        
        def dfs(r, c):
            if (r < 0 or r >= self.grid_size or c < 0 or c >= self.grid_size or
                visited[r][c] or temp_grid[r][c] != 0):
                return 0
            
            visited[r][c] = True
            size = 1
            
            for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                size += dfs(r + dr, c + dc)
            
            return size
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if not visited[i][j] and temp_grid[i][j] == 0:
                    space_size = dfs(i, j)
                    if 0 < space_size < self.shape_size:
                        small_spaces += 1
        
        # 小空间越多，扣分越多
        if small_spaces > 2:
            return -20.0
        elif small_spaces > 0:
            return -10.0
        else:
            return 5.0
    
    def _corner_preference_score(self, shape: List[Tuple[int, int]], start_r: int, start_c: int) -> float:
        """角落偏好评分"""
        positions = [(start_r + dr, start_c + dc) for dr, dc in shape]
        score = 0.0
        
        for r, c in positions:
            # 角落加分
            if (r, c) in [(0, 0), (0, self.grid_size-1), 
                         (self.grid_size-1, 0), (self.grid_size-1, self.grid_size-1)]:
                score += 3.0
            # 边缘加分
            elif (r == 0 or r == self.grid_size-1 or c == 0 or c == self.grid_size-1):
                score += 1.0
        
        return score
    
    def _space_efficiency_score(self, shape: List[Tuple[int, int]], start_r: int, start_c: int,
                               remaining_pieces: int) -> float:
        """空间效率评分"""
        if remaining_pieces == 0:
            return 10.0
        
        # 模拟放置
        temp_grid = [row[:] for row in self.grid]
        for dr, dc in shape:
            r, c = start_r + dr, start_c + dc
            temp_grid[r][c] = 999
        
        # 计算剩余空间
        remaining_space = sum(1 for row in temp_grid for cell in row if cell == 0)
        needed_space = remaining_pieces * self.shape_size
        
        if remaining_space < needed_space:
            return -15.0
        
        # 计算空间利用率
        efficiency = needed_space / remaining_space if remaining_space > 0 else 0
        
        return efficiency * 8.0
    
    def _comprehensive_score(self, shape: List[Tuple[int, int]], start_r: int, start_c: int,
                           remaining_pieces: int) -> float:
        """综合评分"""
        if not self._can_place(shape, start_r, start_c):
            return -float('inf')
        
        adjacency = self._adjacency_score(shape, start_r, start_c)
        compactness = self._compactness_score(shape, start_r, start_c)
        connectivity = self._connectivity_score(shape, start_r, start_c)
        deadlock_avoidance = self._deadlock_avoidance_score(shape, start_r, start_c)
        corner_preference = self._corner_preference_score(shape, start_r, start_c)
        space_efficiency = self._space_efficiency_score(shape, start_r, start_c, remaining_pieces)
        
        total_score = (adjacency * self.weights['adjacency'] +
                      compactness * self.weights['compactness'] +
                      connectivity * self.weights['connectivity'] +
                      deadlock_avoidance * self.weights['deadlock_avoidance'] +
                      corner_preference * self.weights['corner_preference'] +
                      space_efficiency * self.weights['space_efficiency'])
        
        return total_score
    
    def _get_best_moves(self, remaining_pieces: int) -> List[Tuple[float, int, int, int]]:
        """获取最佳移动"""
        moves = []
        
        for shape_id, shape in enumerate(self.shapes):
            for r in range(self.grid_size):
                for c in range(self.grid_size):
                    if self._can_place(shape, r, c):
                        score = self._comprehensive_score(shape, r, c, remaining_pieces)
                        if score > -float('inf'):
                            moves.append((score, shape_id, r, c))
        
        # 排序并返回最佳候选
        moves.sort(reverse=True)
        return moves[:self.config.max_candidates]
    
    def _adjust_weights(self, depth: int):
        """动态调整权重"""
        if not self.config.adaptive_weights:
            return
        
        progress = depth / self.piece_count
        
        if progress < 0.4:
            # 早期：重视形状适应和邻接
            self.weights['adjacency'] = 2.5
            self.weights['compactness'] = 2.0
            self.weights['corner_preference'] = 1.5
        elif progress < 0.8:
            # 中期：重视连通性和空间效率
            self.weights['connectivity'] = 4.0
            self.weights['space_efficiency'] = 3.0
            self.weights['deadlock_avoidance'] = 5.0
        else:
            # 后期：极度重视死锁避免
            self.weights['deadlock_avoidance'] = 8.0
            self.weights['connectivity'] = 6.0
            self.weights['space_efficiency'] = 4.0
    
    def _solve_recursive(self, piece_id: int) -> bool:
        """递归求解"""
        self.nodes += 1
        
        # 进度跟踪
        if piece_id > self.best_depth:
            self.best_depth = piece_id
            print(f"  新深度: {piece_id}/{self.piece_count}")
        
        # 超时检查
        if self.nodes % 10000 == 0:
            elapsed = time.time() - self.start_time
            if elapsed > self.config.max_time:
                return False
            
            if self.nodes % 50000 == 0:
                empty = sum(1 for row in self.grid for cell in row if cell == 0)
                print(f"  状态: 节点{self.nodes}, 深度{piece_id}, 空格{empty}, 时间{elapsed:.1f}s")
        
        # 成功条件
        if piece_id >= self.piece_count:
            return True
        
        # 动态调整权重
        self._adjust_weights(piece_id)
        
        # 基本剪枝
        if self.config.early_pruning:
            empty_cells = sum(1 for row in self.grid for cell in row if cell == 0)
            needed_cells = (self.piece_count - piece_id) * self.shape_size
            if empty_cells < needed_cells:
                return False
        
        # 获取最佳移动
        remaining_pieces = self.piece_count - piece_id
        best_moves = self._get_best_moves(remaining_pieces)
        
        if not best_moves:
            return False
        
        # 调试输出
        if piece_id <= 2:
            print(f"    深度{piece_id}最佳分数: {best_moves[0][0]:.2f}")
        
        # 尝试最佳移动
        for score, shape_id, r, c in best_moves:
            # 过滤分数过低的移动
            if score < -10.0:
                continue
            
            shape = self.shapes[shape_id]
            self._place(shape, r, c, piece_id + 1)
            
            if self._solve_recursive(piece_id + 1):
                return True
            
            self._remove(shape, r, c)
        
        return False
    
    def solve(self) -> Optional[List[List[int]]]:
        """求解主函数"""
        print("开始专注启发式搜索...")
        
        self.start_time = time.time()
        self.nodes = 0
        self.best_depth = 0
        
        # 重置网格
        self.grid = [[0] * self.grid_size for _ in range(self.grid_size)]
        
        if self._solve_recursive(0):
            return self.grid
        else:
            return None
    
    def visualize(self, grid: List[List[int]]) -> str:
        """可视化结果"""
        if not grid:
            return "未找到解"
        
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        result = []
        result.append("✓ 专注启发式找到解决方案！")
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
        result.append(f"\n专注启发式统计:")
        result.append(f"  用时: {elapsed:.2f} 秒")
        result.append(f"  节点: {self.nodes}")
        result.append(f"  最佳深度: {self.best_depth}")
        result.append(f"  搜索效率: {self.nodes/elapsed:.0f} 节点/秒")
        
        occupied = sum(1 for row in grid for cell in row if cell > 0)
        result.append(f"  占用格子: {occupied}")
        result.append(f"  空闲格子: {100 - occupied}")
        
        return "\n".join(result)


def main():
    """主函数"""
    print("专注启发式J形拼图求解器")
    print("=" * 50)
    
    solver = FocusedHeuristicSolver(10, 11)
    solution = solver.solve()
    
    print("\n" + "=" * 50)
    print(solver.visualize(solution))


if __name__ == "__main__":
    main()