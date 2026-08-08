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
4. Starting at `(x1, y1)`, plot `(round(x), round(y))` and increment by `(x_inc, y_inc)` for `steps` iterations.

DDA is simple and easy to implement, but uses floating-point arithmetic for every step.

---

## Shared Dependency Installation

A shared virtual environment is kept at the **repository root** so all experiments can use it.

```bash
# From the repository root
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
pip install Pillow numpy          # needed to save screenshots
```

---

## Run Command

```bash
# From the repository root, with .venv activated
python SimpleDDA/src/simple_dda.py
```

This renders each test case in its own OpenGL window, saves the screenshot, and exits automatically.

---

## Folder Structure

```text
computer_graphics_experiments/
├── .venv/                          ← shared virtual environment (not committed)
├── requirements.txt                ← shared PyOpenGL dependencies
├── .gitignore
├── README.md
└── SimpleDDA/
    ├── src/
    │   └── simple_dda.py           ← DDA implementation + screenshot capture
    ├── outputs/
    │   ├── tc1_positive_slope.png  ← Test Case 1 output
    │   ├── tc2_negative_slope.png  ← Test Case 2 output
    │   └── tc3_vertical_line.png   ← Test Case 3 output
    ├── docs/
    │   └── Simple_DDA_Experiment_Report.docx
    └── README.md
```

---

## Test Cases

| # | Start Point | End Point   | Line Type      | Color | Output File               |
|---|-------------|-------------|----------------|-------|---------------------------|
| 1 | (50, 50)    | (400, 300)  | Positive slope | Red   | `tc1_positive_slope.png`  |
| 2 | (80, 350)   | (420, 120)  | Negative slope | Green | `tc2_negative_slope.png`  |
| 3 | (100, 100)  | (100, 400)  | Vertical line  | Blue  | `tc3_vertical_line.png`   |

---

## Algorithm Summary

```text
INPUT: (x1, y1), (x2, y2)
  dx    = x2 - x1
  dy    = y2 - y1
  steps = max(|dx|, |dy|)
  x_inc = dx / steps
  y_inc = dy / steps
  x, y  = x1, y1

FOR i = 0 TO steps:
    PLOT (round(x), round(y))
    x = x + x_inc
    y = y + y_inc
```

---

## GitHub Repository

[https://github.com/TheNormalCoderr/computer_graphics_experiments](https://github.com/TheNormalCoderr/computer_graphics_experiments)
