import os
import sys
import OpenGL.GL as gl
import OpenGL.GLUT as glut
import OpenGL.GLU as glu
# ======================== Canvas configuration ========================
CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 800
CENTER_X = CANVAS_WIDTH // 2
CENTER_Y = CANVAS_HEIGHT // 2
GRID_SIZE = 20

# ======================== buttons  ========================
CURRENT_OPERATION = "CLIP"
BUTTONS = {
    "CLIP": (-570, -410, 340, 390),
    "UNION": (-400, -240, 340, 390),
    "DIFFERENCE": (-230, -10, 340, 390)
}

# ======================== Keyboard bindings ========================
def keyboard(key, x, y):
    global PHASE

    # ESC key (UNICODE: 0x1B) is pressed to close window 
    if key == b'\x1b':
        """ESC key is pressed to close the window"""
        print("Window is closed")
        os._exit(0)
    elif key == b'\x63':
        """C is pressed to clear the screen"""
        CLIPPING_WINDOW_POINTS.clear()
        POLYGON_POINTS.clear()
        print("Display is now cleared")
        PHASE = "CLIP"
        glut.glutPostRedisplay()
    elif key == b'\r':
        """Enter is pressed to change the PHASE"""
        if PHASE == "CLIP" and len(CLIPPING_WINDOW_POINTS) >= 3:
            PHASE = "POLYGON"
            print("Clipping window completed")
        elif PHASE == "POLYGON" and len(POLYGON_POINTS) >= 3:
            PHASE = "DONE"
            print("Subject Polygon completed")
    glut.glutPostRedisplay()

# ======================== Mouse clicks ========================
CLIPPING_WINDOW_POINTS = []
POLYGON_POINTS = []
PHASE = "CLIP"
def mouse(button, state, x, y):
    global CURRENT_OPERATION

    canvas_x = x - CENTER_X
    canvas_y = CENTER_Y - y

    if button == glut.GLUT_LEFT_BUTTON and state == glut.GLUT_DOWN:
        print(f"Point clicked at {canvas_x, canvas_y}")
        if PHASE == "DONE":
            for name, (x1, x2, y1, y2) in BUTTONS.items():
                if x1 <= canvas_x <= x2 and y1 <= canvas_y <= y2:
                    CURRENT_OPERATION = name
                    print("Selected:", name)
        elif PHASE == "CLIP":
            CLIPPING_WINDOW_POINTS.append((canvas_x, canvas_y))
        elif PHASE == "POLYGON":
            POLYGON_POINTS.append((canvas_x, canvas_y))

    glut.glutPostRedisplay()

# ======================== Initialize OpenGL window ========================
def initWindow():
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    gl.glOrtho(-CENTER_X, CENTER_X, -CENTER_Y, CENTER_Y, -1.0, 1.0)

    # enable blending 
    # Enable transparency
    gl.glEnable(gl.GL_BLEND)
    gl.glBlendFunc(
        gl.GL_SRC_ALPHA,
        gl.GL_ONE_MINUS_SRC_ALPHA
    )

# ======================== Drawing functions ========================
def drawCanvas():
    gl.glClearColor(1.0, 1.0, 1.0, 1.0)
    gl.glClear(gl.GL_COLOR_BUFFER_BIT)

   # Draw axis lines 
    AXIS_COLOR = (0.5, 0.5, 0.5)
    gl.glLineWidth(2)
    gl.glColor3f(*AXIS_COLOR)
    gl.glBegin(gl.GL_LINES)
    gl.glVertex2f(0.0, CENTER_Y)
    gl.glVertex2f(0.0, -CENTER_Y)
    gl.glVertex2f(-CENTER_X, 0.0)
    gl.glVertex2f(CENTER_X, 0.0)
    gl.glEnd()

def drawButtons():
    """Draw operation buttons with labels"""
    for name, (x1, x2, y1, y2) in BUTTONS.items():
        if name == CURRENT_OPERATION:
            gl.glColor3f(0.2, 0.7, 0.3)
        else:
            gl.glColor3f(0.3, 0.3, 0.3)

        gl.glBegin(gl.GL_QUADS)
        gl.glVertex2f(x1, y1)
        gl.glVertex2f(x2, y1)
        gl.glVertex2f(x2, y2)
        gl.glVertex2f(x1, y2)
        gl.glEnd()

        # Draw button text
        gl.glColor3f(1.0, 1.0, 1.0)
        gl.glRasterPos2f((x1+x2)/2 - len(name)*5, (y1+y2)/2 - 6)

        for char in name:
            glut.glutBitmapCharacter(glut.GLUT_BITMAP_HELVETICA_18, ord(char)) # type:ignore

def drawPolygon(points, mode, color):
    """draw the Subject polygon"""
    # to accurately fill concave polygons 
    if mode == gl.GL_POLYGON:
        tess = glu.gluNewTess()
        glu.gluTessCallback(tess, glu.GLU_TESS_BEGIN, gl.glBegin)
        glu.gluTessCallback(tess, glu.GLU_TESS_VERTEX, gl.glVertex3dv)
        glu.gluTessCallback(tess, glu.GLU_TESS_END, gl.glEnd)
        gl.glColor4f(*color)
        glu.gluTessBeginPolygon(tess, None)
        glu.gluTessBeginContour(tess)
    
        for x, y in points:
            glu.gluTessVertex(tess, (x, y, 0), (x, y, 0))
    
        glu.gluTessEndContour(tess)
        glu.gluTessEndPolygon(tess)
        glu.gluDeleteTess(tess)
    else:
        gl.glColor4f(*color)
        gl.glBegin(mode)
        for pt in points:
            gl.glVertex2f(*pt)
        gl.glEnd()

# Display function 
def display():
    """Display canvas and selected operation"""
    drawCanvas()
    drawButtons()
    drawPolygon(CLIPPING_WINDOW_POINTS, gl.GL_LINE_LOOP, (1.0, 0.0, 0.0, 1.0))
    drawPolygon(POLYGON_POINTS, gl.GL_LINE_LOOP, (0.0, 0.0, 1.0, 1.0))
    
    if PHASE == "DONE":
        weilerAtherton()
        
    gl.glFlush()

# ======================== Utility Functions ========================
def crossProduct(a, b):
    """find cross product of two vectors"""
    return a[0] * b[1] - a[1] * b[0]

def getIntersectionOfTwoEdges(A, B, C, D):
    """find intersection points between AB and CD lines"""
    ab = (B[0] - A[0], B[1] - A[1]) # (B - A)
    cd = (D[0] - C[0], D[1] - C[1]) # (D - C)
    ca = (C[0] - A[0], C[1] - A[1]) # (C - A)
    
    D = crossProduct(ab, cd) # denominator 
    if abs(D) < 1e-9: 
        return None
    
    t = crossProduct(ca, cd) / D
    u = crossProduct(ca, ab) / D

    if 0 <= t <= 1 and 0 <= u <= 1:
        return (A[0] + t * ab[0], A[1] + t * ab[1])

    return None

def pointsEqual(p1, p2, tol=1e-6):
    """Check if two 2D points are equal within tolerance."""
    return abs(p1[0] - p2[0]) <= tol and abs(p1[1] - p2[1]) <= tol

def signedArea(polygon):
    """Compute signed area of a polygon (positive = CCW, negative = CW)."""
    area = 0.0
    n = len(polygon)
    for i in range(n):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return area / 2.0

def ensureCCW(polygon):
    """Return polygon vertices in counter-clockwise order."""
    return list(reversed(polygon)) if signedArea(polygon) < 0 else list(polygon)

def getIntersections(clipPoly=None, subjPoly=None):
    """Find and sort intersections along each subject polygon edge.
        returns -> [(point, subject polygon edge(i), clip polygon edge(j))]
    """
    if clipPoly is None:
        clipPoly = CLIPPING_WINDOW_POINTS
    if subjPoly is None:
        subjPoly = POLYGON_POINTS

    intersections = []
    n = len(clipPoly)
    m = len(subjPoly)

    for i in range(m):
        a = subjPoly[i]
        b = subjPoly[(i + 1) % m]
        edge_intersections = []

        for j in range(n):
            c = clipPoly[j]
            d = clipPoly[(j + 1) % n]

            point = getIntersectionOfTwoEdges(a, b, c, d)
            if point is not None:
                # Avoid duplicate intersection if edge passes through a clip vertex
                if not any(pointsEqual(point, existing[0]) for existing in edge_intersections):
                    edge_intersections.append((point, i, j))

        edge_intersections.sort(key=lambda pt: (pt[0][0] - a[0])**2 + (pt[0][1] - a[1])**2)
        intersections.extend(edge_intersections)
    return intersections

def getClippingWindowList(intersections, clipPoly=None):
    """return clipping window vertices including intersections"""
    if clipPoly is None:
        clipPoly = CLIPPING_WINDOW_POINTS

    clippingWindowList = []

    for i in range(len(clipPoly)):
        v = clipPoly[i]
        if not clippingWindowList or not pointsEqual(v, clippingWindowList[-1]):
            clippingWindowList.append(v)

        intersectionPoints = [item for item in intersections if item[2] == i]
        intersectionPoints.sort(
            key=lambda item: (item[0][0] - v[0])**2 + (item[0][1] - v[1])**2
        )
        for item in intersectionPoints:
            pt = item[0]
            if not any(pointsEqual(pt, existing) for existing in clippingWindowList):
                clippingWindowList.append(pt)

    return clippingWindowList

def getPolygonList(intersections, subjPoly=None):
    """Return polygon vertices including intersections"""
    if subjPoly is None:
        subjPoly = POLYGON_POINTS

    # Traverse every polygon edge
    polygonList = []
    m = len(subjPoly)

    for i in range(m):
        v = subjPoly[i]
        if not polygonList or not pointsEqual(v, polygonList[-1]):
            polygonList.append(v)

        intersectionPoints = [item for item in intersections if item[1] == i]

        for item in intersectionPoints:
            pt = item[0]
            if not any(pointsEqual(pt, existing) for existing in polygonList):
                polygonList.append(pt)
    return polygonList

def isInside(point, polygon=None):
    """Check if point is inside polygon"""
    if polygon is None:
        polygon = CLIPPING_WINDOW_POINTS

    x, y = point
    inside = False

    for i in range(len(polygon)):
        x1, y1 = polygon[i]
        x2, y2 = polygon[(i + 1) % len(polygon)]
        if (y1 > y) != (y2 > y):
            if x < (x2-x1)*(y-y1)/(y2-y1) + x1:
                inside = not inside
    return inside

def findPointIndex(pointList, point):
    """Find index of point in pointList using tolerance-aware comparison."""
    for idx, p in enumerate(pointList):
        if pointsEqual(p, point):
            return idx
    raise ValueError(f"Point {point} not found in list")

def isEnteringPoint(before, after, point=None, clipPoly=None):
    """Determine whether an intersection is entering (outside -> inside).
    Returns True for entering, False for exiting, or None if grazing (no crossing).
    """
    if clipPoly is None:
        clipPoly = CLIPPING_WINDOW_POINTS
    if point is not None:
        before = ((before[0] + point[0]) / 2.0, (before[1] + point[1]) / 2.0)
        after = ((point[0] + after[0]) / 2.0, (point[1] + after[1]) / 2.0)

    before_in = isInside(before, clipPoly)
    after_in = isInside(after, clipPoly)
    if not before_in and after_in:
        return True
    if before_in and not after_in:
        return False
    return None

# ======================== Weiler Atherton Functions ========================
def _tracePolygons(clippingWindowList, subjectPolygonList, intersections, start_entering, reverse_clip=False):
    """Trace Weiler-Atherton result polygons for CLIP, UNION, or DIFFERENCE."""
    polygons = []
    max_steps = len(clippingWindowList) + len(subjectPolygonList) + 2

    for item in intersections:
        if item["entering"] is start_entering and not item["visited"]:
            startPoint = item["point"]
            currentPoint = startPoint
            result = [startPoint]
            item["visited"] = True
            currentList = subjectPolygonList
            steps = 0

            while steps < max_steps:
                steps += 1
                i = findPointIndex(currentList, currentPoint)
                step_dir = -1 if (reverse_clip and currentList is clippingWindowList) else 1
                nextPoint = currentList[(i + step_dir) % len(currentList)]

                if pointsEqual(nextPoint, startPoint):
                    break
                result.append(nextPoint)
                currentPoint = nextPoint

                for pt in intersections:
                    if pointsEqual(pt["point"], currentPoint):
                        pt["visited"] = True
                        if currentList is subjectPolygonList and pt["entering"] is (not start_entering):
                            currentList = clippingWindowList
                        elif currentList is clippingWindowList and pt["entering"] is start_entering:
                            currentList = subjectPolygonList
                        break
            polygons.append(result)
    return polygons

def getClippedPolygonPoints(clippingWindowList, subjectPolygonList, intersections):
    """Return points after clipping operation"""
    return _tracePolygons(clippingWindowList, subjectPolygonList, intersections, start_entering=True, reverse_clip=False)

def getUnionPolygonPoints(clippingWindowList, subjectPolygonList, intersections):
    """Return points after union operation"""
    return _tracePolygons(clippingWindowList, subjectPolygonList, intersections, start_entering=False, reverse_clip=False)

def getDifferencePolygonPoints(clippingWindowList, subjectPolygonList, intersections):
    """find the difference of polygons"""
    return _tracePolygons(clippingWindowList, subjectPolygonList, intersections, start_entering=False, reverse_clip=True)

def weilerAtherton():
    """Draw the result of selected Boolean operation"""
    if len(CLIPPING_WINDOW_POINTS) < 3 or len(POLYGON_POINTS) < 3:
        return []    

    # Normalize both polygons to counter-clockwise winding order
    clipPoly = ensureCCW(CLIPPING_WINDOW_POINTS)
    subjPoly = ensureCCW(POLYGON_POINTS)

    # initialize clipping window and subject polygon lists
    allIntersections = getIntersections(clipPoly, subjPoly)
    clippingWindowList = getClippingWindowList(allIntersections, clipPoly)
    subjectPolygonList = getPolygonList(allIntersections, subjPoly)

    # classify intersections as entering and exiting (ignore grazing touches)
    intersections = []
    seen_points = []
    for item in allIntersections:
        point = item[0]
        if any(pointsEqual(point, p) for p in seen_points):
            continue
        seen_points.append(point)
        index = findPointIndex(subjectPolygonList, point)
        entering = isEnteringPoint(
            subjectPolygonList[index - 1],
            subjectPolygonList[(index + 1) % len(subjectPolygonList)],
            point=point,
            clipPoly=clipPoly,
        )
        if entering is not None:
            intersections.append(
                {
                    "point": point,
                    "entering": entering,
                    "visited": False
                }
            )

    # If no true crossings exist, handle containment / disjoint cases
    if not intersections:
        # Use edge midpoint to avoid boundary ambiguity if a vertex grazes
        subj_test = ((subjPoly[0][0] + subjPoly[1][0]) / 2.0, (subjPoly[0][1] + subjPoly[1][1]) / 2.0)
        clip_test = ((clipPoly[0][0] + clipPoly[1][0]) / 2.0, (clipPoly[0][1] + clipPoly[1][1]) / 2.0)
        subject_inside = isInside(subj_test, clipPoly)
        clip_inside = isInside(clip_test, subjPoly)

        if CURRENT_OPERATION == "CLIP":
            if subject_inside:
                polygons = [subjPoly]
            elif clip_inside:
                polygons = [clipPoly]
            else:
                polygons = []

        elif CURRENT_OPERATION == "UNION":
            if subject_inside:
                polygons = [clipPoly]
            elif clip_inside:
                polygons = [subjPoly]
            else:
                polygons = [subjPoly, clipPoly]

        elif CURRENT_OPERATION == "DIFFERENCE":
            polygons = (
                [] if subject_inside
                else [subjPoly]
            )
    else:
        if CURRENT_OPERATION == "CLIP":
            polygons = getClippedPolygonPoints(clippingWindowList, subjectPolygonList, intersections)
        elif CURRENT_OPERATION == "UNION":
            polygons = getUnionPolygonPoints(clippingWindowList, subjectPolygonList, intersections)
        elif CURRENT_OPERATION == "DIFFERENCE":
            polygons = getDifferencePolygonPoints(clippingWindowList, subjectPolygonList, intersections)
        
    for polygon in polygons:
        drawPolygon(polygon, gl.GL_POLYGON, (0.0, 1.0, 0.0, 0.4)) # filled region
        drawPolygon(polygon, gl.GL_LINE_LOOP, (1.0, 0.6471, 0, 1.0)) # orange outline

# ======================== Main function ========================
def main():
    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_SINGLE | glut.GLUT_RGB) #type: ignore
    glut.glutInitWindowSize(CANVAS_WIDTH, CANVAS_HEIGHT)
    glut.glutCreateWindow("Weiler Atherton (Polygon Clipping) Visualization")

    # Initialise Window 
    initWindow()

    # Register callbacks 
    glut.glutDisplayFunc(display)
    glut.glutKeyboardFunc(keyboard)
    glut.glutMouseFunc(mouse)

    # Run the code 
    glut.glutMainLoop()

if __name__ == "__main__":
    main()