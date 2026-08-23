# Mid Point Ellipse Drawing Algorithm using OpenGL in Python

**Subject:** Computer Graphics  
**Language:** Python  
**Graphics Library:** PyOpenGL with GLUT/FreeGLUT

---

## What is the Mid Point Ellipse Algorithm?

The **Mid Point Ellipse Drawing Algorithm** is a scan-conversion algorithm that determines the pixel positions closest to a true ellipse using only integer arithmetic. It exploits the **4-way symmetry** of an ellipse and divides the first quadrant into **two regions** based on the slope of the ellipse curve.

Given a centre **(xc, yc)** and semi-axes **rx** (horizontal) and **ry** (vertical):

**Region 1** (slope magnitude < 1, step in x):
1. Start at the point `(0, ry)` — the top of the ellipse.
2. Initialise the decision parameter: `p1 = ry² − rx²·ry + ¼·rx²`.
3. At each step, if `p1 < 0`, move to `(x+1, y)` and update `p1 += 2·ry²·x + ry²`; if `p1 ≥ 0`, move to `(x+1, y−1)` and update `p1 += 2·ry²·x − 2·rx²·y + ry²`.
4. Continue while `2·ry²·x < 2·rx²·y`.

**Region 2** (slope magnitude ≥ 1, step in y):
5. Initialise the decision parameter: `p2 = ry²·(x+½)² + rx²·(y−1)² − rx²·ry²`.
6. At each step, if `p2 > 0`, move to `(x, y−1)` and update `p2 += −2·rx²·y + rx²`; if `p2 ≤ 0`, move to `(x+1, y−1)` and update `p2 += 2·ry²·x − 2·rx²·y + rx²`.
7. Continue while `y ≥ 0`.

At each step, apply 4-way symmetry to plot all 4 corresponding points: `(xc±x, yc±y)`.

The algorithm is efficient, uses minimal floating-point operations (only for initial parameters), and produces a smooth, complete ellipse from discrete pixel positions.

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

### Standalone Visualization (generates output images)

```bash
# From the repository root
python MidPointEllipse/src/midpoint_ellipse.py --standalone
```

The program opens **two OpenGL windows**, one for each test case. Each window displays the Mid Point Ellipse rasterisation with a reference grid, coordinate labels, coloured plotted pixels, a connected ellipse outline, and semi-axis guide lines. Output images are auto-saved to `MidPointEllipse/outputs/`.

### Using the Shared App

```bash
# From the repository root
python MidPointEllipse/src/midpoint_ellipse.py
```

This launches the shared drawing application with the Mid Point Ellipse algorithm pre-selected. Click a point on the canvas to set the centre, then click a second point to define the horizontal radius (rx), and a third point to define the vertical radius (ry). Dashed guide lines show the distance from the centre during selection.

Press **Esc** or **Q** in any window to exit the program.

---

## Folder Structure

```text
computer_graphics_experiments/
├── .venv/                          ← Shared virtual environment (not committed)
├── requirements.txt                ← Shared project dependencies
├── .gitignore
├── README.md
└── MidPointEllipse/
    ├── src/
    │   └── midpoint_ellipse.py     ← Mid Point Ellipse implementation using PyOpenGL
    ├── outputs/
    │   ├── tc1_horizontal_ellipse.png
    │   └── tc2_vertical_ellipse.png
    ├── docs/
    │   ├── generate_report.py
    │   └── MidPointEllipse_Experiment_Report.docx
    └── README.md
```

---

## Test Cases

| # | Centre | rx | ry | Ellipse Type | Colour | Output |
|---|--------|----|----|-------------|--------|--------|
| 1 | (10, 8) | 5 | 3 | Horizontal Ellipse | Red | `tc1_horizontal_ellipse.png` |
| 2 | (6, 10) | 3 | 5 | Vertical Ellipse | Green | `tc2_vertical_ellipse.png` |

---

## Visualisation

The program renders:

- A Cartesian reference grid
- Labelled x- and y-axes
- Mid Point Ellipse rasterised pixels as coloured filled circles
- A connected ellipse outline through all plotted points
- Semi-axis guide lines (rx and ry) with labels
- Coordinate annotations for every plotted pixel
- The centre point marked and labelled
- Two separate windows corresponding to the two test cases

The plotted points clearly demonstrate the smooth elliptical approximation produced by the Mid Point Ellipse algorithm using 4-way symmetry and the two-region approach.

---

## Algorithm Summary

```text
INPUT: (xc, yc), rx, ry

x = 0, y = ry
p1 = ry² - rx²·ry + ¼·rx²
dx = 0, dy = 2·rx²·ry

REGION 1 (while dx < dy):
    Plot 4 symmetric points:
        (xc+x, yc+y), (xc-x, yc+y)
        (xc+x, yc-y), (xc-x, yc-y)
    x = x + 1
    dx = dx + 2·ry²
    IF p1 < 0 THEN
        p1 = p1 + dx + ry²
    ELSE
        y = y - 1
        dy = dy - 2·rx²
        p1 = p1 + dx - dy + ry²
    END IF

REGION 2 (while y >= 0):
    p2 = ry²·(x+½)² + rx²·(y-1)² - rx²·ry²
    y = y - 1
    dy = dy - 2·rx²
    IF p2 > 0 THEN
        p2 = p2 + rx² - dy
    ELSE
        x = x + 1
        dx = dx + 2·ry²
        p2 = p2 + dx - dy + rx²
    END IF
    Plot 4 symmetric points
```

---

## Output

Two OpenGL visualisations are produced corresponding to:

- Horizontal ellipse (rx=5, ry=3, centre at (10, 8))
- Vertical ellipse (rx=3, ry=5, centre at (6, 10))

The generated figures included in the `outputs` directory illustrate the rasterised pixel positions forming complete ellipses through 4-way symmetry, demonstrating the efficiency and accuracy of the Mid Point Ellipse algorithm.

---

## GitHub Repository

https://github.com/TheNormalCoderr/computer_graphics_experiments
