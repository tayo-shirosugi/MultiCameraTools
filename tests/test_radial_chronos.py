
import pytest
import os
import json
import subprocess
import sys
import shutil

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATOR_SCRIPT = os.path.join(BASE_DIR, "generator_song_multicam.py")
TEMP_STATE_DIR = os.path.join(BASE_DIR, "logs", "temp", "radial_test")
OUTPUT_DIR = os.path.join(BASE_DIR, "logs", "output_radial_test")

@pytest.fixture(scope="module")
def setup_radial_env():
    os.makedirs(TEMP_STATE_DIR, exist_ok=True)
    yield
    # Cleanup optional
    # shutil.rmtree(TEMP_STATE_DIR, ignore_errors=True)
    # shutil.rmtree(OUTPUT_DIR, ignore_errors=True)

def test_radial_chronos_delay_logic():
    """
    Directly test the get_radial_chronos_delay logic
    """
    from multicam_effects import get_radial_chronos_delay
    
    # Grid 3x3
    # Center is (1,1)
    # Corners are (0,0), (0,2), (2,0), (2,2)
    # Sides are (0,1), (1,0), (1,2), (2,1)
    
    grid_size = 3
    entry = {"effect": "radial-chronos", "delay": 0.5}
    
    # Center -> dist 0
    assert get_radial_chronos_delay(entry, 1, 1, grid_size) == 0.0
    
    # Side -> dist 1.0
    assert get_radial_chronos_delay(entry, 0, 1, grid_size) == 0.5 * 1.0
    
    # Corner -> dist sqrt(1^2 + 1^2) = 1.414...
    expected_corner = 0.5 * (2**0.5)
    assert abs(get_radial_chronos_delay(entry, 0, 0, grid_size) - expected_corner) < 0.0001
    
    # Grid 5x5
    # Center (2,2)
    grid_size = 5
    entry = {"effect": "radial-chronos", "delay": 1.0}
    
    # Validating dist from (2,2) to (0,0) -> sqrt(2^2 + 2^2) = sqrt(8) = 2.828...
    expected_corner_5 = (8**0.5) * 1.0
    assert abs(get_radial_chronos_delay(entry, 0, 0, grid_size) - expected_corner_5) < 0.0001


def test_radial_chronos_generation(setup_radial_env):
    """
    Integration test: Run generator with radial-chronos and check script output
    """
    # 1. Input SongScript
    input_json = os.path.join(TEMP_STATE_DIR, "radial_input.json")
    with open(input_json, "w") as f:
        json.dump({
            "Movements": [
                {
                    "StartPos": {"x": 0, "y": 0, "z": 0, "FOV": 60},
                    "EndPos":   {"x": 10, "y": 0, "z": 0, "FOV": 60},
                    "Duration": 2.0
                }
            ]
        }, f)
        
    # 2. EffectScript
    effect_json = os.path.join(TEMP_STATE_DIR, "radial_effect.json")
    with open(effect_json, "w") as f:
        json.dump({
            "bpm": 60,
            "schedule": [
                {"start": 0, "cameras": 9, "effect": "radial-chronos", "delay": 1.0}
            ]
        }, f)
        
    # 3. Run Generator
    cmd = [
        sys.executable, GENERATOR_SCRIPT,
        "-i", input_json,
        "-o", OUTPUT_DIR,
        "--effect-script", effect_json
    ]
    # Use same python executable
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    subprocess.check_call(cmd, cwd=BASE_DIR, env=env)
    
    # 4. Check Output
    scripts_dir = os.path.join(OUTPUT_DIR, "Scripts")
    
    # Load Cam 05 (Center)
    with open(os.path.join(scripts_dir, "radial_input_Cam_Grid3_05.json"), "r") as f:
        cam05 = json.load(f)
        
    # Load Cam 01 (Corner)
    with open(os.path.join(scripts_dir, "radial_input_Cam_Grid3_01.json"), "r") as f:
        cam01 = json.load(f)
        
    # Check EndPos difference
    c05_end = cam05["Movements"][0]["EndPos"]
    c01_end = cam01["Movements"][0]["EndPos"]
    
    print(f"Cam05 End: {c05_end}")
    print(f"Cam01 End: {c01_end}")
    
    assert c05_end != c01_end, "Center and Corner cameras should have different states due to delay"
