
import pytest
import os
import json
import subprocess
import sys
import shutil

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GENERATOR_SCRIPT = os.path.join(BASE_DIR, "generator_song_multicam.py")
TEMP_VAL_DIR = os.path.join(BASE_DIR, "logs", "temp", "validation_test")
OUTPUT_DIR = os.path.join(BASE_DIR, "logs", "output_validation_test")

@pytest.fixture(scope="module")
def setup_val_env():
    os.makedirs(TEMP_VAL_DIR, exist_ok=True)
    yield
    # shutil.rmtree(TEMP_VAL_DIR, ignore_errors=True)

def run_generator(input_path, effect_path=None, expect_fail=False):
    # -e が必須になったため、指定がない場合はダミーの EffectScript を作成
    if effect_path is None:
        effect_path = os.path.join(TEMP_VAL_DIR, "dummy_effect.json")
        with open(effect_path, "w", encoding="utf-8") as f:
            json.dump({"bpm": 120, "schedule": [{"start":0, "cameras":1, "effect":"all-visible"}]}, f)

    cmd = [
        sys.executable, GENERATOR_SCRIPT,
        "-i", input_path,
        "-e", effect_path,
        "-o", OUTPUT_DIR,
        "-g", "1"
    ]
        
    result = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True, encoding="utf-8")
    
    if expect_fail:
        assert result.returncode != 0, f"Generator should have failed but succeeded. Output: {result.stdout}"
        return result
    else:
        assert result.returncode == 0, f"Generator failed. Stderr: {result.stderr}"
        return result

def test_missing_input_file(setup_val_env):
    """
    Test with non-existent input file.
    """
    path = os.path.join(TEMP_VAL_DIR, "non_existent.json")
    if os.path.exists(path):
        os.remove(path)
        
    res = run_generator(path, expect_fail=True)
    # Generator uses print(), so error might be in stdout
    combined = res.stdout + res.stderr
    assert "not found" in combined.lower() or "error" in combined.lower()

def test_invalid_json_format(setup_val_env):
    """
    Test with corrupted JSON file.
    """
    path = os.path.join(TEMP_VAL_DIR, "corrupt.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write("{ invalid json ...")
        
    res = run_generator(path, expect_fail=True)
    combined = res.stdout + res.stderr
    assert "invalid json" in combined.lower() or "error" in combined.lower()

def test_effect_script_missing_bpm(setup_val_env):
    """
    Test EffectScript missing required 'bpm' field.
    """
    # Valid input
    input_path = os.path.join(TEMP_VAL_DIR, "valid_input.json")
    with open(input_path, "w", encoding="utf-8") as f:
        json.dump({"Movements": [{"StartPos":{"x":0,"y":0,"z":0},"Duration":1}]}, f)
        
    # Invalid EffectScript
    effect_path = os.path.join(TEMP_VAL_DIR, "no_bpm.json")
    with open(effect_path, "w", encoding="utf-8") as f:
        json.dump({"schedule": []}, f)
        
    res = run_generator(input_path, effect_path=effect_path, expect_fail=True)
    combined = res.stdout + res.stderr
    assert "must contain 'bpm'" in combined

def test_effect_script_invalid_bpm(setup_val_env):
    """
    Test EffectScript with invalid BPM (<= 0).
    """
    input_path = os.path.join(TEMP_VAL_DIR, "valid_input.json")
    if not os.path.exists(input_path):
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump({"Movements": [{"StartPos":{"x":0,"y":0,"z":0},"Duration":1}]}, f)

    effect_path = os.path.join(TEMP_VAL_DIR, "neg_bpm.json")
    with open(effect_path, "w", encoding="utf-8") as f:
        json.dump({"bpm": -10, "schedule": []}, f)
        
    res = run_generator(input_path, effect_path=effect_path, expect_fail=True)
    combined = res.stdout + res.stderr
    assert "BPM must be positive" in combined

def test_empty_movements(setup_val_env):
    """
    Test SongScript with empty Movements array.
    """
    input_path = os.path.join(TEMP_VAL_DIR, "empty_mov.json")
    with open(input_path, "w", encoding="utf-8") as f:
        json.dump({"Movements": []}, f)
        
    res = run_generator(input_path, expect_fail=True)
    combined = res.stdout + res.stderr
    assert "no movements" in combined.lower() or "empty" in combined.lower()
