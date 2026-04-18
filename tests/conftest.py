
import pytest
import os
import json
import shutil
import sys

# Force UTF-8 for Windows to avoid UnicodeEncodeError in tests
if sys.platform == "win32":
    os.environ["PYTHONUTF8"] = "1"
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if hasattr(sys.stderr, "reconfigure"):
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

@pytest.fixture
def temp_output_dir(tmp_path):
    """
    Creates a temporary output directory that is cleaned up after test.
    Using pytest's tmp_path fixture.
    """
    d = tmp_path / "output_test"
    d.mkdir()
    return str(d)

@pytest.fixture
def song_script_basic():
    """
    Returns a basic SongScript dictionary with one movement (2.0s).
    Default Pos: (0, 2, -3). Rot: (0, 0, 0).
    """
    return {
        "ActiveInPauseMenu": True,
        "Movements": [
            {
                "StartPos": {"x": 0, "y": 2.0, "z": -3.0, "FOV": 60.0},
                "StartRot": {"x": 0, "y": 0, "z": 0},
                "EndPos":   {"x": 0, "y": 2.0, "z": -3.0, "FOV": 60.0},
                "EndRot":   {"x": 0, "y": 0, "z": 0},
                "Duration": 2.0,
                "Delay": 0.0,
                "EaseTransition": True,
                "VisibleObject": {"avatar": True}
            }
        ]
    }

@pytest.fixture
def effect_script_dynamic_grid():
    """
    Effect script that changes grid size over time.
    0-2s: 1x1 (1 cam)
    2-4s: 2x2 (4 cams)
    4-6s: 3x3 (9 cams)
    """
    return {
        "bpm": 60, # 1 beat = 1 sec
        "schedule": [
            {"start": 0, "end": 2.0, "cameras": [1]},
            {"start": 2.0, "end": 4.0, "cameras": [4]},
            {"start": 4.0, "end": 6.0, "cameras": [9]},
        ]
    }

@pytest.fixture
def effect_script_chronos():
    """
    Chronos Cascade effect.
    """
    return {
        "bpm": 60,
        "schedule": [
            {"start": 0, "end": 10.0, "effect": "chronos-cascade", "delay": 0.5, "cameras": [4]}
        ]
    }
