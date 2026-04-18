import pytest
import sys
import os

# Add parent directory to path so we can import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from multicam_effects import get_vortex_spin_rotation

def test_vortex_spin_basic():
    """Test basic rotation without wave check"""
    # Speed 60 deg/sec, Time 1.0s -> 60 deg
    entry = {"effect": "vortex-spin", "speed": 60.0}
    rot = get_vortex_spin_rotation(entry, 1.0, 0, 0)
    assert rot == 60.0

    # Time 2.0s -> 120 deg
    rot = get_vortex_spin_rotation(entry, 2.0, 0, 0)
    assert rot == 120.0

def test_vortex_spin_wave():
    """Test wave mode delay"""
    # Speed 100 deg/sec
    # Delay factor is hardcoded approx 0.2 per (row+col)
    entry = {"effect": "vortex-spin", "speed": 100.0, "mode": "wave"}
    
    # (0,0) -> No delay
    rot_00 = get_vortex_spin_rotation(entry, 1.0, 0, 0)
    assert rot_00 == 100.0 * 1.0
    
    # (1,1) -> Delay = (1+1)*0.2 = 0.4s
    # Effective time = 1.0 - 0.4 = 0.6s
    # Rot = 0.6 * 100 = 60.0
    rot_11 = get_vortex_spin_rotation(entry, 1.0, 1, 1)
    assert abs(rot_11 - 60.0) < 0.001

def test_vortex_spin_ignore():
    """Should return 0 for other effects"""
    entry = {"effect": "other"}
    rot = get_vortex_spin_rotation(entry, 10.0, 0, 0)
    assert rot == 0.0
