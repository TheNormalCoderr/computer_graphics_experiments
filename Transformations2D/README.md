# 2D Basic Transformations using OpenGL in Python

**Subject:** Computer Graphics  
**Language:** Python  
**Graphics Library:** PyOpenGL with GLUT/FreeGLUT

---

## What are 2D Transformations?

**2D Transformations** are operations that alter the position, size, or orientation of objects in a two-dimensional plane. The three basic transformations are:

1. **Translation** — moves an object by a displacement vector (tx, ty).
2. **Scaling** — changes the size of an object by scale factors (sx, sy) relative to the origin.
3. **Rotation** — rotates an object by an angle θ (counter-clockwise) about the origin.

All three can be expressed as **3×3 homogeneous transformation matrices** so that any transformation is a simple matrix–vector multiplication:

```
Translation:             Scaling:                Rotation:
| 1  0  tx |             | sx  0  0 |            | cos θ  -sin θ  0 |
| 0  1  ty |             |  0 sy  0 |            | sin θ   cos θ  0 |
| 0  0   1 |             |  0  0  1 |            |   0       0    1 |
```

A point **(x, y)** is represented in homogeneous coordinates as **[x, y, 1]ᵀ**, and the transformed point is **M · [x, y, 1]ᵀ**.

---

## Shared Dependency Installation

A shared virtual environment is maintained at the **repository root** so that all Computer Graphics experiments use the same Python environment.

```bash
# From the repository root
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

---

## Running the Program

```bash
# From the repository root
python Transformations2D/src/transformations_2d.py
```

The program opens **three OpenGL windows**, one for each test case:
1. Translation of a square
2. Scaling of a square
3. Rotation of a square

Each window shows both the **original** (blue) and **transformed** (red) polygon on a labelled grid. The output PNGs are auto-saved to the `outputs/` directory.

Press **Esc** or **Q** in any window to exit.

---

## Folder Structure

```text
computer_graphics_experiments/
├── .venv/                                ← Shared virtual environment (not committed)
├── requirements.txt                      ← Shared project dependencies
├── .gitignore
├── README.md
└── Transformations2D/
    ├── src/
    │   └── transformations_2d.py         ← Transformation implementation using PyOpenGL
    ├── outputs/
    │   ├── tc1_translation.png
    │   ├── tc2_scaling.png
    │   └── tc3_rotation.png
    ├── docs/
    └── README.md
```

---

## Test Cases

| # | Original Shape | Transformation | Parameters | Output |
|---|----------------|----------------|------------|--------|
| 1 | Square (2,2)→(6,6) | Translation | tx=5, ty=3 | `tc1_translation.png` |
| 2 | Square (2,2)→(5,5) | Scaling | sx=2, sy=1.5 | `tc2_scaling.png` |
| 3 | Square (6,2)→(10,6) | Rotation | θ=45° (about origin) | `tc3_rotation.png` |

---

## Transformation Matrices Used

### Test Case 1 — Translation (tx=5, ty=3)
```
| 1  0  5 |
| 0  1  3 |
| 0  0  1 |
```

### Test Case 2 — Scaling (sx=2, sy=1.5)
```
| 2    0    0 |
| 0    1.5  0 |
| 0    0    1 |
```

### Test Case 3 — Rotation (θ=45°)
```
| 0.7071  -0.7071  0 |
| 0.7071   0.7071  0 |
|   0        0     1 |
```

---

## Visualisation

The program renders for each test case:

- A Cartesian reference grid with labelled axes
- The **original polygon** in blue with vertex coordinates
- The **transformed polygon** in red with vertex coordinates
- A colour legend distinguishing original from transformed
- Three separate windows, one per transformation type

---

## Algorithm Summary

```text
INPUT:  A polygon defined by vertices V = {(x₁,y₁), (x₂,y₂), …, (xₙ,yₙ)}
        A transformation type and its parameters

1. Construct the 3×3 homogeneous transformation matrix M
   based on the transformation type and parameters.

2. FOR each vertex (xᵢ, yᵢ) in V:
       [x'ᵢ]       [xᵢ]
       [y'ᵢ] = M · [yᵢ]
       [ 1 ]       [ 1]
   END FOR

3. Render the original polygon (blue) and the
   transformed polygon (red) on the grid.

OUTPUT: Visual comparison of original vs. transformed polygon.
```

---

## GitHub Repository

https://github.com/TheNormalCoderr/computer_graphics_experiments
