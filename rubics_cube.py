import math
import time
import os
import sys
import random


# -----------------------------
# Terminal / rendering settings
# -----------------------------
try:
    term_size = os.get_terminal_size()
    WIDTH = max(60, min(120, term_size.columns - 2))
    HEIGHT = max(20, min(44, term_size.lines - 5))
except Exception:
    WIDTH = 100
    HEIGHT = 40

CX = WIDTH // 2
CY = HEIGHT // 2


# -----------------------------
# Square view correction
# -----------------------------
# Terminal character cells are usually taller than wide.
# Use 2.0 for a visually square cube in most terminals.
CHAR_ASPECT = 2.0

# Projected extents for this one-corner view.
PROJ_X_EXTENT = 3.0 / math.sqrt(2.0)
PROJ_Y_EXTENT = math.sqrt(6.0)

# Stretch X so the final rendered cube has equal visual width and height.
X_STRETCH = CHAR_ASPECT * (PROJ_Y_EXTENT / PROJ_X_EXTENT)

FULL_X_CELLS = 2.0 * PROJ_X_EXTENT * X_STRETCH
FULL_Y_CELLS = 2.0 * PROJ_Y_EXTENT

FIT_MARGIN = 0.92
BASE_SCALE = max(
    1.0,
    min(HEIGHT / FULL_Y_CELLS, WIDTH / FULL_X_CELLS) * FIT_MARGIN
)


# -----------------------------
# Static corner perspective
# -----------------------------
CAMERA_DISTANCE = 12.0

# Sticker size inside each 1x1 cubie face.
HALF_STICKER = 0.42

FRAME_DELAY = 0.025
WAIT_FOR_SCRAMBLE = 1.0
MOVE_DURATION = 0.65
PAUSE_AFTER_SCRAMBLE = 1.5
PAUSE_AFTER_SOLVE = 3.0
SCRAMBLE_MOVES = 12


# -----------------------------
# Rubik's cube colors / chars
# -----------------------------
COLORS = {
    'U': '◇',   # Up / White
    'D': '▩',   # Down / Yellow
    'F': '+',   # Front / Blue
    'B': '_',   # Back / Green
    'R': '.',   # Right / Red
    'L': '☸',   # Left / Orange
}


# -----------------------------
# Vector helpers
# -----------------------------
def vec_dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vec_cross(a, b):
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0]
    ]


def vec_norm(v):
    length = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if length == 0:
        return [0.0, 0.0, 0.0]
    return [v[0] / length, v[1] / length, v[2] / length]


# -----------------------------
# Static corner camera
# Camera looks at the cube from the (+X, +Y, +Z) corner.
# -----------------------------
CAM_POS = [CAMERA_DISTANCE, CAMERA_DISTANCE, CAMERA_DISTANCE]

FORWARD = vec_norm([-CAMERA_DISTANCE, -CAMERA_DISTANCE, -CAMERA_DISTANCE])
UP_WORLD = [0.0, 1.0, 0.0]

RIGHT = vec_norm(vec_cross(UP_WORLD, FORWARD))
CAM_UP = vec_norm(vec_cross(FORWARD, RIGHT))

# Direction from cube center to camera, normalized.
CAMERA_DIR = vec_norm(CAM_POS)

# Focal length. At the cube center, projection scale equals BASE_SCALE.
FOCAL = BASE_SCALE * (CAMERA_DISTANCE * math.sqrt(3.0))


# -----------------------------
# Cube state
# -----------------------------
def make_cubies():
    """
    Creates the 26 visible cubies of a 3x3x3 cube.
    """
    cubies = []

    for x in (-1, 0, 1):
        for y in (-1, 0, 1):
            for z in (-1, 0, 1):
                if x == 0 and y == 0 and z == 0:
                    continue

                stickers = []

                if x == 1:
                    stickers.append(((1, 0, 0), COLORS['R']))
                if x == -1:
                    stickers.append(((-1, 0, 0), COLORS['L']))

                if y == 1:
                    stickers.append(((0, 1, 0), COLORS['U']))
                if y == -1:
                    stickers.append(((0, -1, 0), COLORS['D']))

                if z == 1:
                    stickers.append(((0, 0, 1), COLORS['F']))
                if z == -1:
                    stickers.append(((0, 0, -1), COLORS['B']))

                cubies.append({
                    'pos': [x, y, z],
                    'sticker': stickers
                })

    return cubies


# -----------------------------
# 3D math helpers
# -----------------------------
def rotate_float(point, axis, angle):
    """
    Rotate a 3D point around X/Y/Z by angle radians.
    axis:
      0 = x
      1 = y
      2 = z
    """
    x, y, z = point
    c = math.cos(angle)
    s = math.sin(angle)

    if axis == 0:
        return [x, y * c - z * s, y * s + z * c]
    elif axis == 1:
        return [x * c + z * s, y, -x * s + z * c]
    else:
        return [x * c - y * s, x * s + y * c, z]


def rotate_exact(vector, axis, direction):
    """
    Exact 90-degree rotation for integer cube state.
    direction:
      +1 = +90
      -1 = -90
    """
    x, y, z = vector

    if direction == 1:
        if axis == 0:
            return [x, -z, y]
        elif axis == 1:
            return [z, y, -x]
        else:
            return [-y, x, z]
    else:
        if axis == 0:
            return [x, z, -y]
        elif axis == 1:
            return [-z, y, x]
        else:
            return [y, -x, z]


def apply_exact_move(cubies, axis, layer, direction):
    """
    Apply a full 90-degree layer turn to the logical cube state.
    """
    for cubie in cubies:
        if cubie['pos'][axis] == layer:
            cubie['pos'] = rotate_exact(cubie['pos'], axis, direction)
            cubie['sticker'] = [
                (tuple(rotate_exact(normal, axis, direction)), char)
                for normal, char in cubie['sticker']
            ]


# -----------------------------
# Move generation
# -----------------------------
def random_moves(count, last=None):
    """
    Generate random outer-face layer moves.
    Avoids immediately repeating the same face.
    """
    moves = []

    while len(moves) < count:
        axis = random.randrange(3)
        layer = random.choice((-1, 1))
        direction = random.choice((-1, 1))

        if last is not None and axis == last[0] and layer == last[1]:
            continue

        moves.append((axis, layer, direction))
        last = (axis, layer)

    return moves


def reverse_moves(moves):
    """
    Reverse a move sequence, flipping each direction.
    """
    return [
        (axis, layer, -direction)
        for axis, layer, direction in reversed(moves)
    ]


def move_name(move):
    """
    Human-readable move label.
    """
    if move is None:
        return '-'

    axis, layer, direction = move

    names = {
        0: {1: 'R', -1: 'L'},
        1: {1: 'U', -1: 'D'},
        2: {1: 'F', -1: 'B'}
    }

    name = names[axis][layer]

    if direction == -1:
        name += "'"

    return name


# -----------------------------
# Projection
# -----------------------------
def project_point(point):
    """
    Project a 3D world point to terminal 2D coordinates
    using the static corner perspective camera.

    X is stretched by X_STRETCH so the rendered cube appears square.
    """
    dx = point[0] - CAM_POS[0]
    dy = point[1] - CAM_POS[1]
    dz = point[2] - CAM_POS[2]

    d = [dx, dy, dz]

    z_depth = vec_dot(d, FORWARD)

    if z_depth <= 0.1:
        return None

    x_cam = vec_dot(d, RIGHT)
    y_cam = vec_dot(d, CAM_UP)

    scale = FOCAL / z_depth

    return [
        CX + x_cam * (scale * X_STRETCH),
        CY - y_cam * scale
    ]


# -----------------------------
# Sticker geometry
# -----------------------------
def sticker_corners(pos, normal):
    """
    Returns the 3D corners of one sticker face on one cubie.
    The sticker is slightly inset so gaps appear between stickers.
    """
    nx, ny, nz = normal

    cx = pos[0] + 0.5 * nx
    cy = pos[1] + 0.5 * ny
    cz = pos[2] + 0.5 * nz

    if nz != 0:
        u = (1.0, 0.0, 0.0)
        v = (0.0, 1.0, 0.0)
    elif nx != 0:
        u = (0.0, 1.0, 0.0)
        v = (0.0, 0.0, 1.0)
    else:
        u = (1.0, 0.0, 0.0)
        v = (0.0, 0.0, 1.0)

    h = HALF_STICKER

    def make(su, sv):
        return [
            cx + su * h * u[0] + sv * h * v[0],
            cy + su * h * u[1] + sv * h * v[1],
            cz + su * h * u[2] + sv * h * v[2]
        ]

    # Order forms a simple quadrilateral.
    return [
        make(1, 1),
        make(1, -1),
        make(-1, -1),
        make(-1, 1)
    ]


# -----------------------------
# ASCII polygon fill
# -----------------------------
def point_in_quad(x, y, pts):
    """
    Point-in-convex-quad test.
    """
    sign = 0

    for i in range(4):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % 4]

        cross = (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)

        if abs(cross) < 1e-7:
            continue

        s = 1 if cross > 0 else -1

        if sign == 0:
            sign = s
        elif s != sign:
            return False

    return True


def fill_quad(grid, pts, ch):
    """
    Fill a projected quadrilateral with a character.
    """
    if len(pts) != 4:
        return

    min_x = int(math.floor(min(p[0] for p in pts)))
    max_x = int(math.ceil(max(p[0] for p in pts)))
    min_y = int(math.floor(min(p[1] for p in pts)))
    max_y = int(math.ceil(max(p[1] for p in pts)))

    min_x = max(0, min_x)
    min_y = max(0, min_y)
    max_x = min(WIDTH - 1, max_x)
    max_y = min(HEIGHT - 1, max_y)

    if min_x > max_x or min_y > max_y:
        return

    for py in range(min_y, max_y + 1):
        y = py + 0.5
        row = grid[py]

        for px in range(min_x, max_x + 1):
            x = px + 0.5

            if point_in_quad(x, y, pts):
                row[px] = ch


# -----------------------------
# Rendering
# -----------------------------
def render(cubies, moving):
    """
    Render the cube to a 2D character grid.

    moving format:
      (axis, layer, angle)
      axis: 0=x, 1=y, 2=z
      layer: -1 or 1
      angle: current animated layer angle
    """
    grid = [[' ' for _ in range(WIDTH)] for _ in range(HEIGHT)]
    draw_items = []

    if moving is not None:
        move_axis, move_layer, move_angle = moving
    else:
        move_axis = move_layer = move_angle = None

    for cubie in cubies:
        pos = cubie['pos']

        in_moving_layer = (
            moving is not None and
            pos[move_axis] == move_layer
        )

        for normal, char in cubie['sticker']:
            nx, ny, nz = normal

            base_center = [
                pos[0] + 0.5 * nx,
                pos[1] + 0.5 * ny,
                pos[2] + 0.5 * nz
            ]

            if in_moving_layer:
                n = rotate_float(normal, move_axis, move_angle)
                center = rotate_float(base_center, move_axis, move_angle)
            else:
                n = list(normal)
                center = base_center

            # Face is visible if its normal points toward the corner camera.
            if vec_dot(n, CAMERA_DIR) <= 0.02:
                continue

            corners = sticker_corners(pos, normal)
            projected = []
            ok = True

            for corner in corners:
                if in_moving_layer:
                    cp = rotate_float(corner, move_axis, move_angle)
                else:
                    cp = list(corner)

                p = project_point(cp)

                if p is None:
                    ok = False
                    break

                projected.append((p[0], p[1]))

            if ok:
                center_dx = center[0] - CAM_POS[0]
                center_dy = center[1] - CAM_POS[1]
                center_dz = center[2] - CAM_POS[2]

                depth = vec_dot(
                    [center_dx, center_dy, center_dz],
                    FORWARD
                )

                draw_items.append((depth, projected, char))

    # Painter's algorithm:
    # Larger depth means farther away, so draw farthest first.
    draw_items.sort(key=lambda item: item[0], reverse=True)

    for _, pts, char in draw_items:
        fill_quad(grid, pts, char)

    return grid


# -----------------------------
# UI text
# -----------------------------
def make_status(phase, queue, current, now, idle_start, scramble_len):
    cur = move_name(current)
    nxt = move_name(queue[0]) if queue else '-'

    if phase == 'idle':
        remaining = max(0.0, WAIT_FOR_SCRAMBLE - (now - idle_start))
        msg = f"SOLVED        next scramble in {remaining:5.1f}s"

    elif phase == 'scrambling':
        done = scramble_len - len(queue) - (1 if current is not None else 0)
        msg = f"SCRAMBLING    {done:2d}/{scramble_len}   turn={cur}   next={nxt}"

    elif phase == 'solving':
        done = scramble_len - len(queue) - (1 if current is not None else 0)
        msg = f"SOLVING       {done:2d}/{scramble_len}   turn={cur}   next={nxt}"

    elif phase == 'scramble_pause':
        msg = "SCRAMBLED     solving in a moment..."

    elif phase == 'solve_pause':
        msg = "SOLVED        waiting..."

    else:
        msg = "READY         waiting..."

    if len(msg) > WIDTH:
        msg = msg[:WIDTH]

    return msg + ' ' * max(0, WIDTH - len(msg))


def make_legend():
    legend = "  U:W   D:Y   F:#   B:G   R:$   L:O        Ctrl+C stop"
    if len(legend) > WIDTH:
        legend = legend[:WIDTH]
    return legend + ' ' * max(0, WIDTH - len(legend))


def write_frame(grid, status, legend):
    lines = [status]
    lines.extend(''.join(row) for row in grid)
    lines.append(legend)

    text = '\n'.join(lines)

    if os.name == 'nt':
        os.system('cls')
    else:
        sys.stdout.write('\x1b[2J\x1b[H')
        sys.stdout.flush()

    sys.stdout.write(text)
    sys.stdout.flush()


def clear_final():
    if os.name == 'nt':
        os.system('cls')
    else:
        sys.stdout.write('\x1b[2J\x1b[H')
        sys.stdout.flush()


# -----------------------------
# Main animation loop
# -----------------------------
def main():
    cubies = make_cubies()

    phase = 'idle'
    idle_start = time.time()
    pause_start = 0.0

    queue = []
    scramble_sequence = []

    current_move = None
    current_start = 0.0

    try:
        while True:
            now = time.time()

            # -------------------
            # State machine
            # -------------------
            if current_move is not None:
                if now - current_start >= MOVE_DURATION:
                    axis, layer, direction = current_move
                    apply_exact_move(cubies, axis, layer, direction)
                    current_move = None

                    if (phase == 'scrambling' or phase == 'solving') and queue:
                        current_move = queue.pop(0)
                        current_start = now
                    elif phase == 'scrambling' and not queue:
                        phase = 'scramble_pause'
                        pause_start = now
                    elif phase == 'solving' and not queue:
                        phase = 'solve_pause'
                        pause_start = now

            else:
                if phase == 'idle':
                    if now - idle_start >= WAIT_FOR_SCRAMBLE:
                        scramble_sequence = random_moves(SCRAMBLE_MOVES)
                        queue = list(scramble_sequence)
                        phase = 'scrambling'

                        if queue:
                            current_move = queue.pop(0)
                            current_start = now

                elif phase == 'scramble_pause':
                    if now - pause_start >= PAUSE_AFTER_SCRAMBLE:
                        queue = reverse_moves(scramble_sequence)
                        phase = 'solving'

                        if queue:
                            current_move = queue.pop(0)
                            current_start = now

                elif phase == 'solve_pause':
                    if now - pause_start >= PAUSE_AFTER_SOLVE:
                        phase = 'idle'
                        idle_start = now

            # -------------------
            # Animated layer turn
            # -------------------
            moving = None

            if current_move is not None:
                axis, layer, direction = current_move

                t = (now - current_start) / MOVE_DURATION
                if t < 0.0:
                    t = 0.0
                elif t > 1.0:
                    t = 1.0

                # Smoothstep easing.
                smooth = t * t * (3.0 - 2.0 * t)

                angle = math.pi * 0.5 * direction * smooth
                moving = (axis, layer, angle)

            grid = render(cubies, moving)

            status = make_status(
                phase,
                queue,
                current_move,
                now,
                idle_start,
                SCRAMBLE_MOVES
            )

            legend = make_legend()

            write_frame(grid, status, legend)

            time.sleep(FRAME_DELAY)

    except KeyboardInterrupt:
        clear_final()
        print("\nStopped.")
        sys.stdout.flush()


if __name__ == '__main__':
    main()
