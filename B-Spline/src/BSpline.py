import os
import sys
import OpenGL.GL as gl
import OpenGL.GLUT as glut
import math
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
        CONTROL_POINTS.clear()
        print("Display is now cleared")
        glut.glutPostRedisplay()
# ======================== Mouse clicks ========================
CONTROL_POINTS = []
selected_point = None
def mouse(button, state, x, y):
    global selected_point

    if button == glut.GLUT_LEFT_BUTTON :
        if state == glut.GLUT_DOWN:
            canvas_x = x - CENTER_X
            canvas_y = CENTER_Y - y

            # find the control point within 15 pixels 
            minDistance = 15**2 
            for i, pt in enumerate(CONTROL_POINTS):
                distance = (pt[0] - canvas_x)**2 + (pt[1] - canvas_y)**2
                if distance < minDistance:
                    minDistance = distance
                    selected_point = i

            if selected_point is None:
                print(f"Point clicked at {canvas_x, canvas_y}")
                CONTROL_POINTS.append((canvas_x, canvas_y))
        elif state == glut.GLUT_UP:
            selected_point = None
    glut.glutPostRedisplay()

def motion(x, y):
    """updates the selected_point using mouse"""
    if selected_point is not None:
        canvas_x = x - CENTER_X
        canvas_y = CENTER_Y - y
        CONTROL_POINTS[selected_point] = (canvas_x, canvas_y)
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
    drawControlPoints()
    drawCurve()
    gl.glFlush()


# ======================== B-Spline Curve Functions ========================
def drawControlPoints():
    """draw the points clicked"""
    gl.glColor3f(0.0, 0.0, 0.0)
    gl.glPointSize(7)
    gl.glBegin(gl.GL_POINTS)
    for pt in CONTROL_POINTS:
        gl.glVertex2f(*pt)
    gl.glEnd()

def getWeight(i, degree, t, knots):
    """find the weight recursively"""
    if degree == 0:
        if t == knots[-1] and i == len(CONTROL_POINTS) - 1:
            return 1.0
        if knots[i] <= t < knots[i + 1]:
            return 1.0
        return 0.0

    weight1, weight2 = 0.0, 0.0

    if knots[i + degree] != knots[i]:
        weight1 = ((t - knots[i]) / (knots[i + degree] - knots[i])) * getWeight(i, degree - 1, t, knots)

    if knots[i + degree + 1] != knots[i + 1]:
        weight2 = ((knots[i + degree + 1] - t) / (knots[i + degree + 1] - knots[i + 1])) * getWeight(i + 1, degree - 1, t, knots)

    return weight1 + weight2

def getKnotVector(degree, n):
    """generate the KNOT vector"""
    knots = []
    # starting knots
    knots.extend([0] * (degree + 1))
    # internal knots 
    for i in range(1, n - degree):
        knots.append(i)
    # ending knots
    knots.extend([n - degree] * (degree + 1))
    return knots

def getCurvePoints():
    """return the curve points using the bezier polynomial general equation
    P(t) = sum(i=0,i=n) [C(n, i) (1 - t)^(n-i) t^i p(i)]
    """
    degree = 2

    if len(CONTROL_POINTS) < degree + 1:
        return []

    steps = 100
    curvePoints = []
    n = len(CONTROL_POINTS)
    knots = getKnotVector(degree, n)

    for step in range(steps + 1):
        t = knots[degree] + (step / steps) * (knots[n] - knots[degree])
        px, py = 0.0, 0.0

        for i in range(n):
            weight = getWeight(i, degree, t, knots)
            x, y = CONTROL_POINTS[i]
            px += x * weight
            py += y * weight
        curvePoints.append((px, py))
    return curvePoints

def drawCurve():
    """draw the curve"""
    curvePoints = getCurvePoints()
    gl.glLineWidth(2)
    gl.glColor3f(1.0, 0.0, 0.0)
    gl.glBegin(gl.GL_LINE_STRIP)
    for pt in curvePoints:
        gl.glVertex2f(*pt)
    gl.glEnd()
# ======================== Main function ========================
def main():
    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_SINGLE | glut.GLUT_RGB) #type: ignore
    glut.glutInitWindowSize(CANVAS_WIDTH, CANVAS_HEIGHT)
    glut.glutCreateWindow("B-Spline Curve Visualization")

    # Initialise Window 
    initWindow()

    # Register callbacks 
    glut.glutDisplayFunc(display)
    glut.glutKeyboardFunc(keyboard)
    glut.glutMouseFunc(mouse)
    glut.glutMotionFunc(motion)
    # Run the code 
    glut.glutMainLoop()

if __name__ == "__main__":
    main()