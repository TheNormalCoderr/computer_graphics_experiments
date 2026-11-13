"""
test_cases.py — Test case runner and screenshot utility for B-Spline Curve
Uses B-Spline/outputs/src/BSpline.py without modifying it.

Run interactive:
  python "B-Spline/src/test_cases.py"
Run headless screenshot capture:
  python "B-Spline/src/test_cases.py" --headless
"""

import os
import struct
import sys
import zlib
import OpenGL.GL as gl
import OpenGL.GLUT as glut

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXP_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUTPUT_DIR = os.path.join(EXP_DIR, "outputs")
BSPLINE_SRC_DIR = os.path.join(EXP_DIR, "outputs", "src")
os.makedirs(OUTPUT_DIR, exist_ok=True)

if BSPLINE_SRC_DIR not in sys.path:
    sys.path.insert(0, BSPLINE_SRC_DIR)

import BSpline as bs  # type: ignore

TEST_CASES = {
    1: {
        "label": "TC1 — Minimal Quadratic B-Spline (3 Control Points, No Internal Knots)",
        "file": "tc1_minimal_quadratic_bspline.png",
        "points": [(-350, -150), (0, 280), (350, -150)],
    },
    2: {
        "label": "TC2 — Four-Point Quadratic B-Spline S-Curve (1 Internal Knot)",
        "file": "tc2_four_point_bspline.png",
        "points": [(-400, -200), (-150, 280), (150, -280), (400, 200)],
    },
    3: {
        "label": "TC3 — Multi-Segment Wave B-Spline (6 Control Points, 4 Quadratic Spans)",
        "file": "tc3_multi_segment_wave.png",
        "points": [(-450, -120), (-270, 240), (-90, -220), (90, 240), (270, -220), (450, 120)],
    },
    4: {
        "label": "TC4 — Local Control Demonstration (7 Control Points with Sharp Peak)",
        "file": "tc4_local_control_peak.png",
        "points": [(-450, -100), (-300, -100), (-150, 280), (0, -100), (150, -100), (300, 180), (450, -100)],
    },
}

current_case = 1


def _write_png(filepath, width, height, rows):
    """Write RGB scanline rows to a PNG file using standard library zlib/struct."""
    def make_chunk(chunk_type, data):
        chunk = chunk_type + data
        return (
            struct.pack(">I", len(data))
            + chunk
            + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
        )

    raw_data = b"".join(b"\x00" + row for row in rows)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"
        + make_chunk(b"IHDR", ihdr)
        + make_chunk(b"IDAT", zlib.compress(raw_data, 9))
        + make_chunk(b"IEND", b"")
    )
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(png_bytes)


def save_framebuffer(filepath):
    """Capture the current OpenGL front buffer and save as PNG."""
    gl.glFinish()
    gl.glReadBuffer(gl.GL_FRONT)
    gl.glPixelStorei(gl.GL_PACK_ALIGNMENT, 1)
    vp = gl.glGetIntegerv(gl.GL_VIEWPORT)
    width, height = int(vp[2]), int(vp[3])
    data = gl.glReadPixels(0, 0, width, height, gl.GL_RGB, gl.GL_UNSIGNED_BYTE)
    raw = data if isinstance(data, bytes) else bytes(data)
    row_size = width * 3
    rows = [raw[y * row_size : (y + 1) * row_size] for y in range(height - 1, -1, -1)]
    _write_png(filepath, width, height, rows)


def load_test_case(case_num):
    """Populate BSpline module globals for the requested test case."""
    global current_case
    current_case = case_num
    tc = TEST_CASES[case_num]
    bs.CONTROL_POINTS.clear()
    bs.CONTROL_POINTS.extend(tc["points"])

    degree = 2
    n = len(tc["points"])
    knots = bs.getKnotVector(degree, n)
    curve_pts = bs.getCurvePoints()
    mid_pt = curve_pts[len(curve_pts) // 2] if curve_pts else (0.0, 0.0)
    print(f"\n--- {tc['label']} ---")
    print(f"Control points ({n}): {tc['points']}")
    print(f"Degree: {degree} | Knot vector ({len(knots)}): {knots}")
    print(f"Sampled curve points: {len(curve_pts)} | Start: {curve_pts[0]} | Mid: ({mid_pt[0]:.2f}, {mid_pt[1]:.2f}) | End: {curve_pts[-1]}")


def capture_all_step(step=1, exit_on_done=False):
    if step > len(TEST_CASES):
        print("\n[Done] All 4 B-Spline Curve test case screenshots saved to outputs/")
        if exit_on_done:
            os._exit(0)
        load_test_case(1)
        glut.glutPostRedisplay()
        return

    load_test_case(step)
    bs.display()
    filepath = os.path.join(OUTPUT_DIR, TEST_CASES[step]["file"])
    save_framebuffer(filepath)
    print(f"[Saved] {filepath}")
    glut.glutTimerFunc(150, lambda v: capture_all_step(step + 1, exit_on_done), 0)


def keyboard_handler(key, x, y):
    if key in (b"1", b"2", b"3", b"4"):
        load_test_case(int(key.decode("utf-8")))
        glut.glutPostRedisplay()
    elif key in (b"s", b"S"):
        capture_all_step(1, exit_on_done=False)
    else:
        bs.keyboard(key, x, y)


def main():
    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_SINGLE | glut.GLUT_RGB)  # type: ignore
    glut.glutInitWindowSize(bs.CANVAS_WIDTH, bs.CANVAS_HEIGHT)
    glut.glutCreateWindow("B-Spline Curve Visualization")

    bs.initWindow()
    load_test_case(1)

    glut.glutDisplayFunc(bs.display)
    glut.glutKeyboardFunc(keyboard_handler)
    glut.glutMouseFunc(bs.mouse)
    glut.glutMotionFunc(bs.motion)

    headless = any(arg in sys.argv for arg in ("--headless", "--capture", "--batch", "-c"))
    if headless:
        glut.glutTimerFunc(250, lambda v: capture_all_step(1, exit_on_done=True), 0)

    glut.glutMainLoop()


if __name__ == "__main__":
    main()
