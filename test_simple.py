#!/usr/bin/env python3

from j_puzzle_solver import JPuzzleSolver, PuzzleConfig

def test_simple_case():
    """测试简单情况：只放置1个J形块"""
    config = PuzzleConfig(
        grid_size=10,
        piece_count=1,  # 只放置1个块
        piece_shape=[
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0],
            [1, 1, 1, 1, 1]
        ]
    )
    
    print("Testing simple case: 1 J-piece on 10x10 grid")
    solver = JPuzzleSolver(config)
    solution = solver.solve()
    
    if solution:
        print("SUCCESS: Found solution for 1 piece!")
        print(solver.visualize_solution(solution))
        return True
    else:
        print("FAILED: Could not find solution for 1 piece")
        return False

def test_debug_placements():
    """调试：检查生成的放置方案数量"""
    config = PuzzleConfig(
        grid_size=10,
        piece_count=1,
        piece_shape=[
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0],
            [1, 1, 1, 1, 1]
        ]
    )
    
    solver = JPuzzleSolver(config)
    solver._generate_all_placements()
    
    print(f"Generated {len(solver.placements)} possible placements")
    print(f"Piece rotations: {len(solver.piece_rotations)}")
    
    # 显示前几个旋转
    for i, rotation in enumerate(solver.piece_rotations):
        print(f"\nRotation {i} (angle {i*90}°):")
        for row in rotation:
            print("  " + "".join("█" if x else "." for x in row))
    
    # 显示前几个放置方案
    print(f"\nFirst 5 placements:")
    for i, placement in enumerate(solver.placements[:5]):
        print(f"  {i}: piece {placement['piece_id']}, rotation {placement['rotation']}, "
              f"start {placement['start_pos']}, positions {placement['grid_positions']}")

if __name__ == "__main__":
    print("Testing J-puzzle solver...")
    test_debug_placements()
    print("\n" + "="*50)
    test_simple_case()