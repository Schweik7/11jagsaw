#!/usr/bin/env python3

from j_puzzle_solver import JPuzzleSolver, PuzzleConfig

def debug_dlx_matrix():
    """调试DLX矩阵构建"""
    config = PuzzleConfig(
        grid_size=3,  # 使用更小的网格便于调试
        piece_count=1,
        piece_shape=[
            [1, 1],
            [1, 0],
            [1, 1]
        ]  # 更简单的形状
    )
    
    solver = JPuzzleSolver(config)
    solver._generate_all_placements()
    
    print(f"Grid size: {config.grid_size}x{config.grid_size}")
    print(f"Total grid cells: {config.grid_size * config.grid_size}")
    print(f"Generated {len(solver.placements)} placements")
    
    # 显示所有旋转
    print("\nPiece rotations:")
    for i, rotation in enumerate(solver.piece_rotations):
        print(f"Rotation {i}:")
        for row in rotation:
            print("  " + "".join("█" if x else "." for x in row))
        positions = solver._get_piece_positions(rotation)
        print(f"  Positions: {positions}")
        print()
    
    # 显示所有放置方案
    print("All placements:")
    for i, placement in enumerate(solver.placements):
        print(f"  {i}: rotation {placement['rotation']}, start {placement['start_pos']}, "
              f"positions {placement['grid_positions']}")
    
    # 构建DLX矩阵
    matrix = solver._build_dlx_matrix()
    
    print(f"\nDLX Matrix info:")
    print(f"Number of columns: {len(matrix.columns)}")
    print(f"Column names: {[col.name for col in matrix.columns]}")
    print(f"Number of rows: {len(matrix.rows)}")
    
    # 检查列的大小
    print("\nColumn sizes:")
    for col in matrix.columns:
        print(f"  {col.name}: {col.size}")
    
    # 尝试求解
    print("\nTrying to solve...")
    solution = solver.solve()
    
    if solution:
        print("Found solution:")
        for placement in solution:
            print(f"  {placement}")
        print(solver.visualize_solution(solution))
    else:
        print("No solution found")

if __name__ == "__main__":
    debug_dlx_matrix()