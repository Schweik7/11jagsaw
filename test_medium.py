#!/usr/bin/env python3

from j_puzzle_solver import JPuzzleSolver, PuzzleConfig

def test_medium_case():
    """测试中等规模：5×5网格放置3个J形块"""
    config = PuzzleConfig(
        grid_size=5,
        piece_count=3,
        piece_shape=[
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0],
            [1, 1, 1, 1, 1]
        ]
    )
    
    print("Testing medium case: 3 J-pieces on 5x5 grid")
    print(f"Grid cells: {config.grid_size**2}")
    print(f"J-piece cells: {sum(sum(row) for row in config.piece_shape)}")
    print(f"Total occupied: {config.piece_count * sum(sum(row) for row in config.piece_shape)}")
    print(f"Empty cells: {config.grid_size**2 - config.piece_count * sum(sum(row) for row in config.piece_shape)}")
    print()
    
    solver = JPuzzleSolver(config)
    print(f"Generated {len(solver.placements)} possible placements")
    
    solution = solver.solve()
    
    if solution:
        print("SUCCESS: Found solution!")
        print(solver.visualize_solution(solution))
    else:
        print("No solution found")

if __name__ == "__main__":
    test_medium_case()