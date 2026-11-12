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
        POINTS.clear()
        print("Display is now cleared")
        glut.glutPostRedisplay()
# ======================== Mouse clicks ========================
CLIPPING_WINODW_POINTS = []
POINTS = []
def mouse(button, state, x, y):
    canvas_x = x - CENTER_X
    canvas_y = CENTER_Y - y

    if button == glut.GLUT_LEFT_BUTTON and state == glut.GLUT_DOWN:
        print(f"Point clicked at {canvas_x, canvas_y}")
        if len(CLIPPING_WINODW_POINTS) == 2:
            POINTS.append((canvas_x, canvas_y))
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
    drawPoints()
    gl.glFlush()

# ======================== Point Clipping Functions ========================
def drawClippingWindow():
    global x_min, x_max, y_min, y_max

    if len(CLIPPING_WINODW_POINTS) < 2:
        return  
    
    x_min = min(CLIPPING_WINODW_POINTS[0][0], CLIPPING_WINODW_POINTS[1][0])
    x_max = max(CLIPPING_WINODW_POINTS[0][0], CLIPPING_WINODW_POINTS[1][0])
    y_min = min(CLIPPING_WINODW_POINTS[0][1], CLIPPING_WINODW_POINTS[1][1])
    y_max = max(CLIPPING_WINODW_POINTS[0][1], CLIPPING_WINODW_POINTS[1][1])

    CLIPPING_WINDOW_COLOR = (0.0, 0.0, 0.0)
    """Draw clipping window"""
    if not CLIPPING_WINODW_POINTS:
        print("Clipping window Points are not clicked yet")
        return 

    # Draw clipping window 
    gl.glColor3f(*CLIPPING_WINDOW_COLOR)
    gl.glBegin(gl.GL_LINE_LOOP)
    gl.glVertex2f(x_min, y_min)
    gl.glVertex2f(x_max, y_min)
    gl.glVertex2f(x_max, y_max)
    gl.glVertex2f(x_min, y_max)
    gl.glEnd()

def isValidPoint(x, y, x_min, x_max, y_min, y_max):
    """Check if the point is inside the clipping window or not"""
    if x_min <= x <= x_max and y_min <= y <= y_max:
        return True
    return False

def drawPoints():
    VALID_POINT_COLOR = (0.0, 1.0, 0.0)
    INVALID_POINT_COLOR = (1.0, 0.0, 0.0)
    POINT_SIZE = 10

    gl.glPointSize(POINT_SIZE)
    gl.glBegin(gl.GL_POINTS)
    for x, y in POINTS:
        if isValidPoint(x, y, x_min, x_max, y_min, y_max):
            gl.glColor3f(*VALID_POINT_COLOR)
            gl.glVertex2f(x, y)
        else:
            gl.glColor3f(*INVALID_POINT_COLOR)
            gl.glVertex2f(x, y)
    gl.glEnd()

# ======================== Main function ========================
def main():
    glut.glutInit(sys.argv)
    glut.glutInitDisplayMode(glut.GLUT_SINGLE | glut.GLUT_RGB) #type: ignore
    glut.glutInitWindowSize(CANVAS_WIDTH, CANVAS_HEIGHT)
    glut.glutCreateWindow("Point Clipping Visualization")

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