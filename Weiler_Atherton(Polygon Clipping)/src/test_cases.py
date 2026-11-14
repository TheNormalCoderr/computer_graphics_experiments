"""
test_cases.py — Test case runner and screenshot utility for Weiler-Atherton Polygon Clipping
Uses Weiler_Atherton(Polygon Clipping)/src/WeilerAtherton.py without modifying it.

Run interactive:
  python "Weiler_Atherton(Polygon Clipping)/src/test_cases.py"
Run headless screenshot capture:
  python "Weiler_Atherton(Polygon Clipping)/src/test_cases.py" --headless
"""

import os
import struct
import sys
import zlib
import OpenGL.GL as gl
import OpenGL.GLUT as glut

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EXP_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
OUTPUT_DIR = os.path.join(EXP_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import WeilerAtherton as wa  # type: ignore

RECT_WINDOW = [(-300, -200), (300, -200), (300, 200), (-300, 200)]
PENTAGON_WINDOW = [(-250, -180), (250, -180), (320, 80), (0, 260), (-320, 80)]
OFFSET_RECT_WINDOW = [(-250, -150), (100, -150), (100, 150), (-250, 150)]

TEST_CASES = {
    1: {
        "label": "TC1 — CLIP: Concave Polygon Splitting into Two Disjoint Polygons",
        "file": "tc1_clip_concave_disjoint_split.png",
        "operation": "CLIP",
        "window": RECT_WINDOW,
        "vertices": [
            (-260, 300),
            (260, 300),
            (180, -100),
            (30, 260),
            (-30, 260),
            (-180, -100),
        ],
    },
    2: {
        "label": "TC2 — CLIP: Concave Chevron Against Pentagonal Clipping Window",
        "file": "tc2_clip_pentagon_concave.png",
        "operation": "CLIP",
        "window": PENTAGON_WINDOW,
        "vertices": [
            (-240, 120),
            (0, 40),
            (240, 120),
            (280, -280),
            (120, -280),
            (0, -40),
            (-120, -280),
            (-280, -280),
        ],
    },
    3: {
        "label": "TC3 — UNION: Overlapping Polygons with Mixed Winding Order",
        "file": "tc3_union_mixed_winding.png",
        "operation": "UNION",
        "window": OFFSET_RECT_WINDOW,
        "vertices": [
            (-50, -220),
            (-50, 80),
            (280, 80),
            (280, -220),
        ],
    },
    4: {
        "label": "TC4 — DIFFERENCE: Clipping Polygon Inside Subject Polygon (Hole)",
        "file": "tc4_difference_hole.png",
        "operation": "DIFFERENCE",
        "window": [
            (-120, -100),
            (120, -100),
            (120, 100),
            (-120, 100),
        ],
        "vertices": [
            (-280, -220),
            (280, -220),
            (280, 220),
            (-280, 220),
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
    """Populate WeilerAtherton module globals for the requested test case."""
    global current_case
    current_case = case_num
    tc = TEST_CASES[case_num]
    wa.CLIPPING_WINDOW_POINTS.clear()
    wa.CLIPPING_WINDOW_POINTS.extend(tc["window"])
    wa.POLYGON_POINTS.clear()
    wa.POLYGON_POINTS.extend(tc["vertices"])
    wa.CURRENT_OPERATION = tc["operation"]
    wa.PHASE = "DONE"

    print(f"\n--- {tc['label']} ---")
    print(f"Operation: {tc['operation']}")
    print(f"Clipping window ({len(tc['window'])}): {tc['window']}")
    print(f"Subject vertices ({len(tc['vertices'])}): {tc['vertices']}")


def capture_all_step(step=1, exit_on_done=False):
    if step > len(TEST_CASES):
        print("\n[Done] All 4 Weiler-Atherton test case screenshots saved to output/")
        if exit_on_done:
            os._exit(0)
        load_test_case(1)
        glut.glutPostRedisplay()
        return

    load_test_case(step)
    wa.display()
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
        wa.keyboard(key, x, y)


def main():
    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_SINGLE | glut.GLUT_RGB)  # type: ignore
    glut.glutInitWindowSize(wa.CANVAS_WIDTH, wa.CANVAS_HEIGHT)
    glut.glutCreateWindow("Weiler Atherton (Polygon Clipping) Visualization")

    wa.initWindow()
    load_test_case(1)

    glut.glutDisplayFunc(wa.display)
    glut.glutKeyboardFunc(keyboard_handler)
    glut.glutMouseFunc(wa.mouse)

    headless = any(arg in sys.argv for arg in ("--headless", "--capture", "--batch", "-c"))
    if headless:
        glut.glutTimerFunc(250, lambda v: capture_all_step(1, exit_on_done=True), 0)

    glut.glutMainLoop()


if __name__ == "__main__":
    main()
