"""
generate_report.py — build CompositeTransformations2D_Experiment_Report.docx
Run from repo root with venv active:
  python CompositeTransformations2D/docs/generate_report.py
"""

import os
import sys
import math

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUTPUT_DIR = os.path.join(REPO_ROOT, "CompositeTransformations2D", "outputs")
DOCS_DIR   = os.path.join(REPO_ROOT, "CompositeTransformations2D", "docs")
DOCX_OUT   = os.path.join(DOCS_DIR, "CompositeTransformations2D_Experiment_Report.docx")

SRC_DIR = os.path.join(REPO_ROOT, "CompositeTransformations2D", "src")
sys.path.insert(0, SRC_DIR)
from composite_transformations import (  # type:ignore
    TEST_CASES, apply_composite_transformation, format_matrix,
)


def main():
    try:
        from docx import Document  # type:ignore
        from docx.shared import Pt, Inches, RGBColor  # type:ignore
        from docx.enum.text import WD_ALIGN_PARAGRAPH  # type:ignore
    except ImportError:
        print("ERROR: python-docx not installed. Run: pip install python-docx")
        sys.exit(1)

    doc = Document()

    # 1 inch margins
    for section in doc.sections:
        section.top_margin    = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin   = Inches(1)
        section.right_margin  = Inches(1)

    def section_label(label):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after  = Pt(4)
        r = p.add_run(label)
        r.font.name = "Times New Roman"
        r.font.size = Pt(13)
        r.font.bold = True
        return p

    def sub_label(label):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after  = Pt(2)
        r = p.add_run(label)
        r.font.name = "Times New Roman"
        r.font.size = Pt(12)
        r.font.bold = True
        return p

    def body(text, size=11, space_before=0, space_after=6):
        p = doc.add_paragraph(text)
        p.paragraph_format.space_before = Pt(space_before)
        p.paragraph_format.space_after  = Pt(space_after)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        for run in p.runs:
            run.font.name = "Times New Roman"
            run.font.size = Pt(size)
        return p

    def bullet(text, level=0):
        p = doc.add_paragraph(style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(11)
        return p

    def caption(text):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after  = Pt(10)
        r = p.add_run(text)
        r.font.name   = "Times New Roman"
        r.font.size   = Pt(10)
        r.font.italic = True
        return p

    def add_image(path, width=Inches(5.0)):
        if not os.path.exists(path):
            print(f"[Warning] Image not found: {path}")
            return None
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after  = Pt(2)
        run = p.add_run()
        run.add_picture(path, width=width)
        return p

    def add_table(headers, rows):
        t = doc.add_table(rows=1 + len(rows), cols=len(headers))
        t.style = "Table Grid"
        t.alignment = WD_ALIGN_PARAGRAPH.CENTER
        hrow = t.rows[0]
        for i, h in enumerate(headers):
            cell = hrow.cells[i]
            cell.text = h
            cell.paragraphs[0].runs[0].font.bold = True
            cell.paragraphs[0].runs[0].font.name = "Times New Roman"
            cell.paragraphs[0].runs[0].font.size = Pt(10)
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        for ri, row in enumerate(rows):
            drow = t.rows[ri + 1]
            for ci, val in enumerate(row):
                cell = drow.cells[ci]
                cell.text = str(val)
                cell.paragraphs[0].runs[0].font.name = "Times New Roman"
                cell.paragraphs[0].runs[0].font.size = Pt(10)
                cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        return t

    # ══════════════════════════════════════════════════════════════════════
    # 1. Centered experiment number & title
    # ══════════════════════════════════════════════════════════════════════
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Experiment 7")
    r.font.name = "Times New Roman"; r.font.size = Pt(14); r.font.bold = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(14)
    r = p.add_run("Implementation of 2D Composite Transformations using OpenGL in Python")
    r.font.name = "Times New Roman"; r.font.size = Pt(14); r.font.bold = True

    # ══════════════════════════════════════════════════════════════════════
    # 2. Aim
    # ══════════════════════════════════════════════════════════════════════
    section_label("Aim:")
    body(
        "To implement 2D composite (concatenated) geometric transformations in Python using 3x3 homogeneous "
        "coordinate matrices and PyOpenGL, specifically evaluating rotation about an arbitrary pivot point, "
        "scaling about an arbitrary fixed point, reflection across an arbitrary axis, and multi-step composite "
        "transformation sequences."
    )

    # ══════════════════════════════════════════════════════════════════════
    # 3. Problem Statement
    # ══════════════════════════════════════════════════════════════════════
    section_label("Problem Statement:")
    body(
        "Standard basic transformations operate exclusively relative to the coordinate origin (0, 0). "
        "In practical computer graphics applications, objects must be rotated about custom pivot points, "
        "scaled relative to arbitrary fixed points, or reflected across arbitrary lines. Applying each transformation "
        "sequentially to every vertex requires k x O(N) operations. The goal is to formulate and pre-multiply "
        "the sequence of elementary transformation matrices into a single 3x3 composite matrix M_composite, "
        "then apply M_composite to all vertices in a single pass O(N) while rendering both original and transformed "
        "shapes alongside reference markers."
    )
    sub_label("Input / Setup:")
    body(
        "Polygon vertices; parameters for arbitrary pivot point (xp, yp) and angle θ; parameters for fixed point (xf, yf) "
        "and scale factors (sx, sy); two endpoints (x1, y1) and (x2, y2) defining an arbitrary reflection axis; "
        "or parameters for a multi-step sequence."
    )
    sub_label("Process / Constraint:")
    body(
        "Compute composite matrix M = M_k · ... · M_1 using matrix multiplication in correct associative order; "
        "transform vertices [x', y', 1]^T = M · [x, y, 1]^T; render original shape (blue), transformed shape (red), "
        "and pivot or reflection axis (green)."
    )
    sub_label("Output:")
    body("Comparison graphics with labeled vertices, axes, pivot markers, and saved high-resolution PNG outputs.")

    # ══════════════════════════════════════════════════════════════════════
    # 4. Theory
    # ══════════════════════════════════════════════════════════════════════
    section_label("Theory:")
    body(
        "A composite transformation is formed by combining multiple elementary affine transformations. "
        "By representing transformations in 3x3 homogeneous coordinates, matrix concatenation is possible. "
        "Because matrix multiplication is associative but non-commutative, the chronological order of operations "
        "is preserved by pre-multiplying newer matrices from the left:"
    )
    body("   M_composite = M_n · ... · M_2 · M_1")
    body("Key composite transformations derived in this experiment include:")
    bullet("Rotation About Arbitrary Pivot (xp, yp): Translate pivot to origin T(-xp, -yp), rotate by θ R(θ), then translate back T(xp, yp): M = T(xp, yp) · R(θ) · T(-xp, -yp).")
    bullet("Scaling About Fixed Point (xf, yf): Translate fixed point to origin T(-xf, -yf), scale by (sx, sy) S(sx, sy), then translate back T(xf, yf): M = T(xf, yf) · S(sx, sy) · T(-xf, -yf).")
    bullet("Reflection Across Arbitrary Axis (x1, y1) to (x2, y2): Translate axis to origin T(-x1, -y1), rotate by -θ to align with X-axis R(-θ), reflect across X-axis Ref_x, invert rotation R(θ), invert translation T(x1, y1): M = T(x1, y1) · R(θ) · Ref_x · R(-θ) · T(-x1, -y1).")
    bullet("Multi-step Composite Sequence: Direct concatenation of translation, rotation, and scaling: M = S · R · T.")

    # ══════════════════════════════════════════════════════════════════════
    # 5. Algorithm / Methodology
    # ══════════════════════════════════════════════════════════════════════
    section_label("Algorithm / Methodology:")
    body("1. Define the input polygon vertices V = {(x1, y1), ..., (xn, yn)}.")
    body("2. Identify the required sequence of elementary transformations and their parameters.")
    body("3. For each elementary step, generate the corresponding 3x3 homogeneous matrix (T, R, S, or Ref).")
    body("4. Compute the net composite matrix M by multiplying the transformation matrices in sequential order.")
    body("5. For each vertex (x, y) in V, compute [x', y', 1]^T = M · [x, y, 1]^T.")
    body("6. Display the original shape (blue), transformed shape (red), pivot/axis indicators (green), and coordinate labels on the OpenGL canvas.")

    # ══════════════════════════════════════════════════════════════════════
    # 6. Implementation & Test Cases
    # ══════════════════════════════════════════════════════════════════════
    section_label("Implementation & Test Cases:")

    tc_table_headers = ["Test Case", "Type", "Original Vertices", "Parameters", "Transformed Vertices"]
    tc_table_rows = []

    for tc in TEST_CASES:
        transformed, M = apply_composite_transformation(tc["vertices"], tc["type"], tc["params"])
        t_rounded = [(round(x, 2), round(y, 2)) for x, y in transformed]
        param_str = ", ".join(f"{k}={v}" for k, v in tc["params"].items())
        tc_table_rows.append([
            tc["label"].split("—")[0].strip(),
            tc["type"],
            str(tc["vertices"]),
            param_str,
            str(t_rounded),
        ])

    add_table(tc_table_headers, tc_table_rows)
    caption("Table 7.1: Test Cases for 2D Composite Transformations")

    for tc in TEST_CASES:
        sub_label(tc["label"])
        img_path = os.path.join(OUTPUT_DIR, tc["file"])
        add_image(img_path, width=Inches(5.5))
        caption(f"Visual result for {tc['label']}")

    # ══════════════════════════════════════════════════════════════════════
    # 7. Result
    # ══════════════════════════════════════════════════════════════════════
    section_label("Result:")
    body(
        "All five composite transformation test cases (pivot point rotation, fixed-point scaling, arbitrary axis reflection, "
        "arbitrary-axis scaling, and general multi-stage sequence) were successfully evaluated and rendered. The pre-multiplied composite matrices "
        "produced mathematically exact transformed coordinates, confirmed by visual alignment with reference pivot points and axis lines."
    )

    # ══════════════════════════════════════════════════════════════════════
    # 8. Conclusion
    # ══════════════════════════════════════════════════════════════════════
    section_label("Conclusion:")
    body(
        "Matrix concatenation via 3x3 homogeneous coordinates drastically enhances computational efficiency in 2D computer graphics. "
        "Complex spatial manipulations such as arbitrary-axis reflections and arbitrary-pivot rotations can be reduced to a single "
        "matrix multiplication per vertex, proving the indispensability of homogeneous matrix formulations."
    )

    # ══════════════════════════════════════════════════════════════════════
    # 9. Source Code and Analysis (GitHub)
    # ══════════════════════════════════════════════════════════════════════
    section_label("Source Code and Analysis (GitHub):")
    body("https://github.com/TheNormalCoderr/computer_graphics_experiments")

    os.makedirs(DOCS_DIR, exist_ok=True)
    doc.save(DOCX_OUT)
    print(f"[Success] Report generated: {DOCX_OUT}")


if __name__ == "__main__":
    main()
