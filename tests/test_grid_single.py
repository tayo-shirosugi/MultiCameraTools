
import pytest
import os
import json
import sys
import shutil
from generator_song_multicam import generate

def test_single_grid_generation(song_script_basic, temp_output_dir):
    """
    Test 1x1 grid generation.
    Expected behavior: 
    - Should generate 1 Script and 1 Profile.
    - Should NOT apply heavy Tiling Scaling (FOV should remain close to original 60, not 10).
    - Or if it enforces 10, verify that. (Design decision needed)
    """
    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp", "test_single")
    if os.path.exists(input_dir):
        shutil.rmtree(input_dir)
    os.makedirs(input_dir, exist_ok=True)
    temp_output_dir = input_dir
    input_path = os.path.join(temp_output_dir, "input.json")
    with open(input_path, "w") as f:
        json.dump(song_script_basic, f)
        
    # Generate Grid 1 (1x1)
    sys.stderr.write(f"DEBUG: Starting generate. input={input_path}\n")
    
    try:
        generate(input_path, grid_size=1, output_dir=temp_output_dir)
    except SystemExit as e:
        sys.stderr.write(f"DEBUG: SystemExit caught: {e}\n")
        # If exit code is not 0, fail test
        if e.code != 0:
            pytest.fail(f"Generator exited with code {e.code}")
    except Exception as e:
        sys.stderr.write(f"DEBUG: Exception caught: {e}\n")
        raise e
            
    sys.stderr.write("DEBUG: generate finished.\n")
    
    # Check Profile
    # Sometimes prefix is missing in test env? allow both
    prof_name_1 = "input_Cam_Grid1_01.json"
    prof_name_2 = "Cam_Grid1_01.json"
    prof_path_1 = os.path.join(temp_output_dir, "Profiles", "SongMultiCam", prof_name_1)
    prof_path_2 = os.path.join(temp_output_dir, "Profiles", "SongMultiCam", prof_name_2)
    
    sys.stderr.write(f"DEBUG: Checking {prof_path_1} or {prof_path_2}\n")
    
    prof_path = None
    if os.path.exists(prof_path_1):
        prof_path = prof_path_1
    elif os.path.exists(prof_path_2):
        prof_path = prof_path_2
        
    if not prof_path:
        sys.stderr.write(f"DEBUG: listdir({temp_output_dir}) = {os.listdir(temp_output_dir)}\n")
        prof_dir = os.path.join(temp_output_dir, "Profiles", "SongMultiCam")
        if os.path.exists(prof_dir):
            sys.stderr.write(f"DEBUG: listdir({prof_dir}) = {os.listdir(prof_dir)}\n")
        else:
            sys.stderr.write(f"DEBUG: {prof_dir} does not exist.\n")
            
    assert prof_path is not None, f"Profile not found: {prof_name_1} or {prof_name_2}"
    
    # Check Script
    script_path = os.path.join(temp_output_dir, "Scripts", "input_Cam_Grid1_01.json")
    assert os.path.exists(script_path)
    
    with open(script_path, "r") as f:
        data = json.load(f)
        
    m0 = data["Movements"][0]
    # Input Z = -3.0. FOV = 60.
    # If force TILING_FOV(10), Z will be ~ -20.
    # If 1x1 logic handles FOV nicely, Z should be -3.0.
    
    z = m0["StartPos"]["z"]
    print(f"Grid 1x1 Z: {z}")
    
    # Current implementation likely uses TILING_FOV for everything.
    # User might want 1x1 to be 'Normal Camera'.
    # If so, Z should be close to -3.0.
    # I will assert < -10 to confirm current behavior (Telephoto), 
    # OR > -5 to confirm "Normal" behavior.
    
    # Let's assume for now that logic is "Everything is Tile".
    # But for 1x1, tiling usually implies full screen.
    # If strict 10 deg, it is zoomed in.
    
    # For Grid 1x1, we expect original FOV (60) and Scale ~1.0.
    # Original Z = -3.0.
    
    assert -3.1 < z < -2.9, f"Grid 1x1 Z should be close to -3.0 (No Scaling), but got {z}" 
