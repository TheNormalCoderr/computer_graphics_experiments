import os
import sys

# add project root to path so we can import the shared studio app
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.src import line_drawing_app as lda


def clip_point(x, y, xmin=100, ymin=100, xmax=400, ymax=300):
    # point is saved if it lies inside or on the window boundary
    return xmin <= x <= xmax and ymin <= y <= ymax


def main():
    print("[Point Clipping] Launching studio app with Point Clipping feature enabled.")
    print("  Configure the 4 window boundaries in the input section on the canvas.")
    print("  Click anywhere on the canvas or type point coordinates to test clipping.")

    # pre-select Point Clipping algorithm in the main studio app
    lda.CURRENT_ALGORITHM = "Point Clipping"
    lda.run()


if __name__ == "__main__":
    main()
