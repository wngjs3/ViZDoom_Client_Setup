import os
import math
import cv2
import numpy as np
import vizdoom as vzd
import webdataset as wds
from time import sleep


def normalize_angle_deg(deg):
    """Normalize to -180~180 range"""
    while deg > 180:
        deg -= 360
    while deg <= -180:
        deg += 360
    return deg


def calculate_relative_angle(player_x, player_y, player_angle, target_x, target_y):
    """Calculate relative angle of target from player's perspective"""
    # Target direction vector
    dx = target_x - player_x
    dy = target_y - player_y

    # Angle to target (in radians)
    target_angle_rad = math.atan2(dy, dx)
    target_angle_deg = math.degrees(target_angle_rad)

    # Relative angle from player's viewpoint
    relative_angle = normalize_angle_deg(target_angle_deg - player_angle)

    return relative_angle


def calculate_distance(x1, y1, x2, y2):
    """Calculate distance between two points"""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def get_all_objects_info(objects, player_x=0, player_y=0, debug_detail=False):
    """Extract information for all objects"""
    objects_info = []
    enemy_objects = []

    if objects is None:
        return objects_info

    # Print attributes of first object (for debugging)
    if len(objects) > 0 and debug_detail:
        print(f"[DEBUG] Object attribute list: {dir(objects[0])}")
        # Print all attribute values of first object
        for attr in dir(objects[0]):
            if not attr.startswith("__"):
                try:
                    value = getattr(objects[0], attr)
                    print(f"   - {attr}: {value}")
                except Exception as e:
                    print(f"   - {attr}: [Error: {e}]")

    # List of enemy object names
    enemy_names = [
        "ZombieMan",
        "ShotgunGuy",
        "ChaingunGuy",
        "DoomImp",
        "Demon",
        "Spectre",
        "LostSoul",
        "Cacodemon",
        "HellKnight",
        "BaronOfHell",
        "Arachnotron",
        "PainElemental",
        "Revenant",
        "Mancubus",
        "Archvile",
        "SpiderMastermind",
        "Cyberdemon",
        "DoomPlayer",  # Include other players
    ]

    # Extract information for all objects
    for obj in objects:
        try:
            # Exclude items
            if hasattr(obj, "type") and obj.type == 1:  # type 1 is item
                continue

            # Extract basic information
            obj_info = {
                "id": obj.id,
                "position": (obj.position_x, obj.position_y, obj.position_z),
                "pitch": obj.pitch,
                "angle": obj.angle,
                "name": getattr(obj, "name", f"Object_{obj.id}"),
                "type": getattr(obj, "type", 0),
            }

            # Always treat players with specific IDs as dead
            # Example: Player with ID 112
            if obj.id == 112:
                obj_info["is_dead"] = True
                if debug_detail:
                    print(f"[INFO] Treating player with specific ID({obj.id}) as dead.")

            # Set dead status if name contains "Dead"
            if "Dead" in obj_info["name"]:
                obj_info["is_dead"] = True

            # Filter server host players (ServerGhost, Host, etc.)
            if obj_info["name"] in ["ServerGhost", "Host"]:
                if debug_detail:
                    print(
                        f"[INFO] Server host player detected: {obj_info['name']}, ID={obj_info['id']}"
                    )
                obj_info["is_server_host"] = True
                obj_info["is_dead"] = True  # Don't display server host

            # Add number to name for DoomPlayer objects and additional debugging
            if obj_info["name"] == "DoomPlayer":
                # Check if player is invisible (possibly server host)
                is_invisible = False

                # Try various methods to detect invisibility
                if hasattr(obj, "is_visible") and not obj.is_visible:
                    is_invisible = True
                elif hasattr(obj, "visible") and not obj.visible:
                    is_invisible = True
                elif hasattr(obj, "alpha") and obj.alpha < 0.5:  # Low transparency
                    is_invisible = True

                # Players near (0,0,0) are usually server players
                if (
                    abs(obj.position_x) < 1
                    and abs(obj.position_y) < 1
                    and abs(obj.position_z) < 1
                ):
                    is_invisible = True
                    if debug_detail:
                        print(
                            f"[INFO] Player detected near origin: ID={obj_info['id']}, Position={obj_info['position']}"
                        )

                if is_invisible:
                    obj_info["is_server_host"] = True
                    obj_info["is_dead"] = True  # Don't display server host
                    if debug_detail:
                        print(f"[INFO] Invisible player detected: ID={obj_info['id']}")

                # Try to extract player number
                if hasattr(obj, "player_number"):
                    obj_info["player_number"] = obj.player_number
                    obj_info["name"] = f"Player{obj.player_number}"
                    if debug_detail:
                        print(f"[INFO] Player number: {obj.player_number}")
                else:
                    obj_info["name"] = f"Player_{obj.id}"

            # Check and extract additional attributes
            if hasattr(obj, "health"):
                obj_info["health"] = obj.health
                # Extract player status (whether alive)
                obj_info["is_dead"] = obj.health <= 0

            # Calculate distance
            dx = obj.position_x - player_x
            dy = obj.position_y - player_y
            distance = math.sqrt(dx * dx + dy * dy)
            obj_info["distance"] = distance

            # Classify enemy objects (include only living enemies)
            if hasattr(obj, "name") and any(enemy in obj.name for enemy in enemy_names):
                # Only display living enemies or players in ESP
                if not hasattr(obj, "health") or obj.health > 0:
                    enemy_objects.append(obj_info)
                else:
                    # Add dead enemies to list with status indicator
                    obj_info["is_dead"] = True
                    enemy_objects.append(obj_info)

            objects_info.append(obj_info)
        except Exception as e:
            print(f"[ERROR] Error extracting object information: {e}")

    # Output enemy object information
    if debug_detail:
        print(f"\n[DEBUG] Total detected objects: {len(objects_info)}")
        print(f"[DEBUG] Detected enemy objects: {len(enemy_objects)}")

    # Sort enemy objects by distance
    enemy_objects.sort(key=lambda x: x["distance"])

    return enemy_objects


def world_to_screen(
    player_x,
    player_y,
    player_z,
    player_angle_deg,
    player_pitch_deg,
    obj_x,
    obj_y,
    obj_z,
    screen_width,
    screen_height,
    fov_deg=90.0,
):
    """
    Estimates screen coordinates (screen_x, screen_y) using the z-coordinate difference
    between player(px, py, pz) and object(ox, oy, oz).

    - Only considers Yaw (horizontal angle) rotation.
    - Does not consider Pitch (vertical view), only adjusts vertical screen coordinates based on z-axis difference.
    - Returns None if localX <= 0 (behind), considering it 'behind the screen'.
    """

    # 1) Relative coordinates from player to object
    dx = obj_x - player_x
    dy = obj_y - player_y
    dz = obj_z - player_z  # Height difference

    # 2) Yaw (horizontal angle) rotation
    yaw = math.radians(player_angle_deg)

    # localX: front/back (camera axis), localY: left/right
    localX = dx * math.cos(yaw) + dy * math.sin(yaw)
    # If the sign differs from the original, adjust the -(...) part
    localY = -(-dx * math.sin(yaw) + dy * math.cos(yaw))

    # Don't display objects behind (localX <= 0)
    if localX <= 0:
        return None

    # 3) Screen X-coordinate based on horizontal FOV
    half_fov = math.radians(fov_deg / 2.0)
    scale = (screen_width / 2) / math.tan(half_fov)
    screen_x = (screen_width / 2) + (localY * scale / localX)

    # 4) Vertical coordinate simply reflects z difference
    #
    #  - The smaller localX (closer), the larger the object should appear,
    #    so screen_y should be proportional to dz / localX.
    #  - Here, we assume vertical FOV is the same as fov_deg (simplification).
    #  - The higher above player's view, the smaller the screen y value (moves upward).

    # screen_y = (screen_height / 2) - (dz * scale / localX * 3.0)
    screen_y = (screen_height / 2) * 0.9 - (
        math.radians(player_pitch_deg) + math.atan(dz / math.sqrt(dx**2 + dy**2))
    ) * scale

    # 5) Handle coordinates outside screen (optional)
    if not (0 <= screen_x <= screen_width and 0 <= screen_y <= screen_height):
        # Depending on needs, return None or clamp to screen borders
        pass

    return int(screen_x), int(screen_y)


def draw_esp_overlay(frame, player_pos, player_angle, player_pitch, objects_info):
    """Draw ESP information overlay on game screen"""
    height, width = frame.shape[:2]
    overlay = frame.copy()

    # Player position information
    px, py, pz = player_pos  # player_pos received as (x, y, z) tuple

    # Process each object information
    for i, obj in enumerate(objects_info):
        # Skip dead players
        is_dead = obj.get("is_dead", False) or (obj.get("health", 100) <= 0)
        if is_dead:
            continue  # Skip dead objects

        obj_x, obj_y, obj_z = obj["position"]
        obj_name = obj["name"]
        obj_id = obj["id"]
        obj_angle = obj["angle"]
        distance = obj["distance"]

        # Color setting - default red (BGR: 0, 0, 255)
        color = (0, 0, 255)

        # Simple 3D projection (using z difference)
        screen_pos = world_to_screen(
            px,
            py,
            pz,  # Player position x,y,z
            player_angle,  # Player angle
            player_pitch,  # Player pitch
            obj_x,
            obj_y,
            obj_z,  # Object x,y,z
            width,
            height,
            fov_deg=90.0,
        )

        if screen_pos is not None:
            sx, sy = screen_pos
            # Adjust display size based on distance (smaller for dead objects)
            size = max(3, int(80 / (1 + distance / 200)))
            if is_dead:
                size = max(2, size // 2)  # Reduce size for dead objects

            # Draw circle
            cv2.circle(overlay, (sx, sy), size, color, 2)

            # Set status text
            status_text = ""
            if is_dead:
                status_text = " DEAD"
            elif "health" in obj:
                status_text = f" HP:{obj['health']}"

            # Display distance and status
            cv2.putText(
                overlay,
                f"{distance:.0f}" + status_text,
                (sx - 20, sy - size - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

            # Display object name
            cv2.putText(
                overlay,
                f"{obj_name}",
                (sx - 20, sy + size + 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

    # Apply overlay (70% transparency)
    alpha = 0.7
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    return frame


def save_episode(
    obs_list,
    map_list,
    measurements_list,
    location_list,
    action_list,
    done_list,
    num_episodes,
    writer,
):
    # Convert lists to numpy arrays and transpose as needed.
    """Save episode data to a file using the webdataset format"""
    if len(obs_list) == 0:
        print("No data to save")
        return

    # Create a dictionary of tensors for sample creation
    sample = {
        "frames.npy": np.array(obs_list),
        "maps.npy": (
            np.array(map_list) if map_list else np.zeros((len(obs_list), 1, 1, 3))
        ),
        "measurements.npy": np.array(measurements_list),
        "locations.npy": np.array(location_list),
        "actions.npy": np.array(action_list),
        "dones.npy": np.array(done_list),
    }

    # Add to the writer
    writer.write(sample)
    print(f"Saved episode {num_episodes} with {len(obs_list)} frames")


def rotate_and_resize(image, angle, output_size=(360, 360), center_coord=None):
    """Rotate and resize an image for automap view"""
    height, width = image.shape[:2]

    # Use center of image as rotation center if not provided
    if center_coord is None:
        center_x, center_y = width // 2, height // 2
    else:
        center_x, center_y = center_coord

    # Get rotation matrix
    rotation_matrix = cv2.getRotationMatrix2D((center_x, center_y), angle, 1)

    # Apply affine transformation (rotation)
    rotated_image = cv2.warpAffine(image, rotation_matrix, (width, height))

    # Resize to output dimensions
    resized_image = cv2.resize(rotated_image, output_size)

    return resized_image
