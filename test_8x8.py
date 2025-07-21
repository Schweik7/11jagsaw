#!/usr/bin/env python3

from j_puzzle_solver import JPuzzleSolver, PuzzleConfig
import time

def test_8x8_case():
    """测试8×8网格放置4个J形块"""
    config = PuzzleConfig(
        grid_size=8,
        piece_count=4,
        piece_shape=[
            [1, 1, 0, 0, 0],
            [1, 0, 0, 0, 0],
            [1, 1, 1, 1, 1]
        ]
    )
    
    print("Testing 8x8 case: 4 J-pieces on 8x8 grid")
    print(f"Grid cells: {config.grid_size**2}")
    print(f"J-piece cells: {sum(sum(row) for row in config.piece_shape)}")
    print(f"Total occupied: {config.piece_count * sum(sum(row) for row in config.piece_shape)}")
    print(f"Empty cells: {config.grid_size**2 - config.piece_count * sum(sum(row) for row in config.piece_shape)}")
    print()
    
    solver = JPuzzleSolver(config)
    solver._generate_all_placements()
    print(f"Generated {len(solver.placements)} possible placements")
    
    print("Solving...")
    start_time = time.time()
    solution = solver.solve()
    end_time = time.time()
    
    print(f"Solving took {end_time - start_time:.2f} seconds")
    
    if solution:
        print("SUCCESS: Found solution!")
        print(solver.visualize_solution(solution))
    else:
        print("No solution found")

if __name__ == "__main__":
    test_8x8_case()