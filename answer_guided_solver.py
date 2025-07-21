#!/usr/bin/env python3
"""
基于答案分析的求解器

从答案中学习到的关键信息：
1. 确实存在解
2. 有12个空格分散在网格中
3. J形块的不同旋转都被使用
4. 搜索策略需要更宽松的剪枝
"""

from typing import List, Tuple, Optional, Set
import time
import random


class AnswerGuidedSolver:
    """基于答案分析的求解器"""
    
    def __init__(self, grid_size: int = 10, piece_count: int = 11):
        self.grid_size = grid_size
        self.piece_count = piece_count
        
        # J形块的所有旋转变体
        self.all_shapes = self._generate_all_rotations()
        self.shape_size = 8
        
        # 预计算所有放置
        self.placements = self._generate_all_placements()
        
        # 搜索参数
        self.nodes = 0
        self.start_time = 0
        self.max_time = 120  # 2分钟超时
        
        print(f"答案引导求解器初始化:")
        print(f"  网格: {grid_size}×{grid_size}")
        print(f"  块数: {piece_count}")
        print(f"  旋转形状数: {len(self.all_shapes)}")
        print(f"  总放置数: {len(self.placements)}")
    
    def _rotate_90(self, positions: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """旋转位置列表90度"""
        if not positions:
            return []
        
        # 找到边界
        max_r = max(r for r, c in positions)
        
        # 旋转：(r, c) -> (c, max_r - r)
        rotated = [(c, max_r - r) for r, c in positions]
        
        # 标准化到原点
        min_r = min(r for r, c in rotated)
        min_c = min(c for r, c in rotated)
        
        return [(r - min_r, c - min_c) for r, c in rotated]
    
    def _flip_horizontal(self, positions: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """水平翻转"""
        if not positions:
            return []
        
        max_c = max(c for r, c in positions)
        flipped = [(r, max_c - c) for r, c in positions]
        
        # 标准化
        min_r = min(r for r, c in flipped)
        min_c = min(c for r, c in flipped)
        
        return [(r - min_r, c - min_c) for r, c in flipped]
    
    def _generate_all_rotations(self) -> List[List[Tuple[int, int]]]:
        """生成J形块的所有8种变体（4个旋转 × 2个翻转）"""
        # 基础J形块
        base_shape = [
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0], 
            [1, 1, 1, 1, 1]
        ]
        
        base_positions = []
        for i in range(len(base_shape)):
            for j in range(len(base_shape[0])):
                if base_shape[i][j]:
                    base_positions.append((i, j))
        
        # 标准化到原点
        min_r = min(r for r, c in base_positions)
        min_c = min(c for r, c in base_positions)
        base_positions = [(r - min_r, c - min_c) for r, c in base_positions]
        
        all_shapes = []
        seen = set()
        
        # 生成所有变体
        for flip in [False, True]:
            current = base_positions[:]
            if flip:
                current = self._flip_horizontal(current)
            
            for _ in range(4):  # 4个旋转
                normalized = tuple(sorted(current))
                if normalized not in seen:
                    seen.add(normalized)
                    all_shapes.append(list(current))
                current = self._rotate_90(current)
        
        return all_shapes
    
    def _generate_all_placements(self) -> List[Tuple[List[Tuple[int, int]], int]]:
        """生成所有有效放置"""
        placements = []
        
        for shape_id, shape in enumerate(self.all_shapes):
            for start_r in range(self.grid_size):
                for start_c in range(self.grid_size):
                    positions = [(start_r + dr, start_c + dc) for dr, dc in shape]
                    
                    # 检查边界
                    if all(0 <= r < self.grid_size and 0 <= c < self.grid_size 
                          for r, c in positions):
                        placements.append((positions, shape_id))
        
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
    
    def _relaxed_connectivity_check(self, grid: List[List[int]], remaining: int) -> bool:
        """宽松的连通性检查"""
        if remaining <= 2:
            return True  # 最后几个块时不严格检查
        
        empty_cells = self._count_empty_cells(grid)
        min_needed = remaining * self.shape_size
        
        # 基本空间检查，但允许一些浪费
        return empty_cells >= min_needed - 4  # 允许最多4个格子的"浪费"
    
    def _get_promising_positions(self, grid: List[List[int]]) -> List[Tuple[int, int]]:
        """获取有希望的位置（不要过度约束）"""
        candidates = []
        
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if grid[i][j] == 0:
                    # 计算约束数，但不要太偏向角落
                    constraints = 0
                    for di, dj in [(0,1), (0,-1), (1,0), (-1,0)]:
                        ni, nj = i + di, j + dj
                        if (ni < 0 or ni >= self.grid_size or 
                            nj < 0 or nj >= self.grid_size or grid[ni][nj] != 0):
                            constraints += 1
                    
                    candidates.append((constraints, i, j))
        
        # 排序但保持一些随机性
        candidates.sort(key=lambda x: x[0] + random.random() * 0.5, reverse=True)
        
        # 返回前几个候选位置
        return [(r, c) for _, r, c in candidates[:min(5, len(candidates))]]
    
    def _get_placements_for_positions(self, positions: List[Tuple[int, int]]) -> List[Tuple[List[Tuple[int, int]], int]]:
        """获取包含任一目标位置的放置方案"""
        target_set = set(positions)
        valid_placements = []
        
        for placement_positions, shape_id in self.placements:
            if any(pos in target_set for pos in placement_positions):
                valid_placements.append((placement_positions, shape_id))
        
        return valid_placements
    
    def _solve_recursive(self, grid: List[List[int]], piece_id: int) -> bool:
        """递归求解"""
        self.nodes += 1
        
        # 超时检查
        if self.nodes % 5000 == 0:
            if time.time() - self.start_time > self.max_time:
                return False
            
            # 进度报告
            if self.nodes % 50000 == 0:
                empty = self._count_empty_cells(grid)
                print(f"  节点: {self.nodes}, 已放置: {piece_id}, 空格: {empty}")
        
        # 成功条件
        if piece_id > self.piece_count:
            return True
        
        # 宽松剪枝
        remaining = self.piece_count - piece_id + 1
        if not self._relaxed_connectivity_check(grid, remaining):
            return False
        
        # 获取有希望的位置
        target_positions = self._get_promising_positions(grid)
        if not target_positions:
            return piece_id > self.piece_count
        
        # 获取相关的放置方案
        candidate_placements = self._get_placements_for_positions(target_positions)
        
        # 随机化顺序以避免局部最优
        random.shuffle(candidate_placements)
        
        # 尝试放置
        for positions, shape_id in candidate_placements:
            if self._can_place(grid, positions):
                self._place(grid, positions, piece_id)
                
                if self._solve_recursive(grid, piece_id + 1):
                    return True
                
                self._remove(grid, positions)
        
        return False
    
    def solve(self, max_attempts: int = 5) -> Optional[List[List[int]]]:
        """多次尝试求解"""
        print(f"开始求解，最多尝试 {max_attempts} 次...")
        
        for attempt in range(max_attempts):
            print(f"\n尝试 {attempt + 1}/{max_attempts}:")
            
            self.start_time = time.time()
            self.nodes = 0
            
            # 使用不同的随机种子
            random.seed(42 + attempt)
            
            grid = [[0] * self.grid_size for _ in range(self.grid_size)]
            
            if self._solve_recursive(grid, 1):
                elapsed = time.time() - self.start_time
                print(f"✓ 在第 {attempt + 1} 次尝试中找到解! ({elapsed:.2f}秒)")
                return grid
            else:
                elapsed = time.time() - self.start_time
                print(f"✗ 第 {attempt + 1} 次尝试失败 ({elapsed:.2f}秒, {self.nodes} 节点)")
        
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
        result.append(f"\n最终统计:")
        result.append(f"  用时: {elapsed:.2f} 秒")
        result.append(f"  搜索节点: {self.nodes}")
        result.append(f"  速度: {self.nodes/elapsed:.0f} 节点/秒")
        
        occupied = sum(1 for row in grid for cell in row if cell > 0)
        result.append(f"  占用格子: {occupied}")
        result.append(f"  空闲格子: {self.grid_size**2 - occupied}")
        
        return "\n".join(result)


def main():
    """主函数"""
    print("答案引导的J形拼图求解器")
    print("=" * 50)
    
    solver = AnswerGuidedSolver(10, 11)
    solution = solver.solve(max_attempts=3)
    
    print("\n" + "=" * 50)
    print(solver.visualize(solution))


if __name__ == "__main__":
    main()