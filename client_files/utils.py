import os
import math
import cv2
import numpy as np
import vizdoom as vzd
import webdataset as wds
from time import sleep


def normalize_angle_deg(deg):
    """-180~180 범위로 정규화"""
    while deg > 180:
        deg -= 360
    while deg <= -180:
        deg += 360
    return deg


def calculate_relative_angle(player_x, player_y, player_angle, target_x, target_y):
    """플레이어 기준 타겟의 상대적 각도 계산"""
    # 타겟 방향 벡터
    dx = target_x - player_x
    dy = target_y - player_y

    # 타겟까지의 각도 (라디안)
    target_angle_rad = math.atan2(dy, dx)
    target_angle_deg = math.degrees(target_angle_rad)

    # 플레이어 시점 기준 상대 각도
    relative_angle = normalize_angle_deg(target_angle_deg - player_angle)

    return relative_angle


def calculate_distance(x1, y1, x2, y2):
    """두 점 사이의 거리 계산"""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def get_all_objects_info(objects, player_x=0, player_y=0, debug_detail=False):
    """모든 오브젝트 정보를 추출하는 함수"""
    objects_info = []
    enemy_objects = []
    
    if objects is None:
        return objects_info
    
    # 첫 번째 오브젝트의 속성 출력 (디버깅용)
    if len(objects) > 0 and debug_detail:
        print(f"[DEBUG] 오브젝트 속성 목록: {dir(objects[0])}")
        # 첫 번째 오브젝트의 모든 속성값 출력
        print("\n[DEBUG] 첫 번째 오브젝트 모든 속성값:")
        for attr in dir(objects[0]):
            if not attr.startswith('__'):
                try:
                    value = getattr(objects[0], attr)
                    print(f"   - {attr}: {value}")
                except Exception as e:
                    print(f"   - {attr}: [에러: {e}]")
    
    # 적 오브젝트 이름 목록
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
        "DoomPlayer"  # 다른 플레이어도 포함
    ]
    
    # 모든 오브젝트 정보 추출
    for obj in objects:
        try:
            # 아이템 제외
            if hasattr(obj, "type") and obj.type == 1:  # type 1은 아이템
                continue
                
            # 기본 정보 추출
            obj_info = {
                "id": obj.id,
                "position": (obj.position_x, obj.position_y, obj.position_z),
                "pitch": obj.pitch,
                "angle": obj.angle,
                "name": getattr(obj, "name", f"Object_{obj.id}"),
                "type": getattr(obj, "type", 0)
            }
            
            # 특정 ID를 가진 플레이어는 항상 죽은 상태로 처리
            # 예: ID가 112인 플레이어
            if obj.id == 112:
                obj_info["is_dead"] = True
                if debug_detail:
                    print(f"[INFO] 특정 ID({obj.id})를 가진 플레이어를 죽은 상태로 처리합니다.")
            
            # 이름에 "Dead"가 포함된 경우 죽은 상태로 설정
            if "Dead" in obj_info["name"]:
                obj_info["is_dead"] = True
            
            # 서버 호스트 플레이어 필터링 (ServerGhost, Host 등)
            if obj_info["name"] in ["ServerGhost", "Host"]:
                if debug_detail:
                    print(f"[INFO] 서버 호스트 플레이어 감지됨: {obj_info['name']}, ID={obj_info['id']}")
                obj_info["is_server_host"] = True
                obj_info["is_dead"] = True  # 서버 호스트는 표시하지 않음
            
            # DoomPlayer 객체일 경우 이름에 번호 추가 및 추가 디버깅
            if obj_info["name"] == "DoomPlayer":
                # 플레이어가 투명한지 확인 (서버 호스트일 가능성)
                is_invisible = False
                
                # 다양한 투명 감지 방법 시도
                if hasattr(obj, "is_visible") and not obj.is_visible:
                    is_invisible = True
                elif hasattr(obj, "visible") and not obj.visible:
                    is_invisible = True
                elif hasattr(obj, "alpha") and obj.alpha < 0.5:  # 투명도가 낮은 경우
                    is_invisible = True
                
                # 위치가 (0,0,0)에 가까운 플레이어는 보통 서버 플레이어
                if abs(obj.position_x) < 1 and abs(obj.position_y) < 1 and abs(obj.position_z) < 1:
                    is_invisible = True
                    if debug_detail:
                        print(f"[INFO] 원점 근처의 플레이어 감지됨: ID={obj_info['id']}, 위치={obj_info['position']}")
                
                if is_invisible:
                    obj_info["is_server_host"] = True
                    obj_info["is_dead"] = True  # 서버 호스트는 표시하지 않음
                    if debug_detail:
                        print(f"[INFO] 투명한 플레이어 감지됨: ID={obj_info['id']}")
                
                # 플레이어 번호 추출 시도
                if hasattr(obj, "player_number"):
                    obj_info["player_number"] = obj.player_number
                    obj_info["name"] = f"Player{obj.player_number}"
                    if debug_detail:
                        print(f"[INFO] 플레이어 번호: {obj.player_number}")
                else:
                    obj_info["name"] = f"Player_{obj.id}"
            
            # 추가 속성 확인 및 추출
            if hasattr(obj, "health"):
                obj_info["health"] = obj.health
                # 플레이어 상태도 추출 (살아있는지 여부)
                obj_info["is_dead"] = obj.health <= 0
            
            # 거리 계산
            dx = obj.position_x - player_x
            dy = obj.position_y - player_y
            distance = math.sqrt(dx*dx + dy*dy)
            obj_info["distance"] = distance
            
            # 적 오브젝트 분류 (살아있는 적만 포함)
            if hasattr(obj, "name") and any(enemy in obj.name for enemy in enemy_names):
                # 살아있는 적 또는 플레이어만 ESP에 표시
                if not hasattr(obj, "health") or obj.health > 0:
                    enemy_objects.append(obj_info)
                else:
                    # 죽은 적은 리스트에 추가하지 않거나, 상태 표시를 위해 추가
                    obj_info["is_dead"] = True
                    enemy_objects.append(obj_info)
            
            objects_info.append(obj_info)
        except Exception as e:
            print(f"[ERROR] 오브젝트 정보 추출 중 오류: {e}")
    
    # 적 오브젝트 정보 출력
    if debug_detail:
        print(f"\n[DEBUG] 감지된 총 오브젝트 수: {len(objects_info)}")
        print(f"[DEBUG] 감지된 적 오브젝트 수: {len(enemy_objects)}")
    
    # 적 오브젝트 정보 출력 (거리순 정렬)
    enemy_objects.sort(key=lambda x: x["distance"])
    
    return enemy_objects



def world_to_screen(player_x, player_y, player_z,
                    player_angle_deg, player_pitch_deg,
                    obj_x, obj_y, obj_z,
                    screen_width, screen_height,
                    fov_deg=90.0):
    """
    플레이어(px, py, pz)와 오브젝트(ox, oy, oz)의 z좌표 차이를 이용해
    화면 좌표 (screen_x, screen_y)를 간단히 추정해 준다.
    
    - 회전은 Yaw(수평 각도)만 반영.
    - Pitch(상하 시야)는 고려하지 않고, z축 차이만으로 수직 화면 좌표를 조정.
    - localX <= 0(뒤쪽)이면 None 반환해서 '화면 뒤'로 간주.
    """

    # 1) 플레이어->오브젝트 상대좌표
    dx = obj_x - player_x
    dy = obj_y - player_y
    dz = obj_z - player_z  # 높이 차이

    # 2) Yaw(수평 각도) 회전
    yaw = math.radians(player_angle_deg)
    

    # localX : 전후방(카메라 축), localY : 좌우방
    localX = dx * math.cos(yaw) + dy * math.sin(yaw)
    # 아래 식에서 부호가 기존과 다르다면 -(...) 부분 조정
    localY = -(-dx * math.sin(yaw) + dy * math.cos(yaw))

    # 뒤쪽(localX <= 0)은 화면 표시 안 함
    if localX <= 0:
        return None
    
    # 3) 가로 FOV에 따른 화면 X좌표
    half_fov = math.radians(fov_deg / 2.0)
    scale = (screen_width / 2) / math.tan(half_fov)
    screen_x = (screen_width / 2) + (localY * scale / localX)

    # 4) 세로 좌표는 z차이를 간단히 반영
    #
    #  - localX가 작을수록(가까울수록) 실제로는 더 크게 보여야 하므로
    #    screen_y도 dz / localX에 비례하도록 잡는다.
    #  - 여기서는 수직 FOV도 똑같이 fov_deg로 가정(간단화).
    #  - '내 시야보다 위'일수록 화면 y값은 작아진다(=위로 올라감).
    

    # screen_y = (screen_height / 2) - (dz * scale / localX * 3.0)
    screen_y = (screen_height / 2)*0.9 - (math.radians(player_pitch_deg)+math.atan(dz/math.sqrt(dx**2+dy**2))) * scale 

    # 5) 화면 범위 밖이면 None 처리(선택)
    if not (0 <= screen_x <= screen_width and 0 <= screen_y <= screen_height):
        # 필요에 따라 None으로 처리하거나, 화면 경계에 클램핑할 수도 있음
        pass

    return int(screen_x), int(screen_y)


def draw_esp_overlay(frame, player_pos, player_angle, player_pitch, objects_info):
    """게임 화면에 ESP 정보 오버레이"""
    height, width = frame.shape[:2]
    overlay = frame.copy()

    # 플레이어 위치 정보
    px, py, pz = player_pos  # player_pos를 (x, y, z) 형태로 받음

    # 각 오브젝트 정보 처리
    for i, obj in enumerate(objects_info):
        # 죽은 플레이어는 표시하지 않음
        is_dead = obj.get("is_dead", False) or (obj.get("health", 100) <= 0)
        if is_dead:
            continue  # 죽은 객체는 건너뛰기
        
        obj_x, obj_y, obj_z = obj["position"]
        obj_name = obj["name"]
        obj_id = obj["id"]
        obj_angle = obj["angle"]
        distance = obj["distance"]

        # 색상 설정 - 기본은 빨간색 (BGR: 0, 0, 255)
        color = (0, 0, 255)

        # 간단한 3D 투영 (z차이 사용)
        screen_pos = world_to_screen(
            px, py, pz,               # 플레이어 위치 x,y,z
            player_angle,             # 플레이어 각도
            player_pitch,             # 플레이어 피치
            obj_x, obj_y, obj_z,      # 오브젝트 x,y,z
            width, height,
            fov_deg=90.0
        )
        
        if screen_pos is not None:
            sx, sy = screen_pos
            # 거리에 따라 표시 크기 조정 (죽은 경우 더 작게 표시)
            size = max(3, int(80 / (1 + distance / 200)))
            if is_dead:
                size = max(2, size // 2)  # 죽은 경우 크기 감소
            
            # 원 그리기
            cv2.circle(overlay, (sx, sy), size, color, 2)
            
            # 상태 텍스트 설정
            status_text = ""
            if is_dead:
                status_text = " DEAD"
            elif "health" in obj:
                status_text = f" HP:{obj['health']}"
                
            # 거리 및 상태 표시
            cv2.putText(
                overlay,
                f"{distance:.0f}" + status_text,
                (sx - 20, sy - size - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )
            
            # 오브젝트 이름 표시
            cv2.putText(
                overlay,
                f"{obj_name}",
                (sx - 20, sy + size + 15),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

    # 오버레이 적용 (70% 투명도)
    alpha = 0.7
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)

    return frame


def save_episode(obs_list, map_list, measurements_list, location_list, action_list, done_list, num_episodes, writer):
    # Convert lists to numpy arrays and transpose as needed.
    obs_array = np.stack(obs_list)  # [T, H, W, C]
    obs_array = np.transpose(obs_array, (0, 3, 1, 2))  # [T, C, H, W]

    map_array = np.stack(map_list)
    map_array = np.transpose(map_array, (0, 3, 1, 2))

    measurements_array = np.stack(measurements_list)
    location_array = np.stack(location_list)
    action_array = np.stack(action_list)
    done_array = np.array(done_list)

    # print(f"obs_array: {obs_array.shape}")
    # print(f"map_array: {map_array.shape}")
    # print(f"measurements_array: {measurements_array.shape}")
    # print(f"location_array: {location_array.shape}")
    # print(f"action_array: {action_array.shape}")
    # print(f"done_array: {done_array.shape}")

    sample = {
        "__key__": f"ep{num_episodes:06d}",
        "obs.npy": obs_array,
        "map.npy": map_array,
        "measurements.npy": measurements_array,
        "location.npy": location_array,
        "action.npy": action_array,
    }
    writer.write(sample)
    print(f"[INFO] Saved episode {num_episodes} with {len(obs_list)} steps")

def rotate_and_resize(image, angle, output_size=(360, 360), center_coord=None):
    """이미지를 회전하고 새 크기로 조정하는 함수
    
    Args:
        image: 회전할 이미지
        angle: 회전 각도(도)
        output_size: 출력 이미지 크기 (width, height)
        center_coord: 회전 중심 좌표 (기본값=이미지 중앙)
        
    Returns:
        회전되고 크기가 조정된 이미지
    """
    h, w = image.shape[:2]
    
    # 회전 중심이 지정되지 않은 경우 이미지 중앙을 사용
    if center_coord is None:
        center = (w // 2, h // 2)
    else:
        center = center_coord
    
    # 회전 행렬 계산 (이미지 좌표계에서는 각도를 음수로 변환해야 함)
    rotation_matrix = cv2.getRotationMatrix2D(center, -angle, 1.0)
    
    # 회전된 이미지 계산
    rotated = cv2.warpAffine(image, rotation_matrix, (w, h), 
                            flags=cv2.INTER_LINEAR, 
                            borderMode=cv2.BORDER_CONSTANT, 
                            borderValue=(0, 0, 0))
    
    # 출력 크기로 조정
    resized = cv2.resize(rotated, output_size, interpolation=cv2.INTER_LINEAR)
    
    return resized
