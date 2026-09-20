# 2D Basic Transformations using OpenGL in Python

**Subject:** Computer Graphics  
**Language:** Python  
**Graphics Library:** PyOpenGL with GLUT/FreeGLUT

---

## 1. What are 2D Basic Transformations?

**2D Transformations** are geometric operations that alter the position, size, or orientation of objects in a two-dimensional Cartesian plane. The three fundamental (basic) transformations are:

1. **Translation** — Displaces an object by a vector $(t_x, t_y)$.
2. **Scaling** — Alters the dimensions of an object by scale factors $(s_x, s_y)$ with respect to the origin $(0, 0)$.
3. **Rotation** — Rotates an object through an angle $\theta$ (counter-clockwise) about the origin $(0, 0)$.

### Homogeneous Coordinates Representation

To represent translation, scaling, and rotation uniformly as matrix multiplications, Computer Graphics employs **homogeneous coordinates**. A 2D point $(x, y)$ is represented as a 3D column vector:

$$
\mathbf{P} = \begin{bmatrix} x \\ y \\ 1 \end{bmatrix}
$$

Any 2D affine transformation can then be expressed as a $3 \times 3$ transformation matrix $\mathbf{M}$, and the transformed point $\mathbf{P}' = [x', y', 1]^T$ is computed as:

$$
\mathbf{P}' = \mathbf{M} \cdot \mathbf{P}
$$

---

## 2. Mathematical Formulations & 3×3 Matrices

### 1. Translation Matrix ($t_x, t_y$)
$$
\begin{bmatrix} x' \\ y' \\ 1 \end{bmatrix} =
\begin{bmatrix}
1 & 0 & t_x \\
0 & 1 & t_y \\
0 & 0 & 1
\end{bmatrix}
\begin{bmatrix} x \\ y \\ 1 \end{bmatrix}
\implies
\begin{aligned}
x' &= x + t_x \\
y' &= y + t_y
\end{aligned}
$$

### 2. Scaling Matrix ($s_x, s_y$)
$$
\begin{bmatrix} x' \\ y' \\ 1 \end{bmatrix} =
\begin{bmatrix}
s_x & 0 & 0 \\
0 & s_y & 0 \\
0 & 0 & 1
\end{bmatrix}
\begin{bmatrix} x \\ y \\ 1 \end{bmatrix}
\implies
\begin{aligned}
x' &= x \cdot s_x \\
y' &= y \cdot s_y
\end{aligned}
$$

### 3. Rotation Matrix ($\theta$ counter-clockwise about origin)
$$
\begin{bmatrix} x' \\ y' \\ 1 \end{bmatrix} =
\begin{bmatrix}
\cos\theta & -\sin\theta & 0 \\
\sin\theta & \cos\theta & 0 \\
0 & 0 & 1
\end{bmatrix}
\begin{bmatrix} x \\ y \\ 1 \end{bmatrix}
\implies
\begin{aligned}
x' &= x\cos\theta - y\sin\theta \\
y' &= x\sin\theta + y\cos\theta
\end{aligned}
$$

---

## 3. Shared Dependency Installation

A shared virtual environment is maintained at the repository root:

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
# From the repository root
python BasicTransformations2D/src/basic_transformations.py
```

The program launches **three OpenGL windows**, one for each test case:
1. **Translation**: Square shifted by $(t_x=4, t_y=3)$
2. **Scaling**: Square magnified by factors $(s_x=1.8, s_y=1.5)$
3. **Rotation**: Square rotated by $\theta = 45^\circ$ about the origin

Each window displays both the **original polygon** (blue) and **transformed polygon** (red) on a Cartesian grid with coordinate labels. Renderings are automatically saved to `BasicTransformations2D/outputs/`.

Press **Esc** or **Q** in any window to exit.

---

## 5. Folder Structure

```text
BasicTransformations2D/
├── src/
│   └── basic_transformations.py     ← Core math and OpenGL visualizer
├── outputs/
│   ├── tc1_translation.png          ← Output for translation test case
│   ├── tc2_scaling.png              ← Output for scaling test case
│   └── tc3_rotation.png             ← Output for rotation test case
├── docs/
│   ├── generate_report.py           ← Generates formal Word (.docx) report
│   └── BasicTransformations2D_Experiment_Report.docx
└── README.md
```

---

## 6. Test Cases & Verification

| # | Original Shape | Transformation | Parameters | Matrix Applied | Output Image |
|---|----------------|----------------|------------|----------------|--------------|
| 1 | Square: $(2,2), (5,2), (5,5), (2,5)$ | Translation | $t_x=4, t_y=3$ | $\begin{bmatrix}1&0&4\\0&1&3\\0&0&1\end{bmatrix}$ | `tc1_translation.png` |
| 2 | Square: $(2,2), (5,2), (5,5), (2,5)$ | Scaling | $s_x=1.8, s_y=1.5$ | $\begin{bmatrix}1.8&0&0\\0&1.5&0\\0&0&1\end{bmatrix}$ | `tc2_scaling.png` |
| 3 | Square: $(7,2), (10,2), (10,5), (7,5)$ | Rotation | $\theta=45^\circ$ | $\begin{bmatrix}0.7071&-0.7071&0\\0.7071&0.7071&0\\0&0&1\end{bmatrix}$ | `tc3_rotation.png` |

---

## 7. Generating the Lab Report

To build the complete Word document report:

```bash
python BasicTransformations2D/docs/generate_report.py
```

The output report will be created at `BasicTransformations2D/docs/BasicTransformations2D_Experiment_Report.docx`.
