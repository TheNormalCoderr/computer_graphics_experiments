# Symmetric DDA Line Drawing Algorithm using OpenGL in Python

**Subject:** Computer Graphics  
**Language:** Python  
**Graphics Library:** PyOpenGL with GLUT/FreeGLUT

---

## What is the Symmetric DDA Algorithm?

The **Symmetric Digital Differential Analyzer (Symmetric DDA)** is a variation of the standard DDA line-drawing algorithm. Instead of choosing `steps = max(|dx|, |dy|)`, it selects the smallest power of two `2^n` that is greater than or equal to `max(|dx|, |dy|)`.

Given endpoints **(x1, y1)** and **(x2, y2)**:

1. Compute `dx = x2 - x1` and `dy = y2 - y1`.
2. Find the smallest `n` such that `2^n >= max(|dx|, |dy|)`. Set `steps = 2^n`.
3. Compute `x_inc = dx / 2^n` and `y_inc = dy / 2^n`.
4. Starting at `(x1, y1)`, plot `(round(x), round(y))` and increment by `(x_inc, y_inc)` for `steps + 1` iterations.
5. Discard any duplicate pixel positions.

Because division by a power of two is equivalent to a binary right-shift, the Symmetric DDA is well suited for hardware implementation. When `2^n > max(|dx|, |dy|)`, some pixel positions are generated more than once and must be deduplicated.

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
python SymmetricDDA/src/symmetric_dda.py
```

The program opens one **OpenGL window per test case** defined in the `TEST_CASES` list inside `symmetric_dda.py`. Each window displays the Symmetric DDA rasterisation with a reference grid, coordinate labels, and coloured plotted pixels.

To add a new test case, simply append a dict to `TEST_CASES` — no other code changes are needed. Colors are generated dynamically.

Press **Esc** or **Q** in any window to exit the program.

---

## Folder Structure

```text
computer_graphics_experiments/
├── .venv/                          ← Shared virtual environment (not committed)
├── requirements.txt                ← Shared project dependencies
├── .gitignore
├── README.md
└── SymmetricDDA/
    ├── src/
    │   └── symmetric_dda.py        ← Symmetric DDA implementation using PyOpenGL
    ├── outputs/
    │   ├── tc1_positive_slope.png
    │   ├── tc2_negative_slope.png
    │   ├── tc3_horizontal_line.png
    │   └── tc4_vertical_line.png
    ├── docs/
    │   ├── generate_report.py
    │   └── Symmetric_DDA_Experiment_Report.docx
    └── README.md
```

---

## Test Cases

| # | Start Point | End Point | Line Type       | Output                     |
|---|-------------|-----------|-----------------|----------------------------|
| 1 | (2, 2)      | (18, 10)  | Positive Slope  | `tc1_positive_slope.png`   |
| 2 | (2, 14)     | (18, 5)   | Negative Slope  | `tc2_negative_slope.png`   |
| 3 | (2, 8)      | (18, 8)   | Horizontal Line | `tc3_horizontal_line.png`  |
| 4 | (10, 2)     | (10, 14)  | Vertical Line   | `tc4_vertical_line.png`    |

> **Adding test cases:** Append a new dict to the `TEST_CASES` list in `symmetric_dda.py` with keys `x1`, `y1`, `x2`, `y2`, `label`, and `file`. The program and report generator will pick it up automatically.

---

## Visualisation

The program renders:

- A Cartesian reference grid
- Labelled x- and y-axes
- Symmetric DDA rasterised pixels as coloured filled circles
- Coordinate annotations for every plotted pixel
- One window per test case (dynamically created)

The plotted points clearly demonstrate the staircase approximation produced by the Symmetric DDA algorithm.

---

## Algorithm Summary

```text
INPUT: (x1, y1), (x2, y2)

dx    = x2 - x1
dy    = y2 - y1

Find smallest n such that 2^n >= max(|dx|, |dy|)
steps = 2^n

x_inc = dx / 2^n
y_inc = dy / 2^n

x = x1
y = y1

FOR i = 0 TO steps
    Plot (round(x), round(y))
    x = x + x_inc
    y = y + y_inc
END FOR

Remove duplicate pixel positions
```

---

## Output

OpenGL visualisations are produced for each test case. The generated figures in the `outputs` directory illustrate the rasterised pixel positions and the characteristic staircase effect. For test cases where `2^n > max(|dx|, |dy|)`, duplicate pixels are discarded, and the final output matches the Simple DDA.

---

## GitHub Repository

https://github.com/TheNormalCoderr/computer_graphics_experiments
