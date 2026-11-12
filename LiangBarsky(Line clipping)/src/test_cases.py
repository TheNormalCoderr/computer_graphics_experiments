"""
test_cases.py — Test case runner and screenshot utility for Liang-Barsky Line Clipping
Uses LiangBarsky(Line clipping)/src/liang_barsky.py without modifying it.

Run interactive:
  python "LiangBarsky(Line clipping)/src/test_cases.py"
Run headless screenshot capture:
  python "LiangBarsky(Line clipping)/src/test_cases.py" --headless
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

import liang_barsky as lb  # type: ignore

# Clipping window corners: (-300, -200) to (300, 200)
WINDOW_CORNERS = [(-300, -200), (300, 200)]

TEST_CASES = {
    1: {
        "label": "TC1 — All Lines Completely Inside",
        "file": "tc1_all_inside.png",
        "window": WINDOW_CORNERS,
        "lines": [
            ((-220, -120), (200, 140)),
            ((-240, 120), (180, -100)),
            ((-150, -150), (220, -150)),
        ],
    },
    2: {
        "label": "TC2 — All Lines Completely Outside",
        "file": "tc2_all_outside.png",
        "window": WINDOW_CORNERS,
        "lines": [
            ((-480, 260), (480, 260)),
            ((-480, -280), (480, -280)),
            ((-500, 50), (-200, 350)),
            ((200, -350), (500, -50)),
        ],
    },
    3: {
        "label": "TC3 — Partially Visible & Spanning Lines",
        "file": "tc3_partial_clipping.png",
        "window": WINDOW_CORNERS,
        "lines": [
            ((-450, -120), (450, 180)),
            ((-100, -40), (140, 280)),
            ((-180, -300), (60, 100)),
        ],
    },
    4: {
        "label": "TC4 — Multi-Orientation Comprehensive Suite",
        "file": "tc4_comprehensive_lines.png",
        "window": WINDOW_CORNERS,
        "lines": [
            ((-150, -320), (-150, 320)),
            ((-480, 60), (480, 60)),
            ((-50, -320), (450, 180)),
            ((40, -120), (220, -40)),
            ((-500, 120), (-200, 360)),
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
    """Populate liang_barsky module globals for the requested test case."""
    global current_case
    current_case = case_num
    tc = TEST_CASES[case_num]
    lb.CLIPPING_WINODW_POINTS.clear()
    lb.CLIPPING_WINODW_POINTS.extend(tc["window"])
    lb.LINE_POINTS.clear()
    for p1, p2 in tc["lines"]:
        lb.LINE_POINTS.append(p1)
        lb.LINE_POINTS.append(p2)

    print(f"\n--- {tc['label']} ---")
    print(f"Lines loaded: {len(tc['lines'])}")


def capture_all_step(step=1, exit_on_done=False):
    if step > len(TEST_CASES):
        print("\n[Done] All 4 Liang-Barsky test case screenshots saved to outputs/")
        if exit_on_done:
            os._exit(0)
        load_test_case(1)
        glut.glutPostRedisplay()
        return

    load_test_case(step)
    lb.display()
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
        lb.keyboard(key, x, y)


def main():
    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_SINGLE | glut.GLUT_RGB)  # type: ignore
    glut.glutInitWindowSize(lb.CANVAS_WIDTH, lb.CANVAS_HEIGHT)
    glut.glutCreateWindow("Liang-Barsky Line Clipping Visualization")

    lb.initWindow()
    load_test_case(1)

    glut.glutDisplayFunc(lb.display)
    glut.glutKeyboardFunc(keyboard_handler)
    glut.glutMouseFunc(lb.mouse)

    headless = any(arg in sys.argv for arg in ("--headless", "--capture", "--batch", "-c"))
    if headless:
        glut.glutTimerFunc(250, lambda v: capture_all_step(1, exit_on_done=True), 0)

    glut.glutMainLoop()


if __name__ == "__main__":
    main()
