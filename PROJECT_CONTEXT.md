# Computer Graphics Lab Work (5th Sem) - Project Context & Architecture

This document provides a complete, self-contained reference of the architecture, algorithms, data structures, UI systems, and file mappings of this repository so AI models and developers can work effectively without scanning the full codebase.

---

## 1. Project Overview & Directory Structure

This repository contains implementation and interactive demonstration software for 5th Semester Computer Graphics Lab experiments:

```
CG_labwork_5th_sem/
├── PROJECT_CONTEXT.md                # [This file] Complete project architecture & context reference
├── README.md                         # General repository information
├── requirements.txt                  # Python dependencies (PyOpenGL, PyOpenGL_accelerate, numpy)
├── app/
│   ├── src/
│   │   ├── main.py                   # App launcher (imports line_drawing_app and calls run())
│   │   └── line_drawing_app.py       # Core interactive OpenGL GUI application (~6,000 lines)
│   └── saved_drawings/               # JSON files of saved drawings and test cases
├── Brestenham/                       # Bresenham line drawing experiment
│   ├── src/bresenham.py              # Launcher -> opens line_drawing_app (or --headless for PNG)
│   └── outputs/                      # Generated test case PNG outputs
├── SimpleDDA/                        # Simple Digital Differential Analyzer line drawing
│   ├── src/simple_dda.py
│   └── outputs/
├── SymmetricDDA/                     # Symmetric Digital Differential Analyzer line drawing
│   ├── src/symmetric_dda.py
│   └── outputs/
├── MidPointCircle/                   # Midpoint circle generation experiment
│   ├── src/mid_point_circle.py
│   └── outputs/
├── MidPointEllipse/                  # Midpoint ellipse generation experiment
│   ├── src/mid_point_ellipse.py
│   └── outputs/
├── BasicTransformations2D/           # 2D Basic Transformations: Translation, Scaling, Rotation
│   ├── src/basic_transformations.py  # Launcher -> opens line_drawing_app (or --headless for PNG)
│   └── outputs/
├── CompositeTransformations2D/       # 2D Composite Transformations (About Point / About Axis)
│   ├── src/composite_transformations.py # Launcher -> opens line_drawing_app (or --headless for PNG)
│   └── outputs/
├── BoundaryFill/                     # Experiment 8: 4-Way & 8-Way Boundary Fill
│   ├── src/boundary_fill.py          # Standalone runner / headless test case generator
│   ├── docs/generate_report.py       # Comprehensive Word (.docx) report generator
│   └── outputs/                      # Headless test case screenshots (TC1-TC4)
├── FloodFill/                        # Experiment 9: 4-Way & 8-Way Flood Fill
│   ├── src/flood_fill.py             # Standalone runner / headless test case generator
│   ├── docs/generate_report.py       # Comprehensive Word (.docx) report generator
│   └── outputs/                      # Headless test case screenshots (TC1-TC4)
└── ScanLineFill/                     # Experiment 10: Scan-Line Polygon Fill
    ├── src/scan_line_fill.py         # Standalone runner / headless test case generator
    ├── docs/generate_report.py       # Comprehensive Word (.docx) report generator
    └── outputs/                      # Headless test case screenshots (TC1-TC4)
```

---

## 2. Core Application: `app/src/line_drawing_app.py`

The interactive application is built with **Python 3**, **PyOpenGL**, and **GLUT**.

### 2.1 Coordinate Systems & Projections
1. **Grid Coordinates $(gx, gy)$**:
   - Discrete Cartesian coordinates centered at $(0, 0)$.
   - 1 grid unit corresponds to `GRID_SIZE` (default $1.5$ px) in world space.
2. **World Coordinates $(wx, wy)$**:
   - $wx = gx \cdot \text{GRID\_SIZE}$, $wy = gy \cdot \text{GRID\_SIZE}$.
   - Origin $(0, 0)$ is at the canvas center (adjusted by `CANVAS_OFFSET_X, CANVAS_OFFSET_Y`).
3. **Screen / GLUT Coordinates $(x, y)$**:
   - Top-left origin $(0, 0)$ to $(W, H)$ in window pixels.
   - Top Menu Bar: $y \in [0, 38]$ (`MENU_BUTTON_HEIGHT = 38`).
   - Secondary Ribbon: $y \in [38, 64]$ (`MENU_HEIGHT = 64`).
   - Canvas Viewport: $y \in [64, H]$.

### 2.2 Projections
- `setup_canvas_projection(width, height)`:
  - Orthographic 2D projection centered at $(cx, cy) = (\text{OFFSET\_X} \cdot \text{GRID\_SIZE}, \text{OFFSET\_Y} \cdot \text{GRID\_SIZE})$.
  - Extents: $\pm \frac{\text{width}}{2 \cdot \text{CANVAS\_SCALE}}$, $\pm \frac{\text{height}}{2 \cdot \text{CANVAS\_SCALE}}$.
- `setup_menu_projection()`:
  - Full-window 2D orthographic $(0, W, H, 0)$ for top-left GUI menus, dropdowns, and overlays.

---

## 3. Key Global State Variables

| Variable | Type | Description |
| :--- | :--- | :--- |
| `CURRENT_ALGORITHM` | `str` | Active algorithm: `"Bresenham"`, `"Simple DDA"`, `"Symmetric DDA"`, `"Mid Point Circle"`, `"Mid Point Ellipse"`, `"Polygon Build"` |
| `CURRENT_COLOR` | `str` | Current drawing color: `"Red"`, `"Green"`, `"Blue"`, `"Cyan"`, `"Magenta"`, `"Yellow"`, `"White"`, `"Gray"` |
| `CURRENT_LINE_WIDTH`| `int` | Line stroke width in pixels ($1$ to $5$) |
| `CURRENT_LINE_STYLE`| `str` | `"Solid"`, `"Dotted"`, `"Dashed"`, `"UserDefined"` |
| `drawn_lines` | `list[dict]`| Primary canvas shapes list (stores lines, circles, ellipses, polygons) |
| `selected_points` | `list[tuple]`| Unconfirmed points clicked by user for the current drawing operation |
| `undo_stack` / `redo_stack` | `list` | Full undo/redo deepcopy history |
| `SELECT_MODE` | `bool` | True when Selective Cursor tool is active (`S` key toggle) |
| `SELECTED_SHAPE_INDICES`| `set[int]`| Set of indices into `drawn_lines` currently selected for transformations |
| `CANVAS_SCALE` | `float` | Canvas zoom scale factor ($0.2$ to $8.0$, default $1.0$) |
| `IS_DRAGGING_SCALE_SLIDER`| `bool` | True when user is dragging the zoom slider handle |
| `CANVAS_OFFSET_X, Y`| `float` | Pan offset in grid units |
| `IS_PANNING` | `bool` | True during right-click or middle-click drag panning |
| `PICKING_PIVOT` | `bool` | True when awaiting user click on canvas to select pivot point |
| `CURRENT_PIVOT` | `tuple` | $(gx, gy)$ of current pivot marker on canvas |
| `PICKING_AXIS_STEP`| `int` | $0$ = idle, $1$ = picking 1st point, $2$ = picking 2nd point for reflection axis |
| `CURRENT_AXIS` | `tuple` | $((x_1, y_1), (x_2, y_2))$ endpoints of reflection axis |
| `OPEN_MENU` | `str \| None` | Currently open top menu dropdown (`"Algorithms"`, `"Line Parameters"`, `"Transformations"`, `"Canvas Scale"`, etc.) |

---

## 4. Shape Data Representation in `drawn_lines`

1. **Line**:
   ```python
   {
       "type": "line",
       "p1": (x1, y1), "p2": (x2, y2),
       "algorithm": "Bresenham",
       "color": "Red", "width": 1, "style": "Solid",
       "line_points": [(x1, y1), ..., (x2, y2)],
       "smooth": False # True for vector polygon lines
   }
   ```
2. **Circle**:
   ```python
   {
       "type": "circle",
       "center": (cx, cy), "radius": r, "radius_point": (rpx, rpy),
       "algorithm": "Mid Point Circle",
       "color": "Blue", "width": 1, "style": "Solid",
       "circle_points": [(x, y), ...]
   }
   ```
3. **Ellipse**:
   ```python
   {
       "type": "ellipse",
       "center": (cx, cy), "rx": rx, "ry": ry,
       "rx_point": (rx_x, rx_y), "ry_point": (ry_x, ry_y), "angle": float,
       "algorithm": "Mid Point Ellipse",
       "color": "Cyan", "width": 1, "style": "Solid",
       "ellipse_points": [(x, y), ...]
   }
   ```
4. **Polygon** (Closed Smooth Vector Shape):
   ```python
   {
       "type": "polygon",
       "vertices": [(x0, y0), (x1, y1), ..., (xn-1, yn-1)],
       "algorithm": "Polygon Build",
       "color": "Red", "width": 2, "style": "Solid",
       "smooth": True
   }
   ```

---

## 5. Transformations & Mathematical Pipeline

Homogeneous $3 \times 3$ affine transformation matrices applied in column or row vector format:
- **Translation**:
  $$T(t_x, t_y) = \begin{bmatrix} 1 & 0 & t_x \\ 0 & 1 & t_y \\ 0 & 0 & 1 \end{bmatrix}$$
- **Scaling**:
  $$S(s_x, s_y) = \begin{bmatrix} s_x & 0 & 0 \\ 0 & s_y & 0 \\ 0 & 0 & 1 \end{bmatrix}$$
- **Rotation**:
  $$R(\theta) = \begin{bmatrix} \cos\theta & -\sin\theta & 0 \\ \sin\theta & \cos\theta & 0 \\ 0 & 0 & 1 \end{bmatrix}$$
- **Composite About Pivot Point $(x_p, y_p)$**:
  $$M = T(x_p, y_p) \cdot R(\theta) \cdot S(s_x, s_y) \cdot T(-x_p, -y_p)$$
- **Arbitrary Axis Reflection**:
  Translates line to origin, rotates axis to align with X-axis, reflects across X ($y \to -y$), reverses rotation, and translates back.
- **Direct Axis Reflections**:
  - Across X-axis: $y \to -y$, $M = \text{diag}(1, -1, 1)$
  - Across Y-axis: $x \to -x$, $M = \text{diag}(-1, 1, 1)$
- **Multi-Operation Pipeline ($M_{total} = M_n \cdot \dots \cdot M_1$)**:
  Sequentially parses and composes multiple operations separated by semicolons:
  - `T:tx,ty` -> Translation
  - `R:angle` (or `R:angle,px,py`) -> Rotation
  - `S:sx,sy` -> Scaling
  - `RE:spec` -> Reflection about line (e.g. `RE:y=mx+3`, `RE:y=2x+1`, `RE:x`, `RE:y`, etc.)

When `SELECTED_SHAPE_INDICES` is non-empty, transformations apply strictly to selected shapes. When empty, they apply to all canvas shapes.

---

## 6. UI Systems & Controls

1. **Top Menu Bar**:
   - `Algorithms` (formerly Line Drawing Algorithm): Bresenham, Simple DDA, Symmetric DDA, Mid Point Circle, Mid Point Ellipse, Polygon Build.
     *(Note: Specific experiment launchers automatically pre-select their matching algorithm upon startup: `Polygon Build` for `BasicTransformations2D` and `CompositeTransformations2D`, `Mid Point Circle` for `MidPointCircle`, etc.).*
   - `Line Parameters`: Color, Line Width, Line Style.
   - `Transformations`:
     - Basic Transformations: Translation, Scaling, Rotation.
     - Composite Transformations: About a Point, About an Axis, Reflect About X-Axis, Reflect About Y-Axis, Multi Operation.
     *(Note: The redundant selection button in this dropdown was removed to keep the menu focused, while the selection feature remains fully operational via `S` hotkey, ribbon button, and Options menu).*
   - `Canvas Scale`: Dedicated interactive slider panel. Features:
     - Real-time scale percentage badge.
     - Smooth slider track with 100% center notch, thumb handle, and range 25% – 500%.
     - Streamlined UI: All duplicate zoom controls (floating HUD, modal dialogs, ribbon quick zoom, preset chips) have been cleanly removed so only this slider panel controls canvas zoom from the UI.
   - `Options`: Clear Canvas, Undo, Redo, Toggle Select Tool.
   - `Import File`: Loads saved `.json` drawings from `app/saved_drawings/`.

2. **Axis Lines & Styling**:
   - Both Cartesian coordinate axes (X and Y origin lines) and reflection axis lines are rendered in clean, high-contrast black (`(0.0, 0.0, 0.0)`).
   - Reflection axes feature dashed line styling with labeled endpoints and black endpoint handles.

3. **Dumbbell Connectors & Screen Invariance**:
   - Permanent dumbbell connector dots are rendered at all connectable endpoints and polygon vertices.
   - Dot radii are automatically compensated by $1.0 / \text{CANVAS\_SCALE}$ so they remain strictly constant in screen pixels at any zoom level.
   - Line strokes rendered with OpenGL `glLineWidth` stay constant in screen pixels without distortion or magnification artifacts.
   - Smooth vector lines (`Polygon Build`) bypass discrete integer rasterization steps and render with anti-aliasing (`GL_LINE_SMOOTH`, `GL_BLEND`) for clean, smooth vector paths.

4. **Selection Tool & Multi-Selection**:
   - `S`: Toggle Selective Cursor Mode.
   - **Cumulative Click Selection**: Clicking an unselected polygon/shape adds it to the selection; clicking an already selected polygon toggles it off.
   - **Marquee Drag Selection**: Dragging the left mouse button across the canvas draws a translucent glowing blue bounding box with corner tick marks and selects all polygons/shapes intersecting or enclosed by the box.
   - `A` or `Ctrl+A`: Select All polygons/shapes on the canvas when in Select Mode.
   - **Clear Selection**: Clicking on empty canvas or pressing `Esc` deselects all shapes.
   - **Visual Feedback**: Bounding box surrounds the entire selection group with a live summary badge (e.g. `Selected: 3 polygons`), glowing cyan halos, and ribbon pill count.
   - **Batch Transformation**: Applying any transformation (Translation, Rotation, Scaling, Reflection, Multi Operation) transforms all selected polygons simultaneously.

5. **Keyboard Hotkeys**:
   - `S`: Toggle Selective Cursor Mode.
   - `A` / `Ctrl+A`: Select All (in Select Mode).
   - `Esc`: Close open dropdown / cancel current action / deselect shapes / cancel polygon build.
   - `Ctrl+Z` or `U`: Undo.
   - `Ctrl+Y` or `R`: Redo.
   - `P`: Save high-resolution PNG screenshot to `output/`.
   - `Enter`: Confirm current input dialog or finalize/close in-progress Polygon Build.
   - `+` / `-` / `0`: Canvas zoom in, zoom out, reset to 100%.

6. **Mouse Gestures**:
   - Left Click: Place points, toggle shapes in Select Mode, drag slider thumb, or click UI elements.
   - Left-Click Drag (in Select Mode): Draw marquee selection box to select multiple shapes.
   - Right-Click Drag or Middle-Click Drag: Pan canvas.
   - Scroll Wheel: Zoom canvas in / out.

---

## 7. Filling Algorithms (Pop-up Application)

- **Launch**: Selected from `Algorithms` -> `Filling Algorithms` in the main application menu (`app/src/line_drawing_app.py`), or run directly via `python app/src/filling_window.py`.
- **Process Architecture**: Launched as a distinct subprocess (`subprocess.Popen`) to maintain OpenGL / GLUT context independence on macOS Cocoa.
- **Visual Style & Layout**:
  - **Left Control Sidebar** (`SIDEBAR_WIDTH = 250`): Permanent studio dark control panel on the left containing all settings vertically organized: Algorithms, Tools/Modes, 5 Boundary Colors, 5 Fill Colors, Action Buttons, and Live Status & Guide card.
  - **Graph-Paper Canvas** (Right): Spans from `x = 250` across full window height. Canvas background matches the main studio app (`CANVAS_BG_COLOR = (0.972, 0.980, 0.988, 1.0)`) with light blue graph-paper grid lines (`GRID_LINE_COLOR = (0.78, 0.85, 0.92)`, cell size 20 px).
- **Palettes (5 Boundary Colors & 5 Fill Colors)**:
  - Boundary: Black, Navy Blue, Dark Green, Dark Red, Purple.
  - Fill: Red, Green, Blue, Yellow, Orange.
- **Interaction Modes**:
  - **Draw Brush Mode** (2-Click Freehand Boundary Tracing):
    - 1st Click: Starts drawing mode; as mouse moves over grid, all touched cells are colored with active boundary color.
    - Continuous Bresenham grid interpolation prevents diagonal/orthogonal leaks during rapid mouse movement.
    - 2nd Click: Seals boundary path and ends current shape; remains in Draw Brush Mode to allow drawing multiple polygons.
  - **Grid Click Mode** (Point & Drag Direct Cell Drawing):
    - Click directly on any grid cell to color it with the active boundary color.
    - Clicking on an already colored boundary cell erases it (toggles off for precision correction).
    - Mouse drag allows painting continuous cells directly.
  - **Fill Mode** (Seed Point & Fill):
    - Activated explicitly via the ribbon `[🪣 Fill Mode]` pill or `F` key.
    - Clicking inside any closed boundary sets the Seed Point.
    - Marked with a high-contrast glowing seed indicator (concentric dark contrast ring, bright gold ring, and white center pip) ensuring visibility over all fill colors.
    - Triggers boundary fill propagation.
- **Supported Algorithms**:
  - `4-Way Boundary Fill`: Orthogonal 4-neighbor expansion; stops at pixels matching the boundary color.
  - `8-Way Boundary Fill`: 8-neighbor expansion (orthogonal + diagonal); stops at pixels matching the boundary color.
  - `4-Way Flood Fill`: Orthogonal 4-neighbor expansion; replaces all connected pixels matching the seed's old color.
  - `8-Way Flood Fill`: 8-neighbor expansion; replaces all connected pixels matching the seed's old color.
  - `Scan-Line Fill`: Edge Table (ET) & Active Edge Table (AET) rasterization with parity span filling.
- **Key Conceptual Differences (Boundary vs Flood vs Scan-Line Fill)**:
  - **Boundary Fill**: Knows the *boundary color*. Fills all reachable pixels that are *neither* boundary color *nor* fill color. Requires an enclosed boundary of a single color, but interior pixels can vary.
  - **Flood Fill**: Knows the *original interior color* at the seed point. Replaces only pixels that match this old color with the fill color. Does not require a single boundary color, but operates on monochromatic regions.
  - **Scan-Line Fill**: Operates on *geometric vector edges* using scanline coherence. Completely seedless, immune to diagonal boundary leakage, and native support for interior holes.
- **Animation**:
  - Smooth animated BFS queue filling with live cell count and timer callback.
  - Speed modes: `Smooth (Animated)`, `Fast (Animated)`, `Instant Fill`.
- **Undo & Redo System**:
  - Full multi-step history stack (up to 50 operations) with bidirectional Undo and Redo.
  - Snapshot points: Click 1 in Draw Brush mode, mouse-down drag gestures in Grid Click mode, Fill executions, and Clear Canvas.
  - Dedicated **[ Undo (Ctrl+Z / U) ]** button in the left sidebar under `ACTIONS` with live step counter badge (e.g. `[1]`, `[2]`) and active glow state.
  - `Esc` cancels any in-progress brush boundary and reverts to the state prior to Click 1.
- **Hotkeys**:
  - `Ctrl+Z` / `U`: Undo last action.
  - `Ctrl+Y` / `R`: Redo undone action.
  - `B`: Draw Brush Mode.
  - `G` / `D`: Grid Click Mode.
  - `F`: Fill Mode.
  - `1`: 4-Way Boundary Fill.
  - `2`: 8-Way Boundary Fill.
  - `3`: 4-Way Flood Fill.
  - `4`: 8-Way Flood Fill / toggle.
  - `5` / `S`: Scan-Line Fill.
  - `8`: 8-Way toggle.
  - `Tab`: Cycle sequentially through all 5 algorithms.
  - `C`: Clear Grid.
  - `P`: Save Screenshot to `outputs/`.
  - `Esc`: Cancel active brush tracing / exit.

---

## 8. Experiment 8: Boundary Fill (`BoundaryFill/`)

- **Source Code**: [`BoundaryFill/src/boundary_fill.py`](BoundaryFill/src/boundary_fill.py)
- **Report Generator**: [`BoundaryFill/docs/generate_report.py`](BoundaryFill/docs/generate_report.py)
- **Output Report**: [`BoundaryFill/docs/BoundaryFill_Experiment_Report.docx`](BoundaryFill/docs/BoundaryFill_Experiment_Report.docx)
- **Test Cases & Connectivity Matrix**:
  | Test Case | Fill Variant | Boundary Type | Expected Behavior | Rationale |
  |---|---|---|---|---|
  | **TC1** | 4-Way Boundary Fill | 4-Connected Rectangle | **CONTAINED** (352 cells) | Orthogonal expansion cannot cross solid 4-connected boundary. |
  | **TC2** | 4-Way Boundary Fill | 8-Connected Diamond | **CONTAINED** (113 cells) | 4-way fill moves only orthogonally; cannot traverse diagonal gaps. |
  | **TC3** | 8-Way Boundary Fill | 4-Connected Rectangle | **CONTAINED** (352 cells) | Solid boundary leaves no orthogonal or diagonal openings. |
  | **TC4** | 8-Way Boundary Fill | 8-Connected Diamond | **LEAKS** (1328 cells) | Diagonal steps slip through diagonal boundary corner gaps into background. |
- **Execution**:
  ```bash
  python BoundaryFill/src/boundary_fill.py            # Interactive visualizer
  python BoundaryFill/src/boundary_fill.py --headless # Generate actual app window screenshots
  python BoundaryFill/docs/generate_report.py         # Generate Word laboratory report
  ```

---

## 9. Experiment 9: Flood Fill (`FloodFill/`)

- **Source Code**: [`FloodFill/src/flood_fill.py`](FloodFill/src/flood_fill.py)
- **Report Generator**: [`FloodFill/docs/generate_report.py`](FloodFill/docs/generate_report.py)
- **Output Report**: [`FloodFill/docs/FloodFill_Experiment_Report.docx`](FloodFill/docs/FloodFill_Experiment_Report.docx)
- **Test Cases & Connectivity Matrix (Hybrid Demonstration Suite)**:
  | Test Case | Fill Variant | Benchmark Geometry | Expected Behavior | Rationale |
  |---|---|---|---|---|
  | **TC1** | 4-Way Flood Fill | Multi-Colored 4-Connected Rectangle | **CONTAINED** (352 cells) | Color replacement of Yellow interior with Blue inside a 4-color boundary (Navy, Red, Green, Purple) where Boundary Fill would fail. |
  | **TC2** | 4-Way Flood Fill | 8-Connected Dual-Chamber (Bottleneck) | **PARTIAL FILL** (81 cells) | Seeded in Chamber 1; 4-way orthogonal steps cannot traverse diagonal corner `(15,14) -> (16,15)`. Chamber 2 remains 100% Yellow. |
  | **TC3** | 8-Way Flood Fill | 8-Connected Dual-Chamber (Bridged) | **FULL FILL** (162 cells) | 8-way diagonal steps bridge the diagonal corner bottleneck, successfully filling both chambers completely. |
  | **TC4** | 8-Way Flood Fill | Multi-Colored 8-Connected Diamond | **LEAKS** (1328 cells) | 8-way diagonal search slips through diagonal gaps between diamond boundary pixels into the empty canvas background. |
- **Execution**:
  ```bash
  python FloodFill/src/flood_fill.py            # Interactive visualizer (loads Flood Fill)
  python FloodFill/src/flood_fill.py --headless # Generate actual app window screenshots
  python FloodFill/docs/generate_report.py      # Generate Word laboratory report
  ```

---

## 10. Experiment 10: Scan-Line Polygon Fill (`ScanLineFill/`)

- **Source Code**: [`ScanLineFill/src/scan_line_fill.py`](ScanLineFill/src/scan_line_fill.py)
- **Report Generator**: [`ScanLineFill/docs/generate_report.py`](ScanLineFill/docs/generate_report.py)
- **Output Report**: [`ScanLineFill/docs/ScanLineFill_Experiment_Report.docx`](ScanLineFill/docs/ScanLineFill_Experiment_Report.docx)
- **Test Cases & Benchmark Suite**:
  | Test Case | Fill Variant | Benchmark Geometry | Expected Behavior | Rationale |
  |---|---|---|---|---|
  | **TC1** | Scan-Line Fill | Convex Pentagon (5 vertices) | **CONVEX COHERENCE** (347 cells) | Single span `[x1, x2]` per scanline demonstrating basic slope coherence (`x <- x + 1/m`). |
  | **TC2** | Scan-Line Fill | Concave Arrowhead (4 vertices) | **MULTI-SPAN PARITY** (150 cells) | Even-odd parity fills two disjoint wing spans (`[x1, x2]` and `[x3, x4]`) while leaving the concave cavity unfilled. |
  | **TC3** | Scan-Line Fill | 10-Point Star Polygon | **EXTREMA PARITY** (204 cells) | Half-open interval `[y_min, y_max)` counts local extrema twice and monotonic edges once, preventing parity glitches. |
  | **TC4** | Scan-Line Fill | Compound Frame with Void (Donut) | **VOID PRESERVED** (340 cells) | Multi-loop Edge Table automatically leaves the interior hole untouched without requiring interior seed points. |
- **Execution**:
  ```bash
  python ScanLineFill/src/scan_line_fill.py            # Interactive visualizer (loads Scan-Line Fill)
  python ScanLineFill/src/scan_line_fill.py --headless # Generate actual app window screenshots
  python ScanLineFill/docs/generate_report.py         # Generate Word laboratory report (.docx)
  ```
