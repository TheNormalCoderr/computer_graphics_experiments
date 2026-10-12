"""
generate_report.py — build PointClipping_Experiment_Report.docx
Run from repo root with venv active:
  python PointClipping/docs/generate_report.py
"""

import os
import sys

# ── Paths ────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
OUTPUT_DIR = os.path.join(REPO_ROOT, "PointClipping", "outputs")
DOCS_DIR   = os.path.join(REPO_ROOT, "PointClipping", "docs")
DOCX_OUT   = os.path.join(DOCS_DIR, "PointClipping_Experiment_Report.docx")

SRC_DIR = os.path.join(REPO_ROOT, "PointClipping", "src")
sys.path.insert(0, SRC_DIR)
import point_clipping as pc


def main():
    try:
        from docx import Document
        from docx.shared import Pt, Inches, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
    except ImportError:
        print("ERROR: python-docx not installed. Run: pip install python-docx")
        sys.exit(1)

    doc = Document()

    # Page margins: 1 inch on all sides
    for section in doc.sections:
        section.top_margin    = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin   = Inches(1)
        section.right_margin  = Inches(1)

    # ── Formatting Helpers ───────────────────────────────────────────────────

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

    def bullet(text):
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

    def code_block(text):
        table = doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.cell(0, 0)
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), "F4F4F4")
        tcPr.append(shd)

        borders = OxmlElement("w:tcBorders")
        for b_name in ("top", "left", "bottom", "right"):
            b = OxmlElement(f"w:{b_name}")
            b.set(qn("w:val"), "single")
            b.set(qn("w:sz"), "4")
            b.set(qn("w:space"), "0")
            b.set(qn("w:color"), "CCCCCC")
            borders.append(b)
        tcPr.append(borders)

        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after  = Pt(4)
        r = p.add_run(text)
        r.font.name = "Courier New"
        r.font.size = Pt(9.5)
        return table

    def add_table(headers, rows, col_widths=None, alignments=None, font_size=9.5):
        table = doc.add_table(rows=len(rows) + 1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr_cells = table.rows[0].cells
        for i, header_text in enumerate(headers):
            hdr_cells[i].text = header_text
            p = hdr_cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after  = Pt(4)
            r = p.runs[0]
            r.font.name = "Times New Roman"
            r.font.size = Pt(10)
            r.font.bold = True
            tcPr = hdr_cells[i]._tc.get_or_add_tcPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), "E8E8E8")
            tcPr.append(shd)

        for row_idx, row_data in enumerate(rows):
            row_cells = table.rows[row_idx + 1].cells
            for col_idx, cell_value in enumerate(row_data):
                row_cells[col_idx].text = str(cell_value)
                p = row_cells[col_idx].paragraphs[0]
                p.paragraph_format.space_before = Pt(3)
                p.paragraph_format.space_after  = Pt(3)
                r = p.runs[0]
                r.font.name = "Times New Roman"
                r.font.size = Pt(font_size)
                if alignments and col_idx < len(alignments):
                    p.alignment = alignments[col_idx]
                elif col_idx in (0, 1):
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

        for row in table.rows:
            for col_idx, cell in enumerate(row.cells):
                if col_widths and col_idx < len(col_widths):
                    cell.width = col_widths[col_idx]
                tcPr = cell._tc.get_or_add_tcPr()
                borders = OxmlElement("w:tcBorders")
                for b_name in ("top", "left", "bottom", "right"):
                    b = OxmlElement(f"w:{b_name}")
                    b.set(qn("w:val"), "single")
                    b.set(qn("w:sz"), "4")
                    b.set(qn("w:space"), "0")
                    b.set(qn("w:color"), "CCCCCC")
                    borders.append(b)
                tcPr.append(borders)
        return table

    def add_image(image_path, width=Inches(5.5)):
        if os.path.isfile(image_path):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after  = Pt(2)
            run = p.add_run()
            run.add_picture(image_path, width=width)
        else:
            p = doc.add_paragraph(f"[Image not found: {os.path.basename(image_path)}]")
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # ══════════════════════════════════════════════════════════════════════
    # 1. Centered experiment number & title
    # ══════════════════════════════════════════════════════════════════════
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Experiment No: 11")
    r.font.name = "Times New Roman"
    r.font.size = Pt(14)
    r.font.bold = True

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after  = Pt(14)
    r = p.add_run("Implementation of Point Clipping Algorithm using OpenGL in Python")
    r.font.name = "Times New Roman"
    r.font.size = Pt(14)
    r.font.bold = True

    # ══════════════════════════════════════════════════════════════════════
    # 2. Aim
    # ══════════════════════════════════════════════════════════════════════
    section_label("Aim:")
    body(
        "To implement and analyze the 2D Point Clipping algorithm in Python using OpenGL, "
        "and to evaluate the visibility of arbitrary 2D points against a defined rectangular "
        "clipping window across interior, exterior, mixed, and boundary test cases."
    )

    # ══════════════════════════════════════════════════════════════════════
    # 3. Problem Statement
    # ══════════════════════════════════════════════════════════════════════
    section_label("Problem Statement:")

    sub_label("Input / Setup:")
    body(
        "A 2D rectangular clipping window defined by lower-left corner (Xmin, Ymin) = (100, 100) "
        "and upper-right corner (Xmax, Ymax) = (400, 300) on a 500 x 400 orthographic display canvas, "
        "together with an arbitrary set of input points P(x, y)."
    )

    sub_label("Process / Constraint:")
    body(
        "For each point P(x, y), determine whether it lies within or on the boundaries of the clipping window "
        "by verifying the four standard boundary inequalities: Xmin <= x <= Xmax and Ymin <= y <= Ymax. "
        "Points satisfying all four conditions are accepted and retained for display; points failing any "
        "condition are rejected and discarded from the active rendering window."
    )

    sub_label("Output:")
    body(
        "A visual OpenGL window showing the rectangular clipping perimeter, with accepted points plotted in "
        "green, rejected points plotted in red, point coordinate annotations, and terminal diagnostic verification."
    )

    # ══════════════════════════════════════════════════════════════════════
    # 4. Theory
    # ══════════════════════════════════════════════════════════════════════
    section_label("Theory:")
    body(
        "Clipping is an essential procedure in computer graphics that extracts the visible portion of a scene "
        "relative to a defined display region (the clipping window) and discards geometry falling outside this region. "
        "This prevents redundant rasterization calculations and avoids rendering outside designated screen viewports."
    )

    sub_label("1. Mathematical Basis of Point Clipping:")
    body(
        "A point P(x, y) in a 2D Cartesian plane is accepted (visible) if and only if it satisfies the following "
        "four boundary inequalities simultaneously:"
    )
    bullet("x >= Xmin   (point lies to the right of or on the left clipping boundary)")
    bullet("x <= Xmax   (point lies to the left of or on the right clipping boundary)")
    bullet("y >= Ymin   (point lies above or on the bottom clipping boundary)")
    bullet("y <= Ymax   (point lies below or on the top clipping boundary)")

    body(
        "Combining these conditions gives the compound logical inequality:",
        space_before=4,
    )
    bullet("Xmin <= x <= Xmax   AND   Ymin <= y <= Ymax")

    sub_label("2. Boundary and Corner Evaluation:")
    body(
        "Because the clipping boundary lines are inclusive (using <= and >=), points that lie exactly on the "
        "edges or at the corner vertices of the clipping window are considered inside and are accepted. "
        "Points located even one coordinate unit beyond the boundary fail the inequality check and are rejected."
    )

    sub_label("3. Computational Efficiency:")
    body(
        "Point clipping requires at most four simple numerical comparisons per point: two for the x-axis and "
        "two for the y-axis. The time complexity per point is O(1), and processing a list of N points takes O(N) "
        "total time. It serves as the baseline test for more sophisticated primitives, such as line and polygon clipping."
    )

    # ══════════════════════════════════════════════════════════════════════
    # 5. Working Example / Visualizing the Process
    # ══════════════════════════════════════════════════════════════════════
    section_label("Working Example / Visualizing the Process:")
    body(
        "Consider the clipping window with Xmin = 100, Ymin = 100, Xmax = 400, Ymax = 300, and the five test points "
        "from Test Case 3 (Mixed Distribution). Each point is tested against the four individual boundary conditions:"
    )

    trace_headers = [
        "Point P(x, y)",
        "x >= 100",
        "x <= 400",
        "y >= 100",
        "y <= 300",
        "Combined Result",
        "Visual Status",
    ]
    trace_rows = [
        ["(60, 150)",   "False (60 < 100)", "True",  "True",  "True",  "False", "REJECTED (Red)"],
        ["(200, 150)",  "True",             "True",  "True",  "True",  "True",  "ACCEPTED (Green)"],
        ["(300, 250)",  "True",             "True",  "True",  "True",  "True",  "ACCEPTED (Green)"],
        ["(450, 200)",  "True",  "False (450 > 400)", "True",  "True",  "False", "REJECTED (Red)"],
        ["(250, 50)",   "True",             "True",  "False (50 < 100)", "True", "False", "REJECTED (Red)"],
    ]
    add_table(trace_headers, trace_rows)
    caption("Table 11.1: Detailed inequality evaluation for Test Case 3 (Mixed Distribution)")

    # ══════════════════════════════════════════════════════════════════════
    # 6. Algorithm / Methodology
    # ══════════════════════════════════════════════════════════════════════
    section_label("Algorithm / Methodology:")
    body("The complete point clipping process follows six straightforward steps:")

    bullet("1. Initialize Clipping Window: Define boundaries Xmin, Ymin, Xmax, and Ymax.")
    bullet("2. Read Input Points: Obtain the coordinate pair (x, y) for each candidate point.")
    bullet("3. Horizontal Check: Verify whether x satisfies Xmin <= x <= Xmax. If false, flag point as REJECTED.")
    bullet("4. Vertical Check: Verify whether y satisfies Ymin <= y <= Ymax. If false, flag point as REJECTED.")
    bullet("5. Classification: If both horizontal and vertical checks succeed, flag point as ACCEPTED.")
    bullet("6. Render and Feedback: Display the clipping window, plot accepted points in green, plot rejected points in red, and print diagnostic decisions to the console.")

    # ══════════════════════════════════════════════════════════════════════
    # 7. Implementation
    # ══════════════════════════════════════════════════════════════════════
    section_label("Implementation:")
    body(
        "The core clipping decision function and OpenGL rendering routine from point_clipping.py are shown below:"
    )

    code_snippet = (
        "# clipping window boundaries\n"
        "XMIN, YMIN = 100, 100\n"
        "XMAX, YMAX = 400, 300\n"
        "\n"
        "def clip_point(x, y):\n"
        "    # point is saved if it lies inside or right on the boundary\n"
        "    return XMIN <= x <= XMAX and YMIN <= y <= YMAX\n"
        "\n"
        "def draw_points():\n"
        "    glPointSize(8)\n"
        "    for x, y in points:\n"
        "        if clip_point(x, y):\n"
        "            glColor3f(0.15, 0.7, 0.2)   # green for accepted point\n"
        "        else:\n"
        "            glColor3f(0.85, 0.15, 0.15) # red for rejected point\n"
        "        glBegin(GL_POINTS)\n"
        "        glVertex2f(x, y)\n"
        "        glEnd()\n"
        "        # small offset so labels don't overlap points or borders\n"
        "        tx = x - 50 if (x < XMIN or x >= XMAX) else x + 6\n"
        "        ty = y + 8 if y > YMAX else (y - 14 if y == YMAX else y + 6)\n"
        "        draw_text(tx, ty, f'({x},{y})')"
    )
    code_block(code_snippet)

    # ══════════════════════════════════════════════════════════════════════
    # 8. Test Cases
    # ══════════════════════════════════════════════════════════════════════
    section_label("Test Cases:")
    body(
        "Four comprehensive test cases were designed to evaluate all possible spatial relationships between "
        "points and the clipping window:"
    )

    tc_table_headers = [
        "Test Case",
        "Description",
        "Total Points",
        "Accepted (Green)",
        "Rejected (Red)",
        "Validation Status",
    ]
    tc_table_rows = [
        ["TC1", "All points positioned strictly inside window", "4", "4", "0", "Pass"],
        ["TC2", "All points positioned outside in exterior regions", "5", "0", "5", "Pass"],
        ["TC3", "Mixed points distributed inside and outside", "5", "2", "3", "Pass"],
        ["TC4", "Points located on window edges, corners, and 1 px outside", "8", "6", "2", "Pass"],
    ]
    add_table(tc_table_headers, tc_table_rows)
    caption("Table 11.2: Summary of Point Clipping Benchmark Test Cases")

    # ══════════════════════════════════════════════════════════════════════
    # 9. Test Case Screenshots
    # ══════════════════════════════════════════════════════════════════════

    # TC1
    sub_label("TC1 — All Points Inside:")
    body(
        "Points: (150, 150), (250, 200), (350, 250), (200, 280). "
        "All four points satisfy 100 <= x <= 400 and 100 <= y <= 300, rendering in green."
    )
    add_image(os.path.join(OUTPUT_DIR, "tc1_all_inside.png"))
    caption("Figure 11.1: TC1 — All test points lie strictly inside the clipping window (4 accepted, 0 rejected).")

    # TC2
    sub_label("TC2 — All Points Outside:")
    body(
        "Points: (50, 50), (450, 350), (250, 350), (50, 200), (250, 50). "
        "All five points violate at least one boundary inequality, rendering in red."
    )
    add_image(os.path.join(OUTPUT_DIR, "tc2_all_outside.png"))
    caption("Figure 11.2: TC2 — All test points lie outside the clipping window in exterior zones (0 accepted, 5 rejected).")

    # TC3
    sub_label("TC3 — Mixed Inside and Outside:")
    body(
        "Points: (60, 150), (200, 150), (300, 250), (450, 200), (250, 50). "
        "Two points lie inside (green), while three points lie outside (red)."
    )
    add_image(os.path.join(OUTPUT_DIR, "tc3_mixed.png"))
    caption("Figure 11.3: TC3 — Mixed distribution with 2 interior accepted points and 3 exterior rejected points.")

    # TC4
    sub_label("TC4 — Boundary, Corner, and Adjacent Points:")
    body(
        "Boundary points: (100, 100), (400, 300), (250, 100), (100, 200), (400, 150), (250, 300). "
        "These six points satisfy the inclusive inequalities and are accepted (green). "
        "Points (99, 200) and (250, 301) are offset by exactly 1 pixel outside the window and are rejected (red)."
    )
    add_image(os.path.join(OUTPUT_DIR, "tc4_on_boundary.png"))
    caption("Figure 11.4: TC4 — Boundary and corner verification showing 6 accepted boundary points and 2 rejected 1-pixel exterior points.")

    # ══════════════════════════════════════════════════════════════════════
    # 10. Observations
    # ══════════════════════════════════════════════════════════════════════
    section_label("Observations / Test Cases:")

    obs_headers = [
        "Test Case",
        "Tested Coordinates",
        "Expected Behavior",
        "Observed Behavior",
        "Status",
    ]
    obs_rows = [
        ["TC1", "4 points within [100, 400] x [100, 300]", "All points accepted", "4 green points plotted", "Pass"],
        ["TC2", "5 points outside bounds", "All points rejected", "5 red points plotted", "Pass"],
        ["TC3", "2 inside, 3 outside points", "2 accepted, 3 rejected", "2 green and 3 red points", "Pass"],
        ["TC4", "6 on edges/corners, 2 outside by 1 px", "Boundary accepted, 1px out rejected", "6 green and 2 red points", "Pass"],
    ]
    add_table(obs_headers, obs_rows)
    caption("Table 11.3: Observation results for all point clipping test cases")

    # ══════════════════════════════════════════════════════════════════════
    # 11. Result
    # ══════════════════════════════════════════════════════════════════════
    section_label("Result:")
    bullet(
        "The Point Clipping algorithm was successfully implemented in Python using OpenGL and FreeGLUT."
    )
    bullet(
        "All four test cases (inside, outside, mixed, and boundary/corner conditions) executed correctly with "
        "exact visual color-coding and matching terminal diagnostics."
    )
    bullet(
        "Boundary precision was confirmed: points lying on the window perimeter (e.g. x = 100 or y = 300) "
        "were correctly accepted, while points lying just one coordinate unit beyond (e.g. x = 99 or y = 301) "
        "were rejected."
    )

    # ══════════════════════════════════════════════════════════════════════
    # 12. Conclusion
    # ══════════════════════════════════════════════════════════════════════
    section_label("Conclusion:")
    body(
        "Point clipping provides the conceptual foundation for all 2D clipping algorithms in computer graphics. "
        "By evaluating points against the four boundary inequalities, the algorithm provides an optimal O(1) "
        "time complexity per point with zero floating-point division or trigonometric overhead. "
        "The experiment confirms that inclusive inequality boundaries correctly retain edge and corner pixels, "
        "providing a clean, reliable filtering mechanism before rasterization."
    )

    # ══════════════════════════════════════════════════════════════════════
    # 13. Source Code and Analysis (GitHub)
    # ══════════════════════════════════════════════════════════════════════
    section_label("Source Code and Analysis (GitHub):")
    body("https://github.com/TheNormalCoderr/computer_graphics_experiments")

    # ── Save ─────────────────────────────────────────────────────────────
    os.makedirs(DOCS_DIR, exist_ok=True)
    doc.save(DOCX_OUT)
    print(f"[Success] Report generated: {DOCX_OUT}")


if __name__ == "__main__":
    main()
