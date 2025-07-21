#!/usr/bin/env python3

from j_puzzle_solver import JPuzzleSolver, PuzzleConfig

def test_6x6_case():
    """测试6×6网格放置2个J形块"""
    config = PuzzleConfig(
        grid_size=6,
        piece_count=2,
        piece_shape=[
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0],
            [1, 1, 1, 1, 1]
        ]
    )
    
    print("Testing 6x6 case: 2 J-pieces on 6x6 grid")
    print(f"Grid cells: {config.grid_size**2}")
    print(f"J-piece cells: {sum(sum(row) for row in config.piece_shape)}")
    print(f"Total occupied: {config.piece_count * sum(sum(row) for row in config.piece_shape)}")
    print(f"Empty cells: {config.grid_size**2 - config.piece_count * sum(sum(row) for row in config.piece_shape)}")
    print()
    
    solver = JPuzzleSolver(config)
    solver._generate_all_placements()
    print(f"Generated {len(solver.placements)} possible placements")
    
    # 显示J形块旋转后的尺寸
    print("\nJ-piece dimensions after rotation:")
    for i, rotation in enumerate(solver.piece_rotations):
        rows, cols = len(rotation), len(rotation[0])
        print(f"  Rotation {i} ({i*90}°): {rows}×{cols}")
    
    solution = solver.solve()
    
    if solution:
        print("SUCCESS: Found solution!")
        print(solver.visualize_solution(solution))
    else:
        print("No solution found")

if __name__ == "__main__":
    test_6x6_case()