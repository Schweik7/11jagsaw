#!/usr/bin/env python3
"""
测试基本放置逻辑
"""

def test_basic_placement():
    """测试基本放置功能"""
    
    # J形块的一个简单旋转
    j_shape = [(0, 0), (0, 1), (1, 0), (2, 0), (2, 1), (2, 2), (2, 3), (2, 4)]
    
    print("J形块形状:")
    max_r = max(r for r, c in j_shape)
    max_c = max(c for r, c in j_shape)
    
    for r in range(max_r + 1):
        line = ""
        for c in range(max_c + 1):
            if (r, c) in j_shape:
                line += "█"
            else:
                line += "·"
        print(f"  {line}")
    
    print(f"包含 {len(j_shape)} 个格子")
    
    # 测试在10x10网格中的放置
    grid_size = 10
    grid = [[0] * grid_size for _ in range(grid_size)]
    
    # 尝试在不同位置放置
    test_positions = [(0, 0), (0, 5), (5, 0), (7, 5)]
    
    for start_r, start_c in test_positions:
        # 计算实际位置
        actual_positions = [(start_r + dr, start_c + dc) for dr, dc in j_shape]
        
        # 检查边界
        valid = all(0 <= r < grid_size and 0 <= c < grid_size 
                   for r, c in actual_positions)
        
        print(f"\n在位置 ({start_r}, {start_c}) 放置:")
        print(f"  实际位置: {actual_positions}")
        print(f"  边界检查: {'✓' if valid else '✗'}")
        
        if valid:
            # 清空网格
            for r in range(grid_size):
                for c in range(grid_size):
                    grid[r][c] = 0
            
            # 放置
            for r, c in actual_positions:
                grid[r][c] = 1
            
            # 显示结果
            print("  网格:")
            for r in range(min(5, grid_size)):  # 只显示前5行
                line = "    "
                for c in range(min(10, grid_size)):  # 只显示前10列
                    if grid[r][c] == 1:
                        line += "█"
                    else:
                        line += "·"
                print(line)
            if grid_size > 5:
                print("    ...")

def test_rotations():
    """测试旋转生成"""
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
    
    print("\n旋转测试:")
    current = base
    for rotation in range(4):
        pos = normalize(get_positions(current))
        print(f"  旋转 {rotation}: {pos}")
        current = rotate_90(current)

def test_grid_coverage():
    """测试11个块是否能在理论上覆盖足够的空间"""
    shape_size = 8
    total_pieces = 11
    grid_size = 10
    
    total_piece_cells = total_pieces * shape_size
    total_grid_cells = grid_size * grid_size
    
    print(f"\n空间分析:")
    print(f"  网格总格子: {total_grid_cells}")
    print(f"  所有块格子: {total_piece_cells}")
    print(f"  剩余空格: {total_grid_cells - total_piece_cells}")
    print(f"  覆盖率: {total_piece_cells / total_grid_cells * 100:.1f}%")
    
    if total_piece_cells <= total_grid_cells:
        print("  ✓ 理论上可以放置")
    else:
        print("  ✗ 理论上不可能放置")

if __name__ == "__main__":
    print("基本放置逻辑测试")
    print("=" * 30)
    
    test_basic_placement()
    test_rotations()
    test_grid_coverage()