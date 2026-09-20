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

---

## Interactive Drawing Application

The repository also includes a comprehensive interactive drawing workbench that integrates line drawing, circle/ellipse algorithms, custom patterns, and 2D basic & composite transformation dialogs:

```bash
# Launch interactive application
python app/src/line_drawing_app.py
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