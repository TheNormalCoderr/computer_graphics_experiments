# Simple DDA Line Drawing Algorithm using OpenGL in Python

**Subject:** Computer Graphics  
**Language:** Python  
**Graphics Library:** PyOpenGL with GLUT/FreeGLUT

---

## What is the DDA Algorithm?

The **Digital Differential Analyzer (DDA)** is a scan-conversion line-drawing algorithm that computes intermediate pixel positions along a line using incremental floating-point additions.

Given endpoints **(x1, y1)** and **(x2, y2)**:

1. Compute `dx = x2 - x1` and `dy = y2 - y1`.
2. Choose `steps = max(|dx|, |dy|)` — the larger span determines how many points to plot.
3. Compute `x_inc = dx / steps` and `y_inc = dy / steps`.
4. Starting at `(x1, y1)`, plot `(round(x), round(y))` and increment by `(x_inc, y_inc)` for `steps + 1` iterations.

The DDA algorithm is simple and easy to implement, making it an excellent introductory raster line-drawing algorithm. Since it uses floating-point arithmetic, small rounding errors may accumulate for very long lines.

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
python SimpleDDA/src/simple_dda.py
```

The program opens **three OpenGL windows**, one for each test case. Each window displays the DDA rasterisation with a reference grid, coordinate labels, and coloured plotted pixels.

Press **Esc** or **Q** in any window to exit the program.

---

## Folder Structure

```text
computer_graphics_experiments/
├── .venv/                          ← Shared virtual environment (not committed)
├── requirements.txt                ← Shared project dependencies
├── .gitignore
├── README.md
└── SimpleDDA/
    ├── src/
    │   └── simple_dda.py           ← DDA implementation using PyOpenGL
    ├── outputs/
    │   ├── tc1_positive_slope.png
    │   ├── tc2_negative_slope.png
    │   └── tc3_vertical_line.png
    ├── docs/
    │   └── Simple_DDA_Experiment_Report.docx
    └── README.md
```

---

## Test Cases

| # | Start Point | End Point | Line Type | Colour | Output |
|---|-------------|-----------|-----------|--------|--------|
| 1 | (2, 2) | (18, 10) | Positive Slope | Red | `tc1_positive_slope.png` |
| 2 | (2, 14) | (18, 5) | Negative Slope | Green | `tc2_negative_slope.png` |
| 3 | (10, 2) | (10, 14) | Vertical Line | Blue | `tc3_vertical_line.png` |

---

## Visualisation

The program renders:

- A Cartesian reference grid
- Labelled x- and y-axes
- DDA rasterised pixels as coloured filled circles
- Coordinate annotations for every plotted pixel
- Three separate windows corresponding to the three test cases

The plotted points clearly demonstrate the staircase approximation produced by the DDA algorithm.

---

## Algorithm Summary

```text
INPUT: (x1, y1), (x2, y2)

dx    = x2 - x1
dy    = y2 - y1

steps = max(|dx|, |dy|)

x_inc = dx / steps
y_inc = dy / steps

x = x1
y = y1

FOR i = 0 TO steps
    Plot (round(x), round(y))
    x = x + x_inc
    y = y + y_inc
END FOR
```

---

## Output

Three OpenGL visualisations are produced corresponding to:

- Positive slope line
- Negative slope line
- Vertical line

The generated figures included in the `outputs` directory illustrate the rasterised pixel positions and the characteristic staircase effect of the DDA algorithm.

---

## GitHub Repository

https://github.com/TheNormalCoderr/computer_graphics_experiments