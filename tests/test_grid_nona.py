
import pytest
import os
import json
from generator_song_multicam import generate
from multicam_utils import OFF_SCREEN_X

def test_nona_grid_generation(song_script_basic, temp_output_dir):
    """
    Test 3x3 grid generation (9 cameras).
    Verify Center Camera behavior and Corner Camera offsets.
    """
    input_path = os.path.join(temp_output_dir, "input.json")
    with open(input_path, "w") as f:
        json.dump(song_script_basic, f)
        
    generate(input_path, grid_size=3, output_dir=temp_output_dir)
    
    # Load Center Camera (05)
    s5_path = os.path.join(temp_output_dir, "Scripts", "input_Cam_Grid3_05.json")
    if not os.path.exists(s5_path):
        s5_path = os.path.join(temp_output_dir, "Scripts", "Cam_Grid3_05.json")
    with open(s5_path, "r") as f:
        d5 = json.load(f)
        
    # Check Center Logic (Row 1, Col 1 -> Offset 0)
    rot_x5 = d5["Movements"][0]["StartRot"]["x"]
    
    # Expected Pitch: LookAt only.
    # Cam Y=2.0 (unscaled), Target Y=1.5. dy = -0.5.
    # Cam Z ~ -6.0. dz = 6.0.
    # Pitch ~ atan(0.5/6) ~ 4.7 degrees.
    assert 4.0 < rot_x5 < 5.0, f"Center cam pitch should be purely LookAt (~4.7), got {rot_x5}"
    
    # Load Corner Cameras
    s1_path = os.path.join(temp_output_dir, "Scripts", "input_Cam_Grid3_01.json") # Top-Left
    if not os.path.exists(s1_path):
        s1_path = os.path.join(temp_output_dir, "Scripts", "Cam_Grid3_01.json")
        
    s9_path = os.path.join(temp_output_dir, "Scripts", "input_Cam_Grid3_09.json") # Bottom-Right
    if not os.path.exists(s9_path):
        s9_path = os.path.join(temp_output_dir, "Scripts", "Cam_Grid3_09.json")
    
    with open(s1_path, "r") as f: d1 = json.load(f)
    with open(s9_path, "r") as f: d9 = json.load(f)
    
    rot_x1 = d1["Movements"][0]["StartRot"]["x"]
    rot_x9 = d9["Movements"][0]["StartRot"]["x"]
    
    # Top Row (Row 0): Offset -10 deg.
    # Bottom Row (Row 2): Offset +10 deg.
    
    assert rot_x1 < -5.0, f"Top cam pitch should include -10 offset, got {rot_x1}"
    assert rot_x9 > 5.0, f"Bottom cam pitch should include +10 offset, got {rot_x9}"

    # Check Slit (WindowRect)
    # Grid 3x3. Width=1920, Height=1080. Slit=6.
    # Full Cell = 640x360.
    # Window Width = 640 - 6 = 634.
    # Col 0 (Left):   x = 0*640 + 3 = 3.   RightEdge = 637.
    # Col 1 (Center): x = 1*640 + 3 = 643. LeftEdge = 643. Gap = 6px (637-643).
    # Col 2 (Right):  x = 2*640 + 3 = 1283.
    
    prof_path_1 = os.path.join(temp_output_dir, "Profiles", "SongMultiCam", "input_Cam_Grid3_01.json")
    if not os.path.exists(prof_path_1):
        prof_path_1 = os.path.join(temp_output_dir, "Profiles", "SongMultiCam", "Cam_Grid3_01.json")
        
    prof_path_5 = os.path.join(temp_output_dir, "Profiles", "SongMultiCam", "input_Cam_Grid3_05.json")
    if not os.path.exists(prof_path_5):
        prof_path_5 = os.path.join(temp_output_dir, "Profiles", "SongMultiCam", "Cam_Grid3_05.json")
        
    prof_path_9 = os.path.join(temp_output_dir, "Profiles", "SongMultiCam", "input_Cam_Grid3_09.json")
    if not os.path.exists(prof_path_9):
        prof_path_9 = os.path.join(temp_output_dir, "Profiles", "SongMultiCam", "Cam_Grid3_09.json")

    with open(prof_path_1, "r") as f: p1 = json.load(f)
    with open(prof_path_5, "r") as f: p5 = json.load(f)
    with open(prof_path_9, "r") as f: p9 = json.load(f)
    
    # 許容誤差なしでチェック (整数計算なので完全一致するはず)
    assert p1["WindowRect"]["x"] == OFF_SCREEN_X, f"Col 0 X should be {OFF_SCREEN_X}, got {p1['WindowRect']['x']}"
    assert p5["WindowRect"]["x"] == OFF_SCREEN_X, f"Col 1 X should be {OFF_SCREEN_X}, got {p5['WindowRect']['x']}"
    assert p9["WindowRect"]["x"] == OFF_SCREEN_X, f"Col 2 X should be {OFF_SCREEN_X}, got {p9['WindowRect']['x']}"
    
    assert p1["WindowRect"]["width"] == 634, f"Width should be 634, got {p1['WindowRect']['width']}"
