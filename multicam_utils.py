"""
multicam_utils.py
マルチカメラ生成のための数学ユーティリティ関数。
FOV計算、距離補正、線形補間、Movement分割を提供。
"""

import math

# ============================================================
# Configuration (共有定数)
# ============================================================
RESOLUTION_W = 1920
RESOLUTION_H = 1080
SLIT_WIDTH = 6          # Pixels between camera views
OFF_SCREEN_X = 5000     # Park inactive cameras off-screen
TILING_FOV = 10.0       # 各カメラの固定FOV（度）。歪み防止のため10°以下を推奨


# ============================================================

def calculate_look_at_rotation(cam_pos, target_pos={"x": 0, "y": 1.7, "z": 0}):
    """
    Computes the Euler rotation (Pitch, Yaw) required for a camera at `cam_pos` 
    to look directly at `target_pos`.

    The coordinate system assumes:
    - Y-up (Standard Unity)
    - Z-forward (Standard Unity)
    
    Args:
        cam_pos (dict): Camera position {"x": float, "y": float, "z": float}
        target_pos (dict, optional): Target position. Defaults to {"x": 0, "y": 1.7, "z": 0} (Avatar Head/Chest).

    Returns:
        dict: Rotation {"x": pitch, "y": yaw, "z": 0} in degrees.
              Pitch is positive for looking down (X-axis rotation).
              Yaw is rotation around Y-axis.
    """
    dx = target_pos["x"] - cam_pos["x"]
    dy = target_pos["y"] - cam_pos["y"]
    dz = target_pos["z"] - cam_pos["z"]
    
    # 距離 (水平、全距離)
    dist_h = math.sqrt(dx*dx + dz*dz)
    dist_3d = math.sqrt(dx*dx + dy*dy + dz*dz)
    
    if dist_3d < 0.001:
        return {"x":0, "y":0, "z":0}

    # Yaw (Y-axis rotation)
    # Unity: Atan2(x, z) gives angle from Z-axis (Forward).
    # dx, dz. 
    # Normal math: atan2(y, x).
    # Unity Yaw: deg(atan2(dx, dz)).
    yaw = math.degrees(math.atan2(dx, dz))
    
    # Pitch (X-axis rotation)
    # Look down = Positive X ? 
    # dy is height difference.
    # sin(pitch) = -dy / dist ?
    # Usually Pitch is angle from unknown to Y?
    # tan(pitch) = -dy / dist_h.
    # Look down (dy < 0) -> Pitch > 0.
    # So pitch = atan2(-dy, dist_h)
    pitch = math.degrees(math.atan2(-dy, dist_h))
    
    return {"x": pitch, "y": yaw, "z": 0}
# ============================================================
# FOV & Distance
# ============================================================

def get_hfov(v_fov):
    """Vertical FOV → Horizontal FOV (度)"""
    aspect = RESOLUTION_W / RESOLUTION_H
    return 2 * math.degrees(math.atan(math.tan(math.radians(v_fov / 2)) * aspect))


def calc_distance_scale(original_fov, target_fov):
    """
    Calculates the distance multiplier required to maintain the subject's apparent size
    when narrowing the FOV.
    
    Logic:
        To keep the subject size constant on screen, the ratio of distance to view-plane size must be adjusted.
        scale = tan(original_fov / 2) / tan(target_fov / 2)
        
    Args:
        original_fov (float): The FOV defined in the SongScript (e.g., 60).
        target_fov (float): The target FOV for the grid tile (e.g., 10).
        
    Returns:
        float: Scale factor (e.g., ~6.6 for 60->10).
    """
    orig_half = math.radians(original_fov / 2)
    tile_half = math.radians(target_fov / 2)
    if math.tan(tile_half) == 0:
        return 1.0
    return math.tan(orig_half) / math.tan(tile_half)


def scale_position(pos, scale_factor, origin=(0.0, 0.0, 0.0)):
    """
    Scales the camera position distance from the origin on the XZ plane.
    Y-coordinate (height) is NOT scaled to maintain camera height relative to the subject.
    
    Args:
        pos (dict): Input position {"x", "y", "z"}.
        scale_factor (float): Distance multiplier.
        origin (tuple): (x, y, z) origin for scaling center.
        
    Returns:
        dict: New position with scaled X and Z.
    """
    return {
        "x": origin[0] + (pos.get("x", 0) - origin[0]) * scale_factor,
        "y": pos.get("y", 0),
        "z": origin[2] + (pos.get("z", 0) - origin[2]) * scale_factor,
    }


# ============================================================
# Linear Interpolation
# ============================================================

def lerp(a, b, t):
    """線形補間: a から b へ t (0.0〜1.0) の割合で補間"""
    return a + (b - a) * t


def rotate_position_around_origin(pos, angle_degrees, origin={"x": 0.0, "y": 1.5, "z": 0.0}):
    """
    指定された原点を中心にXZ平面上で位置を回転させます。
    
    Args:
        pos: 回転させる位置 dict (x, y, z)
        angle_degrees: 回転角（度）。Y軸周りで左手系(Unity)の計算。
        origin: 回転の中心点。
    """
    if angle_degrees == 0.0:
        return pos.copy() # 原本を変更しないようにコピーを返す
        
    angle_rad = math.radians(angle_degrees)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    
    x = pos.get("x", 0.0)
    z = pos.get("z", 0.0)
    ox = origin.get("x", 0.0)
    oz = origin.get("z", 0.0)
    
    dx = x - ox
    dz = z - oz
    
    # Unity (左手系: Z+が奥、X+が右、Y+が上) では、
    # Y軸周りの正の回転(Yaw)は、X軸側からZ軸側への回転に相当
    new_dx = dx * cos_a + dz * sin_a
    new_dz = -dx * sin_a + dz * cos_a
    
    new_pos = pos.copy()
    new_pos["x"] = ox + new_dx
    new_pos["z"] = oz + new_dz
    return new_pos


def lerp_pos(start, end, t):
    """StartPos/EndPos の線形補間"""
    return {
        "x": lerp(start.get("x", 0), end.get("x", 0), t),
        "y": lerp(start.get("y", 0), end.get("y", 0), t),
        "z": lerp(start.get("z", 0), end.get("z", 0), t),
        "FOV": lerp(start.get("FOV", 60), end.get("FOV", 60), t),
    }


def lerp_rot(start, end, t):
    """StartRot/EndRot の線形補間"""
    return {
        "x": lerp(start.get("x", 0), end.get("x", 0), t),
        "y": lerp(start.get("y", 0), end.get("y", 0), t),
        "z": lerp(start.get("z", 0), end.get("z", 0), t),
    }


# ============================================================
# Movement Subdivision
# ============================================================

def subdivide_movements(movements, bpm, beats_per_sub=1, schedule=None):
    """
    Splits long movements into smaller chunks based on music beats, and 
    precisely cuts them at effect schedule boundaries to avoid missing fast effects.
    
    Args:
        movements (list): List of movement dictionaries.
        bpm (float): Beats per minute of the song.
        beats_per_sub (int): Target duration in beats (default 1).
        schedule (list, optional): Effect schedule.
        
    Returns:
        list: A new list of movements where each movement's duration is limited.
        Positions/Rotations are interpolated linearly.
    """
    beat_duration = 60.0 / bpm * beats_per_sub
    subdivided = []
    
    cut_times = set()
    if schedule:
        for entry in schedule:
            cut_times.add(entry["start"])
            if entry.get("end") is not None and entry["end"] != 999999.0:
                cut_times.add(entry["end"])
    cut_times = sorted(list(cut_times))
    
    current_time = 0.0
    
    for m in movements:
        dur = m.get("Duration", 1.0)
        delay = m.get("Delay", 0.0)
        
        current_time += delay
        end_time = current_time + dur
        
        # Determine exact chunk lengths by splitting at effect boundaries
        chunk_durations = []
        last_split_time = current_time
        for ct in cut_times:
            if current_time < ct < end_time:
                # To prevent micro-chunks due to float precision, only split if > 0.001s
                if (ct - last_split_time) > 0.001:
                    chunk_durations.append(ct - last_split_time)
                    last_split_time = ct
        if (end_time - last_split_time) > 0.001:
            chunk_durations.append(end_time - last_split_time)
        
        if not chunk_durations:
            chunk_durations = [dur]
            
        start_pos = m.get("StartPos", {"x": 0, "y": 0, "z": 0, "FOV": 60})
        end_pos = m.get("EndPos", start_pos.copy())
        start_rot = m.get("StartRot", {"x": 0, "y": 0, "z": 0})
        end_rot = m.get("EndRot", start_rot.copy())
        
        # Process each exact-boundary chunk
        chunk_start_t_fraction = 0.0
        for chunk_idx, chunk_dur in enumerate(chunk_durations):
            # For each chunk, apply beat subdivisions
            n_subs = max(1, round(chunk_dur / beat_duration))
            sub_duration = chunk_dur / n_subs
            
            chunk_fraction_len = chunk_dur / max(dur, 0.0001)
            
            for i in range(n_subs):
                t0 = chunk_start_t_fraction + (i / n_subs) * chunk_fraction_len
                t1 = chunk_start_t_fraction + ((i + 1) / n_subs) * chunk_fraction_len
                
                sub_m = {
                    "StartPos": lerp_pos(start_pos, end_pos, t0),
                    "StartRot": lerp_rot(start_rot, end_rot, t0),
                    "EndPos": lerp_pos(start_pos, end_pos, t1),
                    "EndRot": lerp_rot(start_rot, end_rot, t1),
                    "Duration": round(sub_duration, 4),
                    "Delay": delay if (chunk_idx == 0 and i == 0) else 0.0,
                    "EaseTransition": m.get("EaseTransition", True) if (chunk_idx == 0 and i == 0) or (chunk_idx == len(chunk_durations)-1 and i == n_subs - 1) else False,
                }
                
                if "VisibleObject" in m:
                    sub_m["VisibleObject"] = m["VisibleObject"]
                
                if chunk_idx == 0 and i == 0:
                    for key in ("TurnToHead", "TurnToHeadHorizontal",
                                "StartHeadOffset", "EndHeadOffset", "CameraEffect"):
                        if key in m:
                            sub_m[key] = m[key]
                
                subdivided.append(sub_m)
            
            chunk_start_t_fraction += chunk_fraction_len
            
        current_time = end_time
    
    return subdivided


def get_state_at_time(movements, target_time):
    """
    Retrieves the interpolated camera state at a specific absolute time.
    
    Args:
        movements (list): Movements with 'AbsStart' and 'AbsEnd' keys.
        target_time (float): The time to sample.
        
    Returns:
        dict: Interpolated state containing keys: 
              x, y, z, FOV, rot_x, rot_y, rot_z.
              Returns default (all zeros) if time is out of range.
    """
    if not movements:
        return {"x":0,"y":0,"z":0,"FOV":60, "rot_x":0,"rot_y":0,"rot_z":0}

    # target_timeが負の場合: 最初の状態
    if target_time < 0:
        m0 = movements[0]
        p = m0.get("StartPos", {})
        r = m0.get("StartRot", {})
        return {
            "x": p.get("x", 0), "y": p.get("y", 0), "z": p.get("z", 0), "FOV": p.get("FOV", 60),
            "rot_x": r.get("x", 0), "rot_y": r.get("y", 0), "rot_z": r.get("z", 0)
        }
    
    current_time = 0.0
    
    for m in movements:
        dur = m.get("Duration", 1.0)
        delay = m.get("Delay", 0.0)
        
        # DelayのあるMovementの開始時刻
        # start_wait: Delay開始（前の動き終了）
        # start_move: Delay終了・動き開始
        start_wait = current_time
        start_move = start_wait + delay
        end_move = start_move + dur
        
        # Delay期間: 直前の状態を維持 (StartPos)
        if start_wait <= target_time < start_move:

            p = m.get("StartPos", {})
            r = m.get("StartRot", {})
            return {
                "x": p.get("x", 0), "y": p.get("y", 0), "z": p.get("z", 0), "FOV": p.get("FOV", 60),
                "rot_x": r.get("x", 0), "rot_y": r.get("y", 0), "rot_z": r.get("z", 0)
            }
        
            
        # Movement期間: 線形補間
        if start_move <= target_time < end_move:
            progress = (target_time - start_move) / dur if dur > 0 else 1.0
            
            p_start = m.get("StartPos", {})
            p_end = m.get("EndPos", {})
            r_start = m.get("StartRot", {})
            r_end = m.get("EndRot", {})
            
            pos = lerp_pos(p_start, p_end, progress)
            rot = lerp_rot(r_start, r_end, progress)
            
            return {
                "x": pos["x"], "y": pos["y"], "z": pos["z"], "FOV": pos["FOV"],
                "rot_x": rot["x"], "rot_y": rot["y"], "rot_z": rot["z"]
            }
        
        current_time = end_move

    # 全期間を超えている場合: 最後の状態
    last = movements[-1]
    p = last.get("EndPos", {})
    r = last.get("EndRot", {})
    return {
        "x": p.get("x", 0), "y": p.get("y", 0), "z": p.get("z", 0), "FOV": p.get("FOV", 60),
        "rot_x": r.get("x", 0), "rot_y": r.get("y", 0), "rot_z": r.get("z", 0)
    }
