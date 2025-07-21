#!/usr/bin/env python3
"""
J形拼图DLX求解器

使用Dancing Links X算法解决在N×N网格中放置指定数量J形块的拼图问题。
J形块形状可配置，支持旋转和不同网格尺寸。

算法建模思路：
1. 将问题转化为精确覆盖问题的变形（允许部分网格位置不被覆盖）
2. 约束条件：
   - 每个J形块最多使用一次（精确约束）
   - 每个网格位置最多被覆盖一次（精确约束）
3. 目标：在满足约束的前提下，放置尽可能多的J形块
"""

from typing import List, Tuple, Dict, Set, Optional, Iterator
from dataclasses import dataclass


class DLXNode:
    """Dancing Links节点，支持四向链表操作"""
    
    def __init__(self):
        self.left: 'DLXNode' = self
        self.right: 'DLXNode' = self
        self.up: 'DLXNode' = self
        self.down: 'DLXNode' = self
        self.column: Optional['DLXColumn'] = None
        self.row_id: int = -1


class DLXColumn(DLXNode):
    """列头节点，包含列的元信息"""
    
    def __init__(self, name: str, optional: bool = False):
        super().__init__()
        self.name: str = name
        self.size: int = 0  # 该列中1的个数
        self.optional: bool = optional  # 是否为可选列（不要求被覆盖）
        self.column = self


class DLXMatrix:
    """
    Dancing Links X矩阵实现
    
    用于高效地进行精确覆盖问题的搜索，支持O(1)时间的
    行列删除和恢复操作
    """
    
    def __init__(self, column_specs: List[Tuple[str, bool]]):
        """
        初始化DLX矩阵
        
        Args:
            column_specs: 列规格列表，每个元素为(name, optional)元组
        """
        self.header = DLXNode()  # 根节点
        self.columns: List[DLXColumn] = []
        self.rows: List[List[DLXNode]] = []
        
        # 创建列头
        prev = self.header
        for name, optional in column_specs:
            col = DLXColumn(name, optional)
            self.columns.append(col)
            
            # 水平链接
            col.left = prev
            col.right = prev.right
            prev.right.left = col
            prev.right = col
            prev = col
    
    def add_row(self, row_data: List[int], row_id: int) -> None:
        """
        添加一行到矩阵中
        
        Args:
            row_data: 行数据，1表示该列被覆盖，0表示不覆盖
            row_id: 行的唯一标识符
        """
        if len(row_data) != len(self.columns):
            raise ValueError("Row data length must match column count")
        
        row_nodes: List[DLXNode] = []
        prev: Optional[DLXNode] = None
        
        # 只为值为1的位置创建节点
        for i, val in enumerate(row_data):
            if val == 1:
                node = DLXNode()
                node.row_id = row_id
                node.column = self.columns[i]
                row_nodes.append(node)
                
                # 水平链接
                if prev is None:
                    node.left = node.right = node
                else:
                    node.left = prev
                    node.right = prev.right
                    prev.right.left = node
                    prev.right = node
                prev = node
                
                # 垂直链接到列中
                col = self.columns[i]
                node.up = col.up
                node.down = col
                col.up.down = node
                col.up = node
                col.size += 1
        
        self.rows.append(row_nodes)
    
    def cover(self, col: DLXColumn) -> None:
        """
        覆盖操作：移除列及其相关行
        
        Args:
            col: 要覆盖的列
        """
        # 从列头链表中移除该列
        col.right.left = col.left
        col.left.right = col.right
        
        # 移除该列中所有行的其他1节点
        i = col.down
        while i != col:
            j = i.right
            while j != i:
                j.down.up = j.up
                j.up.down = j.down
                j.column.size -= 1
                j = j.right
            i = i.down
    
    def uncover(self, col: DLXColumn) -> None:
        """
        恢复操作：撤销覆盖操作
        
        Args:
            col: 要恢复的列
        """
        # 恢复该列中所有行的其他1节点
        i = col.up
        while i != col:
            j = i.left
            while j != i:
                j.column.size += 1
                j.down.up = j.up.down = j
                j = j.left
            i = i.up
        
        # 恢复列头链表中的该列
        col.right.left = col.left.right = col
    
    def choose_column(self) -> Optional[DLXColumn]:
        """
        选择下一个要处理的列（启发式：选择1最少的必须列）
        
        Returns:
            选中的列，如果没有剩余必须列则返回None
        """
        if self.header.right == self.header:
            return None
        
        col = self.header.right
        min_col = None
        
        # 只考虑非可选的列
        while col != self.header:
            if not col.optional:
                if min_col is None or col.size < min_col.size:
                    min_col = col
            col = col.right
        
        return min_col
    
    def search(self) -> Iterator[List[int]]:
        """
        使用Algorithm X进行搜索
        
        Yields:
            每个解决方案，表示为选中的行ID列表
        """
        solution: List[int] = []
        yield from self._search_recursive(solution)
    
    def _search_recursive(self, solution: List[int]) -> Iterator[List[int]]:
        """递归搜索实现"""
        col = self.choose_column()
        if col is None:
            # 所有列都被覆盖，找到一个解
            yield solution.copy()
            return
        
        if col.size == 0:
            # 该列无法被覆盖，无解
            return
        
        self.cover(col)
        
        # 尝试该列中的每一行
        r = col.down
        while r != col:
            solution.append(r.row_id)
            
            # 覆盖该行涉及的其他列
            j = r.right
            while j != r:
                self.cover(j.column)
                j = j.right
            
            # 递归搜索
            yield from self._search_recursive(solution)
            
            # 回溯：恢复该行涉及的其他列
            j = r.left
            while j != r:
                self.uncover(j.column)
                j = j.left
            
            solution.pop()
            r = r.down
        
        self.uncover(col)


@dataclass
class PuzzleConfig:
    """拼图配置参数"""
    grid_size: int = 10           # 网格边长
    piece_count: int = 11         # J形块数量
    piece_shape: List[List[int]] = None  # J形块形状
    
    def __post_init__(self):
        if self.piece_shape is None:
            # 默认J形块形状
            self.piece_shape = [
                [1, 1, 0, 0, 0],
                [1, 0, 0, 0, 0], 
                [1, 1, 1, 1, 1]
            ]


class JPuzzleSolver:
    """J形拼图求解器主类"""
    
    def __init__(self, config: PuzzleConfig):
        self.config = config
        self.piece_rotations: List[List[List[int]]] = []
        self.placements: List[Dict] = []
        self._generate_piece_rotations()
    
    def _rotate_90(self, matrix: List[List[int]]) -> List[List[int]]:
        """将矩阵顺时针旋转90度"""
        rows, cols = len(matrix), len(matrix[0])
        rotated = [[0] * rows for _ in range(cols)]
        
        for i in range(rows):
            for j in range(cols):
                rotated[j][rows - 1 - i] = matrix[i][j]
        
        return rotated
    
    def _generate_piece_rotations(self) -> None:
        """生成J形块的四个旋转方向"""
        current = [row[:] for row in self.config.piece_shape]  # 深拷贝
        self.piece_rotations = []
        
        for rotation in range(4):
            self.piece_rotations.append([row[:] for row in current])  # 深拷贝
            current = self._rotate_90(current)
    
    def _get_piece_positions(self, shape: List[List[int]]) -> List[Tuple[int, int]]:
        """获取形状中所有1的相对位置"""
        positions = []
        for i in range(len(shape)):
            for j in range(len(shape[0])):
                if shape[i][j] == 1:
                    positions.append((i, j))
        return positions
    
    def _generate_all_placements(self) -> None:
        """生成所有可能的J形块放置方案"""
        self.placements = []
        placement_id = 0
        
        for piece_id in range(self.config.piece_count):
            for rotation_id, rotated_shape in enumerate(self.piece_rotations):
                positions = self._get_piece_positions(rotated_shape)
                
                # 尝试所有可能的起始位置
                for start_row in range(self.config.grid_size):
                    for start_col in range(self.config.grid_size):
                        # 检查是否可以放置
                        grid_positions = []
                        valid = True
                        
                        for rel_row, rel_col in positions:
                            abs_row = start_row + rel_row
                            abs_col = start_col + rel_col
                            
                            if (abs_row >= self.config.grid_size or 
                                abs_col >= self.config.grid_size or
                                abs_row < 0 or abs_col < 0):
                                valid = False
                                break
                            
                            grid_positions.append((abs_row, abs_col))
                        
                        if valid:
                            self.placements.append({
                                'id': placement_id,
                                'piece_id': piece_id,
                                'rotation': rotation_id,
                                'start_pos': (start_row, start_col),
                                'grid_positions': grid_positions
                            })
                            placement_id += 1
    
    def _build_dlx_matrix(self) -> DLXMatrix:
        """
        构建DLX矩阵
        
        列约束：
        - 前 grid_size² 列：网格位置约束（每个位置最多被覆盖一次）- 可选
        - 后 piece_count 列：块使用约束（每个块最多被使用一次）- 必须
        
        行：每行代表一个具体的块放置方案
        """
        grid_cells = self.config.grid_size * self.config.grid_size
        
        # 列规格：(name, optional)
        column_specs = []
        # 网格位置列（可选，因为允许空格）
        for i in range(self.config.grid_size):
            for j in range(self.config.grid_size):
                column_specs.append((f"pos_{i}_{j}", True))
        # 块使用列（必须，每个块最多使用一次）
        for i in range(self.config.piece_count):
            column_specs.append((f"piece_{i}", False))
        
        matrix = DLXMatrix(column_specs)
        
        # 为每个放置方案添加一行
        for placement in self.placements:
            row_data = [0] * len(column_specs)
            
            # 标记网格位置被占用
            for row, col in placement['grid_positions']:
                pos_index = row * self.config.grid_size + col
                row_data[pos_index] = 1
            
            # 标记块被使用
            piece_index = self.config.grid_size * self.config.grid_size + placement['piece_id']
            row_data[piece_index] = 1
            
            matrix.add_row(row_data, placement['id'])
        
        return matrix
    
    def solve(self) -> Optional[List[Dict]]:
        """
        求解拼图
        
        Returns:
            解决方案列表，每个元素包含一个块的放置信息；如果无解则返回None
        """
        self._generate_all_placements()
        matrix = self._build_dlx_matrix()
        
        # 寻找第一个解
        for solution_row_ids in matrix.search():
            solution_placements = []
            for row_id in solution_row_ids:
                solution_placements.append(self.placements[row_id])
            return solution_placements
        
        return None
    
    def visualize_solution(self, solution: List[Dict]) -> str:
        """
        可视化解决方案
        
        Args:
            solution: 求解得到的放置方案列表
            
        Returns:
            可视化字符串，用不同字母表示不同的J形块
        """
        if not solution:
            return "No solution found"
        
        # 创建空网格
        grid = [['.' for _ in range(self.config.grid_size)] 
                for _ in range(self.config.grid_size)]
        
        # 为每个块分配一个字母
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        
        # 填充网格
        for i, placement in enumerate(solution):
            letter = letters[i % len(letters)]
            for row, col in placement['grid_positions']:
                grid[row][col] = letter
        
        # 生成字符串表示
        result = []
        result.append(f"Solution with {len(solution)} J-pieces:")
        result.append("+" + "-" * (self.config.grid_size * 2 + 1) + "+")
        
        for row in grid:
            line = "| " + " ".join(row) + " |"
            result.append(line)
        
        result.append("+" + "-" * (self.config.grid_size * 2 + 1) + "+")
        
        # 添加图例
        result.append("\nPiece mapping:")
        for i, placement in enumerate(solution):
            letter = letters[i % len(letters)]
            result.append(f"{letter}: Piece {placement['piece_id']} "
                         f"(rotation {placement['rotation']}°, "
                         f"start at {placement['start_pos']})")
        
        return "\n".join(result)


def main():
    """主函数：演示J形拼图求解"""
    # 创建配置
    config = PuzzleConfig(
        grid_size=10,
        piece_count=11,
        piece_shape=[
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0],
            [1, 1, 1, 1, 1]
        ]
    )
    
    print("J-Piece Puzzle Solver")
    print("=" * 50)
    print(f"Grid size: {config.grid_size}×{config.grid_size}")
    print(f"Number of J-pieces: {config.piece_count}")
    print(f"J-piece shape:")
    for row in config.piece_shape:
        print("  " + "".join("█" if x else "." for x in row))
    print()
    
    # 创建求解器并求解
    solver = JPuzzleSolver(config)
    print("Solving puzzle...")
    
    solution = solver.solve()
    
    if solution:
        print("Solution found!")
        print(solver.visualize_solution(solution))
        
        # 验证解的正确性
        total_cells = sum(len(p['grid_positions']) for p in solution)
        expected_cells = len(solver._get_piece_positions(config.piece_shape)) * len(solution)
        print(f"\nVerification:")
        print(f"Total cells occupied: {total_cells}")
        print(f"Expected cells: {expected_cells}")
        print(f"Empty cells: {config.grid_size**2 - total_cells}")
    else:
        print("No solution found!")


if __name__ == "__main__":
    main()