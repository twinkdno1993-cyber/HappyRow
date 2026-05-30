import random
from typing import List, Tuple

TILE_TYPES = ['🔴', '🔵', '🟢', '🟡', '🟣', '🟠']
BOARD_SIZE = 8


def generate_field() -> List[List[str]]:
    field = [[random.choice(TILE_TYPES) for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
    while True:
        has_matches = False
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                if check_match_at(field, row, col):
                    field[row][col] = random.choice(TILE_TYPES)
                    has_matches = True
        if not has_matches:
            break
    return field


def check_match_at(field: List[List[str]], row: int, col: int) -> bool:
    tile = field[row][col]
    if not tile:
        return False
    
    horizontal_count = 1
    c = col - 1
    while c >= 0 and field[row][c] == tile:
        horizontal_count += 1
        c -= 1
    c = col + 1
    while c < BOARD_SIZE and field[row][c] == tile:
        horizontal_count += 1
        c += 1
    
    if horizontal_count >= 3:
        return True
    
    vertical_count = 1
    r = row - 1
    while r >= 0 and field[r][col] == tile:
        vertical_count += 1
        r -= 1
    r = row + 1
    while r < BOARD_SIZE and field[r][col] == tile:
        vertical_count += 1
        r += 1
    
    return vertical_count >= 3


def find_all_matches(field: List[List[str]]) -> List[Tuple[int, int]]:
    matches = set()
    for row in range(BOARD_SIZE):
        for col in range(BOARD_SIZE):
            if check_match_at(field, row, col):
                matches.add((row, col))
    return list(matches)


def clear_matches(field: List[List[str]], extra_points: int = 0) -> Tuple[List[List[str]], int]:
    matches = find_all_matches(field)
    if not matches:
        return field, extra_points
    
    points = len(matches) * 10 + extra_points
    
    for row, col in matches:
        field[row][col] = None
    
    for col in range(BOARD_SIZE):
        column_tiles = []
        for row in range(BOARD_SIZE - 1, -1, -1):
            if field[row][col] is not None:
                column_tiles.append(field[row][col])
        
        while len(column_tiles) < BOARD_SIZE:
            column_tiles.append(random.choice(TILE_TYPES))
        
        for row in range(BOARD_SIZE - 1, -1, -1):
            field[row][col] = column_tiles[BOARD_SIZE - 1 - row]
    
    return clear_matches(field, points)


def apply_move(field: List[List[str]], from_row: int, from_col: int, to_row: int, to_col: int) -> Tuple[List[List[str]], int]:
    if abs(from_row - to_row) + abs(from_col - to_col) != 1:
        return field, 0
    
    new_field = [row[:] for row in field]
    new_field[from_row][from_col], new_field[to_row][to_col] = new_field[to_row][to_col], new_field[from_row][from_col]
    
    if not find_all_matches(new_field):
        return field, 0
    
    return clear_matches(new_field)