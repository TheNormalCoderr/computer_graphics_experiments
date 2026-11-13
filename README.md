# Computer Graphics Experiments (5th Semester)

This repository contains practical laboratory implementations and interactive visualizers for fundamental Computer Graphics algorithms in Python using PyOpenGL, GLUT/FreeGLUT, and custom rasterization routines.

---

## Laboratory Experiments

| # | Experiment Name | Directory | Key Topics / Implementations |
|---|-----------------|-----------|------------------------------|
| 1 | **Simple DDA** | [`SimpleDDA/`](SimpleDDA/) | Digital Differential Analyzer line algorithm with floating-point steps |
| 2 | **Symmetric DDA** | [`SymmetricDDA/`](SymmetricDDA/) | Power-of-two step DDA suitable for hardware shift implementation |
| 3 | **Bresenham's Line Algorithm** | [`Brestenham/`](Brestenham/) | Fast integer-only incremental line rasterization |
| 4 | **Midpoint Circle Algorithm** | [`MidPointCircle/`](MidPointCircle/) | 8-way symmetric decision variable circle drawing |
| 5 | **Midpoint Ellipse Algorithm** | [`MidPointEllipse/`](MidPointEllipse/) | 4-way symmetric two-region decision variable ellipse drawing |
| 6 | **2D Basic Transformations** | [`BasicTransformations2D/`](BasicTransformations2D/) | Translation, Scaling, and Rotation using 3×3 homogeneous matrices |
| 7 | **2D Composite Transformations** | [`CompositeTransformations2D/`](CompositeTransformations2D/) | Pivot rotation, fixed-point scaling, arbitrary axis reflection, and multi-step sequence compounding |
| 8 | **Boundary Fill Algorithm** | [`BoundaryFill/`](BoundaryFill/) | 4-Way & 8-Way boundary fill on 4-connected and 8-connected boundaries (leak analysis) |
| 9 | **Flood Fill Algorithm** | [`FloodFill/`](FloodFill/) | 4-Way & 8-Way fill: multi-colored boundary containment, diagonal bottleneck bridging, and boundary leakage |
| 10 | **Scan-Line Polygon Fill Algorithm** | [`ScanLineFill/`](ScanLineFill/) | Edge Table & Active Edge Table: scanline coherence, parity multi-span, vertex coincidence, and seedless hole preservation |
| 11 | **Point Clipping Algorithm** | [`PointClipping/`](PointClipping/) / [`PointClipping2/`](PointClipping2/) | 2D rectangular window clipping: interior, exterior, mixed distribution, and boundary/corner inequality evaluation |
| 12 | **Liang-Barsky Line Clipping** | [`LiangBarsky(Line clipping)/`](LiangBarsky(Line%20clipping)/) | Parametric line clipping using inequalities and t-interval intersection |
| 13 | **Weiler-Atherton Polygon Clipping** | [`Weiler_Atherton(Polygon Clipping)/`](Weiler_Atherton(Polygon%20Clipping)/) | Dual clockwise vertex-list traversal for convex and concave polygons (including disjoint splits) |
| 14 | **Bezier Curve Generation** | [`Bezier_Curve/`](Bezier_Curve/) | Interactive parametric Bezier curves of arbitrary degree using Bernstein basis polynomials |
| 15 | **B-Spline Curve Generation** | [`B-Spline/`](B-Spline/) | Clamped open-uniform quadratic B-Spline curves using recursive Cox-de Boor basis functions |

---

## Interactive Drawing Application

The repository also includes a comprehensive interactive drawing workbench that integrates line drawing, circle/ellipse algorithms, custom patterns, and 2D basic & composite transformation dialogs, along with a dedicated Filling Algorithms studio window:

```bash
# Launch interactive application
python app/src/line_drawing_app.py

# Launch interactive filling workbench directly
python app/src/filling_window.py
```

---

## Shared Virtual Environment Setup

A shared virtual environment at the repository root serves all experiments:

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

---

## Running Individual Experiments

### Experiment 6: 2D Basic Transformations
```bash
# Interactive OpenGL visualizer
python BasicTransformations2D/src/basic_transformations.py

# Generate laboratory Word report
python BasicTransformations2D/docs/generate_report.py
```

### Experiment 7: 2D Composite Transformations
```bash
# Interactive OpenGL visualizer
python CompositeTransformations2D/src/composite_transformations.py

# Headless generation of output images
python CompositeTransformations2D/src/composite_transformations.py --headless

# Generate laboratory Word report
python CompositeTransformations2D/docs/generate_report.py
```

### Experiment 8: Boundary Fill Algorithm
```bash
# Interactive visualizer
python BoundaryFill/src/boundary_fill.py

# Headless generation of actual app window screenshots
python BoundaryFill/src/boundary_fill.py --headless

# Generate laboratory Word report (.docx)
python BoundaryFill/docs/generate_report.py
```

### Experiment 9: Flood Fill Algorithm
```bash
# Interactive visualizer
python FloodFill/src/flood_fill.py

# Headless generation of actual app window screenshots
python FloodFill/src/flood_fill.py --headless

# Generate laboratory Word report (.docx)
python FloodFill/docs/generate_report.py
```

### Experiment 10: Scan-Line Polygon Fill Algorithm
```bash
# Interactive visualizer
python ScanLineFill/src/scan_line_fill.py

# Headless generation of actual app window screenshots
python ScanLineFill/src/scan_line_fill.py --headless

# Generate laboratory Word report (.docx)
python ScanLineFill/docs/generate_report.py
```

### Experiment 11: Point Clipping Algorithm
```bash
# Interactive visualizer
python PointClipping/src/point_clipping.py

# Generate laboratory Word report (.docx)
python PointClipping/docs/generate_report.py
```

### Experiment 12: Liang-Barsky Line Clipping
```bash
# Interactive visualizer / test cases
python "LiangBarsky(Line clipping)/src/test_cases.py"

# Headless generation of test case screenshots
python "LiangBarsky(Line clipping)/src/test_cases.py" --headless

# Generate laboratory Word report (.docx)
python "LiangBarsky(Line clipping)/docs/generate_report.py"
```

### Experiment 13: Weiler-Atherton Polygon Clipping
```bash
# Interactive visualizer / test cases
python "Weiler_Atherton(Polygon Clipping)/src/test_cases.py"

# Headless generation of test case screenshots
python "Weiler_Atherton(Polygon Clipping)/src/test_cases.py" --headless

# Generate laboratory Word report (.docx)
python "Weiler_Atherton(Polygon Clipping)/docs/generate_report.py"
```

### Experiment 14: Bezier Curve Generation
```bash
# Interactive visualizer (click to add, drag to move, 'c' to clear)
python Bezier_Curve/src/BezierCurve.py

# Test case runner / headless screenshot capture
python Bezier_Curve/src/test_cases.py --headless

# Generate laboratory Word report (.docx)
python Bezier_Curve/docs/generate_report.py
```

### Experiment 15: B-Spline Curve Generation
```bash
# Interactive visualizer (click to add, drag to move, 'c' to clear)
python B-Spline/src/BSpline.py

# Test case runner / headless screenshot capture
python B-Spline/src/test_cases.py --headless

# Generate laboratory Word report (.docx)
python B-Spline/docs/generate_report.py
```