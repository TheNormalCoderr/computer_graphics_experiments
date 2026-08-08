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
OUTPUT_DIR = os.path.join(REPO_ROOT, "SimpleDDA", "outputs")

# ── Canvas & grid ─────────────────────────────────────────────────────────────
CANVAS_W, CANVAS_H = 760, 620
CELL      = 34          # pixels per grid cell
MARGIN    = 40          # border margin in pixels
GRID_COLS = 20
GRID_ROWS = 16

# ── Clean, readable color scheme ──────────────────────────────────────────────
# Background: dark navy  |  Grid: very subtle  |  Points: vivid single accent
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
    {"x1": 10, "y1":  2, "x2": 10, "y2": 14,
     "label": "Test Case 3 — Vertical Line",  "file": "tc3_vertical_line.png"},
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
# Core DDA — returns list of (int, int) rasterised grid positions
# ───────────────────────────────────────────────────────────────────────────
def dda_points(x1: float, y1: float, x2: float, y2: float):
    """
    Simple DDA — manual implementation.

    1. dx = x2 - x1,   dy = y2 - y1
    2. steps = max(|dx|, |dy|)
    3. x_inc = dx / steps,  y_inc = dy / steps
    4. Plot round(x), round(y) for i = 0 … steps.
    """
    dx    = x2 - x1
    dy    = y2 - y1
    steps = int(max(abs(dx), abs(dy)))
    if steps == 0:
        return [(int(round(x1)), int(round(y1)))]

    x_inc = dx / steps
    y_inc = dy / steps
    x, y  = float(x1), float(y1)
    pts   = []
    for _ in range(steps + 1):
        pts.append((int(round(x)), int(round(y))))
        x += x_inc
        y += y_inc
    return pts


# ───────────────────────────────────────────────────────────────────────────
# OpenGL Rendering Helpers
# ───────────────────────────────────────────────────────────────────────────
def to_canvas(gx: int, gy: int):
    # OpenGL origin is naturally bottom-left. We just scale by cell size.
    cx = MARGIN + gx * CELL
    cy = MARGIN + gy * CELL
    return cx, cy

def draw_text(x, y, text, color, font=glut.GLUT_BITMAP_HELVETICA_10):
    gl.glColor3f(
        color[0] / 255.0,
        color[1] / 255.0,
        color[2] / 255.0,
    )

    gl.glRasterPos2f(x, y)

    for ch in text:
        glut.glutBitmapCharacter(font, ord(ch))

# Global dict to map window IDs to test case indices
window_to_tc = {}

def display():
    win_id = glut.glutGetWindow()
    idx = window_to_tc.get(win_id, 0)
    tc = TEST_CASES[idx]

    gl.glClearColor(BG_COLOR[0]/255.0, BG_COLOR[1]/255.0, BG_COLOR[2]/255.0, 1.0)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)

    color = POINT_COLORS[idx]
    r = POINT_RADIUS

    # ── Grid ─────────────────────────────────────────────────────────────
    gl.glColor3f(GRID_COLOR[0]/255.0, GRID_COLOR[1]/255.0, GRID_COLOR[2]/255.0)
    gl.glLineWidth(1)
    gl.glBegin(gl.GL_LINES)
    for col in range(GRID_COLS + 1):
        cx, _ = to_canvas(col, 0)
        gl.glVertex2f(cx, MARGIN)
        gl.glVertex2f(cx, CANVAS_H - MARGIN)
    for row in range(GRID_ROWS + 1):
        _, cy = to_canvas(0, row)
        gl.glVertex2f(MARGIN, cy)
        gl.glVertex2f(CANVAS_W - MARGIN, cy)
    gl.glEnd()

    # ── Axes ──────────────────────────────────────────────────────────────
    gl.glColor3f(AXIS_COLOR[0]/255.0, AXIS_COLOR[1]/255.0, AXIS_COLOR[2]/255.0)
    gl.glLineWidth(2)
    gl.glBegin(gl.GL_LINES)
    ox, oy = to_canvas(0, 0)
    gl.glVertex2f(ox, MARGIN)
    gl.glVertex2f(ox, CANVAS_H - MARGIN)
    gl.glVertex2f(MARGIN, oy)
    gl.glVertex2f(CANVAS_W - MARGIN, oy)
    gl.glEnd()

    # ── Axis tick labels ──────────────────────────────────────────────────
    for col in range(0, GRID_COLS + 1, 2):
        cx, cy = to_canvas(col, 0)
        draw_text(cx - 4, cy - 14, str(col), AXIS_LBL, glut.GLUT_BITMAP_HELVETICA_10)
    for row in range(0, GRID_ROWS + 1, 2):
        cx, cy = to_canvas(0, row)
        draw_text(cx - 24, cy - 4, str(row), AXIS_LBL, glut.GLUT_BITMAP_HELVETICA_10)

    # ── Compute DDA points ────────────────────────────────────────────────
    x1, y1, x2, y2 = tc["x1"], tc["y1"], tc["x2"], tc["y2"]
    pts = dda_points(x1, y1, x2, y2)

    # ── Direct line segments between consecutive DDA pixels ───────────────
    gl.glColor3f(STAIR_COLOR[0]/255.0, STAIR_COLOR[1]/255.0, STAIR_COLOR[2]/255.0)
    gl.glLineWidth(1)
    gl.glBegin(gl.GL_LINES)
    for i in range(len(pts) - 1):
        ax, ay = to_canvas(*pts[i])
        bx, by = to_canvas(*pts[i + 1])
        gl.glVertex2f(ax, ay)
        gl.glVertex2f(bx, by)
    gl.glEnd()

    # ── Determine dominant axis for label placement ───────────────────────
    dx_abs = abs(x2 - x1)
    dy_abs = abs(y2 - y1)
    dominant_y = dy_abs >= dx_abs

    # ── Circles for each DDA pixel ────────────────────────────────────────
    for i, (gx, gy) in enumerate(pts):
        cx, cy = to_canvas(gx, gy)

        # Filled circle
        gl.glColor3f(color[0]/255.0, color[1]/255.0, color[2]/255.0)
        gl.glBegin(gl.GL_POLYGON)
        for angle in range(0, 360, 8):
            rad = math.radians(angle)
            gl.glVertex2f(cx + r * math.cos(rad), cy + r * math.sin(rad))
        gl.glEnd()

        # Thin dark outline
        gl.glColor3f(0.0, 0.0, 0.0)
        gl.glLineWidth(1)
        gl.glBegin(gl.GL_LINE_LOOP)
        for angle in range(0, 360, 15):
            rad = math.radians(angle)
            gl.glVertex2f(cx + (r + 1.5) * math.cos(rad), cy + (r + 1.5) * math.sin(rad))
        gl.glEnd()

        # Coordinate label
        label = f"({gx},{gy})"

        if dominant_y:
            tx = cx + 8
            ty = cy - 4
            if tx + 46 > CANVAS_W - 4:
                tx = cx - r - 48
        else:
            offset_y = -18 if (i % 2 == 0) else 10
            tx = cx + 6
            ty = cy + offset_y
            if tx + 44 > CANVAS_W - 4:
                tx = cx - r - 46

        ty = max(2, min(ty, CANVAS_H - 14))

        # Draw main text
        draw_text(tx, ty, label, LABEL_COLOR, glut.GLUT_BITMAP_HELVETICA_10)

    gl.glFlush()

    # ── Save the rendered frame as PNG (once per window) ──────────────────
    if win_id not in saved_windows:
        saved_windows.add(win_id)
        out_path = os.path.join(OUTPUT_DIR, tc["file"])
        save_framebuffer(out_path, CANVAS_W, CANVAS_H)


def reshape(w, h):
    gl.glViewport(0, 0, w, h)
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    glu.gluOrtho2D(0, CANVAS_W, 0, CANVAS_H)
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()


def keyboard(key, x, y):
    if key in (b'\x1b', b'q', b'Q'):  # Escape or q/Q
        os._exit(0)


# ───────────────────────────────────────────────────────────────────────────
# Entry point
# ───────────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=== Simple DDA Line Drawing Algorithm (OpenGL) ===")

    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_SINGLE | glut.GLUT_RGB)

    # Calculate info for console and create 3 windows
    for idx, tc in enumerate(TEST_CASES):
        x1, y1, x2, y2 = tc["x1"], tc["y1"], tc["x2"], tc["y2"]
        dx    = x2 - x1
        dy    = y2 - y1
        steps = int(max(abs(dx), abs(dy)))
        x_inc = round(dx / steps, 4) if steps else 0
        y_inc = round(dy / steps, 4) if steps else 0
        pts   = dda_points(x1, y1, x2, y2)
        print(f"[DDA] {tc['label']}  ({x1},{y1})→({x2},{y2})  "
              f"dx={dx} dy={dy} steps={steps} x_inc={x_inc} y_inc={y_inc}  "
              f"pixels={len(pts)}")

        glut.glutInitWindowSize(CANVAS_W, CANVAS_H)
        glut.glutInitWindowPosition(100 + idx * 40, 100 + idx * 40)

        win_title = f"DDA - {tc['label']}".encode("utf-8")
        win_id = glut.glutCreateWindow(win_title)

        window_to_tc[win_id] = idx

        glut.glutDisplayFunc(display)
        glut.glutReshapeFunc(reshape)
        glut.glutKeyboardFunc(keyboard)

    print(f"[Info] Images will be saved to: {OUTPUT_DIR}")
    print("Running OpenGL main loop. Press ESC or 'q' in any window to exit.")
    glut.glutMainLoop()


if __name__ == "__main__":
    main()
