"""
==============================================================================
Interactive 2D Filling Algorithms Application (Left Sidebar Layout)
==============================================================================
Features:
- Left Control Sidebar with studio dark styling, hosting all controls:
  - Algorithm Selection: 4-Way Boundary Fill, 8-Way Boundary Fill,
    Flood Fill (Upcoming), Scan Line Fill (Upcoming)
  - Tool Modes: Draw Brush (B), Grid Click (G), Fill Mode (F)
  - 5 Boundary Colors & 5 Fill Colors with active swatch indicators
  - Quick Action Buttons: Clear Grid (C), Save Screenshot (P), Reset Defaults
  - Live Status & Guide Card
- Graph-paper style grid canvas on the right (light-blue grid lines, crisp studio background).
- Bresenham line rasterization for leak-free brush tracing.
- High-contrast concentric ring seed point indicator.
- Animated BFS queue fill engine.
- Scan-Line Fill with a visible sweeping scan line (intersection markers +
  row-by-row span filling).
==============================================================================
"""

import os
import sys
import math
import struct
import zlib
from collections import deque

import OpenGL.GL as gl      # type: ignore
import OpenGL.GLUT as glut  # type: ignore
import OpenGL.GLU as glu    # type: ignore

# ── Paths ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR    = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUTPUT_DIR = os.path.join(APP_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Window & Sidebar Metrics ────────────────────────────────────────────────
DEFAULT_WIDTH  = 1050
DEFAULT_HEIGHT = 680
CURRENT_WIDTH  = DEFAULT_WIDTH
CURRENT_HEIGHT = DEFAULT_HEIGHT

SIDEBAR_WIDTH  = 250
CELL_SIZE      = 20  # Cell dimension in window pixels

# ── Left Sidebar Studio Theme ───────────────────────────────────────────────
SIDEBAR_BG_COLOR     = (0.065, 0.075, 0.098)   # Deep obsidian-navy panel
SIDEBAR_CARD_BG      = (0.090, 0.105, 0.138)   # Elevated card background
SIDEBAR_BORDER_COLOR = (0.18, 0.22, 0.30)     # Subtle divider line
SIDEBAR_TEXT_PRIMARY = (0.92, 0.94, 0.98)     # Crisp white
SIDEBAR_TEXT_MUTED   = (0.55, 0.60, 0.70)     # Secondary slate
SIDEBAR_ACCENT       = (0.0, 0.82, 1.0)       # Electric cyan highlight
SIDEBAR_ACTIVE_BG    = (0.14, 0.38, 0.62)     # Active button background

# ── Graph Paper Canvas Theme (Matching Main Application) ────────────────────
CANVAS_BG_COLOR = (0.972, 0.980, 0.988, 1.0)  # Studio canvas tone (matching line_drawing_app.py)
GRID_LINE_COLOR = (0.78, 0.85, 0.92)          # Crisp graph-paper light blue
SCANLINE_COLOR  = (0.93, 0.18, 0.86)          # Vivid magenta sweeping scan line

# ── Color Palettes (5 Boundary Colors & 5 Fill Colors) ──────────────────────
BOUNDARY_COLORS = {
    "Black":      (0.00, 0.00, 0.00),
    "Navy Blue":  (0.08, 0.20, 0.45),
    "Dark Green": (0.08, 0.35, 0.15),
    "Dark Red":   (0.50, 0.08, 0.10),
    "Purple":     (0.35, 0.10, 0.45),
}

FILL_COLORS = {
    "Red":    (1.00, 0.08, 0.08),
    "Green":  (0.12, 0.80, 0.35),
    "Blue":   (0.15, 0.55, 0.95),
    "Yellow": (1.00, 0.85, 0.10),
    "Orange": (1.00, 0.50, 0.05),
}

CURRENT_BOUNDARY_COLOR_NAME = "Black"
CURRENT_BOUNDARY_COLOR      = BOUNDARY_COLORS["Black"]

CURRENT_FILL_COLOR_NAME     = "Red"
CURRENT_FILL_COLOR          = FILL_COLORS["Red"]

# ── Algorithm Options ───────────────────────────────────────────────────────
ALGORITHM_LIST = [
    "4-Way Boundary Fill",
    "8-Way Boundary Fill",
    "4-Way Flood Fill",
    "8-Way Flood Fill",
    "Scan-Line Fill",
]
CURRENT_ALGORITHM = "4-Way Boundary Fill"

SPEED_MODES = ["Smooth (Animated)", "Fast (Animated)", "Instant Fill"]
CURRENT_SPEED_MODE = "Smooth (Animated)"

# ── Interaction Modes: "BRUSH", "CLICK", or "FILL" ──────────────────────────
CURRENT_MODE = "BRUSH"
IS_DRAWING_BOUNDARY = False
LAST_DRAW_CELL = None
SEED_POINT = None  # (col, row) of active fill seed point
FLOOD_OLD_COLOR = None  # The original color at seed point (for Flood Fill)

# ── Filling Animation State ─────────────────────────────────────────────────
IS_FILLING = False
FILL_QUEUE = deque()
FILL_VISITED = set()
FILL_COUNT = 0
FILL_TIMER_ACTIVE = False

# ── Scan-Line Sweep Animation State ─────────────────────────────────────────
SCANLINE_ROWS = []             # Ordered list of (row, [(x_left, x_right), ...])
SCANLINE_INDEX = 0             # Index of the row currently being processed
SCANLINE_ROW = None            # Row under the visible scan line (None = hidden)
SCANLINE_SPANS = []            # Interior spans on the current scan line
SCANLINE_PENDING_FILL = False  # True = intersections marked, spans not yet filled
SCANLINE_FILL_COLOR = None
SCANLINE_BOUNDARY_COLOR = None
SCANLINE_RUNNING = False
SCANLINE_TIMER_ACTIVE = False

# ── Grid State: dictionary mapping (col, row) -> (r, g, b) ──────────────────
GRID_CELLS = {}

# ── Undo / Redo History Stack ───────────────────────────────────────────────
UNDO_STACK = []
REDO_STACK = []
MAX_UNDO_STEPS = 50


def save_undo_state():
    """Save current grid state to undo stack before making a modification."""
    global UNDO_STACK, REDO_STACK
    UNDO_STACK.append(dict(GRID_CELLS))
    if len(UNDO_STACK) > MAX_UNDO_STEPS:
        UNDO_STACK.pop(0)
    REDO_STACK.clear()


def undo():
    """Undo the last drawing or filling action."""
    global GRID_CELLS, SEED_POINT, IS_FILLING, FILL_QUEUE
    if not UNDO_STACK:
        print("[Undo] Nothing to undo.")
        return

    _stop_scanline_sweep()
    IS_FILLING = False
    FILL_QUEUE.clear()

    REDO_STACK.append(dict(GRID_CELLS))
    prev_state = UNDO_STACK.pop()
    GRID_CELLS.clear()
    GRID_CELLS.update(prev_state)
    SEED_POINT = None
    print(f"[Undo] Action undone. ({len(UNDO_STACK)} steps remaining in history)")
    glut.glutPostRedisplay()


def redo():
    """Redo the last undone action."""
    global GRID_CELLS, SEED_POINT, IS_FILLING, FILL_QUEUE
    if not REDO_STACK:
        print("[Redo] Nothing to redo.")
        return

    _stop_scanline_sweep()
    IS_FILLING = False
    FILL_QUEUE.clear()

    UNDO_STACK.append(dict(GRID_CELLS))
    next_state = REDO_STACK.pop()
    GRID_CELLS.clear()
    GRID_CELLS.update(next_state)
    SEED_POINT = None
    print(f"[Redo] Action redone. ({len(REDO_STACK)} steps remaining)")
    glut.glutPostRedisplay()


# Backward-compatibility placeholder for test suite
OPEN_MENU = None
MENU_ITEMS = ["Algorithms", "Boundary Color", "Fill Color", "Actions"]


# ============================================================================
# Coordinate & Grid Conversion
# ============================================================================

def get_grid_dimensions():
    """Calculate the number of columns and rows based on current canvas area."""
    canvas_w = max(1, CURRENT_WIDTH - SIDEBAR_WIDTH)
    canvas_h = max(1, CURRENT_HEIGHT)
    num_cols = max(1, canvas_w // CELL_SIZE)
    num_rows = max(1, canvas_h // CELL_SIZE)
    return num_cols, num_rows


def mouse_to_grid(x, y):
    """
    Convert window mouse coordinates (x, y) to grid cell (col, row).
    Returns (col, row) or None if click is on the left sidebar.
    """
    if x < SIDEBAR_WIDTH:
        return None
    canvas_x = x - SIDEBAR_WIDTH
    col = canvas_x // CELL_SIZE
    row = y // CELL_SIZE
    num_cols, num_rows = get_grid_dimensions()
    if 0 <= col < num_cols and 0 <= row < num_rows:
        return (col, row)
    return None


def grid_to_screen_rect(col, row):
    """Get screen bounding rectangle [x1, y1, x2, y2] for a grid cell."""
    x1 = SIDEBAR_WIDTH + col * CELL_SIZE
    y1 = row * CELL_SIZE
    x2 = x1 + CELL_SIZE
    y2 = y1 + CELL_SIZE
    return x1, y1, x2, y2


# ============================================================================
# Bresenham Line Rasterization on Grid (Guarantees Leak-Free Boundaries)
# ============================================================================

def bresenham_grid_line(c0, r0, c1, r1):
    """Yield all grid cells along the line between (c0, r0) and (c1, r1)."""
    dc = abs(c1 - c0)
    dr = abs(r1 - r0)
    sc = 1 if c0 < c1 else -1
    sr = 1 if r0 < r1 else -1
    err = dc - dr
    curr_c, curr_r = c0, r0

    while True:
        yield curr_c, curr_r
        if curr_c == c1 and curr_r == r1:
            break
        e2 = 2 * err
        if e2 > -dr:
            err -= dr
            curr_c += sc
        if e2 < dc:
            err += dc
            curr_r += sr


# ============================================================================
# Boundary Fill Algorithm (Iterative BFS Queue Engine)
# ============================================================================

def _colors_match(c1, c2, tol=0.01):
    """Compare two RGB color tuples."""
    if c1 is None or c2 is None:
        return c1 == c2
    return (abs(c1[0] - c2[0]) < tol and
            abs(c1[1] - c2[1]) < tol and
            abs(c1[2] - c2[2]) < tol)


def start_boundary_fill(seed_col, seed_row):
    """Initialize boundary fill algorithm from the seed cell."""
    global IS_FILLING, FILL_QUEUE, FILL_VISITED, FILL_COUNT, FILL_TIMER_ACTIVE
    num_cols, num_rows = get_grid_dimensions()

    if not (0 <= seed_col < num_cols and 0 <= seed_row < num_rows):
        return

    curr_col = GRID_CELLS.get((seed_col, seed_row))

    # Cannot fill if already boundary color or already fill color
    if _colors_match(curr_col, CURRENT_BOUNDARY_COLOR):
        print(f"[Fill] Seed ({seed_col}, {seed_row}) is on the boundary color. Please click inside the shape.")
        return
    if _colors_match(curr_col, CURRENT_FILL_COLOR):
        print(f"[Fill] Seed ({seed_col}, {seed_row}) is already filled.")
        return

    save_undo_state()
    IS_FILLING = True
    FILL_COUNT = 0
    FILL_QUEUE = deque([(seed_col, seed_row)])
    FILL_VISITED = {(seed_col, seed_row)}

    print(f"[Fill] Started {CURRENT_ALGORITHM} at seed ({seed_col}, {seed_row}).")

    if CURRENT_SPEED_MODE == "Instant Fill":
        # Process entire fill immediately
        while FILL_QUEUE:
            _process_fill_batch(batch_size=5000)
        IS_FILLING = False
        print(f"[Fill] Completed! Filled {FILL_COUNT} cells.")
        glut.glutPostRedisplay()
    else:
        # Animated mode: kick off timer loop
        if not FILL_TIMER_ACTIVE:
            FILL_TIMER_ACTIVE = True
            delay = 20 if "Smooth" in CURRENT_SPEED_MODE else 5
            glut.glutTimerFunc(delay, fill_timer_callback, 0)


def start_flood_fill(seed_col, seed_row):
    """Initialize flood fill algorithm from the seed cell.

    Unlike boundary fill (which stops at a known boundary color),
    flood fill replaces all connected pixels that match the OLD color
    at the seed point with the new fill color.
    """
    global IS_FILLING, FILL_QUEUE, FILL_VISITED, FILL_COUNT, FILL_TIMER_ACTIVE, FLOOD_OLD_COLOR
    num_cols, num_rows = get_grid_dimensions()

    if not (0 <= seed_col < num_cols and 0 <= seed_row < num_rows):
        return

    # Record the original color at the seed point
    FLOOD_OLD_COLOR = GRID_CELLS.get((seed_col, seed_row))

    # Cannot fill if already fill color
    if _colors_match(FLOOD_OLD_COLOR, CURRENT_FILL_COLOR):
        print(f"[Flood Fill] Seed ({seed_col}, {seed_row}) is already the fill color.")
        return

    save_undo_state()
    IS_FILLING = True
    FILL_COUNT = 0
    FILL_QUEUE = deque([(seed_col, seed_row)])
    FILL_VISITED = {(seed_col, seed_row)}

    print(f"[Flood Fill] Started {CURRENT_ALGORITHM} at seed ({seed_col}, {seed_row}). Old color: {FLOOD_OLD_COLOR}")

    if CURRENT_SPEED_MODE == "Instant Fill":
        # Process entire fill immediately
        while FILL_QUEUE:
            _process_fill_batch(batch_size=5000)
        IS_FILLING = False
        print(f"[Flood Fill] Completed! Filled {FILL_COUNT} cells.")
        glut.glutPostRedisplay()
    else:
        # Animated mode: kick off timer loop
        if not FILL_TIMER_ACTIVE:
            FILL_TIMER_ACTIVE = True
            delay = 20 if "Smooth" in CURRENT_SPEED_MODE else 5
            glut.glutTimerFunc(delay, fill_timer_callback, 0)


# ============================================================================
# Scan-Line Fill (Visible Sweeping Scan Line Engine)
# ============================================================================
#
# Both scan-line entry points (polygon ET/AET and interactive seed click)
# first compute the interior spans of every scanline, then hand them to a
# common sweep engine. In animated modes a highlighted horizontal scan line
# travels from the top row of the region to the bottom row. On each row it:
#   Phase 1: moves onto the row and marks the span intersections (x pairs)
#   Phase 2: fills the spans between those intersection pairs
# In "Instant Fill" mode all spans are filled immediately (used by headless).

def _fill_scanline_row(row, spans, fill_color, boundary_color=None):
    """Fill every horizontal span [x_left, x_right] on one scanline.

    Returns the number of cells filled on this row.
    """
    filled = 0
    for x_left, x_right in spans:
        for col in range(x_left, x_right + 1):
            if boundary_color is not None and _colors_match(GRID_CELLS.get((col, row)), boundary_color):
                continue
            GRID_CELLS[(col, row)] = fill_color
            filled += 1
    return filled


def _scanline_phase_delay():
    """Timer delay (ms) for each sweep phase depending on the speed mode."""
    return 60 if "Smooth" in CURRENT_SPEED_MODE else 18


def _stop_scanline_sweep():
    """Abort any running scan-line sweep and hide the scan line."""
    global IS_FILLING, SCANLINE_RUNNING, SCANLINE_ROWS, SCANLINE_INDEX
    global SCANLINE_ROW, SCANLINE_SPANS, SCANLINE_PENDING_FILL
    if SCANLINE_RUNNING:
        IS_FILLING = False
    SCANLINE_RUNNING = False
    SCANLINE_ROWS = []
    SCANLINE_INDEX = 0
    SCANLINE_ROW = None
    SCANLINE_SPANS = []
    SCANLINE_PENDING_FILL = False


def _run_scanline_sweep(spans_by_row, fill_color, boundary_color=None, label="Scan-Line Fill"):
    """Fill precomputed spans scanline by scanline (top to bottom).

    Parameters:
      spans_by_row: dict mapping row -> list of (x_left, x_right) spans.
      fill_color: RGB tuple for the interior fill.
      boundary_color: Optional RGB tuple; cells of this color are never overwritten.

    Returns:
      Number of cells filled (Instant mode) or 0 (animated mode; FILL_COUNT
      is updated live as the scan line sweeps).
    """
    global IS_FILLING, FILL_COUNT, SCANLINE_RUNNING, SCANLINE_ROWS, SCANLINE_INDEX
    global SCANLINE_ROW, SCANLINE_SPANS, SCANLINE_PENDING_FILL
    global SCANLINE_FILL_COLOR, SCANLINE_BOUNDARY_COLOR, SCANLINE_TIMER_ACTIVE

    _stop_scanline_sweep()
    FILL_COUNT = 0

    if not spans_by_row:
        IS_FILLING = False
        glut.glutPostRedisplay()
        return 0

    first_row, last_row = min(spans_by_row), max(spans_by_row)
    rows = [(r, sorted(spans_by_row.get(r, []))) for r in range(first_row, last_row + 1)]

    if CURRENT_SPEED_MODE == "Instant Fill":
        for r, spans in rows:
            FILL_COUNT += _fill_scanline_row(r, spans, fill_color, boundary_color)
        IS_FILLING = False
        print(f"[{label}] Completed! Filled {FILL_COUNT} cells across {len(rows)} scanlines.")
        glut.glutPostRedisplay()
        return FILL_COUNT

    # Animated sweep: place the scan line on the first row immediately
    SCANLINE_ROWS = rows
    SCANLINE_INDEX = 0
    SCANLINE_ROW, SCANLINE_SPANS = rows[0]
    SCANLINE_PENDING_FILL = True
    SCANLINE_FILL_COLOR = fill_color
    SCANLINE_BOUNDARY_COLOR = boundary_color
    SCANLINE_RUNNING = True
    IS_FILLING = True

    print(f"[{label}] Sweeping scan line from y = {first_row} to y = {last_row} ({len(rows)} scanlines).")

    if not SCANLINE_TIMER_ACTIVE:
        SCANLINE_TIMER_ACTIVE = True
        glut.glutTimerFunc(_scanline_phase_delay(), scanline_timer_callback, 0)
    glut.glutPostRedisplay()
    return 0


def scanline_timer_callback(val):
    """Timer callback that advances the visible scan line one phase at a time."""
    global IS_FILLING, FILL_COUNT, SCANLINE_INDEX, SCANLINE_ROW, SCANLINE_SPANS
    global SCANLINE_PENDING_FILL, SCANLINE_TIMER_ACTIVE

    if not SCANLINE_RUNNING:
        SCANLINE_TIMER_ACTIVE = False
        glut.glutPostRedisplay()
        return

    if SCANLINE_PENDING_FILL:
        # Phase 2: fill spans between the intersection pairs on this scanline
        FILL_COUNT += _fill_scanline_row(SCANLINE_ROW, SCANLINE_SPANS,
                                         SCANLINE_FILL_COLOR, SCANLINE_BOUNDARY_COLOR)
        SCANLINE_PENDING_FILL = False
        SCANLINE_INDEX += 1
    elif SCANLINE_INDEX < len(SCANLINE_ROWS):
        # Phase 1: advance the scan line to the next row and mark intersections
        SCANLINE_ROW, SCANLINE_SPANS = SCANLINE_ROWS[SCANLINE_INDEX]
        SCANLINE_PENDING_FILL = True
    else:
        # Sweep complete
        print(f"[Scan-Line Fill] Sweep finished! Total filled cells: {FILL_COUNT}.")
        _stop_scanline_sweep()
        IS_FILLING = False
        SCANLINE_TIMER_ACTIVE = False
        glut.glutPostRedisplay()
        return

    glut.glutPostRedisplay()
    glut.glutTimerFunc(_scanline_phase_delay(), scanline_timer_callback, 0)


def scan_line_fill_polygon(polygons, fill_color, boundary_color=None):
    """Scan-Line Polygon Fill Algorithm using Edge Table (ET) & Active Edge Table (AET).

    Parameters:
      polygons: A single list of vertices [(x0, y0), (x1, y1), ...] or
                a list of vertex lists [[(x0, y0), ...], [(hx0, hy0), ...]]
                supporting polygons with holes (interior voids).
      fill_color: RGB tuple for the interior fill.
      boundary_color: Optional RGB tuple to rasterize boundary perimeter.

    Returns:
      Number of interior cells filled (in animated modes the scan line sweeps
      visibly and FILL_COUNT is updated live; this returns 0).
    """
    global FILL_COUNT, GRID_CELLS
    num_cols, num_rows = get_grid_dimensions()

    if not polygons:
        return 0
    if isinstance(polygons[0][0], (int, float)):
        loops = [polygons]
    else:
        loops = polygons

    save_undo_state()

    # Draw boundary outlines if requested
    if boundary_color is not None:
        for loop in loops:
            n = len(loop)
            for i in range(n):
                c0, r0 = loop[i]
                c1, r1 = loop[(i + 1) % n]
                for c, r in bresenham_grid_line(int(c0), int(r0), int(c1), int(r1)):
                    if 0 <= c < num_cols and 0 <= r < num_rows:
                        GRID_CELLS[(c, r)] = boundary_color

    # Build Global Edge Table (ET)
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

            # Ignore horizontal edges
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

    if min_scanline > max_scanline:
        return 0

    # Active Edge Table (AET): collect the interior spans of every scanline
    aet = []
    spans_by_row = {}

    for scan_y in range(min_scanline, min(num_rows, max_scanline + 1)):
        # 1. Add edges from ET[scan_y] into AET
        if scan_y in edge_table:
            aet.extend(edge_table[scan_y])

        # 2. Remove edges whose y_max <= scan_y (half-open interval [y_min, y_max))
        aet = [e for e in aet if e["y_max"] > scan_y]

        # 3. Sort AET by current x coordinate
        aet.sort(key=lambda e: e["x"])

        # 4. Record spans between pairs of active edges: [x0, x1], [x2, x3], ...
        row_spans = []
        for idx in range(0, len(aet) - 1, 2):
            e_left = aet[idx]
            e_right = aet[idx + 1]

            x_left = max(0, int(math.ceil(e_left["x"])))
            x_right = min(num_cols - 1, int(math.floor(e_right["x"])))
            if x_left <= x_right:
                row_spans.append((x_left, x_right))
        spans_by_row[scan_y] = row_spans

        # 5. Advance x by 1/m for all edges remaining in AET
        for e in aet:
            e["x"] += e["inv_m"]

    # Sweep the visible scan line across the collected spans (or fill instantly)
    return _run_scanline_sweep(spans_by_row, fill_color, boundary_color, label="Scan-Line Polygon Fill")


def _collect_interior_spans(seed_col, seed_row):
    """Collect all interior horizontal spans connected to the seed cell.

    Uses scanline span coherence: each popped seed is expanded left/right to
    a maximal span [x_left, x_right] bounded by boundary (or already filled)
    cells, then the rows directly above and below are scanned for new spans.

    Returns:
      dict mapping row -> list of (x_left, x_right) spans.
    """
    num_cols, num_rows = get_grid_dimensions()

    def fillable(c, r):
        color = GRID_CELLS.get((c, r))
        return (not _colors_match(color, CURRENT_BOUNDARY_COLOR) and
                not _colors_match(color, CURRENT_FILL_COLOR))

    visited = set()
    spans_by_row = {}
    stack = [(seed_col, seed_row)]

    while stack:
        c, r = stack.pop()
        if (c, r) in visited or not fillable(c, r):
            continue

        # Expand to the maximal span on this scanline
        x_left = c
        while x_left > 0 and fillable(x_left - 1, r):
            x_left -= 1
        x_right = c
        while x_right < num_cols - 1 and fillable(x_right + 1, r):
            x_right += 1

        for x in range(x_left, x_right + 1):
            visited.add((x, r))
        spans_by_row.setdefault(r, []).append((x_left, x_right))

        # Look for new spans on the neighbouring scanlines
        for nr in (r - 1, r + 1):
            if not (0 <= nr < num_rows):
                continue
            x = x_left
            while x <= x_right:
                if (x, nr) not in visited and fillable(x, nr):
                    stack.append((x, nr))
                    while x <= x_right and fillable(x, nr):
                        x += 1
                else:
                    x += 1

    return spans_by_row


def start_scan_line_fill(seed_col, seed_row):
    """Initialize Scan-Line Fill from the seed cell on the interactive grid.

    1. Collects the interior spans [x_left, x_right] of every scanline in the
       region connected to the seed (scanline span coherence).
    2. Sweeps a visible scan line from the top row of the region to the
       bottom row, marking each row's intersections and then filling its spans.
    """
    num_cols, num_rows = get_grid_dimensions()

    if not (0 <= seed_col < num_cols and 0 <= seed_row < num_rows):
        return

    curr_col = GRID_CELLS.get((seed_col, seed_row))
    if _colors_match(curr_col, CURRENT_BOUNDARY_COLOR):
        print(f"[Scan-Line Fill] Seed ({seed_col}, {seed_row}) is on the boundary.")
        return
    if _colors_match(curr_col, CURRENT_FILL_COLOR):
        print(f"[Scan-Line Fill] Seed ({seed_col}, {seed_row}) is already filled.")
        return

    spans_by_row = _collect_interior_spans(seed_col, seed_row)
    if not spans_by_row:
        return

    save_undo_state()
    print(f"[Scan-Line Fill] Seed ({seed_col}, {seed_row}): region covers rows "
          f"{min(spans_by_row)}..{max(spans_by_row)}.")
    _run_scanline_sweep(spans_by_row, CURRENT_FILL_COLOR, None, label="Scan-Line Fill")


def _process_fill_batch(batch_size=40):
    """Process a batch of cells from the fill queue.

    Supports both Boundary Fill and Flood Fill:
    - Boundary Fill: fills pixels that are NOT the boundary color
    - Flood Fill: fills pixels that MATCH the old color at the seed point
    """
    global FILL_COUNT, IS_FILLING
    num_cols, num_rows = get_grid_dimensions()
    is_8_way = ("8-Way" in CURRENT_ALGORITHM)
    is_flood = ("Flood" in CURRENT_ALGORITHM)

    # 4-way orthogonal vs 8-way neighbors
    if is_8_way:
        neighbors = [
            (0, 1), (0, -1), (1, 0), (-1, 0),
            (1, 1), (1, -1), (-1, 1), (-1, -1)
        ]
    else:
        neighbors = [
            (0, 1), (0, -1), (1, 0), (-1, 0)
        ]

    processed = 0
    while FILL_QUEUE and processed < batch_size:
        col, row = FILL_QUEUE.popleft()
        cell_color = GRID_CELLS.get((col, row))

        # Check if cell can be filled
        if is_flood:
            # Flood fill: fill if cell matches the original old color
            can_fill = _colors_match(cell_color, FLOOD_OLD_COLOR)
        else:
            # Boundary fill: fill if not boundary and not already filled
            can_fill = (not _colors_match(cell_color, CURRENT_BOUNDARY_COLOR) and
                        not _colors_match(cell_color, CURRENT_FILL_COLOR))

        if can_fill:
            GRID_CELLS[(col, row)] = CURRENT_FILL_COLOR
            FILL_COUNT += 1
            processed += 1

            # Explore neighbors
            for dc, dr in neighbors:
                nc, nr = col + dc, row + dr
                if 0 <= nc < num_cols and 0 <= nr < num_rows:
                    if (nc, nr) not in FILL_VISITED:
                        n_color = GRID_CELLS.get((nc, nr))
                        if is_flood:
                            can_add = _colors_match(n_color, FLOOD_OLD_COLOR)
                        else:
                            can_add = (not _colors_match(n_color, CURRENT_BOUNDARY_COLOR) and
                                       not _colors_match(n_color, CURRENT_FILL_COLOR))
                        if can_add:
                            FILL_VISITED.add((nc, nr))
                            FILL_QUEUE.append((nc, nr))

    if not FILL_QUEUE:
        IS_FILLING = False


def fill_timer_callback(val):
    """Timer callback driving animated fill propagation."""
    global FILL_TIMER_ACTIVE, IS_FILLING
    if IS_FILLING and FILL_QUEUE:
        batch = 6 if "Smooth" in CURRENT_SPEED_MODE else 40
        _process_fill_batch(batch_size=batch)
        glut.glutPostRedisplay()
        delay = 20 if "Smooth" in CURRENT_SPEED_MODE else 5
        glut.glutTimerFunc(delay, fill_timer_callback, 0)
    else:
        FILL_TIMER_ACTIVE = False
        IS_FILLING = False
        print(f"[Fill] Animation finished! Total filled cells: {FILL_COUNT}.")
        glut.glutPostRedisplay()


# ============================================================================
# Mouse & Keyboard Event Handlers
# ============================================================================

def handle_canvas_press(col, row):
    """Handle click on the grid canvas depending on active mode."""
    global CURRENT_MODE, IS_DRAWING_BOUNDARY, LAST_DRAW_CELL, SEED_POINT

    if CURRENT_MODE in ("BRUSH", "DRAW"):
        if not IS_DRAWING_BOUNDARY:
            # 1st Click: Start boundary drawing with brush
            save_undo_state()
            IS_DRAWING_BOUNDARY = True
            LAST_DRAW_CELL = (col, row)
            GRID_CELLS[(col, row)] = CURRENT_BOUNDARY_COLOR
            print(f"[Brush] Started boundary at cell ({col}, {row}). Move mouse to draw. Click again to stop.")
        else:
            # 2nd Click: Stop boundary drawing & seal path
            IS_DRAWING_BOUNDARY = False
            if LAST_DRAW_CELL is not None and LAST_DRAW_CELL != (col, row):
                for c, r in bresenham_grid_line(LAST_DRAW_CELL[0], LAST_DRAW_CELL[1], col, row):
                    GRID_CELLS[(c, r)] = CURRENT_BOUNDARY_COLOR
            GRID_CELLS[(col, row)] = CURRENT_BOUNDARY_COLOR
            LAST_DRAW_CELL = None
            print("[Brush] Completed boundary shape. Click to draw another shape, or switch to Fill Mode to fill.")

    elif CURRENT_MODE == "CLICK":
        # Click a grid cell to draw / toggle
        save_undo_state()
        IS_DRAWING_BOUNDARY = False
        curr_val = GRID_CELLS.get((col, row))
        if curr_val is not None and _colors_match(curr_val, CURRENT_BOUNDARY_COLOR):
            # Erase if already colored with boundary color
            del GRID_CELLS[(col, row)]
            print(f"[Grid Click] Erased cell ({col}, {row}).")
        else:
            GRID_CELLS[(col, row)] = CURRENT_BOUNDARY_COLOR
            print(f"[Grid Click] Drew boundary cell ({col}, {row}).")

    elif CURRENT_MODE == "FILL":
        IS_DRAWING_BOUNDARY = False
        _stop_scanline_sweep()
        SEED_POINT = (col, row)
        if "Flood" in CURRENT_ALGORITHM:
            start_flood_fill(col, row)
        elif "Scan-Line" in CURRENT_ALGORITHM:
            start_scan_line_fill(col, row)
        else:
            start_boundary_fill(col, row)

    glut.glutPostRedisplay()


def mouse(button, state, x, y):
    """Handle mouse button clicks."""
    if button != glut.GLUT_LEFT_BUTTON or state != glut.GLUT_DOWN:
        return

    # Check Left Sidebar click
    if x < SIDEBAR_WIDTH:
        handle_sidebar_click(x, y)
        return

    # Click on grid canvas
    cell = mouse_to_grid(x, y)
    if cell is not None:
        handle_canvas_press(cell[0], cell[1])


def motion(x, y):
    """Handle mouse drag with button pressed."""
    global LAST_DRAW_CELL
    if CURRENT_MODE == "CLICK":
        cell = mouse_to_grid(x, y)
        if cell is not None:
            col, row = cell
            GRID_CELLS[(col, row)] = CURRENT_BOUNDARY_COLOR
            glut.glutPostRedisplay()
    elif CURRENT_MODE in ("BRUSH", "DRAW"):
        passive_motion(x, y)


def passive_motion(x, y):
    """Handle mouse hover across the canvas for drawing."""
    global LAST_DRAW_CELL
    if CURRENT_MODE in ("BRUSH", "DRAW") and IS_DRAWING_BOUNDARY:
        cell = mouse_to_grid(x, y)
        if cell is not None:
            col, row = cell
            if LAST_DRAW_CELL is not None and LAST_DRAW_CELL != (col, row):
                # Interpolate between last sampled cell and current cell
                for c, r in bresenham_grid_line(LAST_DRAW_CELL[0], LAST_DRAW_CELL[1], col, row):
                    GRID_CELLS[(c, r)] = CURRENT_BOUNDARY_COLOR
            else:
                GRID_CELLS[(col, row)] = CURRENT_BOUNDARY_COLOR
            LAST_DRAW_CELL = (col, row)
            glut.glutPostRedisplay()


def keyboard(key, x, y):
    """Handle keyboard shortcuts."""
    global CURRENT_MODE, IS_DRAWING_BOUNDARY, CURRENT_ALGORITHM, SEED_POINT

    if key == b'\x1b':  # Esc key
        if IS_DRAWING_BOUNDARY:
            IS_DRAWING_BOUNDARY = False
            undo()
            print("[Draw] Cancelled boundary drawing.")
            glut.glutPostRedisplay()
            return
        os._exit(0)

    # Undo: Ctrl+Z (b'\x1a') or 'u' / 'U'
    elif key in (b'\x1a', b'u', b'U'):
        undo()

    # Redo: Ctrl+Y (b'\x19') or 'r' / 'R'
    elif key in (b'\x19', b'r', b'R'):
        redo()

    elif key in (b'b', b'B'):  # Draw Brush
        CURRENT_MODE = "BRUSH"
        IS_DRAWING_BOUNDARY = False
        print("[Mode] Switched to Draw Brush. Click canvas to start tracing, click again to stop.")
        glut.glutPostRedisplay()

    elif key in (b'g', b'G', b'd', b'D'):  # Grid Click
        CURRENT_MODE = "CLICK"
        IS_DRAWING_BOUNDARY = False
        print("[Mode] Switched to Grid Click. Click or drag on grid cells to draw/erase.")
        glut.glutPostRedisplay()

    elif key in (b'f', b'F'):  # Fill Mode
        CURRENT_MODE = "FILL"
        IS_DRAWING_BOUNDARY = False
        print("[Mode] Switched to Fill Mode. Click inside shape to set seed and fill.")
        glut.glutPostRedisplay()

    elif key in (b'\t',):  # Tab cycles all 4 algorithms
        if CURRENT_ALGORITHM in ALGORITHM_LIST:
            idx = (ALGORITHM_LIST.index(CURRENT_ALGORITHM) + 1) % len(ALGORITHM_LIST)
            CURRENT_ALGORITHM = ALGORITHM_LIST[idx]
        else:
            CURRENT_ALGORITHM = ALGORITHM_LIST[0]
        print(f"[Algorithm] Active: {CURRENT_ALGORITHM}")
        glut.glutPostRedisplay()

    elif key == b'1':  # 4-Way Boundary Fill
        CURRENT_ALGORITHM = "4-Way Boundary Fill"
        print("[Algorithm] Selected: 4-Way Boundary Fill")
        glut.glutPostRedisplay()

    elif key == b'2':  # 8-Way Boundary Fill
        CURRENT_ALGORITHM = "8-Way Boundary Fill"
        print("[Algorithm] Selected: 8-Way Boundary Fill")
        glut.glutPostRedisplay()

    elif key == b'3':  # 4-Way Flood Fill
        CURRENT_ALGORITHM = "4-Way Flood Fill"
        print("[Algorithm] Selected: 4-Way Flood Fill")
        glut.glutPostRedisplay()

    elif key in (b'5', b's', b'S'):  # Scan-Line Fill
        CURRENT_ALGORITHM = "Scan-Line Fill"
        print("[Algorithm] Selected: Scan-Line Fill")
        glut.glutPostRedisplay()

    elif key == b'4':  # Toggle or select 4-way
        if CURRENT_ALGORITHM == "4-Way Boundary Fill":
            CURRENT_ALGORITHM = "4-Way Flood Fill"
        else:
            CURRENT_ALGORITHM = "4-Way Boundary Fill"
        print(f"[Algorithm] Selected: {CURRENT_ALGORITHM}")
        glut.glutPostRedisplay()

    elif key == b'8':  # Toggle or select 8-way
        if CURRENT_ALGORITHM == "8-Way Boundary Fill":
            CURRENT_ALGORITHM = "8-Way Flood Fill"
        else:
            CURRENT_ALGORITHM = "8-Way Boundary Fill"
        print(f"[Algorithm] Selected: {CURRENT_ALGORITHM}")
        glut.glutPostRedisplay()

    elif key in (b'c', b'C'):  # Clear Grid
        clear_grid()

    elif key in (b'p', b'P'):  # Save screenshot
        save_screenshot()


def clear_grid():
    """Clear all grid cells and reset seed point."""
    global GRID_CELLS, SEED_POINT, IS_FILLING, FILL_QUEUE, IS_DRAWING_BOUNDARY
    if GRID_CELLS:
        save_undo_state()
    GRID_CELLS.clear()
    SEED_POINT = None
    _stop_scanline_sweep()
    IS_FILLING = False
    FILL_QUEUE.clear()
    IS_DRAWING_BOUNDARY = False
    print("[Grid] Cleared all cells.")
    glut.glutPostRedisplay()


# ============================================================================
# Left Sidebar Interaction
# ============================================================================

def handle_sidebar_click(x, y):
    """Handle clicks inside the left controls panel."""
    global CURRENT_ALGORITHM, CURRENT_MODE, IS_DRAWING_BOUNDARY
    global CURRENT_BOUNDARY_COLOR, CURRENT_BOUNDARY_COLOR_NAME
    global CURRENT_FILL_COLOR, CURRENT_FILL_COLOR_NAME

    # Section 1: Algorithms (y: 72 to 198)
    if 14 <= x <= 236:
        if 72 <= y <= 94:
            CURRENT_ALGORITHM = "4-Way Boundary Fill"
            print("[Algorithm] Active: 4-Way Boundary Fill")
            glut.glutPostRedisplay()
            return
        elif 98 <= y <= 120:
            CURRENT_ALGORITHM = "8-Way Boundary Fill"
            print("[Algorithm] Active: 8-Way Boundary Fill")
            glut.glutPostRedisplay()
            return
        elif 124 <= y <= 146:
            CURRENT_ALGORITHM = "4-Way Flood Fill"
            print("[Algorithm] Active: 4-Way Flood Fill")
            glut.glutPostRedisplay()
            return
        elif 150 <= y <= 172:
            CURRENT_ALGORITHM = "8-Way Flood Fill"
            print("[Algorithm] Active: 8-Way Flood Fill")
            glut.glutPostRedisplay()
            return
        elif 176 <= y <= 198:
            CURRENT_ALGORITHM = "Scan-Line Fill"
            print("[Algorithm] Active: Scan-Line Fill")
            glut.glutPostRedisplay()
            return

    # Section 2: Tools / Modes (y: 224 to 304)
    if 14 <= x <= 236:
        if 224 <= y <= 248:
            CURRENT_MODE = "BRUSH"
            IS_DRAWING_BOUNDARY = False
            print("[Mode] Draw Brush activated. Click canvas to start tracing, click again to stop.")
            glut.glutPostRedisplay()
            return
        elif 252 <= y <= 276:
            CURRENT_MODE = "CLICK"
            IS_DRAWING_BOUNDARY = False
            print("[Mode] Grid Click activated. Click on grid cells to draw/erase.")
            glut.glutPostRedisplay()
            return
        elif 280 <= y <= 304:
            CURRENT_MODE = "FILL"
            IS_DRAWING_BOUNDARY = False
            print("[Mode] Fill Mode activated. Click inside boundary to fill.")
            glut.glutPostRedisplay()
            return

    # Section 3: Boundary Colors (5 swatches at y: 332 to 356)
    if 332 <= y <= 356:
        boundary_keys = list(BOUNDARY_COLORS.keys())
        for i, name in enumerate(boundary_keys):
            bx1 = 14 + i * 45
            bx2 = bx1 + 38
            if bx1 <= x <= bx2:
                CURRENT_BOUNDARY_COLOR_NAME = name
                CURRENT_BOUNDARY_COLOR = BOUNDARY_COLORS[name]
                print(f"[Color] Boundary Color set to: {name}")
                glut.glutPostRedisplay()
                return

    # Section 4: Fill Colors (5 swatches at y: 400 to 424)
    if 400 <= y <= 424:
        fill_keys = list(FILL_COLORS.keys())
        for i, name in enumerate(fill_keys):
            bx1 = 14 + i * 45
            bx2 = bx1 + 38
            if bx1 <= x <= bx2:
                CURRENT_FILL_COLOR_NAME = name
                CURRENT_FILL_COLOR = FILL_COLORS[name]
                print(f"[Color] Fill Color set to: {name}")
                glut.glutPostRedisplay()
                return

    # Section 5: Actions (y: 468 to 568)
    if 14 <= x <= 236:
        if 468 <= y <= 490:
            undo()
            return
        elif 494 <= y <= 516:
            clear_grid()
            return
        elif 520 <= y <= 542:
            save_screenshot()
            return
        elif 546 <= y <= 568:
            clear_grid()
            CURRENT_ALGORITHM = "4-Way Boundary Fill"
            CURRENT_BOUNDARY_COLOR_NAME = "Black"
            CURRENT_BOUNDARY_COLOR = BOUNDARY_COLORS["Black"]
            CURRENT_FILL_COLOR_NAME = "Red"
            CURRENT_FILL_COLOR = FILL_COLORS["Red"]
            CURRENT_SPEED_MODE = "Smooth (Animated)"
            CURRENT_MODE = "BRUSH"
            print("[Reset] Reset settings to default.")
            glut.glutPostRedisplay()
            return


# Backward compatibility alias for test suite
def handle_ribbon_click(x, y):
    """Backward compatibility alias for tests."""
    handle_sidebar_click(x, y)


# ============================================================================
# Rendering: Graph-Paper Grid & Colored Cells
# ============================================================================

def draw_grid_canvas():
    """Draw the graph paper background, light blue grid lines, and colored cells."""
    num_cols, num_rows = get_grid_dimensions()

    # 1. Clean Canvas Background
    gl.glColor4f(*CANVAS_BG_COLOR)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(SIDEBAR_WIDTH, 0)
    gl.glVertex2f(CURRENT_WIDTH, 0)
    gl.glVertex2f(CURRENT_WIDTH, CURRENT_HEIGHT)
    gl.glVertex2f(SIDEBAR_WIDTH, CURRENT_HEIGHT)
    gl.glEnd()

    # 2. Render Filled and Boundary Grid Cells
    for (c, r), col_rgb in GRID_CELLS.items():
        if 0 <= c < num_cols and 0 <= r < num_rows:
            x1, y1, x2, y2 = grid_to_screen_rect(c, r)
            gl.glColor3f(*col_rgb)
            gl.glBegin(gl.GL_QUADS)
            gl.glVertex2f(x1, y1)
            gl.glVertex2f(x2, y1)
            gl.glVertex2f(x2, y2)
            gl.glVertex2f(x1, y2)
            gl.glEnd()

    # 3. Seed Point Indicator (High-Contrast Indicator for Fill Mode)
    if SEED_POINT is not None:
        sc, sr = SEED_POINT
        if 0 <= sc < num_cols and 0 <= sr < num_rows:
            x1, y1, x2, y2 = grid_to_screen_rect(sc, sr)
            cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            gl.glEnable(gl.GL_BLEND)
            gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

            # Outer dark contrast ring
            gl.glColor4f(0.10, 0.12, 0.18, 0.85)
            gl.glLineWidth(3.0)
            gl.glBegin(gl.GL_LINE_LOOP)
            for i in range(16):
                th = 2.0 * math.pi * i / 16.0
                gl.glVertex2f(cx + 6.8 * math.cos(th), cy + 6.8 * math.sin(th))
            gl.glEnd()

            # Inner bright golden seed ring
            gl.glColor4f(1.0, 0.90, 0.15, 1.0)
            gl.glLineWidth(2.0)
            gl.glBegin(gl.GL_LINE_LOOP)
            for i in range(16):
                th = 2.0 * math.pi * i / 16.0
                gl.glVertex2f(cx + 6.0 * math.cos(th), cy + 6.0 * math.sin(th))
            gl.glEnd()

            # Center white seed pip
            gl.glColor4f(1.0, 1.0, 1.0, 1.0)
            gl.glBegin(gl.GL_POLYGON)
            for i in range(12):
                th = 2.0 * math.pi * i / 12.0
                gl.glVertex2f(cx + 2.5 * math.cos(th), cy + 2.5 * math.sin(th))
            gl.glEnd()

            gl.glDisable(gl.GL_BLEND)

    # 4. Light-Blue Graph-Paper Grid Lines (Matching Reference Photo)
    gl.glColor3f(*GRID_LINE_COLOR)
    gl.glLineWidth(1.0)
    gl.glBegin(gl.GL_LINES)

    # Vertical grid lines
    for c in range(num_cols + 1):
        x = SIDEBAR_WIDTH + c * CELL_SIZE
        gl.glVertex2f(x, 0)
        gl.glVertex2f(x, CURRENT_HEIGHT)

    # Horizontal grid lines
    for r in range(num_rows + 1):
        y = r * CELL_SIZE
        gl.glVertex2f(SIDEBAR_WIDTH, y)
        gl.glVertex2f(CURRENT_WIDTH, y)

    gl.glEnd()

    # 5. Sweeping scan line overlay (drawn on top of everything on the canvas)
    draw_scanline_overlay()


def _draw_quad(x1, y1, x2, y2):
    """Draw a filled axis-aligned rectangle using the current color."""
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(x1, y1)
    gl.glVertex2f(x2, y1)
    gl.glVertex2f(x2, y2)
    gl.glVertex2f(x1, y2)
    gl.glEnd()


def _draw_disc(cx, cy, radius, rgba, segments=16):
    """Draw a filled circle centred at (cx, cy)."""
    gl.glColor4f(*rgba)
    gl.glBegin(gl.GL_POLYGON)
    for i in range(segments):
        th = 2.0 * math.pi * i / segments
        gl.glVertex2f(cx + radius * math.cos(th), cy + radius * math.sin(th))
    gl.glEnd()


def draw_scanline_overlay():
    """Render the visible scan line while a Scan-Line Fill sweep is running.

    - Translucent highlight band across the whole current row
    - Ghost preview of the spans about to be filled (phase 1)
    - Bright scan line through the row centre with a dark halo
    - Intersection markers at both ends of every interior span
    - A 'y = N' tag showing the current scanline index
    """
    if SCANLINE_ROW is None:
        return
    num_cols, num_rows = get_grid_dimensions()
    if not (0 <= SCANLINE_ROW < num_rows):
        return

    x_start = SIDEBAR_WIDTH
    x_end = SIDEBAR_WIDTH + num_cols * CELL_SIZE
    y1 = SCANLINE_ROW * CELL_SIZE
    y2 = y1 + CELL_SIZE
    cy = (y1 + y2) / 2.0
    sr, sg, sb = SCANLINE_COLOR

    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    # 1. Highlight band across the row
    gl.glColor4f(sr, sg, sb, 0.12)
    _draw_quad(x_start, y1, x_end, y2)

    # 2. Ghost preview of spans that will be filled on the next phase
    if SCANLINE_PENDING_FILL and SCANLINE_FILL_COLOR is not None:
        fr, fg, fb = SCANLINE_FILL_COLOR
        gl.glColor4f(fr, fg, fb, 0.40)
        for x_left, x_right in SCANLINE_SPANS:
            _draw_quad(SIDEBAR_WIDTH + x_left * CELL_SIZE, y1 + 3,
                       SIDEBAR_WIDTH + (x_right + 1) * CELL_SIZE, y2 - 3)

    # 3. Thin band edges
    gl.glColor4f(sr, sg, sb, 0.55)
    gl.glLineWidth(1.0)
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(x_start, y1); gl.glVertex2f(x_end, y1)
    gl.glVertex2f(x_start, y2); gl.glVertex2f(x_end, y2)
    gl.glEnd()

    # 4. The scan line itself: dark halo + bright core
    gl.glColor4f(0.10, 0.04, 0.12, 0.55)
    gl.glLineWidth(4.5)
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(x_start, cy); gl.glVertex2f(x_end, cy)
    gl.glEnd()
    gl.glColor4f(sr, sg, sb, 1.0)
    gl.glLineWidth(2.0)
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(x_start, cy); gl.glVertex2f(x_end, cy)
    gl.glEnd()

    # 5. Intersection markers at both ends of every interior span
    for x_left, x_right in SCANLINE_SPANS:
        for ix in (SIDEBAR_WIDTH + x_left * CELL_SIZE, SIDEBAR_WIDTH + (x_right + 1) * CELL_SIZE):
            _draw_disc(ix, cy, 5.5, (0.10, 0.04, 0.12, 0.90))
            _draw_disc(ix, cy, 4.0, (sr, sg, sb, 1.0))
            _draw_disc(ix, cy, 1.8, (1.0, 1.0, 1.0, 1.0))

    # 6. 'y = N' tag at the right end of the scan line
    tag_w, tag_h = 54, 16
    tx2 = x_end - 6
    tx1 = tx2 - tag_w
    ty1 = y1 - tag_h - 3 if y1 - tag_h - 3 >= 0 else y2 + 3
    ty2 = ty1 + tag_h
    gl.glColor4f(0.10, 0.04, 0.12, 0.90)
    _draw_quad(tx1, ty1, tx2, ty2)
    gl.glColor4f(sr, sg, sb, 1.0)
    gl.glLineWidth(1.2)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(tx1, ty1); gl.glVertex2f(tx2, ty1)
    gl.glVertex2f(tx2, ty2); gl.glVertex2f(tx1, ty2)
    gl.glEnd()

    gl.glDisable(gl.GL_BLEND)
    draw_bitmap_string(tx1 + 9, ty1 + 12, f"y = {SCANLINE_ROW}",
                       font=glut.GLUT_BITMAP_HELVETICA_10, color=(1.0, 1.0, 1.0))


# ============================================================================
# Rendering: Left Control Sidebar
# ============================================================================

def draw_bitmap_string(x, y, text, font=glut.GLUT_BITMAP_HELVETICA_12, color=SIDEBAR_TEXT_PRIMARY):
    """Render 2D bitmap text at (x, y)."""
    gl.glColor3f(*color)
    gl.glRasterPos2f(x, y)
    for ch in text:
        glut.glutBitmapCharacter(font, ord(ch))


def draw_sidebar():
    """Render the complete left sidebar with all controls organized vertically."""
    # 1. Sidebar Background
    gl.glColor3f(*SIDEBAR_BG_COLOR)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(0, 0)
    gl.glVertex2f(SIDEBAR_WIDTH, 0)
    gl.glVertex2f(SIDEBAR_WIDTH, CURRENT_HEIGHT)
    gl.glVertex2f(0, CURRENT_HEIGHT)
    gl.glEnd()

    # 2. Right Vertical Divider Border
    gl.glColor3f(*SIDEBAR_BORDER_COLOR)
    gl.glLineWidth(1.5)
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(SIDEBAR_WIDTH - 1, 0)
    gl.glVertex2f(SIDEBAR_WIDTH - 1, CURRENT_HEIGHT)
    gl.glEnd()

    # 3. Header / Branding
    draw_bitmap_string(16, 26, "FILLING ALGORITHMS", font=glut.GLUT_BITMAP_HELVETICA_12, color=(1.0, 1.0, 1.0))
    draw_bitmap_string(16, 42, "CG Lab Studio - 2D Grid Engine", font=glut.GLUT_BITMAP_HELVETICA_10, color=SIDEBAR_ACCENT)

    _draw_h_divider(52)

    # 4. Section 1: ALGORITHMS
    draw_bitmap_string(16, 64, "ALGORITHM", font=glut.GLUT_BITMAP_HELVETICA_10, color=SIDEBAR_TEXT_MUTED)

    algo_items = [
        ("4-Way Boundary Fill", "4-Way Boundary Fill", False),
        ("8-Way Boundary Fill", "8-Way Boundary Fill", False),
        ("4-Way Flood Fill", "4-Way Flood Fill", False),
        ("8-Way Flood Fill", "8-Way Flood Fill", False),
        ("Scan-Line Fill", "Scan-Line Fill", False),
    ]

    for idx, (label, name, is_upcoming) in enumerate(algo_items):
        by1 = 72 + idx * 26
        by2 = by1 + 22
        is_active = (CURRENT_ALGORITHM == label)

        # Background quad
        if is_active:
            gl.glColor3f(0.14, 0.38, 0.62)
        elif is_upcoming:
            gl.glColor3f(0.08, 0.09, 0.12)
        else:
            gl.glColor3f(0.09, 0.11, 0.15)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(14, by1); gl.glVertex2f(236, by1)
        gl.glVertex2f(236, by2); gl.glVertex2f(14, by2)
        gl.glEnd()

        # Border
        gl.glColor3f(*(SIDEBAR_ACCENT if is_active else (0.16, 0.20, 0.28)))
        gl.glLineWidth(1.5 if is_active else 1.0)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(14, by1); gl.glVertex2f(236, by1)
        gl.glVertex2f(236, by2); gl.glVertex2f(14, by2)
        gl.glEnd()

        bullet = "[*] " if is_active else ("- " if is_upcoming else "o ")
        text_col = (1.0, 1.0, 1.0) if is_active else ((0.45, 0.50, 0.58) if is_upcoming else (0.80, 0.84, 0.90))
        draw_bitmap_string(22, by1 + 16, f"{bullet}{label}", font=glut.GLUT_BITMAP_HELVETICA_10, color=text_col)

    _draw_h_divider(204)

    # 5. Section 2: DRAW & FILL TOOLS
    draw_bitmap_string(16, 216, "DRAW & FILL TOOLS", font=glut.GLUT_BITMAP_HELVETICA_10, color=SIDEBAR_TEXT_MUTED)

    tool_items = [
        ("Draw Brush (B)", "BRUSH"),
        ("Grid Click (G)", "CLICK"),
        ("Fill Mode (F)", "FILL"),
    ]

    for idx, (label, mode_code) in enumerate(tool_items):
        by1 = 224 + idx * 28
        by2 = by1 + 24
        is_active = (CURRENT_MODE == mode_code or (mode_code == "BRUSH" and CURRENT_MODE == "DRAW"))

        if is_active:
            gl.glColor3f(0.14, 0.40, 0.65)
        else:
            gl.glColor3f(0.09, 0.11, 0.15)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(14, by1); gl.glVertex2f(236, by1)
        gl.glVertex2f(236, by2); gl.glVertex2f(14, by2)
        gl.glEnd()

        gl.glColor3f(*((0.0, 0.85, 1.0) if is_active else (0.16, 0.20, 0.28)))
        gl.glLineWidth(1.5 if is_active else 1.0)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(14, by1); gl.glVertex2f(236, by1)
        gl.glVertex2f(236, by2); gl.glVertex2f(14, by2)
        gl.glEnd()

        bullet = "[*] " if is_active else "  "
        text_col = (1.0, 1.0, 1.0) if is_active else (0.78, 0.82, 0.88)
        draw_bitmap_string(22, by1 + 17, f"{bullet}{label}", font=glut.GLUT_BITMAP_HELVETICA_12, color=text_col)

    _draw_h_divider(312)

    # 6. Section 3: BOUNDARY COLOR (5 Colors)
    draw_bitmap_string(16, 324, "BOUNDARY COLOR", font=glut.GLUT_BITMAP_HELVETICA_10, color=SIDEBAR_TEXT_MUTED)

    for i, (name, col_rgb) in enumerate(BOUNDARY_COLORS.items()):
        bx1 = 14 + i * 45
        bx2 = bx1 + 38
        by1 = 332
        by2 = by1 + 24
        is_sel = (CURRENT_BOUNDARY_COLOR_NAME == name)

        gl.glColor3f(*col_rgb)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(bx1, by1); gl.glVertex2f(bx2, by1)
        gl.glVertex2f(bx2, by2); gl.glVertex2f(bx1, by2)
        gl.glEnd()

        gl.glColor3f(*(SIDEBAR_ACCENT if is_sel else (0.35, 0.40, 0.50)))
        gl.glLineWidth(2.2 if is_sel else 1.0)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(bx1, by1); gl.glVertex2f(bx2, by1)
        gl.glVertex2f(bx2, by2); gl.glVertex2f(bx1, by2)
        gl.glEnd()

        if is_sel:
            gl.glColor3f(1.0, 1.0, 1.0)
            gl.glLineWidth(2.0)
            gl.glBegin(gl.GL_LINE_LOOP)
            gl.glVertex2f(bx1 + 2, by1 + 2); gl.glVertex2f(bx2 - 2, by1 + 2)
            gl.glVertex2f(bx2 - 2, by2 - 2); gl.glVertex2f(bx1 + 2, by2 - 2)
            gl.glEnd()

    draw_bitmap_string(16, 372, f"Selected: {CURRENT_BOUNDARY_COLOR_NAME}", font=glut.GLUT_BITMAP_HELVETICA_10, color=SIDEBAR_TEXT_PRIMARY)

    _draw_h_divider(380)

    # 7. Section 4: FILL COLOR (5 Colors)
    draw_bitmap_string(16, 392, "FILL COLOR", font=glut.GLUT_BITMAP_HELVETICA_10, color=SIDEBAR_TEXT_MUTED)

    for i, (name, col_rgb) in enumerate(FILL_COLORS.items()):
        bx1 = 14 + i * 45
        bx2 = bx1 + 38
        by1 = 400
        by2 = by1 + 24
        is_sel = (CURRENT_FILL_COLOR_NAME == name)

        gl.glColor3f(*col_rgb)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(bx1, by1); gl.glVertex2f(bx2, by1)
        gl.glVertex2f(bx2, by2); gl.glVertex2f(bx1, by2)
        gl.glEnd()

        gl.glColor3f(*(SIDEBAR_ACCENT if is_sel else (0.35, 0.40, 0.50)))
        gl.glLineWidth(2.2 if is_sel else 1.0)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(bx1, by1); gl.glVertex2f(bx2, by1)
        gl.glVertex2f(bx2, by2); gl.glVertex2f(bx1, by2)
        gl.glEnd()

        if is_sel:
            gl.glColor3f(1.0, 1.0, 1.0)
            gl.glLineWidth(2.0)
            gl.glBegin(gl.GL_LINE_LOOP)
            gl.glVertex2f(bx1 + 2, by1 + 2); gl.glVertex2f(bx2 - 2, by1 + 2)
            gl.glVertex2f(bx2 - 2, by2 - 2); gl.glVertex2f(bx1 + 2, by2 - 2)
            gl.glEnd()

    draw_bitmap_string(16, 440, f"Selected: {CURRENT_FILL_COLOR_NAME}", font=glut.GLUT_BITMAP_HELVETICA_10, color=SIDEBAR_TEXT_PRIMARY)

    _draw_h_divider(448)

    # 8. Section 5: ACTIONS
    draw_bitmap_string(16, 460, "ACTIONS", font=glut.GLUT_BITMAP_HELVETICA_10, color=SIDEBAR_TEXT_MUTED)

    # Undo Button
    can_undo = len(UNDO_STACK) > 0
    if can_undo:
        gl.glColor3f(0.12, 0.24, 0.38)
    else:
        gl.glColor3f(0.09, 0.12, 0.16)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(14, 468); gl.glVertex2f(236, 468)
    gl.glVertex2f(236, 490); gl.glVertex2f(14, 490)
    gl.glEnd()

    if can_undo:
        gl.glColor3f(0.25, 0.55, 0.85)
    else:
        gl.glColor3f(0.16, 0.20, 0.26)
    gl.glLineWidth(1.0)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(14, 468); gl.glVertex2f(236, 468)
    gl.glVertex2f(236, 490); gl.glVertex2f(14, 490)
    gl.glEnd()

    undo_label = f"Undo (Ctrl+Z / U) [{len(UNDO_STACK)}]" if can_undo else "Undo (Ctrl+Z / U)"
    text_color = (0.85, 0.94, 1.0) if can_undo else (0.42, 0.48, 0.56)
    draw_bitmap_string(52 if can_undo else 66, 483, undo_label, font=glut.GLUT_BITMAP_HELVETICA_10, color=text_color)

    # Clear Grid Button (Red highlight)
    gl.glColor3f(0.28, 0.12, 0.15)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(14, 494); gl.glVertex2f(236, 494)
    gl.glVertex2f(236, 516); gl.glVertex2f(14, 516)
    gl.glEnd()
    gl.glColor3f(0.65, 0.25, 0.30)
    gl.glLineWidth(1.0)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(14, 494); gl.glVertex2f(236, 494)
    gl.glVertex2f(236, 516); gl.glVertex2f(14, 516)
    gl.glEnd()
    draw_bitmap_string(70, 509, "Clear Canvas (C)", font=glut.GLUT_BITMAP_HELVETICA_10, color=(1.0, 0.80, 0.80))

    # Save Screenshot Button
    gl.glColor3f(0.12, 0.18, 0.26)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(14, 520); gl.glVertex2f(236, 520)
    gl.glVertex2f(236, 542); gl.glVertex2f(14, 542)
    gl.glEnd()
    gl.glColor3f(0.25, 0.35, 0.50)
    gl.glLineWidth(1.0)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(14, 520); gl.glVertex2f(236, 520)
    gl.glVertex2f(236, 542); gl.glVertex2f(14, 542)
    gl.glEnd()
    draw_bitmap_string(62, 535, "Save Screenshot (P)", font=glut.GLUT_BITMAP_HELVETICA_10, color=(0.85, 0.90, 0.96))

    # Reset Defaults Button
    gl.glColor3f(0.10, 0.12, 0.16)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(14, 546); gl.glVertex2f(236, 546)
    gl.glVertex2f(236, 568); gl.glVertex2f(14, 568)
    gl.glEnd()
    gl.glColor3f(0.20, 0.25, 0.35)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(14, 546); gl.glVertex2f(236, 546)
    gl.glVertex2f(236, 568); gl.glVertex2f(14, 568)
    gl.glEnd()
    draw_bitmap_string(78, 561, "Reset Defaults", font=glut.GLUT_BITMAP_HELVETICA_10, color=(0.75, 0.80, 0.88))

    _draw_h_divider(576)

    # 9. Section 6: Live Status & Guide Card
    gl.glColor3f(0.08, 0.11, 0.16)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(14, 584); gl.glVertex2f(236, 584)
    gl.glVertex2f(236, 670); gl.glVertex2f(14, 670)
    gl.glEnd()
    gl.glColor3f(0.20, 0.26, 0.36)
    gl.glLineWidth(1.0)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(14, 584); gl.glVertex2f(236, 584)
    gl.glVertex2f(236, 670); gl.glVertex2f(14, 670)
    gl.glEnd()

    draw_bitmap_string(22, 598, "STATUS & GUIDE", font=glut.GLUT_BITMAP_HELVETICA_10, color=SIDEBAR_ACCENT)

    if IS_FILLING and SCANLINE_ROW is not None:
        status_msg = f"Scan line sweeping: y = {SCANLINE_ROW}"
        if SCANLINE_SPANS:
            span_txt = " ".join(f"[{a},{b}]" for a, b in SCANLINE_SPANS[:3])
            if len(SCANLINE_SPANS) > 3:
                span_txt += " ..."
            hint_msg = f"Spans: {span_txt}"
        else:
            hint_msg = "Spans: none on this row"
    elif IS_FILLING:
        status_msg = f"Filling: {FILL_COUNT} cells..."
        hint_msg = "Please wait for fill..."
    elif CURRENT_MODE in ("BRUSH", "DRAW"):
        if IS_DRAWING_BOUNDARY:
            status_msg = "Brush: Tracing boundary"
            hint_msg = "Click canvas again to stop"
        else:
            status_msg = "Brush: Ready to trace"
            hint_msg = "Click 1 start, Click 2 stop"
    elif CURRENT_MODE == "CLICK":
        status_msg = "Grid Click: Direct draw"
        hint_msg = "Click to draw/erase cell"
    else:  # FILL
        status_msg = f"Fill: {CURRENT_ALGORITHM}"
        hint_msg = "Click inside shape to fill"

    draw_bitmap_string(22, 618, status_msg, font=glut.GLUT_BITMAP_HELVETICA_10, color=(1.0, 1.0, 1.0))
    draw_bitmap_string(22, 636, f"Filled Cells: {FILL_COUNT}", font=glut.GLUT_BITMAP_HELVETICA_10, color=(0.85, 0.88, 0.94))
    draw_bitmap_string(22, 654, hint_msg, font=glut.GLUT_BITMAP_HELVETICA_10, color=SIDEBAR_TEXT_MUTED)


def _draw_h_divider(y):
    """Draw a subtle horizontal divider line in the sidebar."""
    gl.glColor3f(*SIDEBAR_BORDER_COLOR)
    gl.glLineWidth(1.0)
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(14, y)
    gl.glVertex2f(236, y)
    gl.glEnd()


# ============================================================================
# Main Display & Setup
# ============================================================================

def display():
    """Main rendering loop."""
    gl.glClearColor(*CANVAS_BG_COLOR)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)

    # 2D Orthographic Projection in screen pixel coordinates
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    glu.gluOrtho2D(0, CURRENT_WIDTH, CURRENT_HEIGHT, 0)

    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()

    # Draw canvas first on the right, then sidebar on the left
    draw_grid_canvas()
    draw_sidebar()

    glut.glutSwapBuffers()


def reshape(width, height):
    """Handle window resizing."""
    global CURRENT_WIDTH, CURRENT_HEIGHT
    CURRENT_WIDTH = max(1, width)
    CURRENT_HEIGHT = max(1, height)
    gl.glViewport(0, 0, CURRENT_WIDTH, CURRENT_HEIGHT)
    glut.glutPostRedisplay()


def save_screenshot():
    """Save high-resolution PNG screenshot to output/ directory."""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"filling_algo_{timestamp}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)

    w, h = CURRENT_WIDTH, CURRENT_HEIGHT
    gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
    raw = gl.glReadPixels(0, 0, w, h, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)

    # Invert rows (OpenGL origin is bottom-left, PNG is top-left)
    rows = [raw[i * w * 3:(i + 1) * w * 3] for i in range(h)]
    rows.reverse()
    raw_flipped = b"".join(rows)

    def _chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    raw_lines = b"".join(b"\x00" + raw_flipped[i * w * 3:(i + 1) * w * 3] for i in range(h))
    png += _chunk(b"IDAT", zlib.compress(raw_lines, 9))
    png += _chunk(b"IEND", b"")

    try:
        with open(filepath, "wb") as f:
            f.write(png)
        print(f"[Screenshot] Saved image to: {filepath}")
    except Exception as e:
        print(f"[Error] Failed to save screenshot: {e}")


def run():
    """Initialize and run the Filling Algorithms window."""
    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_DOUBLE | glut.GLUT_RGB)
    glut.glutInitWindowSize(CURRENT_WIDTH, CURRENT_HEIGHT)
    glut.glutInitWindowPosition(120, 100)
    glut.glutCreateWindow("Filling Algorithms - Boundary Fill & Flood Fill")

    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    glut.glutDisplayFunc(display)
    glut.glutReshapeFunc(reshape)
    glut.glutMouseFunc(mouse)
    glut.glutMotionFunc(motion)
    glut.glutPassiveMotionFunc(passive_motion)
    glut.glutKeyboardFunc(keyboard)

    print("=== Filling Algorithms Application Window ===")
    print("Controls Panel: Left Sidebar")
    print("Mode: Draw Brush (Click 1 starts, Click 2 finishes)")
    print("Press 'G' for Grid Click, 'F' for Fill Mode")
    print("Press 'P' to save screenshot to output/")
    print("Press 'Esc' to exit.")

    glut.glutMainLoop()


if __name__ == "__main__":
    run()
