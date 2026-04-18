import pytest
from multicam_effects import get_diagonal_wave_delay

def test_diagonal_wave_delay():
    """
    Diagonal Wave: (row + col) * delay
    """
    effect_entry = {
        "effect": "diagonal-wave",
        "delay": 0.5
    }
    
    # Grid 3x3
    # (0,0) -> 0
    assert get_diagonal_wave_delay(effect_entry, 0, 0, 3) == 0.0
    
    # (0,1) -> 0.5
    assert get_diagonal_wave_delay(effect_entry, 0, 1, 3) == 0.5
    
    # (1,0) -> 0.5
    assert get_diagonal_wave_delay(effect_entry, 1, 0, 3) == 0.5
    
    # (1,1) -> 1.0
    assert get_diagonal_wave_delay(effect_entry, 1, 1, 3) == 1.0
    
    # (2,2) -> 2.0
    assert get_diagonal_wave_delay(effect_entry, 2, 2, 3) == 2.0

def test_diagonal_wave_ignore_others():
    entry = {"effect": "other"}
    assert get_diagonal_wave_delay(entry, 0, 0, 3) == 0.0

def test_static_outline_params_defaults():
    from multicam_effects import get_static_outline_params
    
    entry = {"effect": "symmetry-view"}
    params = get_static_outline_params(entry)
    
    assert params["enableOutlineEffect"] is True
    assert params["StartOutlineEffect"]["outlineEffectOnly"] == 1.0
    assert params["StartOutlineEffect"]["outlineColor"] == {"r": 0.0, "g": 0.0, "b": 0.0}
    assert params["StartOutlineEffect"]["outlineBackgroundColor"] == {"r": 1.0, "g": 1.0, "b": 1.0}

def test_static_outline_params_custom_colors():
    from multicam_effects import get_static_outline_params
    
    entry = {
        "effect": "symmetry-view",
        "color_line": {"r": 1.0, "g": 0.0, "b": 0.0},
        "color_bg": {"r": 0.0, "g": 0.0, "b": 0.0}
    }
    params = get_static_outline_params(entry)
    
    assert params["StartOutlineEffect"]["outlineColor"] == {"r": 1.0, "g": 0.0, "b": 0.0}
    assert params["StartOutlineEffect"]["outlineBackgroundColor"] == {"r": 0.0, "g": 0.0, "b": 0.0}
    assert params["EndOutlineEffect"]["outlineColor"] == {"r": 1.0, "g": 0.0, "b": 0.0}
    assert params["EndOutlineEffect"]["outlineBackgroundColor"] == {"r": 0.0, "g": 0.0, "b": 0.0}
