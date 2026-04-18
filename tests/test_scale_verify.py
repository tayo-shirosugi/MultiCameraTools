
import pytest
import os
import sys
import subprocess
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATOR_SCRIPT = os.path.join(BASE_DIR, "generator_song_multicam.py")
TEMP_STATE_DIR = os.path.join(BASE_DIR, "logs", "temp", "scale_verify")
OUTPUT_DIR = os.path.join(BASE_DIR, "logs", "output_scale_verify")

@pytest.fixture(scope="module")
def setup_scale_env():
    os.makedirs(TEMP_STATE_DIR, exist_ok=True)
    yield

def test_scale_logic_runtime(setup_scale_env):
    """
    Run generator and check the coordinate scale of generated output.
    """
    # Input with known StartPos
    # StartPos z = -3.0. FOV = 60.
    input_json = os.path.join(TEMP_STATE_DIR, "scale_input.json")
    with open(input_json, "w") as f:
        json.dump({
            "Movements": [{
                "StartPos": {"x": 0, "y": 2.0, "z": -3.0, "FOV": 60},
                "Duration": 1.0
            }]
        }, f)
        
    # Effect Grid 3
    effect_json = os.path.join(TEMP_STATE_DIR, "scale_effect.json")
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
    
    # Check Center Camera (Cam 05)
    # Origin is (0,0,0) usually unless specified in 'scale_position'.
    # Default origin is (0,0,0).
    # Original Pos: x=0, z=-3.0.
    
    # Old Logic (Incorrect): Scale ~6.6. 
    # New z = -3.0 * 6.6 = -19.8.
    
    # New Logic (Correct): Scale ~2.0.
    # New z = -3.0 * 2.0 = -6.0.
    
    profiles_dir = os.path.join(OUTPUT_DIR, "Scripts")
    with open(os.path.join(profiles_dir, "scale_input_Cam_Grid3_05.json"), "r") as f:
        cam05 = json.load(f)
        
    pos = cam05["Movements"][0]["StartPos"]
    z = pos["z"]
    
    print(f"Generated Z: {z}")
    
    # Assert Z is around -6.0, definitely NOT -19.8
    assert abs(z) < 10.0, f"Z should be closer to -6.0, got {z}"
    assert abs(z) > 4.0, f"Z should be > 4.0, got {z}"
