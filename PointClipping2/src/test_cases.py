"""
test_cases.py — Test case runner and screenshot utility for PointClipping2
Uses PointClipping2/src/point_clipping.py without modifying it.

Run interactive:
  python PointClipping2/src/test_cases.py
Run headless screenshot capture:
  python PointClipping2/src/test_cases.py --headless
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
os.makedirs(OUTPUT_DIR, exist_ok=True)

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import point_clipping as pc  # type: ignore

# Clipping window corners: (-300, -200) to (300, 200)
WINDOW_CORNERS = [(-300, -200), (300, 200)]

TEST_CASES = {
    1: {
        "label": "TC1 — All Points Inside",
        "file": "tc1_all_inside.png",
        "window": WINDOW_CORNERS,
        "points": [
            (-200, 120),
            (-100, -100),
            (0, 50),
            (150, 130),
            (220, -120),
            (-50, 150),
        ],
    },
    2: {
        "label": "TC2 — All Points Outside",
        "file": "tc2_all_outside.png",
        "window": WINDOW_CORNERS,
        "points": [
            (-450, 100),
            (450, -100),
            (-150, 300),
            (150, -300),
            (-420, -280),
            (420, 280),
        ],
    },
    3: {
        "label": "TC3 — Mixed Inside and Outside",
        "file": "tc3_mixed.png",
        "window": WINDOW_CORNERS,
        "points": [
            (-180, 100),
            (160, 110),
            (-120, -110),
            (180, -90),
            (-420, 150),
            (420, 120),
            (-200, -290),
            (200, 290),
        ],
    },
    4: {
        "label": "TC4 — Boundary, Corner, and Exterior-Adjacent Points",
        "file": "tc4_on_boundary.png",
        "window": WINDOW_CORNERS,
        "points": [
            (-300, -200),
            (300, 200),
            (-300, 100),
            (300, -100),
            (0, 200),
            (0, -200),
            (-315, 0),
            (0, 215),
        ],
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
    """Populate point_clipping module globals for the requested test case."""
    global current_case
    current_case = case_num
    tc = TEST_CASES[case_num]
    pc.CLIPPING_WINODW_POINTS.clear()
    pc.CLIPPING_WINODW_POINTS.extend(tc["window"])
    pc.POINTS.clear()
    pc.POINTS.extend(tc["points"])

    x_min = min(tc["window"][0][0], tc["window"][1][0])
    x_max = max(tc["window"][0][0], tc["window"][1][0])
    y_min = min(tc["window"][0][1], tc["window"][1][1])
    y_max = max(tc["window"][0][1], tc["window"][1][1])

    accepted = sum(1 for x, y in tc["points"] if pc.isValidPoint(x, y, x_min, x_max, y_min, y_max))
    rejected = len(tc["points"]) - accepted
    print(f"\n--- {tc['label']} ---")
    print(f"Window: [{x_min}, {y_min}] to [{x_max}, {y_max}]")
    print(f"Total: {len(tc['points'])} | Accepted (Green): {accepted} | Rejected (Red): {rejected}")


def capture_all_step(step=1, exit_on_done=False):
    if step > len(TEST_CASES):
        print("\n[Done] All 4 PointClipping2 test case screenshots saved to outputs/")
        if exit_on_done:
            os._exit(0)
        load_test_case(1)
        glut.glutPostRedisplay()
        return

    load_test_case(step)
    pc.display()
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
        pc.keyboard(key, x, y)


def main():
    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_SINGLE | glut.GLUT_RGB)  # type: ignore
    glut.glutInitWindowSize(pc.CANVAS_WIDTH, pc.CANVAS_HEIGHT)
    glut.glutCreateWindow("Point Clipping Visualization")

    pc.initWindow()
    load_test_case(1)

    glut.glutDisplayFunc(pc.display)
    glut.glutKeyboardFunc(keyboard_handler)
    glut.glutMouseFunc(pc.mouse)

    headless = any(arg in sys.argv for arg in ("--headless", "--capture", "--batch", "-c"))
    if headless:
        glut.glutTimerFunc(250, lambda v: capture_all_step(1, exit_on_done=True), 0)

    glut.glutMainLoop()


if __name__ == "__main__":
    main()
