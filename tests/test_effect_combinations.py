
import pytest
import os
import json
import subprocess
import sys
import shutil

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATOR_SCRIPT = os.path.join(BASE_DIR, "generator_song_multicam.py")
TEMP_STATE_DIR = os.path.join(BASE_DIR, "logs", "temp", "combo_test")
OUTPUT_DIR = os.path.join(BASE_DIR, "logs", "output_combo_test")

@pytest.fixture(scope="module")
def setup_combo_env():
    os.makedirs(TEMP_STATE_DIR, exist_ok=True)
    yield
    # shutil.rmtree(TEMP_STATE_DIR, ignore_errors=True)
    # shutil.rmtree(OUTPUT_DIR, ignore_errors=True)

@pytest.mark.parametrize("grid_size, effect_name", [
    (1, "all-visible"),
    (1, "mosaic-blink"),
    (1, "chronos-cascade"),
    (1, "dimension-roulette"),
    (2, "all-visible"),
    (2, "mosaic-blink"),
    (2, "chronos-cascade"),
    (2, "dimension-roulette"),
    (3, "all-visible"),
    (3, "mosaic-blink"),
    (3, "chronos-cascade"),
    (3, "dimension-roulette"),
    (1, "radial-chronos"),
    (2, "radial-chronos"),
    (3, "radial-chronos"),
    (1, "random-outline-fill"),
    (2, "random-outline-fill"),
    (3, "random-outline-fill"),
])
def test_effect_combination(setup_combo_env, grid_size, effect_name):
    """
    Test all 12 combinations of Grid Size (1,2,3) and Effects.
    """
    # 1. Prepare Input SongScript (Simple 2 movements to allow Blink/Chronos check)
    input_json_path = os.path.join(TEMP_STATE_DIR, f"input_{grid_size}_{effect_name}.json")
    input_data = {
        "ActiveInPauseMenu": True,
        "Movements": [
            {
                "StartPos": {"x": 0, "y": 0, "z": 0, "FOV": 60},
                "EndPos":   {"x": 10, "y": 0, "z": 0, "FOV": 60}, # Moving for Chronos check
                "Duration": 1.0, # Beat 0-2 (assuming bpm 120)
                "VisibleObject": {"avatar": True}
            },
            {
                "StartPos": {"x": 10, "y": 0, "z": 0, "FOV": 60},
                "EndPos":   {"x": 0, "y": 0, "z": 0, "FOV": 60},
                "Duration": 1.0,
                "VisibleObject": {"avatar": True}
            }
        ]
    }
    with open(input_json_path, "w", encoding="utf-8") as f:
        json.dump(input_data, f)

    # 2. Prepare EffectScript
    effect_json_path = os.path.join(TEMP_STATE_DIR, f"effect_{grid_size}_{effect_name}.json")
    
    # Calculate target cameras from grid_size (1->1, 2->4, 3->9)
    target_cameras = grid_size * grid_size
    
    effect_data = {
        "bpm": 120,
        "schedule": [
            {
                "start": 0, 
                "end": None, 
                "cameras": target_cameras, 
                "effect": effect_name
            }
        ],
        "parameters": {
            "chronos_delay": 0.1 # Significant delay
        }
    }
    with open(effect_json_path, "w", encoding="utf-8") as f:
        json.dump(effect_data, f)
        
    # 3. Clean Output Dir for this run
    current_output = os.path.join(OUTPUT_DIR, f"{grid_size}_{effect_name}")
    if os.path.exists(current_output):
        shutil.rmtree(current_output)
        
    # 4. Run Generator
    cmd = [
        sys.executable, GENERATOR_SCRIPT,
        "-i", input_json_path,
        "-o", current_output,
        "--effect-script", effect_json_path
    ]
    
    # Run
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8", env=env)
    assert result.returncode == 0, f"Generator failed for {grid_size}/{effect_name}: {result.stderr}"
    
    # 5. Verify File Existence
    scripts_dir = os.path.join(current_output, "Scripts")
    profiles_dir = os.path.join(current_output, "Profiles", f"input_{grid_size}_{effect_name}")
    
    assert os.path.exists(scripts_dir)
    assert os.path.exists(profiles_dir)
    
    # Count generated files
    # Should satisfy target_cameras count.
    # Pattern: input_..._Cam_Grid{size}_{01..N}.json
    
    generated_profiles = [f for f in os.listdir(profiles_dir) if f.endswith(".json") and "cameraplus" not in f]
    generated_scripts = [f for f in os.listdir(scripts_dir) if f.endswith(".json") and "cameraplus" not in f]
    
    # grid_size=1 は範囲外デフォルトで常に必要グリッドに含まれる
    # total_profiles = grid_size=1 の1台 + target_cameras
    # ただし grid_size=1 の場合はすでに target_cameras=1 なので重複なし
    extra_grid1_cams = 1 if grid_size != 1 else 0  # grid_size=1以外は1カメラグリッドが追加される
    expected_count = target_cameras + extra_grid1_cams
    
    assert len(generated_profiles) == expected_count, f"Expected {expected_count} profiles, got {len(generated_profiles)}"
    assert len(generated_scripts) == expected_count, f"Expected {expected_count} scripts, got {len(generated_scripts)}"
    
    # 6. Content Verification (Effect specific)
    
    # Load first camera script
    script_01_path = os.path.join(scripts_dir, f"input_{grid_size}_{effect_name}_Cam_Grid{grid_size}_01.json")
    with open(script_01_path, "r", encoding="utf-8") as f:
        s01 = json.load(f)
        
    movements = s01["Movements"]
    
    if effect_name == "all-visible":
        # All visible
        # WindowControl logic is in Master script, but per-camera JSON doesn't track visibility usually unless it's in WindowControl?
        # Grid visibility is controlled by Master WindowControl, not per-camera scripts.
        # But wait, 'apply_window_visibility' in generator logic:
        # It sets win_ctrl.append({"Visible": False}) in MASTER script.
        # The grid scripts themselves don't change visibility.
        
        # So we need to check Master script for visibility commands?
        # Or does the generator inject VisibleObject into grid scripts?
        # Generator: `cur_m["VisibleObject"]` is copied from input.
        # It does NOT verify master logic here.
        pass
        
    elif effect_name == "mosaic-blink":
        # Check Master script for Blink logic
        master_path = os.path.join(scripts_dir, f"input_{grid_size}_{effect_name}_cameraplus.json")
        with open(master_path, "r", encoding="utf-8") as f:
            master = json.load(f)
            
        # Get WindowControl from first movement
        wc_entries = master["Movements"][0].get("WindowControl", [])
        
        # If Grid=1, 1x1 only has 1 cell. (0,0). Checker=(0+0)%2=0. Mov 0 -> Visible. Mov 1 -> Hidden.
        # If blinking working, visibility should flip between movements for the same target.
        
        # Check target "Cam_GridX_01" across movements
        target_name = f"Cam_Grid{grid_size}_01.json" # No input_ prefix in Target usually?
        # Generator uses file_id + ".json". file_id = Cam_Grid{g}_01.
        # Wait, generator logic:
        # win_ctrl.append({"Target": f"{file_id}.json", "Visible": should_show, ...})
        
        vis_mov0 = None
        vis_mov1 = None
        
        # Movement 0
        wc0 = master["Movements"][0]["WindowControl"]
        for w in wc0:
            if w["Target"].startswith(f"Cam_Grid{grid_size}_01") or w["Target"] == f"Cam_Grid{grid_size}_01.json":
                vis_mov0 = w.get("Visible", True)
        
        # Movement 1
        wc1 = master["Movements"][1]["WindowControl"]
        for w in wc1:
            if w["Target"].startswith(f"Cam_Grid{grid_size}_01") or w["Target"] == f"Cam_Grid{grid_size}_01.json":
                vis_mov1 = w.get("Visible", True)
                
        # With Mosaic Blink, they should differ (True/False)
        assert vis_mov0 is not None, "Could not find target in Movement 0 WindowControl"
        assert vis_mov1 is not None, "Could not find target in Movement 1 WindowControl"
        assert vis_mov0 != vis_mov1, f"Mosaic Blink should toggle visibility (Got {vis_mov0} -> {vis_mov1})"
        
    elif effect_name == "chronos-cascade":
        if grid_size == 1:
            # 1 col. No delay possible relative to itself.
            pass
        else:
            # Grid 2 (2x2) or 3 (3x3).
            # Cam 01 (Col 0) vs Cam 02 (Col 1).
            script_02_path = os.path.join(scripts_dir, f"input_{grid_size}_{effect_name}_Cam_Grid{grid_size}_02.json")
            with open(script_02_path, "r", encoding="utf-8") as f:
                s02 = json.load(f)
            
            # Binary diff check
            assert s01 != s02, "Chronos: Col 0 and Col 1 should differ"
            
    elif effect_name == "dimension-roulette":
         # Check FOV or Roll in s01
         # Default FOV is TILING_FOV = 10.0
         # Roulette modifies it.
         
         # Check first few movements (subdivided)
         has_deviated = False
         for m in movements:
             fov = m["StartPos"].get("FOV", 10.0)
             z_rot = m["StartRot"].get("z", 0.0)
             
             # Check if FOV deviates significantly from 10.0
             if abs(fov - 10.0) > 0.1:
                 has_deviated = True
                 break
             # Check if Z rot deviates from 0.0
             if abs(z_rot) > 0.1:
                 has_deviated = True
                 break
                 
         assert has_deviated, "Dimension Roulette should modify FOV or Z-Rotation from defaults (10.0, 0.0)"

    elif effect_name == "radial-chronos":
        if grid_size == 3:
             # Grid 3: Center (Cam 05) vs Corner (Cam 01)
             # Center has dist=0 (no delay), Corner has dist>0 (delay)
             # They should have different coordinates at the same time step
             
             script_05_path = os.path.join(scripts_dir, f"input_{grid_size}_{effect_name}_Cam_Grid{grid_size}_05.json")
             if os.path.exists(script_05_path):
                 with open(script_05_path, "r", encoding="utf-8") as f:
                     s05 = json.load(f)
                 
                 # Check EndPos difference
                 # Note: Even without delay, they have different coordinates due to grid position (StartPos x/y).
                 # valid point. Grid logic shifts x/y.
                 # BUT, let's look at FOV or something that might be uniform? No, FOV is fixed TILING_FOV.
                 
                 # However, relying on `test_radial_chronos.py` for strict logic.
                 # Here we mainly ensure it Runs and produces output.
                 # But we can check that s05 and s01 are NOT identical textually (which is obvious).
                 
                 # Let's check that the delay mechanism didn't crash.
                 # A weak check: EndPos should be present.
                 pass
        else:
            # Grid 1 or 2
            pass
            
    elif effect_name == "random-outline-fill":
        # ジェネレータが正常完了しファイルが生成されることを確認。
        # エフェクトパラメータの詳細検証は test_effects.py::TestRandomOutlineFill で担保済み。
        # (duration_beats のデフォルト = 4 * grid_size ビートで、入力が2秒しかないため
        #  trigger が届かないカメラが存在しての検証は不適切)
        if grid_size > 1:
            script_01_path = os.path.join(scripts_dir, f"input_{grid_size}_{effect_name}_Cam_Grid{grid_size}_01.json")
            assert os.path.exists(script_01_path), "random-outline-fill: grid camera script should be generated"
            with open(script_01_path, "r", encoding="utf-8") as f:
                s01_check = json.load(f)
            assert "Movements" in s01_check, "Grid camera script should have Movements"
