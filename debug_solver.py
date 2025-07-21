#!/usr/bin/env python3
"""
调试版本：验证我们的J形块形状和答案是否匹配
"""

def parse_answer():
    """解析答案文件"""
    answer_text = """     1→C C C C C D D D D D
     2→G G G · C D · J J J
     3→G · G C C D D J · J
     4→G F F F I I I I I J
     5→G F E F I · K K K J
     6→G F E · I I K · K J
     7→· F E H H H H H K ·
     8→E F E A A B B H K ·
     9→E E E · A B H H K ·
    10→A A A A A B B B B B"""
    
    grid = []
    for line in answer_text.strip().split('\n'):
        # 提取实际的网格内容
        parts = line.split('→')[1].strip()
        row = []
        for char in parts.split():
            if char == '·':
                row.append(0)
            else:
                row.append(ord(char) - ord('A') + 1)
        grid.append(row)
    
    return grid

def analyze_pieces(grid):
    """分析每个块的形状"""
    pieces = {}
    for i in range(len(grid)):
        for j in range(len(grid[0])):
            if grid[i][j] > 0:
                piece_id = grid[i][j]
                if piece_id not in pieces:
                    pieces[piece_id] = []
                pieces[piece_id].append((i, j))
    
    return pieces

def normalize_piece(positions):
    """标准化块的位置"""
    if not positions:
        return []
    
    min_r = min(r for r, c in positions)
    min_c = min(c for r, c in positions)
    
    return sorted([(r - min_r, c - min_c) for r, c in positions])

def check_j_shape():
    """检查我们的J形块定义是否正确"""
    # 我们定义的J形块
    our_shape = [
        [1, 1, 0, 0, 0],
        [1, 0, 0, 0, 0], 
        [1, 1, 1, 1, 1]
    ]
    
    our_positions = []
    for i in range(len(our_shape)):
        for j in range(len(our_shape[0])):
            if our_shape[i][j]:
                our_positions.append((i, j))
    
    our_normalized = normalize_piece(our_positions)
    
    print("我们的J形块:")
    for row in our_shape:
        print("  " + "".join("█" if x else "·" for x in row))
    print(f"位置: {our_normalized}")
    print(f"大小: {len(our_normalized)}")
    
    # 分析答案中的块
    answer_grid = parse_answer()
    pieces = analyze_pieces(answer_grid)
    
    print(f"\n答案中有 {len(pieces)} 个块:")
    
    unique_shapes = set()
    for piece_id, positions in pieces.items():
        normalized = tuple(normalize_piece(positions))
        unique_shapes.add(normalized)
        
        piece_letter = chr(ord('A') + piece_id - 1)
        print(f"  块 {piece_letter}: {len(positions)} 个格子, 形状: {normalized}")
    
    print(f"\n答案中唯一形状数: {len(unique_shapes)}")
    
    # 检查我们的形状是否匹配答案中的某个形状
    our_shape_tuple = tuple(our_normalized)
    if our_shape_tuple in unique_shapes:
        print("✓ 我们的J形块形状与答案匹配!")
    else:
        print("✗ 我们的J形块形状与答案不匹配")
        print("答案中的形状:")
        for shape in unique_shapes:
            print(f"  {shape}")

def visualize_answer():
    """可视化答案"""
    grid = parse_answer()
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    
    print("\n答案可视化:")
    print("+" + "-" * 21 + "+")
    for row in grid:
        line = "| "
        for cell in row:
            if cell == 0:
                line += "· "
            else:
                line += letters[cell - 1] + " "
        line += "|"
        print(line)
    print("+" + "-" * 21 + "+")
    
    # 统计
    occupied = sum(1 for row in grid for cell in row if cell > 0)
    print(f"占用格子: {occupied}")
    print(f"空闲格子: {100 - occupied}")

if __name__ == "__main__":
    print("调试分析：J形块形状验证")
    print("=" * 50)
    
    check_j_shape()
    visualize_answer()