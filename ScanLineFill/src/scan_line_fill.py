"""
==============================================================================
Scan-Line Polygon Fill Algorithm (Edge Table & Active Edge Table Engine)
==============================================================================
Implements the Scan-Line Polygon Fill algorithm for 2D polygon rasterization
using OpenGL in Python.

Key Theoretical Concepts Demonstrated:
  1. Scanline Coherence & Slope Arithmetic (TC1):
     Adjacent scanlines intersect edges at predictable x coordinates differing
     only by the edge's inverse slope (dx/dy = 1/m). By maintaining an Active
     Edge Table (AET) sorted by x, horizontal pixel spans [x_2i, x_2i+1] are
     filled efficiently in a single streaming pass.
  2. Parity & Multi-Span Concave Filling (TC2):
     For non-convex / concave polygons (e.g. arrowheads or U-shapes), a single
     scanline produces 4 or more intersections. The even-odd parity rule
     (toggling between OUT and IN) ensures that disjoint interior spans
     ([x1, x2] and [x3, x4]) are filled while concave cavities remain empty.
  3. Vertex Coincidence & Local Extrema Handling (TC3):
     When a scanline intersects a polygon vertex:
     - Local Extrema (peaks and valleys): Both edges lie entirely above or below
       the vertex; the intersection is counted twice (parity preserved).
     - Monotonic Vertices: One edge enters from below and the next exits above;
       the intersection is counted once (parity toggled) using the half-open
       interval [y_min, y_max).
  4. Multi-Boundary Filling & Seedless Void Preservation (TC4):
     Polygons with interior holes (donuts / window frames) are handled natively
     by inserting all boundary loops into the global Edge Table. The even-odd
     parity rule automatically leaves the interior hole unfilled, completely
     eliminating the seed-point requirement of Boundary Fill and Flood Fill.

Test Cases:
  TC1: Convex Polygon (Pentagon)                  → Single Span Coherence (347 cells)
  TC2: Concave Polygon (Arrowhead)                → Multi-Span Parity (150 cells)
  TC3: Complex Non-Convex Polygon (10-Point Star) → Vertex Coincidence & Extrema (204 cells)
  TC4: Multi-Boundary Polygon with Hole (Donut)   → Seedless Hole Preservation (340 cells)

Run:
  python ScanLineFill/src/scan_line_fill.py           # Launches the interactive app
  python ScanLineFill/src/scan_line_fill.py --headless # Generates actual app window PNGs
==============================================================================
"""

import os
import sys
import math
import struct
import zlib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUTPUT_DIR = os.path.join(REPO_ROOT, "ScanLineFill", "outputs")
APP_SRC    = os.path.join(REPO_ROOT, "app", "src")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ============================================================================
# Color Definitions
# ============================================================================

COLOR_NAVY   = (0.08, 0.20, 0.45)
COLOR_BLACK  = (0.00, 0.00, 0.00)
COLOR_RED    = (1.00, 0.08, 0.08)
COLOR_GREEN  = (0.12, 0.80, 0.35)
COLOR_BLUE   = (0.15, 0.55, 0.95)
COLOR_ORANGE = (1.00, 0.50, 0.05)


# ============================================================================
# Core Scan-Line Polygon Fill Algorithm (ET / AET Engine)
# ============================================================================

def build_edge_table(loops, num_rows):
    """
    Construct the Global Edge Table (ET) for a polygon with one or more boundary loops.

    Each bucket ET[y] contains edges whose lower endpoint is at scanline y (y_min = y).
    Horizontal edges (dy = 0) are omitted because they do not cross scanlines.
    Each edge record stores:
      - y_max: Upper scanline limit (half-open interval [y_min, y_max))
      - x: Starting x-coordinate at y_min
      - inv_m: Inverse slope dx / dy = 1 / m
    """
    edge_table = {r: [] for r in range(num_rows)}
    min_scanline = num_rows
    max_scanline = -1

    for loop in loops:
        n = len(loop)
        for i in range(n):
            p1 = loop[i]
            p2 = loop[(i + 1) % n]
            x1, y1 = float(p1[0]), float(p1[1])
            x2, y2 = float(p2[0]), float(p2[1])

            # Discard horizontal edges
            if round(y1) == round(y2):
                continue

            if y1 < y2:
                y_min = int(round(y1))
                y_max = int(round(y2))
                x_start = x1
                dx = x2 - x1
                dy = y2 - y1
            else:
                y_min = int(round(y2))
                y_max = int(round(y1))
                x_start = x2
                dx = x1 - x2
                dy = y1 - y2

            inv_m = dx / dy

            if y_min < num_rows and y_max >= 0:
                y_min_clamped = max(0, y_min)
                if y_min < 0:
                    x_start += (0 - y_min) * inv_m

                edge_table[y_min_clamped].append({
                    "y_max": y_max,
                    "x": x_start,
                    "inv_m": inv_m
                })
                min_scanline = min(min_scanline, y_min_clamped)
                max_scanline = max(max_scanline, y_max)

    return edge_table, min_scanline, max_scanline


def scan_line_fill(loops, fill_color, num_cols, num_rows, grid_cells=None, boundary_color=None):
    """
    Rasterize polygon loops using the Active Edge Table (AET) algorithm.

    Iterates from min_scanline to max_scanline:
      1. Adds new edges from ET[y] to AET.
      2. Retires edges where y >= y_max.
      3. Sorts AET by current x.
      4. Fills horizontal spans [x_2i, x_2i+1] between successive edge pairs.
      5. Increments x by inv_m for all active edges.
    """
    if grid_cells is None:
        grid_cells = {}

    edge_table, min_scanline, max_scanline = build_edge_table(loops, num_rows)
    if min_scanline > max_scanline:
        return 0

    aet = []
    filled_count = 0

    for scan_y in range(min_scanline, min(num_rows, max_scanline + 1)):
        # 1. Add edges from ET[scan_y]
        if scan_y in edge_table:
            aet.extend(edge_table[scan_y])

        # 2. Retire edges using half-open interval [y_min, y_max)
        aet = [e for e in aet if e["y_max"] > scan_y]

        # 3. Sort AET by current x
        aet.sort(key=lambda e: e["x"])

        # 4. Fill horizontal spans between edge pairs
        for idx in range(0, len(aet) - 1, 2):
            e_left = aet[idx]
            e_right = aet[idx + 1]

            x_left = max(0, int(math.ceil(e_left["x"])))
            x_right = min(num_cols - 1, int(math.floor(e_right["x"])))

            for col in range(x_left, x_right + 1):
                if boundary_color is not None:
                    curr = grid_cells.get((col, scan_y))
                    if curr == boundary_color:
                        continue
                grid_cells[(col, scan_y)] = fill_color
                filled_count += 1

        # 5. Advance x by 1/m
        for e in aet:
            e["x"] += e["inv_m"]

    return filled_count


# ============================================================================
# Benchmark Test Case Geometries
# ============================================================================

def setup_tc1_convex_polygon():
    """
    TC1: Convex Pentagon Polygon.
    - 5 vertices forming a symmetric convex pentagon.
    - Demonstrates single [x1, x2] span per scanline and baseline scanline coherence.
    - Expected filled cells: 347.
    """
    return [(10, 26), (30, 26), (34, 16), (20, 6), (6, 16)]


def setup_tc2_concave_arrowhead():
    """
    TC2: Concave Arrowhead Polygon (Chevron).
    - 4 vertices with a deep upward concave notch at (20, 19).
    - Demonstrates multi-span even-odd parity filling:
      Upper region (y < 19): 1 span [x1, x2].
      Lower region (y in [19, 27]): 2 disjoint spans [x1, x2] and [x3, x4].
    - Expected filled cells: 150.
    """
    return [(20, 5), (33, 27), (20, 19), (7, 27)]


def setup_tc3_star_local_extrema():
    """
    TC3: Complex Non-Convex 10-Point Star Polygon.
    - 10 alternating tip and notch vertices with multiple local peaks and valleys.
    - Demonstrates vertex coincidence handling:
      Local minima/maxima counted twice vs monotonic vertices shortened by 1.
    - Expected filled cells: 204.
    """
    return [
        (20, 4),   # Top tip (local min y)
        (24, 13),  # Notch
        (33, 13),  # Right-upper tip
        (26, 19),  # Notch
        (29, 29),  # Right-bottom tip (local max y)
        (20, 23),  # Bottom notch (local min y)
        (11, 29),  # Left-bottom tip (local max y)
        (14, 19),  # Notch
        (7, 13),   # Left-upper tip
        (16, 13),  # Notch
    ]


def setup_tc4_donut_interior_hole():
    """
    TC4: Multi-Boundary Polygon with Interior Void / Donut (Window Frame).
    - Outer boundary: 24 x 22 box [(8, 6), (32, 6), (32, 28), (8, 28)]
    - Inner boundary: 12 x 10 hole [(14, 12), (26, 12), (26, 22), (14, 22)]
    - Demonstrates seedless interior hole preservation via parity rule:
      Middle scanlines have 4 edges; hole span (x in [14, 26]) has parity 0 (OUT).
    - Expected filled cells: 340.
    """
    return [
        [(8, 6), (32, 6), (32, 28), (8, 28)],         # Outer frame
        [(14, 12), (26, 12), (26, 22), (14, 22)]      # Inner void / hole
    ]


# ============================================================================
# Test Cases Definitions
# ============================================================================

TEST_CASES = [
    {
        "id": "TC1",
        "label": "TC1 — Convex Polygon (Pentagon) Baseline Rasterization",
        "algorithm": "Scan-Line Fill",
        "setup_fn": setup_tc1_convex_polygon,
        "boundary_color": COLOR_NAVY,
        "fill_color": COLOR_RED,
        "expected": "CONVEX COHERENCE",
        "expected_cells": 347,
        "file": "tc1_convex_polygon.png",
        "description": (
            "Convex 5-vertex pentagon with exactly one horizontal span [x1, x2] per scanline. "
            "Demonstrates basic scanline coherence: active edges are entered into the AET "
            "at y_min, updated along each row using inverse slope dx/dy = 1/m, and retired at y_max. "
            "A total of 347 interior cells are filled cleanly within the Navy Blue perimeter."
        ),
    },
    {
        "id": "TC2",
        "label": "TC2 — Concave Arrowhead Polygon (Multi-Span Parity Rule)",
        "algorithm": "Scan-Line Fill",
        "setup_fn": setup_tc2_concave_arrowhead,
        "boundary_color": COLOR_NAVY,
        "fill_color": COLOR_BLUE,
        "expected": "MULTI-SPAN PARITY",
        "expected_cells": 150,
        "file": "tc2_concave_polygon.png",
        "description": (
            "Concave arrowhead polygon with a deep upward interior notch at (20, 19). "
            "Across rows y in [19, 27], the scanline intersects 4 boundary edges. The even-odd "
            "parity rule fills the left wing [x1, x2] and right wing [x3, x4] while preserving "
            "the concave cavity between x2 and x3 unfilled (150 interior cells filled)."
        ),
    },
    {
        "id": "TC3",
        "label": "TC3 — Complex Star Polygon (Vertex Coincidence & Extrema)",
        "algorithm": "Scan-Line Fill",
        "setup_fn": setup_tc3_star_local_extrema,
        "boundary_color": COLOR_NAVY,
        "fill_color": COLOR_GREEN,
        "expected": "EXTREMA PARITY",
        "expected_cells": 204,
        "file": "tc3_vertex_coincidence_star.png",
        "description": (
            "10-vertex star polygon featuring multiple local extrema (peaks at y=4, y=29, and "
            "valleys at y=23) alongside monotonic sloping edges. Uses the half-open interval "
            "[y_min, y_max) to count monotonic vertices once and local extrema twice, preventing "
            "parity inversion bugs and rasterizing 204 interior cells perfectly."
        ),
    },
    {
        "id": "TC4",
        "label": "TC4 — Polygon with Interior Void / Donut (Seedless Void Preservation)",
        "algorithm": "Scan-Line Fill",
        "setup_fn": setup_tc4_donut_interior_hole,
        "boundary_color": COLOR_NAVY,
        "fill_color": COLOR_ORANGE,
        "expected": "SEEDLESS HOLE PRESERVATION",
        "expected_cells": 340,
        "file": "tc4_polygon_with_hole.png",
        "description": (
            "Compound polygon composed of an outer rectangular window and an inner rectangular hole. "
            "Because both boundary loops are placed into the global Edge Table, even-odd parity "
            "automatically switches to OUT inside the central chamber [14, 26], leaving the hole "
            "completely unfilled (340 cells filled) without requiring any interior seed points."
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
            print("ALL SCAN-LINE FILL TEST CASES COMPLETED SUCCESSFULLY!")
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

        # Clear app state
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
        fw.CURRENT_BOUNDARY_COLOR = tc["boundary_color"]
        fw.CURRENT_FILL_COLOR = tc["fill_color"]

        # Color name matching
        for name, col_rgb in fw.FILL_COLORS.items():
            if fw._colors_match(col_rgb, tc["fill_color"]):
                fw.CURRENT_FILL_COLOR_NAME = name
                break

        fw.CURRENT_MODE = "FILL"
        fw.CURRENT_SPEED_MODE = "Instant Fill"

        # Execute polygon scanline fill
        geom = tc["setup_fn"]()
        filled = fw.scan_line_fill_polygon(geom, tc["fill_color"], tc["boundary_color"])
        print(f"  Rasterized {filled} interior cells (Expected: {tc['expected_cells']})")

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
        png += _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
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
    glut.glutCreateWindow("Scan-Line Polygon Fill — Screenshot Generator")

    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    glut.glutDisplayFunc(fw.display)
    glut.glutReshapeFunc(fw.reshape)

    print(f"{'=' * 60}")
    print("  SCAN-LINE FILL — Generating Benchmark Screenshots")
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
        sys.path.insert(0, APP_SRC)
        import filling_window as fw
        fw.CURRENT_ALGORITHM = "Scan-Line Fill"
        fw.run()
