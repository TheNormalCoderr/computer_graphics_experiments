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

# ── Save Dialog State ────────────────────────────────────────────────────────
SAVE_DIALOG_OPEN = False
SAVE_DIALOG_TEXT = ""           # Current text in the input field
SAVE_DIALOG_DEFAULT = ""       # Default filename shown as placeholder
SAVE_DIALOG_CURSOR_BLINK = 0   # Frame counter for cursor blinking


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
    global SAVE_DIALOG_OPEN, SAVE_DIALOG_TEXT

    # ── If save dialog is open, route all keys to it ─────────────────────
    if SAVE_DIALOG_OPEN:
        if key == b'\x1b':          # Escape → cancel
            SAVE_DIALOG_OPEN = False
            SAVE_DIALOG_TEXT = ""
            print("[Save] Cancelled.")
            glut.glutPostRedisplay()
            return
        elif key == b'\r' or key == b'\n':   # Enter → confirm save
            _confirm_save()
            return
        elif key == b'\x08' or key == b'\x7f':  # Backspace / Delete
            SAVE_DIALOG_TEXT = SAVE_DIALOG_TEXT[:-1]
            glut.glutPostRedisplay()
            return
        else:
            ch = key.decode('ascii', errors='ignore')
            # Allow printable characters and common filename characters
            if ch and ch.isprintable() and ch not in ('/', '\\', ':', '*', '?', '"', '<', '>', '|'):
                SAVE_DIALOG_TEXT += ch
                glut.glutPostRedisplay()
            return

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
        print(f"[Points] {line_pts}")

        # Reset selection
        selected_points = []

    glut.glutPostRedisplay()


def mouse(button, state, x, y):
    """
    Handle mouse input and determine whether the click
    occurred on the menu, dropdown, or canvas.
    """

    global OPEN_MENU, OPEN_SUB_MENU, SAVE_DIALOG_OPEN, SAVE_DIALOG_TEXT

    # Only handle left mouse button.
    if button != glut.GLUT_LEFT_BUTTON:
        return

    # Only handle button press.
    if state != glut.GLUT_DOWN:
        return

    # ── If save dialog is open, handle its button clicks ─────────────────
    if SAVE_DIALOG_OPEN:
        _handle_save_dialog_click(x, y)
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
    Open the save dialog popup so the user can choose a filename.
    """
    global SAVE_DIALOG_OPEN, SAVE_DIALOG_TEXT, SAVE_DIALOG_DEFAULT

    import datetime
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    SAVE_DIALOG_DEFAULT = f"drawing_{ts}"
    SAVE_DIALOG_TEXT = ""
    SAVE_DIALOG_OPEN = True
    glut.glutPostRedisplay()


def _confirm_save():
    """
    Actually perform the save using the dialog text (or default name).
    """
    global SAVE_DIALOG_OPEN, SAVE_DIALOG_TEXT

    # Use user-entered name, or fall back to default
    name = SAVE_DIALOG_TEXT.strip() if SAVE_DIALOG_TEXT.strip() else SAVE_DIALOG_DEFAULT

    # Ensure .json extension
    if not name.endswith(".json"):
        name += ".json"

    os.makedirs(SAVED_DIR, exist_ok=True)
    filepath = os.path.join(SAVED_DIR, name)

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

    SAVE_DIALOG_OPEN = False
    SAVE_DIALOG_TEXT = ""
    glut.glutPostRedisplay()


def _handle_save_dialog_click(x, y):
    """
    Handle mouse clicks when the save dialog is open.
    Check if Save or Cancel buttons were clicked.
    """
    global SAVE_DIALOG_OPEN, SAVE_DIALOG_TEXT

    # Dialog dimensions (must match draw_save_dialog)
    dialog_w = 420
    dialog_h = 180
    dlg_left = (CURRENT_WIDTH - dialog_w) / 2
    dlg_top  = (CURRENT_HEIGHT - dialog_h) / 2

    btn_w = 90
    btn_h = 32
    btn_y_top = dlg_top + dialog_h - 18 - btn_h
    btn_y_bot = btn_y_top + btn_h

    # Save button (right-aligned)
    save_btn_left = dlg_left + dialog_w - 20 - btn_w
    save_btn_right = save_btn_left + btn_w

    # Cancel button (to the left of Save)
    cancel_btn_left = save_btn_left - btn_w - 12
    cancel_btn_right = cancel_btn_left + btn_w

    if btn_y_top <= y <= btn_y_bot:
        if save_btn_left <= x <= save_btn_right:
            _confirm_save()
            return
        if cancel_btn_left <= x <= cancel_btn_right:
            SAVE_DIALOG_OPEN = False
            SAVE_DIALOG_TEXT = ""
            print("[Save] Cancelled.")
            glut.glutPostRedisplay()
            return

    # Click anywhere else inside the dialog — do nothing (keep dialog open)
    # Click outside the dialog — also keep dialog open (modal behavior)


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


def _draw_styled_line(x1, y1, x2, y2, style, width):
    """
    Draw a line from (x1,y1) to (x2,y2) with the given style.
    For 'Dotted' and 'Dashed', manually break the line into segments
    because GL_LINE_STIPPLE is deprecated and broken on macOS.
    """
    if style == "Solid":
        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(x1, y1)
        gl.glVertex2f(x2, y2)
        gl.glEnd()
        return

    # Compute total line length in pixels
    dx = x2 - x1
    dy = y2 - y1
    length = math.sqrt(dx * dx + dy * dy)

    if length < 1.0:
        # Too short to pattern — just draw a point
        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(x1, y1)
        gl.glVertex2f(x2, y2)
        gl.glEnd()
        return

    # Pattern definitions: (draw_length, gap_length) in pixels
    if style == "Dotted":
        draw_len, gap_len = 5.0, 5.0
    elif style == "Dashed":
        draw_len, gap_len = 12.0, 8.0
    else:
        draw_len, gap_len = 12.0, 8.0

    pattern_len = draw_len + gap_len

    # Unit direction vector
    ux = dx / length
    uy = dy / length

    if style == "Dotted":
        # Draw actual points/dots at regular intervals
        dot_spacing = 6.0
        gl.glEnable(gl.GL_POINT_SMOOTH)
        gl.glPointSize(width if width > 1 else 2.0)  # use line width for point size
        gl.glBegin(gl.GL_POINTS)
        dist = 0.0
        while dist <= length:
            px = x1 + ux * dist
            py = y1 + uy * dist
            gl.glVertex2f(px, py)
            dist += dot_spacing
        gl.glEnd()
        gl.glDisable(gl.GL_POINT_SMOOTH)
    else:
        # Dashed: draw short line segments with gaps
        dist = 0.0
        gl.glBegin(gl.GL_LINES)
        while dist < length:
            seg_start = dist
            seg_end = min(dist + draw_len, length)

            sx = x1 + ux * seg_start
            sy = y1 + uy * seg_start
            ex = x1 + ux * seg_end
            ey = y1 + uy * seg_end

            gl.glVertex2f(sx, sy)
            gl.glVertex2f(ex, ey)

            dist += pattern_len
        gl.glEnd()


def draw_lines_on_canvas():
    """
    Draw all user-drawn lines on the canvas as straight lines from p1 to p2.
    The algorithm-computed pixel points are printed to the terminal only.
    """

    # Enable smooth lines
    gl.glEnable(gl.GL_LINE_SMOOTH)
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glHint(gl.GL_LINE_SMOOTH_HINT, gl.GL_NICEST)

    for line in drawn_lines:
        p1 = line["p1"]
        p2 = line["p2"]
        color = COLOR_MAP.get(line["color"], (1.0, 0.0, 0.0))
        width = line["width"]
        style = line["style"]

        # Set line color
        gl.glColor3f(*color)

        # Set line width
        gl.glLineWidth(width)

        # Draw the line with the appropriate style
        _draw_styled_line(
            p1[0] * GRID_SIZE, p1[1] * GRID_SIZE,
            p2[0] * GRID_SIZE, p2[1] * GRID_SIZE,
            style,
            width,
        )

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

def draw_save_dialog():
    """
    Draw the "Save As" popup dialog over the canvas.
    """
    global SAVE_DIALOG_CURSOR_BLINK

    if not SAVE_DIALOG_OPEN:
        return

    SAVE_DIALOG_CURSOR_BLINK = (SAVE_DIALOG_CURSOR_BLINK + 1) % 60

    # ── Semi-transparent overlay ──────────────────────────────────────────
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glColor4f(0.0, 0.0, 0.0, 0.45)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(0, 0)
    gl.glVertex2f(CURRENT_WIDTH, 0)
    gl.glVertex2f(CURRENT_WIDTH, CURRENT_HEIGHT)
    gl.glVertex2f(0, CURRENT_HEIGHT)
    gl.glEnd()

    # ── Dialog box dimensions ────────────────────────────────────────────
    dialog_w = 420
    dialog_h = 180
    dlg_left   = (CURRENT_WIDTH - dialog_w) / 2
    dlg_right  = dlg_left + dialog_w
    dlg_top    = (CURRENT_HEIGHT - dialog_h) / 2
    dlg_bottom = dlg_top + dialog_h

    # ── Dialog shadow ────────────────────────────────────────────────────
    shadow_off = 5
    gl.glColor4f(0.0, 0.0, 0.0, 0.25)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(dlg_left + shadow_off, dlg_top + shadow_off)
    gl.glVertex2f(dlg_right + shadow_off, dlg_top + shadow_off)
    gl.glVertex2f(dlg_right + shadow_off, dlg_bottom + shadow_off)
    gl.glVertex2f(dlg_left + shadow_off, dlg_bottom + shadow_off)
    gl.glEnd()

    # ── Dialog background ────────────────────────────────────────────────
    gl.glColor3f(0.18, 0.18, 0.22)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(dlg_left, dlg_top)
    gl.glVertex2f(dlg_right, dlg_top)
    gl.glVertex2f(dlg_right, dlg_bottom)
    gl.glVertex2f(dlg_left, dlg_bottom)
    gl.glEnd()

    # ── Dialog border ────────────────────────────────────────────────────
    gl.glColor3f(0.45, 0.45, 0.50)
    gl.glLineWidth(2)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(dlg_left, dlg_top)
    gl.glVertex2f(dlg_right, dlg_top)
    gl.glVertex2f(dlg_right, dlg_bottom)
    gl.glVertex2f(dlg_left, dlg_bottom)
    gl.glEnd()

    # ── Title ────────────────────────────────────────────────────────────
    title = "Save Drawing As"
    title_x = dlg_left + (dialog_w - len(title) * 8) / 2
    title_y = dlg_top + 28
    gl.glColor3f(0.95, 0.95, 0.95)
    gl.glRasterPos2f(title_x, title_y)
    for ch in title:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_18, ord(ch))

    # ── Separator line under title ───────────────────────────────────────
    gl.glColor3f(0.35, 0.35, 0.40)
    gl.glLineWidth(1)
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(dlg_left + 15, dlg_top + 38)
    gl.glVertex2f(dlg_right - 15, dlg_top + 38)
    gl.glEnd()

    # ── Label ────────────────────────────────────────────────────────────
    label = "File name (.json auto-appended):"
    gl.glColor3f(0.75, 0.75, 0.78)
    gl.glRasterPos2f(dlg_left + 20, dlg_top + 62)
    for ch in label:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))

    # ── Text input field ─────────────────────────────────────────────────
    input_left   = dlg_left + 20
    input_right  = dlg_right - 20
    input_top    = dlg_top + 72
    input_bottom = input_top + 30

    # Input background
    gl.glColor3f(0.12, 0.12, 0.15)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(input_left, input_top)
    gl.glVertex2f(input_right, input_top)
    gl.glVertex2f(input_right, input_bottom)
    gl.glVertex2f(input_left, input_bottom)
    gl.glEnd()

    # Input border
    gl.glColor3f(0.40, 0.55, 0.90)
    gl.glLineWidth(2)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(input_left, input_top)
    gl.glVertex2f(input_right, input_top)
    gl.glVertex2f(input_right, input_bottom)
    gl.glVertex2f(input_left, input_bottom)
    gl.glEnd()

    # Display text (user input or placeholder)
    text_y = input_top + 20
    if SAVE_DIALOG_TEXT:
        display_text = SAVE_DIALOG_TEXT
        gl.glColor3f(0.95, 0.95, 0.95)
    else:
        display_text = SAVE_DIALOG_DEFAULT
        gl.glColor3f(0.45, 0.45, 0.50)   # Dimmed placeholder

    gl.glRasterPos2f(input_left + 8, text_y)
    for ch in display_text:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))

    # Blinking cursor (only if user has focus = dialog is open)
    if SAVE_DIALOG_TEXT and SAVE_DIALOG_CURSOR_BLINK < 35:
        cursor_x = input_left + 8 + len(SAVE_DIALOG_TEXT) * 7
        gl.glColor3f(0.90, 0.90, 0.95)
        gl.glLineWidth(1)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(cursor_x, input_top + 6)
        gl.glVertex2f(cursor_x, input_bottom - 6)
        gl.glEnd()

    # ── Hint text ────────────────────────────────────────────────────────
    hint = "Press Enter to save, Escape to cancel"
    gl.glColor3f(0.50, 0.50, 0.55)
    gl.glRasterPos2f(dlg_left + 20, input_bottom + 18)
    for ch in hint:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_10, ord(ch))

    # ── Buttons ──────────────────────────────────────────────────────────
    btn_w = 90
    btn_h = 32
    btn_y_top = dlg_bottom - 18 - btn_h
    btn_y_bot = btn_y_top + btn_h

    # Save button (right-aligned, accent color)
    save_btn_left = dlg_right - 20 - btn_w
    gl.glColor3f(0.22, 0.45, 0.85)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(save_btn_left, btn_y_top)
    gl.glVertex2f(save_btn_left + btn_w, btn_y_top)
    gl.glVertex2f(save_btn_left + btn_w, btn_y_bot)
    gl.glVertex2f(save_btn_left, btn_y_bot)
    gl.glEnd()
    # Save button text
    gl.glColor3f(1.0, 1.0, 1.0)
    gl.glRasterPos2f(save_btn_left + 30, btn_y_top + 21)
    for ch in "Save":
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))

    # Cancel button (to the left of Save)
    cancel_btn_left = save_btn_left - btn_w - 12
    gl.glColor3f(0.32, 0.32, 0.36)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(cancel_btn_left, btn_y_top)
    gl.glVertex2f(cancel_btn_left + btn_w, btn_y_top)
    gl.glVertex2f(cancel_btn_left + btn_w, btn_y_bot)
    gl.glVertex2f(cancel_btn_left, btn_y_bot)
    gl.glEnd()
    # Cancel button text
    gl.glColor3f(0.85, 0.85, 0.85)
    gl.glRasterPos2f(cancel_btn_left + 22, btn_y_top + 21)
    for ch in "Cancel":
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))

    gl.glDisable(gl.GL_BLEND)


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
    # Save Dialog (drawn last, on top of everything)
    # ------------------------------------------------------------------------

    draw_save_dialog()

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
