import os
import sys
import math
import struct
import zlib
import OpenGL.GL as gl     #type:ignore
import OpenGL.GLUT as glut #type:ignore
import OpenGL.GLU as glu   #type:ignore

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUTPUT_DIR = os.path.join(REPO_ROOT, "SymmetricDDA", "outputs")

# ── Canvas & grid ─────────────────────────────────────────────────────────────
CANVAS_W, CANVAS_H = 760, 620
CELL      = 34          # pixels per grid cell
MARGIN    = 40          # border margin in pixels
GRID_COLS = 20
GRID_ROWS = 16

# ── Clean, readable color scheme ──────────────────────────────────────────────
BG_COLOR      = (255, 255, 255)   # White
GRID_COLOR    = (235, 235, 235)   # Light gray
AXIS_COLOR    = (40, 40, 40)      # Dark gray
AXIS_LBL      = (90, 90, 90)      # Gray text
STAIR_COLOR   = (0, 0, 0)         # Black connector

def _generate_colors(n):
    """Generate n visually distinct colors using HSL with fixed S=0.75, L=0.45."""
    import colorsys
    colors = []
    for i in range(n):
        hue = i / max(n, 1)
        r, g, b = colorsys.hls_to_rgb(hue, 0.45, 0.75)
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors

POINT_COLORS = [(0, 0, 0)]
LABEL_COLOR   = (20, 20, 20)
POINT_RADIUS  = 5

# ── Test cases ─────────────────────────────────────────────────────────────────
TEST_CASES = [
    {"x1":  2, "y1":  2, "x2": 18, "y2": 10,
     "label": "Test Case 1 — Positive Slope", "file": "tc1_positive_slope.png"},
    {"x1":  2, "y1": 14, "x2": 18, "y2":  5,
     "label": "Test Case 2 — Negative Slope", "file": "tc2_negative_slope.png"},
    {"x1": 2, "y1":  8, "x2": 18, "y2": 8,
     "label": "Test Case 3 — Horizontal Line",  "file": "tc3_horizontal_line.png"}
]

# Track which windows have already been saved
saved_windows = set()


# ───────────────────────────────────────────────────────────────────────────
# Minimal PNG writer
# ───────────────────────────────────────────────────────────────────────────
def _write_png(filepath, width, height, rgb_rows):
    """
    Write an RGB PNG from a list of rows (top-to-bottom).
    Each row is a bytes/bytearray of length width*3.
    Uses only stdlib struct + zlib.
    """
    def _chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = _chunk(b'IHDR', ihdr_data)

    raw = b''
    for row in rgb_rows:
        raw += b'\x00' + bytes(row)  # filter byte 0 (None) per row
    idat = _chunk(b'IDAT', zlib.compress(raw, 9))
    iend = _chunk(b'IEND', b'')

    with open(filepath, 'wb') as f:
        f.write(sig + ihdr + idat + iend)


def save_framebuffer(filepath, width, height):
    """
    Read the OpenGL framebuffer and save as PNG.
    """
    gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
    data = gl.glReadPixels(0, 0, width, height, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
    # glReadPixels returns bottom-to-top; flip vertically for PNG (top-to-bottom)
    row_size = width * 3
    if isinstance(data, bytes):
        raw = data
    else:
        raw = bytes(data)
    rows = []
    for y in range(height - 1, -1, -1):
        start = y * row_size
        rows.append(raw[start:start + row_size])

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    _write_png(filepath, width, height, rows)
    print(f"[Save] {filepath}")


# ───────────────────────────────────────────────────────────────────────────
# Core Symmetric DDA — returns list of (int, int) rasterised grid positions
# ───────────────────────────────────────────────────────────────────────────
def next_power_of_two(n):
    """
    Return the power of 2 strictly greater than or equal to the textbook condition.
    2^n-1 <= max(|dx|,|dy|) <= 2^n
    """
    if n <= 0:
        return 1
    p = 1
    while p <= n:
        p <<= 1          # p = p * 2  (bit-shift left)
    return p


def sym_round(n):
    """
    Symmetric rounding: half-way values always round away from zero.
    This prevents asymmetry (bumps) in negative coordinates.
    """
    if n > 0:
        return math.floor(n + 0.5)
    elif n < 0:
        return math.ceil(n - 0.5)
    return 0

def symmetric_dda_points(x1: float, y1: float, x2: float, y2: float):
    """
    Symmetric DDA — manual implementation.

    1. dx = x2 - x1,   dy = y2 - y1
    2. steps = 2^n  where  2^n >= max(|dx|, |dy|)   (smallest such power of 2)
    3. x_inc = dx / steps,  y_inc = dy / steps
       (division by a power of 2 is a single arithmetic right-shift)
    4. Plot sym_round(x) sym_round(y) for i = 0 … steps.

    Because steps >= max(|dx|, |dy|), both |x_inc| and |y_inc| are <= 1,
    so no pixel is ever skipped.  However, some pixels may be plotted more
    than once (duplicates), since 2^n can exceed max(|dx|, |dy|).
    """
    dx    = x2 - x1
    dy    = y2 - y1
    steps = next_power_of_two(int(max(abs(dx), abs(dy))))
    if steps == 0:
        return [(sym_round(x1), sym_round(y1))]

    x_inc = dx / steps
    y_inc = dy / steps
    x, y  = float(x1), float(y1)
    pts   = []
    for _ in range(steps + 1):
        # Round to nearest integer properly for both positive and negative
        pt = (sym_round(x), sym_round(y))
        # Symmetric DDA may generate duplicate points — include them
        pts.append(pt)
        x += x_inc
        y += y_inc
    return pts


def unique_points(pts):
    """
    Symmetric DDA generates many sub-pixel points.
    We round them to integers and remove adjacent duplicates.
    """
    unique = []
    seen = set()
    for (x, y) in pts:
        gx = int(sym_round(x))
        gy = int(sym_round(y))
        if (gx, gy) not in seen:
            seen.add((gx, gy))
            unique.append((gx, gy))
    return unique


if __name__ == "__main__":
    import os
    import sys
    
    # Add repo root to sys.path to allow importing the app module
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.append(repo_root)
        
    from app.src import line_drawing_app as lda
    
    # Set default algorithm
    lda.CURRENT_ALGORITHM = "Symmetric DDA"
    
    print(f"[Info] Opening application window (clean canvas) for Symmetric DDA.")
    
    # Launch the app
    lda.run()
