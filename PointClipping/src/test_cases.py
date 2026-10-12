import os
import sys
import OpenGL.GL as gl
import OpenGL.GLUT as glut

# add repository root to sys.path to access the shared app canvas
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.src import line_drawing_app as lda

OUTPUT_DIR = os.path.join(REPO_ROOT, "PointClipping", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# clipping window boundaries
XMIN, YMIN = 100, 100
XMAX, YMAX = 400, 300

# 4 benchmark test cases covering interior, exterior, mixed, and boundary points
TEST_CASES = {
    1: {
        "label": "TC1 — All Points Inside",
        "file": "tc1_all_inside.png",
        "points": [(150, 150), (250, 200), (350, 250), (200, 280)],
    },
    2: {
        "label": "TC2 — All Points Outside",
        "file": "tc2_all_outside.png",
        "points": [(50, 50), (450, 350), (250, 350), (50, 200), (250, 50)],
    },
    3: {
        "label": "TC3 — Mixed Inside and Outside",
        "file": "tc3_mixed.png",
        "points": [(60, 150), (200, 150), (300, 250), (450, 200), (250, 50)],
    },
    4: {
        "label": "TC4 — Boundary, Corner, and Adjacent Points",
        "file": "tc4_on_boundary.png",
        "points": [
            (100, 100), (400, 300), (250, 100), (100, 200),
            (400, 150), (250, 300), (99, 200), (250, 301)
        ],
    },
}

current_case = 1


def clip_point(x, y):
    # point is saved if it lies inside or right on the boundary
    return XMIN <= x <= XMAX and YMIN <= y <= YMAX


def load_test_case(case_num):
    # setup the app's point clipping mode with the given test case
    global current_case
    current_case = case_num
    tc = TEST_CASES[case_num]

    lda.CURRENT_ALGORITHM = "Point Clipping"
    lda.POINT_CLIPPING_WINDOW["xmin"] = str(XMIN)
    lda.POINT_CLIPPING_WINDOW["ymin"] = str(YMIN)
    lda.POINT_CLIPPING_WINDOW["xmax"] = str(XMAX)
    lda.POINT_CLIPPING_WINDOW["ymax"] = str(YMAX)
    lda.POINT_CLIPPING_POINTS.clear()

    # center canvas around the clipping window and test points
    lda.CANVAS_OFFSET_X = 170.0
    lda.CANVAS_OFFSET_Y = 190.0
    lda.CANVAS_SCALE = 1.0

    print(f"\n--- {tc['label']} ---")
    for px, py in tc["points"]:
        lda.test_clip_point(px, py)


def save_current_case_screenshot():
    # render frame and save screenshot to outputs folder
    tc = TEST_CASES[current_case]
    lda.display()
    gl.glReadBuffer(gl.GL_FRONT)
    filepath = os.path.join(OUTPUT_DIR, tc["file"])
    lda.save_framebuffer(filepath, lda.CURRENT_WIDTH, lda.CURRENT_HEIGHT)
    print(f"[Screenshot Saved] {tc['label']} -> {filepath}")


def capture_all_step(step=1, exit_on_done=False):
    # step through all 4 test cases and capture screenshots automatically
    if step > 4:
        print("\n[Done] All 4 test case screenshots saved from the app canvas to outputs/")
        if exit_on_done:
            os._exit(0)
        # return to test case 1 for interactive use
        load_test_case(1)
        glut.glutPostRedisplay()
        return

    load_test_case(step)
    save_current_case_screenshot()
    glut.glutTimerFunc(120, lambda v: capture_all_step(step + 1, exit_on_done), 0)


def test_cases_keyboard(key, x, y):
    # allow pressing 1-4 to switch test cases, 's' to re-save all, and delegate others
    try:
        ch = key.decode("utf-8")
    except Exception:
        ch = ""

    if ch in "1234":
        load_test_case(int(ch))
        glut.glutPostRedisplay()
    elif ch in ("s", "S"):
        print("\nCapturing screenshots for all 4 test cases...")
        capture_all_step(1, exit_on_done=False)
    else:
        # pass all other inputs to the app's default keyboard handler
        lda.keyboard(key, x, y)


def main():
    # initialize GLUT window with the studio app's canvas
    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_DOUBLE | glut.GLUT_RGB)
    glut.glutInitWindowSize(lda.DEFAULT_WIDTH, lda.DEFAULT_HEIGHT)
    glut.glutCreateWindow(b"Point Clipping - Test Cases on Canvas")
    gl.glClearColor(*lda.CANVAS_BG_COLOR)

    # register app callbacks
    glut.glutReshapeFunc(lda.reshape)
    glut.glutDisplayFunc(lda.display)
    glut.glutKeyboardFunc(test_cases_keyboard)
    glut.glutSpecialFunc(lda.special_keyboard)
    glut.glutMouseFunc(lda.mouse)
    glut.glutMotionFunc(lda.motion)
    glut.glutPassiveMotionFunc(lda.passive_motion)

    # load initial test case
    load_test_case(1)

    print("\n[Point Clipping Test Runner]")
    print("  Keys 1-4 : Switch between test cases on the app canvas")
    print("  Key 'S'  : Capture all 4 screenshots to PointClipping/outputs/")
    print("  Key 'C'  : Clear plotted points")
    print("  Canvas   : Click directly on canvas or use panel to clip custom points")

    # check if user ran with capture or headless flag
    batch_mode = any(arg in sys.argv for arg in ("--capture", "--headless", "--batch", "-c"))
    if batch_mode:
        print("Running in batch capture mode...")
        glut.glutTimerFunc(200, lambda v: capture_all_step(1, exit_on_done=True), 0)
    else:
        # save all 4 screenshots once on start, then stay open for interaction
        glut.glutTimerFunc(200, lambda v: capture_all_step(1, exit_on_done=False), 0)

    glut.glutMainLoop()


if __name__ == "__main__":
    main()
