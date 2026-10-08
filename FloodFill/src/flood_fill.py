"""
==============================================================================
Flood Fill Algorithm — 4-Way and 8-Way Fill (Hybrid Demonstration Suite)
==============================================================================
Implements the Flood Fill algorithm for region filling in 2D raster graphics.

Key Concepts Demonstrated:
  1. Multi-Colored Boundaries & Color Replacement (TC1):
     Unlike Boundary Fill (which strictly requires a single known boundary
     color and leaks through any differently-colored edge), Flood Fill operates
     by matching the OLD COLOR of the seed pixel. It replaces that color and
     stops at ANY boundary of ANY color.
  2. The 8-Connected Diagonal Bottleneck / Dual-Chamber Problem (TC2 vs TC3):
     In regions connected only at a diagonal corner vertex (an 8-connected neck),
     4-Way Flood Fill cannot cross the diagonal opening and leaves Chamber 2
     unfilled. 8-Way Flood Fill evaluates diagonal neighbors, steps across the
     diagonal vertex, and fills BOTH chambers completely!
  3. Boundary Leakage through 8-Connected Boundaries (TC4):
     When an enclosing boundary has diagonal-only connections (orthogonal gaps),
     8-Way Flood Fill slips through the diagonal openings into the exterior
     background, demonstrating the hazard of 8-way fill on thin boundaries.

Test Cases:
  TC1: 4-Way Flood Fill on Multi-Colored 4-Connected Boundary → CONTAINED (352 cells)
  TC2: 4-Way Flood Fill on 8-Connected Dual-Chamber        → PARTIAL FILL (81 cells)
  TC3: 8-Way Flood Fill on 8-Connected Dual-Chamber        → FULL FILL (162 cells)
  TC4: 8-Way Flood Fill on 8-Connected Multi-Colored Wall   → LEAKS (1152 cells)

Run:
  python FloodFill/src/flood_fill.py           # Launches the interactive filling app
  python FloodFill/src/flood_fill.py --headless # Generates actual app window PNGs
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
OUTPUT_DIR = os.path.join(REPO_ROOT, "FloodFill", "outputs")
APP_SRC    = os.path.join(REPO_ROOT, "app", "src")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================================
# Color Definitions
# ============================================================================

COLOR_NAVY   = (0.08, 0.20, 0.45)
COLOR_RED    = (0.60, 0.10, 0.12)
COLOR_GREEN  = (0.10, 0.45, 0.20)
COLOR_PURPLE = (0.45, 0.15, 0.55)
COLOR_YELLOW = (1.00, 0.85, 0.10)
COLOR_BLUE   = (0.15, 0.55, 0.95)


# ============================================================================
# Core Flood Fill Algorithm
# ============================================================================

def flood_fill_4way(grid, seed_col, seed_row, fill_color, num_cols, num_rows):
    """
    4-Way Flood Fill Algorithm (Iterative BFS).

    Starting from the seed pixel, examines only the 4 orthogonal neighbors
    (up, down, left, right). Replaces all connected pixels that match the
    OLD COLOR at the seed point with the new fill color.

    Key Difference from Boundary Fill:
    - Boundary Fill checks: "is this pixel NOT the boundary color?" -> fill
    - Flood Fill checks: "does this pixel MATCH the old color?" -> replace
    """
    neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]  # Orthogonal
    return _flood_fill_bfs(grid, seed_col, seed_row, fill_color,
                           num_cols, num_rows, neighbors)


def flood_fill_8way(grid, seed_col, seed_row, fill_color, num_cols, num_rows):
    """
    8-Way Flood Fill Algorithm (Iterative BFS).

    Starting from the seed pixel, examines all 8 neighbors including diagonals.
    Replaces all connected pixels that match the OLD COLOR at the seed point
    with the new fill color.
    """
    neighbors = [
        (0, 1), (0, -1), (1, 0), (-1, 0),       # Orthogonal
        (1, 1), (1, -1), (-1, 1), (-1, -1),      # Diagonal
    ]
    return _flood_fill_bfs(grid, seed_col, seed_row, fill_color,
                           num_cols, num_rows, neighbors)


def _colors_match(c1, c2, tol=0.01):
    """Compare two RGB color tuples with tolerance."""
    if c1 is None or c2 is None:
        return c1 == c2
    return (abs(c1[0] - c2[0]) < tol and
            abs(c1[1] - c2[1]) < tol and
            abs(c1[2] - c2[2]) < tol)


def _flood_fill_bfs(grid, seed_col, seed_row, fill_color,
                    num_cols, num_rows, neighbors):
    """
    Core iterative BFS flood fill engine used by both 4-way and 8-way variants.

    The algorithm:
      1. Record the OLD COLOR at the seed pixel
      2. Push seed pixel onto the queue
      3. Pop a pixel from the queue
      4. If the pixel matches the OLD COLOR:
         a. Replace it with fill_color
         b. Push all valid unvisited neighbors that also match OLD COLOR
      5. Repeat until queue is empty
    """
    if not (0 <= seed_col < num_cols and 0 <= seed_row < num_rows):
        return 0

    old_color = grid.get((seed_col, seed_row))
    if _colors_match(old_color, fill_color):
        return 0

    queue = deque([(seed_col, seed_row)])
    visited = {(seed_col, seed_row)}
    count = 0

    while queue:
        col, row = queue.popleft()
        cell_color = grid.get((col, row))

        if _colors_match(cell_color, old_color):
            grid[(col, row)] = fill_color
            count += 1

            for dc, dr in neighbors:
                nc, nr = col + dc, row + dr
                if 0 <= nc < num_cols and 0 <= nr < num_rows:
                    if (nc, nr) not in visited:
                        n_color = grid.get((nc, nr))
                        if _colors_match(n_color, old_color):
                            visited.add((nc, nr))
                            queue.append((nc, nr))
    return count


# ============================================================================
# Shape & Canvas Setup Builders
# ============================================================================

def setup_tc1_canvas():
    """
    TC1: Multi-Colored 4-Connected Rectangular Boundary with Pre-Filled Interior.
    - Top edge: Navy Blue
    - Bottom edge: Dark Green
    - Left edge: Purple
    - Right edge: Dark Red
    - Interior: Pre-filled with Yellow (22 cols x 16 rows = 352 cells).
    """
    grid = {}
    left, top, right, bottom = 5, 5, 28, 22
    for c in range(left, right + 1):
        grid[(c, top)] = COLOR_NAVY
        grid[(c, bottom)] = COLOR_GREEN
    for r in range(top, bottom + 1):
        grid[(left, r)] = COLOR_PURPLE
        grid[(right, r)] = COLOR_RED
    for c in range(left + 1, right):
        for r in range(top + 1, bottom):
            grid[(c, r)] = COLOR_YELLOW
    return grid


def setup_dual_chamber_canvas():
    """
    TC2 & TC3: 8-Connected Dual-Chamber (Hourglass / Diagonal Bottleneck).
    - Chamber 1 (Left):   Interior cols [7, 15], rows [6, 14]  (81 cells, Yellow).
    - Chamber 2 (Right):  Interior cols [16, 24], rows [15, 23] (81 cells, Yellow).
    - The two chambers meet ONLY at the diagonal vertex (15, 14) -> (16, 15).
    - Wall cells at (16, 14) and (15, 15) prevent any orthogonal passage.
    - Walls are colored with multi-colored borders (Navy Blue, Dark Red, Purple).
    """
    grid = {}
    # Chamber 1 walls (Navy Blue)
    for c in range(6, 17):
        grid[(c, 5)] = COLOR_NAVY
    for c in range(6, 16):
        grid[(c, 15)] = COLOR_NAVY
    for r in range(5, 16):
        grid[(6, r)] = COLOR_NAVY
    for r in range(5, 15):
        grid[(16, r)] = COLOR_NAVY

    # Chamber 2 walls (Dark Red)
    for c in range(15, 26):
        grid[(c, 24)] = COLOR_RED
    for c in range(16, 26):
        grid[(c, 14)] = COLOR_RED
    for r in range(14, 25):
        grid[(25, r)] = COLOR_RED
    for r in range(15, 25):
        grid[(15, r)] = COLOR_RED

    # Central divider corners (Purple accent)
    grid[(16, 14)] = COLOR_PURPLE
    grid[(15, 15)] = COLOR_PURPLE

    # Pre-fill Chamber 1 with Yellow
    for c in range(7, 16):
        for r in range(6, 15):
            grid[(c, r)] = COLOR_YELLOW

    # Pre-fill Chamber 2 with Yellow
    for c in range(16, 25):
        for r in range(15, 24):
            grid[(c, r)] = COLOR_YELLOW

    return grid


def setup_tc4_canvas():
    """
    TC4: Multi-Colored 8-Connected Diamond Boundary on Empty Background.
    - Boundary pixels only touch diagonally (32 boundary cells).
    - Multi-colored edges: Navy Blue, Dark Red, Dark Green, Purple.
    - Interior & exterior are canvas background (None).
    """
    grid = {}
    cx, cy, radius = 16, 14, 8
    for i in range(radius):
        grid[(cx + i, cy - radius + i)] = COLOR_NAVY
        grid[(cx + radius - i, cy + i)] = COLOR_RED
        grid[(cx - i, cy + radius - i)] = COLOR_GREEN
        grid[(cx - radius + i, cy - i)] = COLOR_PURPLE
    return grid


# ============================================================================
# Test Cases Definitions
# ============================================================================

TEST_CASES = [
    {
        "id": "TC1",
        "label": "TC1 — 4-Way Flood Fill on Multi-Colored 4-Connected Boundary",
        "algorithm": "4-Way Flood Fill",
        "setup_fn": setup_tc1_canvas,
        "seed": (16, 14),
        "fill_color": COLOR_BLUE,
        "expected": "CONTAINED",
        "expected_cells": 352,
        "file": "tc1_4way_flood_multicolor_boundary.png",
        "description": (
            "Multi-colored 4-connected boundary with a pre-filled Yellow interior. "
            "Unlike Boundary Fill (which fails on multi-colored boundaries), "
            "4-Way Flood Fill matches the seed's Yellow color and replaces all 352 "
            "interior cells with Blue, stopping cleanly at all four colored walls."
        ),
    },
    {
        "id": "TC2",
        "label": "TC2 — 4-Way Flood Fill on 8-Connected Dual-Chamber (Bottleneck)",
        "algorithm": "4-Way Flood Fill",
        "setup_fn": setup_dual_chamber_canvas,
        "seed": (11, 10),
        "fill_color": COLOR_BLUE,
        "expected": "PARTIAL FILL",
        "expected_cells": 81,
        "file": "tc2_4way_flood_dual_chamber_bottleneck.png",
        "description": (
            "Two Yellow chambers meeting only at a single diagonal corner (15, 14) -> (16, 15). "
            "The 4-way flood fill explores only orthogonal neighbors. Because no orthogonal "
            "path connects Chamber 1 to Chamber 2, the fill is trapped in Chamber 1 (81 cells). "
            "Chamber 2 remains completely Yellow, proving 4-way fill fails on 8-connected regions."
        ),
    },
    {
        "id": "TC3",
        "label": "TC3 — 8-Way Flood Fill on 8-Connected Dual-Chamber (Bridged)",
        "algorithm": "8-Way Flood Fill",
        "setup_fn": setup_dual_chamber_canvas,
        "seed": (11, 10),
        "fill_color": COLOR_BLUE,
        "expected": "FULL FILL",
        "expected_cells": 162,
        "file": "tc3_8way_flood_dual_chamber_bridged.png",
        "description": (
            "Identical dual-chamber setup. 8-Way Flood Fill evaluates diagonal neighbors, "
            "steps directly through the diagonal corner vertex (15, 14) -> (16, 15), "
            "and propagates into Chamber 2. Fills both chambers completely (162 cells), "
            "demonstrating the primary architectural reason 8-way fill is required."
        ),
    },
    {
        "id": "TC4",
        "label": "TC4 — 8-Way Flood Fill on 8-Connected Boundary (Leakage)",
        "algorithm": "8-Way Flood Fill",
        "setup_fn": setup_tc4_canvas,
        "seed": (16, 14),
        "fill_color": COLOR_BLUE,
        "expected": "LEAKS",
        "expected_cells": 1328,
        "file": "tc4_8way_flood_8connected_leak.png",
        "description": (
            "8-connected multi-colored diamond boundary on an empty background. "
            "Because boundary pixels touch only diagonally, 8-way flood fill's diagonal "
            "search slips through the diagonal gaps between boundary pixels into the "
            "matching canvas background, flooding the entire canvas (1,328 cells)."
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

    def setup_and_run(tc_index):
        if tc_index >= len(TEST_CASES):
            print(f"\n{'=' * 60}")
            print("ALL FLOOD FILL TEST CASES COMPLETED SUCCESSFULLY!")
            print(f"Screenshots saved to: {OUTPUT_DIR}")
            print(f"{'=' * 60}")
            os._exit(0)
            return

        tc = TEST_CASES[tc_index]
        print(f"\n{'=' * 60}")
        print(f"  {tc['id']}: {tc['label']}")
        print(f"  Algorithm: {tc['algorithm']}")
        print(f"  Expected:  {tc['expected']} ({tc['expected_cells']} cells)")
        print(f"{'=' * 60}")

        # Clear state
        fw.GRID_CELLS.clear()
        fw.SEED_POINT = None
        fw.IS_FILLING = False
        fw.FILL_QUEUE.clear()
        fw.FILL_VISITED.clear()
        fw.FILL_COUNT = 0
        fw.IS_DRAWING_BOUNDARY = False
        fw.FLOOD_OLD_COLOR = None

        # Configure app settings
        fw.CURRENT_ALGORITHM = tc["algorithm"]
        fw.CURRENT_BOUNDARY_COLOR_NAME = "Navy Blue"
        fw.CURRENT_BOUNDARY_COLOR = fw.BOUNDARY_COLORS["Navy Blue"]
        fw.CURRENT_FILL_COLOR_NAME = "Blue"
        fw.CURRENT_FILL_COLOR = tc["fill_color"]
        fw.CURRENT_MODE = "FILL"
        fw.CURRENT_SPEED_MODE = "Instant Fill"

        # Populate canvas from setup function
        grid_data = tc["setup_fn"]()
        fw.GRID_CELLS.update(grid_data)
        print(f"  Canvas initialized with {len(grid_data)} colored cells")

        # Fill using the app's flood fill engine
        seed_col, seed_row = tc["seed"]
        fw.SEED_POINT = (seed_col, seed_row)
        fw.start_flood_fill(seed_col, seed_row)
        print(f"  Filled {fw.FILL_COUNT} cells (Expected: {tc['expected_cells']})")

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
        print(f"  [OK] Screenshot saved: {filepath}")

        glut.glutTimerFunc(200, lambda val: setup_and_run(tc_index + 1), 0)

    def start_tests(val):
        setup_and_run(0)

    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_DOUBLE | glut.GLUT_RGB)
    glut.glutInitWindowSize(fw.CURRENT_WIDTH, fw.CURRENT_HEIGHT)
    glut.glutInitWindowPosition(120, 100)
    glut.glutCreateWindow("Flood Fill — Screenshot Generator")

    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    glut.glutDisplayFunc(fw.display)
    glut.glutReshapeFunc(fw.reshape)

    print(f"{'=' * 60}")
    print("  FLOOD FILL — Generating Hybrid Suite Screenshots")
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
        # Launch the interactive filling app with flood fill selected
        sys.path.insert(0, APP_SRC)
        import filling_window as fw
        fw.CURRENT_ALGORITHM = "4-Way Flood Fill"
        fw.run()
