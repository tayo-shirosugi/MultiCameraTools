import pytest
from multicam_effects import get_outline_effect_params

def test_outline_effect_basic():
    """
    基本動作テスト:
    - trigger 前のカメラは None（通常映像を表示。黒画面バグ回避のため）
    - trigger 時刻以降はパラメータを返す
    """
    effect_entry = {
        "effect": "outline-fill",
        "duration_beats": 1.0, # 1 beat transition
        "step_delay": 1.0      # 1 beat delay per step
    }
    
    # Grid 3x3, Cam 0 (0,0) -> Step Index = 0, Trigger = 0.0 beats
    
    # t=0.0 (Beat 0): Start of transition -> Start=0, End=1
    params_t0 = get_outline_effect_params(effect_entry, 0, 3, 0.0, 60.0)
    assert params_t0 is not None
    assert params_t0["enableOutlineEffect"] is True
    assert params_t0["StartOutlineEffect"]["outlineEffectOnly"] == 0.0
    assert params_t0["EndOutlineEffect"]["outlineEffectOnly"] == 1.0
    
    # t=0.5 (Beat 0.5): Middle of transition -> Start=0.5, End=1 (approx)
    params_t05 = get_outline_effect_params(effect_entry, 0, 3, 0.5, 60.0)
    assert params_t05["StartOutlineEffect"]["outlineEffectOnly"] == 0.5
    
    # t=1.0 (Beat 1.0): End of transition -> Start=1.0, End=1.0
    params_t1 = get_outline_effect_params(effect_entry, 0, 3, 1.0, 60.0)
    assert params_t1["StartOutlineEffect"]["outlineEffectOnly"] == 1.0
    assert params_t1["EndOutlineEffect"]["outlineEffectOnly"] == 1.0
    
    # Cam 4 (1,1) -> Step Index = 2, Trigger = 2.0 beats
    # t=0.0 (Beat 0) < Trigger 2.0
    # -> None (黒画面バグ回避: trigger前はエフェクト無効、通常映像を表示)
    params_c4_t0 = get_outline_effect_params(effect_entry, 4, 3, 0.0, 60.0)
    assert params_c4_t0 is None
    
    # t=2.0 (Beat 2) == Trigger 2.0 -> Start of transition: Start=0, End=1
    params_c4_t2 = get_outline_effect_params(effect_entry, 4, 3, 2.0, 60.0)
    assert params_c4_t2["StartOutlineEffect"]["outlineEffectOnly"] == 0.0
    assert params_c4_t2["EndOutlineEffect"]["outlineEffectOnly"] == 1.0

def test_outline_effect_colors():
    """
    色設定の反映確認
    """
    effect_entry = {
        "effect": "outline-fill",
        "color_line": {"r": 1, "g": 0, "b": 0},
        "color_bg": {"r": 0, "g": 1, "b": 0}
    }
    
    params = get_outline_effect_params(effect_entry, 0, 3, 0.0, 60.0)
    assert params["StartOutlineEffect"]["outlineColor"] == {"r": 1, "g": 0, "b": 0}
    assert params["StartOutlineEffect"]["outlineBackgroundColor"] == {"r": 0, "g": 1, "b": 0}

def test_outline_effect_ignore_others():
    """
    異なるエフェクト名は無視
    """
    effect_entry = {"effect": "other-effect"}
    params = get_outline_effect_params(effect_entry, 0, 3, 0.0, 60.0)
    assert params is None
