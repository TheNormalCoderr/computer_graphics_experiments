import os
import sys
import OpenGL.GL as gl
import OpenGL.GLUT as glut

# ======================== Canvas configuration ========================
CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 800
CENTER_X = CANVAS_WIDTH // 2
CENTER_Y = CANVAS_HEIGHT // 2
GRID_SIZE = 20

# ======================== Keyboard bindings ========================
def keyboard(key, x, y):
    # ESC key (UNICODE: 0x1B) is pressed to close window 
    if key == b'\x1b':
        print("Window is closed")
        os._exit(0)
    elif key == b'\x63':
        CLIPPING_WINODW_POINTS.clear()
        POLYGON_VERTICES.clear()
        print("Display is now cleared")
        glut.glutPostRedisplay()
# ======================== Mouse clicks ========================
CLIPPING_WINODW_POINTS = []
POLYGON_VERTICES = []
def mouse(button, state, x, y):
    canvas_x = x - CENTER_X
    canvas_y = CENTER_Y - y

    if button == glut.GLUT_LEFT_BUTTON and state == glut.GLUT_DOWN:
        print(f"Point clicked at {canvas_x, canvas_y}")
        if len(CLIPPING_WINODW_POINTS) == 2:
            POLYGON_VERTICES.append((canvas_x, canvas_y))
        else:
            # First 2 points for clipping window 
            CLIPPING_WINODW_POINTS.append((canvas_x, canvas_y))
    glut.glutPostRedisplay()

# ======================== Initialize OpenGL window ========================
def initWindow():
    gl.glMatrixMode(gl.GL_PROJECTION)
    gl.glLoadIdentity()
    gl.glOrtho(-CENTER_X, CENTER_X, -CENTER_Y, CENTER_Y, -1.0, 1.0)

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


# Display function 
def display():
    drawCanvas()
    drawClippingWindow()
    WeilerAtherton()
    gl.glFlush()


# ======================== Weiler Atherton Functions ========================

def drawClippingWindow():
    """Draw the clipping window"""
    # Calculate clipping window boundaries
    global x_min, x_max, y_min, y_max
    if len(CLIPPING_WINODW_POINTS) < 2:
        return
    x_min = min(CLIPPING_WINODW_POINTS[0][0], CLIPPING_WINODW_POINTS[1][0])
    x_max = max(CLIPPING_WINODW_POINTS[0][0], CLIPPING_WINODW_POINTS[1][0])
    y_min = min(CLIPPING_WINODW_POINTS[0][1], CLIPPING_WINODW_POINTS[1][1])
    y_max = max(CLIPPING_WINODW_POINTS[0][1], CLIPPING_WINODW_POINTS[1][1])
    CLIPPING_WINDOW_COLOR = (0.0, 0.0, 0.0)

    # Draw clipping window
    gl.glColor3f(*CLIPPING_WINDOW_COLOR)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(x_min, y_min)
    gl.glVertex2f(x_max, y_min)
    gl.glVertex2f(x_max, y_max)
    gl.glVertex2f(x_min, y_max)
    gl.glEnd()


def getIntersectionOnEdge(p1, p2, edge):
    """Find intersection of polygon segment with clipping edge"""
    # Extract coordinates of both endpoints
    x1, y1 = p1
    x2, y2 = p2
    # Check intersection with left boundary
    if edge == "left":
        if (x1 < x_min and x2 >= x_min) or (x1 >= x_min and x2 < x_min):
            y = y1 + (y2 - y1) * (x_min - x1) / (x2 - x1)
            if y_min <= y <= y_max:
                return (x_min, y)
    # Check intersection with right boundary
    elif edge == "right":
        if (x1 > x_max and x2 <= x_max) or (x1 <= x_max and x2 > x_max):
            y = y1 + (y2 - y1) * (x_max - x1) / (x2 - x1)
            if y_min <= y <= y_max:
                return (x_max, y)
    # Check intersection with bottom boundary
    elif edge == "bottom":
        if (y1 < y_min and y2 >= y_min) or (y1 >= y_min and y2 < y_min):
            x = x1 + (x2 - x1) * (y_min - y1) / (y2 - y1)
            if x_min <= x <= x_max:
                return (x, y_min)
    # Check intersection with top boundary
    elif edge == "top":
        if (y1 > y_max and y2 <= y_max) or (y1 <= y_max and y2 > y_max):
            x = x1 + (x2 - x1) * (y_max - y1) / (y2 - y1)
            if x_min <= x <= x_max:
                return (x, y_max)
    return None


def getIntersection(p1, p2):
    """Return all intersections along a polygon edge"""
    # Check all four clipping window boundaries
    intersections = []
    for edge in ["left", "top", "right", "bottom"]:
        point = getIntersectionOnEdge(p1, p2, edge)
        if point is not None and point not in intersections:
            intersections.append(point)

    # Sort intersections according to distance from p1
    intersections.sort(key=lambda pt: (pt[0] - p1[0])**2 + (pt[1] - p1[1])**2)
    return intersections


def getClippingWindowList():
    """Return clipping window vertices including intersections"""
    # Define clipping window corners and their corresponding edges
    window = [(x_min, y_min), (x_min, y_max), (x_max, y_max), (x_max, y_min)]
    edges = ["left", "top", "right", "bottom"]
    clippingWindowList = []
    # Traverse each clipping window edge
    for i in range(len(window)):
        p1 = window[i]
        clippingWindowList.append(p1)

        intersections = []
        # Find polygon intersections with the current window edge
        for j in range(len(POLYGON_VERTICES)):
            poly1 = POLYGON_VERTICES[j]
            poly2 = POLYGON_VERTICES[(j + 1) % len(POLYGON_VERTICES)]
            point = getIntersectionOnEdge(poly1, poly2, edges[i])
            if point is not None and point not in intersections:
                intersections.append(point)
        # Sort intersections along the current window edge
        intersections.sort(key=lambda pt: (pt[0] - p1[0])**2 + (pt[1] - p1[1])**2)
        
        clippingWindowList.extend(intersections)
    return clippingWindowList


def getPolygonList():
    """Return polygon vertices including intersections"""
    # Traverse every polygon edge
    polygonList = []
    for i in range(len(POLYGON_VERTICES)):
        p1 = POLYGON_VERTICES[i]
        p2 = POLYGON_VERTICES[(i + 1) % len(POLYGON_VERTICES)]
        polygonList.append(p1)
        # Insert intersections between consecutive polygon vertices
        polygonList.extend(getIntersection(p1, p2))
    return polygonList


def isInside(point):
    """Check whether a point lies inside the clipping window"""
    # Check whether point coordinates are within clipping boundaries
    x, y = point
    return x_min <= x <= x_max and y_min <= y <= y_max


def isEnteringPoint(before, after):
    """Determine whether an intersection is entering"""
    # Outside to inside indicates an entering intersection
    return not isInside(before) and isInside(after)


def processPoints():
    """Return clipped polygon vertices using Weiler-Atherton traversal"""
    # Check whether a valid polygon exists
    if len(POLYGON_VERTICES) < 3:
        return []
    
    # Construct polygon and clipping window lists
    polygonList = getPolygonList()
    clippingWindowList = getClippingWindowList()
    clippedPolygonPoints = []

    # Identify all intersection points
    intersections = []
    for point in polygonList:
        if point not in POLYGON_VERTICES and point not in intersections:
            intersections.append(point)

    # Classify intersections as entering or exiting
    intersectionInfo = {}
    for point in intersections:
        index = polygonList.index(point)
        before = polygonList[index - 1]
        after = polygonList[(index + 1) % len(polygonList)]
        intersectionInfo[point] = {"entering": isEnteringPoint(before, after), "visited": False}

    # Traverse from every unvisited entering intersection
    for startPoint in intersections:
        if not intersectionInfo[startPoint]["entering"] or intersectionInfo[startPoint]["visited"]:
            continue

        currentPolygon = [startPoint]
        currentPoint = startPoint
        currentList = "polygon"

        # Follow polygon and clipping window boundaries alternately
        while True:
            currentListPoints = polygonList if currentList == "polygon" else clippingWindowList
            index = currentListPoints.index(currentPoint)
            nextPoint = currentListPoints[(index + 1) % len(currentListPoints)]

            # Stop when the starting intersection is reached
            if nextPoint == startPoint:
                break
            if nextPoint not in currentPolygon:
                currentPolygon.append(nextPoint)

            # Switch lists at exiting and entering intersections
            if nextPoint in intersectionInfo:
                intersectionInfo[nextPoint]["visited"] = True
                if currentList == "polygon" and not intersectionInfo[nextPoint]["entering"]:
                    currentList = "window"
                elif currentList == "window" and intersectionInfo[nextPoint]["entering"]:
                    currentList = "polygon"
            currentPoint = nextPoint

        # Store the resulting clipped polygon
        if len(currentPolygon) >= 3:
            clippedPolygonPoints.append(currentPolygon)
    return clippedPolygonPoints


def WeilerAtherton():
    """Draw original and clipped polygons"""
    # Draw original polygon in red
    gl.glColor3f(1.0, 0.0, 0.0)
    gl.glLineWidth(2)
    gl.glBegin(gl.GL_LINE_LOOP)
    for point in POLYGON_VERTICES:
        gl.glVertex2f(*point)
    gl.glEnd()

    # Draw clipped polygons in green
    polygonsPoints = processPoints()
    gl.glLineWidth(2)
    gl.glColor3f(0.0, 1.0, 0.0)
    for polygon in polygonsPoints:
        gl.glBegin(gl.GL_LINE_LOOP)
        for pt in polygon:
            gl.glVertex2f(*pt)
        gl.glEnd()
      
    
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