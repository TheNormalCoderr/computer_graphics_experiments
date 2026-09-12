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
OUTPUT_DIR = os.path.join(REPO_ROOT, "Transformations2D", "outputs")

# ── Canvas & grid ─────────────────────────────────────────────────────────────
CANVAS_W, CANVAS_H = 760, 620
CELL      = 34          # pixels per grid cell
MARGIN    = 40          # border margin in pixels
GRID_COLS = 20
GRID_ROWS = 16

# ── Color scheme ──────────────────────────────────────────────────────────────
BG_COLOR      = (255, 255, 255)   # White
GRID_COLOR    = (235, 235, 235)   # Light gray
AXIS_COLOR    = (40, 40, 40)      # Dark gray
AXIS_LBL      = (90, 90, 90)      # Gray text
LABEL_COLOR   = (20, 20, 20)

ORIGINAL_COLOR   = (31, 119, 180)     # Blue — original shape
TRANSFORMED_COLOR = (214, 39, 40)     # Red — transformed shape
POINT_RADIUS = 5

# ── Test cases ─────────────────────────────────────────────────────────────────
# Each test case defines a polygon (list of vertices), a transformation, and
# the transformation parameters.  The visualiser draws both original and
# transformed polygon on the same grid.

TEST_CASES = [
    {
        "label": "Test Case 1 — Translation (tx=5, ty=3)",
        "file":  "tc1_translation.png",
        "vertices": [(2, 2), (6, 2), (6, 6), (2, 6)],   # square
        "transform": "translation",
        "params": {"tx": 5, "ty": 3},
    },
    {
        "label": "Test Case 2 — Scaling (sx=2, sy=1.5)",
        "file":  "tc2_scaling.png",
        "vertices": [(2, 2), (5, 2), (5, 5), (2, 5)],   # square
        "transform": "scaling",
        "params": {"sx": 2, "sy": 1.5},
    },
    {
        "label": "Test Case 3 — Rotation (θ = 45°)",
        "file":  "tc3_rotation.png",
        "vertices": [(6, 2), (10, 2), (10, 6), (6, 6)],  # square
        "transform": "rotation",
        "params": {"angle_deg": 45},
    },
]



# ───────────────────────────────────────────────────────────────────────────
# Minimal PNG writer (reused from existing experiments)
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
    """Read the OpenGL framebuffer and save as PNG."""
    gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
    data = gl.glReadPixels(0, 0, width, height, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
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
# 2D Transformation functions using homogeneous coordinates
#
#   A 2D point (x, y) is represented as [x, y, 1] (column vector).
#   A 3×3 transformation matrix M transforms it as [x', y', 1] = M · [x, y, 1]^T.
# ───────────────────────────────────────────────────────────────────────────

def mat3_identity():
    """Return a 3×3 identity matrix (list of 3 lists)."""
    return [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]


def mat3_multiply(A, B):
    """Multiply two 3×3 matrices A and B, return C = A·B."""
    C = [[0.0]*3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                C[i][j] += A[i][k] * B[k][j]
    return C


def mat3_transform_point(M, x, y):
    """Apply 3×3 matrix M to point (x, y) using homogeneous coords."""
    xp = M[0][0]*x + M[0][1]*y + M[0][2]
    yp = M[1][0]*x + M[1][1]*y + M[1][2]
    return (xp, yp)


def translation_matrix(tx, ty):
    """
    Translation matrix:
        | 1  0  tx |
        | 0  1  ty |
        | 0  0   1 |
    """
    return [
        [1.0, 0.0, float(tx)],
        [0.0, 1.0, float(ty)],
        [0.0, 0.0, 1.0],
    ]


def scaling_matrix(sx, sy):
    """
    Scaling matrix (about the origin):
        | sx  0  0 |
        |  0 sy  0 |
        |  0  0  1 |
    """
    return [
        [float(sx), 0.0,       0.0],
        [0.0,       float(sy), 0.0],
        [0.0,       0.0,       1.0],
    ]


def rotation_matrix(angle_deg):
    """
    Rotation matrix (counter-clockwise about the origin):
        | cos θ  -sin θ  0 |
        | sin θ   cos θ  0 |
        |   0       0    1 |
    """
    theta = math.radians(angle_deg)
    c = math.cos(theta)
    s = math.sin(theta)
    return [
        [ c, -s, 0.0],
        [ s,  c, 0.0],
        [0.0, 0.0, 1.0],
    ]


def apply_transformation(vertices, transform_name, params):
    """
    Apply the requested transformation to a list of 2D vertices.

    Returns:
        transformed_vertices: list of (x', y') tuples
        matrix: the 3×3 transformation matrix used
    """
    if transform_name == "translation":
        M = translation_matrix(params["tx"], params["ty"])
    elif transform_name == "scaling":
        M = scaling_matrix(params["sx"], params["sy"])
    elif transform_name == "rotation":
        M = rotation_matrix(params["angle_deg"])
    else:
        raise ValueError(f"Unknown transformation: {transform_name}")

    transformed = [mat3_transform_point(M, x, y) for (x, y) in vertices]
    return transformed, M


def format_matrix(M):
    """Pretty-print a 3×3 matrix for console output."""
    lines = []
    for row in M:
        lines.append("  | " + "  ".join(f"{v:8.4f}" for v in row) + " |")
    return "\n".join(lines)


# ───────────────────────────────────────────────────────────────────────────
# OpenGL drawing helpers (adapted from SimpleDDA style)
# ───────────────────────────────────────────────────────────────────────────

def _gl_color(rgb):
    """Set GL colour from an (R, G, B) 0-255 tuple."""
    gl.glColor3f(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)


def _screen_pos(gx, gy):
    """Convert grid coordinates (gx, gy) to screen pixel coordinates."""
    sx = MARGIN + gx * CELL
    sy = MARGIN + gy * CELL
    return sx, sy


def _draw_filled_circle(cx, cy, radius, segments=20):
    """Draw a filled circle at screen position (cx, cy)."""
    gl.glBegin(gl.GL_TRIANGLE_FAN)
    gl.glVertex2f(cx, cy)
    for i in range(segments + 1):
        angle = 2.0 * math.pi * i / segments
        gl.glVertex2f(cx + radius * math.cos(angle),
                      cy + radius * math.sin(angle))
    gl.glEnd()


def _draw_text(x, y, text, font=glut.__dict__["GLUT_BITMAP_HELVETICA_10"]):
    """Render a bitmap string at screen position (x, y)."""
    gl.glRasterPos2f(x, y)
    for ch in text:
        glut.glutBitmapCharacter(font, ord(ch))


def _draw_grid():
    """Draw reference grid with axis labels."""
    # Vertical grid lines
    _gl_color(GRID_COLOR)
    for col in range(GRID_COLS + 1):
        sx = MARGIN + col * CELL
        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(sx, MARGIN)
        gl.glVertex2f(sx, MARGIN + GRID_ROWS * CELL)
        gl.glEnd()

    # Horizontal grid lines
    for row in range(GRID_ROWS + 1):
        sy = MARGIN + row * CELL
        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(MARGIN, sy)
        gl.glVertex2f(MARGIN + GRID_COLS * CELL, sy)
        gl.glEnd()

    # Draw axes (column 0 and row 0)
    _gl_color(AXIS_COLOR)
    gl.glLineWidth(2.0)
    # X-axis
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(MARGIN, MARGIN)
    gl.glVertex2f(MARGIN + GRID_COLS * CELL, MARGIN)
    gl.glEnd()
    # Y-axis
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(MARGIN, MARGIN)
    gl.glVertex2f(MARGIN, MARGIN + GRID_ROWS * CELL)
    gl.glEnd()
    gl.glLineWidth(1.0)

    # Axis labels
    _gl_color(AXIS_LBL)
    for col in range(0, GRID_COLS + 1, 2):
        sx = MARGIN + col * CELL - 4
        _draw_text(sx, MARGIN - 14, str(col))
    for row in range(0, GRID_ROWS + 1, 2):
        sy = MARGIN + row * CELL - 4
        _draw_text(MARGIN - 20, sy, str(row))


def _draw_polygon(vertices, color, line_width=2.0, draw_points=True, label_points=True):
    """
    Draw a closed polygon on the grid.
    - Edges are drawn as GL_LINE_LOOP.
    - Vertices are drawn as filled circles with coordinate labels.
    """
    _gl_color(color)
    gl.glLineWidth(line_width)

    # Edges
    gl.glBegin(gl.GL_LINE_LOOP)
    for (gx, gy) in vertices:
        sx, sy = _screen_pos(gx, gy)
        gl.glVertex2f(sx, sy)
    gl.glEnd()

    # Vertices
    if draw_points:
        for (gx, gy) in vertices:
            sx, sy = _screen_pos(gx, gy)
            _draw_filled_circle(sx, sy, POINT_RADIUS)

    # Labels
    if label_points:
        for (gx, gy) in vertices:
            sx, sy = _screen_pos(gx, gy)
            lbl = f"({gx:.1f},{gy:.1f})" if isinstance(gx, float) else f"({gx},{gy})"
            _draw_text(sx + 8, sy + 8, lbl)

    gl.glLineWidth(1.0)


def _draw_legend(y_base):
    """Draw a simple colour legend at the bottom of the window."""
    # Original
    _gl_color(ORIGINAL_COLOR)
    _draw_filled_circle(MARGIN + 10, y_base, 6)
    _gl_color(LABEL_COLOR)
    _draw_text(MARGIN + 22, y_base - 4, "Original")

    # Transformed
    _gl_color(TRANSFORMED_COLOR)
    _draw_filled_circle(MARGIN + 110, y_base, 6)
    _gl_color(LABEL_COLOR)
    _draw_text(MARGIN + 122, y_base - 4, "Transformed")


# ───────────────────────────────────────────────────────────────────────────
# Per-test-case display callback factory
# ───────────────────────────────────────────────────────────────────────────

def make_display_func(tc):
    """Return a display callback for the given test case dict."""
    def display():
        gl.glClearColor(BG_COLOR[0]/255, BG_COLOR[1]/255, BG_COLOR[2]/255, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        _draw_grid()

        original = tc["vertices"]
        transformed, M = apply_transformation(original, tc["transform"], tc["params"])

        # Draw original polygon
        _draw_polygon(original, ORIGINAL_COLOR)

        # Draw transformed polygon
        _draw_polygon(transformed, TRANSFORMED_COLOR)

        # Title
        _gl_color(LABEL_COLOR)
        title_font = glut.__dict__.get(
            "GLUT_BITMAP_HELVETICA_18",
            glut.__dict__.get("GLUT_BITMAP_HELVETICA_12",
                              glut.__dict__["GLUT_BITMAP_HELVETICA_10"]),
        )
        _draw_text(MARGIN, CANVAS_H - 12, tc["label"], font=title_font)

        # Legend
        _draw_legend(CANVAS_H - 38)

        gl.glFlush()
        glut.glutSwapBuffers()

    return display


def make_save_timer(tc, win_id, display_func):
    """Return a timer callback that saves the framebuffer for a test case."""
    def timer_cb(_value):
        glut.glutSetWindow(win_id)
        # Directly call the display function to ensure framebuffer is populated
        display_func()
        filepath = os.path.join(OUTPUT_DIR, tc["file"])
        save_framebuffer(filepath, CANVAS_W, CANVAS_H)
    return timer_cb


# ───────────────────────────────────────────────────────────────────────────
# Keyboard handler
# ───────────────────────────────────────────────────────────────────────────

def keyboard(key, _x, _y):
    if key in (b'\x1b', b'q', b'Q'):
        sys.exit(0)


# ───────────────────────────────────────────────────────────────────────────
# Main — open one window per test case
# ───────────────────────────────────────────────────────────────────────────

def main():
    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(int(glut.GLUT_DOUBLE) | int(glut.GLUT_RGB))

    window_data = []

    for idx, tc in enumerate(TEST_CASES):
        # Print transformation details to console
        transformed, M = apply_transformation(tc["vertices"], tc["transform"], tc["params"])
        print(f"\n{'='*60}")
        print(f"  {tc['label']}")
        print(f"{'='*60}")
        print(f"  Original vertices : {tc['vertices']}")
        print(f"  Transformation    : {tc['transform']}")
        print(f"  Parameters        : {tc['params']}")
        print(f"  Matrix:")
        print(format_matrix(M))
        print(f"  Transformed vertices: {[(round(x,2), round(y,2)) for x,y in transformed]}")

        # Create window
        glut.glutInitWindowSize(CANVAS_W, CANVAS_H)
        glut.glutInitWindowPosition(80 + idx * 40, 80 + idx * 40)
        win_id = glut.glutCreateWindow(tc["label"].encode())
        display_func = make_display_func(tc)
        window_data.append((win_id, tc, display_func))

        # Setup 2D projection
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluOrtho2D(0, CANVAS_W, 0, CANVAS_H)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        # Enable anti-aliasing
        gl.glEnable(gl.GL_LINE_SMOOTH)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        glut.glutDisplayFunc(display_func)
        glut.glutKeyboardFunc(keyboard)

    # Schedule saves with a delay so windows are fully rendered
    for i, (win_id, tc, display_func) in enumerate(window_data):
        delay_ms = 1000 + i * 500  # stagger saves
        glut.glutTimerFunc(delay_ms, make_save_timer(tc, win_id, display_func), 0)

    print(f"\n[Info] Outputs will be saved to: {OUTPUT_DIR}")
    print("[Info] Press Esc or Q to exit.\n")
    glut.glutMainLoop()


if __name__ == "__main__":
    main()
