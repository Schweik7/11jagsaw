import matplotlib.pyplot as plt
import numpy as np

# --- 基础配置 ---
GRID_SIZE = 10
NUM_PIECES = 11
PIECE_SIZE = 8
TOTAL_CELLS = GRID_SIZE * GRID_SIZE
MAX_HOLES = TOTAL_CELLS - (NUM_PIECES * PIECE_SIZE)  # 100 - 88 = 12

# 边界掩码：用于位移扩散时防止“穿墙”
COL0_MASK = 0
for i in range(GRID_SIZE):
    COL0_MASK |= (1 << (i * GRID_SIZE))
COL9_MASK = COL0_MASK << (GRID_SIZE - 1)
NOT_COL0 = ((1 << TOTAL_CELLS) - 1) ^ COL0_MASK
NOT_COL9 = ((1 << TOTAL_CELLS) - 1) ^ COL9_MASK
FULL_MASK = (1 << TOTAL_CELLS) - 1

def get_variations():
    """生成 J 形块的 8 种对称变换（旋转+镜像）"""
    # 原始坐标
    base_coords = [(0,0), (0,1), (1,0), (2,0), (2,1), (2,2), (2,3), (2,4)]
    
    def rotate(coords): return [(c, -r) for r, c in coords]
    def flip(coords): return [(r, -c) for r, c in coords]
    def normalize(coords):
        min_r = min(r for r, c in coords)
        min_c = min(c for r, c in coords)
        return sorted([(r - min_r, c - min_c) for r, c in coords])

    variants = set()
    curr = base_coords
    for _ in range(4): # 4次旋转
        curr = rotate(curr)
        variants.add(tuple(normalize(curr)))
        variants.add(tuple(normalize(flip(curr))))
    return [list(v) for v in variants]

def precompute_moves():
    """预计算所有合法位置的位掩码，按最低位索引分类"""
    variants = get_variations()
    moves_at_index = [[] for _ in range(TOTAL_CELLS)]
    
    for v in variants:
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                mask = 0
                valid = True
                for pr, pc in v:
                    nr, nc = r + pr, c + pc
                    if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE:
                        mask |= (1 << (nr * GRID_SIZE + nc))
                    else:
                        valid = False
                        break
                if valid:
                    # 找到该掩码的最低 set bit (LSB)
                    lsb = (mask & -mask).bit_length() - 1
                    moves_at_index[lsb].append(mask)
    return moves_at_index

MOVES_AT_INDEX = precompute_moves()

def flood_fill_pruning(board_mask, holes_left):
    """纯位运算连通性剪枝"""
    remaining = FULL_MASK ^ board_mask
    needed_holes = 0
    
    temp_remaining = remaining
    while temp_remaining:
        # 找到一个起点
        seed = temp_remaining & -temp_remaining
        region = 0
        frontier = seed
        
        # 扩散
        while frontier:
            region |= frontier
            # 向四个方向扩散，注意边界
            expanded = ((frontier << 1) & NOT_COL0) | \
                       ((frontier >> 1) & NOT_COL9) | \
                       (frontier << GRID_SIZE) | \
                       (frontier >> GRID_SIZE)
            frontier = expanded & temp_remaining & ~region
        
        # 计算区域大小
        region_size = bin(region).count('1')
        # 核心逻辑：每个连通区域的大小 S，若不能被 8 整除，余数必占空位额度
        needed_holes += (region_size % PIECE_SIZE)
        
        if needed_holes > holes_left:
            return False
        
        temp_remaining ^= region
        
    return True

# 用于记录路径
solution_path = []

def solve(board_mask, pieces_left, holes_left):
    if pieces_left == 0:
        return True
    
    # 找到第一个空位 (Lowest Empty Bit)
    # 取反后低位第一个1即为原掩码低位第一个0
    first_empty = ((board_mask + 1) & ~board_mask).bit_length() - 1
    
    if first_empty >= TOTAL_CELLS:
        return pieces_left == 0

    # 分支 A: 尝试在此位置放入一个块
    for move_mask in MOVES_AT_INDEX[first_empty]:
        if not (move_mask & board_mask):
            new_board = board_mask | move_mask
            # 连通性剪枝
            if flood_fill_pruning(new_board, holes_left):
                solution_path.append(move_mask)
                if solve(new_board, pieces_left - 1, holes_left):
                    return True
                solution_path.pop()

    # 分支 B: 标记此位为空洞 (Skip)
    if holes_left > 0:
        new_board_with_hole = board_mask | (1 << first_empty)
        if flood_fill_pruning(new_board_with_hole, holes_left - 1):
            if solve(new_board_with_hole, pieces_left, holes_left - 1):
                return True
                
    return False

def visualize(masks):
    grid = np.zeros((GRID_SIZE, GRID_SIZE))
    for idx, mask in enumerate(masks):
        for bit in range(TOTAL_CELLS):
            if (mask >> bit) & 1:
                grid[bit // GRID_SIZE, bit % GRID_SIZE] = idx + 1
                
    plt.figure(figsize=(8, 8))
    plt.imshow(grid, cmap='tab20', interpolation='nearest')
    
    # 绘制网格线
    for i in range(GRID_SIZE + 1):
        plt.axhline(i - 0.5, color='black', lw=2)
        plt.axvline(i - 0.5, color='black', lw=2)
        
    plt.title(f"Polyomino Exact Cover: {NUM_PIECES} Pieces (88/100 cells)")
    plt.axis('off')
    plt.show()

# --- 执行 ---
print("正在计算中... 这是一个高难度搜索，请稍候...")
if solve(0, NUM_PIECES, MAX_HOLES):
    print("成功找到解！正在生成可视化...")
    visualize(solution_path)
else:
    print("在当前限制下未找到解。")