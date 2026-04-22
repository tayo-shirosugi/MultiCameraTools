
import pytest
import os
import json
from generator_song_multicam import generate
from multicam_utils import OFF_SCREEN_X

def test_quad_grid_generation(song_script_basic, temp_output_dir):
    """
    Test 2x2 grid generation (4 cameras).
    Verify Scaling, Tiling Rotation, and Slit positioning.
    """
    input_path = os.path.join(temp_output_dir, "input.json")
    with open(input_path, "w") as f:
        json.dump(song_script_basic, f)
        
    generate(input_path, grid_size=2, output_dir=temp_output_dir)
    
    # Check scaling (Z coordinate)
    # Cam 01 (Top-Left)
    script_name_1 = "input_Cam_Grid2_01.json"
    script_path = os.path.join(temp_output_dir, "Scripts", script_name_1)
    if not os.path.exists(script_path):
        script_path = os.path.join(temp_output_dir, "Scripts", "Cam_Grid2_01.json")
        
    with open(script_path, "r") as f:
        data = json.load(f)
    
    z = data["Movements"][0]["StartPos"]["z"]
    # Expecting scale ~3.06x for 2x2 grid (60/2=30 FOV -> 10 FOV). -3.0 -> -9.18
    assert z < -8.0, f"Distance not scaled properly. Got {z}"
    
    # Check Rotation Relationship (Top vs Bottom)
    # Cam 01 (Top-Left), Cam 03 (Bottom-Left)
    script_path_3 = os.path.join(temp_output_dir, "Scripts", "input_Cam_Grid2_03.json")
    if not os.path.exists(script_path_3):
        script_path_3 = os.path.join(temp_output_dir, "Scripts", "Cam_Grid2_03.json")
    with open(script_path_3, "r") as f:
        data3 = json.load(f)
        
    rot_x1 = data["Movements"][0]["StartRot"]["x"]
    rot_x3 = data3["Movements"][0]["StartRot"]["x"]
    
    # Top cam looks up (smaller/negative pitch relative to center)
    # Bottom cam looks down (larger/positive pitch relative to center)
    assert rot_x1 < rot_x3, f"Top cam pitch ({rot_x1}) should be < Bottom cam pitch ({rot_x3})"
    
    # Check Slit Position (WindowRect)
    # Cam 01 (Col 0), Cam 02 (Col 1)
    prof_path_1 = os.path.join(temp_output_dir, "Profiles", "input", "input_Cam_Grid2_01.json")
    if not os.path.exists(prof_path_1):
        prof_path_1 = os.path.join(temp_output_dir, "Profiles", "input", "Cam_Grid2_01.json")
        
    prof_path_2 = os.path.join(temp_output_dir, "Profiles", "input", "input_Cam_Grid2_02.json")
    if not os.path.exists(prof_path_2):
        prof_path_2 = os.path.join(temp_output_dir, "Profiles", "input", "Cam_Grid2_02.json")
    
    with open(prof_path_1, "r") as f: p1 = json.load(f)
    with open(prof_path_2, "r") as f: p2 = json.load(f)
    
    # Assuming Width=1920, Slit=6
    # Col 0: x = 0*960 + 3 = 3
    # Col 1: x = 1*960 + 3 = 963
    
    assert p1["WindowRect"]["x"] == OFF_SCREEN_X
    assert p2["WindowRect"]["x"] == OFF_SCREEN_X
