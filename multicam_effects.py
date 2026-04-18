"""
multicam_effects.py
エフェクトスケジュールの読み込み、時間ベース検索、Visible判定を提供。

EffectScript JSON フォーマット:
{
    "bpm": 170,
    "beats_per_sub": 1,
    "schedule": [
        {"start": 0, "end": 30, "cameras": 9, "effect": "mosaic-blink"},
        {"start": 30, "end": 60, "cameras": 1},
        {"start": 60, "end": null, "cameras": 9, "effect": "all-visible"}
    ]
}
"""

import json
import sys


def load_effect_script(path):
    """
    EffectScript JSON を読み込み、正規化して返す。
    
    Returns:
        dict: {"bpm": float, "beats_per_sub": int, "schedule": [...]}
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if "bpm" not in data:
        print("ERROR: EffectScript must contain 'bpm' field.")
        sys.exit(1)
        
    if data["bpm"] <= 0:
        print(f"ERROR: EffectScript BPM must be positive (got {data['bpm']}).")
        sys.exit(1)
        
    if "schedule" not in data or not data["schedule"]:
        print("ERROR: EffectScript must contain non-empty 'schedule' array.")
        sys.exit(1)
    
    # 開始時間でソート
    normalize_schedule(data["schedule"])
    return data


def normalize_schedule(schedule):
    """
    スケジュールリストを正規化する（end=None -> 999999.0, sort by start）。
    In-place で変更する。
    """
    for entry in schedule:
        if entry.get("end") is None:
            entry["end"] = 999999.0
    
    schedule.sort(key=lambda e: e["start"])


def find_effect_for_time(schedule, abs_time):
    """
    絶対時間に対応するスケジュールエントリを返す。
    該当なしの場合は {"effect": "all-visible", "cameras": 1} を返す
    （スケジュール範囲外 = 1カメラ表示）。
    
    Args:
        schedule: スケジュールエントリのリスト
        abs_time: 絶対秒数
    
    Returns:
        dict: マッチしたスケジュールエントリ (重なった場合は後のエントリを優先)
    """
    matched = {"effect": "all-visible", "cameras": 1}
    for entry in schedule:
        if entry["start"] <= abs_time < entry["end"]:
            matched = entry
    return matched


def apply_window_visibility(effect_entry, cam_i, grid_size, movement_idx):
    """
    エフェクトエントリに基づいて、カメラの表示/非表示を決定。
    
    Args:
        effect_entry: スケジュールエントリ dict
        cam_i: カメラインデックス (0-based)
        grid_size: グリッドの辺サイズ (2 or 3)
        movement_idx: 現在のMovementインデックス
    
    Returns:
        bool: True=表示, False=非表示
    """
    effect = effect_entry.get("effect", "all-visible")
    
    if effect == "mosaic-blink":
        row = cam_i // grid_size
        col = cam_i % grid_size
        checker = (row + col) % 2
        return checker == (movement_idx % 2)
    
    if effect == "mosaic-shuffle":
        # Randomly hide/show cameras based on a density parameter
        density = effect_entry.get("density", 0.5) # probability of being visible
        import random
        # Seed by movement and camera index to ensure deterministic blinking
        seed = (movement_idx * 1000) + cam_i
        rd = random.Random(seed)
        return rd.random() < density

    # For panoptic-view (9 cameras), cameras 1-8 surround camera 0 (center)
    # They should all be visible by default unless specified otherwise.
    
    # all-visible, chronos-cascade, dimension-roulette, split-view, surround-view, panoptic-view, outline-fill, random-outline-fill 等
    return True



def get_required_grids(schedule):
    """
    スケジュールで使用されている全てのカメラ台数（の平方根=グリッドサイズ）のセットを返す。
    スケジュール範囲外のデフォルトは grid_size=1 (1台=フルスクリーン)。
    
    Returns:
        set: {1, 2, 3, ...} 
             1=1台, 2=4台, 3=9台, 4=16台
    
    Note:
        - スケジュールに "cameras" フィールドがないエントリは 9台 (3x3) として扱う
        - "cameras": 1 は 1台表示（エフェクトなし）として使用可能
        - スケジュール範囲外の時間帯は常に 1台表示 (grid_size=1)
    """
    grids = set()
    grids.add(1)  # 範囲外デフォルト: 常に1カメラを必要グリッドに含める
    for entry in schedule:
        cams = entry.get("cameras", 9)  # エントリのデフォルト9台
        # cameras 数から grid_size (平方根) を算出
        # 1->1, 4->2, 9->3, 16->4
        g = int(cams ** 0.5)
        grids.add(g)
    
    return grids


def get_chronos_delay(effect_entry, row, col, grid_size):
    """
    Chronos Cascade 用の遅延時間を計算。
    
    Args:
        effect_entry: EffectScriptのエントリ
        row: カメラの行インデックス (0-based)
        col: カメラの列インデックス (0-based)
        grid_size: グリッドサイズ (e.g. 3)
        
    Returns:
        float: 遅延時間 (秒)
    """
    effect_name = effect_entry.get("effect", "all-visible")
    
    if effect_name != "chronos-cascade":
        return 0.0
    
    unit_delay = effect_entry.get("delay", 0.0)
    
    # 将来的に方向(direction)を追加するならここで分岐
    # 今はデフォルトで水平方向 (左->右)
    
    return col * unit_delay


def get_radial_chronos_delay(effect_entry, row, col, grid_size):
    """
    Radial Chronos (放射状遅延) 用の遅延時間を計算。
    グリッド中心からの距離に応じて遅延させる。
    
    Args:
        effect_entry: EffectScriptのエントリ
        row: カメラの行インデックス (0-based)
        col: カメラの列インデックス (0-based)
        grid_size: グリッドサイズ (e.g. 3)
        
    Returns:
        float: 遅延時間 (秒)
    """
    effect_name = effect_entry.get("effect", "all-visible")
    
    if effect_name != "radial-chronos":
        return 0.0
        
    unit_delay = effect_entry.get("delay", 0.0)
    
    # 中心座標 (0-based index の中心)
    center = (grid_size - 1) / 2.0
    
    # 中心からのユークリッド距離
    dist = ((row - center) ** 2 + (col - center) ** 2) ** 0.5
    
    return dist * unit_delay


def get_diagonal_wave_delay(effect_entry, row, col, grid_size):
    """
    Diagonal Wave (斜め波) 用の遅延時間を計算。
    左上(0,0)から右下に向かって遅延が増加。
    
    Args:
        effect_entry: EffectScriptのエントリ
        row: カメラの行インデックス
        col: カメラの列インデックス
        grid_size: グリッドサイズ
        
    Returns:
        float: 遅延時間 (秒)
    """
    effect_name = effect_entry.get("effect", "all-visible")
    
    if effect_name != "diagonal-wave":
        return 0.0
        
    unit_delay = effect_entry.get("delay", 0.0)
    
    # Simple sum of indices (Manhattan distance from top-left)
    dist = row + col
    
    return dist * unit_delay


def get_dimension_roulette_params(effect_entry, cam_i, movement_idx):
    """
    Dimension Roulette 用のランダムパラメータを生成。
    決定論的（同じ入力なら同じ結果）にするため、ハッシュを使用。
    
    Returns:
        dict: {"fov_mul": float, "rot_z": float}
    """
    if effect_entry.get("effect") != "dimension-roulette":
        return {"fov_mul": 1.0, "rot_z": 0.0}
    
    # シンプルなハッシュ
    seed = (movement_idx * 100) + cam_i
    import random
    rd = random.Random(seed)
    
    # FOV倍率: 0.8 〜 1.5
    fov_mul = rd.uniform(0.8, 1.5)
    
    # Roll回転: -15度 〜 +15度
    rot_z = rd.uniform(-15.0, 15.0)
    
    return {"fov_mul": fov_mul, "rot_z": rot_z}


def get_static_outline_params(effect_entry):
    """
    静的な Outline Effect のパラメータを生成 (Symmetry View などで片側だけ強調する用途)。
    
    Args:
        effect_entry: スケジュールエントリ
        
    Returns:
        dict: MovementScriptの "CameraEffect" オブジェクト
    """
    color_line = effect_entry.get("color_line", {"r": 0.0, "g": 0.0, "b": 0.0})
    color_bg = effect_entry.get("color_bg", {"r": 1.0, "g": 1.0, "b": 1.0})
    
    return {
        "enableOutlineEffect": True,
        "StartOutlineEffect": {
            "outlineEffectOnly": 1.0,
            "outlineColor": color_line,
            "outlineBackgroundColor": color_bg
        },
        "EndOutlineEffect": {
            "outlineEffectOnly": 1.0,
            "outlineColor": color_line,
            "outlineBackgroundColor": color_bg
        }
    }


def get_outline_effect_params(effect_entry, cam_i, grid_size, time_since_start, bpm):
    """
    Outline Effect (Fill/Wipe) 用のパラメータを生成。
    
    Args:
        effect_entry: スケジュールエントリ
        cam_i: カメラID (0-based)
        grid_size: グリッドサイズ
        time_since_start: エフェクト開始からの経過時間(秒)
        bpm: 曲のBPM
        
    Returns:
        dict: MovementScriptの "CameraEffect" オブジェクト (None if effect is not active)
    """
    effect_name = effect_entry.get("effect")
    if effect_name not in ("outline-fill", "outline-wipe", "random-outline-fill"):
        return None

    # パラメータ取得
    # delay_beats: カメラごとの開始遅延 (ビート単位)
    transition_beats = effect_entry.get("duration_beats", 4) # 全体のアニメーションにかけるビート数目安？ 
    # いや、Wave状にするなら、Stepごとの遅延を定義すべき。
    # default: 1 beat per step
    step_delay = effect_entry.get("step_delay", 1.0) 
    
    # 色設定 (Default: Black Line on White BG)
    color_line = effect_entry.get("color_line", {"r": 0.0, "g": 0.0, "b": 0.0})
    color_bg = effect_entry.get("color_bg", {"r": 1.0, "g": 1.0, "b": 1.0})
    
    total_cameras = grid_size * grid_size
    trigger_beat = 0.0
    
    if effect_name == "random-outline-fill":
        # Duration for the whole random fill process
        effect_duration_beats = effect_entry.get("duration_beats", 4 * grid_size)
        # Random trigger order assignment
        # Seed must be deterministic per effect entry. Since an entry is uniquely defined by its start time in most cases, we can use that.
        seed_value = int(effect_entry.get("start", 0) * 1000)
        import random
        rd = random.Random(seed_value)
        # Generate a list of indices 0 to N-1 and shuffle them
        indices = list(range(total_cameras))
        rd.shuffle(indices)
        
        # Find the sequential position of THIS camera in the shuffled list
        sequential_order = indices.index(cam_i)
        
        # Assign uniformly distributed trigger times based on the order
        trigger_beat = (effect_duration_beats / total_cameras) * sequential_order
        
    else: # normal outline-fill / outline-wipe
        # 座標計算
        row = cam_i // grid_size
        col = cam_i % grid_size
        
        # Step Index (Diagonal: Top-Left to Bottom-Right)
        step_index = row + col
        
        # Trigger Beat
        trigger_beat = step_index * step_delay
    
    # Current Beat (Float)
    sec_per_beat = 60.0 / bpm
    current_beat = time_since_start / sec_per_beat
    
    # 状態判定
    # 1 beat かけて 0.0 -> 1.0 に遷移すると仮定
    # movement duration があるので、厳密には "StartVal -> EndVal" を決める
    # ここでは簡易的に「現在のビート」が遷移期間内かどうかで判定
    
    # duration of this single movement (assuming standard subdivision)
    # We don't have movement duration here, but we return Start/End state.
    # Logic:
    #   current_beat is the START of the movement.
    #   Let's assume movement duration is approx 1 beat (if sub=1).
    #   Actually we should probably control Start and End separately?
    #   But simplified logic:
    #   If current_beat < trigger: Start=0, End=0 (or 0->1 if closely approaching?)
    #   
    #   Better logic: Calculate value at T_start and T_end.
    #   But we only have T_start (current_beat). 
    #   This function calculates the props for the WHOLE movement.
    #   So we need to know the duration of the movement to calculate EndVal.
    #   
    #   Let's assume the calling side handles time? No, the caller passes `time_since_start`.
    #   We can assume the movement lasts for... we don't know exactly without passing duration.
    #   Let's add `duration` to args? Or assume short calculation.
    
    #   Wait, `outlineEffectOnly` is a float 0.0-1.0.
    #   Value(t) = clamp((t - trigger) / transition_duration, 0, 1)
    
    transit_duration_beats = 1.0 # 遷移にかかる時間(ビート)
    
    val_start = (current_beat - trigger_beat) / transit_duration_beats
    val_start = max(0.0, min(1.0, val_start))
    
    # End Value estimation
    # If the movement spans 1 beat, then End Value is value at (current + 1)
    # But we don't know duration.
    # However, for a "Fill" effect, once it starts filling, it usually completes.
    
    start_val = 0.0
    end_val = 0.0
    
    if current_beat < trigger_beat:
        # Before transition: 通常映像を表示（黒画面バグ回避のため None を返す）
        return None
    elif current_beat >= (trigger_beat + transit_duration_beats):
        # After transition (Filled or Wiped)
        if effect_name in ("outline-fill", "random-outline-fill"):
            start_val = 1.0
            end_val = 1.0
        else: # outline-wipe
            start_val = 0.0
            end_val = 0.0
    else:
        # In transition
        start_val = val_start
        # Force 1.0 at the end of the movement chunk to ensure the visual pops fully
        end_val = 1.0

    return {
        "enableOutlineEffect": True,
        "StartOutlineEffect": {
            "outlineEffectOnly": start_val,
            "outlineColor": color_line,
            "outlineBackgroundColor": color_bg
        },
        "EndOutlineEffect": {
            "outlineEffectOnly": end_val,
            "outlineColor": color_line,
            "outlineBackgroundColor": color_bg
        }
    }


def get_vortex_spin_rotation(effect_entry, current_time, row, col):
    """
    Vortex Spin 用の回転角(Z軸)を計算。
    
    Args:
        effect_entry: スケジュールエントリ
        current_time: 現在の絶対時間 (秒)
        row: カメラ行
        col: カメラ列
        
    Returns:
        float: Z軸回転角 (度)
    """
    if effect_entry.get("effect") != "vortex-spin":
        return 0.0
        
    speed = effect_entry.get("speed", 60.0) # deg/sec
    
    # Wave mode
    wave_delay = 0.0
    if effect_entry.get("mode") == "wave":
        # Simple wave: (row + col) * delay_factor (approx 0.2s)
        wave_delay = (row + col) * 0.2
    
    # Time-based rotation
    # Start Z
    t_target = current_time - wave_delay
    rotation = t_target * speed
    
    return rotation

def get_split_view_rotation_offset(effect_entry, col, grid_size):
    """
    Split View (Triptych) 用のY軸(Yaw)回転オフセットを計算。
    3列の場合: 左(-90), 中央(0), 右(+90) など。
    
    Args:
        effect_entry: スケジュールエントリ
        col: カメラ列 (0-based)
        grid_size: グリッドサイズ (前提として3を想定)
        
    Returns:
        float: Y軸回転角 (度)
    """
    if effect_entry.get("effect") != "split-view":
        return 0.0

    angle = effect_entry.get("angle", 90.0) # デフォルトで90度
    
    # 3列 (0, 1, 2) を前提として動作
    # col = 0 (Left) -> -angle
    # col = 1 (Center) -> 0
    # col = 2 (Right) -> +angle
    
    center_col = (grid_size - 1) / 2.0
    
    if col < center_col:
        return -angle
    elif col > center_col:
        return angle
    else:
        return 0.0

def get_surround_view_rotation_offset(effect_entry, cam_i, grid_size):
    """
    Surround View 用のY軸(Yaw)回転オフセットを計算。
    4台カメラ用: 0(正面), 1(右90), 2(背後180), 3(左-90)
    """
    if effect_entry.get("effect") != "surround-view":
        return 0.0
        
    if grid_size * grid_size != 4:
        return 0.0 # 4カメラグリッド以外では無効化するか、適宜割り当てる
        
    angles = [0.0, 90.0, 180.0, -90.0]
    return angles[cam_i % 4]

def get_panoptic_view_rotation_offset(effect_entry, cam_i, grid_size):
    """
    Panoptic View 用のY軸(Yaw)回転オフセットを計算。
    9台カメラ用:
    中央(cam 4) を正面(0度)とし、
    他の8台がアバターの周囲を45度刻みで囲む。
    """
    if effect_entry.get("effect") != "panoptic-view":
        return 0.0
        
    if grid_size * grid_size != 9:
        return 0.0
        
    # cam_i: 0-8
    # 4 is center -> 0 degrees
    if cam_i == 4:
        return 0.0
        
    # Mapping for the other 8 cameras
    # 0, 1, 2
    # 3, 4, 5
    # 6, 7, 8
    # We want them to circle around. Let's map them to 45 degree increments.
    # We can do this intuitively:
    # 1: 0 (Front, slightly offset? Or make center purely front, and others form the circle)
    # Actually, if 4 is Front (0), let's distribute 0,1,2,3,5,6,7,8 evenly in 360/8 = 45 degree increments.
    # Angles: 45, 90, 135, 180, -135, -90, -45, (0 is already taken by 4)
    # Let's map them to compass directions:
    # 0: -45 (Front-Left)
    # 1: 0 (Front) -> maybe overlapping with 4? Let's make 4 the sole front, and others space out.
    # Better: 8 cameras around = 45 deg each starting from 45.
    
    # 0: -135 (Back-Left)
    # 1: 180 (Back)
    # 2: 135 (Back-Right)
    # 3: -90 (Left)
    # 5: 90 (Right)
    # 6: -45 (Front-Left)
    # 7: 0 (Front-Top maybe? Since 4 is Front-Center. If they share Y rotation, they'll just stack vertically.
    #       Wait, offset_y is just rotation. If 4 and 7 both have 0, they both look front.
    #       But 7 is bottom row. It'll be looking up? (X rotation is separate).
    #       Let's just give them 45-degree rotational slicing around the Y axis.)
    
    mapping = {
        0: -135.0,
        1: 180.0,
        2: 135.0,
        3: -90.0,
        5: 90.0,
        6: -45.0,
        7: 0.0,   # Actually let's let 7 be 0.0 too, or maybe give it a slight offset? Let's just do 8 compass points.
        8: 45.0
    }
    return mapping.get(cam_i, 0.0)

