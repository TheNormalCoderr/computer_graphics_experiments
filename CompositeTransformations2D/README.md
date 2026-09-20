# 2D Composite Transformations using OpenGL in Python

**Subject:** Computer Graphics  
**Language:** Python  
**Graphics Library:** PyOpenGL with GLUT/FreeGLUT

---

## 1. What are Composite Transformations?

A **Composite Transformation** (or concatenated/compound transformation) is a combination of two or more basic geometric transformations (such as translations, rotations, scalings, reflections, or shears) applied in succession to a geometric object.

In computer graphics, applying transformations individually to each vertex of a complex polygon with $N$ vertices would require $k$ separate matrix-vector calculations per vertex (where $k$ is the number of transformation stages), yielding $k \times O(N)$ operations.

By utilizing **homogeneous coordinates**, all transformations are expressed as $3 \times 3$ matrices. Because matrix multiplication is associative, any sequence of transformations can be pre-multiplied into a **single $3 \times 3$ composite matrix**:

$$
\mathbf{M}_{\text{composite}} = \mathbf{M}_k \cdot \mathbf{M}_{k-1} \cdots \mathbf{M}_2 \cdot \mathbf{M}_1
$$

Each vertex $\mathbf{P} = [x, y, 1]^T$ is then transformed in a single matrix-vector multiplication:

$$
\mathbf{P}' = \mathbf{M}_{\text{composite}} \cdot \mathbf{P}
$$

This reduces runtime complexity from $k \times O(N)$ to a single $O(N)$ pass, yielding massive efficiency in graphics pipelines.

> **Important (Non-Commutativity):** Matrix multiplication is non-commutative in general ($\mathbf{A} \cdot \mathbf{B} \neq \mathbf{B} \cdot \mathbf{A}$). The chronological order of transformations is maintained by multiplying new transformation matrices from the **left** of the preceding matrices.

---

## 2. Mathematical Formulations & Derivations

### 1. Rotation About an Arbitrary Pivot Point $(x_p, y_p)$

Standard rotation $R(\theta)$ only rotates an object about the coordinate origin $(0, 0)$. To rotate an object about an arbitrary point $(x_p, y_p)$:

1. **Translate** the pivot point to the origin: $T(-x_p, -y_p)$
2. **Rotate** about the origin by angle $\theta$: $R(\theta)$
3. **Translate** back to original position: $T(x_p, y_p)$

The composite transformation matrix is:

$$
\mathbf{M}_{\text{pivot}} = \mathbf{T}(x_p, y_p) \cdot \mathbf{R}(\theta) \cdot \mathbf{T}(-x_p, -y_p)
$$

$$
\mathbf{M}_{\text{pivot}} =
\begin{bmatrix}
1 & 0 & x_p \\
0 & 1 & y_p \\
0 & 0 & 1
\end{bmatrix}
\begin{bmatrix}
\cos\theta & -\sin\theta & 0 \\
\sin\theta & \cos\theta & 0 \\
0 & 0 & 1
\end{bmatrix}
\begin{bmatrix}
1 & 0 & -x_p \\
0 & 1 & -y_p \\
0 & 0 & 1
\end{bmatrix}
$$

Expanding:
$$
\mathbf{M}_{\text{pivot}} =
\begin{bmatrix}
\cos\theta & -\sin\theta & x_p(1 - \cos\theta) + y_p\sin\theta \\
\sin\theta & \cos\theta & y_p(1 - \cos\theta) - x_p\sin\theta \\
0 & 0 & 1
\end{bmatrix}
$$

---

### 2. Scaling About an Arbitrary Fixed Point $(x_f, y_f)$

Standard scaling alters coordinates relative to the origin, which causes displacement unless the object is centered at $(0, 0)$. To scale about a fixed point $(x_f, y_f)$:

1. **Translate** the fixed point to the origin: $T(-x_f, -y_f)$
2. **Scale** with factors $(s_x, s_y)$: $S(s_x, s_y)$
3. **Translate** back to original position: $T(x_f, y_f)$

The composite transformation matrix is:

$$
\mathbf{M}_{\text{fixed}} = \mathbf{T}(x_f, y_f) \cdot \mathbf{S}(s_x, s_y) \cdot \mathbf{T}(-x_f, -y_f)
$$

$$
\mathbf{M}_{\text{fixed}} =
\begin{bmatrix}
1 & 0 & x_f \\
0 & 1 & y_f \\
0 & 0 & 1
\end{bmatrix}
\begin{bmatrix}
s_x & 0 & 0 \\
0 & s_y & 0 \\
0 & 0 & 1
\end{bmatrix}
\begin{bmatrix}
1 & 0 & -x_f \\
0 & 1 & -y_f \\
0 & 0 & 1
\end{bmatrix}
=
\begin{bmatrix}
s_x & 0 & x_f(1 - s_x) \\
0 & s_y & y_f(1 - s_y) \\
0 & 0 & 1
\end{bmatrix}
$$

---

### 3. Reflection About an Arbitrary Axis Line

To reflect an object across an arbitrary line passing through $(x_1, y_1)$ and $(x_2, y_2)$ with inclination angle $\theta = \text{atan2}(y_2 - y_1, x_2 - x_1)$:

1. **Translate** the line so $(x_1, y_1)$ passes through origin: $T(-x_1, -y_1)$
2. **Rotate** clockwise by $-\theta$ so the axis line aligns with the X-axis: $R(-\theta)$
3. **Reflect** across the X-axis: $\mathbf{Ref}_x = \begin{bmatrix} 1 & 0 & 0 \\ 0 & -1 & 0 \\ 0 & 0 & 1 \end{bmatrix}$
4. **Rotate** counter-clockwise by $+\theta$ to restore orientation: $R(\theta)$
5. **Translate** back to original location: $T(x_1, y_1)$

The composite matrix is:

$$
\mathbf{M}_{\text{reflect\_axis}} = \mathbf{T}(x_1, y_1) \cdot \mathbf{R}(\theta) \cdot \mathbf{Ref}_x \cdot \mathbf{R}(-\theta) \cdot \mathbf{T}(-x_1, -y_1)
$$

---

### 4. Scaling Along an Arbitrary Axis Direction

To scale an object by factor $s_{\parallel}$ along an arbitrary axis line (passing through $(x_1, y_1)$ and $(x_2, y_2)$ with inclination $\theta$) and by factor $s_{\perp}$ perpendicular to it:

1. **Translate** so $(x_1, y_1)$ is at the origin: $T(-x_1, -y_1)$
2. **Rotate** by $-\theta$ so the axis aligns with the X-axis: $R(-\theta)$
3. **Scale** by $(s_{\parallel}, s_{\perp})$: $S(s_{\parallel}, s_{\perp})$
4. **Rotate** back by $+\theta$: $R(\theta)$
5. **Translate** back: $T(x_1, y_1)$

$$
\mathbf{M}_{\text{scale\_axis}} = \mathbf{T}(x_1, y_1) \cdot \mathbf{R}(\theta) \cdot \mathbf{S}(s_{\parallel}, s_{\perp}) \cdot \mathbf{R}(-\theta) \cdot \mathbf{T}(-x_1, -y_1)
$$

---

### 5. General Multi-Step Sequence (Translation $\to$ Rotation $\to$ Scaling)

When an object undergoes a multi-step sequence of transformations (first Translation $T(t_x, t_y)$, then Rotation $R(\theta)$, then Scaling $S(s_x, s_y)$):

$$
\mathbf{P}' = \mathbf{S}(s_x, s_y) \cdot \mathbf{R}(\theta) \cdot \mathbf{T}(t_x, t_y) \cdot \mathbf{P}
$$

---

## 3. Shared Dependency Installation

```bash
# From repository root
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

---

## 4. Running the Program

```bash
# Interactive OpenGL visualizer
python CompositeTransformations2D/src/composite_transformations.py

# Headless batch generation of outputs
python CompositeTransformations2D/src/composite_transformations.py --headless
```

The program opens **five OpenGL windows**, one for each test case:
1. **Rotation About Pivot Point**: Square rotated by $45^\circ$ about pivot $(5, 5)$
2. **Scaling About Fixed Point**: Triangle scaled by $(1.6, 1.6)$ about fixed point $(3, 3)$
3. **Reflection About Arbitrary Axis**: Triangle reflected across the line from $(1, 2)$ to $(13, 11)$
4. **Scaling Along Arbitrary Axis**: Square scaled along a $45^\circ$ axis direction
5. **General Composite Sequence**: Square translated by $(2, 1)$, rotated $30^\circ$ about pivot $(6, 5)$, then scaled by $(1.2, 1.2)$

Each window displays:
- Reference Cartesian grid with coordinate labels
- Original polygon in **blue**
- Transformed polygon in **red**
- Pivot point or reflection axis in **green**
- Legend and descriptive header

Press **Esc** or **Q** to exit.

---

## 5. Folder Structure

```text
CompositeTransformations2D/
├── src/
│   └── composite_transformations.py     ← Composite math and OpenGL visualizer
├── outputs/
│   ├── tc1_rotation_about_point.png     ← Output for pivot rotation
│   ├── tc2_scaling_about_point.png      ← Output for fixed-point scaling
│   ├── tc3_reflection_about_axis.png    ← Output for arbitrary axis reflection
│   ├── tc4_scaling_along_axis.png       ← Output for scaling along arbitrary axis
│   └── tc5_composite_sequence.png       ← Output for general composite sequence
├── docs/
│   ├── generate_report.py               ← Generates formal Word (.docx) report
│   └── CompositeTransformations2D_Experiment_Report.docx
└── README.md
```

---

## 6. Test Cases & Verification

| # | Transformation Type | Original Shape | Parameters | Matrix Applied | Output Image |
|---|---------------------|----------------|------------|----------------|--------------|
| 1 | Rotation About Pivot Point | Square: $(3,3), (7,3), (7,7), (3,7)$ | Pivot $(5, 5)$, $\theta = 45^\circ$ | $T(5,5) \cdot R(45^\circ) \cdot T(-5,-5)$ | `tc1_rotation_about_point.png` |
| 2 | Scaling About Fixed Point | Triangle: $(3,3), (7,3), (5,6)$ | Fixed $(3, 3)$, $s_x=1.6, s_y=1.6$ | $T(3,3) \cdot S(1.6,1.6) \cdot T(-3,-3)$ | `tc2_scaling_about_point.png` |
| 3 | Reflection Across Arbitrary Axis | Triangle: $(3,6), (7,8), (5,10)$ | Axis from $(1, 2)$ to $(13, 11)$ | $T \cdot R \cdot Ref_x \cdot R^{-1} \cdot T^{-1}$ | `tc3_reflection_about_axis.png` |
| 4 | Scaling Along Arbitrary Axis | Square: $(4,4), (7,4), (7,7), (4,7)$ | Axis from $(2,2)$ to $(12,12)$, $s_{\parallel}=1.8, s_{\perp}=0.8$ | $T \cdot R \cdot S \cdot R^{-1} \cdot T^{-1}$ | `tc4_scaling_along_axis.png` |
| 5 | Multi-Step Composite Sequence | Square: $(2,2), (5,2), (5,5), (2,5)$ | $T(2, 1) \to R(30^\circ)$ about $(6,5)$ $\to S(1.2, 1.2)$ | $S(1.2, 1.2) \cdot M_{pivot} \cdot T(2, 1)$ | `tc5_composite_sequence.png` |

---

## 7. Generating the Lab Report

To build the complete Word document report:

```bash
python CompositeTransformations2D/docs/generate_report.py
```

The report will be created at `CompositeTransformations2D/docs/CompositeTransformations2D_Experiment_Report.docx`.
