# Bresenham Line Drawing Algorithm using OpenGL in Python

**Subject:** Computer Graphics  
**Language:** Python  
**Graphics Library:** PyOpenGL with GLUT/FreeGLUT

---

## What is the Bresenham Line Algorithm?

The **Bresenham Line Drawing Algorithm** is a scan-conversion algorithm that determines the pixel positions closest to a true line segment using only integer arithmetic. Unlike the DDA algorithms, which rely on floating-point increments and rounding, Bresenham uses a decision parameter updated with integer additions and subtractions at each step.

Given endpoints **(x1, y1)** and **(x2, y2)**:

1. Compute `dx = |x2 - x1|` and `dy = |y2 - y1|`.
2. Determine the dominant axis (x if `dx >= dy`, y otherwise).
3. Initialise the decision parameter: `p = 2*dy - dx` (for x-dominant) or `p = 2*dx - dy` (for y-dominant).
4. At each step along the dominant axis, plot the current pixel and update the decision parameter to decide whether the non-dominant axis also increments.

The algorithm is efficient, uses no floating-point operations, and produces the same rasterised output as the DDA algorithms for the same endpoints.

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
python Brestenham/src/bresenham.py
```

The program opens **three OpenGL windows**, one for each test case. Each window displays the Bresenham rasterisation with a reference grid, coordinate labels, and coloured plotted pixels.

Press **Esc** or **Q** in any window to exit the program.

---

## Folder Structure

```text
computer_graphics_experiments/
├── .venv/                          ← Shared virtual environment (not committed)
├── requirements.txt                ← Shared project dependencies
├── .gitignore
├── README.md
└── Brestenham/
    ├── src/
    │   └── bresenham.py            ← Bresenham implementation using PyOpenGL
    ├── outputs/
    │   ├── tc1_positive_slope.png
    │   ├── tc2_negative_slope.png
    │   └── tc3_steep_line.png
    ├── docs/
    │   ├── generate_report.py
    │   └── Bresenham_Experiment_Report.docx
    └── README.md
```

---

## Test Cases

| # | Start Point | End Point | Line Type | Colour | Output |
|---|-------------|-----------|-----------|--------|--------|
| 1 | (2, 2) | (18, 10) | Positive Slope | Red | `tc1_positive_slope.png` |
| 2 | (2, 14) | (18, 5) | Negative Slope | Green | `tc2_negative_slope.png` |
| 3 | (4, 2) | (8, 14) | Steep Line | Blue | `tc3_steep_line.png` |

---

## Visualisation

The program renders:

- A Cartesian reference grid
- Labelled x- and y-axes
- Bresenham rasterised pixels as coloured filled circles
- Coordinate annotations for every plotted pixel
- Three separate windows corresponding to the three test cases

The plotted points clearly demonstrate the staircase approximation produced by the Bresenham algorithm.

---

## Algorithm Summary

```text
INPUT: (x1, y1), (x2, y2)

dx = |x2 - x1|
dy = |y2 - y1|
sx = sign(x2 - x1)
sy = sign(y2 - y1)

IF dx >= dy THEN            (shallow line — step along x)
    p = 2*dy - dx
    FOR i = 0 TO dx
        Plot (x, y)
        IF p >= 0 THEN
            y = y + sy
            p = p - 2*dx
        END IF
        p = p + 2*dy
        x = x + sx
    END FOR
ELSE                        (steep line — step along y)
    p = 2*dx - dy
    FOR i = 0 TO dy
        Plot (x, y)
        IF p >= 0 THEN
            x = x + sx
            p = p - 2*dy
        END IF
        p = p + 2*dx
        y = y + sy
    END FOR
END IF
```

---

## Output

Three OpenGL visualisations are produced corresponding to:

- Positive slope line
- Negative slope line
- Steep line (|dy| > |dx|)

The generated figures included in the `outputs` directory illustrate the rasterised pixel positions and the characteristic staircase effect of the Bresenham algorithm.

---

## GitHub Repository

https://github.com/TheNormalCoderr/computer_graphics_experiments
