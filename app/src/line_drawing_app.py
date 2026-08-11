import os
import sys
import json
import math
import struct
import zlib
import glob

import OpenGL.GL as gl     #type:ignore
import OpenGL.GLUT as glut #type:ignore
import OpenGL.GLU as glu   #type:ignore

# ── Add repo root to sys.path so we can import algorithm modules ─────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR    = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
REPO_ROOT  = os.path.abspath(os.path.join(APP_DIR, ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from SimpleDDA.src.simple_dda import dda_points                                      #type:ignore
from SymmetricDDA.src.symmetric_dda import symmetric_dda_points, unique_points        #type:ignore
from Brestenham.src.bresenham import bresenham_points                                 #type:ignore


# ============================================================================
# Window Configuration
# ============================================================================

DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 800

CURRENT_WIDTH = DEFAULT_WIDTH
CURRENT_HEIGHT = DEFAULT_HEIGHT


# ============================================================================
# Menu Configuration
# ============================================================================

MENU_HEIGHT = 40
MENU_BG_COLOR = (0.22, 0.22, 0.25)
MENU_ITEM_COLOR = (0.35, 0.35, 0.38)
MENU_TEXT_COLOR = (0.92, 0.92, 0.92)
MENU_HOVER_COLOR = (0.40, 0.40, 0.45)

MENU_LIST = [
    "Line Drawing Algorithm",
    "Line Parameters",
    "Import File",
    "Options",
]

# Dropdown configuration
DROPDOWN_ITEM_HEIGHT = 30
DROPDOWN_WIDTH = 200
DROPDOWN_BG_COLOR = (0.20, 0.20, 0.23)
DROPDOWN_HOVER_COLOR = (0.35, 0.35, 0.40)
DROPDOWN_TEXT_COLOR = (0.90, 0.90, 0.90)

ALGORITHM_ITEMS = [
    "Simple DDA",
    "Symmetric DDA",
    "Bresenham",
]

LINE_PARAMETERS_ITEMS = [
    "Color",
    "Line Width",
    "Solid Line",
    "Dotted Line",
    "Dashed Line",
]

COLOR_ITEMS = [
    "Red",
    "Green",
    "Blue",
    "Black",
    "White",
    "Yellow",
]

WIDTH_ITEMS = [
    "1",
    "2",
    "3",
    "4",
    "5",
]

OPTIONS_ITEMS = [
    "Clear",
    "Save",
    "Exit",
]

MENU_DROPDOWN = {
    "Line Drawing Algorithm": ALGORITHM_ITEMS,
    "Line Parameters": LINE_PARAMETERS_ITEMS,
    "Options": OPTIONS_ITEMS,
}

# Sub-dropdown mapping (for Line Parameters items that need a second level)
SUB_DROPDOWN = {
    "Color": COLOR_ITEMS,
    "Line Width": WIDTH_ITEMS,
}

# Currently opened menu / sub-menu
OPEN_MENU = None
OPEN_SUB_MENU = None


# ============================================================================
# Drawing State
# ============================================================================

# Color name → RGB (0.0-1.0)
COLOR_MAP = {
    "Red":    (1.0, 0.0, 0.0),
    "Green":  (0.0, 0.7, 0.0),
    "Blue":   (0.0, 0.0, 1.0),
    "Black":  (0.0, 0.0, 0.0),
    "White":  (1.0, 1.0, 1.0),
    "Yellow": (1.0, 1.0, 0.0),
}

# Current drawing settings (defaults per spec)
CURRENT_ALGORITHM = "Bresenham"
CURRENT_COLOR = "Red"
CURRENT_LINE_WIDTH = 1
CURRENT_LINE_STYLE = "Solid"   # "Solid", "Dotted", "Dashed"

# Point selection state
selected_points = []    # list of (x_world, y_world) — max 2

# All drawn lines (persisted until Clear)
# Each entry: {
#   "p1": (x, y),
#   "p2": (x, y),
#   "algorithm": str,
#   "color": str,
#   "width": int,
#   "style": str,
#   "line_points": [(x, y), ...],
# }
drawn_lines = []

# Import file list (populated when Import File dropdown is opened)
import_file_list = []

# Saved drawings folder
SAVED_DIR = os.path.join(APP_DIR, "saved_drawings")
OUTPUT_DIR = os.path.join(APP_DIR, "output")


# ============================================================================
# Canvas Configuration
# ============================================================================

CANVAS_BG_COLOR = (0.96, 0.96, 0.97, 1.0)

GRID_SIZE = 20
GRID_LINE_COLOR = (0.82, 0.82, 0.84)
GRID_LINE_THICKNESS = 1

ORIGIN_LINE_COLOR = (0.15, 0.15, 0.15)
ORIGIN_LINE_THICKNESS = 2

TICK_LABEL_COLOR = (0.4, 0.4, 0.4)
POINT_MARKER_COLOR = (1.0, 0.3, 0.3)
POINT_MARKER_RADIUS = 4


# ============================================================================
# Minimal PNG writer (same pattern as DDA files)
# ============================================================================

def _write_png(filepath, width, height, rgb_rows):
    """
    Write an RGB PNG from a list of rows (top-to-bottom).
    """
    def _chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = _chunk(b'IHDR', ihdr_data)

    raw = b''
    for row in rgb_rows:
        raw += b'\x00' + bytes(row)
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


# ============================================================================
# Algorithm dispatch
# ============================================================================

def round_half_up(n):
    """
    Standard rounding away from zero for half-way points, avoiding Python's
    default Banker's rounding which causes visual line staggering.
    """
    return math.floor(n + 0.5)

def compute_line_points(algorithm, x1, y1, x2, y2):
    """
    Call the selected algorithm and return a list of (int, int) pixel positions.
    """
    if algorithm == "Simple DDA":
        return dda_points(x1, y1, x2, y2)
    elif algorithm == "Symmetric DDA":
        raw = symmetric_dda_points(x1, y1, x2, y2)
        return unique_points(raw)
    elif algorithm == "Bresenham":
        return bresenham_points(x1, y1, x2, y2)
    else:
        # Fallback to Bresenham
        return bresenham_points(x1, y1, x2, y2)

def add_line(x1, y1, x2, y2, algorithm="Bresenham", color="Red", width=1, style="Solid"):
    """
    Utility function to programmatically add a line to the canvas.
    """
    global drawn_lines
    pts = compute_line_points(algorithm, x1, y1, x2, y2)
    drawn_lines.append({
        "p1": (x1, y1),
        "p2": (x2, y2),
        "algorithm": algorithm,
        "color": color,
        "width": width,
        "style": style,
        "line_points": pts
    })


# ============================================================================
# Keyboard Input
# ============================================================================

def keyboard(key, x, y):
    """
    Handle keyboard input.
    """

    # Escape key
    if key == b'\x1b':
        os._exit(0)

    # 'p' — save screenshot to output/
    if key in (b'p', b'P'):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        # Generate a timestamped filename
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(OUTPUT_DIR, f"screenshot_{ts}.png")
        save_framebuffer(filepath, CURRENT_WIDTH, CURRENT_HEIGHT)
        print(f"[Screenshot] Saved → {filepath}")


# ============================================================================
# Mouse Input
# ============================================================================

def get_menu_item_bounds_px(index):
    """
    Return the left and right pixel boundaries of a menu item
    in window (GLUT) coordinates.
    """
    menu_item_width = CURRENT_WIDTH / len(MENU_LIST)
    left = index * menu_item_width
    right = left + menu_item_width
    return left, right


def handle_menu_click(x, y):
    """
    Handle clicks on the top menu bar.
    x, y are in GLUT window coordinates (top-left origin).
    """

    global OPEN_MENU, OPEN_SUB_MENU

    for index, item in enumerate(MENU_LIST):

        left, right = get_menu_item_bounds_px(index)

        if left <= x <= right:

            # Clicking the currently open menu closes it.
            if OPEN_MENU == item:
                OPEN_MENU = None
                OPEN_SUB_MENU = None

            # Otherwise, open the selected menu.
            else:
                OPEN_MENU = item
                OPEN_SUB_MENU = None

                # If Import File is clicked, refresh the file list
                if item == "Import File":
                    _refresh_import_list()

            glut.glutPostRedisplay()
            return


def _refresh_import_list():
    """
    Scan saved_drawings/ for JSON files and populate import_file_list.
    """
    global import_file_list
    import_file_list = []
    if os.path.isdir(SAVED_DIR):
        files = sorted(glob.glob(os.path.join(SAVED_DIR, "*.json")), reverse=True)
        for f in files:
            import_file_list.append(os.path.basename(f))


def handle_dropdown_click(x, y):
    """
    Handle clicks on open dropdown menus.
    x, y are in GLUT window coordinates (top-left origin).
    Returns True if the click was consumed by a dropdown.
    """

    global OPEN_MENU, OPEN_SUB_MENU
    global CURRENT_ALGORITHM, CURRENT_COLOR, CURRENT_LINE_WIDTH, CURRENT_LINE_STYLE

    if OPEN_MENU is None:
        return False

    # Find which menu item the dropdown belongs to
    menu_index = None
    for i, item in enumerate(MENU_LIST):
        if item == OPEN_MENU:
            menu_index = i
            break

    if menu_index is None:
        return False

    # Get dropdown items
    if OPEN_MENU == "Import File":
        dropdown_items = import_file_list if import_file_list else ["(no saved files)"]
    else:
        dropdown_items = MENU_DROPDOWN.get(OPEN_MENU, [])

    if not dropdown_items:
        return False

    # Calculate dropdown position (in GLUT window coordinates)
    menu_left, menu_right = get_menu_item_bounds_px(menu_index)
    dd_left = menu_left
    dd_right = dd_left + DROPDOWN_WIDTH
    dd_top = MENU_HEIGHT
    dd_bottom = dd_top + len(dropdown_items) * DROPDOWN_ITEM_HEIGHT

    # ── IMPORTANT: Check sub-dropdown FIRST ─────────────────────────────
    # If a sub-dropdown is open, check it before the parent dropdown.
    # Otherwise clicking a sub-item that overlaps the parent area
    # gets consumed by the parent handler and never reaches here.
    if OPEN_SUB_MENU and OPEN_SUB_MENU in SUB_DROPDOWN:
        sub_items = SUB_DROPDOWN[OPEN_SUB_MENU]

        # Find the index of the parent item in the dropdown
        parent_index = None
        parent_items = MENU_DROPDOWN.get(OPEN_MENU, [])
        for pi, pitem in enumerate(parent_items):
            if pitem == OPEN_SUB_MENU:
                parent_index = pi
                break

        if parent_index is not None:
            # Sub-dropdown appears to the right of the parent dropdown
            sub_left = dd_right
            sub_right = sub_left + DROPDOWN_WIDTH
            sub_top = dd_top + parent_index * DROPDOWN_ITEM_HEIGHT
            sub_bottom = sub_top + len(sub_items) * DROPDOWN_ITEM_HEIGHT

            if sub_left <= x <= sub_right and sub_top <= y <= sub_bottom:
                sub_index = int((y - sub_top) / DROPDOWN_ITEM_HEIGHT)
                if 0 <= sub_index < len(sub_items):
                    sub_clicked = sub_items[sub_index]

                    if OPEN_SUB_MENU == "Color":
                        CURRENT_COLOR = sub_clicked
                        print(f"[Color] Selected: {CURRENT_COLOR}")
                    elif OPEN_SUB_MENU == "Line Width":
                        CURRENT_LINE_WIDTH = int(sub_clicked)
                        print(f"[Width] Selected: {CURRENT_LINE_WIDTH}")

                    OPEN_MENU = None
                    OPEN_SUB_MENU = None

                glut.glutPostRedisplay()
                return True

    # ── Check if click is within the main dropdown ──────────────────────
    if dd_left <= x <= dd_right and dd_top <= y <= dd_bottom:
        # Determine which item was clicked
        item_index = int((y - dd_top) / DROPDOWN_ITEM_HEIGHT)
        if 0 <= item_index < len(dropdown_items):
            clicked_item = dropdown_items[item_index]

            # Handle based on which menu we're in
            if OPEN_MENU == "Line Drawing Algorithm":
                CURRENT_ALGORITHM = clicked_item
                print(f"[Algorithm] Selected: {CURRENT_ALGORITHM}")
                OPEN_MENU = None
                OPEN_SUB_MENU = None

            elif OPEN_MENU == "Line Parameters":
                # Check if this item has a sub-dropdown
                if clicked_item in SUB_DROPDOWN:
                    if OPEN_SUB_MENU == clicked_item:
                        OPEN_SUB_MENU = None
                    else:
                        OPEN_SUB_MENU = clicked_item
                elif clicked_item == "Solid Line":
                    CURRENT_LINE_STYLE = "Solid"
                    print(f"[Style] Selected: Solid")
                    OPEN_MENU = None
                    OPEN_SUB_MENU = None
                elif clicked_item == "Dotted Line":
                    CURRENT_LINE_STYLE = "Dotted"
                    print(f"[Style] Selected: Dotted")
                    OPEN_MENU = None
                    OPEN_SUB_MENU = None
                elif clicked_item == "Dashed Line":
                    CURRENT_LINE_STYLE = "Dashed"
                    print(f"[Style] Selected: Dashed")
                    OPEN_MENU = None
                    OPEN_SUB_MENU = None

            elif OPEN_MENU == "Options":
                if clicked_item == "Clear":
                    _do_clear()
                    OPEN_MENU = None
                    OPEN_SUB_MENU = None
                elif clicked_item == "Save":
                    _do_save()
                    OPEN_MENU = None
                    OPEN_SUB_MENU = None
                elif clicked_item == "Exit":
                    print("[Exit] Goodbye.")
                    os._exit(0)

            elif OPEN_MENU == "Import File":
                if clicked_item != "(no saved files)":
                    _do_import(clicked_item)
                OPEN_MENU = None
                OPEN_SUB_MENU = None

        glut.glutPostRedisplay()
        return True

    return False


def _get_pixel_ratio():
    """
    Detect the pixel ratio (Retina scaling) on macOS.
    On Retina displays, the framebuffer is 2x the window size in points.
    """
    try:
        fb_width = gl.glGetIntegerv(gl.GL_VIEWPORT)[2]
        win_width = glut.glutGet(glut.GLUT_WINDOW_WIDTH)
        if win_width > 0:
            return fb_width / win_width
    except Exception:
        pass
    return 1.0


def handle_canvas_click(x, y):
    """
    Handle clicks on the drawing canvas.

    Converts GLUT mouse coordinates into Cartesian world coordinates
    and snaps to the nearest grid intersection.
    """

    global selected_points

    # Convert window coordinates to Cartesian coordinates.
    # GLUT y is top-down, canvas starts below menu.
    #
    # The canvas viewport is: glViewport(0, 0, canvas_width, canvas_height)
    # which occupies the bottom canvas_height pixels of the window.
    #
    # GLUT gives mouse coords with origin at top-left.
    # OpenGL viewport has origin at bottom-left.
    #
    # viewport_y = CURRENT_HEIGHT - y  (convert top-down to bottom-up)
    # Cartesian:  x_world = x - CURRENT_WIDTH / 2
    #             y_world = viewport_y - canvas_height / 2

    canvas_height = CURRENT_HEIGHT - MENU_HEIGHT

    x_world = x - CURRENT_WIDTH / 2.0
    y_world = (CURRENT_HEIGHT - y) - canvas_height / 2.0

    # Snap to nearest grid intersection using proper rounding
    gx = int(round_half_up(x_world / GRID_SIZE))
    gy = int(round_half_up(y_world / GRID_SIZE))

    print(f"[Click] Mouse: ({x}, {y}) → World: ({x_world:.1f}, {y_world:.1f}) → Grid: ({gx}, {gy})")

    selected_points.append((gx, gy))

    if len(selected_points) == 2:
        p1 = selected_points[0]
        p2 = selected_points[1]

        # Compute line points using selected algorithm
        line_pts = compute_line_points(
            CURRENT_ALGORITHM,
            p1[0], p1[1],
            p2[0], p2[1],
        )

        # Store the drawn line
        drawn_lines.append({
            "p1": p1,
            "p2": p2,
            "algorithm": CURRENT_ALGORITHM,
            "color": CURRENT_COLOR,
            "width": CURRENT_LINE_WIDTH,
            "style": CURRENT_LINE_STYLE,
            "line_points": line_pts,
        })

        print(f"[Line] {CURRENT_ALGORITHM}: ({p1[0]},{p1[1]}) → ({p2[0]},{p2[1]}), "
              f"{len(line_pts)} pixels, color={CURRENT_COLOR}, width={CURRENT_LINE_WIDTH}, style={CURRENT_LINE_STYLE}")

        # Reset selection
        selected_points = []

    glut.glutPostRedisplay()


def mouse(button, state, x, y):
    """
    Handle mouse input and determine whether the click
    occurred on the menu, dropdown, or canvas.
    """

    global OPEN_MENU, OPEN_SUB_MENU

    # Only handle left mouse button.
    if button != glut.GLUT_LEFT_BUTTON:
        return

    # Only handle button press.
    if state != glut.GLUT_DOWN:
        return

    # GLUT mouse coordinates start at the top-left.

    # First, check if a dropdown is open and the click is within it
    if OPEN_MENU is not None:
        if handle_dropdown_click(x, y):
            return

        # If click is on the menu bar, let handle_menu_click deal with it
        if y < MENU_HEIGHT:
            handle_menu_click(x, y)
            return

        # Click is outside menu and dropdown — close dropdown
        OPEN_MENU = None
        OPEN_SUB_MENU = None
        glut.glutPostRedisplay()
        # Also process as canvas click if it's on the canvas
        if y >= MENU_HEIGHT:
            handle_canvas_click(x, y)
        return

    # No dropdown open
    if y < MENU_HEIGHT:
        handle_menu_click(x, y)
    else:
        handle_canvas_click(x, y)


# ============================================================================
# Clear / Save / Import
# ============================================================================

def _do_clear():
    """
    Clear all drawn lines and reset point selection.
    """
    global drawn_lines, selected_points
    drawn_lines = []
    selected_points = []
    print("[Clear] All lines cleared.")
    glut.glutPostRedisplay()


def _do_save():
    """
    Save the current drawing session to a JSON file.
    """
    os.makedirs(SAVED_DIR, exist_ok=True)

    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"drawing_{ts}.json"
    filepath = os.path.join(SAVED_DIR, filename)

    # Build serializable data
    save_data = []
    for line in drawn_lines:
        save_data.append({
            "p1": list(line["p1"]),
            "p2": list(line["p2"]),
            "algorithm": line["algorithm"],
            "color": line["color"],
            "width": line["width"],
            "style": line["style"],
        })

    with open(filepath, "w") as f:
        json.dump(save_data, f, indent=2)

    print(f"[Save] Session saved → {filepath}")


def _do_import(filename):
    """
    Import a previously saved drawing session.
    """
    global drawn_lines, selected_points

    filepath = os.path.join(SAVED_DIR, filename)
    if not os.path.isfile(filepath):
        print(f"[Import] File not found: {filepath}")
        return

    with open(filepath, "r") as f:
        save_data = json.load(f)

    # Clear current canvas before importing
    drawn_lines.clear()
    selected_points.clear()

    # Reconstruct lines
    for entry in save_data:
        p1 = tuple(entry["p1"])
        p2 = tuple(entry["p2"])
        algorithm = entry.get("algorithm", "Bresenham")
        color = entry.get("color", "Red")
        width = entry.get("width", 1)
        style = entry.get("style", "Solid")

        line_pts = compute_line_points(algorithm, p1[0], p1[1], p2[0], p2[1])

        drawn_lines.append({
            "p1": p1,
            "p2": p2,
            "algorithm": algorithm,
            "color": color,
            "width": width,
            "style": style,
            "line_points": line_pts,
        })

    selected_points = []
    print(f"[Import] Loaded {len(save_data)} lines from {filename}")
    glut.glutPostRedisplay()


# ============================================================================
# Canvas Projection
# ============================================================================

def get_canvas_height_width():
    """
    Return the current canvas height and width.
    """

    canvas_height = CURRENT_HEIGHT - MENU_HEIGHT
    canvas_width = CURRENT_WIDTH

    return canvas_height, canvas_width


def setup_canvas_projection(width, height):
    """
    Configure the OpenGL viewport and Cartesian projection
    used by the drawing canvas.
    """

    gl.glViewport(
        0,
        0,
        width,
        height,
    )

    # Projection matrix
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()

    half_height = height / 2
    half_width = width / 2

    glu.gluOrtho2D(
        -half_width,
        half_width,
        -half_height,
        half_height,
    )

    # Model-view matrix
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()


# ============================================================================
# Canvas Drawing
# ============================================================================

def draw_grid(half_height, half_width):
    """
    Draw the Cartesian grid centered around the origin.
    """

    gl.glLineWidth(GRID_LINE_THICKNESS)
    gl.glColor3f(*GRID_LINE_COLOR)

    gl.glBegin(gl.GL_LINES)

    # Vertical grid lines
    x = 0

    while x <= half_width:

        gl.glVertex2f(x, -half_height)
        gl.glVertex2f(x, half_height)

        if x != 0:
            gl.glVertex2f(-x, -half_height)
            gl.glVertex2f(-x, half_height)

        x += GRID_SIZE

    # Horizontal grid lines
    y = 0

    while y <= half_height:

        gl.glVertex2f(-half_width, y)
        gl.glVertex2f(half_width, y)

        if y != 0:
            gl.glVertex2f(-half_width, -y)
            gl.glVertex2f(half_width, -y)

        y += GRID_SIZE

    gl.glEnd()


def draw_origin_line(half_height, half_width):
    """
    Draw the X and Y axes.
    """

    gl.glColor3f(*ORIGIN_LINE_COLOR)
    gl.glLineWidth(ORIGIN_LINE_THICKNESS)

    gl.glBegin(gl.GL_LINES)

    # X-axis
    gl.glVertex2f(-half_width, 0)
    gl.glVertex2f(half_width, 0)

    # Y-axis
    gl.glVertex2f(0, -half_height)
    gl.glVertex2f(0, half_height)

    gl.glEnd()


def draw_tick_labels(half_height, half_width):
    """
    Draw tick labels along the X and Y axes.
    """

    gl.glColor3f(*TICK_LABEL_COLOR)

    # X-axis labels
    x = -int(half_width / GRID_SIZE) * GRID_SIZE
    while x <= half_width:
        val = int(x / GRID_SIZE)
        if val != 0:
            label = str(val)
            # Position label below the x-axis
            gl.glRasterPos2f(x - 4, -14)
            for ch in label:
                glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_10, ord(ch))
        x += GRID_SIZE * 5   # label every 5 grid units

    # Y-axis labels
    y = -int(half_height / GRID_SIZE) * GRID_SIZE
    while y <= half_height:
        val = int(y / GRID_SIZE)
        if val != 0:
            label = str(val)
            # Position label to the left of the y-axis
            gl.glRasterPos2f(-24 - len(label) * 2, y - 4)
            for ch in label:
                glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_10, ord(ch))
        y += GRID_SIZE * 5   # label every 5 grid units


def draw_lines_on_canvas():
    """
    Draw all user-drawn lines on the canvas.
    """

    # Enable smooth lines
    gl.glEnable(gl.GL_LINE_SMOOTH)
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glHint(gl.GL_LINE_SMOOTH_HINT, gl.GL_NICEST)

    for line in drawn_lines:
        pts = line["line_points"]
        color = COLOR_MAP.get(line["color"], (1.0, 0.0, 0.0))
        width = line["width"]
        style = line["style"]

        # Set line color
        gl.glColor3f(*color)

        # Set line width
        gl.glLineWidth(width)

        # Render based on line style
        gl.glEnable(gl.GL_LINE_SMOOTH)
        gl.glDisable(gl.GL_LINE_STIPPLE)

        if style == "Dotted":
            # Draw distinct points (dots) skipping every other grid point
            gl.glPointSize(width * 2 + 1)
            gl.glBegin(gl.GL_POINTS)
            for i, (px, py) in enumerate(pts):
                if i % 2 == 0:
                    gl.glVertex2f(px * GRID_SIZE, py * GRID_SIZE)
            gl.glEnd()
            
        elif style == "Dashed":
            # Draw discrete line segments (dashes), skipping a few grid points
            gl.glBegin(gl.GL_LINES)
            for i in range(0, len(pts) - 1, 3):
                px1, py1 = pts[i]
                px2, py2 = pts[i+1]
                gl.glVertex2f(px1 * GRID_SIZE, py1 * GRID_SIZE)
                gl.glVertex2f(px2 * GRID_SIZE, py2 * GRID_SIZE)
            gl.glEnd()
            
        else:
            # Solid line
            if len(pts) >= 2:
                gl.glBegin(gl.GL_LINE_STRIP)
                for (px, py) in pts:
                    gl.glVertex2f(px * GRID_SIZE, py * GRID_SIZE)
                gl.glEnd()

        # Reset state after drawing this line
        gl.glPointSize(1)

    # Reset line width
    gl.glLineWidth(1)

    # Disable smooth lines (so it doesn't affect grid/axes/menu)
    gl.glDisable(gl.GL_LINE_SMOOTH)
    gl.glDisable(gl.GL_BLEND)


def draw_selected_points():
    """
    Draw the currently selected (pending) point(s) as markers.
    """

    if not selected_points:
        return

    gl.glColor3f(*POINT_MARKER_COLOR)

    for (gx, gy) in selected_points:
        cx = gx * GRID_SIZE
        cy = gy * GRID_SIZE
        r = POINT_MARKER_RADIUS

        # Filled circle
        gl.glBegin(gl.GL_POLYGON)
        for angle in range(0, 360, 15):
            rad = math.radians(angle)
            gl.glVertex2f(cx + r * math.cos(rad), cy + r * math.sin(rad))
        gl.glEnd()

        # Dark outline
        gl.glColor3f(0.0, 0.0, 0.0)
        gl.glLineWidth(1)
        gl.glBegin(gl.GL_LINE_LOOP)
        for angle in range(0, 360, 15):
            rad = math.radians(angle)
            gl.glVertex2f(cx + (r + 1) * math.cos(rad), cy + (r + 1) * math.sin(rad))
        gl.glEnd()

        # Reset color for next point
        gl.glColor3f(*POINT_MARKER_COLOR)


def draw_canvas():
    """
    Draw the complete Cartesian drawing canvas.
    """

    canvas_height, canvas_width = get_canvas_height_width()

    half_height = canvas_height / 2
    half_width = canvas_width / 2

    draw_grid(
        half_height,
        half_width,
    )

    draw_origin_line(
        half_height,
        half_width,
    )

    draw_tick_labels(
        half_height,
        half_width,
    )

    # Draw all user lines
    draw_lines_on_canvas()

    # Draw pending selected points
    draw_selected_points()


# ============================================================================
# Menu Projection
# ============================================================================

def setup_menu_projection():
    """
    Configure the OpenGL viewport and projection
    used by the top menu bar and its dropdowns.

    Uses a top-left origin coordinate system covering the full window,
    so dropdowns can extend below the menu bar.
    """

    gl.glViewport(
        0,
        0,
        CURRENT_WIDTH,
        CURRENT_HEIGHT,
    )

    # Projection matrix — full window, top-left origin
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()

    glu.gluOrtho2D(
        0,
        CURRENT_WIDTH,
        CURRENT_HEIGHT,
        0,
    )

    # Model-view matrix
    gl.glMatrixMode(gl.GL_MODELVIEW)
    gl.glLoadIdentity()


# ============================================================================
# Menu Drawing
# ============================================================================

def draw_menu_text(x, y, text, color=(0.9, 0.9, 0.9)):
    """
    Draw text at the given position using bitmap font.
    """
    gl.glColor3f(*color)
    gl.glRasterPos2f(x, y)
    for ch in text:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))


def draw_menu():
    """
    Draw the background of the top menu bar and its items.
    """

    # Menu background
    gl.glColor3f(*MENU_BG_COLOR)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(0, 0)
    gl.glVertex2f(CURRENT_WIDTH, 0)
    gl.glVertex2f(CURRENT_WIDTH, MENU_HEIGHT)
    gl.glVertex2f(0, MENU_HEIGHT)
    gl.glEnd()

    # Draw individual menu items
    menu_item_width = CURRENT_WIDTH / len(MENU_LIST)

    for index, item in enumerate(MENU_LIST):

        left = index * menu_item_width
        right = left + menu_item_width

        # Highlight the active menu item
        if OPEN_MENU == item:
            gl.glColor3f(*MENU_HOVER_COLOR)
            gl.glBegin(gl.GL_QUADS)
            gl.glVertex2f(left, 0)
            gl.glVertex2f(right, 0)
            gl.glVertex2f(right, MENU_HEIGHT)
            gl.glVertex2f(left, MENU_HEIGHT)
            gl.glEnd()

        # Item border
        gl.glColor3f(*MENU_ITEM_COLOR)
        gl.glLineWidth(1)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(left, 0)
        gl.glVertex2f(right, 0)
        gl.glVertex2f(right, MENU_HEIGHT)
        gl.glVertex2f(left, MENU_HEIGHT)
        gl.glEnd()

        # Item text — centered
        text_x = left + (menu_item_width - len(item) * 7) / 2
        text_y = MENU_HEIGHT / 2 + 5
        draw_menu_text(text_x, text_y, item, MENU_TEXT_COLOR)

    # Draw status bar text showing current settings
    status = f"  {CURRENT_ALGORITHM} | {CURRENT_COLOR} | Width:{CURRENT_LINE_WIDTH} | {CURRENT_LINE_STYLE}"
    draw_menu_text(5, MENU_HEIGHT - 3, status, (0.55, 0.55, 0.55))


def draw_dropdown():
    """
    Draw the dropdown menu for the currently selected menu item.
    """

    if OPEN_MENU is None:
        return

    # Get dropdown items
    if OPEN_MENU == "Import File":
        dropdown_items = import_file_list if import_file_list else ["(no saved files)"]
    else:
        dropdown_items = MENU_DROPDOWN.get(OPEN_MENU, [])

    if not dropdown_items:
        return

    # Find menu item index
    menu_index = MENU_LIST.index(OPEN_MENU)
    menu_left, _ = get_menu_item_bounds_px(menu_index)

    dd_left = menu_left
    dd_top = MENU_HEIGHT

    # Draw dropdown background
    dd_height = len(dropdown_items) * DROPDOWN_ITEM_HEIGHT

    gl.glColor3f(*DROPDOWN_BG_COLOR)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(dd_left, dd_top)
    gl.glVertex2f(dd_left + DROPDOWN_WIDTH, dd_top)
    gl.glVertex2f(dd_left + DROPDOWN_WIDTH, dd_top + dd_height)
    gl.glVertex2f(dd_left, dd_top + dd_height)
    gl.glEnd()

    # Draw each dropdown item
    for i, item in enumerate(dropdown_items):
        item_top = dd_top + i * DROPDOWN_ITEM_HEIGHT
        item_bottom = item_top + DROPDOWN_ITEM_HEIGHT

        # Highlight active selection
        is_active = False
        if OPEN_MENU == "Line Drawing Algorithm" and item == CURRENT_ALGORITHM:
            is_active = True
        elif OPEN_MENU == "Line Parameters":
            if item == "Color" and OPEN_SUB_MENU == "Color":
                is_active = True
            elif item == "Line Width" and OPEN_SUB_MENU == "Line Width":
                is_active = True
            elif item == "Solid Line" and CURRENT_LINE_STYLE == "Solid":
                is_active = True
            elif item == "Dotted Line" and CURRENT_LINE_STYLE == "Dotted":
                is_active = True
            elif item == "Dashed Line" and CURRENT_LINE_STYLE == "Dashed":
                is_active = True

        if is_active:
            gl.glColor3f(*DROPDOWN_HOVER_COLOR)
            gl.glBegin(gl.GL_QUADS)
            gl.glVertex2f(dd_left, item_top)
            gl.glVertex2f(dd_left + DROPDOWN_WIDTH, item_top)
            gl.glVertex2f(dd_left + DROPDOWN_WIDTH, item_bottom)
            gl.glVertex2f(dd_left, item_bottom)
            gl.glEnd()

        # Item border
        gl.glColor3f(0.30, 0.30, 0.33)
        gl.glLineWidth(1)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(dd_left, item_top)
        gl.glVertex2f(dd_left + DROPDOWN_WIDTH, item_top)
        gl.glVertex2f(dd_left + DROPDOWN_WIDTH, item_bottom)
        gl.glVertex2f(dd_left, item_bottom)
        gl.glEnd()

        # Item text
        text_x = dd_left + 12
        text_y = item_top + DROPDOWN_ITEM_HEIGHT / 2 + 5
        draw_menu_text(text_x, text_y, item, DROPDOWN_TEXT_COLOR)

        # Arrow indicator for items with sub-dropdowns
        if OPEN_MENU == "Line Parameters" and item in SUB_DROPDOWN:
            draw_menu_text(dd_left + DROPDOWN_WIDTH - 18, text_y, "\u25B6", DROPDOWN_TEXT_COLOR)

    # Draw sub-dropdown if open
    if OPEN_SUB_MENU and OPEN_SUB_MENU in SUB_DROPDOWN:
        sub_items = SUB_DROPDOWN[OPEN_SUB_MENU]

        # Find parent index
        parent_items = MENU_DROPDOWN.get(OPEN_MENU, [])
        parent_index = 0
        for pi, pitem in enumerate(parent_items):
            if pitem == OPEN_SUB_MENU:
                parent_index = pi
                break

        sub_left = dd_left + DROPDOWN_WIDTH
        sub_top = dd_top + parent_index * DROPDOWN_ITEM_HEIGHT
        sub_height = len(sub_items) * DROPDOWN_ITEM_HEIGHT

        # Sub-dropdown background
        gl.glColor3f(*DROPDOWN_BG_COLOR)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(sub_left, sub_top)
        gl.glVertex2f(sub_left + DROPDOWN_WIDTH, sub_top)
        gl.glVertex2f(sub_left + DROPDOWN_WIDTH, sub_top + sub_height)
        gl.glVertex2f(sub_left, sub_top + sub_height)
        gl.glEnd()

        for si, sitem in enumerate(sub_items):
            s_top = sub_top + si * DROPDOWN_ITEM_HEIGHT
            s_bottom = s_top + DROPDOWN_ITEM_HEIGHT

            # Highlight active selection
            is_sub_active = False
            if OPEN_SUB_MENU == "Color" and sitem == CURRENT_COLOR:
                is_sub_active = True
            elif OPEN_SUB_MENU == "Line Width" and sitem == str(CURRENT_LINE_WIDTH):
                is_sub_active = True

            if is_sub_active:
                gl.glColor3f(*DROPDOWN_HOVER_COLOR)
                gl.glBegin(gl.GL_QUADS)
                gl.glVertex2f(sub_left, s_top)
                gl.glVertex2f(sub_left + DROPDOWN_WIDTH, s_top)
                gl.glVertex2f(sub_left + DROPDOWN_WIDTH, s_bottom)
                gl.glVertex2f(sub_left, s_bottom)
                gl.glEnd()

            # Color swatch for color items
            if OPEN_SUB_MENU == "Color" and sitem in COLOR_MAP:
                swatch_color = COLOR_MAP[sitem]
                gl.glColor3f(*swatch_color)
                gl.glBegin(gl.GL_QUADS)
                gl.glVertex2f(sub_left + 8, s_top + 6)
                gl.glVertex2f(sub_left + 22, s_top + 6)
                gl.glVertex2f(sub_left + 22, s_bottom - 6)
                gl.glVertex2f(sub_left + 8, s_bottom - 6)
                gl.glEnd()

            # Item border
            gl.glColor3f(0.30, 0.30, 0.33)
            gl.glLineWidth(1)
            gl.glBegin(gl.GL_LINE_LOOP)
            gl.glVertex2f(sub_left, s_top)
            gl.glVertex2f(sub_left + DROPDOWN_WIDTH, s_top)
            gl.glVertex2f(sub_left + DROPDOWN_WIDTH, s_bottom)
            gl.glVertex2f(sub_left, s_bottom)
            gl.glEnd()

            # Item text
            text_offset = 28 if OPEN_SUB_MENU == "Color" else 12
            text_x = sub_left + text_offset
            text_y = s_top + DROPDOWN_ITEM_HEIGHT / 2 + 5
            draw_menu_text(text_x, text_y, sitem, DROPDOWN_TEXT_COLOR)


# ============================================================================
# Display
# ============================================================================

def display():
    """
    Render the complete application window.
    """

    # Clear the screen.
    gl.glClearColor(*CANVAS_BG_COLOR)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)

    # ------------------------------------------------------------------------
    # Canvas
    # ------------------------------------------------------------------------

    canvas_height, canvas_width = get_canvas_height_width()

    setup_canvas_projection(
        canvas_width,
        canvas_height,
    )

    draw_canvas()

    # ------------------------------------------------------------------------
    # Menu (drawn on top of canvas using full-window projection)
    # ------------------------------------------------------------------------

    setup_menu_projection()

    draw_menu()
    draw_dropdown()

    # ------------------------------------------------------------------------
    # Present Frame
    # ------------------------------------------------------------------------

    glut.glutSwapBuffers()


# ============================================================================
# Window Resize
# ============================================================================

def reshape(width, height):
    """
    Update the current window dimensions when the window is resized.
    """

    global CURRENT_WIDTH, CURRENT_HEIGHT

    if height == 0:
        height = 1

    CURRENT_WIDTH = width
    CURRENT_HEIGHT = height


# ============================================================================
# Application Entry Point
# ============================================================================

def run():
    """
    Initialize the application and start the GLUT event loop.
    """

    # ------------------------------------------------------------------------
    # Initialize GLUT
    # ------------------------------------------------------------------------

    glut.glutInit(sys.argv)

    glut.glutInitDisplayMode(
        glut.GLUT_DOUBLE |
        glut.GLUT_RGB
    )

    # ------------------------------------------------------------------------
    # Create Window
    # ------------------------------------------------------------------------

    glut.glutInitWindowSize(
        DEFAULT_WIDTH,
        DEFAULT_HEIGHT,
    )

    glut.glutCreateWindow(
        "Line Drawing Algorithm"
    )

    # ------------------------------------------------------------------------
    # OpenGL Configuration
    # ------------------------------------------------------------------------

    gl.glClearColor(
        *CANVAS_BG_COLOR
    )

    # ------------------------------------------------------------------------
    # Register Callbacks
    # ------------------------------------------------------------------------

    glut.glutReshapeFunc(reshape)
    glut.glutDisplayFunc(display)
    glut.glutKeyboardFunc(keyboard)
    glut.glutMouseFunc(mouse)

    # ------------------------------------------------------------------------
    # Print usage info
    # ------------------------------------------------------------------------

    print("=== Line Drawing Algorithm Application ===")
    print(f"Default algorithm: {CURRENT_ALGORITHM}")
    print(f"Default color: {CURRENT_COLOR}")
    print(f"Default width: {CURRENT_LINE_WIDTH}")
    print(f"Default style: {CURRENT_LINE_STYLE}")
    print("Click two points on the canvas to draw a line.")
    print("Press 'P' to save a screenshot to output/")
    print("Press 'Esc' to exit.")

    # ------------------------------------------------------------------------
    # Start Event Loop
    # ------------------------------------------------------------------------

    glut.glutMainLoop()
