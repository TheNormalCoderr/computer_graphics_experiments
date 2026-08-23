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
OUTPUT_DIR = os.path.join(REPO_ROOT, "MidPointEllipse", "outputs")

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
ELLIPSE_COLOR = (0, 0, 0)         # Black connector

POINT_COLORS = [
    (214,39,40),      # Red
    (44,160,44),      # Green
]

LABEL_COLOR   = (20, 20, 20)
POINT_RADIUS  = 5

# ── Test cases ─────────────────────────────────────────────────────────────────
TEST_CASES = [
    {"xc": 10, "yc":  8, "rx": 5, "ry": 3,
     "label": "Test Case 1 \u2014 Horizontal Ellipse (rx=5, ry=3)", "file": "tc1_horizontal_ellipse.png"},
    {"xc":  6, "yc": 10, "rx": 3, "ry": 5,
     "label": "Test Case 2 \u2014 Vertical Ellipse (rx=3, ry=5)",   "file": "tc2_vertical_ellipse.png"},
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
# Core Mid Point Ellipse Algorithm — returns list of (int, int) positions
# Uses 4-way symmetry and two-region approach
# ───────────────────────────────────────────────────────────────────────────
def _plot_ellipse_symmetric_points(xc, yc, x, y):
    """
    Given a point (x, y) relative to the center, apply 4-way symmetry
    to produce all 4 symmetric points on the ellipse.
    Returns a list of (int, int) pixel positions.
    """
    return [
        (xc + x, yc + y),
        (xc - x, yc + y),
        (xc + x, yc - y),
        (xc - x, yc - y),
    ]


def midpoint_ellipse_points(xc: int, yc: int, rx: int, ry: int):
    """
    Mid Point Ellipse Drawing Algorithm — integer-only arithmetic.

    Computes the pixel positions that approximate an ellipse with
    semi-major axis rx and semi-minor axis ry, centered at (xc, yc).

    The algorithm divides the first quadrant into two regions:
      Region 1: where the slope magnitude is < 1 (step in x)
      Region 2: where the slope magnitude is >= 1 (step in y)

    The boundary between regions is where 2·ry²·x = 2·rx²·y.

    Region 1:
      Start at (0, ry).
      p1 = ry² - rx²·ry + ¼·rx²
      At each step:
        - If p1 < 0: x++, p1 += 2·ry²·x + ry²
        - If p1 >= 0: x++, y--, p1 += 2·ry²·x - 2·rx²·y + ry²

    Region 2:
      Continue from where Region 1 ended.
      p2 = ry²·(x + ½)² + rx²·(y - 1)² - rx²·ry²
      At each step:
        - If p2 > 0: y--, p2 += -2·rx²·y + rx²
        - If p2 <= 0: x++, y--, p2 += 2·ry²·x - 2·rx²·y + rx²

    4-way symmetry is applied at each step.

    Returns a list of (int, int) pixel positions forming the complete ellipse.
    """
    pts = []
    x = 0
    y = ry

    rx2 = rx * rx
    ry2 = ry * ry
    two_rx2 = 2 * rx2
    two_ry2 = 2 * ry2

    # ── Region 1 ──────────────────────────────────────────────────────────
    # Decision parameter for region 1
    # p1 = ry² - rx²·ry + ¼·rx²
    # To avoid floating point, multiply everything by 4:
    # We'll use the standard formulation with float for the initial value,
    # then track with integers via incremental updates.
    p1 = ry2 - (rx2 * ry) + (0.25 * rx2)

    dx = 0        # 2·ry²·x
    dy = two_rx2 * ry   # 2·rx²·y

    # Plot the initial point
    pts.extend(_plot_ellipse_symmetric_points(xc, yc, x, y))

    # Region 1: while the slope magnitude is < 1
    while dx < dy:
        x += 1
        dx += two_ry2
        if p1 < 0:
            p1 += dx + ry2
        else:
            y -= 1
            dy -= two_rx2
            p1 += dx - dy + ry2
        pts.extend(_plot_ellipse_symmetric_points(xc, yc, x, y))

    # ── Region 2 ──────────────────────────────────────────────────────────
    # Decision parameter for region 2
    p2 = (ry2 * (x + 0.5) * (x + 0.5)) + (rx2 * (y - 1) * (y - 1)) - (rx2 * ry2)

    while y > 0:
        y -= 1
        dy -= two_rx2
        if p2 > 0:
            p2 += rx2 - dy
        else:
            x += 1
            dx += two_ry2
            p2 += dx - dy + rx2
        pts.extend(_plot_ellipse_symmetric_points(xc, yc, x, y))

    # Remove duplicate points and sort for consistent ordering
    seen = set()
    unique_pts = []
    for pt in pts:
        if pt not in seen:
            seen.add(pt)
            unique_pts.append(pt)

    # Sort by angle for smooth ellipse drawing
    def angle_key(pt):
        ddx = pt[0] - xc
        ddy = pt[1] - yc
        return math.atan2(ddy, ddx)

    unique_pts.sort(key=angle_key)

    # Validate output to strictly ensure boundaries are not exceeded
    for (px, py) in unique_pts:
        assert abs(px - xc) <= rx, f"Point {px, py} exceeds horizontal bounds {rx}"
        assert abs(py - yc) <= ry, f"Point {px, py} exceeds vertical bounds {ry}"

    assert (xc, yc + ry) in unique_pts or (xc, yc - ry) in unique_pts, "Vertical extremum missing"
    assert (xc + rx, yc) in unique_pts or (xc - rx, yc) in unique_pts, "Horizontal extremum missing"

    return unique_pts


# ───────────────────────────────────────────────────────────────────────────
# OpenGL Rendering Helpers
# ───────────────────────────────────────────────────────────────────────────
def _grid_to_px(gx, gy):
    """Convert grid coordinates to pixel coordinates on the canvas."""
    return MARGIN + gx * CELL, MARGIN + gy * CELL


def _set_color_rgb(r, g, b):
    gl.glColor3f(r / 255.0, g / 255.0, b / 255.0)


def _draw_filled_circle(cx, cy, radius, segments=24):
    """Draw a filled circle at pixel coordinates (cx, cy)."""
    gl.glBegin(gl.GL_POLYGON)
    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        gl.glVertex2f(cx + radius * math.cos(theta),
                      cy + radius * math.sin(theta))
    gl.glEnd()


def _draw_text(x, y, text, font=None):
    """Render bitmap text at the given pixel coordinates."""
    if font is None:
        font = glut.GLUT_BITMAP_HELVETICA_10
    gl.glRasterPos2f(x, y)
    for ch in text:
        glut.glutBitmapCharacter(font, ord(ch))


# ───────────────────────────────────────────────────────────────────────────
# Per-test-case display callback
# ───────────────────────────────────────────────────────────────────────────
def _make_display(tc_index):
    """Return a display callback for the given test case index."""
    def _display():
        tc = TEST_CASES[tc_index]
        xc, yc, rx, ry = tc["xc"], tc["yc"], tc["rx"], tc["ry"]
        pts = midpoint_ellipse_points(xc, yc, rx, ry)
        color = POINT_COLORS[tc_index % len(POINT_COLORS)]

        # Background
        gl.glClearColor(BG_COLOR[0]/255, BG_COLOR[1]/255, BG_COLOR[2]/255, 1)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluOrtho2D(0, CANVAS_W, 0, CANVAS_H)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        # ── Grid ──────────────────────────────────────────────────────────
        _set_color_rgb(*GRID_COLOR)
        gl.glLineWidth(1)
        gl.glBegin(gl.GL_LINES)
        for c in range(GRID_COLS + 1):
            gx = MARGIN + c * CELL
            gl.glVertex2f(gx, MARGIN)
            gl.glVertex2f(gx, MARGIN + GRID_ROWS * CELL)
        for r_ in range(GRID_ROWS + 1):
            gy = MARGIN + r_ * CELL
            gl.glVertex2f(MARGIN, gy)
            gl.glVertex2f(MARGIN + GRID_COLS * CELL, gy)
        gl.glEnd()

        # ── Axes ──────────────────────────────────────────────────────────
        _set_color_rgb(*AXIS_COLOR)
        gl.glLineWidth(2)
        gl.glBegin(gl.GL_LINES)
        # x-axis
        gl.glVertex2f(MARGIN, MARGIN)
        gl.glVertex2f(MARGIN + GRID_COLS * CELL, MARGIN)
        # y-axis
        gl.glVertex2f(MARGIN, MARGIN)
        gl.glVertex2f(MARGIN, MARGIN + GRID_ROWS * CELL)
        gl.glEnd()

        # ── Axis labels ──────────────────────────────────────────────────
        _set_color_rgb(*AXIS_LBL)
        for c in range(0, GRID_COLS + 1, 2):
            px = MARGIN + c * CELL
            _draw_text(px - 4, MARGIN - 14, str(c))
        for r_ in range(0, GRID_ROWS + 1, 2):
            py = MARGIN + r_ * CELL
            lbl = str(r_)
            _draw_text(MARGIN - 10 - len(lbl) * 6, py - 4, lbl)

        # ── Draw the complete smooth mathematical ellipse outline ────────
        _set_color_rgb(*color)
        gl.glLineWidth(2)
        gl.glBegin(gl.GL_LINE_LOOP)
        cx_px, cy_px = _grid_to_px(xc, yc)
        rx_px = rx * CELL
        ry_px = ry * CELL
        # Use enough segments for a smooth ellipse
        circumference_approx = math.pi * (3 * (rx_px + ry_px) - math.sqrt((3 * rx_px + ry_px) * (rx_px + 3 * ry_px)))
        segments = max(64, int(circumference_approx / 2))
        for i in range(segments):
            theta = 2.0 * math.pi * i / segments
            gl.glVertex2f(cx_px + rx_px * math.cos(theta), cy_px + ry_px * math.sin(theta))
        gl.glEnd()

        # ── Mark the center point ─────────────────────────────────────────
        gl.glColor3f(0, 0, 0)
        _draw_filled_circle(cx_px, cy_px, 3)
        _draw_text(cx_px + 6, cy_px + 6, f"C({xc},{yc})")

        # ── Draw semi-axis guide lines ────────────────────────────────────
        gl.glColor3f(0.5, 0.5, 0.5)
        gl.glLineWidth(1)
        gl.glEnable(gl.GL_LINE_STIPPLE)
        gl.glLineStipple(2, 0xAAAA)
        gl.glBegin(gl.GL_LINES)
        # Horizontal semi-axis (rx)
        gl.glVertex2f(cx_px, cy_px)
        gl.glVertex2f(cx_px + rx_px, cy_px)
        # Vertical semi-axis (ry)
        gl.glVertex2f(cx_px, cy_px)
        gl.glVertex2f(cx_px, cy_px + ry_px)
        gl.glEnd()
        gl.glDisable(gl.GL_LINE_STIPPLE)

        # Label the semi-axes
        _draw_text(cx_px + rx_px / 2 - 8, cy_px - 12, f"rx={rx}")
        _draw_text(cx_px + 8, cy_px + ry_px / 2, f"ry={ry}")

        # ── Title ─────────────────────────────────────────────────────────
        _set_color_rgb(*LABEL_COLOR)
        _draw_text(MARGIN, CANVAS_H - 15, tc["label"],
                   glut.GLUT_BITMAP_HELVETICA_18)

        # ── Ensure all rendering is complete before reading ───────────────
        gl.glFinish()

        # ── Auto-save (read back buffer before swap) ─────────────────────
        win_id = glut.glutGetWindow()
        if win_id not in saved_windows:
            saved_windows.add(win_id)
            out_path = os.path.join(OUTPUT_DIR, tc["file"])
            save_framebuffer(out_path, CANVAS_W, CANVAS_H)

        glut.glutSwapBuffers()

    return _display


def _keyboard(key, x, y):
    """Exit on Escape or Q."""
    if key in (b'\x1b', b'q', b'Q'):
        os._exit(0)


def run_standalone():
    """
    Launch standalone OpenGL windows for each test case.
    Each window shows the Mid Point Ellipse visualization and auto-saves
    the output PNG to MidPointEllipse/outputs/.
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_DOUBLE | glut.GLUT_RGB)

    for i, tc in enumerate(TEST_CASES):
        glut.glutInitWindowSize(CANVAS_W, CANVAS_H)
        glut.glutInitWindowPosition(50 + i * 30, 50 + i * 30)
        glut.glutCreateWindow(tc["label"].encode())
        glut.glutDisplayFunc(_make_display(i))
        glut.glutKeyboardFunc(_keyboard)

    print("[Info] Mid Point Ellipse — press Esc or Q to close all windows.")
    glut.glutMainLoop()


if __name__ == "__main__":
    import os
    import sys

    # Add repo root to sys.path to allow importing the app module
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if repo_root not in sys.path:
        sys.path.append(repo_root)

    # Check if --standalone flag is passed
    if "--standalone" in sys.argv:
        run_standalone()
    else:
        from app.src import line_drawing_app as lda

        # Set default algorithm to Mid Point Ellipse
        lda.CURRENT_ALGORITHM = "Mid Point Ellipse"

        print(f"[Info] Opening application window (clean canvas) for Mid Point Ellipse.")

        # Launch the app
        lda.run()
