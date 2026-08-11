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
OUTPUT_DIR = os.path.join(REPO_ROOT, "Brestenham", "outputs")

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

POINT_COLORS = [
    (214,39,40),      # Red
    (44,160,44),      # Green
    (31,119,180),     # Blue
]

LABEL_COLOR   = (20, 20, 20)
POINT_RADIUS  = 5

# ── Test cases ─────────────────────────────────────────────────────────────────
TEST_CASES = [
    {"x1":  2, "y1":  2, "x2": 18, "y2": 10,
     "label": "Test Case 1 — Positive Slope", "file": "tc1_positive_slope.png"},
    {"x1":  2, "y1": 14, "x2": 18, "y2":  5,
     "label": "Test Case 2 — Negative Slope", "file": "tc2_negative_slope.png"},
    {"x1":  4, "y1":  2, "x2":  8, "y2": 14,
     "label": "Test Case 3 — Steep Line",     "file": "tc3_steep_line.png"},
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
    ihdr_data = struct.pack(">IIBBBB B", width, height, 8, 2, 0, 0, 0)
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
# Core Bresenham — returns list of (int, int) rasterised grid positions
# ───────────────────────────────────────────────────────────────────────────
def bresenham_points(x1: int, y1: int, x2: int, y2: int):
    """
    Bresenham Line Drawing Algorithm — integer-only arithmetic.

    Handles all octants:
    - Positive and negative slopes
    - Horizontal and vertical lines
    - Steep lines (|dy| > |dx|) and shallow lines (|dx| >= |dy|)
    - Lines drawn in either direction

    Returns a list of (int, int) pixel positions.
    """
    pts = []

    dx = abs(x2 - x1)
    dy = abs(y2 - y1)

    # Determine step direction for each axis
    sx = 1 if x2 > x1 else -1
    sy = 1 if y2 > y1 else -1

    # Decide whether to step along x or y as the dominant axis
    if dx >= dy:
        # Shallow line — step along x
        # Decision parameter: p = 2*dy - dx
        p = 2 * dy - dx
        x, y = x1, y1

        for _ in range(dx + 1):
            pts.append((x, y))
            if p >= 0:
                y += sy
                p -= 2 * dx
            p += 2 * dy
            x += sx
    else:
        # Steep line — step along y
        # Decision parameter: p = 2*dx - dy
        p = 2 * dx - dy
        x, y = x1, y1

        for _ in range(dy + 1):
            pts.append((x, y))
            if p >= 0:
                x += sx
                p -= 2 * dy
            p += 2 * dx
            y += sy
    return pts

if __name__ == "__main__":
    import os
    import sys
    
    # Add repo root to sys.path to allow importing the app module
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.append(repo_root)
        
    from app.src import line_drawing_app as lda
    
    # Set default algorithm to Bresenham
    lda.CURRENT_ALGORITHM = "Bresenham"
    
    print(f"[Info] Opening application window (clean canvas) for Bresenham.")
    
    # Launch the app
    lda.run()
