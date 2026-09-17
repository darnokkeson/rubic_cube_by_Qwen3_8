import math
import time
import os
import random

# --- Configuration ---
GRID_WIDTH = 80
GRID_HEIGHT = 40
FOV = 1.2
CAMERA_DISTANCE = 10.0
FRAME_DELAY = 0.05
SCRAMBLE_START_TIME = 5.0
SCRAMBLE_MOVES = 10

# Colors mapped to characters for better visibility in terminals
COLORS = {
    'U': 'W',  # White (Up)
    'D': 'Y',  # Yellow (Down)
    'F': '#',  # Blue (Front)
    'B': 'G',  # Green (Back)
    'R': '$',  # Red (Right)
    'L': 'O'   # Orange (Left)
}

# Initialize the 26 cubies of a 3x3x3 cube
def initialize_cubies():
    cubies = []
    for x in range(-1, 2):
        for y in range(-1, 2):
            for z in range(-1, 2):
                if x == 0 and y == 0 and z == 0:
                    continue
                
                faces = {}
                # Determine which faces this cubie has based on its position
                if x == 1: faces['R'] = COLORS['R']
                if x == -1: faces['L'] = COLORS['L']
                if y == 1: faces['U'] = COLORS['U']
                if y == -1: faces['D'] = COLORS['D']
                if z == 1: faces['F'] = COLORS['F']
                if z == -1: faces['B'] = COLORS['B']
                
                cubies.append({
                    'pos': [x, y, z],
                    'faces': faces,
                    # Orientation matrix (initially identity)
                    'rot': [[1,0,0],[0,1,0],[0,0,1]]
                })
    return cubies

def rotate_point_around_axis(point, axis, angle):
    """Rotate a 3D point around X, Y, or Z axis."""
    x, y, z = point
    if axis == 'x':
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        return [x, y * cos_a - z * sin_a, y * sin_a + z * cos_a]
    elif axis == 'y':
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        return [x * cos_a + z * sin_a, y, -x * sin_a + z * cos_a]
    elif axis == 'z':
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        return [x * cos_a - y * sin_a, x * sin_a + y * cos_a, z]

def project_to_2d(x, y, z):
    """Perspective projection to 2D screen coordinates."""
    # Move camera back
    z = z + CAMERA_DISTANCE
    if z <= 0.1:
        return None, None, 0
    
    scale = FOV / z
    sx = x * scale
    sy = y * scale
    return sx, sy, scale

def draw_block_on_grid(grid, cx, cy, size, char):
    """Draw a small square block of characters on the grid."""
    for i in range(size):
        for j in range(size):
            px = int(cx) + i
            py = int(cy) + j
            if 0 <= px < GRID_WIDTH and 0 <= py < GRID_HEIGHT:
                grid[py][px] = char

def render_cube(cubies, angle_x, angle_y):
    """Render the cube to a 2D grid."""
    grid = [[' ' for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
    
    # List to hold all visible faces with their depth and screen position
    draw_list = []
    
    # Center of the screen
    center_x = GRID_WIDTH // 2
    center_y = GRID_HEIGHT // 2
    
    # Scale factor to make the cube large enough to see details
    display_scale = 6.0 
    
    for cubie in cubies:
        pos = cubie['pos']
        
        # Rotate the entire cube around X and Y axes
        rotated_pos = rotate_point_around_axis(pos, 'x', angle_x)
        rotated_pos = rotate_point_around_axis(rotated_pos, 'y', angle_y)
        
        # For each face of this cubie, check if it's visible
        for face_name, char in cubie['faces'].items():
            # Define the normal vector for this face
            normals = {
                'U': [0, 1, 0], 'D': [0, -1, 0],
                'F': [0, 0, 1], 'B': [0, 0, -1],
                'R': [1, 0, 0], 'L': [-1, 0, 0]
            }
            normal = normals[face_name]
            
            # Rotate the normal vector to see which way it's pointing in world space
            rotated_normal = rotate_point_around_axis(normal, 'x', angle_x)
            rotated_normal = rotate_point_around_axis(rotated_normal, 'y', angle_y)
            
            # A face is visible if its z-component is positive (facing camera)
            # We use a threshold to avoid drawing edges that are perfectly sideways
            if rotated_normal[2] > 0.1:
                
                # Calculate the center of this face in 3D space
                # The face is offset from the cubie center by 0.5 units along the normal
                face_center_3d = [
                    rotated_pos[0] + normal[0] * 0.5,
                    rotated_pos[1] + normal[1] * 0.5,
                    rotated_pos[2] + normal[2] * 0.5
                ]
                
                # Project to 2D
                sx, sy, scale = project_to_2d(face_center_3d[0], face_center_3d[1], face_center_3d[2])
                
                if sx is not None:
                    # Convert to screen coordinates
                    screen_x = center_x + int(sx * display_scale)
                    screen_y = center_y - int(sy * display_scale)  # Invert Y
                    
                    # Depth for sorting (farther objects have smaller z in our projection, 
                    # but we want to draw farthest first, so we sort by original z)
                    depth = face_center_3d[2]
                    
                    draw_list.append({
                        'x': screen_x,
                        'y': screen_y,
                        'z': depth,
                        'char': char
                    })
    
    # Sort by depth: Farthest (smallest z) first
    draw_list.sort(key=lambda x: x['z'])
    
    # Draw all visible faces
    for face in draw_list:
        # Each sticker is a 3x3 block of characters for visibility
        draw_block_on_grid(grid, face['x'] - 1, face['y'] - 1, 3, face['char'])
    
    return grid

def rotate_layer(cubies, axis, layer_index, angle):
    """Rotate a specific layer of the cube around an axis."""
    # Only rotate cubies that belong to this layer
    for i, cubie in enumerate(cubies):
        pos = cubie['pos']
        if pos[axis] == layer_index:
            # Rotate position
            new_pos = rotate_point_around_axis(pos, axis, angle)
            cubies[i]['pos'] = new_pos
            
            # Update face orientations
            # We need to track which original faces are now pointing where.
            # For simplicity in this visualization, we just rotate the position.
            # The colors are tied to the *global* direction they originally had.
            # To make it look correct after rotation, we need to update the 'faces' dict keys.
            
            # Let's implement a proper orientation update for the faces.
            # We'll keep track of the original face normals and rotate them.
            
            # This is a simplified approach: 
            # Instead of tracking complex orientations, we can just rotate the *position* 
            # and then re-determine which global faces are visible based on the new position.
            # However, this doesn't work for Rubik's cubes because the colors move with the piece.
            
            # Correct approach: Store the orientation matrix for each cubie.
            # For this script, we'll use a simpler trick: 
            # We store the *original* face names and their positions relative to the cubie center.
            # When we rotate the cubie, we rotate those relative normals too.
            
            # Let's add an 'orientation' field to each cubie if not present.
            if 'orientation' not in cubie:
                cubie['orientation'] = {name: normal for name, normal in [
                    ('U', [0, 1, 0]), ('D', [0, -1, 0]),
                    ('F', [0, 0, 1]), ('B', [0, 0, -1]),
                    ('R', [1, 0, 0]), ('L', [-1, 0, 0])
                ] if name in cubie['faces']}
            
            # Rotate the orientation normals
            new_orientation = {}
            for name, normal in cubie['orientation'].items():
                rotated_normal = rotate_point_around_axis(normal, axis, angle)
                # Round to nearest integer to avoid floating point errors
                rounded_normal = tuple(round(v) for v in rotated_normal)
                new_orientation[name] = rounded_normal
            
            cubie['orientation'] = new_orientation

def scramble_cube(cubies):
    """Perform random layer turns to scramble the cube."""
    axes = ['x', 'y', 'z']
    layers = [-1, 0, 1]
    
    for _ in range(SCRAMBLE_MOVES):
        axis = random.choice(axes)
        layer = random.choice(layers)
        # 90 degree turn
        angle = math.pi / 2 * random.choice([1, -1])
        
        rotate_layer(cubies, axes.index(axis), layer, angle)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    print("Initializing Large Rubik's Cube...")
    cubies = initialize_cubies()
    
    # Initialize orientation for all cubies
    normals_map = {
        'U': [0, 1, 0], 'D': [0, -1, 0],
        'F': [0, 0, 1], 'B': [0, 0, -1],
        'R': [1, 0, 0], 'L': [-1, 0, 0]
    }
    for cubie in cubies:
        cubie['orientation'] = {}
        for name in cubie['faces']:
            cubie['orientation'][name] = normals_map[name]

    start_time = time.time()
    angle_x = math.pi / 6  # Start with a slight tilt to see 3 faces
    angle_y = math.pi / 4  # Start rotated to show corner
    
    speed = 0.02
    scrambled = False
    
    try:
        while True:
            elapsed = time.time() - start_time
            
            if not scrambled and elapsed > SCRAMBLE_START_TIME:
                print("\n*** SCRAMBLING CUBE ***")
                scramble_cube(cubies)
                scrambled = True
                time.sleep(1)
            
            # Render
            grid = render_cube(cubies, angle_x, angle_y)
            
            clear_screen()
            for row in grid:
                print(''.join(row))
            
            # Update rotation
            angle_x += speed
            angle_y += speed * 0.7
            
            time.sleep(FRAME_DELAY)
            
    except KeyboardInterrupt:
        clear_screen()
        print("\nAnimation stopped.")

if __name__ == "__main__":
    main()
