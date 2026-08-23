# Mid Point Circle Drawing Algorithm using OpenGL in Python

**Subject:** Computer Graphics  
**Language:** Python  
**Graphics Library:** PyOpenGL with GLUT/FreeGLUT

---

## What is the Mid Point Circle Algorithm?

The **Mid Point Circle Drawing Algorithm** is a scan-conversion algorithm that determines the pixel positions closest to a true circle using only integer arithmetic. It exploits the **8-way symmetry** of a circle to compute points for only one octant and then mirrors them to produce the complete circumference.

Given a centre **(xc, yc)** and radius **r**:

1. Start at the point `(0, r)` — the top of the first octant.
2. Initialise the decision parameter: `p = 1 − r`.
3. At each step, if `p < 0`, move to `(x+1, y)` and update `p = p + 2x + 1`; if `p ≥ 0`, move to `(x+1, y−1)` and update `p = p + 2(x − y) + 1`.
4. Apply 8-way symmetry at each step to plot all 8 corresponding points.
5. Repeat while `x ≤ y`.

The algorithm is efficient, uses no floating-point operations, and produces a smooth, complete circle from discrete pixel positions.

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
python MidPointCircle/src/midpoint_circle.py --standalone
```

The program opens **three OpenGL windows**, one for each test case. Each window displays the Mid Point Circle rasterisation with a reference grid, coordinate labels, coloured plotted pixels, and a connected circle outline. Output images are auto-saved to `MidPointCircle/outputs/`.

### Using the Shared App

```bash
# From the repository root
python MidPointCircle/src/midpoint_circle.py
```

This launches the shared drawing application with the Mid Point Circle algorithm pre-selected. Click a point on the canvas to set the centre, then click a second point to define the radius.

Press **Esc** or **Q** in any window to exit the program.

---

## Folder Structure

```text
computer_graphics_experiments/
├── .venv/                          ← Shared virtual environment (not committed)
├── requirements.txt                ← Shared project dependencies
├── .gitignore
├── README.md
└── MidPointCircle/
    ├── src/
    │   └── midpoint_circle.py      ← Mid Point Circle implementation using PyOpenGL
    ├── outputs/
    │   ├── tc1_standard_circle.png
    │   ├── tc2_medium_circle.png
    │   └── tc3_small_circle.png
    ├── docs/
    │   ├── generate_report.py
    │   └── MidPointCircle_Experiment_Report.docx
    └── README.md
```

---

## Test Cases

| # | Centre | Radius | Circle Type | Colour | Output |
|---|--------|--------|-------------|--------|--------|
| 1 | (10, 8) | 5 | Standard Circle | Red | `tc1_standard_circle.png` |
| 2 | (6, 10) | 4 | Medium Circle | Green | `tc2_medium_circle.png` |
| 3 | (14, 6) | 3 | Small Circle | Blue | `tc3_small_circle.png` |

---

## Visualisation

The program renders:

- A Cartesian reference grid
- Labelled x- and y-axes
- Mid Point Circle rasterised pixels as coloured filled circles
- A connected circle outline through all plotted points (complete circle, not zig-zag)
- Coordinate annotations for every plotted pixel
- The centre point marked and labelled
- Three separate windows corresponding to the three test cases

The plotted points clearly demonstrate the smooth circular approximation produced by the Mid Point Circle algorithm using 8-way symmetry.

---

## Algorithm Summary

```text
INPUT: (xc, yc), r

x = 0
y = r
p = 1 - r

REPEAT
    Plot 8 symmetric points:
        (xc+x, yc+y), (xc-x, yc+y)
        (xc+x, yc-y), (xc-x, yc-y)
        (xc+y, yc+x), (xc-y, yc+x)
        (xc+y, yc-x), (xc-y, yc-x)

    x = x + 1

    IF p < 0 THEN
        p = p + 2*x + 1
    ELSE
        y = y - 1
        p = p + 2*(x - y) + 1
    END IF
UNTIL x > y
```

---

## Output

Three OpenGL visualisations are produced corresponding to:

- Standard circle (radius 5, centre at (10, 8))
- Medium circle (radius 4, centre at (6, 10))
- Small circle (radius 3, centre at (14, 6))

The generated figures included in the `outputs` directory illustrate the rasterised pixel positions forming complete circles through 8-way symmetry, demonstrating the efficiency and accuracy of the Mid Point Circle algorithm.

---

## GitHub Repository

https://github.com/TheNormalCoderr/computer_graphics_experiments
