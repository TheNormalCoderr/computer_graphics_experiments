"""
==============================================================================
Boundary Fill Algorithm — 4-Way and 8-Way Fill
==============================================================================
Implements the Boundary Fill algorithm for region filling in 2D raster graphics.

Two variants:
  - 4-Way Boundary Fill: evaluates only orthogonal neighbors (up, down, left, right)
  - 8-Way Boundary Fill: evaluates all 8 neighbors including diagonals

Demonstrates the critical relationship between fill connectivity and boundary
connectivity:
  - 4-Way fill works safely with both 4-connected and 8-connected boundaries
  - 8-Way fill requires 4-connected (solid) boundaries; it leaks through
    8-connected (diagonal) boundaries

Test Cases:
  TC1: 4-Way Fill on 4-Connected Boundary  →  Fill CONTAINED
  TC2: 4-Way Fill on 8-Connected Boundary  →  Fill CONTAINED
  TC3: 8-Way Fill on 4-Connected Boundary  →  Fill CONTAINED
  TC4: 8-Way Fill on 8-Connected Boundary  →  Fill LEAKS

Run:
  python BoundaryFill/src/boundary_fill.py           # Launches the filling app
  python BoundaryFill/src/boundary_fill.py --headless # Generates test case PNGs
==============================================================================
"""

import os
import sys
import math
import struct
import zlib
from collections import deque

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUTPUT_DIR = os.path.join(REPO_ROOT, "BoundaryFill", "outputs")
APP_SRC    = os.path.join(REPO_ROOT, "app", "src")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================================
# Core Boundary Fill Algorithm
# ============================================================================

def boundary_fill_4way(grid, seed_col, seed_row, fill_color, boundary_color,
                       num_cols, num_rows):
    """
    4-Way Boundary Fill Algorithm (Iterative BFS).

    Starting from the seed pixel, examines only the 4 orthogonal neighbors
    (up, down, left, right). A pixel is filled if it is:
      - Within grid bounds
      - Not the boundary color
      - Not already the fill color

    Parameters
    ----------
    grid : dict
        Mapping of (col, row) → (r, g, b) color tuples.
    seed_col, seed_row : int
        Starting pixel coordinates.
    fill_color : tuple
        (r, g, b) color to fill with.
    boundary_color : tuple
        (r, g, b) boundary color that stops propagation.
    num_cols, num_rows : int
        Grid dimensions.

    Returns
    -------
    int
        Number of pixels filled.
    """
    neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # Up, Down, Right, Left
    return _boundary_fill_bfs(grid, seed_col, seed_row, fill_color,
                              boundary_color, num_cols, num_rows, neighbors)


def boundary_fill_8way(grid, seed_col, seed_row, fill_color, boundary_color,
                       num_cols, num_rows):
    """
    8-Way Boundary Fill Algorithm (Iterative BFS).

    Starting from the seed pixel, examines all 8 neighbors including diagonals.
    A pixel is filled if it is:
      - Within grid bounds
      - Not the boundary color
      - Not already the fill color

    Parameters
    ----------
    grid : dict
        Mapping of (col, row) → (r, g, b) color tuples.
    seed_col, seed_row : int
        Starting pixel coordinates.
    fill_color : tuple
        (r, g, b) color to fill with.
    boundary_color : tuple
        (r, g, b) boundary color that stops propagation.
    num_cols, num_rows : int
        Grid dimensions.

    Returns
    -------
    int
        Number of pixels filled.
    """
    neighbors = [
        (0, 1), (0, -1), (1, 0), (-1, 0),       # Orthogonal
        (1, 1), (1, -1), (-1, 1), (-1, -1),      # Diagonal
    ]
    return _boundary_fill_bfs(grid, seed_col, seed_row, fill_color,
                              boundary_color, num_cols, num_rows, neighbors)


def _colors_match(c1, c2, tol=0.01):
    """Compare two RGB color tuples with tolerance."""
    if c1 is None or c2 is None:
        return c1 == c2
    return (abs(c1[0] - c2[0]) < tol and
            abs(c1[1] - c2[1]) < tol and
            abs(c1[2] - c2[2]) < tol)


def _boundary_fill_bfs(grid, seed_col, seed_row, fill_color, boundary_color,
                        num_cols, num_rows, neighbors):
    """
    Core iterative BFS fill engine used by both 4-way and 8-way variants.

    Uses a queue (deque) instead of recursion to avoid stack overflow on
    large regions. The algorithm:
      1. Push seed pixel onto the queue
      2. Pop a pixel from the queue
      3. If the pixel is not boundary and not already filled:
         a. Color it with fill_color
         b. Push all valid unvisited neighbors onto the queue
      4. Repeat until queue is empty
    """
    if not (0 <= seed_col < num_cols and 0 <= seed_row < num_rows):
        return 0

    curr_col = grid.get((seed_col, seed_row))
    if _colors_match(curr_col, boundary_color):
        return 0
    if _colors_match(curr_col, fill_color):
        return 0

    queue = deque([(seed_col, seed_row)])
    visited = {(seed_col, seed_row)}
    count = 0

    while queue:
        col, row = queue.popleft()
        cell_color = grid.get((col, row))

        if not _colors_match(cell_color, boundary_color) and \
           not _colors_match(cell_color, fill_color):
            grid[(col, row)] = fill_color
            count += 1

            for dc, dr in neighbors:
                nc, nr = col + dc, row + dr
                if 0 <= nc < num_cols and 0 <= nr < num_rows:
                    if (nc, nr) not in visited:
                        n_color = grid.get((nc, nr))
                        if not _colors_match(n_color, boundary_color) and \
                           not _colors_match(n_color, fill_color):
                            visited.add((nc, nr))
                            queue.append((nc, nr))
    return count


# ============================================================================
# Boundary Shape Builders
# ============================================================================

def build_4connected_rectangle(left=5, top=5, right=28, bottom=22):
    """
    Build a closed 4-connected rectangular boundary.
    Every boundary pixel shares an orthogonal edge with the next pixel —
    no diagonal-only connections. This is a solid, leak-proof wall.
    """
    cells = set()
    for c in range(left, right + 1):
        cells.add((c, top))
        cells.add((c, bottom))
    for r in range(top, bottom + 1):
        cells.add((left, r))
        cells.add((right, r))
    return cells


def build_8connected_diamond(cx=16, cy=14, radius=8):
    """
    Build an 8-connected boundary (diagonal diamond pattern).
    Boundary pixels only touch at diagonal corners — orthogonal gaps exist.
    The 8-way fill algorithm can slip through these diagonal gaps.
    """
    cells = set()
    for i in range(radius):
        cells.add((cx + i, cy - radius + i))        # Top-right
        cells.add((cx + radius - i, cy + i))         # Bottom-right
        cells.add((cx - i, cy + radius - i))         # Bottom-left
        cells.add((cx - radius + i, cy - i))         # Top-left
    return cells


# ============================================================================
# Test Cases
# ============================================================================

BOUNDARY_COLOR = (0.00, 0.00, 0.00)     # Black
FILL_COLOR     = (0.12, 0.80, 0.35)     # Green

TEST_CASES = [
    {
        "id": "TC1",
        "label": "TC1 — 4-Way Fill on 4-Connected Boundary",
        "algorithm": "4-Way Boundary Fill",
        "fill_fn": boundary_fill_4way,
        "boundary_fn": build_4connected_rectangle,
        "seed": (16, 14),
        "expected": "CONTAINED",
        "file": "tc1_4way_fill_4connected_boundary.png",
        "description": (
            "4-connected boundary (solid rectangle): all boundary pixels share "
            "orthogonal edges. The 4-way fill checks only up/down/left/right "
            "neighbors and is completely blocked by the solid walls."
        ),
    },
    {
        "id": "TC2",
        "label": "TC2 — 4-Way Fill on 8-Connected Boundary",
        "algorithm": "4-Way Boundary Fill",
        "fill_fn": boundary_fill_4way,
        "boundary_fn": build_8connected_diamond,
        "seed": (16, 14),
        "expected": "CONTAINED",
        "file": "tc2_4way_fill_8connected_boundary.png",
        "description": (
            "8-connected boundary (diagonal diamond): boundary pixels only touch "
            "diagonally with orthogonal gaps. However, 4-way fill only moves "
            "orthogonally and cannot escape through diagonal gaps — fill stays contained."
        ),
    },
    {
        "id": "TC3",
        "label": "TC3 — 8-Way Fill on 4-Connected Boundary",
        "algorithm": "8-Way Boundary Fill",
        "fill_fn": boundary_fill_8way,
        "boundary_fn": build_4connected_rectangle,
        "seed": (16, 14),
        "expected": "CONTAINED",
        "file": "tc3_8way_fill_4connected_boundary.png",
        "description": (
            "4-connected boundary (solid rectangle): even the 8-way fill, which "
            "checks all 8 neighbors including diagonals, cannot escape because "
            "the boundary has no gaps at all."
        ),
    },
    {
        "id": "TC4",
        "label": "TC4 — 8-Way Fill on 8-Connected Boundary",
        "algorithm": "8-Way Boundary Fill",
        "fill_fn": boundary_fill_8way,
        "boundary_fn": build_8connected_diamond,
        "seed": (16, 14),
        "expected": "LEAKS",
        "file": "tc4_8way_fill_8connected_boundary.png",
        "description": (
            "8-connected boundary (diagonal diamond): boundary pixels only touch "
            "diagonally. The 8-way fill checks diagonal neighbors and slips RIGHT "
            "BETWEEN two diagonally-touching boundary pixels, flooding the entire "
            "canvas beyond the boundary."
        ),
    },
]


# ============================================================================
# Headless Screenshot Generation (Actual App Window Capture)
# ============================================================================

def run_headless():
    """
    Generate all test case PNG screenshots by rendering the actual
    filling_window app (sidebar + grid canvas) and capturing the framebuffer.
    """
    import OpenGL.GL as gl
    import OpenGL.GLUT as glut

    sys.path.insert(0, APP_SRC)
    import filling_window as fw

    current_tc = [0]  # mutable index

    def setup_and_run(tc_index):
        if tc_index >= len(TEST_CASES):
            print(f"\n{'=' * 60}")
            print("ALL TEST CASES COMPLETED SUCCESSFULLY!")
            print(f"Screenshots saved to: {OUTPUT_DIR}")
            print(f"{'=' * 60}")
            os._exit(0)
            return

        tc = TEST_CASES[tc_index]
        print(f"\n{'=' * 60}")
        print(f"  {tc['id']}: {tc['label']}")
        print(f"  Algorithm: {tc['algorithm']}")
        print(f"  Expected:  {tc['expected']}")
        print(f"{'=' * 60}")

        # Clear
        fw.GRID_CELLS.clear()
        fw.SEED_POINT = None
        fw.IS_FILLING = False
        fw.FILL_QUEUE.clear()
        fw.FILL_VISITED.clear()
        fw.FILL_COUNT = 0
        fw.IS_DRAWING_BOUNDARY = False

        # Configure
        fw.CURRENT_ALGORITHM = tc["algorithm"]
        fw.CURRENT_BOUNDARY_COLOR_NAME = "Black"
        fw.CURRENT_BOUNDARY_COLOR = fw.BOUNDARY_COLORS["Black"]
        fw.CURRENT_FILL_COLOR_NAME = "Green"
        fw.CURRENT_FILL_COLOR = fw.FILL_COLORS["Green"]
        fw.CURRENT_MODE = "FILL"
        fw.CURRENT_SPEED_MODE = "Instant Fill"

        # Draw boundary
        boundary_cells = tc["boundary_fn"]()
        for (col, row) in boundary_cells:
            fw.GRID_CELLS[(col, row)] = fw.CURRENT_BOUNDARY_COLOR
        print(f"  Drew {len(boundary_cells)} boundary pixels")

        # Fill
        seed_col, seed_row = tc["seed"]
        fw.SEED_POINT = (seed_col, seed_row)
        fw.start_boundary_fill(seed_col, seed_row)
        print(f"  Filled {fw.FILL_COUNT} cells")

        glut.glutPostRedisplay()
        glut.glutTimerFunc(500, take_screenshot, tc_index)

    def take_screenshot(tc_index):
        tc = TEST_CASES[tc_index]
        fw.display()

        w, h = fw.CURRENT_WIDTH, fw.CURRENT_HEIGHT
        gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
        raw = gl.glReadPixels(0, 0, w, h, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)

        rows = [raw[i * w * 3:(i + 1) * w * 3] for i in range(h)]
        rows.reverse()
        raw_flipped = b"".join(rows)

        def _chunk(chunk_type, data):
            c = chunk_type + data
            return (struct.pack(">I", len(data)) + c +
                    struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF))

        png = b"\x89PNG\r\n\x1a\n"
        png += _chunk(b"IHDR", struct.pack(">IIBBBB B", w, h, 8, 2, 0, 0, 0))
        raw_lines = b"".join(
            b"\x00" + raw_flipped[i * w * 3:(i + 1) * w * 3] for i in range(h)
        )
        png += _chunk(b"IDAT", zlib.compress(raw_lines, 9))
        png += _chunk(b"IEND", b"")

        filepath = os.path.join(OUTPUT_DIR, tc["file"])
        with open(filepath, "wb") as f:
            f.write(png)
        print(f"  ✓ Screenshot saved: {filepath}")

        glut.glutTimerFunc(200, lambda val: setup_and_run(tc_index + 1), 0)

    def start_tests(val):
        setup_and_run(0)

    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_DOUBLE | glut.GLUT_RGB)
    glut.glutInitWindowSize(fw.CURRENT_WIDTH, fw.CURRENT_HEIGHT)
    glut.glutInitWindowPosition(120, 100)
    glut.glutCreateWindow("Boundary Fill — Screenshot Generator")

    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    glut.glutDisplayFunc(fw.display)
    glut.glutReshapeFunc(fw.reshape)

    print(f"{'=' * 60}")
    print("  BOUNDARY FILL — Generating Test Case Screenshots")
    print(f"{'=' * 60}")

    glut.glutTimerFunc(1000, start_tests, 0)
    glut.glutMainLoop()


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    if "--headless" in sys.argv:
        run_headless()
    else:
        # Launch the interactive filling app
        sys.path.insert(0, APP_SRC)
        import filling_window as fw
        fw.run()
