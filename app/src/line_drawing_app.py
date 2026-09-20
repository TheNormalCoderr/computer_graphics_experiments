import os
import sys
import json
import math
import struct
import zlib
import glob
import copy

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
from MidPointCircle.src.midpoint_circle import midpoint_circle_points                 #type:ignore
from MidPointEllipse.src.midpoint_ellipse import midpoint_ellipse_points               #type:ignore
from BasicTransformations2D.src.basic_transformations import (                         #type:ignore
    translation_matrix, scaling_matrix, rotation_matrix, mat3_multiply,
    mat3_transform_point,
)
from CompositeTransformations2D.src.composite_transformations import (                 #type:ignore
    compose_transformations, transform_about_point_matrix, transform_about_axis_matrix,
)


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

MENU_HEIGHT = 60
MENU_BUTTON_HEIGHT = 40
MENU_BG_COLOR = (0.22, 0.22, 0.25)
MENU_ITEM_COLOR = (0.35, 0.35, 0.38)
MENU_TEXT_COLOR = (0.92, 0.92, 0.92)
MENU_HOVER_COLOR = (0.40, 0.40, 0.45)

MENU_LIST = [
    "Line Drawing Algorithm",
    "Line Parameters",
    "Transformations",
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
    "Mid Point Circle",
    "Mid Point Ellipse",
]

LINE_PARAMETERS_ITEMS = [
    "Color",
    "Line Width",
    "Solid Line",
    "Dotted Line",
    "Dashed Line",
    "User Defined",
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
    "Undo (Ctrl+Z)",
    "Redo (Ctrl+Y)",
    "Clear",
    "Save",
    "Exit",
]

TRANSFORMATION_ITEMS = [
    "Basic Transformations",
    "Composite Transformations",
]

BASIC_TRANSFORMATION_ITEMS = [
    "Translation",
    "Scaling",
    "Rotation",
]

COMPOSITE_TRANSFORMATION_ITEMS = [
    "About a Point",
    "About an Axis",
]

MENU_DROPDOWN = {
    "Line Drawing Algorithm": ALGORITHM_ITEMS,
    "Line Parameters": LINE_PARAMETERS_ITEMS,
    "Transformations": TRANSFORMATION_ITEMS,
    "Options": OPTIONS_ITEMS,
}

# Sub-dropdown mapping for menu items that need a second level.
SUB_DROPDOWN = {
    "Color": COLOR_ITEMS,
    "Line Width": WIDTH_ITEMS,
    "Basic Transformations": BASIC_TRANSFORMATION_ITEMS,
    "Composite Transformations": COMPOSITE_TRANSFORMATION_ITEMS,
}

# Currently opened menu / sub-menu
OPEN_MENU = None
OPEN_SUB_MENU = None

# ── Save Dialog State ────────────────────────────────────────────────────────
SAVE_DIALOG_OPEN = False
SAVE_DIALOG_TEXT = ""           # Current text in the input field
SAVE_DIALOG_DEFAULT = ""       # Default filename shown as placeholder
SAVE_DIALOG_CURSOR_BLINK = 0   # Frame counter for cursor blinking

# ── Pattern Dialog State ─────────────────────────────────────────────────────
PATTERN_DIALOG_OPEN = False
PATTERN_DIALOG_TEXT = ""        # Current text in the pattern input field
PATTERN_DIALOG_CURSOR_BLINK = 0 # Frame counter for cursor blinking
CURRENT_USER_PATTERN_HEX = "0xF0F0"     # Default user-defined hex pattern
CURRENT_USER_PATTERN = "1111000011110000"  # 16-bit binary expansion (1=draw, 0=gap)

# ── Transformation Dialog State ──────────────────────────────────────────────
TRANSFORM_DIALOG_OPEN = False
TRANSFORM_DIALOG_TYPE = ""              # Selected basic or composite transformation
TRANSFORM_DIALOG_FIELDS = {}            # e.g. {"tx": "", "ty": ""}
TRANSFORM_DIALOG_FIELD_ORDER = []       # ordered list of field names
TRANSFORM_DIALOG_ACTIVE_FIELD = 0       # index into FIELD_ORDER for focused field
TRANSFORM_DIALOG_CURSOR_BLINK = 0      # Frame counter for cursor blinking


def hex_to_binary_pattern(val):
    """
    Convert a user-supplied pattern string (Hex e.g. '0xF0F0', 'F0F0', '0xAAAA', '0x1C47',
    or Binary '11110000') into a tuple: (hex_str, binary_str).
    """
    if not val or not str(val).strip():
        return "0xF0F0", "1111000011110000"

    s = str(val).strip()
    raw = s
    if raw.lower().startswith("0x"):
        raw = raw[2:]

    # Try parsing as Hex
    try:
        int_val = int(raw, 16)
        bit_len = max(8, len(raw) * 4)
        bin_str = bin(int_val)[2:].zfill(bit_len)
        hex_display = f"0x{raw.upper()}"
        return hex_display, bin_str
    except ValueError:
        # Fallback if user typed binary string of 0s and 1s
        if all(c in ('0', '1') for c in s):
            try:
                int_val = int(s, 2)
                hex_display = f"0x{int_val:X}"
                return hex_display, s
            except ValueError:
                pass

    return "0xF0F0", "1111000011110000"


def get_binary_pattern(val):
    """Return the binary mask string ('1' and '0') for any pattern input (hex or binary)."""
    _, bin_str = hex_to_binary_pattern(val)
    return bin_str


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
CURRENT_LINE_STYLE = "Solid"   # "Solid", "Dotted", "Dashed", "UserDefined"

# Point selection state
selected_points = []    # list of (x_world, y_world)
current_mouse_grid = None # (gx, gy) of current mouse position

# All drawn shapes (lines, circles, and ellipses, persisted until Clear)
# Line entry: {
#   "type": "line",
#   "p1": (x, y),
#   "p2": (x, y),
#   "algorithm": str,
#   "color": str,
#   "width": int,
#   "style": str,
#   "pattern": str,       # user-defined pattern (only for "UserDefined" style)
#   "line_points": [(x, y), ...],
# }
# Circle entry: {
#   "type": "circle",
#   "center": (x, y),
#   "radius_point": (x, y),
#   "radius": int,
#   "algorithm": str,
#   "color": str,
#   "width": int,
#   "circle_points": [(x, y), ...],
# }
# Ellipse entry: {
#   "type": "ellipse",
#   "center": (x, y),
#   "rx_point": (x, y),
#   "ry_point": (x, y),
#   "rx": int,
#   "ry": int,
#   "algorithm": str,
#   "color": str,
#   "width": int,
#   "style": str,
#   "ellipse_points": [(x, y), ...],
# }
drawn_lines = []

# Animation state for circles and ellipses
circle_animation = {
    "active": False,
    "phase": "radius",      # "radius" -> "points" -> "finished"
    "progress": 0.0,        # 0.0 to 1.0 for radius, 0 to len(pts) for points
    "entry": None           # The dictionary that will eventually go into drawn_lines
}

ellipse_animation = {
    "active": False,
    "phase": "rx",          # "rx" -> "ry" -> "points" -> "finished"
    "progress": 0.0,
    "entry": None
}

# --- Animation Speed Settings ---
# Time (in milliseconds) between animation frames. Default 16ms (~60 FPS)
ANIMATION_FRAME_MS = 16
# How much the radius line grows per frame (0.0 to 1.0). Default 0.05 (takes 20 frames). Higher = faster.
ANIMATION_RADIUS_SPEED = 0.03 
# How many frames it should take to draw the entire circle of points. Default 30. Lower = faster.
ANIMATION_POINTS_FRAMES = 50.0
# --------------------------------

# Import file list (populated when Import File dropdown is opened)
import_file_list = []

# Saved drawings folder
SAVED_DIR = os.path.join(APP_DIR, "saved_drawings")
OUTPUT_DIR = os.path.join(APP_DIR, "output")


# ============================================================================
# Canvas Configuration
# ============================================================================

CANVAS_BG_COLOR = (0.96, 0.96, 0.97, 1.0)

GRID_SIZE = 1.5
GRID_LINE_COLOR = (0.82, 0.82, 0.84)
GRID_LINE_THICKNESS = 1

ORIGIN_LINE_COLOR = (0.15, 0.15, 0.15)
ORIGIN_LINE_THICKNESS = 2

TICK_LABEL_COLOR = (0.4, 0.4, 0.4)
POINT_MARKER_COLOR = (1.0, 0.3, 0.3)
POINT_MARKER_RADIUS = 4

# ── Undo / Redo Configuration & State ─────────────────────────────────────────
undo_stack = []   # list of deep-copied drawn_lines states
redo_stack = []   # list of deep-copied drawn_lines states
MAX_UNDO_STEPS = 50

def _save_undo_state():
    """Save current state of drawn_lines to undo_stack and clear redo_stack."""
    global undo_stack, redo_stack
    undo_stack.append(copy.deepcopy(drawn_lines))
    if len(undo_stack) > MAX_UNDO_STEPS:
        undo_stack.pop(0)
    redo_stack.clear()

def _do_undo():
    """Revert to previous state."""
    global drawn_lines, selected_points, undo_stack, redo_stack
    if not undo_stack:
        print("[Undo] Nothing to undo.")
        return
    redo_stack.append(copy.deepcopy(drawn_lines))
    drawn_lines = undo_stack.pop()
    selected_points = []
    print(f"[Undo] Reverted. {len(drawn_lines)} shape(s) on canvas. ({len(undo_stack)} undo(s) remaining)")
    glut.glutPostRedisplay()

def _do_redo():
    """Re-apply previously undone state."""
    global drawn_lines, selected_points, undo_stack, redo_stack
    if not redo_stack:
        print("[Redo] Nothing to redo.")
        return
    undo_stack.append(copy.deepcopy(drawn_lines))
    drawn_lines = redo_stack.pop()
    selected_points = []
    print(f"[Redo] Redone. {len(drawn_lines)} shape(s) on canvas. ({len(redo_stack)} redo(s) remaining)")
    glut.glutPostRedisplay()

# ── Endpoint Snap / Dumbbell Configuration ───────────────────────────────────
SNAP_DISTANCE_PIXELS = 14.0   # screen pixel radius for magnetic snapping
SNAP_MARKER_RADIUS = 5        # pixel radius of the dumbbell dot at endpoints
SNAP_MARKER_COLOR = (0.2, 0.6, 1.0)       # blue dots at connectable endpoints
SNAP_HIGHLIGHT_COLOR = (1.0, 0.45, 0.0)   # orange glow when hovering near a snap target
SNAP_HIGHLIGHT_RADIUS = 9     # pixel radius for the hover highlight ring


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

def is_circle_algorithm(algorithm):
    """Return True if the algorithm is a circle-drawing algorithm."""
    return algorithm == "Mid Point Circle"


def is_ellipse_algorithm(algorithm):
    """Return True if the algorithm is an ellipse-drawing algorithm."""
    return algorithm == "Mid Point Ellipse"


def compute_line_points(algorithm, x1, y1, x2, y2):
    """
    Call the selected line algorithm and return a list of (int, int) pixel positions.
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


def compute_circle_points(xc, yc, r):
    """
    Call the Mid Point Circle algorithm and return a list of (int, int) pixel positions.
    """
    if r <= 0:
        return [(xc, yc)]
    return midpoint_circle_points(xc, yc, r)


def compute_ellipse_points(xc, yc, rx, ry, angle=0.0):
    """
    Call the Mid Point Ellipse algorithm and return a list of (int, int) pixel positions.
    Applies rotation based on the given angle.
    """
    if rx <= 0 and ry <= 0:
        return [(xc, yc)]
    
    # Generate points around origin
    pts = midpoint_ellipse_points(0, 0, max(1, rx), max(1, ry))
    
    if angle == 0.0:
        return [(x + xc, y + yc) for (x, y) in pts]
        
    rotated_pts = []
    cos_t = math.cos(angle)
    sin_t = math.sin(angle)
    for (x, y) in pts:
        rot_x = x * cos_t - y * sin_t
        rot_y = x * sin_t + y * cos_t
        gx = int(round_half_up(xc + rot_x))
        gy = int(round_half_up(yc + rot_y))
        rotated_pts.append((gx, gy))
    
    # Remove duplicates from rounding
    unique = []
    seen = set()
    for pt in rotated_pts:
        if pt not in seen:
            seen.add(pt)
            unique.append(pt)
            
    return unique


def add_line(x1, y1, x2, y2, algorithm="Bresenham", color="Red", width=1, style="Solid"):
    """
    Utility function to programmatically add a line to the canvas.
    """
    global drawn_lines
    pts = compute_line_points(algorithm, x1, y1, x2, y2)
    drawn_lines.append({
        "type": "line",
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
    global PATTERN_DIALOG_OPEN, PATTERN_DIALOG_TEXT
    global TRANSFORM_DIALOG_OPEN, TRANSFORM_DIALOG_FIELDS, TRANSFORM_DIALOG_ACTIVE_FIELD

    # ── If transform dialog is open, route all keys to it ────────────────
    if TRANSFORM_DIALOG_OPEN:
        if key == b'\x1b':          # Escape → cancel
            TRANSFORM_DIALOG_OPEN = False
            print("[Transform] Cancelled.")
            glut.glutPostRedisplay()
            return
        elif key == b'\r' or key == b'\n':   # Enter → advance or apply
            if TRANSFORM_DIALOG_ACTIVE_FIELD < len(TRANSFORM_DIALOG_FIELD_ORDER) - 1:
                TRANSFORM_DIALOG_ACTIVE_FIELD += 1
                glut.glutPostRedisplay()
            else:
                _confirm_transform()
            return
        elif key == b'\t':           # Tab → switch to next field
            TRANSFORM_DIALOG_ACTIVE_FIELD = (TRANSFORM_DIALOG_ACTIVE_FIELD + 1) % len(TRANSFORM_DIALOG_FIELD_ORDER)
            glut.glutPostRedisplay()
            return
        elif key == b'\x08' or key == b'\x7f':  # Backspace / Delete
            field_name = TRANSFORM_DIALOG_FIELD_ORDER[TRANSFORM_DIALOG_ACTIVE_FIELD]
            TRANSFORM_DIALOG_FIELDS[field_name] = TRANSFORM_DIALOG_FIELDS[field_name][:-1]
            glut.glutPostRedisplay()
            return
        else:
            ch = key.decode('ascii', errors='ignore')
            field_name = TRANSFORM_DIALOG_FIELD_ORDER[TRANSFORM_DIALOG_ACTIVE_FIELD]
            current_val = TRANSFORM_DIALOG_FIELDS.get(field_name, "")
            if ch == '-':
                # Toggle minus sign at the front of current value
                if current_val.startswith('-'):
                    TRANSFORM_DIALOG_FIELDS[field_name] = current_val[1:]
                else:
                    TRANSFORM_DIALOG_FIELDS[field_name] = '-' + current_val
                glut.glutPostRedisplay()
                return
            elif ch == '+':
                if current_val.startswith('-'):
                    TRANSFORM_DIALOG_FIELDS[field_name] = current_val[1:]
                glut.glutPostRedisplay()
                return
            elif ch in '0123456789.':
                if ch == '.' and '.' in current_val:
                    return  # Prevent multiple decimal points
                if len(current_val) < 10:
                    TRANSFORM_DIALOG_FIELDS[field_name] += ch
                    glut.glutPostRedisplay()
            return

    # ── If pattern dialog is open, route all keys to it ──────────────────
    if PATTERN_DIALOG_OPEN:
        if key == b'\x1b':          # Escape → cancel
            PATTERN_DIALOG_OPEN = False
            PATTERN_DIALOG_TEXT = ""
            print("[Pattern] Cancelled.")
            glut.glutPostRedisplay()
            return
        elif key == b'\r' or key == b'\n':   # Enter → confirm pattern
            _confirm_pattern()
            return
        elif key == b'\x08' or key == b'\x7f':  # Backspace / Delete
            PATTERN_DIALOG_TEXT = PATTERN_DIALOG_TEXT[:-1]
            glut.glutPostRedisplay()
            return
        else:
            ch = key.decode('ascii', errors='ignore')
            # Only allow valid hex characters and standard pattern characters
            if ch in '0123456789abcdefABCDEFxX':
                if len(PATTERN_DIALOG_TEXT) < 10:  # e.g. "0xFFFFFFFF"
                    PATTERN_DIALOG_TEXT += ch
                    glut.glutPostRedisplay()
            return

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

    # Undo: Ctrl+Z (b'\x1a') or 'u' / 'U'
    if key in (b'\x1a', b'u', b'U'):
        _do_undo()
        return

    # Redo: Ctrl+Y (b'\x19') or 'r' / 'R'
    if key in (b'\x19', b'r', b'R'):
        _do_redo()
        return

    # 'p' — save screenshot to output/
    if key in (b'p', b'P'):
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        # Generate a timestamped filename
        import datetime
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(OUTPUT_DIR, f"screenshot_{ts}.png")
        save_framebuffer(filepath, CURRENT_WIDTH, CURRENT_HEIGHT)
        print(f"[Screenshot] Saved → {filepath}")


def special_keyboard(key, x, y):
    """
    Handle special GLUT keys like Arrow keys, Page Up/Down.
    Used for dialog navigation.
    """
    global TRANSFORM_DIALOG_ACTIVE_FIELD

    if TRANSFORM_DIALOG_OPEN and TRANSFORM_DIALOG_FIELD_ORDER:
        if key == glut.GLUT_KEY_DOWN:
            TRANSFORM_DIALOG_ACTIVE_FIELD = (TRANSFORM_DIALOG_ACTIVE_FIELD + 1) % len(TRANSFORM_DIALOG_FIELD_ORDER)
            glut.glutPostRedisplay()
        elif key == glut.GLUT_KEY_UP:
            TRANSFORM_DIALOG_ACTIVE_FIELD = (TRANSFORM_DIALOG_ACTIVE_FIELD - 1) % len(TRANSFORM_DIALOG_FIELD_ORDER)
            glut.glutPostRedisplay()


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
    dd_top = MENU_BUTTON_HEIGHT
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
                    elif OPEN_MENU == "Transformations":
                        if OPEN_SUB_MENU == "Basic Transformations":
                            _open_transform_dialog(sub_clicked)
                        elif OPEN_SUB_MENU == "Composite Transformations":
                            composite_types = {
                                "About a Point": "Transform About a Point",
                                "About an Axis": "Transform About an Axis",
                            }
                            _open_transform_dialog(composite_types[sub_clicked])

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
                elif clicked_item == "User Defined":
                    _open_pattern_dialog()
                    OPEN_MENU = None
                    OPEN_SUB_MENU = None

            elif OPEN_MENU == "Options":
                if "Undo" in clicked_item:
                    _do_undo()
                    OPEN_MENU = None
                    OPEN_SUB_MENU = None
                elif "Redo" in clicked_item:
                    _do_redo()
                    OPEN_MENU = None
                    OPEN_SUB_MENU = None
                elif clicked_item == "Clear":
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

            elif OPEN_MENU == "Transformations":
                if clicked_item in SUB_DROPDOWN:
                    OPEN_SUB_MENU = None if OPEN_SUB_MENU == clicked_item else clicked_item

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


# ============================================================================
# Endpoint Snap / Dumbbell Helpers
# ============================================================================

def _get_all_endpoints():
    """
    Collect every connectable endpoint from drawn_lines.
    Returns a list of (gx, gy) tuples (grid coordinates).
    """
    endpoints = []
    for shape in drawn_lines:
        stype = shape.get("type", "line")
        if stype == "line":
            endpoints.append(shape["p1"])
            endpoints.append(shape["p2"])
        elif stype == "circle":
            endpoints.append(shape["center"])
            endpoints.append(shape["radius_point"])
        elif stype == "ellipse":
            endpoints.append(shape["center"])
            endpoints.append(shape["rx_point"])
            endpoints.append(shape["ry_point"])
    return endpoints


def _snap_to_nearest_endpoint(gx, gy, pixel_threshold=None):
    """
    If (gx, gy) is within pixel_threshold screen pixels of any existing
    endpoint, return that endpoint instead.  Otherwise return (gx, gy)
    unchanged.  Also returns a bool indicating whether a snap occurred.
    """
    if pixel_threshold is None:
        pixel_threshold = SNAP_DISTANCE_PIXELS
    endpoints = _get_all_endpoints()
    best_dist = float('inf')
    best_pt = (gx, gy)
    for (ex, ey) in endpoints:
        dx = (gx - ex) * GRID_SIZE
        dy = (gy - ey) * GRID_SIZE
        d = math.sqrt(dx * dx + dy * dy)
        if d < best_dist:
            best_dist = d
            best_pt = (ex, ey)
    if best_dist <= pixel_threshold:
        return best_pt, True
    return (gx, gy), False


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

    # ── Dumbbell snap: connect to a nearby existing endpoint ─────────────
    (gx, gy), snapped = _snap_to_nearest_endpoint(gx, gy)
    if snapped:
        print(f"[Snap] Snapped to existing endpoint ({gx}, {gy})")

    print(f"[Click] Mouse: ({x}, {y}) → World: ({x_world:.1f}, {y_world:.1f}) → Grid: ({gx}, {gy})")

    selected_points.append((gx, gy))

    if is_ellipse_algorithm(CURRENT_ALGORITHM):
        # Ellipse mode: 3 clicks — centre, rx point, ry point (orthogonal)
        if len(selected_points) == 1:
            print(f"[Ellipse] Centre selected: ({gx}, {gy}). Click a point to define horizontal radius (rx).")
        elif len(selected_points) == 2:
            print(f"[Ellipse] rx point selected: ({gx}, {gy}). Click along the orthogonal line to define vertical radius (ry).")
        elif len(selected_points) == 3:
            centre = selected_points[0]
            rx_click = selected_points[1]
            ry_click = selected_points[2]
            
            dx1 = rx_click[0] - centre[0]
            dy1 = rx_click[1] - centre[1]
            dist1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
            rx = max(1, int(round_half_up(dist1)))
            
            angle = math.atan2(dy1, dx1) if dist1 > 0 else 0.0
            vx = -math.sin(angle)
            vy = math.cos(angle)
            
            # Project 3rd click onto orthogonal axis
            wx = ry_click[0] - centre[0]
            wy = ry_click[1] - centre[1]
            d_perp = wx * vx + wy * vy
            
            if abs(d_perp) >= 0.5:
                ry = max(1, int(round_half_up(abs(d_perp))))
                sign = 1 if d_perp >= 0 else -1
            else:
                dist2 = math.sqrt(wx * wx + wy * wy)
                ry = max(1, int(round_half_up(dist2))) if dist2 > 0 else 1
                sign = 1
                
            rx_pt = rx_click if dist1 > 0 else (centre[0] + 1, centre[1])
            ry_pt = (int(round_half_up(centre[0] + sign * ry * vx)),
                     int(round_half_up(centre[1] + sign * ry * vy)))

            # Compute ellipse points with rotation
            ellipse_pts = compute_ellipse_points(centre[0], centre[1], rx, ry, angle)

            ellipse_entry = {
                "type": "ellipse",
                "center": centre,
                "rx_point": rx_pt,
                "ry_point": ry_pt,
                "rx": rx,
                "ry": ry,
                "angle": angle,
                "algorithm": CURRENT_ALGORITHM,
                "color": CURRENT_COLOR,
                "width": CURRENT_LINE_WIDTH,
                "style": CURRENT_LINE_STYLE,
                "ellipse_points": ellipse_pts,
            }
            if CURRENT_LINE_STYLE == "UserDefined":
                ellipse_entry["pattern"] = CURRENT_USER_PATTERN

            # Start animation
            global ellipse_animation
            ellipse_animation["active"] = True
            ellipse_animation["phase"] = "rx"
            ellipse_animation["progress"] = 0.0
            ellipse_animation["entry"] = ellipse_entry

            print(f"[Ellipse] {CURRENT_ALGORITHM}: centre=({centre[0]},{centre[1]}), "
                  f"rx={rx}, ry={ry}, angle={math.degrees(angle):.1f}°, {len(ellipse_pts)} pixels, color={CURRENT_COLOR} - Animating...")

            # Start the timer loop
            glut.glutTimerFunc(ANIMATION_FRAME_MS, _ellipse_animation_tick, 0)

            # Reset selection
            selected_points = []

    elif is_circle_algorithm(CURRENT_ALGORITHM):
        # Circle mode: first click = centre, second click = radius point
        if len(selected_points) == 1:
            print(f"[Circle] Centre selected: ({gx}, {gy}). Click another point to define radius.")
        elif len(selected_points) == 2:
            centre = selected_points[0]
            radius_pt = selected_points[1]

            # Compute radius as integer distance
            dx = radius_pt[0] - centre[0]
            dy = radius_pt[1] - centre[1]
            r = int(round_half_up(math.sqrt(dx * dx + dy * dy)))

            # Compute circle points
            circle_pts = compute_circle_points(centre[0], centre[1], r)

            circle_entry = {
                "type": "circle",
                "center": centre,
                "radius_point": radius_pt,
                "radius": r,
                "algorithm": CURRENT_ALGORITHM,
                "color": CURRENT_COLOR,
                "width": CURRENT_LINE_WIDTH,
                "style": CURRENT_LINE_STYLE,
                "circle_points": circle_pts,
            }
            if CURRENT_LINE_STYLE == "UserDefined":
                circle_entry["pattern"] = CURRENT_USER_PATTERN
            
            # Start animation instead of appending instantly
            global circle_animation
            circle_animation["active"] = True
            circle_animation["phase"] = "radius"
            circle_animation["progress"] = 0.0
            circle_animation["entry"] = circle_entry

            print(f"[Circle] {CURRENT_ALGORITHM}: centre=({centre[0]},{centre[1]}), "
                  f"radius={r}, {len(circle_pts)} pixels, color={CURRENT_COLOR} - Animating...")
            
            # Start the timer loop
            glut.glutTimerFunc(ANIMATION_FRAME_MS, _animation_tick, 0)

            # Reset selection
            selected_points = []
    else:
        # Line mode: two endpoints
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
            line_entry = {
                "type": "line",
                "p1": p1,
                "p2": p2,
                "algorithm": CURRENT_ALGORITHM,
                "color": CURRENT_COLOR,
                "width": CURRENT_LINE_WIDTH,
                "style": CURRENT_LINE_STYLE,
                "line_points": line_pts,
            }
            if CURRENT_LINE_STYLE == "UserDefined":
                line_entry["pattern"] = CURRENT_USER_PATTERN
            _save_undo_state()
            drawn_lines.append(line_entry)

            print(f"[Line] {CURRENT_ALGORITHM}: ({p1[0]},{p1[1]}) → ({p2[0]},{p2[1]}), "
                  f"{len(line_pts)} pixels, color={CURRENT_COLOR}, width={CURRENT_LINE_WIDTH}, style={CURRENT_LINE_STYLE}")
            print(f"[Points] {line_pts}")

            # Reset selection
            selected_points = []
            
            # Ensure the drawn line shows up immediately without waiting for mouse move
            glut.glutPostRedisplay()
            
def passive_motion(x, y):
    """Update current mouse grid position for dynamic UI drawing."""
    global current_mouse_grid
    
    if y <= MENU_HEIGHT:
        if current_mouse_grid is not None:
            current_mouse_grid = None
            glut.glutPostRedisplay()
        return
        
    canvas_height = CURRENT_HEIGHT - MENU_HEIGHT
    x_world = x - CURRENT_WIDTH / 2.0
    y_world = (CURRENT_HEIGHT - y) - canvas_height / 2.0

    gx = int(round_half_up(x_world / GRID_SIZE))
    gy = int(round_half_up(y_world / GRID_SIZE))

    # Live magnetic snapping to existing dumbbell endpoints
    (snap_gx, snap_gy), _ = _snap_to_nearest_endpoint(gx, gy)
    
    if current_mouse_grid != (snap_gx, snap_gy):
        current_mouse_grid = (snap_gx, snap_gy)
        glut.glutPostRedisplay()


def mouse(button, state, x, y):
    """
    Handle mouse input and determine whether the click
    occurred on the menu, dropdown, or canvas.
    """

    global OPEN_MENU, OPEN_SUB_MENU, SAVE_DIALOG_OPEN, SAVE_DIALOG_TEXT
    global PATTERN_DIALOG_OPEN

    # Only handle left mouse button.
    if button != glut.GLUT_LEFT_BUTTON:
        return

    # Only handle button press.
    if state != glut.GLUT_DOWN:
        return

    # ── If transform dialog is open, handle its button clicks ─────────────
    if TRANSFORM_DIALOG_OPEN:
        _handle_transform_dialog_click(x, y)
        return

    # ── If pattern dialog is open, handle its button clicks ──────────────
    if PATTERN_DIALOG_OPEN:
        _handle_pattern_dialog_click(x, y)
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
            if y < MENU_BUTTON_HEIGHT:
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
        if y < MENU_BUTTON_HEIGHT:
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
    if drawn_lines:
        _save_undo_state()
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
    for shape in drawn_lines:
        shape_type = shape.get("type", "line")
        if shape_type == "circle":
            entry = {
                "type": "circle",
                "center": list(shape["center"]),
                "radius_point": list(shape["radius_point"]),
                "radius": shape["radius"],
                "algorithm": shape["algorithm"],
                "color": shape["color"],
                "width": shape["width"],
                "style": shape.get("style", "Solid"),
            }
            if shape.get("style") == "UserDefined" and "pattern" in shape:
                entry["pattern"] = shape["pattern"]
        elif shape_type == "ellipse":
            entry = {
                "type": "ellipse",
                "center": list(shape["center"]),
                "rx_point": list(shape.get("rx_point", shape["center"])),
                "ry_point": list(shape.get("ry_point", shape["center"])),
                "rx": shape["rx"],
                "ry": shape["ry"],
                "angle": shape.get("angle", 0.0),
                "algorithm": shape["algorithm"],
                "color": shape["color"],
                "width": shape["width"],
                "style": shape.get("style", "Solid"),
            }
            if shape.get("style") == "UserDefined" and "pattern" in shape:
                entry["pattern"] = shape["pattern"]
        else:
            entry = {
                "type": "line",
                "p1": list(shape["p1"]),
                "p2": list(shape["p2"]),
                "algorithm": shape["algorithm"],
                "color": shape["color"],
                "width": shape["width"],
                "style": shape.get("style", "Solid"),
            }
            if shape.get("style") == "UserDefined" and "pattern" in shape:
                entry["pattern"] = shape["pattern"]
        save_data.append(entry)

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


def _open_pattern_dialog():
    """
    Open the pattern input dialog so the user can enter a custom hexadecimal line pattern.
    """
    global PATTERN_DIALOG_OPEN, PATTERN_DIALOG_TEXT
    PATTERN_DIALOG_TEXT = ""
    PATTERN_DIALOG_OPEN = True
    glut.glutPostRedisplay()


def _confirm_pattern():
    """
    Apply the user-entered hex pattern and set line style to UserDefined.
    """
    global PATTERN_DIALOG_OPEN, PATTERN_DIALOG_TEXT
    global CURRENT_LINE_STYLE, CURRENT_USER_PATTERN, CURRENT_USER_PATTERN_HEX

    raw_input = PATTERN_DIALOG_TEXT.strip() if PATTERN_DIALOG_TEXT.strip() else CURRENT_USER_PATTERN_HEX
    hex_str, bin_str = hex_to_binary_pattern(raw_input)

    # Validate: must contain at least one '1' bit
    if not any(c == '1' for c in bin_str):
        print("[Pattern] Invalid pattern — must contain at least one non-zero bit. Using 0xF0F0.")
        hex_str, bin_str = "0xF0F0", "1111000011110000"

    CURRENT_USER_PATTERN_HEX = hex_str
    CURRENT_USER_PATTERN = bin_str
    CURRENT_LINE_STYLE = "UserDefined"
    print(f"[Pattern] Set to: {CURRENT_USER_PATTERN_HEX} (Binary mask: {CURRENT_USER_PATTERN})")

    PATTERN_DIALOG_OPEN = False
    PATTERN_DIALOG_TEXT = ""
    glut.glutPostRedisplay()


def _handle_pattern_dialog_click(x, y):
    """
    Handle mouse clicks when the pattern dialog is open.
    Check if Apply, Cancel, or preset chip buttons were clicked.
    """
    global PATTERN_DIALOG_OPEN, PATTERN_DIALOG_TEXT

    dialog_w = 500
    dialog_h = 250
    dlg_left = (CURRENT_WIDTH - dialog_w) / 2
    dlg_right = dlg_left + dialog_w
    dlg_top  = (CURRENT_HEIGHT - dialog_h) / 2
    dlg_bottom = dlg_top + dialog_h

    # Check Preset chips
    chip_y_top = dlg_top + 150
    chip_y_bot = chip_y_top + 24
    if chip_y_top <= y <= chip_y_bot:
        chips = [
            (dlg_left + 75, dlg_left + 155, "0xF0F0"),
            (dlg_left + 165, dlg_left + 245, "0xAAAA"),
            (dlg_left + 255, dlg_left + 335, "0x1C47"),
            (dlg_left + 345, dlg_left + 425, "0x00FF"),
        ]
        for (cx1, cx2, val) in chips:
            if cx1 <= x <= cx2:
                PATTERN_DIALOG_TEXT = val
                glut.glutPostRedisplay()
                return

    btn_w = 90
    btn_h = 30
    btn_y_top = dlg_bottom - 16 - btn_h
    btn_y_bot = btn_y_top + btn_h

    apply_btn_left = dlg_right - 20 - btn_w
    apply_btn_right = apply_btn_left + btn_w

    cancel_btn_left = apply_btn_left - btn_w - 12
    cancel_btn_right = cancel_btn_left + btn_w

    if btn_y_top <= y <= btn_y_bot:
        if apply_btn_left <= x <= apply_btn_right:
            _confirm_pattern()
            return
        if cancel_btn_left <= x <= cancel_btn_right:
            PATTERN_DIALOG_OPEN = False
            PATTERN_DIALOG_TEXT = ""
            print("[Pattern] Cancelled.")
            glut.glutPostRedisplay()
            return

    # Click anywhere else — keep dialog open (modal behavior)


# ============================================================================
# Transformation Dialog Logic
# ============================================================================

def _open_transform_dialog(transform_type):
    """
    Open the transformation parameter input dialog for the given type.
    """
    global TRANSFORM_DIALOG_OPEN, TRANSFORM_DIALOG_TYPE
    global TRANSFORM_DIALOG_FIELDS, TRANSFORM_DIALOG_FIELD_ORDER
    global TRANSFORM_DIALOG_ACTIVE_FIELD

    TRANSFORM_DIALOG_TYPE = transform_type

    if transform_type == "Translation":
        TRANSFORM_DIALOG_FIELDS = {"tx": "", "ty": ""}
        TRANSFORM_DIALOG_FIELD_ORDER = ["tx", "ty"]
    elif transform_type == "Scaling":
        TRANSFORM_DIALOG_FIELDS = {"sx": "", "sy": ""}
        TRANSFORM_DIALOG_FIELD_ORDER = ["sx", "sy"]
    elif transform_type == "Rotation":
        TRANSFORM_DIALOG_FIELDS = {"angle": ""}
        TRANSFORM_DIALOG_FIELD_ORDER = ["angle"]
    elif transform_type == "Transform About a Point":
        # T(pivot) · R(θ) · S(sx, sy) · T(-pivot)
        TRANSFORM_DIALOG_FIELDS = {
            "pivot_x": "", "pivot_y": "", "angle": "", "sx": "", "sy": "",
        }
        TRANSFORM_DIALOG_FIELD_ORDER = ["pivot_x", "pivot_y", "angle", "sx", "sy"]
    elif transform_type == "Transform About an Axis":
        # The axis is an arbitrary line represented by two points.
        TRANSFORM_DIALOG_FIELDS = {"axis_x1": "", "axis_y1": "", "axis_x2": "", "axis_y2": ""}
        TRANSFORM_DIALOG_FIELD_ORDER = ["axis_x1", "axis_y1", "axis_x2", "axis_y2"]
    else:
        return

    TRANSFORM_DIALOG_ACTIVE_FIELD = 0
    TRANSFORM_DIALOG_OPEN = True
    print(f"[Transform] Opening {transform_type} dialog.")
    glut.glutPostRedisplay()


def _safe_parse_transform_float(val, default):
    """
    Safely convert dialog string to float.
    Treats empty or incomplete sign strings ('-', '+', '.') as default.
    """
    try:
        s = str(val or "").strip()
        if s in ("", "-", "+", ".", "-.", "+."):
            return float(default)
        return float(s)
    except (ValueError, TypeError):
        return float(default)


def _compose_transform_matrices(*matrices):
    """Return the product of 3×3 homogeneous matrices."""
    return compose_transformations(*matrices)


def _confirm_transform():
    """
    Parse the dialog input values, build the transformation matrix,
    and apply it to all drawn shapes on the canvas.
    """
    global TRANSFORM_DIALOG_OPEN

    try:
        if TRANSFORM_DIALOG_TYPE == "Translation":
            tx = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("tx"), 0.0)
            ty = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("ty"), 0.0)
            M = translation_matrix(tx, ty)
            print(f"[Transform] Translation: tx={tx}, ty={ty}")

        elif TRANSFORM_DIALOG_TYPE == "Scaling":
            sx = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("sx"), 1.0)
            sy = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("sy"), 1.0)
            if sx == 0.0:
                sx = 1.0
            if sy == 0.0:
                sy = 1.0
            M = scaling_matrix(sx, sy)
            print(f"[Transform] Scaling: sx={sx}, sy={sy}")

        elif TRANSFORM_DIALOG_TYPE == "Rotation":
            angle = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("angle"), 0.0)
            M = rotation_matrix(angle)
            print(f"[Transform] Rotation: angle={angle}°")

        elif TRANSFORM_DIALOG_TYPE == "Transform About a Point":
            pivot_x = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("pivot_x"), 0.0)
            pivot_y = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("pivot_y"), 0.0)
            angle = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("angle"), 0.0)
            sx = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("sx"), 1.0)
            sy = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("sy"), 1.0)
            M = transform_about_point_matrix(pivot_x, pivot_y, angle_deg=angle, sx=sx, sy=sy)
            print(
                "[Transform] About point "
                f"({pivot_x}, {pivot_y}): rotate={angle}°, scale=({sx}, {sy})"
            )

        elif TRANSFORM_DIALOG_TYPE == "Transform About an Axis":
            x1 = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("axis_x1"), 0.0)
            y1 = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("axis_y1"), 0.0)
            x2 = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("axis_x2"), 1.0)
            y2 = _safe_parse_transform_float(TRANSFORM_DIALOG_FIELDS.get("axis_y2"), 0.0)
            dx, dy = x2 - x1, y2 - y1
            if dx == 0.0 and dy == 0.0:
                print("[Transform] Axis needs two different points.")
                return

            M = transform_about_axis_matrix(x1, y1, x2, y2)
            print(f"[Transform] Reflection about axis through ({x1}, {y1}) and ({x2}, {y2})")

        else:
            print(f"[Transform] Unknown type: {TRANSFORM_DIALOG_TYPE}")
            TRANSFORM_DIALOG_OPEN = False
            glut.glutPostRedisplay()
            return

    except Exception as e:
        print(f"[Transform] Error constructing matrix: {e}")
        return

    _apply_transform_to_shapes(M)

    TRANSFORM_DIALOG_OPEN = False
    glut.glutPostRedisplay()


def _apply_transform_to_shapes(M):
    """
    Apply a 3×3 homogeneous transformation matrix M to all drawn shapes.
    Transforms the control points and recomputes the rasterised pixels.
    """
    global drawn_lines

    if not drawn_lines:
        print("[Transform] No shapes on canvas to transform.")
        return

    _save_undo_state()

    for shape in drawn_lines:
        shape_type = shape.get("type", "line")

        if shape_type == "line":
            # Transform endpoints
            p1 = shape["p1"]
            p2 = shape["p2"]
            np1 = mat3_transform_point(M, p1[0], p1[1])
            np2 = mat3_transform_point(M, p2[0], p2[1])
            shape["p1"] = (int(round_half_up(np1[0])), int(round_half_up(np1[1])))
            shape["p2"] = (int(round_half_up(np2[0])), int(round_half_up(np2[1])))

            # Recompute rasterised points
            shape["line_points"] = compute_line_points(
                shape.get("algorithm", "Bresenham"),
                shape["p1"][0], shape["p1"][1],
                shape["p2"][0], shape["p2"][1],
            )
            print(f"  [Line] ({p1}) → ({shape['p1']}), ({p2}) → ({shape['p2']})")

        elif shape_type == "circle":
            # Transform centre
            c = shape["center"]
            nc = mat3_transform_point(M, c[0], c[1])
            shape["center"] = (int(round_half_up(nc[0])), int(round_half_up(nc[1])))

            # Transform radius point to get new radius
            rp = shape.get("radius_point", (c[0] + shape["radius"], c[1]))
            nrp = mat3_transform_point(M, rp[0], rp[1])
            shape["radius_point"] = (int(round_half_up(nrp[0])), int(round_half_up(nrp[1])))

            # Recalculate radius from transformed points
            dx = shape["radius_point"][0] - shape["center"][0]
            dy = shape["radius_point"][1] - shape["center"][1]
            shape["radius"] = max(1, int(round_half_up(math.sqrt(dx*dx + dy*dy))))

            # Recompute circle points
            shape["circle_points"] = compute_circle_points(
                shape["center"][0], shape["center"][1], shape["radius"]
            )
            print(f"  [Circle] centre ({c}) → ({shape['center']}), r={shape['radius']}")

        elif shape_type == "ellipse":
            # Transform centre
            c = shape["center"]
            nc = mat3_transform_point(M, c[0], c[1])
            shape["center"] = (int(round_half_up(nc[0])), int(round_half_up(nc[1])))

            # Transform rx and ry points
            rx_pt = shape.get("rx_point", (c[0] + shape["rx"], c[1]))
            ry_pt = shape.get("ry_point", (c[0], c[1] + shape["ry"]))
            nrx = mat3_transform_point(M, rx_pt[0], rx_pt[1])
            nry = mat3_transform_point(M, ry_pt[0], ry_pt[1])
            shape["rx_point"] = (int(round_half_up(nrx[0])), int(round_half_up(nrx[1])))
            shape["ry_point"] = (int(round_half_up(nry[0])), int(round_half_up(nry[1])))

            # Recalculate radii
            dx1 = shape["rx_point"][0] - shape["center"][0]
            dy1 = shape["rx_point"][1] - shape["center"][1]
            shape["rx"] = max(1, int(round_half_up(math.sqrt(dx1*dx1 + dy1*dy1))))
            shape["angle"] = math.atan2(dy1, dx1) if (dx1 != 0 or dy1 != 0) else 0.0

            dx2 = shape["ry_point"][0] - shape["center"][0]
            dy2 = shape["ry_point"][1] - shape["center"][1]
            shape["ry"] = max(1, int(round_half_up(math.sqrt(dx2*dx2 + dy2*dy2))))

            # Recompute ellipse points
            shape["ellipse_points"] = compute_ellipse_points(
                shape["center"][0], shape["center"][1],
                shape["rx"], shape["ry"], shape.get("angle", 0.0)
            )
            print(f"  [Ellipse] centre ({c}) → ({shape['center']}), rx={shape['rx']}, ry={shape['ry']}")

    print(f"[Transform] Applied to {len(drawn_lines)} shape(s).")


def _handle_transform_dialog_click(x, y):
    """
    Handle mouse clicks when the transform dialog is open.
    Check if Apply or Cancel buttons were clicked, or if a field was clicked.
    """
    global TRANSFORM_DIALOG_OPEN, TRANSFORM_DIALOG_ACTIVE_FIELD

    dialog_w = 460
    dialog_h = 60 + len(TRANSFORM_DIALOG_FIELD_ORDER) * 60 + 100
    dlg_left = (CURRENT_WIDTH - dialog_w) / 2
    dlg_right = dlg_left + dialog_w
    dlg_top  = (CURRENT_HEIGHT - dialog_h) / 2
    dlg_bottom = dlg_top + dialog_h

    # Check field clicks — switch active field (matching field_y_top = dlg_top + 55 + fi * 60)
    for fi, fname in enumerate(TRANSFORM_DIALOG_FIELD_ORDER):
        field_top = dlg_top + 55 + fi * 60
        field_bottom = field_top + 30
        field_left = dlg_left + 100
        field_right = dlg_right - 20
        if field_left <= x <= field_right and field_top <= y <= field_bottom:
            TRANSFORM_DIALOG_ACTIVE_FIELD = fi
            glut.glutPostRedisplay()
            return

    # Check buttons
    btn_w = 90
    btn_h = 32
    btn_y_top = dlg_bottom - 18 - btn_h
    btn_y_bot = btn_y_top + btn_h

    apply_btn_left = dlg_right - 20 - btn_w
    apply_btn_right = apply_btn_left + btn_w

    cancel_btn_left = apply_btn_left - btn_w - 12
    cancel_btn_right = cancel_btn_left + btn_w

    if btn_y_top <= y <= btn_y_bot:
        if apply_btn_left <= x <= apply_btn_right:
            _confirm_transform()
            return
        if cancel_btn_left <= x <= cancel_btn_right:
            TRANSFORM_DIALOG_OPEN = False
            print("[Transform] Cancelled.")
            glut.glutPostRedisplay()
            return

    # Click anywhere else — keep dialog open (modal behavior)


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
    if drawn_lines:
        _save_undo_state()
    drawn_lines.clear()
    selected_points.clear()

    # Reconstruct shapes (lines, circles, and ellipses)
    for entry in save_data:
        shape_type = entry.get("type", "line")
        algorithm = entry.get("algorithm", "Bresenham")
        color = entry.get("color", "Red")
        width = entry.get("width", 1)

        if shape_type == "circle":
            centre = tuple(entry["center"])
            radius_pt = tuple(entry.get("radius_point", centre))
            r = entry.get("radius", 0)
            style = entry.get("style", "Solid")
            pattern = entry.get("pattern", "11110000")
            circle_pts = compute_circle_points(centre[0], centre[1], r)
            circle_entry = {
                "type": "circle",
                "center": centre,
                "radius_point": radius_pt,
                "radius": r,
                "algorithm": algorithm,
                "color": color,
                "width": width,
                "style": style,
                "circle_points": circle_pts,
            }
            if style == "UserDefined":
                circle_entry["pattern"] = pattern
            drawn_lines.append(circle_entry)
        elif shape_type == "ellipse":
            centre = tuple(entry["center"])
            rx_pt = tuple(entry.get("rx_point", centre))
            ry_pt = tuple(entry.get("ry_point", centre))
            erx = entry.get("rx", 1)
            ery = entry.get("ry", 1)
            style = entry.get("style", "Solid")
            pattern = entry.get("pattern", "11110000")
            if "angle" in entry:
                angle = entry["angle"]
            elif rx_pt != centre:
                angle = math.atan2(rx_pt[1] - centre[1], rx_pt[0] - centre[0])
            else:
                angle = 0.0
            ellipse_pts = compute_ellipse_points(centre[0], centre[1], erx, ery, angle)
            ellipse_entry = {
                "type": "ellipse",
                "center": centre,
                "rx_point": rx_pt,
                "ry_point": ry_pt,
                "rx": erx,
                "ry": ery,
                "angle": angle,
                "algorithm": algorithm,
                "color": color,
                "width": width,
                "style": style,
                "ellipse_points": ellipse_pts,
            }
            if style == "UserDefined":
                ellipse_entry["pattern"] = pattern
            drawn_lines.append(ellipse_entry)
        else:
            p1 = tuple(entry["p1"])
            p2 = tuple(entry["p2"])
            style = entry.get("style", "Solid")
            pattern = entry.get("pattern", "11110000")

            line_pts = compute_line_points(algorithm, p1[0], p1[1], p2[0], p2[1])

            line_entry = {
                "type": "line",
                "p1": p1,
                "p2": p2,
                "algorithm": algorithm,
                "color": color,
                "width": width,
                "style": style,
                "line_points": line_pts,
            }
            if style == "UserDefined":
                line_entry["pattern"] = pattern
            drawn_lines.append(line_entry)

    selected_points = []
    print(f"[Import] Loaded {len(save_data)} shapes from {filename}")
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


def _draw_user_defined_pattern(x1, y1, x2, y2, length, ux, uy, width, pattern):
    """
    Draw a line using a user-defined pattern string (hex or binary).
    '1' = draw a pixel-sized segment, '0' = skip (gap).
    The pattern repeats along the line.
    Each pattern character corresponds to 'step_size' pixels of the line.
    """
    pattern = get_binary_pattern(pattern)
    pat_len = len(pattern)
    # Scale each pattern character to cover ~4 pixels so the pattern is visible
    step_size = 4.0

    dist = 0.0
    pat_idx = 0
    drawing = False
    seg_start_x = seg_start_y = 0.0

    gl.glBegin(gl.GL_LINES)
    while dist <= length:
        ch = pattern[pat_idx % pat_len]

        if ch == '1':
            if not drawing:
                # Start a new drawn segment
                seg_start_x = x1 + ux * dist
                seg_start_y = y1 + uy * dist
                drawing = True
        else:
            if drawing:
                # End the current drawn segment
                seg_end_x = x1 + ux * dist
                seg_end_y = y1 + uy * dist
                gl.glVertex2f(seg_start_x, seg_start_y)
                gl.glVertex2f(seg_end_x, seg_end_y)
                drawing = False

        dist += step_size
        pat_idx += 1

    # If we were still drawing at the end, close the segment to the endpoint
    if drawing:
        gl.glVertex2f(seg_start_x, seg_start_y)
        gl.glVertex2f(x2, y2)

    gl.glEnd()


def _draw_styled_line(x1, y1, x2, y2, style, width, user_pattern=""):
    """
    Draw a line from (x1,y1) to (x2,y2) with the given style.
    For 'Dotted' and 'Dashed', manually break the line into segments
    because GL_LINE_STIPPLE is deprecated and broken on macOS.
    For 'UserDefined', use the user-supplied binary pattern string.
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

    # ── User-defined pattern (binary string) ─────────────────────────────
    if style == "UserDefined":
        _draw_user_defined_pattern(x1, y1, x2, y2, length, ux, uy, width, user_pattern)
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


def _draw_circle_filled_point(cx, cy, radius=3, segments=16):
    """Draw a small filled circle at canvas coordinates (cx, cy)."""
    gl.glBegin(gl.GL_POLYGON)
    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        gl.glVertex2f(cx + radius * math.cos(theta),
                      cy + radius * math.sin(theta))
    gl.glEnd()


def _draw_styled_circle(cx, cy, r, style, width, user_pattern=""):
    """
    Draw a smooth circle at (cx, cy) with radius r using the given style.
    cx, cy, and r are in pixels (already multiplied by GRID_SIZE).
    """
    if r <= 0:
        return
        
    circumference = 2 * math.pi * r
    # Number of segments for smooth circle (more segments for larger circles)
    segments = max(64, int(circumference / 2))
    
    if style == "Solid":
        gl.glBegin(gl.GL_LINE_LOOP)
        for i in range(segments):
            theta = 2.0 * math.pi * i / segments
            gl.glVertex2f(cx + r * math.cos(theta), cy + r * math.sin(theta))
        gl.glEnd()
        return

    if style == "UserDefined":
        user_pattern = get_binary_pattern(user_pattern)
        pat_len = len(user_pattern)
        step_size = 4.0  # pixels per pattern character
        
        gl.glBegin(gl.GL_LINES)
        dist = 0.0
        pat_idx = 0
        drawing = False
        seg_start_theta = 0
        
        while dist <= circumference:
            char = user_pattern[pat_idx % pat_len]
            theta = (dist / circumference) * 2.0 * math.pi
            
            if char == '1':
                if not drawing:
                    seg_start_theta = theta
                    drawing = True
            else:
                if drawing:
                    # Draw curved segment
                    dash_dist = (seg_start_theta / (2.0 * math.pi)) * circumference
                    while dash_dist < dist:
                        next_dist = min(dash_dist + 4.0, dist)
                        t1 = (dash_dist / circumference) * 2.0 * math.pi
                        t2 = (next_dist / circumference) * 2.0 * math.pi
                        gl.glVertex2f(cx + r * math.cos(t1), cy + r * math.sin(t1))
                        gl.glVertex2f(cx + r * math.cos(t2), cy + r * math.sin(t2))
                        dash_dist = next_dist
                    drawing = False
                    
            dist += step_size
            pat_idx += 1
            
        if drawing:
            theta = 2.0 * math.pi
            dash_dist = (seg_start_theta / (2.0 * math.pi)) * circumference
            while dash_dist < circumference:
                next_dist = min(dash_dist + 4.0, circumference)
                t1 = (dash_dist / circumference) * 2.0 * math.pi
                t2 = (next_dist / circumference) * 2.0 * math.pi
                gl.glVertex2f(cx + r * math.cos(t1), cy + r * math.sin(t1))
                gl.glVertex2f(cx + r * math.cos(t2), cy + r * math.sin(t2))
                dash_dist = next_dist
        gl.glEnd()
        return

    if style == "Dotted":
        dot_spacing = 6.0
        gl.glEnable(gl.GL_POINT_SMOOTH)
        gl.glPointSize(width if width > 1 else 2.0)
        gl.glBegin(gl.GL_POINTS)
        dist = 0.0
        while dist <= circumference:
            theta = (dist / circumference) * 2.0 * math.pi
            gl.glVertex2f(cx + r * math.cos(theta), cy + r * math.sin(theta))
            dist += dot_spacing
        gl.glEnd()
        gl.glDisable(gl.GL_POINT_SMOOTH)
        return

    # Dashed
    draw_len, gap_len = 12.0, 8.0
    pattern_len = draw_len + gap_len
    
    gl.glBegin(gl.GL_LINES)
    dist = 0.0
    while dist < circumference:
        seg_start = dist
        seg_end = min(dist + draw_len, circumference)
        
        # Draw curved dash segment
        dash_dist = seg_start
        while dash_dist < seg_end:
            next_dist = min(dash_dist + 4.0, seg_end)
            t1 = (dash_dist / circumference) * 2.0 * math.pi
            t2 = (next_dist / circumference) * 2.0 * math.pi
            gl.glVertex2f(cx + r * math.cos(t1), cy + r * math.sin(t1))
            gl.glVertex2f(cx + r * math.cos(t2), cy + r * math.sin(t2))
            dash_dist = next_dist
            
        dist += pattern_len
    gl.glEnd()


def _animation_tick(value):
    """Timer callback to step the circle drawing animation (radius creation guide then flowing points)."""
    if not circle_animation["active"]:
        return

    phase = circle_animation["phase"]
    
    if phase == "radius":
        circle_animation["progress"] += ANIMATION_RADIUS_SPEED
        if circle_animation["progress"] >= 1.0:
            circle_animation["progress"] = 0.0
            circle_animation["phase"] = "points"
    elif phase == "points":
        pts_len = len(circle_animation["entry"]["circle_points"])
        circle_animation["progress"] += max(2.0, pts_len / ANIMATION_POINTS_FRAMES)
        if circle_animation["progress"] >= pts_len:
            circle_animation["progress"] = pts_len
            # Animation finished -> add finalized shape to drawn_lines
            _save_undo_state()
            drawn_lines.append(circle_animation["entry"])
            circle_animation["active"] = False
            glut.glutPostRedisplay()
            return

    glut.glutPostRedisplay()
    glut.glutTimerFunc(ANIMATION_FRAME_MS, _animation_tick, 0)


def _ellipse_animation_tick(value):
    """Timer callback to step the ellipse drawing animation (rx & ry guides then flowing points)."""
    if not ellipse_animation["active"]:
        return

    phase = ellipse_animation["phase"]

    if phase == "rx":
        ellipse_animation["progress"] += ANIMATION_RADIUS_SPEED
        if ellipse_animation["progress"] >= 1.0:
            ellipse_animation["progress"] = 0.0
            ellipse_animation["phase"] = "ry"
    elif phase == "ry":
        ellipse_animation["progress"] += ANIMATION_RADIUS_SPEED
        if ellipse_animation["progress"] >= 1.0:
            ellipse_animation["progress"] = 0.0
            ellipse_animation["phase"] = "points"
    elif phase == "points":
        pts_len = len(ellipse_animation["entry"]["ellipse_points"])
        ellipse_animation["progress"] += max(2.0, pts_len / ANIMATION_POINTS_FRAMES)
        if ellipse_animation["progress"] >= pts_len:
            ellipse_animation["progress"] = pts_len
            # Animation finished -> add finalized shape to drawn_lines
            _save_undo_state()
            drawn_lines.append(ellipse_animation["entry"])
            ellipse_animation["active"] = False
            glut.glutPostRedisplay()
            return

    glut.glutPostRedisplay()
    glut.glutTimerFunc(ANIMATION_FRAME_MS, _ellipse_animation_tick, 0)


def _draw_styled_ellipse(cx, cy, rx, ry, style, width, user_pattern=""):
    """
    Draw a smooth ellipse at (cx, cy) with semi-axes rx, ry using the given style.
    cx, cy, rx, ry are in pixels (already multiplied by GRID_SIZE).
    """
    if rx <= 0 and ry <= 0:
        return

    # Approximate ellipse circumference using Ramanujan's approximation
    circ = math.pi * (3 * (rx + ry) - math.sqrt((3 * rx + ry) * (rx + 3 * ry)))
    segments = max(64, int(circ / 2))

    if style == "Solid":
        gl.glBegin(gl.GL_LINE_LOOP)
        for i in range(segments):
            theta = 2.0 * math.pi * i / segments
            gl.glVertex2f(cx + rx * math.cos(theta), cy + ry * math.sin(theta))
        gl.glEnd()
        return

    circumference = circ

    if style == "UserDefined":
        user_pattern = get_binary_pattern(user_pattern)
        pat_len = len(user_pattern)
        step_size = 4.0

        gl.glBegin(gl.GL_LINES)
        dist = 0.0
        pat_idx = 0
        drawing = False
        seg_start_theta = 0

        while dist <= circumference:
            char = user_pattern[pat_idx % pat_len]
            theta = (dist / circumference) * 2.0 * math.pi

            if char == '1':
                if not drawing:
                    seg_start_theta = theta
                    drawing = True
            else:
                if drawing:
                    dash_dist = (seg_start_theta / (2.0 * math.pi)) * circumference
                    while dash_dist < dist:
                        next_dist = min(dash_dist + 4.0, dist)
                        t1 = (dash_dist / circumference) * 2.0 * math.pi
                        t2 = (next_dist / circumference) * 2.0 * math.pi
                        gl.glVertex2f(cx + rx * math.cos(t1), cy + ry * math.sin(t1))
                        gl.glVertex2f(cx + rx * math.cos(t2), cy + ry * math.sin(t2))
                        dash_dist = next_dist
                    drawing = False

            dist += step_size
            pat_idx += 1

        if drawing:
            dash_dist = (seg_start_theta / (2.0 * math.pi)) * circumference
            while dash_dist < circumference:
                next_dist = min(dash_dist + 4.0, circumference)
                t1 = (dash_dist / circumference) * 2.0 * math.pi
                t2 = (next_dist / circumference) * 2.0 * math.pi
                gl.glVertex2f(cx + rx * math.cos(t1), cy + ry * math.sin(t1))
                gl.glVertex2f(cx + rx * math.cos(t2), cy + ry * math.sin(t2))
                dash_dist = next_dist
        gl.glEnd()
        return

    if style == "Dotted":
        dot_spacing = 6.0
        gl.glEnable(gl.GL_POINT_SMOOTH)
        gl.glPointSize(width if width > 1 else 2.0)
        gl.glBegin(gl.GL_POINTS)
        dist = 0.0
        while dist <= circumference:
            theta = (dist / circumference) * 2.0 * math.pi
            gl.glVertex2f(cx + rx * math.cos(theta), cy + ry * math.sin(theta))
            dist += dot_spacing
        gl.glEnd()
        gl.glDisable(gl.GL_POINT_SMOOTH)
        return

    # Dashed
    draw_len, gap_len = 12.0, 8.0
    pattern_len = draw_len + gap_len

    gl.glBegin(gl.GL_LINES)
    dist = 0.0
    while dist < circumference:
        seg_start = dist
        seg_end = min(dist + draw_len, circumference)

        dash_dist = seg_start
        while dash_dist < seg_end:
            next_dist = min(dash_dist + 4.0, seg_end)
            t1 = (dash_dist / circumference) * 2.0 * math.pi
            t2 = (next_dist / circumference) * 2.0 * math.pi
            gl.glVertex2f(cx + rx * math.cos(t1), cy + ry * math.sin(t1))
            gl.glVertex2f(cx + rx * math.cos(t2), cy + ry * math.sin(t2))
            dash_dist = next_dist

        dist += pattern_len
    gl.glEnd()


def _draw_algorithm_points_with_style(pts, style, width, user_pattern, close_loop=False):
    """
    Draw a list of computed points with the specified line style,
    without using GL_LINE_STIPPLE which is buggy on macOS for complex shapes.
    """
    if not pts:
        return

    def get_pt(i):
        return (pts[i][0] * GRID_SIZE, pts[i][1] * GRID_SIZE)

    if style == "Solid":
        gl.glBegin(gl.GL_LINE_STRIP)
        for i in range(len(pts)):
            pt = get_pt(i)
            gl.glVertex2f(pt[0], pt[1])
        if close_loop:
            pt = get_pt(0)
            gl.glVertex2f(pt[0], pt[1])
        gl.glEnd()
        return

    if style == "Dotted":
        dot_spacing = 6.0
        gl.glEnable(gl.GL_POINT_SMOOTH)
        gl.glPointSize(width if width > 1 else 2.0)
        gl.glBegin(gl.GL_POINTS)
        
        dist_acc = 0.0
        for i in range(len(pts)):
            if i == 0:
                pt = get_pt(i)
                gl.glVertex2f(pt[0], pt[1])
            else:
                p1 = get_pt(i-1)
                p2 = get_pt(i)
                dist_acc += math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
                if dist_acc >= dot_spacing:
                    gl.glVertex2f(p2[0], p2[1])
                    dist_acc = 0.0
                    
        gl.glEnd()
        gl.glDisable(gl.GL_POINT_SMOOTH)
        return

    if style == "UserDefined":
        user_pattern = get_binary_pattern(user_pattern)
        pat_len = len(user_pattern)
        step_size = 4.0
        
        dist_acc = 0.0
        pat_idx = 0
        drawing = user_pattern[0] == '1'
        
        if drawing:
            gl.glBegin(gl.GL_LINE_STRIP)
            pt = get_pt(0)
            gl.glVertex2f(pt[0], pt[1])
            
        for i in range(1, len(pts)):
            p1 = get_pt(i-1)
            p2 = get_pt(i)
            dist_acc += math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            
            curr_char = user_pattern[pat_idx % pat_len]
            if curr_char == '1':
                if not drawing:
                    drawing = True
                    gl.glBegin(gl.GL_LINE_STRIP)
                    gl.glVertex2f(p1[0], p1[1])
                gl.glVertex2f(p2[0], p2[1])
            else:
                if drawing:
                    drawing = False
                    gl.glEnd()
                    
            if dist_acc >= step_size:
                pat_idx += int(dist_acc // step_size)
                dist_acc = dist_acc % step_size
                
        if close_loop and drawing:
            pt = get_pt(0)
            gl.glVertex2f(pt[0], pt[1])
            
        if drawing:
            gl.glEnd()
        return

    # Dashed
    draw_len, gap_len = 12.0, 8.0
    
    dist_acc = 0.0
    drawing = True
    
    gl.glBegin(gl.GL_LINE_STRIP)
    pt = get_pt(0)
    gl.glVertex2f(pt[0], pt[1])
    
    for i in range(1, len(pts)):
        p1 = get_pt(i-1)
        p2 = get_pt(i)
        dist_acc += math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        
        if drawing:
            gl.glVertex2f(p2[0], p2[1])
            if dist_acc >= draw_len:
                gl.glEnd()
                drawing = False
                dist_acc -= draw_len
        else:
            if dist_acc >= gap_len:
                drawing = True
                dist_acc -= gap_len
                gl.glBegin(gl.GL_LINE_STRIP)
                gl.glVertex2f(p2[0], p2[1])
                
    if drawing:
        if close_loop:
            pt = get_pt(0)
            gl.glVertex2f(pt[0], pt[1])
        gl.glEnd()


LIGHT_GUIDE_COLOR = (0.60, 0.60, 0.65)
ORTHOGONAL_GUIDE_COLOR = (0.30, 0.60, 0.95)
PROJECTION_LINE_COLOR = (0.70, 0.70, 0.75)


def _draw_canvas_label(x, y, text, align="center", text_color=(0.10, 0.12, 0.18),
                       bg_color=(1.0, 1.0, 1.0, 0.94), border_color=(0.72, 0.74, 0.80)):
    """
    Render a clean, high-contrast label with a crisp background badge/pill
    to guarantee 100% legibility and prevent visual overlap with grid lines or shapes.
    """
    if not text:
        return

    char_w = 7.2
    pad_x = 5.0
    pad_y = 3.0
    font_h = 10.0

    text_w = len(text) * char_w
    box_w = text_w + pad_x * 2.0
    box_h = font_h + pad_y * 2.0

    if align == "center":
        x0 = x - box_w / 2.0
        y0 = y - box_h / 2.0
    elif align in ("top_left", "nw"):
        x0 = x - box_w
        y0 = y
    elif align in ("top_right", "ne"):
        x0 = x
        y0 = y
    elif align in ("bottom_left", "sw"):
        x0 = x - box_w
        y0 = y - box_h
    elif align in ("bottom_right", "se"):
        x0 = x
        y0 = y - box_h
    elif align == "left":
        x0 = x - box_w
        y0 = y - box_h / 2.0
    elif align == "right":
        x0 = x
        y0 = y - box_h / 2.0
    elif align == "top":
        x0 = x - box_w / 2.0
        y0 = y
    elif align == "bottom":
        x0 = x - box_w / 2.0
        y0 = y - box_h
    else:
        x0 = x
        y0 = y

    x1 = x0 + box_w
    y1 = y0 + box_h

    # Enable blending for semi-opaque pill background
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    # 1. Background Pill Box
    gl.glColor4f(*bg_color)
    gl.glBegin(gl.GL_POLYGON)
    gl.glVertex2f(x0, y0)
    gl.glVertex2f(x1, y0)
    gl.glVertex2f(x1, y1)
    gl.glVertex2f(x0, y1)
    gl.glEnd()

    # 2. Subtle Pill Border
    gl.glColor3f(*border_color)
    gl.glLineWidth(1.0)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(x0, y0)
    gl.glVertex2f(x1, y0)
    gl.glVertex2f(x1, y1)
    gl.glVertex2f(x0, y1)
    gl.glEnd()

    # 3. High-Contrast Text
    gl.glColor3f(*text_color)
    gl.glRasterPos2f(x0 + pad_x, y0 + pad_y + 1.0)
    for ch in text:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))


def _draw_canvas_text(x, y, text, color=(0.10, 0.12, 0.18), font=None):
    """Render bitmap text on the drawing canvas in world coordinates."""
    _draw_canvas_label(x, y, text, align="center", text_color=color)


def _draw_circle_light_lines(cx, cy, r_px, rpx, rpy, centre_grid, radius_val):
    """
    Draw radius line, non-overlapping labels, and prominent center dot marker for a completed circle.
    (No x, y axis lines). Coordinates cx, cy, rpx, rpy are in pixel units on the canvas.
    """
    gl.glColor3f(*LIGHT_GUIDE_COLOR)
    # Radius line to radius point
    _draw_styled_line(cx, cy, rpx, rpy, "Dotted", 1, "")

    # ── Non-overlapping Labels with Background Badges ───────────────────
    dx = rpx - cx
    dy = rpy - cy
    dist = math.sqrt(dx * dx + dy * dy)
    if dist > 0:
        ux = dx / dist
        uy = dy / dist
        nx = -uy
        ny = ux
    else:
        ux, uy = 1.0, 0.0
        nx, ny = 0.0, 1.0

    # Center label: calculate badge width and offset completely outside center dot
    c_label = f"C({centre_grid[0]},{centre_grid[1]})"
    char_w = 7.2
    c_box_w = len(c_label) * char_w + 10.0
    c_offset_dist = (c_box_w / 2.0) + 14.0

    c_x = cx - ux * c_offset_dist - nx * 10.0
    c_y = cy - uy * c_offset_dist - ny * 10.0
    _draw_canvas_label(c_x, c_y, c_label, align="center")

    # Radius label: placed at 55% along radius line, offset perpendicularly by 16px
    r_label = f"r={radius_val}"
    r_x = cx + 0.55 * dx + nx * 16.0
    r_y = cy + 0.55 * dy + ny * 16.0
    _draw_canvas_label(r_x, r_y, r_label, align="center")

    # Marker at radius point (drawn on top)
    gl.glColor3f(0.25, 0.55, 0.90)
    _draw_circle_filled_point(rpx, rpy, radius=3.0)

    # Prominent Center Dot (drawn on top of badges with dual-ring highlight)
    gl.glColor3f(0.08, 0.08, 0.12)
    _draw_circle_filled_point(cx, cy, radius=4.0)
    gl.glColor3f(1.0, 1.0, 1.0)
    _draw_circle_filled_point(cx, cy, radius=1.5)


def _draw_ellipse_light_lines(cx, cy, rx_px, ry_px, rx_px_pt, ry_px_pt, angle, centre_grid, rx_val, ry_val):
    """
    Draw semi-major and semi-minor radius lines, non-overlapping labels, and center dot for an ellipse.
    (No full major/minor axis diameter lines). Coordinates are in pixel units on the canvas.
    """
    cos_t = math.cos(angle)
    sin_t = math.sin(angle)

    gl.glColor3f(*LIGHT_GUIDE_COLOR)
    # Radius line from center to rx_point
    _draw_styled_line(cx, cy, rx_px_pt[0], rx_px_pt[1], "Dotted", 1, "")

    # Radius line from center to ry_point
    _draw_styled_line(cx, cy, ry_px_pt[0], ry_px_pt[1], "Dotted", 1, "")

    # ── Non-overlapping Labels with Background Badges ───────────────────
    ux, uy = cos_t, sin_t
    vx, vy = -sin_t, cos_t

    # Center label: calculate badge width and offset in negative quadrant (-u, -v) outside center dot
    c_label = f"C({centre_grid[0]},{centre_grid[1]})"
    char_w = 7.2
    c_box_w = len(c_label) * char_w + 10.0
    c_offset_dist = (c_box_w / 2.0) + 14.0

    d_diag_x = -(ux + vx) * 0.7071
    d_diag_y = -(uy + vy) * 0.7071
    c_x = cx + d_diag_x * c_offset_dist
    c_y = cy + d_diag_y * c_offset_dist
    _draw_canvas_label(c_x, c_y, c_label, align="center")

    # rx label: placed at 55% along rx semi-axis, offset towards -v by 16px
    rx_label = f"rx={rx_val}"
    rx_x = cx + 0.55 * (rx_px_pt[0] - cx) - 16.0 * vx
    rx_y = cy + 0.55 * (rx_px_pt[1] - cy) - 16.0 * vy
    _draw_canvas_label(rx_x, rx_y, rx_label, align="center")

    # ry label: placed at 55% along ry semi-axis, offset towards +u by 16px
    ry_label = f"ry={ry_val}"
    ry_x = cx + 0.55 * (ry_px_pt[0] - cx) + 16.0 * ux
    ry_y = cy + 0.55 * (ry_px_pt[1] - cy) + 16.0 * uy
    _draw_canvas_label(ry_x, ry_y, ry_label, align="center")

    # Markers at rx and ry points (drawn on top)
    gl.glColor3f(0.25, 0.55, 0.90)
    _draw_circle_filled_point(rx_px_pt[0], rx_px_pt[1], radius=3.0)
    _draw_circle_filled_point(ry_px_pt[0], ry_px_pt[1], radius=3.0)

    # Prominent Center Dot (drawn on top of badges with dual-ring highlight)
    gl.glColor3f(0.08, 0.08, 0.12)
    _draw_circle_filled_point(cx, cy, radius=4.0)
    gl.glColor3f(1.0, 1.0, 1.0)
    _draw_circle_filled_point(cx, cy, radius=1.5)


def draw_lines_on_canvas():
    """
    Draw all user-drawn shapes (lines, circles, and ellipses) on the canvas.
    Lines are drawn as straight lines from p1 to p2.
    Circles are drawn with center dot, radius line, labels, and outline.
    Ellipses are drawn with center dot, radius lines, labels, and smooth outline.
    """

    # Enable smooth lines and alpha blending
    gl.glEnable(gl.GL_LINE_SMOOTH)
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glHint(gl.GL_LINE_SMOOTH_HINT, gl.GL_NICEST)

    # 1. Draw completed shapes
    for shape in drawn_lines:
        color = COLOR_MAP.get(shape["color"], (1.0, 0.0, 0.0))
        width = shape["width"]
        shape_type = shape.get("type", "line")
        style = shape.get("style", "Solid")
        user_pattern = shape.get("pattern", "")

        if shape_type == "line":
            gl.glColor3f(*color)
            gl.glLineWidth(width)
            pts = shape.get("line_points", [])
            _draw_algorithm_points_with_style(pts, style, width, user_pattern, close_loop=False)

        elif shape_type == "circle":
            centre = shape.get("center", (0, 0))
            cx = centre[0] * GRID_SIZE
            cy = centre[1] * GRID_SIZE
            r = shape.get("radius", 0)
            r_px = r * GRID_SIZE
            rp = shape.get("radius_point", (centre[0] + r, centre[1]))
            rpx = rp[0] * GRID_SIZE
            rpy = rp[1] * GRID_SIZE

            # Draw radius light line, labels, and center dot
            _draw_circle_light_lines(cx, cy, r_px, rpx, rpy, centre, r)

            # Draw circle outline
            gl.glColor3f(*color)
            gl.glLineWidth(width)
            pts = shape.get("circle_points", [])
            _draw_algorithm_points_with_style(pts, style, width, user_pattern, close_loop=True)

        elif shape_type == "ellipse":
            centre = shape.get("center", (0, 0))
            cx = centre[0] * GRID_SIZE
            cy = centre[1] * GRID_SIZE
            rx = shape.get("rx", 1)
            ry = shape.get("ry", 1)
            rx_px = rx * GRID_SIZE
            ry_px = ry * GRID_SIZE
            rx_pt = shape.get("rx_point", (centre[0] + rx, centre[1]))
            ry_pt = shape.get("ry_point", (centre[0], centre[1] + ry))
            rx_px_pt = (rx_pt[0] * GRID_SIZE, rx_pt[1] * GRID_SIZE)
            ry_px_pt = (ry_pt[0] * GRID_SIZE, ry_pt[1] * GRID_SIZE)

            if "angle" in shape:
                angle = shape["angle"]
            elif rx_pt != centre:
                angle = math.atan2(rx_pt[1] - centre[1], rx_pt[0] - centre[0])
            else:
                angle = 0.0

            # Draw radius light lines, labels, and center dot
            _draw_ellipse_light_lines(cx, cy, rx_px, ry_px, rx_px_pt, ry_px_pt, angle, centre, rx, ry)

            # Draw ellipse outline
            gl.glColor3f(*color)
            gl.glLineWidth(width)
            pts = shape.get("ellipse_points", [])
            _draw_algorithm_points_with_style(pts, style, width, user_pattern, close_loop=True)

    # 2. Draw active circle animation
    if circle_animation["active"]:
        entry = circle_animation["entry"]
        color = COLOR_MAP.get(entry["color"], (1.0, 0.0, 0.0))
        width = entry["width"]
        style = entry.get("style", "Solid")
        user_pattern = entry.get("pattern", "")

        c = entry["center"]
        cx = c[0] * GRID_SIZE
        cy = c[1] * GRID_SIZE
        r = entry["radius"]
        r_px = r * GRID_SIZE

        rp = entry["radius_point"]
        rpx = rp[0] * GRID_SIZE
        rpy = rp[1] * GRID_SIZE

        phase = circle_animation["phase"]
        prog = circle_animation["progress"]

        if phase == "radius":
            dx = rpx - cx
            dy = rpy - cy
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                ux, uy = dx / dist, dy / dist
                nx, ny = -uy, ux
            else:
                ux, uy, nx, ny = 1.0, 0.0, 0.0, 1.0

            c_label = f"C({c[0]},{c[1]})"
            c_box_w = len(c_label) * 7.2 + 10.0
            c_offset_dist = (c_box_w / 2.0) + 14.0
            _draw_canvas_label(cx - ux * c_offset_dist - nx * 10.0,
                               cy - uy * c_offset_dist - ny * 10.0,
                               c_label, align="center")

            # Draw radius guide line growing from center to radius_point
            curr_x = cx + (rpx - cx) * prog
            curr_y = cy + (rpy - cy) * prog
            gl.glColor3f(*ORTHOGONAL_GUIDE_COLOR)
            _draw_styled_line(cx, cy, curr_x, curr_y, "Solid", 2, "")
            gl.glColor3f(0.3, 0.6, 0.95)
            _draw_circle_filled_point(curr_x, curr_y, radius=3.5)

            # Center dot (on top)
            gl.glColor3f(0.08, 0.08, 0.12)
            _draw_circle_filled_point(cx, cy, radius=4.0)
            gl.glColor3f(1.0, 1.0, 1.0)
            _draw_circle_filled_point(cx, cy, radius=1.5)

            if prog > 0.3:
                _draw_canvas_label(cx + 0.55 * (curr_x - cx) + nx * 16.0,
                                   cy + 0.55 * (curr_y - cy) + ny * 16.0,
                                   f"r={r}",
                                   text_color=(0.15, 0.45, 0.85))

        elif phase == "points":
            # Draw full center dot, radius guide line, and labels
            _draw_circle_light_lines(cx, cy, r_px, rpx, rpy, c, r)

            # Animate the outline points connecting in a continuous flow
            limit = int(prog)
            pts = entry["circle_points"]
            if limit > 1:
                gl.glColor3f(*color)
                gl.glLineWidth(width)
                _draw_algorithm_points_with_style(pts[:min(limit, len(pts))], style, width, user_pattern, close_loop=False)

                # Leading tracer point
                tip_idx = min(limit, len(pts)) - 1
                tip_pt = pts[tip_idx]
                gl.glColor3f(*color)
                _draw_circle_filled_point(tip_pt[0] * GRID_SIZE, tip_pt[1] * GRID_SIZE, radius=max(2.5, width + 1.0))

    # 3. Draw active ellipse animation
    if ellipse_animation["active"]:
        entry = ellipse_animation["entry"]
        color = COLOR_MAP.get(entry["color"], (1.0, 0.0, 0.0))
        width = entry["width"]
        style = entry.get("style", "Solid")
        user_pattern = entry.get("pattern", "")

        c = entry["center"]
        cx = c[0] * GRID_SIZE
        cy = c[1] * GRID_SIZE

        erx = entry["rx"]
        ery = entry["ry"]
        rx_px = erx * GRID_SIZE
        ry_px = ery * GRID_SIZE

        rx_pt = entry.get("rx_point", c)
        ry_pt = entry.get("ry_point", c)

        rx_px_pt = (rx_pt[0] * GRID_SIZE, rx_pt[1] * GRID_SIZE)
        ry_px_pt = (ry_pt[0] * GRID_SIZE, ry_pt[1] * GRID_SIZE)

        angle = entry.get("angle", 0.0)
        cos_t = math.cos(angle)
        sin_t = math.sin(angle)
        ux, uy = cos_t, sin_t
        vx, vy = -sin_t, cos_t

        phase = ellipse_animation["phase"]
        prog = ellipse_animation["progress"]

        if phase == "rx":
            # Center label badge
            c_label = f"C({c[0]},{c[1]})"
            c_box_w = len(c_label) * 7.2 + 10.0
            c_offset_dist = (c_box_w / 2.0) + 14.0
            d_diag_x = -(ux + vx) * 0.7071
            d_diag_y = -(uy + vy) * 0.7071
            _draw_canvas_label(cx + d_diag_x * c_offset_dist, cy + d_diag_y * c_offset_dist, c_label, align="center")

            # Animate the rx radius line growing from center to rx_point
            curr_x = cx + (rx_px_pt[0] - cx) * prog
            curr_y = cy + (rx_px_pt[1] - cy) * prog
            gl.glColor3f(*ORTHOGONAL_GUIDE_COLOR)
            _draw_styled_line(cx, cy, curr_x, curr_y, "Solid", 2, "")
            _draw_circle_filled_point(curr_x, curr_y, radius=3.5)

            # Center dot (on top)
            gl.glColor3f(0.08, 0.08, 0.12)
            _draw_circle_filled_point(cx, cy, radius=4.0)
            gl.glColor3f(1.0, 1.0, 1.0)
            _draw_circle_filled_point(cx, cy, radius=1.5)

            if prog > 0.3:
                _draw_canvas_label(cx + 0.55 * (curr_x - cx) - 16.0 * vx,
                                   cy + 0.55 * (curr_y - cy) - 16.0 * vy,
                                   f"rx={erx}",
                                   text_color=(0.15, 0.45, 0.85))

        elif phase == "ry":
            # Center label badge
            c_label = f"C({c[0]},{c[1]})"
            c_box_w = len(c_label) * 7.2 + 10.0
            c_offset_dist = (c_box_w / 2.0) + 14.0
            d_diag_x = -(ux + vx) * 0.7071
            d_diag_y = -(uy + vy) * 0.7071
            _draw_canvas_label(cx + d_diag_x * c_offset_dist, cy + d_diag_y * c_offset_dist, c_label, align="center")

            # Full rx radius line & label
            gl.glColor3f(*LIGHT_GUIDE_COLOR)
            _draw_styled_line(cx, cy, rx_px_pt[0], rx_px_pt[1], "Solid", 1.5, "")
            _draw_circle_filled_point(rx_px_pt[0], rx_px_pt[1], radius=2.5)
            _draw_canvas_label(cx + 0.55 * (rx_px_pt[0] - cx) - 16.0 * vx,
                               cy + 0.55 * (rx_px_pt[1] - cy) - 16.0 * vy,
                               f"rx={erx}")

            # Animate the ry radius line along orthogonal axis
            curr_x = cx + (ry_px_pt[0] - cx) * prog
            curr_y = cy + (ry_px_pt[1] - cy) * prog
            gl.glColor3f(*ORTHOGONAL_GUIDE_COLOR)
            _draw_styled_line(cx, cy, curr_x, curr_y, "Solid", 2, "")
            _draw_circle_filled_point(curr_x, curr_y, radius=3.5)

            # Center dot (on top)
            gl.glColor3f(0.08, 0.08, 0.12)
            _draw_circle_filled_point(cx, cy, radius=4.0)
            gl.glColor3f(1.0, 1.0, 1.0)
            _draw_circle_filled_point(cx, cy, radius=1.5)

            if prog > 0.3:
                _draw_canvas_label(cx + 0.55 * (curr_x - cx) + 16.0 * ux,
                                   cy + 0.55 * (curr_y - cy) + 16.0 * uy,
                                   f"ry={ery}",
                                   text_color=(0.15, 0.45, 0.85))

        elif phase == "points":
            # Full center axes, radius lines, and labels
            _draw_ellipse_light_lines(cx, cy, rx_px, ry_px, rx_px_pt, ry_px_pt, angle, c, erx, ery)

            # Animate the outline points connecting in a continuous flow
            limit = int(prog)
            pts = entry["ellipse_points"]
            if limit > 1:
                gl.glColor3f(*color)
                gl.glLineWidth(width)
                _draw_algorithm_points_with_style(pts[:min(limit, len(pts))], style, width, user_pattern, close_loop=False)

                # Leading tracer point
                tip_idx = min(limit, len(pts)) - 1
                tip_pt = pts[tip_idx]
                gl.glColor3f(*color)
                _draw_circle_filled_point(tip_pt[0] * GRID_SIZE, tip_pt[1] * GRID_SIZE, radius=max(2.5, width + 1.0))

    # Reset line width
    gl.glLineWidth(1)

    # Disable smooth lines
    gl.glDisable(gl.GL_LINE_SMOOTH)
    gl.glDisable(gl.GL_BLEND)

def draw_endpoint_dumbbells():
    """
    Draw snap preview indicators only when hovering near a connectable endpoint.
    No permanent vertex markers are drawn so shapes and figures remain clean.
    """
    if current_mouse_grid is None:
        return

    mx, my = current_mouse_grid
    snap_pt, snapped = _snap_to_nearest_endpoint(mx, my)
    if not snapped:
        return

    sx = snap_pt[0] * GRID_SIZE
    sy = snap_pt[1] * GRID_SIZE

    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)

    # Subtle snap indicator ring only when hovering near an endpoint
    gl.glColor4f(*SNAP_HIGHLIGHT_COLOR, 0.65)
    gl.glLineWidth(2.0)
    gl.glBegin(gl.GL_LINE_LOOP)
    segments = 24
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        gl.glVertex2f(sx + SNAP_HIGHLIGHT_RADIUS * math.cos(angle),
                      sy + SNAP_HIGHLIGHT_RADIUS * math.sin(angle))
    gl.glEnd()

    # High-contrast snap indicator badge
    _draw_canvas_label(sx + 14.0, sy + 14.0, f"Snap ({snap_pt[0]},{snap_pt[1]})",
                       align="left",
                       text_color=(0.95, 0.40, 0.05),
                       border_color=(1.0, 0.60, 0.20))

    gl.glLineWidth(1)
    gl.glDisable(gl.GL_BLEND)


def draw_selected_points():
    """
    Draw the currently selected (pending) point(s) as markers,
    including long dynamic guided lines, orthogonal guidelines, and high-contrast badges.
    """
    long_len = max(CURRENT_WIDTH, CURRENT_HEIGHT) * 2.5

    # ── 1. Draw dynamic interactive guides (without shape outlines) ──────────
    if is_ellipse_algorithm(CURRENT_ALGORITHM):
        if len(selected_points) == 1:
            c = selected_points[0]
            cx = c[0] * GRID_SIZE
            cy = c[1] * GRID_SIZE

            # Long center crosshair lines across the canvas
            gl.glColor3f(*LIGHT_GUIDE_COLOR)
            _draw_styled_line(cx - long_len, cy, cx + long_len, cy, "Dotted", 1, "")
            _draw_styled_line(cx, cy - long_len, cx, cy + long_len, "Dotted", 1, "")

            if current_mouse_grid is not None:
                mx = current_mouse_grid[0] * GRID_SIZE
                my = current_mouse_grid[1] * GRID_SIZE

                dx = current_mouse_grid[0] - c[0]
                dy = current_mouse_grid[1] - c[1]
                dist = math.sqrt(dx * dx + dy * dy)
                rx_val = max(1, int(round_half_up(dist)))

                if dist > 0:
                    ux = (mx - cx) / (dist * GRID_SIZE)
                    uy = (my - cy) / (dist * GRID_SIZE)
                    nx = -uy
                    ny = ux
                else:
                    ux, uy, nx, ny = 1.0, 0.0, 0.0, 1.0

                # Center badge opposite to mouse
                _draw_canvas_label(cx - ux * 18.0 - nx * 8.0, cy - uy * 18.0 - ny * 8.0, f"C({c[0]},{c[1]})")

                # Long guided line passing through center and mouse across the canvas
                if dist > 0:
                    gl.glColor3f(*LIGHT_GUIDE_COLOR)
                    _draw_styled_line(cx - long_len * ux, cy - long_len * uy,
                                      cx + long_len * ux, cy + long_len * uy, "Dotted", 1, "")

                # Active rx radius line from center to mouse
                gl.glColor3f(*ORTHOGONAL_GUIDE_COLOR)
                _draw_styled_line(cx, cy, mx, my, "Dashed", 1.5, "")
                _draw_circle_filled_point(mx, my, radius=3.5)

                # Live label along the rx line
                _draw_canvas_label(cx + 0.55 * (mx - cx) + nx * 14.0,
                                   cy + 0.55 * (my - cy) + ny * 14.0,
                                   f"rx={rx_val}",
                                   text_color=(0.15, 0.45, 0.85))
            else:
                _draw_canvas_label(cx - 18.0, cy + 18.0, f"C({c[0]},{c[1]})")

        elif len(selected_points) == 2:
            c = selected_points[0]
            rx_pt = selected_points[1]
            cx = c[0] * GRID_SIZE
            cy = c[1] * GRID_SIZE
            rx_px = rx_pt[0] * GRID_SIZE
            ry_px = rx_pt[1] * GRID_SIZE

            dx1 = rx_pt[0] - c[0]
            dy1 = rx_pt[1] - c[1]
            dist1 = math.sqrt(dx1 * dx1 + dy1 * dy1)
            rx_val = max(1, int(round_half_up(dist1)))

            if dist1 > 0:
                ux1 = (rx_px - cx) / (dist1 * GRID_SIZE)
                uy1 = (ry_px - cy) / (dist1 * GRID_SIZE)
            else:
                ux1, uy1 = 1.0, 0.0

            nx1 = -uy1
            ny1 = ux1

            # Long semi-major axis line
            gl.glColor3f(*LIGHT_GUIDE_COLOR)
            _draw_styled_line(cx - long_len * ux1, cy - long_len * uy1,
                              cx + long_len * ux1, cy + long_len * uy1, "Dotted", 1, "")

            # Long semi-minor axis line (orthogonal)
            gl.glColor3f(*LIGHT_GUIDE_COLOR)
            _draw_styled_line(cx - long_len * nx1, cy - long_len * ny1,
                              cx + long_len * nx1, cy + long_len * ny1, "Dotted", 1, "")

            # Fixed radius line to rx point
            gl.glColor3f(*ORTHOGONAL_GUIDE_COLOR)
            _draw_styled_line(cx, cy, rx_px, ry_px, "Dashed", 1.5, "")
            _draw_circle_filled_point(rx_px, ry_px, radius=3)

            # Badges
            _draw_canvas_label(cx - ux1 * 18.0 - nx1 * 8.0, cy - uy1 * 18.0 - ny1 * 8.0, f"C({c[0]},{c[1]})")
            _draw_canvas_label(cx + 0.55 * (rx_px - cx) + nx1 * 14.0,
                               cy + 0.55 * (ry_px - cy) + ny1 * 14.0,
                               f"rx={rx_val}",
                               text_color=(0.15, 0.45, 0.85))

            if current_mouse_grid is not None:
                mx = current_mouse_grid[0] * GRID_SIZE
                my = current_mouse_grid[1] * GRID_SIZE

                # Project mouse onto orthogonal axis
                v_mouse_x = mx - cx
                v_mouse_y = my - cy
                proj_dist_px = v_mouse_x * nx1 + v_mouse_y * ny1
                ry_val = max(1, int(round_half_up(abs(proj_dist_px) / GRID_SIZE)))

                ry_guided_px_x = cx + proj_dist_px * nx1
                ry_guided_px_y = cy + proj_dist_px * ny1

                # Dashed projection line from mouse to orthogonal axis
                gl.glColor3f(*PROJECTION_LINE_COLOR)
                _draw_styled_line(mx, my, ry_guided_px_x, ry_guided_px_y, "Dotted", 1, "")

                # Guided radius line on orthogonal axis
                gl.glColor3f(*ORTHOGONAL_GUIDE_COLOR)
                _draw_styled_line(cx, cy, ry_guided_px_x, ry_guided_px_y, "Dashed", 1.5, "")
                _draw_circle_filled_point(ry_guided_px_x, ry_guided_px_y, radius=4)

                # Mouse tracking dot
                gl.glColor3f(0.5, 0.5, 0.5)
                _draw_circle_filled_point(mx, my, radius=2.5)

                # Live vertical radius badge
                side_sign = 1.0 if proj_dist_px >= 0 else -1.0
                _draw_canvas_label(cx + 0.55 * (ry_guided_px_x - cx) + ux1 * 14.0 * side_sign,
                                   cy + 0.55 * (ry_guided_px_y - cy) + uy1 * 14.0 * side_sign,
                                   f"ry={ry_val}",
                                   text_color=(0.15, 0.45, 0.85))

    elif is_circle_algorithm(CURRENT_ALGORITHM):
        if len(selected_points) == 1:
            c = selected_points[0]
            cx = c[0] * GRID_SIZE
            cy = c[1] * GRID_SIZE

            # Long center crosshair lines across the canvas
            gl.glColor3f(*LIGHT_GUIDE_COLOR)
            _draw_styled_line(cx - long_len, cy, cx + long_len, cy, "Dotted", 1, "")
            _draw_styled_line(cx, cy - long_len, cx, cy + long_len, "Dotted", 1, "")

            if current_mouse_grid is not None:
                mx = current_mouse_grid[0] * GRID_SIZE
                my = current_mouse_grid[1] * GRID_SIZE

                dx = current_mouse_grid[0] - c[0]
                dy = current_mouse_grid[1] - c[1]
                dist = math.sqrt(dx * dx + dy * dy)
                r_val = max(1, int(round_half_up(dist)))

                if dist > 0:
                    ux = (mx - cx) / (dist * GRID_SIZE)
                    uy = (my - cy) / (dist * GRID_SIZE)
                    nx = -uy
                    ny = ux
                else:
                    ux, uy, nx, ny = 1.0, 0.0, 0.0, 1.0

                # Center badge opposite to mouse
                _draw_canvas_label(cx - ux * 18.0 - nx * 8.0, cy - uy * 18.0 - ny * 8.0, f"C({c[0]},{c[1]})")

                # Long guided line passing through center and mouse
                if dist > 0:
                    gl.glColor3f(*LIGHT_GUIDE_COLOR)
                    _draw_styled_line(cx - long_len * ux, cy - long_len * uy,
                                      cx + long_len * ux, cy + long_len * uy, "Dotted", 1, "")

                # Dynamic radius line from center to mouse
                gl.glColor3f(*ORTHOGONAL_GUIDE_COLOR)
                _draw_styled_line(cx, cy, mx, my, "Dashed", 1.5, "")
                _draw_circle_filled_point(mx, my, radius=3.5)

                # Live radius badge
                _draw_canvas_label(cx + 0.55 * (mx - cx) + nx * 14.0,
                                   cy + 0.55 * (my - cy) + ny * 14.0,
                                   f"r={r_val}",
                                   text_color=(0.15, 0.45, 0.85))
            else:
                _draw_canvas_label(cx - 18.0, cy + 18.0, f"C({c[0]},{c[1]})")

    else:
        # Line drawing preview
        if len(selected_points) == 1 and current_mouse_grid is not None:
            p1 = selected_points[0]
            p1x = p1[0] * GRID_SIZE
            p1y = p1[1] * GRID_SIZE
            mx = current_mouse_grid[0] * GRID_SIZE
            my = current_mouse_grid[1] * GRID_SIZE
            gl.glColor3f(*ORTHOGONAL_GUIDE_COLOR)
            _draw_styled_line(p1x, p1y, mx, my, "Dashed", 1, "")
            _draw_circle_filled_point(mx, my, radius=3)


    # ── 2. Draw red marker dots at clicked anchor points ────────────────────
    if selected_points:
        gl.glColor3f(*POINT_MARKER_COLOR)
        for (gx, gy) in selected_points:
            cx = gx * GRID_SIZE
            cy = gy * GRID_SIZE
            r = POINT_MARKER_RADIUS

            # Filled circle
            gl.glBegin(gl.GL_POLYGON)
            for angle_deg in range(0, 360, 15):
                rad = math.radians(angle_deg)
                gl.glVertex2f(cx + r * math.cos(rad), cy + r * math.sin(rad))
            gl.glEnd()

            # Dark outline
            gl.glColor3f(0.0, 0.0, 0.0)
            gl.glLineWidth(1)
            gl.glBegin(gl.GL_LINE_LOOP)
            for angle_deg in range(0, 360, 15):
                rad = math.radians(angle_deg)
                gl.glVertex2f(cx + (r + 1) * math.cos(rad), cy + (r + 1) * math.sin(rad))
            gl.glEnd()

            # Reset color
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

    # draw_tick_labels(
    #     half_height,
    #     half_width,
    # )

    # Draw all user lines
    draw_lines_on_canvas()

    # Draw dumbbell snap markers at connectable endpoints
    draw_endpoint_dumbbells()

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
            gl.glVertex2f(right, MENU_BUTTON_HEIGHT)
            gl.glVertex2f(left, MENU_BUTTON_HEIGHT)
            gl.glEnd()

        # Item border
        gl.glColor3f(*MENU_ITEM_COLOR)
        gl.glLineWidth(1)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(left, 0)
        gl.glVertex2f(right, 0)
        gl.glVertex2f(right, MENU_BUTTON_HEIGHT)
        gl.glVertex2f(left, MENU_BUTTON_HEIGHT)
        gl.glEnd()

        # Item text — centered
        text_x = left + (menu_item_width - len(item) * 7) / 2
        text_y = MENU_BUTTON_HEIGHT / 2 + 5
        draw_menu_text(text_x, text_y, item, MENU_TEXT_COLOR)

    # Draw status bar text showing current settings
    if is_ellipse_algorithm(CURRENT_ALGORITHM):
        if len(selected_points) == 0:
            click_hint = "Click to set centre"
        elif len(selected_points) == 1:
            rx_hint = ""
            if current_mouse_grid is not None:
                dx = current_mouse_grid[0] - selected_points[0][0]
                dy = current_mouse_grid[1] - selected_points[0][1]
                rx_val = max(1, int(round_half_up(math.sqrt(dx * dx + dy * dy))))
                rx_hint = f" (rx={rx_val})"
            click_hint = f"Click to set rx point{rx_hint}"
        else:
            ry_hint = ""
            if current_mouse_grid is not None:
                c = selected_points[0]
                rx_pt = selected_points[1]
                dx1 = rx_pt[0] - c[0]
                dy1 = rx_pt[1] - c[1]
                ang = math.atan2(dy1, dx1) if (dx1 != 0 or dy1 != 0) else 0.0
                vx = -math.sin(ang)
                vy = math.cos(ang)
                wx = current_mouse_grid[0] - c[0]
                wy = current_mouse_grid[1] - c[1]
                d_p = wx * vx + wy * vy
                ry_val = max(1, int(round_half_up(abs(d_p)))) if abs(d_p) >= 0.5 else 1
                ry_hint = f" (ry={ry_val})"
            click_hint = f"Click along orthogonal line to set ry{ry_hint}"
        status = f"  {CURRENT_ALGORITHM} | {CURRENT_COLOR} | Width:{CURRENT_LINE_WIDTH} | {click_hint}"
    elif is_circle_algorithm(CURRENT_ALGORITHM):
        if len(selected_points) == 0:
            click_hint = "Click to set centre"
        else:
            r_hint = ""
            if current_mouse_grid is not None:
                dx = current_mouse_grid[0] - selected_points[0][0]
                dy = current_mouse_grid[1] - selected_points[0][1]
                r_val = max(1, int(round_half_up(math.sqrt(dx * dx + dy * dy))))
                r_hint = f" (r={r_val})"
            click_hint = f"Click to set radius point{r_hint}"
        status = f"  {CURRENT_ALGORITHM} | {CURRENT_COLOR} | Width:{CURRENT_LINE_WIDTH} | {click_hint}"
    else:
        style_display = CURRENT_LINE_STYLE
        if CURRENT_LINE_STYLE == "UserDefined":
            style_display = f"UserDefined({CURRENT_USER_PATTERN_HEX})"
        status = f"  {CURRENT_ALGORITHM} | {CURRENT_COLOR} | Width:{CURRENT_LINE_WIDTH} | {style_display}"
    draw_menu_text(5, MENU_HEIGHT - 6, status, (0.55, 0.55, 0.55))


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
    dd_top = MENU_BUTTON_HEIGHT

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
            elif item == "User Defined" and CURRENT_LINE_STYLE == "UserDefined":
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
        if item in SUB_DROPDOWN:
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


def draw_pattern_dialog():
    """
    Draw the modern "User Defined Hex Pattern" popup dialog over the canvas.
    """
    global PATTERN_DIALOG_CURSOR_BLINK

    if not PATTERN_DIALOG_OPEN:
        return

    PATTERN_DIALOG_CURSOR_BLINK = (PATTERN_DIALOG_CURSOR_BLINK + 1) % 60

    # ── Semi-transparent overlay ──────────────────────────────────────────
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glColor4f(0.0, 0.0, 0.0, 0.50)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(0, 0)
    gl.glVertex2f(CURRENT_WIDTH, 0)
    gl.glVertex2f(CURRENT_WIDTH, CURRENT_HEIGHT)
    gl.glVertex2f(0, CURRENT_HEIGHT)
    gl.glEnd()

    # ── Dialog box dimensions ────────────────────────────────────────────
    dialog_w = 500
    dialog_h = 250
    dlg_left   = (CURRENT_WIDTH - dialog_w) / 2
    dlg_right  = dlg_left + dialog_w
    dlg_top    = (CURRENT_HEIGHT - dialog_h) / 2
    dlg_bottom = dlg_top + dialog_h

    # ── Dialog shadow ────────────────────────────────────────────────────
    shadow_off = 6
    gl.glColor4f(0.0, 0.0, 0.0, 0.30)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(dlg_left + shadow_off, dlg_top + shadow_off)
    gl.glVertex2f(dlg_right + shadow_off, dlg_top + shadow_off)
    gl.glVertex2f(dlg_right + shadow_off, dlg_bottom + shadow_off)
    gl.glVertex2f(dlg_left + shadow_off, dlg_bottom + shadow_off)
    gl.glEnd()

    # ── Dialog background ────────────────────────────────────────────────
    gl.glColor3f(0.16, 0.17, 0.21)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(dlg_left, dlg_top)
    gl.glVertex2f(dlg_right, dlg_top)
    gl.glVertex2f(dlg_right, dlg_bottom)
    gl.glVertex2f(dlg_left, dlg_bottom)
    gl.glEnd()

    # ── Dialog border ────────────────────────────────────────────────────
    gl.glColor3f(0.40, 0.42, 0.48)
    gl.glLineWidth(1.5)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(dlg_left, dlg_top)
    gl.glVertex2f(dlg_right, dlg_top)
    gl.glVertex2f(dlg_right, dlg_bottom)
    gl.glVertex2f(dlg_left, dlg_bottom)
    gl.glEnd()

    # ── Title ────────────────────────────────────────────────────────────
    title = "User Defined Hex Pattern"
    title_x = dlg_left + (dialog_w - len(title) * 8.5) / 2
    title_y = dlg_top + 28
    gl.glColor3f(0.95, 0.95, 0.98)
    gl.glRasterPos2f(title_x, title_y)
    for ch in title:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Separator line under title
    gl.glColor3f(0.30, 0.32, 0.38)
    gl.glLineWidth(1)
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(dlg_left + 15, dlg_top + 38)
    gl.glVertex2f(dlg_right - 15, dlg_top + 38)
    gl.glEnd()

    # ── Label ────────────────────────────────────────────────────────────
    label = "Enter Hexadecimal Pattern (e.g. 0xF0F0, 0xAAAA, 0x1C47, 0x00FF):"
    gl.glColor3f(0.80, 0.82, 0.88)
    gl.glRasterPos2f(dlg_left + 20, dlg_top + 58)
    for ch in label:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))

    # ── Text input field ─────────────────────────────────────────────────
    input_left   = dlg_left + 20
    input_right  = dlg_right - 20
    input_top    = dlg_top + 68
    input_bottom = input_top + 30

    # Input background
    gl.glColor3f(0.10, 0.10, 0.13)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(input_left, input_top)
    gl.glVertex2f(input_right, input_top)
    gl.glVertex2f(input_right, input_bottom)
    gl.glVertex2f(input_left, input_bottom)
    gl.glEnd()

    # Input border (purple glow)
    gl.glColor3f(0.65, 0.40, 0.95)
    gl.glLineWidth(1.8)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(input_left, input_top)
    gl.glVertex2f(input_right, input_top)
    gl.glVertex2f(input_right, input_bottom)
    gl.glVertex2f(input_left, input_bottom)
    gl.glEnd()

    # Display text (user input or placeholder)
    text_y = input_top + 20
    if PATTERN_DIALOG_TEXT:
        display_text = PATTERN_DIALOG_TEXT
        gl.glColor3f(0.98, 0.98, 1.0)
    else:
        display_text = CURRENT_USER_PATTERN_HEX
        gl.glColor3f(0.48, 0.50, 0.55)   # Dimmed placeholder

    gl.glRasterPos2f(input_left + 10, text_y)
    for ch in display_text:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))

    # Blinking cursor
    if PATTERN_DIALOG_TEXT and PATTERN_DIALOG_CURSOR_BLINK < 35:
        cursor_x = input_left + 10 + len(PATTERN_DIALOG_TEXT) * 7.5
        gl.glColor3f(0.90, 0.90, 0.98)
        gl.glLineWidth(1)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(cursor_x, input_top + 6)
        gl.glVertex2f(cursor_x, input_bottom - 6)
        gl.glEnd()

    # ── Binary Mask Decoding Info & Visual Preview ───────────────────────
    curr_input = PATTERN_DIALOG_TEXT.strip() if PATTERN_DIALOG_TEXT.strip() else CURRENT_USER_PATTERN_HEX
    hex_str, bin_str = hex_to_binary_pattern(curr_input)

    mask_info = f"Mask: {hex_str}  ->  Binary: {bin_str} ({len(bin_str)}-bit)"
    gl.glColor3f(0.35, 0.75, 0.95)
    gl.glRasterPos2f(dlg_left + 20, input_bottom + 16)
    for ch in mask_info:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_10, ord(ch))

    # Draw visual stipple preview line
    preview_y = input_bottom + 28
    preview_left = dlg_left + 20
    preview_right = dlg_right - 20
    preview_total = preview_right - preview_left

    if bin_str and any(c == '1' for c in bin_str):
        pat_len = len(bin_str)
        step = preview_total / max(pat_len * 2.5, 1)
        gl.glColor3f(0.92, 0.92, 0.98)
        gl.glLineWidth(2.5)
        gl.glBegin(gl.GL_LINES)
        px = preview_left
        idx = 0
        drawing = False
        seg_sx = 0.0
        while px <= preview_right:
            ch = bin_str[idx % pat_len]
            if ch == '1':
                if not drawing:
                    seg_sx = px
                    drawing = True
            else:
                if drawing:
                    gl.glVertex2f(seg_sx, preview_y)
                    gl.glVertex2f(px, preview_y)
                    drawing = False
            px += step
            idx += 1
        if drawing:
            gl.glVertex2f(seg_sx, preview_y)
            gl.glVertex2f(min(px, preview_right), preview_y)
        gl.glEnd()

    # ── Quick Preset Chips ────────────────────────────────────────────────
    gl.glColor3f(0.65, 0.65, 0.70)
    gl.glRasterPos2f(dlg_left + 20, dlg_top + 166)
    for ch in "Presets:":
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_10, ord(ch))

    chips = [
        (dlg_left + 75, dlg_left + 155, "0xF0F0"),
        (dlg_left + 165, dlg_left + 245, "0xAAAA"),
        (dlg_left + 255, dlg_left + 335, "0x1C47"),
        (dlg_left + 345, dlg_left + 425, "0x00FF"),
    ]
    for (cx1, cx2, val) in chips:
        # Chip background
        gl.glColor3f(0.24, 0.25, 0.30)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(cx1, dlg_top + 150)
        gl.glVertex2f(cx2, dlg_top + 150)
        gl.glVertex2f(cx2, dlg_top + 172)
        gl.glVertex2f(cx1, dlg_top + 172)
        gl.glEnd()

        # Chip border
        gl.glColor3f(0.40, 0.42, 0.50)
        gl.glLineWidth(1)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(cx1, dlg_top + 150)
        gl.glVertex2f(cx2, dlg_top + 150)
        gl.glVertex2f(cx2, dlg_top + 172)
        gl.glVertex2f(cx1, dlg_top + 172)
        gl.glEnd()

        # Chip text
        gl.glColor3f(0.88, 0.90, 0.96)
        gl.glRasterPos2f(cx1 + 14, dlg_top + 165)
        for ch in val:
            glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_10, ord(ch))

    # ── Hint text ────────────────────────────────────────────────────────
    hint = "Press Enter to apply, Escape to cancel. Enter hex values (0-9, A-F)."
    gl.glColor3f(0.50, 0.52, 0.58)
    gl.glRasterPos2f(dlg_left + 20, dlg_top + 194)
    for ch in hint:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_10, ord(ch))

    # ── Buttons ──────────────────────────────────────────────────────────
    btn_w = 90
    btn_h = 30
    btn_y_top = dlg_bottom - 16 - btn_h
    btn_y_bot = btn_y_top + btn_h

    # Apply button (right-aligned, accent color)
    apply_btn_left = dlg_right - 20 - btn_w
    gl.glColor3f(0.55, 0.28, 0.85)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(apply_btn_left, btn_y_top)
    gl.glVertex2f(apply_btn_left + btn_w, btn_y_top)
    gl.glVertex2f(apply_btn_left + btn_w, btn_y_bot)
    gl.glVertex2f(apply_btn_left, btn_y_bot)
    gl.glEnd()
    # Apply button text
    gl.glColor3f(1.0, 1.0, 1.0)
    gl.glRasterPos2f(apply_btn_left + 26, btn_y_top + 20)
    for ch in "Apply":
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))

    # Cancel button (to the left of Apply)
    cancel_btn_left = apply_btn_left - btn_w - 12
    gl.glColor3f(0.30, 0.30, 0.35)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(cancel_btn_left, btn_y_top)
    gl.glVertex2f(cancel_btn_left + btn_w, btn_y_top)
    gl.glVertex2f(cancel_btn_left + btn_w, btn_y_bot)
    gl.glVertex2f(cancel_btn_left, btn_y_bot)
    gl.glEnd()
    # Cancel button text
    gl.glColor3f(0.85, 0.85, 0.90)
    gl.glRasterPos2f(cancel_btn_left + 23, btn_y_top + 20)
    for ch in "Cancel":
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))

    gl.glDisable(gl.GL_BLEND)


def draw_transform_dialog():
    """
    Draw the transformation parameter input dialog over the canvas.
    Adapts its layout based on TRANSFORM_DIALOG_TYPE.
    """
    global TRANSFORM_DIALOG_CURSOR_BLINK

    if not TRANSFORM_DIALOG_OPEN:
        return

    TRANSFORM_DIALOG_CURSOR_BLINK = (TRANSFORM_DIALOG_CURSOR_BLINK + 1) % 60

    num_fields = len(TRANSFORM_DIALOG_FIELD_ORDER)

    # ── Semi-transparent overlay ──────────────────────────────────────────
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(gl.GL_SRC_ALPHA, gl.GL_ONE_MINUS_SRC_ALPHA)
    gl.glColor4f(0.0, 0.0, 0.0, 0.50)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(0, 0)
    gl.glVertex2f(CURRENT_WIDTH, 0)
    gl.glVertex2f(CURRENT_WIDTH, CURRENT_HEIGHT)
    gl.glVertex2f(0, CURRENT_HEIGHT)
    gl.glEnd()

    # ── Dialog box dimensions ────────────────────────────────────────────
    dialog_w = 460
    dialog_h = 60 + num_fields * 60 + 100
    dlg_left   = (CURRENT_WIDTH - dialog_w) / 2
    dlg_right  = dlg_left + dialog_w
    dlg_top    = (CURRENT_HEIGHT - dialog_h) / 2
    dlg_bottom = dlg_top + dialog_h

    # ── Dialog shadow ────────────────────────────────────────────────────
    shadow_off = 6
    gl.glColor4f(0.0, 0.0, 0.0, 0.30)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(dlg_left + shadow_off, dlg_top + shadow_off)
    gl.glVertex2f(dlg_right + shadow_off, dlg_top + shadow_off)
    gl.glVertex2f(dlg_right + shadow_off, dlg_bottom + shadow_off)
    gl.glVertex2f(dlg_left + shadow_off, dlg_bottom + shadow_off)
    gl.glEnd()

    # ── Dialog background ────────────────────────────────────────────────
    gl.glColor3f(0.16, 0.17, 0.21)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(dlg_left, dlg_top)
    gl.glVertex2f(dlg_right, dlg_top)
    gl.glVertex2f(dlg_right, dlg_bottom)
    gl.glVertex2f(dlg_left, dlg_bottom)
    gl.glEnd()

    # ── Dialog border ────────────────────────────────────────────────────
    gl.glColor3f(0.40, 0.55, 0.90)
    gl.glLineWidth(1.5)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(dlg_left, dlg_top)
    gl.glVertex2f(dlg_right, dlg_top)
    gl.glVertex2f(dlg_right, dlg_bottom)
    gl.glVertex2f(dlg_left, dlg_bottom)
    gl.glEnd()

    # ── Title ────────────────────────────────────────────────────────────
    title = f"2D {TRANSFORM_DIALOG_TYPE}"
    title_x = dlg_left + (dialog_w - len(title) * 9) / 2
    title_y = dlg_top + 28
    gl.glColor3f(0.95, 0.95, 0.98)
    gl.glRasterPos2f(title_x, title_y)
    for ch in title:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_18, ord(ch))

    # Separator line under title
    gl.glColor3f(0.30, 0.40, 0.65)
    gl.glLineWidth(1)
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(dlg_left + 15, dlg_top + 38)
    gl.glVertex2f(dlg_right - 15, dlg_top + 38)
    gl.glEnd()

    # ── Field labels and descriptions ────────────────────────────────────
    field_labels = {
        "tx": ("tx", "Shift X: - shifts left, + shifts right"),
        "ty": ("ty", "Shift Y: - shifts down, + shifts up"),
        "sx": ("sx", "Scale X: - flips across Y-axis, >1 expands, <1 shrinks"),
        "sy": ("sy", "Scale Y: - flips across X-axis, >1 expands, <1 shrinks"),
        "angle": ("θ°", "Angle in degrees: + is CCW, - is CW"),
        "pivot_x": ("Pivot X", "X coordinate of the fixed point"),
        "pivot_y": ("Pivot Y", "Y coordinate of the fixed point"),
        "axis_x1": ("Axis X1", "First point on the reflection axis"),
        "axis_y1": ("Axis Y1", "First point on the reflection axis"),
        "axis_x2": ("Axis X2", "Second point on the reflection axis"),
        "axis_y2": ("Axis Y2", "Second point on the reflection axis"),
    }
    field_placeholders = {
        "tx": "0", "ty": "0",
        "sx": "1", "sy": "1",
        "angle": "0",
        "pivot_x": "0", "pivot_y": "0",
        "axis_x1": "0", "axis_y1": "0",
        "axis_x2": "1", "axis_y2": "0",
    }

    # ── Draw each input field ────────────────────────────────────────────
    for fi, fname in enumerate(TRANSFORM_DIALOG_FIELD_ORDER):
        label_text, desc_text = field_labels.get(fname, (fname, ""))
        placeholder = field_placeholders.get(fname, "0")

        field_y_top = dlg_top + 55 + fi * 60
        field_y_bot = field_y_top + 30

        # Label
        gl.glColor3f(0.80, 0.82, 0.90)
        gl.glRasterPos2f(dlg_left + 20, field_y_top + 20)
        for ch in f"{label_text}:":
            glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))

        # Input field background
        input_left = dlg_left + 100
        input_right = dlg_right - 20
        is_active = (fi == TRANSFORM_DIALOG_ACTIVE_FIELD)

        gl.glColor3f(0.10, 0.10, 0.14)
        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(input_left, field_y_top)
        gl.glVertex2f(input_right, field_y_top)
        gl.glVertex2f(input_right, field_y_bot)
        gl.glVertex2f(input_left, field_y_bot)
        gl.glEnd()

        # Input field border — accent color if active
        if is_active:
            gl.glColor3f(0.35, 0.60, 1.0)
        else:
            gl.glColor3f(0.35, 0.35, 0.42)
        gl.glLineWidth(1.8 if is_active else 1.0)
        gl.glBegin(gl.GL_LINE_LOOP)
        gl.glVertex2f(input_left, field_y_top)
        gl.glVertex2f(input_right, field_y_top)
        gl.glVertex2f(input_right, field_y_bot)
        gl.glVertex2f(input_left, field_y_bot)
        gl.glEnd()

        # Input text or placeholder
        field_value = TRANSFORM_DIALOG_FIELDS.get(fname, "")
        text_y = field_y_top + 20
        if field_value:
            gl.glColor3f(0.98, 0.98, 1.0)
            display_text = field_value
        else:
            gl.glColor3f(0.42, 0.44, 0.50)
            display_text = placeholder

        gl.glRasterPos2f(input_left + 10, text_y)
        for ch in display_text:
            glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))

        # Blinking cursor for active field
        if is_active and TRANSFORM_DIALOG_CURSOR_BLINK < 35:
            cursor_x = input_left + 10 + len(field_value) * 7.5
            gl.glColor3f(0.90, 0.90, 0.98)
            gl.glLineWidth(1.5)
            gl.glBegin(gl.GL_LINES)
            gl.glVertex2f(cursor_x, field_y_top + 6)
            gl.glVertex2f(cursor_x, field_y_bot - 6)
            gl.glEnd()

        # Description text below field
        gl.glColor3f(0.50, 0.52, 0.58)
        gl.glRasterPos2f(input_left, field_y_bot + 14)
        for ch in desc_text:
            glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_10, ord(ch))

    # ── Hint text ────────────────────────────────────────────────────────
    if TRANSFORM_DIALOG_TYPE == "Transform About a Point":
        hint = "Scales, then rotates around the pivot. Enter applies; Esc cancels."
    elif TRANSFORM_DIALOG_TYPE == "Transform About an Axis":
        hint = "Reflects across the line through the two axis points. Enter applies; Esc cancels."
    else:
        hint = "Enter to apply, Esc to cancel. Reference: Canvas Origin (0, 0)."
    hint_y = dlg_top + 55 + num_fields * 60 + 18
    gl.glColor3f(0.50, 0.52, 0.58)
    gl.glRasterPos2f(dlg_left + 20, hint_y)
    for ch in hint:
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_10, ord(ch))

    # ── Buttons ──────────────────────────────────────────────────────────
    btn_w = 90
    btn_h = 32
    btn_y_top = dlg_bottom - 18 - btn_h
    btn_y_bot = btn_y_top + btn_h

    # Apply button (right-aligned, accent color)
    apply_btn_left = dlg_right - 20 - btn_w
    gl.glColor3f(0.22, 0.50, 0.88)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(apply_btn_left, btn_y_top)
    gl.glVertex2f(apply_btn_left + btn_w, btn_y_top)
    gl.glVertex2f(apply_btn_left + btn_w, btn_y_bot)
    gl.glVertex2f(apply_btn_left, btn_y_bot)
    gl.glEnd()
    gl.glColor3f(1.0, 1.0, 1.0)
    gl.glRasterPos2f(apply_btn_left + 26, btn_y_top + 21)
    for ch in "Apply":
        glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_12, ord(ch))

    # Cancel button (to the left of Apply)
    cancel_btn_left = apply_btn_left - btn_w - 12
    gl.glColor3f(0.30, 0.30, 0.35)
    gl.glBegin(gl.GL_QUADS)
    gl.glVertex2f(cancel_btn_left, btn_y_top)
    gl.glVertex2f(cancel_btn_left + btn_w, btn_y_top)
    gl.glVertex2f(cancel_btn_left + btn_w, btn_y_bot)
    gl.glVertex2f(cancel_btn_left, btn_y_bot)
    gl.glEnd()
    gl.glColor3f(0.85, 0.85, 0.90)
    gl.glRasterPos2f(cancel_btn_left + 23, btn_y_top + 21)
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
    draw_pattern_dialog()
    draw_transform_dialog()

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
    glut.glutSpecialFunc(special_keyboard)
    glut.glutMouseFunc(mouse)
    glut.glutPassiveMotionFunc(passive_motion)

    # ------------------------------------------------------------------------
    # Print usage info
    # ------------------------------------------------------------------------

    print("=== Line, Circle & Ellipse Drawing Algorithm Application ===")
    print(f"Default algorithm: {CURRENT_ALGORITHM}")
    print(f"Default color: {CURRENT_COLOR}")
    print(f"Default width: {CURRENT_LINE_WIDTH}")
    print(f"Default style: {CURRENT_LINE_STYLE}")
    print("Click two points on the canvas to draw a line.")
    print("For Mid Point Circle: click centre, then a point to define the radius.")
    print("For Mid Point Ellipse: click centre, then rx point, then ry point.")
    print("Press 'P' to save a screenshot to output/")
    print("Press 'Esc' to exit.")

    # ------------------------------------------------------------------------
    # Start Event Loop
    # ------------------------------------------------------------------------

    glut.glutMainLoop()
