import os
import sys
import math
import struct
import zlib

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUTPUT_DIR = os.path.join(REPO_ROOT, "CompositeTransformations2D", "outputs")

# ── Canvas & grid geometry (generous margins prevent any cropping) ───────────
CANVAS_W, CANVAS_H = 960, 700
CELL          = 34          # pixels per grid cell
MARGIN_LEFT   = 70          # margin for Y-axis labels
MARGIN_BOTTOM = 60          # margin for X-axis labels
GRID_COLS     = 20
GRID_ROWS     = 16

# ── Color scheme ──────────────────────────────────────────────────────────────
BG_COLOR          = (255, 255, 255)   # White
GRID_COLOR        = (235, 235, 235)   # Light gray
AXIS_COLOR        = (40, 40, 40)      # Dark gray
AXIS_LBL          = (80, 80, 80)      # Gray text
LABEL_COLOR       = (20, 20, 20)
ORIGINAL_COLOR    = (31, 119, 180)    # Blue — original shape
TRANSFORMED_COLOR = (214, 39, 40)     # Red — transformed shape
PIVOT_COLOR       = (44, 160, 44)     # Green — pivot / arbitrary axis
POINT_RADIUS      = 5

# ── Test Cases ─────────────────────────────────────────────────────────────────
# All coordinates stay within [1..19, 1..15] so polygons, labels, and axes are never cropped
TEST_CASES = [
    {
        "label": "TC1 - Rotation About Pivot (5,5) by 45 deg",
        "file":  "tc1_rotation_about_point.png",
        "vertices": [(3, 3), (7, 3), (7, 7), (3, 7)],
        "type": "pivot_rotation",
        "params": {"pivot_x": 5.0, "pivot_y": 5.0, "angle_deg": 45.0},
        "pivot": (5.0, 5.0),
        "axis": None,
    },
    {
        "label": "TC2 - Scaling About Fixed Point (3,3)",
        "file":  "tc2_scaling_about_point.png",
        "vertices": [(3, 3), (7, 3), (5, 6)],
        "type": "fixed_point_scaling",
        "params": {"fixed_x": 3.0, "fixed_y": 3.0, "sx": 1.6, "sy": 1.6},
        "pivot": (3.0, 3.0),
        "axis": None,
    },
    {
        "label": "TC3 - Reflection About Arbitrary Axis",
        "file":  "tc3_reflection_about_axis.png",
        "vertices": [(3, 6), (7, 8), (5, 10)],
        "type": "axis_reflection",
        "params": {"x1": 1.0, "y1": 2.0, "x2": 13.0, "y2": 11.0},
        "pivot": None,
        "axis": ((1.0, 2.0), (13.0, 11.0)),
    },
    {
        "label": "TC4 - Scaling Along Arbitrary Axis (45 deg)",
        "file":  "tc4_scaling_along_axis.png",
        "vertices": [(4, 4), (7, 4), (7, 7), (4, 7)],
        "type": "axis_scaling",
        "params": {"x1": 2.0, "y1": 2.0, "x2": 12.0, "y2": 12.0, "s_along": 1.8, "s_perp": 0.8},
        "pivot": None,
        "axis": ((2.0, 2.0), (12.0, 12.0)),
    },
    {
        "label": "TC5 - Composite: Translate -> Rotate -> Scale",
        "file":  "tc5_composite_sequence.png",
        "vertices": [(2, 2), (5, 2), (5, 5), (2, 5)],
        "type": "general_sequence",
        "params": {"tx": 2.0, "ty": 1.0, "pivot_x": 6.0, "pivot_y": 5.0, "angle_deg": 30.0, "sx": 1.2, "sy": 1.2},
        "pivot": (6.0, 5.0),
        "axis": None,
    },
]


# ───────────────────────────────────────────────────────────────────────────
# Minimal PNG writer (pure Python standard library)
# ───────────────────────────────────────────────────────────────────────────
def _write_png(filepath, width, height, rgb_rows):
    """Write an RGB PNG from a list of rows (top-to-bottom)."""
    def _chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack(">IIBBBB B", width, height, 8, 2, 0, 0, 0)
    ihdr = _chunk(b'IHDR', ihdr_data)

    raw = b''
    for row in rgb_rows:
        raw += b'\x00' + bytes(row)
    idat = _chunk(b'IDAT', zlib.compress(raw, 9))
    iend = _chunk(b'IEND', b'')

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(sig + ihdr + idat + iend)


# ───────────────────────────────────────────────────────────────────────────
# 3×3 Matrix operations (Homogeneous Coordinates)
# ───────────────────────────────────────────────────────────────────────────

def mat3_identity():
    """Return a 3×3 identity matrix."""
    return [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0],
    ]


def mat3_multiply(A, B):
    """Multiply two 3×3 matrices A and B, returning C = A · B."""
    C = [[0.0] * 3 for _ in range(3)]
    for i in range(3):
        for j in range(3):
            for k in range(3):
                C[i][j] += A[i][k] * B[k][j]
    return C


def mat3_transform_point(M, x, y):
    """Apply 3×3 matrix M to point (x, y) using homogeneous coordinates [x, y, 1]^T."""
    xp = M[0][0] * x + M[0][1] * y + M[0][2]
    yp = M[1][0] * x + M[1][1] * y + M[1][2]
    return (xp, yp)


def translation_matrix(tx, ty):
    """3×3 Translation Matrix T(tx, ty)."""
    return [
        [1.0, 0.0, float(tx)],
        [0.0, 1.0, float(ty)],
        [0.0, 0.0, 1.0],
    ]


def scaling_matrix(sx, sy):
    """3×3 Scaling Matrix S(sx, sy)."""
    return [
        [float(sx), 0.0,       0.0],
        [0.0,       float(sy), 0.0],
        [0.0,       0.0,       1.0],
    ]


def rotation_matrix(angle_deg):
    """3×3 Counter-clockwise Rotation Matrix R(θ)."""
    theta = math.radians(angle_deg)
    c = math.cos(theta)
    s = math.sin(theta)
    return [
        [ c, -s, 0.0],
        [ s,  c, 0.0],
        [0.0, 0.0, 1.0],
    ]


def reflection_x_matrix():
    """3×3 Reflection Matrix across the X-axis."""
    return [
        [1.0,  0.0, 0.0],
        [0.0, -1.0, 0.0],
        [0.0,  0.0, 1.0],
    ]


def compose_transformations(*matrices):
    """
    Compose a sequence of transformation matrices.
    If transformations T1, T2, ..., Tn are applied in chronological sequence to point P:
        P' = Tn · ... · T2 · T1 · P
    This function computes the single composite matrix:
        M = Tn · ... · T2 · T1
    """
    if len(matrices) == 1 and isinstance(matrices[0], (list, tuple)) and len(matrices[0]) > 0 and isinstance(matrices[0][0], list) and isinstance(matrices[0][0][0], list):
        matrices = matrices[0]

    if not matrices:
        return mat3_identity()

    result = matrices[0]
    for mat in matrices[1:]:
        result = mat3_multiply(mat, result)
    return result


# ───────────────────────────────────────────────────────────────────────────
# Composite Transformation Generators (Arbitrary Axes & Pivots)
# ───────────────────────────────────────────────────────────────────────────

def transform_about_point_matrix(pivot_x, pivot_y, angle_deg=0.0, sx=1.0, sy=1.0):
    """
    Composite transformation for rotation and/or scaling about an arbitrary pivot point (xp, yp):
        M = T(xp, yp) · R(θ) · S(sx, sy) · T(-xp, -yp)
    """
    t_orig = translation_matrix(-pivot_x, -pivot_y)
    s = scaling_matrix(sx, sy)
    r = rotation_matrix(angle_deg)
    t_back = translation_matrix(pivot_x, pivot_y)

    m = mat3_multiply(s, t_orig)
    m = mat3_multiply(r, m)
    return mat3_multiply(t_back, m)


def scale_about_point_matrix(fixed_x, fixed_y, sx, sy):
    """
    Scaling about an arbitrary fixed point (xf, yf):
        M = T(xf, yf) · S(sx, sy) · T(-xf, -yf)
    """
    return transform_about_point_matrix(fixed_x, fixed_y, angle_deg=0.0, sx=sx, sy=sy)


def transform_about_axis_matrix(x1, y1, x2, y2):
    """
    Reflection across an arbitrary axis line passing through (x1, y1) and (x2, y2):
        1. Translate line so (x1, y1) is at the origin: T(-x1, -y1)
        2. Rotate line by -θ so it aligns with the X-axis: R(-θ)
        3. Reflect across the X-axis: Ref_x
        4. Invert rotation by +θ: R(θ)
        5. Invert translation: T(x1, y1)
        Net Composite Matrix:
            M = T(x1, y1) · R(θ) · Ref_x · R(-θ) · T(-x1, -y1)
    """
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0.0 and dy == 0.0:
        raise ValueError("Arbitrary axis requires two distinct points.")

    theta_deg = math.degrees(math.atan2(dy, dx))

    t_orig = translation_matrix(-x1, -y1)
    r_align = rotation_matrix(-theta_deg)
    ref_x = reflection_x_matrix()
    r_back = rotation_matrix(theta_deg)
    t_back = translation_matrix(x1, y1)

    m = mat3_multiply(r_align, t_orig)
    m = mat3_multiply(ref_x, m)
    m = mat3_multiply(r_back, m)
    return mat3_multiply(t_back, m)


def scale_along_axis_matrix(x1, y1, x2, y2, s_along, s_perp):
    """
    Scaling along an arbitrary axis line:
        Scales by factor s_along along the axis direction, and s_perp perpendicular to it.
        M = T(x1, y1) · R(θ) · S(s_along, s_perp) · R(-θ) · T(-x1, -y1)
    """
    dx = x2 - x1
    dy = y2 - y1
    if dx == 0.0 and dy == 0.0:
        raise ValueError("Arbitrary axis requires two distinct points.")

    theta_deg = math.degrees(math.atan2(dy, dx))

    t_orig = translation_matrix(-x1, -y1)
    r_align = rotation_matrix(-theta_deg)
    s = scaling_matrix(s_along, s_perp)
    r_back = rotation_matrix(theta_deg)
    t_back = translation_matrix(x1, y1)

    m = mat3_multiply(r_align, t_orig)
    m = mat3_multiply(s, m)
    m = mat3_multiply(r_back, m)
    return mat3_multiply(t_back, m)


def composite_sequence_matrix(tx, ty, pivot_x, pivot_y, angle_deg, sx, sy):
    """
    General multi-stage composite sequence:
    Translation by (tx, ty) -> Rotation by angle_deg about (pivot_x, pivot_y) -> Scaling by (sx, sy).
        M = S(sx, sy) · M_pivot(pivot_x, pivot_y, angle_deg) · T(tx, ty)
    """
    t = translation_matrix(tx, ty)
    r_p = transform_about_point_matrix(pivot_x, pivot_y, angle_deg=angle_deg, sx=1.0, sy=1.0)
    s = scaling_matrix(sx, sy)
    m = mat3_multiply(r_p, t)
    return mat3_multiply(s, m)


def apply_composite_transformation(vertices, tc_type, params):
    """Apply composite transformation to a list of vertices."""
    if tc_type == "pivot_rotation":
        M = transform_about_point_matrix(
            params["pivot_x"], params["pivot_y"],
            angle_deg=params["angle_deg"],
            sx=1.0, sy=1.0
        )
    elif tc_type == "fixed_point_scaling":
        M = scale_about_point_matrix(
            params["fixed_x"], params["fixed_y"],
            params["sx"], params["sy"]
        )
    elif tc_type == "axis_reflection":
        M = transform_about_axis_matrix(
            params["x1"], params["y1"],
            params["x2"], params["y2"]
        )
    elif tc_type == "axis_scaling":
        M = scale_along_axis_matrix(
            params["x1"], params["y1"],
            params["x2"], params["y2"],
            params["s_along"], params["s_perp"]
        )
    elif tc_type == "general_sequence":
        M = composite_sequence_matrix(
            params["tx"], params["ty"],
            params["pivot_x"], params["pivot_y"],
            params["angle_deg"],
            params["sx"], params["sy"]
        )
    else:
        raise ValueError(f"Unknown composite transformation type: {tc_type}")

    transformed = [mat3_transform_point(M, x, y) for (x, y) in vertices]
    return transformed, M


def format_matrix(M):
    """Pretty-print a 3×3 matrix."""
    lines = []
    for row in M:
        lines.append("  | " + "  ".join(f"{v:8.4f}" for v in row) + " |")
    return "\n".join(lines)


# ───────────────────────────────────────────────────────────────────────────
# Coordinate mapping helper
# ───────────────────────────────────────────────────────────────────────────

def _screen_pos(gx, gy):
    """
    Convert grid coordinates (gx, gy) to screen pixel coordinates.
    Origin (0,0) is near bottom-left: (MARGIN_LEFT, CANVAS_H - MARGIN_BOTTOM).
    """
    sx = int(round(MARGIN_LEFT + gx * CELL))
    sy = int(round(CANVAS_H - MARGIN_BOTTOM - gy * CELL))
    return sx, sy


# ───────────────────────────────────────────────────────────────────────────
# Built-in 5x7 Bitmap Font Dictionary
# ───────────────────────────────────────────────────────────────────────────
FONT_5X7 = {
    ' ': [0x00, 0x00, 0x00, 0x00, 0x00],
    '!': [0x00, 0x00, 0x5F, 0x00, 0x00],
    '"': [0x00, 0x07, 0x00, 0x07, 0x00],
    '#': [0x14, 0x7F, 0x14, 0x7F, 0x14],
    '$': [0x24, 0x2A, 0x7F, 0x2A, 0x12],
    '%': [0x23, 0x13, 0x08, 0x64, 0x62],
    '&': [0x36, 0x49, 0x55, 0x22, 0x50],
    "'": [0x00, 0x05, 0x03, 0x00, 0x00],
    '(': [0x00, 0x1C, 0x22, 0x41, 0x00],
    ')': [0x00, 0x41, 0x22, 0x1C, 0x00],
    '*': [0x08, 0x2A, 0x1C, 0x2A, 0x08],
    '+': [0x08, 0x08, 0x3E, 0x08, 0x08],
    ',': [0x00, 0x50, 0x30, 0x00, 0x00],
    '-': [0x08, 0x08, 0x08, 0x08, 0x08],
    '.': [0x00, 0x60, 0x60, 0x00, 0x00],
    '/': [0x20, 0x10, 0x08, 0x04, 0x02],
    '0': [0x3E, 0x51, 0x49, 0x45, 0x3E],
    '1': [0x00, 0x42, 0x7F, 0x40, 0x00],
    '2': [0x42, 0x61, 0x51, 0x49, 0x46],
    '3': [0x21, 0x41, 0x45, 0x4B, 0x31],
    '4': [0x18, 0x14, 0x12, 0x7F, 0x10],
    '5': [0x27, 0x45, 0x45, 0x45, 0x39],
    '6': [0x3C, 0x4A, 0x49, 0x49, 0x30],
    '7': [0x01, 0x71, 0x09, 0x05, 0x03],
    '8': [0x36, 0x49, 0x49, 0x49, 0x36],
    '9': [0x06, 0x49, 0x49, 0x29, 0x1E],
    ':': [0x00, 0x36, 0x36, 0x00, 0x00],
    ';': [0x00, 0x56, 0x36, 0x00, 0x00],
    '<': [0x08, 0x14, 0x22, 0x41, 0x00],
    '=': [0x14, 0x14, 0x14, 0x14, 0x14],
    '>': [0x00, 0x41, 0x22, 0x14, 0x08],
    '?': [0x02, 0x01, 0x51, 0x09, 0x06],
    '@': [0x32, 0x49, 0x79, 0x41, 0x3E],
    'A': [0x7E, 0x11, 0x11, 0x11, 0x7E],
    'B': [0x7F, 0x49, 0x49, 0x49, 0x36],
    'C': [0x3E, 0x41, 0x41, 0x41, 0x22],
    'D': [0x7F, 0x41, 0x41, 0x22, 0x1C],
    'E': [0x7F, 0x49, 0x49, 0x49, 0x41],
    'F': [0x7F, 0x09, 0x09, 0x09, 0x01],
    'G': [0x3E, 0x41, 0x49, 0x49, 0x7A],
    'H': [0x7F, 0x08, 0x08, 0x08, 0x7F],
    'I': [0x00, 0x41, 0x7F, 0x41, 0x00],
    'J': [0x20, 0x40, 0x41, 0x3F, 0x01],
    'K': [0x7F, 0x08, 0x14, 0x22, 0x41],
    'L': [0x7F, 0x40, 0x40, 0x40, 0x40],
    'M': [0x7F, 0x02, 0x04, 0x02, 0x7F],
    'N': [0x7F, 0x04, 0x08, 0x10, 0x7F],
    'O': [0x3E, 0x41, 0x41, 0x41, 0x3E],
    'P': [0x7F, 0x09, 0x09, 0x09, 0x06],
    'Q': [0x3E, 0x41, 0x51, 0x21, 0x5E],
    'R': [0x7F, 0x09, 0x19, 0x29, 0x46],
    'S': [0x46, 0x49, 0x49, 0x49, 0x31],
    'T': [0x01, 0x01, 0x7F, 0x01, 0x01],
    'U': [0x3F, 0x40, 0x40, 0x40, 0x3F],
    'V': [0x1F, 0x20, 0x40, 0x20, 0x1F],
    'W': [0x3F, 0x40, 0x38, 0x40, 0x3F],
    'X': [0x63, 0x14, 0x08, 0x14, 0x63],
    'Y': [0x07, 0x08, 0x70, 0x08, 0x07],
    'Z': [0x61, 0x51, 0x49, 0x45, 0x43],
    '[': [0x00, 0x7F, 0x41, 0x41, 0x00],
    '\\': [0x02, 0x04, 0x08, 0x10, 0x20],
    ']': [0x00, 0x41, 0x41, 0x7F, 0x00],
    '^': [0x04, 0x02, 0x01, 0x02, 0x04],
    '_': [0x40, 0x40, 0x40, 0x40, 0x40],
    '`': [0x00, 0x01, 0x02, 0x04, 0x00],
    'a': [0x20, 0x54, 0x54, 0x54, 0x78],
    'b': [0x7F, 0x48, 0x44, 0x44, 0x38],
    'c': [0x38, 0x44, 0x44, 0x44, 0x20],
    'd': [0x38, 0x44, 0x44, 0x48, 0x7F],
    'e': [0x38, 0x54, 0x54, 0x54, 0x18],
    'f': [0x08, 0x7E, 0x09, 0x01, 0x02],
    'g': [0x0C, 0x52, 0x52, 0x52, 0x3E],
    'h': [0x7F, 0x08, 0x04, 0x04, 0x78],
    'i': [0x00, 0x44, 0x7D, 0x40, 0x00],
    'j': [0x20, 0x40, 0x44, 0x3D, 0x00],
    'k': [0x7F, 0x10, 0x28, 0x44, 0x00],
    'l': [0x00, 0x41, 0x7F, 0x40, 0x00],
    'm': [0x7C, 0x04, 0x18, 0x04, 0x78],
    'n': [0x7C, 0x08, 0x04, 0x04, 0x78],
    'o': [0x38, 0x44, 0x44, 0x44, 0x38],
    'p': [0x7C, 0x14, 0x14, 0x14, 0x08],
    'q': [0x08, 0x14, 0x14, 0x18, 0x7C],
    'r': [0x7C, 0x08, 0x04, 0x04, 0x08],
    's': [0x48, 0x54, 0x54, 0x54, 0x20],
    't': [0x04, 0x3F, 0x44, 0x40, 0x20],
    'u': [0x3C, 0x40, 0x40, 0x20, 0x7C],
    'v': [0x1C, 0x20, 0x40, 0x20, 0x1C],
    'w': [0x3C, 0x40, 0x30, 0x40, 0x3C],
    'x': [0x44, 0x28, 0x10, 0x28, 0x44],
    'y': [0x0C, 0x50, 0x50, 0x50, 0x3C],
    'z': [0x44, 0x64, 0x54, 0x4C, 0x44],
}


def _draw_char(buf, w, h, x, y, ch, color, scale=1):
    """Draw a single 5x7 character into the pixel buffer."""
    cols = FONT_5X7.get(ch, FONT_5X7.get(ch.lower(), [0, 0, 0, 0, 0]))
    for col_idx, col_val in enumerate(cols):
        for bit_idx in range(7):
            if (col_val >> bit_idx) & 1:
                for dx in range(scale):
                    for dy in range(scale):
                        px = int(x + col_idx * scale + dx)
                        py = int(y + bit_idx * scale + dy)
                        if 0 <= px < w and 0 <= py < h:
                            idx = (py * w + px) * 3
                            buf[idx:idx+3] = bytes(color)


def _draw_string(buf, w, h, x, y, text, color, scale=1):
    """Draw a string into the pixel buffer using the bitmap font."""
    cx = x
    for ch in text:
        _draw_char(buf, w, h, cx, y, ch, color, scale)
        cx += (5 + 1) * scale


# ───────────────────────────────────────────────────────────────────────────
# Pure Python Software Rasterizer (Zero-Crop Guarantee)
# ───────────────────────────────────────────────────────────────────────────

def render_test_case_image(tc, filepath):
    """Render a complete, uncropped test case image to PNG."""
    buf = bytearray([255] * (CANVAS_W * CANVAS_H * 3))

    def set_pixel(px, py, color):
        if 0 <= px < CANVAS_W and 0 <= py < CANVAS_H:
            idx = (py * CANVAS_W + px) * 3
            buf[idx:idx+3] = bytes(color)

    def draw_line(x0, y0, x1, y1, color, width=1, dashed=False):
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        step = 0
        while True:
            if not dashed or (step % 12 < 7):
                for wox in range(-width // 2, width // 2 + 1):
                    for woy in range(-width // 2, width // 2 + 1):
                        set_pixel(x0 + wox, y0 + woy, color)
            step += 1
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def draw_circle(cx, cy, r, color):
        cx, cy = int(round(cx)), int(round(cy))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    set_pixel(cx + dx, cy + dy, color)

    grid_right = MARGIN_LEFT + GRID_COLS * CELL
    grid_top   = CANVAS_H - MARGIN_BOTTOM - GRID_ROWS * CELL
    grid_base  = CANVAS_H - MARGIN_BOTTOM

    # 1. Reference Grid
    for col in range(GRID_COLS + 1):
        sx = MARGIN_LEFT + col * CELL
        draw_line(sx, grid_top, sx, grid_base, GRID_COLOR)
    for row in range(GRID_ROWS + 1):
        sy = grid_base - row * CELL
        draw_line(MARGIN_LEFT, sy, grid_right, sy, GRID_COLOR)

    # 2. Axes
    draw_line(MARGIN_LEFT, grid_base, grid_right, grid_base, AXIS_COLOR, width=2)
    draw_line(MARGIN_LEFT, grid_base, MARGIN_LEFT, grid_top, AXIS_COLOR, width=2)

    # 3. Axis Labels
    for col in range(0, GRID_COLS + 1, 2):
        sx = MARGIN_LEFT + col * CELL
        s = str(col)
        _draw_string(buf, CANVAS_W, CANVAS_H, sx - len(s) * 3, grid_base + 12, s, AXIS_LBL, scale=1)
    for row in range(0, GRID_ROWS + 1, 2):
        sy = grid_base - row * CELL
        s = str(row)
        _draw_string(buf, CANVAS_W, CANVAS_H, MARGIN_LEFT - 26, sy - 3, s, AXIS_LBL, scale=1)

    # 4. Underlay: Pivot or Arbitrary Axis Line
    if tc.get("axis"):
        (x1, y1), (x2, y2) = tc["axis"]
        sx1, sy1 = _screen_pos(x1, y1)
        sx2, sy2 = _screen_pos(x2, y2)
        # Draw prominent dashed line for arbitrary axis
        draw_line(sx1, sy1, sx2, sy2, PIVOT_COLOR, width=2, dashed=True)
        # Label the axis
        mid_x = (sx1 + sx2) // 2 + 10
        mid_y = (sy1 + sy2) // 2 - 12
        _draw_string(buf, CANVAS_W, CANVAS_H, mid_x, mid_y, f"Arbitrary Axis: ({x1},{y1})->({x2},{y2})", PIVOT_COLOR, scale=1)

    if tc.get("pivot"):
        px, py = tc["pivot"]
        psx, psy = _screen_pos(px, py)
        draw_circle(psx, psy, 7, PIVOT_COLOR)
        label_text = f"Pivot ({px:.1f},{py:.1f})" if tc["type"] != "fixed_point_scaling" else f"Fixed Point ({px:.1f},{py:.1f})"
        _draw_string(buf, CANVAS_W, CANVAS_H, psx + 10, psy - 14, label_text, PIVOT_COLOR, scale=1)

    # 5. Polygons
    original = tc["vertices"]
    transformed, _ = apply_composite_transformation(original, tc["type"], tc["params"])

    n = len(original)
    # Original shape (Blue)
    for i in range(n):
        sx0, sy0 = _screen_pos(original[i][0], original[i][1])
        sx1, sy1 = _screen_pos(original[(i + 1) % n][0], original[(i + 1) % n][1])
        draw_line(sx0, sy0, sx1, sy1, ORIGINAL_COLOR, width=2)
    for (gx, gy) in original:
        sx, sy = _screen_pos(gx, gy)
        draw_circle(sx, sy, POINT_RADIUS, ORIGINAL_COLOR)
        lbl = f"({gx},{gy})"
        _draw_string(buf, CANVAS_W, CANVAS_H, sx + 8, sy - 14, lbl, ORIGINAL_COLOR, scale=1)

    # Transformed shape (Red)
    for i in range(n):
        sx0, sy0 = _screen_pos(transformed[i][0], transformed[i][1])
        sx1, sy1 = _screen_pos(transformed[(i + 1) % n][0], transformed[(i + 1) % n][1])
        draw_line(sx0, sy0, sx1, sy1, TRANSFORMED_COLOR, width=2)
    for (gx, gy) in transformed:
        sx, sy = _screen_pos(gx, gy)
        draw_circle(sx, sy, POINT_RADIUS, TRANSFORMED_COLOR)
        lbl = f"({gx:.1f},{gy:.1f})"
        _draw_string(buf, CANVAS_W, CANVAS_H, sx + 8, sy - 14, lbl, TRANSFORMED_COLOR, scale=1)

    # 6. Header: Title & Legend
    clean_title = tc["label"].replace("—", "-").replace("θ", "theta").replace("°", " deg")
    _draw_string(buf, CANVAS_W, CANVAS_H, MARGIN_LEFT, 26, clean_title, LABEL_COLOR, scale=2)

    # Legend at y = 58
    draw_circle(MARGIN_LEFT + 8, 62, 6, ORIGINAL_COLOR)
    _draw_string(buf, CANVAS_W, CANVAS_H, MARGIN_LEFT + 22, 58, "Original Shape", LABEL_COLOR, scale=1)

    draw_circle(MARGIN_LEFT + 150, 62, 6, TRANSFORMED_COLOR)
    _draw_string(buf, CANVAS_W, CANVAS_H, MARGIN_LEFT + 164, 58, "Transformed Shape", LABEL_COLOR, scale=1)

    if tc.get("pivot") or tc.get("axis"):
        marker_label = "Pivot / Fixed Point" if tc.get("pivot") else "Arbitrary Axis Line"
        draw_circle(MARGIN_LEFT + 320, 62, 6, PIVOT_COLOR)
        _draw_string(buf, CANVAS_W, CANVAS_H, MARGIN_LEFT + 334, 58, marker_label, LABEL_COLOR, scale=1)

    # Rows are already top-to-bottom
    row_stride = CANVAS_W * 3
    rows = [buf[y * row_stride:(y + 1) * row_stride] for y in range(CANVAS_H)]

    _write_png(filepath, CANVAS_W, CANVAS_H, rows)
    print(f"[Generated Image] {filepath}")


def generate_all_outputs():
    """Batch generate uncropped output images for all test cases."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for tc in TEST_CASES:
        out_path = os.path.join(OUTPUT_DIR, tc["file"])
        render_test_case_image(tc, out_path)


# ───────────────────────────────────────────────────────────────────────────
# OpenGL Interactive Visualizer
# ───────────────────────────────────────────────────────────────────────────

def _gl_color(rgb):
    import OpenGL.GL as gl  # type:ignore
    gl.glColor3f(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)


def _draw_gl_filled_circle(cx, cy, radius, segments=20):
    import OpenGL.GL as gl  # type:ignore
    gl.glBegin(gl.GL_TRIANGLE_FAN)
    gl.glVertex2f(cx, cy)
    for i in range(segments + 1):
        angle = 2.0 * math.pi * i / segments
        gl.glVertex2f(cx + radius * math.cos(angle), cy + radius * math.sin(angle))
    gl.glEnd()


def _draw_gl_text(x, y, text, font=None):
    import OpenGL.GL as gl      # type:ignore
    import OpenGL.GLUT as glut  # type:ignore
    if font is None:
        font = glut.__dict__.get("GLUT_BITMAP_HELVETICA_10")
    gl.glRasterPos2f(x, y)
    for ch in text:
        glut.glutBitmapCharacter(font, ord(ch))


def _draw_gl_grid():
    import OpenGL.GL as gl  # type:ignore
    grid_right = MARGIN_LEFT + GRID_COLS * CELL
    grid_top   = MARGIN_BOTTOM + GRID_ROWS * CELL

    # Grid
    _gl_color(GRID_COLOR)
    for col in range(GRID_COLS + 1):
        sx = MARGIN_LEFT + col * CELL
        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(sx, MARGIN_BOTTOM)
        gl.glVertex2f(sx, grid_top)
        gl.glEnd()

    for row in range(GRID_ROWS + 1):
        sy = MARGIN_BOTTOM + row * CELL
        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(MARGIN_LEFT, sy)
        gl.glVertex2f(grid_right, sy)
        gl.glEnd()

    # Axes
    _gl_color(AXIS_COLOR)
    gl.glLineWidth(2.0)
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(MARGIN_LEFT, MARGIN_BOTTOM)
    gl.glVertex2f(grid_right, MARGIN_BOTTOM)
    gl.glEnd()
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(MARGIN_LEFT, MARGIN_BOTTOM)
    gl.glVertex2f(MARGIN_LEFT, grid_top)
    gl.glEnd()
    gl.glLineWidth(1.0)

    # Labels
    _gl_color(AXIS_LBL)
    for col in range(0, GRID_COLS + 1, 2):
        sx = MARGIN_LEFT + col * CELL - 4
        _draw_gl_text(sx, MARGIN_BOTTOM - 18, str(col))
    for row in range(0, GRID_ROWS + 1, 2):
        sy = MARGIN_BOTTOM + row * CELL - 4
        _draw_gl_text(MARGIN_LEFT - 26, sy, str(row))


def _draw_gl_polygon(vertices, color):
    import OpenGL.GL as gl  # type:ignore
    _gl_color(color)
    gl.glLineWidth(2.0)
    gl.glBegin(gl.GL_LINE_LOOP)
    for (gx, gy) in vertices:
        sx = MARGIN_LEFT + gx * CELL
        sy = MARGIN_BOTTOM + gy * CELL
        gl.glVertex2f(sx, sy)
    gl.glEnd()

    for (gx, gy) in vertices:
        sx = MARGIN_LEFT + gx * CELL
        sy = MARGIN_BOTTOM + gy * CELL
        _draw_gl_filled_circle(sx, sy, POINT_RADIUS)
        lbl = f"({gx:.1f},{gy:.1f})" if isinstance(gx, float) else f"({gx},{gy})"
        _draw_gl_text(sx + 8, sy + 6, lbl)
    gl.glLineWidth(1.0)


def _draw_gl_pivot_or_axis(tc):
    import OpenGL.GL as gl  # type:ignore
    if tc.get("pivot"):
        px, py = tc["pivot"]
        sx = MARGIN_LEFT + px * CELL
        sy = MARGIN_BOTTOM + py * CELL
        _gl_color(PIVOT_COLOR)
        _draw_gl_filled_circle(sx, sy, 7)
        _draw_gl_text(sx + 10, sy - 12, f"Pivot ({px:.1f},{py:.1f})")

    if tc.get("axis"):
        (x1, y1), (x2, y2) = tc["axis"]
        sx1 = MARGIN_LEFT + x1 * CELL
        sy1 = MARGIN_BOTTOM + y1 * CELL
        sx2 = MARGIN_LEFT + x2 * CELL
        sy2 = MARGIN_BOTTOM + y2 * CELL
        _gl_color(PIVOT_COLOR)
        gl.glLineWidth(2.0)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(sx1, sy1)
        gl.glVertex2f(sx2, sy2)
        gl.glEnd()
        gl.glLineWidth(1.0)
        _draw_gl_text((sx1 + sx2) / 2 + 10, (sy1 + sy2) / 2 + 5, f"Arbitrary Axis: ({x1},{y1})->({x2},{y2})")


def make_display_func(tc):
    import OpenGL.GL as gl      # type:ignore
    import OpenGL.GLUT as glut  # type:ignore

    def display():
        gl.glClearColor(BG_COLOR[0] / 255.0, BG_COLOR[1] / 255.0, BG_COLOR[2] / 255.0, 1.0)
        gl.glClear(gl.GL_COLOR_BUFFER_BIT)

        _draw_gl_grid()
        _draw_gl_pivot_or_axis(tc)

        original = tc["vertices"]
        transformed, M = apply_composite_transformation(original, tc["type"], tc["params"])

        _draw_gl_polygon(original, ORIGINAL_COLOR)
        _draw_gl_polygon(transformed, TRANSFORMED_COLOR)

        # Title
        _gl_color(LABEL_COLOR)
        title_font = glut.__dict__.get("GLUT_BITMAP_HELVETICA_18", glut.__dict__["GLUT_BITMAP_HELVETICA_10"])
        _draw_gl_text(MARGIN_LEFT, 660, tc["label"], font=title_font)

        # Legend
        _gl_color(ORIGINAL_COLOR)
        _draw_gl_filled_circle(MARGIN_LEFT + 8, 628, 6)
        _gl_color(LABEL_COLOR)
        _draw_gl_text(MARGIN_LEFT + 22, 624, "Original Shape")

        _gl_color(TRANSFORMED_COLOR)
        _draw_gl_filled_circle(MARGIN_LEFT + 150, 628, 6)
        _gl_color(LABEL_COLOR)
        _draw_gl_text(MARGIN_LEFT + 164, 624, "Transformed Shape")

        if tc.get("pivot") or tc.get("axis"):
            name = "Pivot / Fixed Point" if tc.get("pivot") else "Arbitrary Axis Line"
            _gl_color(PIVOT_COLOR)
            _draw_gl_filled_circle(MARGIN_LEFT + 320, 628, 6)
            _gl_color(LABEL_COLOR)
            _draw_gl_text(MARGIN_LEFT + 334, 624, name)

        gl.glFlush()
        glut.glutSwapBuffers()

    return display


def keyboard(key, _x, _y):
    if key in (b'\x1b', b'q', b'Q'):
        sys.exit(0)


def main():
    if "--headless" in sys.argv or "--generate-outputs" in sys.argv:
        generate_all_outputs()
        return

    # Automatically generate crisp uncropped images
    generate_all_outputs()

    import OpenGL.GL as gl      # type:ignore
    import OpenGL.GLUT as glut  # type:ignore
    import OpenGL.GLU as glu    # type:ignore

    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(int(glut.GLUT_DOUBLE) | int(glut.GLUT_RGB))

    for idx, tc in enumerate(TEST_CASES):
        transformed, M = apply_composite_transformation(tc["vertices"], tc["type"], tc["params"])
        print(f"\n{'='*60}")
        print(f"  {tc['label']}")
        print(f"{'='*60}")
        print(f"  Original vertices : {tc['vertices']}")
        print(f"  Transformation    : {tc['type']}")
        print(f"  Parameters        : {tc['params']}")
        print(f"  Composite Matrix:")
        print(format_matrix(M))
        print(f"  Transformed vertices: {[(round(x, 2), round(y, 2)) for x, y in transformed]}")

        glut.glutInitWindowSize(CANVAS_W, CANVAS_H)
        glut.glutInitWindowPosition(60 + idx * 30, 60 + idx * 30)
        glut.glutCreateWindow(tc["label"].encode())

        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        glu.gluOrtho2D(0, CANVAS_W, 0, CANVAS_H)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()

        gl.glEnable(gl.GL_LINE_SMOOTH)
        gl.glEnable(gl.GL_BLEND)
        gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

        glut.glutDisplayFunc(make_display_func(tc))
        glut.glutKeyboardFunc(keyboard)

    print(f"\n[Info] Outputs saved to: {OUTPUT_DIR}")
    print("[Info] Interactive windows opened. Press Esc or Q to exit.\n")
    glut.glutMainLoop()


if __name__ == "__main__":
    main()
