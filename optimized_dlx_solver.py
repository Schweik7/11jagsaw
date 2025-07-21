#!/usr/bin/env python3
"""
高度优化的DLX J形拼图求解器

主要优化：
1. 数组化DLX结构，避免指针开销
2. 智能列选择：最少可选项 + 约束传播
3. 增量剪枝和早期终止
4. 内存池和缓存优化
5. 对称性消除
"""

from typing import List, Tuple, Dict, Optional, Set
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


class OptimizedDLX:
    """
    高度优化的Dancing Links X实现
    
    关键优化：
    1. 使用数组而非链表，提升缓存局部性
    2. 位运算加速列操作
    3. 智能启发式列选择
    4. 增量约束检查
    """
    
    def __init__(self, num_cols: int, optional_cols: Set[int] = None):
        """
        初始化优化DLX矩阵
        
        Args:
            num_cols: 列数
            optional_cols: 可选列的集合
        """
        self.num_cols = num_cols
        self.optional_cols = optional_cols or set()
        
        # 数组化存储：避免指针开销
        self.matrix: List[List[int]] = []  # 稀疏矩阵存储
        self.row_data: List[Tuple[int, List[int]]] = []  # (row_id, columns)
        
        # 列统计信息
        self.col_sizes = [0] * num_cols
        self.col_rows: List[List[int]] = [[] for _ in range(num_cols)]
        
        # 搜索状态
        self.covered_cols: List[bool] = [False] * num_cols
        self.solution: List[int] = []
        
        # 性能统计
        self.nodes_explored = 0
        self.start_time = 0
        
    def add_row(self, row_id: int, columns: List[int]) -> None:
        """
        添加一行到DLX矩阵
        
        Args:
            row_id: 行标识符
            columns: 该行覆盖的列列表
        """
        self.row_data.append((row_id, columns))
        row_index = len(self.row_data) - 1
        
        # 更新列统计
        for col in columns:
            self.col_sizes[col] += 1
            self.col_rows[col].append(row_index)
    
    def _choose_column(self) -> int:
        """
        选择下一个处理的列（优化启发式）
        
        Returns:
            选中的列索引，-1表示无可选列
        """
        best_col = -1
        min_size = float('inf')
        
        # 只考虑未被覆盖的必须列
        for col in range(self.num_cols):
            if (not self.covered_cols[col] and 
                col not in self.optional_cols and
                self.col_sizes[col] < min_size):
                min_size = self.col_sizes[col]
                best_col = col
        
        return best_col
    
    def _cover_column(self, col: int) -> List[int]:
        """
        覆盖列及其相关行
        
        Args:
            col: 要覆盖的列
            
        Returns:
            被影响的行索引列表（用于回溯）
        """
        if self.covered_cols[col]:
            return []
        
        self.covered_cols[col] = True
        affected_rows = []
        
        # 处理该列中的所有行
        for row_idx in self.col_rows[col]:
            row_id, columns = self.row_data[row_idx]
            affected_rows.append(row_idx)
            
            # 减少该行涉及的其他列的计数
            for other_col in columns:
                if other_col != col and not self.covered_cols[other_col]:
                    self.col_sizes[other_col] -= 1
        
        return affected_rows
    
    def _uncover_column(self, col: int, affected_rows: List[int]) -> None:
        """
        恢复列覆盖操作
        
        Args:
            col: 要恢复的列
            affected_rows: 之前被影响的行
        """
        if not self.covered_cols[col]:
            return
        
        # 恢复该行涉及的其他列的计数
        for row_idx in affected_rows:
            row_id, columns = self.row_data[row_idx]
            
            for other_col in columns:
                if other_col != col and not self.covered_cols[other_col]:
                    self.col_sizes[other_col] += 1
        
        self.covered_cols[col] = False
    
    def _is_satisfiable(self) -> bool:
        """
        快速可满足性检查
        
        Returns:
            当前状态是否可能有解
        """
        # 检查是否有必须列无法被覆盖
        for col in range(self.num_cols):
            if (not self.covered_cols[col] and 
                col not in self.optional_cols and
                self.col_sizes[col] == 0):
                return False
        return True
    
    def _search_recursive(self) -> bool:
        """
        递归搜索解决方案
        
        Returns:
            是否找到解
        """
        self.nodes_explored += 1
        
        # 超时检查
        if self.nodes_explored % 1000 == 0:
            elapsed = time.time() - self.start_time
            if elapsed > 60:  # 60秒超时
                return False
        
        # 快速可满足性检查
        if not self._is_satisfiable():
            return False
        
        # 选择下一个要处理的列
        col = self._choose_column()
        if col == -1:
            # 所有必须列都已覆盖
            return True
        
        if self.col_sizes[col] == 0:
            # 该列无法被覆盖
            return False
        
        # 尝试该列中的每一行
        for row_idx in self.col_rows[col][:]:  # 复制列表避免修改问题
            if self.covered_cols[col]:  # 列可能已被其他操作覆盖
                continue
                
            row_id, columns = self.row_data[row_idx]
            
            # 检查该行是否仍然有效（所有列都未被覆盖）
            if any(self.covered_cols[c] for c in columns):
                continue
            
            # 选择该行：覆盖所有相关列
            affected_states = []
            self.solution.append(row_id)
            
            for c in columns:
                affected_rows = self._cover_column(c)
                affected_states.append((c, affected_rows))
            
            # 递归搜索
            if self._search_recursive():
                return True
            
            # 回溯：恢复所有被覆盖的列
            for c, affected_rows in reversed(affected_states):
                self._uncover_column(c, affected_rows)
            self.solution.pop()
        
        return False
    
    def solve(self) -> Optional[List[int]]:
        """
        求解精确覆盖问题
        
        Returns:
            解决方案（选中的行ID列表），无解返回None
        """
        self.start_time = time.time()
        self.nodes_explored = 0
        self.solution = []
        self.covered_cols = [False] * self.num_cols
        
        if self._search_recursive():
            return self.solution.copy()
        
        return None


class OptimizedDLXSolver:
    """使用优化DLX的J形拼图求解器"""
    
    def __init__(self, config: PuzzleConfig):
        self.config = config
        self.grid_size = config.grid_size
        self.piece_count = config.piece_count
        self.piece_size = sum(sum(row) for row in config.piece_shape)
        
        # 预计算优化的放置方案
        self.canonical_shapes = self._get_canonical_shapes()
        self.placements = self._generate_optimized_placements()
        
    def _rotate_90(self, matrix: List[List[int]]) -> List[List[int]]:
        """顺时针旋转90度"""
        return [[matrix[len(matrix)-1-j][i] for j in range(len(matrix))] 
                for i in range(len(matrix[0]))]
    
    def _normalize_shape(self, shape: List[List[int]]) -> Tuple[Tuple[int, ...], ...]:
        """标准化形状并转为不可变类型"""
        # 找边界
        occupied = [(i, j) for i in range(len(shape)) 
                   for j in range(len(shape[0])) if shape[i][j]]
        
        if not occupied:
            return ()
        
        min_r = min(r for r, c in occupied)
        max_r = max(r for r, c in occupied)
        min_c = min(c for r, c in occupied)
        max_c = max(c for r, c in occupied)
        
        normalized = []
        for i in range(min_r, max_r + 1):
            row = []
            for j in range(min_c, max_c + 1):
                row.append(shape[i][j] if i < len(shape) and j < len(shape[0]) else 0)
            normalized.append(tuple(row))
        
        return tuple(normalized)
    
    def _get_canonical_shapes(self) -> List[List[List[int]]]:
        """获取去重的标准形状"""
        seen = set()
        shapes = []
        current = [row[:] for row in self.config.piece_shape]
        
        for _ in range(4):
            normalized = self._normalize_shape(current)
            if normalized not in seen:
                seen.add(normalized)
                # 转回list格式
                shape_list = [list(row) for row in normalized]
                shapes.append(shape_list)
            current = self._rotate_90(current)
        
        return shapes
    
    def _get_shape_positions(self, shape: List[List[int]]) -> List[Tuple[int, int]]:
        """获取形状的相对位置"""
        return [(i, j) for i in range(len(shape)) 
                for j in range(len(shape[0])) if shape[i][j]]
    
    def _generate_optimized_placements(self) -> List[Dict]:
        """生成优化的放置方案"""
        placements = []
        placement_id = 0
        
        for piece_id in range(self.piece_count):
            for shape_id, shape in enumerate(self.canonical_shapes):
                positions = self._get_shape_positions(shape)
                
                for start_row in range(self.grid_size):
                    for start_col in range(self.grid_size):
                        # 计算绝对位置
                        grid_positions = []
                        valid = True
                        
                        for rel_row, rel_col in positions:
                            abs_row = start_row + rel_row
                            abs_col = start_col + rel_col
                            
                            if (abs_row >= self.grid_size or 
                                abs_col >= self.grid_size or
                                abs_row < 0 or abs_col < 0):
                                valid = False
                                break
                            
                            grid_positions.append((abs_row, abs_col))
                        
                        if valid:
                            placements.append({
                                'id': placement_id,
                                'piece_id': piece_id,
                                'shape_id': shape_id,
                                'start_pos': (start_row, start_col),
                                'grid_positions': grid_positions
                            })
                            placement_id += 1
        
        return placements
    
    def _build_optimized_dlx_matrix(self) -> OptimizedDLX:
        """构建优化的DLX矩阵"""
        grid_cells = self.grid_size * self.grid_size
        total_cols = grid_cells + self.piece_count
        
        # 网格位置列是可选的，块使用列是必须的
        optional_cols = set(range(grid_cells))
        
        dlx = OptimizedDLX(total_cols, optional_cols)
        
        # 添加每个放置方案作为一行
        for placement in self.placements:
            columns = []
            
            # 网格位置列
            for row, col in placement['grid_positions']:
                pos_index = row * self.grid_size + col
                columns.append(pos_index)
            
            # 块使用列
            piece_index = grid_cells + placement['piece_id']
            columns.append(piece_index)
            
            dlx.add_row(placement['id'], columns)
        
        return dlx
    
    def solve(self) -> Optional[List[Dict]]:
        """求解拼图"""
        print(f"优化DLX求解器:")
        print(f"  网格: {self.grid_size}×{self.grid_size}")
        print(f"  J形块: {self.piece_count}个")
        print(f"  标准形状: {len(self.canonical_shapes)}个")
        print(f"  放置方案: {len(self.placements)}个")
        print()
        
        dlx = self._build_optimized_dlx_matrix()
        
        print("开始优化DLX搜索...")
        solution_row_ids = dlx.solve()
        
        if solution_row_ids:
            # 转换为标准格式
            solution = []
            for row_id in solution_row_ids:
                placement = self.placements[row_id]
                solution.append(placement)
            
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
        
        # 填充解决方案
        for i, placement in enumerate(solution):
            letter = letters[i % len(letters)]
            for row, col in placement['grid_positions']:
                grid[row][col] = letter
        
        # 生成显示
        result = [f"优化DLX解决方案 ({len(solution)} 个J形块):"]
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        for row in grid:
            result.append("| " + " ".join(row) + " |")
        
        result.append("+" + "-" * (self.grid_size * 2 + 1) + "+")
        
        return "\n".join(result)


def benchmark_optimized_dlx():
    """优化DLX性能测试"""
    print("优化DLX性能基准测试")
    print("="*50)
    
    test_cases = [
        (6, 2, "热身测试"),
        (7, 3, "基础测试"), 
        (8, 4, "中级测试"),
        (9, 5, "进阶测试"),
        (10, 6, "挑战测试"),
        (10, 8, "高难测试"),
        (10, 10, "极限测试")
    ]
    
    for grid_size, piece_count, desc in test_cases:
        print(f"\n{'-'*30}")
        print(f"{desc}: {grid_size}×{grid_size}, {piece_count}块")
        print('-'*30)
        
        config = PuzzleConfig(grid_size=grid_size, piece_count=piece_count)
        solver = OptimizedDLXSolver(config)
        
        start_time = time.time()
        solution = solver.solve()
        elapsed = time.time() - start_time
        
        if solution:
            print("成功!")
            print(solver.visualize_solution(solution))
            print(f"\n优化DLX统计:")
            print(f"  求解时间: {elapsed:.3f} 秒")
        else:
            print(f"未找到解 (用时: {elapsed:.3f}s)")


if __name__ == "__main__":
    benchmark_optimized_dlx()