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
        LINE_POINTS.clear()
        print("Display is now cleared")
        glut.glutPostRedisplay()
# ======================== Mouse clicks ========================
CLIPPING_WINODW_POINTS = []
LINE_POINTS = []
def mouse(button, state, x, y):
    canvas_x = x - CENTER_X
    canvas_y = CENTER_Y - y

    if button == glut.GLUT_LEFT_BUTTON and state == glut.GLUT_DOWN:
        print(f"Point clicked at {canvas_x, canvas_y}")
        if len(CLIPPING_WINODW_POINTS) == 2:
            LINE_POINTS.append((canvas_x, canvas_y))
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
    drawLines()
    gl.glFlush()

# ======================== Liang Barsky Functions ========================
RED = (1.0, 0.0, 0.0)
GREEN = (0.0, 1.0, 0.0)
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

def drawLines():
    global LINE_WIDTH, LINE_COLOR
    LINE_WIDTH = 2
    LINE_COLOR = RED
    for i in range(0, len(LINE_POINTS) - 1, 2):
        p1 = (LINE_POINTS[i][0], LINE_POINTS[i][1])
        p2 = (LINE_POINTS[i + 1][0], LINE_POINTS[i + 1][1])
        LiangBarskyClipLine(p1, p2)

def LiangBarskyClipLine(p1, p2):
    def colorLine(x1, y1, x2, y2, color):
        gl.glLineWidth(LINE_WIDTH)
        gl.glColor3f(*color)
        gl.glBegin(gl.GL_LINES)
        gl.glVertex2f(x1, y1)
        gl.glVertex2f(x2, y2)
        gl.glEnd()

    # Calculate P and Q values 
    x1, y1 = p1[0], p1[1]
    x2, y2 = p2[0], p2[1]

    delX = x2 - x1
    delY = y2 - y1

    # Original line color to RED 
    colorLine(x1, y1, x2, y2, RED)

    P = [-delX, delX, -delY, delY]
    Q = [x1 - x_min, x_max - x1, y1 - y_min, y_max - y1]
    r_enter, r_exit = 0.0, 1.0

    for i in range(4):
        if P[i] == 0: # line is parallel to clipping boundary
            if Q[i] < 0: # line is rejected 
                return
        else:
            r = Q[i] / P[i]
            if P[i] < 0:
                r_enter = max(r_enter, r)
            else:
                r_exit = min(r_exit, r)
    # Line is completely outside so rejected 
    if r_enter > r_exit: 
        return

    x1_clip = x1 + r_enter * delX
    y1_clip = y1 + r_enter * delY
    x2_clip = x1 + r_exit * delX
    y2_clip = y1 + r_exit * delY

    # Part of line is inside
    colorLine(x1_clip, y1_clip, x2_clip, y2_clip, color=GREEN)

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