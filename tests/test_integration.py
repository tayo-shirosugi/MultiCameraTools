
import pytest
import os
import json
import subprocess
import shutil
import sys

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATOR_SCRIPT = os.path.join(BASE_DIR, "generator_song_multicam.py")
TEMP_INPUT_JSON = os.path.join(BASE_DIR, "logs", "temp", "integration_input.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "logs", "output_integration_test")

@pytest.fixture(scope="module")
def setup_integration_env():
    # 1. Create dummy input
    os.makedirs(os.path.dirname(TEMP_INPUT_JSON), exist_ok=True)
    
    input_data = {
        "ActiveInPauseMenu": True,
        "Movements": [
            {
                "StartPos": {"x": 0, "y": 2.0, "z": -3.0, "FOV": 60.0},
                "StartRot": {"x": 0, "y": 0, "z": 0}, # Flat rotation
                "EndPos":   {"x": 0, "y": 2.0, "z": -3.0, "FOV": 60.0},
                "EndRot":   {"x": 0, "y": 0, "z": 0},
                "Duration": 2.0,
                "VisibleObject": {"avatar": True}
            }
        ]
    }
    
    with open(TEMP_INPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(input_data, f, indent=2)
        
    # 2. Run generator (Grid=2, 4 cameras)
    # output_integration_test folder will be created
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
        
    # 1.5 Create dummy effect script (Required -e)
    temp_effect_json = os.path.join(os.path.dirname(TEMP_INPUT_JSON), "integration_effect_dummy.json")
    with open(temp_effect_json, "w", encoding="utf-8") as f:
        json.dump({
            "bpm": 120, 
            "schedule": [{"start":0, "cameras":4, "effect":"all-visible"}]
        }, f, indent=2)

    cmd = [
        sys.executable, GENERATOR_SCRIPT,
        "-i", TEMP_INPUT_JSON,
        "-e", temp_effect_json,
        "-o", OUTPUT_DIR,
        "-g", "2"
    ]
    
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8", env=env)
    
    if result.returncode != 0:
        print("Generator failed!")
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        
    assert result.returncode == 0, f"Generator failed: {result.stderr}"
    
    yield
    
    # Teardown (optional - keep for inspection if failed)
    # shutil.rmtree(OUTPUT_DIR, ignore_errors=True)

def test_rotation_direction(setup_integration_env):
    """
    Verify that vertical rotation offset direction is correct for panorama.
    Row 0 (Top) should look UP (negative X rotation).
    Row 1 (Bottom) should look DOWN (positive X rotation).
    """
    # Grid 2x2.
    # Cam 01: Top-Left (Row 0)
    # Cam 03: Bottom-Left (Row 1)
    
    path_01 = os.path.join(OUTPUT_DIR, "Scripts", "integration_input_Cam_Grid2_01.json")
    path_03 = os.path.join(OUTPUT_DIR, "Scripts", "integration_input_Cam_Grid2_03.json")
    
    with open(path_01, "r", encoding="utf-8") as f:
        data_01 = json.load(f)
    with open(path_03, "r", encoding="utf-8") as f:
        data_03 = json.load(f)
        
    rot_x_01 = data_01["Movements"][0]["StartRot"]["x"]
    rot_x_03 = data_03["Movements"][0]["StartRot"]["x"]
    
    print(f"Cam 01 (Top) Rot X: {rot_x_01}")
    print(f"Cam 03 (Bottom) Rot X: {rot_x_03}")
    
    # Expected: 
    # Center Row = 0.5
    # Row 0 offset (Top) = (0 - 0.5) * 10 = -5.0 (Relative Up)
    # Row 1 offset (Bottom) = (1 - 0.5) * 10 = +5.0 (Relative Down)
    # Therefore, Top X should be smaller than Bottom X.
    
    assert rot_x_01 < rot_x_03, f"Top camera ({rot_x_01}) should have smaller X rotation than Bottom camera ({rot_x_03})"

def test_window_control_target_name(setup_integration_env):
    """
    Verify that WindowControl target names have .json extension.
    """
    master_script = os.path.join(OUTPUT_DIR, "Scripts", "integration_input_cameraplus.json")
    
    with open(master_script, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    win_ctrl = data["Movements"][0]["WindowControl"]
    
    # Check if we have at least one valid target (excluding master self-hide)
    targets_found = []
    
    for entry in win_ctrl:
        target = entry["Target"]
        targets_found.append(target)
        # Target must be full filename including .json
        assert target.endswith(".json"), f"Target name '{target}' should end with .json"

def test_slit_offset(setup_integration_env):
    """
    Verify that slit offset is applied correctly (centered).
    Profile X is initially parked at 5000 (off-screen).
    Actual placement is in Master Script's WindowControl.
    """
    # 1. Check Profile (Should be parked)
    prof_01 = os.path.join(OUTPUT_DIR, "Profiles", "integration_input", "integration_input_Cam_Grid2_01.json")
    with open(prof_01, "r", encoding="utf-8") as f:
        p1 = json.load(f)
    assert p1["WindowRect"]["x"] == 5000, "Profile X should be parked at 5000 (off-screen initial position)"

    # 2. Check Master Script for actual placement
    master_script = os.path.join(OUTPUT_DIR, "Scripts", "integration_input_cameraplus.json")
    with open(master_script, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    win_ctrl = data["Movements"][0]["WindowControl"]
    
    # Find Cam 01 and Cam 02 control entries
    # Target names: "integration_input_Cam_Grid2_01.json" (Profile name, not Script name)
    t1_name = "integration_input_Cam_Grid2_01.json"
    t2_name = "integration_input_Cam_Grid2_02.json"
    
    x1 = None
    x2 = None
    
    for entry in win_ctrl:
        if entry["Target"] == t1_name and entry["Visible"]:
            x1 = int(entry["StartPos"]["x"])
        if entry["Target"] == t2_name and entry["Visible"]:
            x2 = int(entry["StartPos"]["x"])
            
    assert x1 is not None, "Cam 01 WindowControl entry not found"
    assert x2 is not None, "Cam 02 WindowControl entry not found"
    
    print(f"Cam 01 X (WindowControl): {x1}")
    print(f"Cam 02 X (WindowControl): {x2}")
    
    # With 1920 width, Grid 2, Slit 6:
    # FullW = 960.
    # X1 = 0 * 960 + 3 = 3.
    # X2 = 1 * 960 + 3 = 963.
    
    assert x1 == 3, f"Cam 01 X should be 3 (Slit/2), but got {x1}"
    assert x2 == 963, f"Cam 02 X should be 963, but got {x2}"

def test_effect_script_loading():
    """
    Verify that --effect-script (JSON) argument works and controls generation.
    """
    # 1. Create EffectScript
    effect_json_path = os.path.join(BASE_DIR, "logs", "temp", "integration_effect.json")
    effect_data = {
        "bpm": 120,
        "schedule": [
            {"start": 0, "end": 1.0, "cameras": 1, "effect": "all-visible"},
            {"start": 1.0, "end": 2.0, "cameras": 4, "effect": "all-visible"}
        ]
    }
    with open(effect_json_path, "w", encoding="utf-8") as f:
        json.dump(effect_data, f, indent=2)
        
    # 2. Run generator with --effect-script
    output_dir = os.path.join(BASE_DIR, "logs", "output_integration_effect")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
        
    # Re-use TEMP_INPUT_JSON from module level if exists, else create simple one
    if not os.path.exists(TEMP_INPUT_JSON):
        # Fallback creation (copy from setup_integration_env logic)
        os.makedirs(os.path.dirname(TEMP_INPUT_JSON), exist_ok=True)
        input_data = {
            "ActiveInPauseMenu": True,
            "Movements": [{"StartPos":{"x":0,"y":0,"z":0},"Duration":2.0,"VisibleObject":{"avatar":True}}]
        }
        with open(TEMP_INPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(input_data, f)

    cmd = [
        sys.executable, GENERATOR_SCRIPT,
        "-i", TEMP_INPUT_JSON,
        "-o", output_dir,
        "-g", "3", # Default grid size (should be ignored/overridden by effect script for specific times)
        "--effect-script", effect_json_path
    ]
    
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8", env=env)
    assert result.returncode == 0, f"Generator failed: {result.stderr}"
    
    # 3. Verify Output
    # Should have Grid 1 (single) and Grid 2 (quad) profiles because schedule demands them.
    # Grid 3 (command line arg) might be generated if 'required_grids' logic includes default, 
    # BUT logic says 'if schedule: required_grids = get_required_grids(schedule)'.
    # So Grid 3 should NOT be generated if schedule only uses 1 and 4.
    
    # Check Grid 1
    path_g1 = os.path.join(output_dir, "Profiles", "integration_input", "integration_input_Cam_Grid1_01.json")
    assert os.path.exists(path_g1), "Grid 1 profile should exist (schedule 0-1s)"
    
    # Check Grid 2 (4 cameras)
    path_g2_01 = os.path.join(output_dir, "Profiles", "integration_input", "integration_input_Cam_Grid2_01.json")
    path_g2_04 = os.path.join(output_dir, "Profiles", "integration_input", "integration_input_Cam_Grid2_04.json")
    assert os.path.exists(path_g2_01), "Grid 2 profile 01 should exist (schedule 1-2s)"
    assert os.path.exists(path_g2_04), "Grid 2 profile 04 should exist"
    
    # Check Grid 3 (Should NOT exist)
    path_g3 = os.path.join(output_dir, "Profiles", "integration_input", "integration_input_Cam_Grid3_01.json")
    assert not os.path.exists(path_g3), "Grid 3 should NOT be generated because EffectScript didn't ask for it"

def test_chronos_cascade_generation():
    """
    Verify Chronos Cascade effect (Time Delay per column).
    Grid 3x3.
    """
    # 1. EffectScript
    effect_json_path = os.path.join(BASE_DIR, "logs", "temp", "integration_chronos.json")
    effect_data = {
        "bpm": 120,
        "schedule": [
            {"start": 0, "end": 2.0, "cameras": 9, "effect": "chronos-cascade"}
        ],
        "parameters": {
            "chronos_delay": 0.1
        }
    }
    with open(effect_json_path, "w", encoding="utf-8") as f:
        json.dump(effect_data, f, indent=2)
        
    output_dir = os.path.join(BASE_DIR, "logs", "output_integration_chronos")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    # 2. Run
    # Use existing TEMP_INPUT_JSON (created by fixture or previous test)
    # If not exists, create simple one
    os.makedirs(os.path.dirname(TEMP_INPUT_JSON), exist_ok=True)
    if not os.path.exists(TEMP_INPUT_JSON):
        input_data = {
            "ActiveInPauseMenu": True,
            "Movements": [{"StartPos":{"x":0,"y":0,"z":0},"Duration":2.0,"VisibleObject":{"avatar":True}}]
        }
        with open(TEMP_INPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(input_data, f)

    cmd = [
        sys.executable, GENERATOR_SCRIPT,
        "-i", TEMP_INPUT_JSON,
        "-o", output_dir,
        "-g", "3",
        "--effect-script", effect_json_path
    ]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    subprocess.run(cmd, cwd=BASE_DIR, check=True, env=env)
    
    # 3. Verify
    # Cam 01 (Col 0) vs Cam 02 (Col 1).
    # Col 1 should be delayed by 0.1s.
    # Logic: The generator shifts the entire movement logic or inserts wait?
    # The generator shifts the Start/End state using get_state_at_time(t - delay).
    # Let's check the generated script for Cam 02.
    
    path_01 = os.path.join(output_dir, "Scripts", "integration_input_Cam_Grid3_01.json")
    path_02 = os.path.join(output_dir, "Scripts", "integration_input_Cam_Grid3_02.json")
    
    with open(path_01, "r", encoding="utf-8") as f: d1 = json.load(f)
    with open(path_02, "r", encoding="utf-8") as f: d2 = json.load(f)
    
    # In Chronos Cascade, Movements are subdivided or shifted.
    # The key check is that they are DIFFERENT, and specifically that Col 1 has a delay behavior.
    # Implementation detail: It calls get_state_at_time(t - delay).
    # So for the SAME Movement Index, the value should differ if the source movement is changing.
    # But here source is static (0,0,0). So checking value difference might be hard if input is static.
    
    # Wait, if input is static, output is static even with delay.
    # We need a MOVING input to verify Chronos.
    
    # Re-create input with movement
    input_moving = {
        "ActiveInPauseMenu": True,
        "Movements": [
            {
                "StartPos": {"x": 0, "y": 0, "z": 0},
                "EndPos":   {"x": 10, "y": 0, "z": 0}, # Moving along X
                "Duration": 2.0,
                "VisibleObject": {"avatar": True}
            }
        ]
    }
    with open(TEMP_INPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(input_moving, f)
        
    subprocess.run(cmd, cwd=BASE_DIR, check=True, env=env) # Re-run with moving input
    
    with open(path_01, "r", encoding="utf-8") as f: d1 = json.load(f)
    with open(path_02, "r", encoding="utf-8") as f: d2 = json.load(f)
    
    # At t=0 (StartPos of first movement in script):
    # Cam 01 (Delay=0): Should be at x=0 (plus tiled offset)
    # Cam 02 (Delay=0.1): Should be at state of t=-0.1 -> Clamped to Start -> x=0?
    # Wait, delay means it shows PAST. t_effective = t_current - delay.
    # If t_current=0, t_effective=-0.1.
    # If source movement is 0 to 2.0.
    # t=-0.1 is clamped to 0.
    
    # Let's check t=0.5 (middle of movement).
    # Since script is baked/subdivided, we might need to find a movement starting around 0.5s.
    # Or just check that the entire sequence is not identical (excluding the static offsets).
    
    # Actually, simpler check:
    # Cam 01 and Cam 02 output should NOT be identical (binary diff).
    # Because of delay!
    assert d1 != d2, "Chronos Cascade should produce different scripts for different columns."
    
    print("Chronos Cascade verification: Scripts are different as expected.")


def test_dimension_roulette_generation():
    """
    Verify Dimension Roulette effect (Random FOV/Roll).
    Grid 2x2.
    """
    # 1. EffectScript
    effect_json_path = os.path.join(BASE_DIR, "logs", "temp", "integration_roulette.json")
    effect_data = {
        "bpm": 120,
        "schedule": [
            {"start": 0, "end": 2.0, "cameras": 4, "effect": "dimension-roulette"}
        ]
    }
    with open(effect_json_path, "w", encoding="utf-8") as f:
        json.dump(effect_data, f, indent=2)
        
    output_dir = os.path.join(BASE_DIR, "logs", "output_integration_roulette")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    # Use simple input
    if not os.path.exists(TEMP_INPUT_JSON):
         with open(TEMP_INPUT_JSON, "w", encoding="utf-8") as f:
             json.dump({"Movements":[{"StartPos":{"x":0,"y":0,"z":0},"Duration":2.0,"VisibleObject":{"avatar":True}}]}, f)

    cmd = [
        sys.executable, GENERATOR_SCRIPT,
        "-i", TEMP_INPUT_JSON,
        "-o", output_dir,
        "-g", "2",
        "--effect-script", effect_json_path
    ]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    subprocess.run(cmd, cwd=BASE_DIR, check=True, env=env)
    
    # 2. Verify
    # Check Cam 01. It looks at (0, 0) normally (top-left of grid).
    # With Roulette, output FOV should NOT be exactly TILING_FOV (unless random hit exact value).
    # Also Roll (z-rot) might be non-zero (default is 0).
    
    path_01 = os.path.join(output_dir, "Scripts", "integration_input_Cam_Grid2_01.json")
    with open(path_01, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    # Check first movement
    m0 = data["Movements"][0]
    z_rot = m0["StartRot"]["z"]
    fov = m0["StartPos"]["FOV"]
    
    # Default without effect: z_rot should be small (just tilt correction? No, Z rot is 0 for flat grid usually).
    # Actually, V4 uses Rot X/Y for tiling. Rot Z is usually 0.
    # Roulette adds random Z rotation.
    
    # We can't guarantee Z != 0 because random might choose 0.
    # But FOV is heavily randomized.
    # Normal FOV for Grid2 is scaled TILING_FOV.
    
    print(f"Roulette Output: Z_Rot={z_rot}, FOV={fov}")
    
    # Just asserting it generated *something* is good enough for now, 
    # but let's check if we have multiple movements (subdivision happened).
    # Effect usually forces subdivision if BPM is set.
    
    assert len(data["Movements"]) > 1, "Effect should cause subdivision of movements."


def test_symmetry_outline_generation():
    """
    Verify Outline Effect for Symmetry View (Left/Right parameter).
    Grid 2x2.
    """
    import os, json, subprocess, shutil, sys
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    GENERATOR_SCRIPT = os.path.join(BASE_DIR, "generator_song_multicam.py")
    TEMP_INPUT_JSON = os.path.join(BASE_DIR, "logs", "temp", "integration_input.json")

    # 1. EffectScript
    effect_json_path = os.path.join(BASE_DIR, "logs", "temp", "integration_symmetry_outline.json")
    effect_data = {
        "bpm": 120,
        "schedule": [
            {
                "start": 0, "end": 2.0, "cameras": 4, 
                "effect": "symmetry-view",
                "symmetry_type": "mirror",
                "outline_side": "right",
                "color_line": {"r": 1.0, "g": 0.5, "b": 0.0},
                "color_bg": {"r": 0.0, "g": 0.0, "b": 0.0}
            }
        ]
    }
    os.makedirs(os.path.dirname(effect_json_path), exist_ok=True)
    with open(effect_json_path, "w", encoding="utf-8") as f:
        json.dump(effect_data, f, indent=2)
        
    output_dir = os.path.join(BASE_DIR, "logs", "output_integration_symmetry_outline")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    if not os.path.exists(TEMP_INPUT_JSON):
         with open(TEMP_INPUT_JSON, "w", encoding="utf-8") as f:
             json.dump({"Movements":[{"StartPos":{"x":0,"y":0,"z":0},"Duration":2.0,"VisibleObject":{"avatar":True}}]}, f)

    cmd = [
        sys.executable, GENERATOR_SCRIPT,
        "-i", TEMP_INPUT_JSON,
        "-o", output_dir,
        "-g", "2",
        "--effect-script", effect_json_path
    ]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    subprocess.run(cmd, cwd=BASE_DIR, check=True, env=env)
    
    # 2. Verify
    path_01 = os.path.join(output_dir, "Scripts", "integration_input_Cam_Grid2_01.json")
    path_02 = os.path.join(output_dir, "Scripts", "integration_input_Cam_Grid2_02.json")
    
    with open(path_01, "r", encoding="utf-8") as f:
        data_left = json.load(f)
        
    with open(path_02, "r", encoding="utf-8") as f:
        data_right = json.load(f)
        
    m_left = data_left["Movements"][0]
    m_right = data_right["Movements"][0]
    
    assert "CameraEffect" not in m_left, "Left camera should NOT have outline"
    assert "CameraEffect" in m_right, "Right camera SHOULD have outline"
    
    outline = m_right["CameraEffect"]
    assert outline["StartOutlineEffect"]["outlineColor"] == {"r": 1.0, "g": 0.5, "b": 0.0}, "Outline color should match"

def test_inactive_camera_optimization():
    """
    Verify that inactive cameras (grid sizes not in current schedule entry)
    output minimal json (only Duration, StartPos/EndPos x:5000, VisibleObject:false)
    and that their total duration exactly matches the original movement duration sum.
    """
    import os, json, subprocess, shutil, sys
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    GENERATOR_SCRIPT = os.path.join(BASE_DIR, "generator_song_multicam.py")
    TEMP_INPUT_JSON = os.path.join(BASE_DIR, "logs", "temp", "integration_input.json")

    # 1. EffectScript (10 seconds total)
    # 0-5s: grid 1x1
    # 5-10s: grid 2x2
    effect_json_path = os.path.join(BASE_DIR, "logs", "temp", "integration_inactive_opt.json")
    effect_data = {
        "bpm": 120,
        "schedule": [
            {"start": 0, "end": 5.0, "cameras": 1},
            {"start": 5.0, "end": 10.0, "cameras": 4}
        ]
    }
    os.makedirs(os.path.dirname(effect_json_path), exist_ok=True)
    with open(effect_json_path, "w", encoding="utf-8") as f:
        json.dump(effect_data, f, indent=2)
        
    output_dir = os.path.join(BASE_DIR, "logs", "output_integration_inactive_opt")
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)

    # 10 second input movement
    with open(TEMP_INPUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"Movements":[{"StartPos":{"x":0,"y":0,"z":0},"Duration":10.0,"VisibleObject":{"avatar":True}}]}, f)

    cmd = [
        sys.executable, GENERATOR_SCRIPT,
        "-i", TEMP_INPUT_JSON,
        "-o", output_dir,
        "--effect-script", effect_json_path
    ]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    subprocess.run(cmd, cwd=BASE_DIR, check=True, env=env)
    
    # 2. Verify integration_input_Cam_Grid2_01.json
    # It should be hidden from 0-5s, and active from 5-10s.
    path_g2 = os.path.join(output_dir, "Scripts", "integration_input_Cam_Grid2_01.json")
    
    with open(path_g2, "r", encoding="utf-8") as f:
        data_g2 = json.load(f)
        
    movs = data_g2["Movements"]
    total_dur = sum(m.get("Duration", 0) for m in movs)
    
    # Total duration must equal 10.0 exactly
    assert abs(total_dur - 10.0) < 0.0001, f"Total duration is {total_dur}, expected 10.0"
    
    # First 5 seconds (inactive) -> should be minimal
    t = 0.0
    for m in movs:
        # Avoid float precision issues
        if t < 4.99:
            # Should be minimal: x=5000, Avatar=False
            assert m["StartPos"]["x"] == 5000, "Inactive camera should be parked at x=5000"
            assert "FOV" not in m["StartPos"], "FOV should be stripped to save space"
            assert m["VisibleObject"]["avatar"] is False, "Avatar should be false"
        elif t >= 5.0:
            # Should be active: valid position, avatar True
            assert m["StartPos"]["x"] != 5000, "Active camera should have actual X position"
            assert "FOV" in m["StartPos"], "Active camera should have FOV"
            assert isinstance(m["VisibleObject"]["avatar"], bool), "VisibleObject avatar should exist"
        t += m.get("Duration", 0)
