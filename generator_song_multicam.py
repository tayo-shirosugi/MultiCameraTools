"""
generator_song_multicam.py

SongScript.json を解析し、CameraPlus用のマルチカメラ設定(Profile)と動作スクリプト(MovementScript)を生成するツール。

[主な機能]
1. 動的グリッド切替:
   - 時間経過に合わせて 1x1, 2x2, 3x3, 4x4 のグリッド構成を切り替える。
   - マスターカメラ (cameraplus.json) の WindowControl 機能を使用して実現。

2. パノラマ・タイリング生成:
   - 指定されたグリッド数に合わせて FOV (視野角) を狭め (例: 60° -> 10°)、
     その分カメラを遠ざける「距離スケーリング」を自動適用。
   - 各カメラの回転角度を調整し、全体で一つの広い画角(80°程度)を構成するよう配置。
   - アバター(0, 1.5, 0)を常に注視する「強制LookAt」補正を適用。

3. エフェクト適用:
   - Chronos Cascade: 時間差をつけて波打つような動きを生成。
   - Dimension Roulette: ランダムなFOV/回転を付与してカオスな映像を作る。

[処理フロー]
1. 入力ファイルの読み込み (SongScript, EffectScript)
2. Movementの細分化 (subdivide): BPMに基づいて動きを細かく分割し、エフェクトの粒度を向上。
3. 必要グリッドの特定: EffectScriptのスケジュールから、作成すべきグリッドサイズ(例: 2x2, 3x3)をリストアップ。
4. グリッドごとの生成ループ:
   - Profile生成: 画面上の配置(WindowRect)を計算。スリット(隙間)も考慮。
   - Script生成: 各Movementの座標をスケール・回転補正して出力。
5. マスタースクリプト生成:
   - 曲の進行に合わせて、表示するカメラ(WindowControl)を切り替えるコマンドを生成。
"""

import os
import sys
import json
import argparse

from multicam_utils import (
    RESOLUTION_W, RESOLUTION_H, SLIT_WIDTH, OFF_SCREEN_X, TILING_FOV,
    get_hfov, calc_distance_scale, scale_position,
    subdivide_movements, get_state_at_time, rotate_position_around_origin, calculate_look_at_rotation,
)
from multicam_effects import (
    load_effect_script, find_effect_for_time, apply_window_visibility,
    get_required_grids, normalize_schedule, get_chronos_delay,
    get_dimension_roulette_params, get_radial_chronos_delay,
    get_outline_effect_params, get_diagonal_wave_delay, get_vortex_spin_rotation,
    get_split_view_rotation_offset, get_surround_view_rotation_offset,
    get_panoptic_view_rotation_offset
)


# ============================================================
# Main Generator
# ============================================================

def generate(input_path, grid_size, output_dir=None, song_name=None,
             effect_script=None):
    """
    SongScript.json を読み込み、grid_size x grid_size のマルチカメラスクリプトを生成するメイン処理。
    
    [引数]
    input_path (str): 元となる SongScript.json のパス。
    grid_size (int): デフォルトのグリッドサイズ（EffectScriptがない場合に使用）。
                     2なら2x2=4台、3なら3x3=9台。
    output_dir (str): 生成ファイルの出力先ディレクトリ。Noneなら入力ファイルの常駐ディレクトリに 'output' という名前で生成。
    song_name (str): 出力ファイル名のプレフィックス。Noneなら入力ファイル名を使用。
    effect_script (dict): load_effect_script() で読み込んだエフェクト定義データ。
    
    [戻り値]
    なし (ファイル生成のみ)
    """
    # Load input script
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            song_script = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: file not found: {input_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON format: {e}")
        sys.exit(1)
    
    source_movements = song_script.get("Movements", [])
    if not source_movements:
        print("ERROR: No Movements found in input file.")
        sys.exit(1)
    
    # EffectScript からBPM/スケジュールを取得
    schedule = []
    if effect_script is not None:
        bpm = effect_script["bpm"]
        beats_per_sub = effect_script.get("beats_per_sub", 1)
        schedule = effect_script.get("schedule", [])
        original_count = len(source_movements)
        source_movements = subdivide_movements(source_movements, bpm, beats_per_sub, schedule)
        print(f"Movement subdivision: {original_count} → {len(source_movements)} (BPM={bpm})")
        print(f"Effect schedule: {len(schedule)} entries")
    
    # 必要なグリッドサイズを特定 (デフォルトは引数のgrid_size)
    required_grids = {grid_size}
    if schedule:
        required_grids = get_required_grids(schedule)
        print(f"Required grids: {sorted(required_grids)} (from schedule)")
    else:
        print(f"Required grids: {sorted(required_grids)} (CLI default)")
    
    # Derive names
    if song_name is None:
        song_name = os.path.splitext(os.path.basename(input_path))[0]
    
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(input_path), "output")
    
    scripts_dir = os.path.join(output_dir, "Scripts")
    profiles_dir = os.path.join(output_dir, "Profiles", song_name)
    os.makedirs(scripts_dir, exist_ok=True)
    os.makedirs(profiles_dir, exist_ok=True)
    
    print(f"=== SongScript Multi-Camera Generator ===")
    print(f"Input:     {input_path}")
    print(f"Grids:     {sorted(required_grids)}")
    print(f"Movements: {len(source_movements)}")
    print(f"Output:    {output_dir}")
    print()
    
    # Pre-calculate the total expected duration of the track
    expected_total_duration = sum(m.get("Duration", 0.0) for m in source_movements)
    print(f"Expected Duration: {expected_total_duration:.4f}s")
    
    # デフォルトのグリッドサイズ (計算グリッドサイズが見つからない場合のフォールバック)
    default_grid_size = max(required_grids) if required_grids else grid_size
    
    # ============================================================
    # PASS 1: 各グリッドサイズのカメラ配置 & プロファイル生成
    # ============================================================
    
    # 全グリッドの全カメラ情報を保持
    # key: filename (e.g. "Cam_Grid3_01.json"), value: {x, y, grid_size, cam_index}
    all_camera_info = {}
    
    for g_size in required_grids:
        num_cams = g_size * g_size
        print(f"Generating grid {g_size}x{g_size} ({num_cams} cameras)...")
        
        # 1つのスリット幅を考慮したセルサイズ計算（スリットはセル中心に配置）
        full_w = RESOLUTION_W // g_size
        full_h = RESOLUTION_H // g_size
        
        # スリット分だけ縮小
        w = full_w - SLIT_WIDTH
        h = full_h - SLIT_WIDTH
        
        for cam_i in range(num_cams):
            # Row/Col (0-based)
            r = cam_i // g_size
            c = cam_i % g_size
            
            # 座標計算 (左下原点, セル中央配置)
            # sx = (col * full_w) + (SLIT_WIDTH // 2)
            # sy = ((g_size - 1 - r) * full_h) + (SLIT_WIDTH // 2)  <-- row0 is top
            sx = (c * full_w) + (SLIT_WIDTH // 2)
            sy = ((g_size - 1 - r) * full_h) + (SLIT_WIDTH // 2)
            
            file_id = f"Cam_Grid{g_size}_{cam_i + 1:02d}"
            script_filename = f"{song_name}_{file_id}.json"
            
            # 情報を登録
            all_camera_info[file_id] = {
                "x": sx, "y": sy,
                "w": w, "h": h,
                "grid_size": g_size,
                "cam_index": cam_i
            }
            
            # プロファイル生成
            # 1カメラ(g_size=1)は元SongScriptのコピー扱い: FOVも元スクリプトの最初のMovementから取得
            is_single_cam = (g_size == 1)
            profile_fov = source_movements[0].get("StartPos", {}).get("FOV", 60.0) if is_single_cam else TILING_FOV
            profile_data = {
                "CameraType": "ThirdPerson",
                "FieldOfView": profile_fov,
                "VisibleObject": {
                    "Avatar": True, "UI": False, "Wall": True, "WallFrame": True,
                    "Saber": True, "Notes": True, "Debris": "Link", "CutParticles": True
                },
                "Layer": -68,
                "AntiAliasing": 2,
                "RenderScale": 1.0,
                "WindowRect": {
                    # 全カメラ共通: FitToCanvas=False でWindowControlによる表示/非表示を可能にする
                    # 1カメラはフルスクリーンサイズ (1920x1080)、マルチカメラはグリッドセルサイズ
                    "FitToCanvas": False,
                    "x": OFF_SCREEN_X,  # 初期は画面外 (WindowControlで制御)
                    "y": 0 if is_single_cam else sy,
                    "width": RESOLUTION_W if is_single_cam else w,
                    "height": RESOLUTION_H if is_single_cam else h
                },
                "MovementScript": {
                    "MovementScript": script_filename,
                    "UseAudioSync": True
                },
                "CameraExtensions": {
                    "dontDrawDesktop": False,
                    "PreviewCamera": False
                },
                "ThirdPersonPos": {"x": 0, "y": 2.0, "z": -3.0},
                "ThirdPersonRot": {"x": 15, "y": 0, "z": 0}
            }
            
            with open(os.path.join(profiles_dir, f"{file_id}.json"), "w", encoding="utf-8") as f:
                json.dump(profile_data, f, indent=2)
            
            # グリッド用 MovementScript 生成
            movements = []
            
            center_r = (g_size - 1) / 2.0
            center_c = (g_size - 1) / 2.0
            
            # 垂直方向のタイリングオフセット：弓形配列の中心を基準に計算。
            # Row0 (上) -> 負値 (上向き), RowMax (下) -> 正値 (下向き)。
            v_offset = (r - center_r) * TILING_FOV
            
            # 水平: 右がプラス -> calc is (col - center)
            # H-FOV (deg) of **ONE TILE**
            h_fov_tile = get_hfov(TILING_FOV)
            h_offset = (c - center_c) * h_fov_tile
            
            current_time = 0.0
            
            for idx, m in enumerate(source_movements):
                dur = m.get("Duration", 1.0)
                
                # 現在の絶対時間におけるエフェクトをチェック
                # Loop開始時点でのエフェクトを採用
                if schedule:
                    effect_entry = find_effect_for_time(schedule, current_time)
                    target_cameras = effect_entry.get("cameras", 9)
                    current_grid_size = int(target_cameras ** 0.5)
                else:
                    effect_entry = {}
                    current_grid_size = default_grid_size
                
                # 最適化: 現在対象ではないグリッドのカメラは完全に非表示なので、
                # 複雑な計算をスキップして最小限の時間同調データだけ書き込む
                if current_grid_size != g_size:
                    cur_m = {
                        "StartPos": {"x": 5000, "y": 0, "z": 0},
                        "EndPos": {"x": 5000, "y": 0, "z": 0},
                        "Duration": dur,
                        "VisibleObject": {"avatar": False}
                    }
                    movements.append(cur_m)
                    current_time += dur
                    continue
                
                # Chronos Cascade: 時間オフセット計算
                # delay > 0 の場合、「遅れて」動く => 過去の状態(t - delay)を参照
                delay_offset = 0.0
                # Base tiling offsets for current grid size (restored on each loop)
                v_offset = (r - center_r) * TILING_FOV
                h_offset = (c - center_c) * h_fov_tile
                
                # Clone Grid / Symmetry View etc: Override offsets
                is_centered_view = False
                effect_name = effect_entry.get("effect")
                
                if effect_name in ("clone-grid", "surround-view", "panoptic-view"):
                    v_offset = 0.0
                    h_offset = 0.0
                    is_centered_view = True
                elif effect_name == "split-view":
                    # Keep v_offset so cameras stay stacked vertically
                    h_offset = 0.0
                    is_centered_view = True
                elif effect_name == "symmetry-view":
                    # Keep v_offset for vertical tiling (e.g. 1x2 panorama for each avatar)
                    h_offset = 0.0 # No horizontal spreading
                    is_centered_view = False # Must be false to apply v_offset independently without TurnToHead override
                
                # Vortex Spin: Calculate Z-rotation
                vortex_rot_start = 0.0
                vortex_rot_end = 0.0
                
                if effect_entry.get("effect") == "vortex-spin":
                    vortex_rot_start = get_vortex_spin_rotation(effect_entry, current_time, r, c)
                    vortex_rot_end = get_vortex_spin_rotation(effect_entry, current_time + dur, r, c)

                # Check for other delay effects
                if effect_entry.get("effect") == "chronos-cascade":
                    delay_offset = get_chronos_delay(effect_entry, r, c, g_size)
                elif effect_entry.get("effect") == "radial-chronos":
                    delay_offset = get_radial_chronos_delay(effect_entry, r, c, g_size)
                elif effect_entry.get("effect") == "diagonal-wave":
                    delay_offset = get_diagonal_wave_delay(effect_entry, r, c, g_size)
                
                # Dimension Roulette: ランダムパラメータ
                roulette = get_dimension_roulette_params(effect_entry, cam_i, idx)

                # Delay Logic: Calculate effective Start/End state
                if delay_offset > 0.001:
                    eff_start = current_time - delay_offset
                    eff_end = current_time + dur - delay_offset
                    
                    st_s = get_state_at_time(source_movements, eff_start)
                    st_e = get_state_at_time(source_movements, eff_end)
                    
                    target_start_pos = {"x": st_s["x"], "y": st_s["y"], "z": st_s["z"], "FOV": st_s["FOV"]}
                    target_end_pos = {"x": st_e["x"], "y": st_e["y"], "z": st_e["z"], "FOV": st_e["FOV"]}
                    target_start_rot = {"x": st_s["rot_x"], "y": st_s["rot_y"], "z": st_s["rot_z"]}
                    target_end_rot = {"x": st_e["rot_x"], "y": st_e["rot_y"], "z": st_e["rot_z"]}
                else:
                    target_start_pos = m.get("StartPos", {})
                    target_end_pos = m.get("EndPos", {})
                    target_start_rot = m.get("StartRot", {})
                    target_end_rot = m.get("EndRot", {})

                # StartPos計算 & LookAt
                g1_fov = target_start_pos.get("FOV", 60.0)
                
                # Grid 1x1 (Single Camera) の場合は FOV を固定せず、元のFOVを使用する
                # Grid > 1 の場合は TILING_FOV (10度) に固定する
                # scale計算: Gridの場合は「1タイルのFOV」に対してTILING_FOVを合わせる
                # 1タイルのFOV = OriginalFOV / grid_size (簡易計算)
                target_fov = g1_fov if g_size == 1 else TILING_FOV
                source_fov_for_scale = g1_fov if g_size == 1 else (g1_fov / g_size)
                
                g1_scale = calc_distance_scale(source_fov_for_scale, target_fov)
                scaled_start = scale_position(target_start_pos, g1_scale)
                
                # Symmetric View Transformation (Start)
                if effect_entry.get("effect") == "symmetry-view":
                    # Default Pattern: left-right
                    # If column is on the right side, mirror it
                    cutoff = (g_size - 1) / 2.0
                    if c > cutoff:
                        sym_type = effect_entry.get("symmetry_type", "point")
                        
                        if sym_type == "point":
                            scaled_start["x"] = -scaled_start["x"]
                            scaled_start["z"] = -scaled_start["z"]
                        elif sym_type == "mirror":
                            scaled_start["x"] = -scaled_start["x"]
                
                look_at_start = calculate_look_at_rotation(scaled_start, {"x": 0, "y": 1.5, "z": 0})
                orig_s_rot = target_start_rot
                s_rot = {
                    "x": look_at_start["x"],
                    "y": look_at_start["y"],
                    "z": orig_s_rot.get("z", 0)
                }

                # EndPos計算 & LookAt
                g1_fov_end = target_end_pos.get("FOV", 60.0)
                target_fov_end = g1_fov_end if g_size == 1 else TILING_FOV
                source_fov_end_for_scale = g1_fov_end if g_size == 1 else (g1_fov_end / g_size)
                
                g1_scale_end = calc_distance_scale(source_fov_end_for_scale, target_fov_end)
                scaled_end = scale_position(target_end_pos, g1_scale_end)
                
                # Symmetric View Transformation (End)
                if effect_entry.get("effect") == "symmetry-view":
                    cutoff = (g_size - 1) / 2.0
                    if c > cutoff:
                        sym_type = effect_entry.get("symmetry_type", "point")
                        if sym_type == "point":
                            scaled_end["x"] = -scaled_end["x"]
                            scaled_end["z"] = -scaled_end["z"]
                        elif sym_type == "mirror":
                            scaled_end["x"] = -scaled_end["x"]
                
                look_at_end = calculate_look_at_rotation(scaled_end, {"x": 0, "y": 1.5, "z": 0})
                orig_e_rot = target_end_rot
                e_rot = {
                    "x": look_at_end["x"],
                    "y": look_at_end["y"],
                    "z": orig_e_rot.get("z", 0)
                }
                
                # Rot (Grid offset 加算)
                s_rot_x = s_rot.get("x", 0)
                s_rot_y = s_rot.get("y", 0)
                s_rot_z = s_rot.get("z", 0)
                
                e_rot_x = e_rot.get("x", 0)
                e_rot_y = e_rot.get("y", 0)
                e_rot_z = e_rot.get("z", 0)

                # Fix Spin: Ensure shortest path for Y rotation (Start -> End)
                # Especially important for Symmetric View where inversion causes Yaw jumps.
                diff_y = e_rot_y - s_rot_y
                if diff_y > 180:
                    e_rot_y -= 360
                elif diff_y < -180:
                    e_rot_y += 360
                # Orbit Calculation
                orbit_angle = 0.0
                is_mirror_view = False
                
                if effect_name == "split-view":
                    orbit_angle = get_split_view_rotation_offset(effect_entry, c, g_size)
                elif effect_name == "surround-view":
                    orbit_angle = get_surround_view_rotation_offset(effect_entry, cam_i, g_size)
                elif effect_name == "panoptic-view":
                    orbit_angle = get_panoptic_view_rotation_offset(effect_entry, cam_i, g_size)

                # Apply orbiting to position
                if orbit_angle != 0.0:
                    scaled_start = rotate_position_around_origin(scaled_start, orbit_angle)
                    scaled_end = rotate_position_around_origin(scaled_end, orbit_angle)
                    
                    if is_centered_view:
                        # For split/surround/panoptic (is_centered=True), TurnToHead handles Yaw. 
                        # We still set h_offset identically stringently just in case TurnToHead is missing.
                        h_offset = orbit_angle
                    else:
                        # For symmetry-view (is_centered=False), we MUST manually adjust Yaw to face avatar.
                        s_rot_y += orbit_angle
                        e_rot_y += orbit_angle

                fov_mul = roulette["fov_mul"]
                rot_z_offset = roulette["rot_z"]

                # Outline Effect
                outline_params = None
                if schedule:
                   # effect_entry is already retrieved above
                   # we need absolute time relative to effect start?
                   # find_effect_for_time returns entry.
                   # we need bpm from somewhere. (available in outer var `bpm` if effect_script was loaded)
                   
                   # But `bpm` variable is inside `if effect_script is not None:` block.
                   # valid BPM is required. fallback to 120?
                   current_bpm = 120.0
                   if effect_script:
                       current_bpm = effect_script.get("bpm", 120.0)
                   
                   # Calculate time since effect start
                   eff_start_time = effect_entry.get("start", 0.0)
                   time_since_start = current_time - eff_start_time
                   
                   outline_params = get_outline_effect_params(
                       effect_entry, cam_i, g_size, time_since_start, current_bpm
                   )

                else:
                    outline_params = None

                # Apply static outline effect for symmetry-view if specified
                if effect_entry.get("effect") == "symmetry-view":
                    outline_side = effect_entry.get("outline_side")
                    if outline_side:
                        is_left = c < g_size / 2.0
                        is_right = c > (g_size - 1) / 2.0
                        if (outline_side == "left" and is_left) or (outline_side == "right" and is_right) or outline_side == "both":
                            # We import inside or just call since we imported everything from multicam_effects
                            from multicam_effects import get_static_outline_params
                            outline_params = get_static_outline_params(effect_entry)



                cur_m = {
                    "StartPos": {
                        "x": round(scaled_start["x"], 3),
                        "y": round(scaled_start["y"], 3),
                        "z": round(scaled_start["z"], 3),
                        # g_size=1(1カメラ)は元のFOV維持。それ以外はタイリング用FOV固定
                        "FOV": round(target_fov * fov_mul, 2)
                    },
                    "StartRot": {
                        "x": round(s_rot_x + v_offset, 2),
                        "y": round(s_rot_y + h_offset, 2),
                        "z": round(s_rot_z + rot_z_offset + vortex_rot_start, 2)
                    },
                    "EndPos": {
                        "x": round(scaled_end["x"], 3),
                        "y": round(scaled_end["y"], 3),
                        "z": round(scaled_end["z"], 3),
                        "FOV": round(target_fov_end * fov_mul, 2)
                    },
                    "EndRot": {
                        "x": round(e_rot_x + v_offset, 2),
                        "y": round(e_rot_y + h_offset, 2),
                        "z": round(e_rot_z + rot_z_offset + vortex_rot_end, 2)
                    },
                    "Duration": dur,
                    "Delay": m.get("Delay", 0.0), # Delayはそのまま (タイミングはマスター同期)
                    "EaseTransition": m.get("EaseTransition", True),
                    "VisibleObject": m.get("VisibleObject", {
                        "avatar": True, "ui": True, "wall": True, "wallFrame": True,
                        "saber": True, "notes": True, "cutParticles": True
                    })
                }
                
                for key in ("CameraEffect", "TurnToHead", "TurnToHeadHorizontal"):
                    if key in m:
                        # TurnToHead disables manual grid rotation offsets natively,
                        # so we only pass it through if the panel is meant to be a centered view.
                        if key.startswith("TurnToHead"):
                            if is_centered_view:
                                cur_m[key] = m[key]
                            else:
                                cur_m[key] = False
                        else:
                            cur_m[key] = m[key]
                
                if outline_params:
                    # Merge or Overwrite CameraEffect
                    if "CameraEffect" not in cur_m:
                        cur_m["CameraEffect"] = {}
                    cur_m["CameraEffect"].update(outline_params)
                
                movements.append(cur_m)
                current_time += dur
            
            # Validation: Verify sum of durations matches original exactly
            actual_total_duration = sum(m.get("Duration", 0.0) for m in movements)
            if abs(actual_total_duration - expected_total_duration) > 0.001:
                raise ValueError(
                    f"Duration mismatch for {script_filename}: "
                    f"expected {expected_total_duration:.4f}s, got {actual_total_duration:.4f}s. "
                    f"This will cause audio desynchronization in Beat Saber."
                )
            
            script_data = {
                "ActiveInPauseMenu": song_script.get("ActiveInPauseMenu", True),
                "TurnToHeadUseCameraSetting": song_script.get("TurnToHeadUseCameraSetting", False),
                "Movements": movements
            }
            # TurnToHeadUseCameraSetting は除外（グリッドカメラはTurnToHead無効）
            
            with open(os.path.join(scripts_dir, script_filename), "w", encoding="utf-8") as f:
                json.dump(script_data, f, indent=2)
    
    # ============================================================
    # PASS 2: マスター生成 & WindowControl
    # ============================================================
    
    # マスターカメラ情報
    # Option 4: "Invisible Orchestrator"
    # Use cameraplus.json (so it works as main), but dontDrawDesktop=True (so it's black/invisible).
    master_file_id = "cameraplus"
    master_script_filename = f"{song_name}_{master_file_id}.json"
    
    master_profile = {
        "CameraType": "ThirdPerson",
        "FieldOfView": TILING_FOV,
        "VisibleObject": {
            "Avatar": True, "UI": True, "Wall": True, "WallFrame": True,
            "Saber": True, "Notes": True, "Debris": "Link", "CutParticles": True
        },
        "Layer": -1000, # Background Layer
        "AntiAliasing": 2,
        "RenderScale": 1.0,
        "WindowRect": {
            "FitToCanvas": True,
            "x": 0,
            "y": 0,
            "width": RESOLUTION_W, "height": RESOLUTION_H
        },
        "MovementScript": {
            "MovementScript": master_script_filename,
            "UseAudioSync": True
        },
        "CameraExtensions": {
            "dontDrawDesktop": True,
            "PreviewCamera": False
        },
        "ThirdPersonPos": {"x": 0, "y": 2.0, "z": -3.0},
        "ThirdPersonRot": {"x": 0, "y": 0, "z": 0}
    }
    
    with open(os.path.join(profiles_dir, f"{master_file_id}.json"), "w", encoding="utf-8") as f:
        json.dump(master_profile, f, indent=2)
    
    
    # マスタースクリプト生成 (Grid切替 & エフェクト適用)
    master_movements = []
    abs_time = 0.0
    
    for movement_idx, m in enumerate(source_movements):
        abs_time += m.get("Delay", 0.0)
        
        # マスター自身の動き
        g1_fov = m.get("StartPos", {}).get("FOV", 60.0)
        # Master is essentially a 1x1 grid for calculation purposes here, or we simulate one tile?
        # Actually Master is usually hidden. But if it's used for something...
        # Let's keep Master logic as "Overview" (1x1 Equivalent).
        # v_offset/h_offset are 0 for Master.
        # So Master should just track the Original script?
        # But wait, Master FOV is set to TILING_FOV (10) in profile.
        # If we want Master to track the "Center View", we should use Center Tile logic.
        # Center Tile logic = Original / GridSize -> TILING_FOV.
        # Let's use default_grid_size for master calculation.
        
        source_fov_for_scale = g1_fov / default_grid_size if default_grid_size > 1 else g1_fov
        target_fov = TILING_FOV if default_grid_size > 1 else g1_fov
        
        g1_scale = calc_distance_scale(source_fov_for_scale, target_fov)
        
        scaled_start = scale_position(m.get("StartPos", {}), g1_scale)
        
        # 強制LookAt: アバター(0,1.5,0)を向く回転を計算
        # SongScriptの元回転は無視する (FOV変更によりズレるため)
        look_at_start = calculate_look_at_rotation(scaled_start, {"x": 0, "y": 1.5, "z": 0})
        
        # 元のRoll(Z)は維持
        orig_s_rot = m.get("StartRot", {"x":0,"y":0,"z":0})
        s_rot = {
            "x": look_at_start["x"],
            "y": look_at_start["y"],
            "z": orig_s_rot.get("z", 0)
        }

        # EndPos計算 & LookAt
        g1_fov_end = m.get("EndPos", {}).get("FOV", 60.0)
        source_fov_end_for_scale = g1_fov_end / default_grid_size if default_grid_size > 1 else g1_fov_end
        target_fov_end = TILING_FOV if default_grid_size > 1 else g1_fov_end

        g1_scale_end = calc_distance_scale(source_fov_end_for_scale, target_fov_end)
        scaled_end = scale_position(m.get("EndPos", {}), g1_scale_end)
        
        look_at_end = calculate_look_at_rotation(scaled_end, {"x": 0, "y": 1.5, "z": 0})
        orig_e_rot = m.get("EndRot", {"x":0,"y":0,"z":0})
        e_rot = {
            "x": look_at_end["x"],
            "y": look_at_end["y"],
            "z": orig_e_rot.get("z", 0)
        }
        
        cur_m = {
            "StartPos": {
                "x": round(scaled_start["x"], 3), "y": round(scaled_start["y"], 3), "z": round(scaled_start["z"], 3),
                "FOV": TILING_FOV
            },
            "EndPos": {
                "x": round(scaled_end["x"], 3), "y": round(scaled_end["y"], 3), "z": round(scaled_end["z"], 3),
                "FOV": TILING_FOV
            },
            "StartRot": {"x": round(s_rot["x"], 2), "y": round(s_rot["y"], 2), "z": round(s_rot["z"], 2)},
            "EndRot":   {"x": round(e_rot["x"], 2), "y": round(e_rot["y"], 2), "z": round(e_rot["z"], 2)},
            "Duration": m.get("Duration", 1.0),
            "Delay": m.get("Delay", 0.0),
            "EaseTransition": m.get("EaseTransition", True),
            "VisibleObject": { # Force True to ensure CameraPlus updates it
                "avatar": True, "ui": True, "wall": True, "wallFrame": True,
                "saber": True, "notes": True, "cutParticles": True
            },
        }
        
        # オプションフィールド
        for key in ("CameraEffect",):
            if key in m:
                cur_m[key] = m[key]
        
        # WindowControl 生成
        win_ctrl = []
        
        # 1. マスター自身(cameraplus.json)は WindowControlで制御しない (常時表示・FitToCanvas)
        
        # 2. 現在のエフェクトとグリッドサイズを取得
        effect_entry = find_effect_for_time(schedule, abs_time) if schedule else {"effect": "all-visible"}
        
        target_cameras = effect_entry.get("cameras", 9) # デフォルト9台
        # cameras数から grid_size を決定 (平方根の整数)
        current_grid_size = int(target_cameras ** 0.5)
        # もし計算したgrid_sizeのファイルが生成されてなければフォールバック
        if current_grid_size not in required_grids:
            current_grid_size = default_grid_size
        
        # 3. 全生成済みカメラに対して Visible 判定
        sorted_filenames = sorted(all_camera_info.keys())
        for f_id in sorted_filenames:
            info = all_camera_info[f_id]
            
            # Target Name: f_id + ".json"
            f_name = f"{f_id}.json"
            target_name = f_name
            
            # Determine visibility
            should_show = False
            
            cam_g_size = info["grid_size"]
            cam_idx = info["cam_index"]
            
            if cam_g_size == current_grid_size:
                # グリッドが一致する場合のみ、エフェクト判定を行う
                is_effect_visible = apply_window_visibility(effect_entry, cam_idx, cam_g_size, movement_idx)
                if is_effect_visible:
                    should_show = True

            if should_show:
                # 表示位置
                win_ctrl.append({
                    "Target": target_name,
                    "Visible": True,
                    "StartPos": {"x": info["x"], "y": info["y"]},
                    "EndPos":   {"x": info["x"], "y": info["y"]}
                })
            else:
                # 非表示 (画面外へ)
                win_ctrl.append({
                    "Target": target_name,
                    "Visible": False,
                    "StartPos": {"x": OFF_SCREEN_X, "y": 0},
                    "EndPos":   {"x": OFF_SCREEN_X, "y": 0}
                })
        
        cur_m["WindowControl"] = win_ctrl
        master_movements.append(cur_m)
        abs_time += m.get("Duration", 0.0)
    
    # Validation: Verify sum of durations for master script
    actual_master_duration = sum(m.get("Duration", 0.0) for m in master_movements)
    if abs(actual_master_duration - expected_total_duration) > 0.001:
        raise ValueError(
            f"Duration mismatch for {master_script_filename}: "
            f"expected {expected_total_duration:.4f}s, got {actual_master_duration:.4f}s. "
            f"This will cause audio desynchronization in Beat Saber."
        )

    master_script = {
        "ActiveInPauseMenu": song_script.get("ActiveInPauseMenu", True),
        "Movements": master_movements
    }
    
    with open(os.path.join(scripts_dir, master_script_filename), "w", encoding="utf-8") as f:
        json.dump(master_script, f, indent=2)
    
    # ============================================================
    # Summary
    # ============================================================
    total_files = 1 + len(all_camera_info)  # master + all grid cameras
    total_duration = sum(m.get("Duration", 0) for m in source_movements)
    print(f"✅ Generated {total_files} profiles + {total_files} scripts")
    print(f"   Master:   {master_file_id}.json")
    print(f"   Grids:    {sorted(required_grids)} (Total {len(all_camera_info)} cameras)")
    print(f"   Scripts:  {scripts_dir}/")
    print(f"   Profiles: {profiles_dir}/")
    print(f"   Duration: {total_duration:.1f}s ({len(source_movements)} movements)")
    print()
    print(f"NOTE: 配置前に既存の Profiles/{song_name} フォルダを削除してください。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="SongScriptからマルチカメラ用MovementScriptを生成します。",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
[使用例]
  python generator_song_multicam.py -i SongScript.json -e EffectScript.json
  python generator_song_multicam.py -i SongScript.json -e EffectScript.json -o output -n MySong
"""
    )
    parser.add_argument("-i", "--input", required=True, metavar="SONGSCRIPT_JSON", help="入力 SongScript.json のパス")
    parser.add_argument("-e", "--effect-script", type=str, required=True, help="EffectScript JSON のパス")
    parser.add_argument("-o", "--output", help="出力ディレクトリ (デフォルト: 入力ファイルと同じディレクトリに 'output' を作成)")
    # 以下は主に-eなしで使う簡易オプション。helpからは隠す
    parser.add_argument("-g", "--grid", type=int, default=3, help=argparse.SUPPRESS)
    parser.add_argument("-n", "--name", help=argparse.SUPPRESS)
    parser.add_argument("--bpm", type=float, help=argparse.SUPPRESS)
    parser.add_argument("--effect", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--beats-per-sub", type=int, default=1, help=argparse.SUPPRESS)
    
    args = parser.parse_args()
    
    # EffectScript Construction
    eff_script = None
    
    if args.effect_script:
        eff_script = load_effect_script(args.effect_script)
        
    elif args.effect:
        if not args.bpm:
            print("ERROR: --bpm is required when using --effect.")
            sys.exit(1)
        # Create a single-entry schedule
        eff_script = {
            "bpm": args.bpm,
            "beats_per_sub": args.beats_per_sub,
            "schedule": [
                {
                    "start": 0,
                    "end": None,
                    "effect": args.effect,
                    "cameras": args.grid * args.grid # CLIのgridを使用
                }
            ]
        }
        normalize_schedule(eff_script["schedule"])
    elif args.bpm:
        # BPM指定のみ（分割あり、エフェクトなし）
        eff_script = {
            "bpm": args.bpm,
            "beats_per_sub": args.beats_per_sub,
            "schedule": [] # empty schedule
        }
        
    generate(args.input, args.grid, args.output, args.name, eff_script)
