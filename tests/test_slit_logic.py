
import pytest
import os
import json
import sys
from multicam_utils import RESOLUTION_W, RESOLUTION_H, SLIT_WIDTH, OFF_SCREEN_X

# We don't need to run the full generator to test the logic if we trust the formula,
# but running the generator is the ultimate integration test.

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATOR_SCRIPT = os.path.join(BASE_DIR, "generator_song_multicam.py")
TEMP_STATE_DIR = os.path.join(BASE_DIR, "logs", "temp", "slit_test")
OUTPUT_DIR = os.path.join(BASE_DIR, "logs", "output_slit_test")

@pytest.fixture(scope="module")
def setup_slit_env():
    os.makedirs(TEMP_STATE_DIR, exist_ok=True)
    yield

def test_slit_geometry(setup_slit_env):
    import subprocess
    
    # 1. Create a dummy input and effect script
    # We want to check Grid 3 (9 cameras) specifically as per user query
    grid_size = 3
    
    input_json = os.path.join(TEMP_STATE_DIR, "slit_input.json")
    with open(input_json, "w") as f:
        json.dump({"Movements": [{"Duration": 1.0}]}, f)
        
    # Effect script to force Grid 3
    effect_json = os.path.join(TEMP_STATE_DIR, "slit_effect.json")
    with open(effect_json, "w") as f:
        json.dump({
            "bpm": 120,
            "schedule": [{"start": 0, "cameras": 9}]
        }, f)
        
    cmd = [
        sys.executable, GENERATOR_SCRIPT,
        "-i", input_json,
        "-o", OUTPUT_DIR,
        "--effect-script", effect_json
    ]
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    subprocess.check_call(cmd, cwd=BASE_DIR, env=env)
    
    # 2. Check Generated Profiles
    profiles_dir = os.path.join(OUTPUT_DIR, "Profiles", "SongMultiCam")
    
    # Grid Calculation Expectations
    # full_w = 1920 // 3 = 640
    # w = 640 - 6 = 634
    # sx(col) = col * 640 + 3
    
    expected_w = (1920 // 3) - SLIT_WIDTH
    expected_x_col0 = (0 * (1920 // 3)) + (SLIT_WIDTH // 2)
    expected_x_col1 = (1 * (1920 // 3)) + (SLIT_WIDTH // 2)
    
    # Load Cam 01 (Row 0, Col 0) -> But generator row 0 is top.
    # Cam 01 is Row 0, Col 0.
    # y calculation: ((3 - 1 - 0) * full_h) + 3 = 2 * full_h + 3.
    
    # Check Cam 01
    with open(os.path.join(profiles_dir, "Cam_Grid3_01.json"), "r") as f:
        cam01 = json.load(f)
        rect = cam01["WindowRect"]
        
        print(f"Cam01 Rect: {rect}")
        
        assert rect["width"] == expected_w, f"Width should be {expected_w}, got {rect['width']}"
        assert rect["x"] == OFF_SCREEN_X, f"X in profile should be {OFF_SCREEN_X}, got {rect['x']}"
        
    # Check Cam 02 (Row 0, Col 1)
    with open(os.path.join(profiles_dir, "Cam_Grid3_02.json"), "r") as f:
        cam02 = json.load(f)
        rect = cam02["WindowRect"]
        
        print(f"Cam02 Rect: {rect}")
        
        assert rect["width"] == expected_w
        assert rect["x"] == OFF_SCREEN_X, f"X in profile should be {OFF_SCREEN_X}, got {rect['x']}"
        
    # Verify Gap via Master Script WindowControl (Profile x is now OFF_SCREEN_X)
    master_script_path = os.path.join(profiles_dir, "..", "..", "Scripts", f"{os.path.basename(input_json).split('.')[0]}_cameraplus.json")
    if not os.path.exists(master_script_path):
        # Fallback for different naming schemes
        master_script_path = os.path.join(profiles_dir, "..", "..", "Scripts", "slit_input_cameraplus.json")

    with open(master_script_path, "r") as f:
        master_data = json.load(f)
        movements = master_data.get("Movements", [])
        assert len(movements) > 0
        win_ctrl = movements[0].get("WindowControl", [])
        
        # Find Cam01 and Cam02 in WindowControl
        ctrl01 = next(c for c in win_ctrl if c["Target"] == "Cam_Grid3_01.json")
        ctrl02 = next(c for c in win_ctrl if c["Target"] == "Cam_Grid3_02.json")
        
        real_x01 = ctrl01["StartPos"]["x"]
        real_x02 = ctrl02["StartPos"]["x"]
        
        gap = real_x02 - (real_x01 + expected_w)
        assert gap == SLIT_WIDTH, f"Gap between Cam01 and Cam02 in WindowControl should be {SLIT_WIDTH}, got {gap}"

if __name__ == "__main__":
    # Allow running directly
    sys.exit(pytest.main(["-v", __file__]))
