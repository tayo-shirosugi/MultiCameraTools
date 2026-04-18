"""
test_utils.py
multicam_utils モジュールの単体テスト。
"""
import sys
import os
import math
import pytest

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multicam_utils import (
    lerp, lerp_pos, lerp_rot,
    calc_distance_scale, scale_position, get_hfov,
    subdivide_movements, get_state_at_time,
)


# ============================================================
# lerp
# ============================================================

class TestLerp:
    def test_lerp_start(self):
        assert lerp(0, 10, 0.0) == 0.0
    
    def test_lerp_end(self):
        assert lerp(0, 10, 1.0) == 10.0
    
    def test_lerp_midpoint(self):
        assert lerp(0, 10, 0.5) == 5.0
    
    def test_lerp_quarter(self):
        assert lerp(0, 100, 0.25) == 25.0
    
    def test_lerp_negative(self):
        assert lerp(-10, 10, 0.5) == 0.0


class TestLerpPos:
    def test_interpolation(self):
        start = {"x": 0, "y": 0, "z": 0, "FOV": 60}
        end = {"x": 10, "y": 20, "z": 30, "FOV": 90}
        result = lerp_pos(start, end, 0.5)
        assert result["x"] == 5.0
        assert result["y"] == 10.0
        assert result["z"] == 15.0
        assert result["FOV"] == 75.0
    
    def test_start_boundary(self):
        start = {"x": 1, "y": 2, "z": 3, "FOV": 60}
        end = {"x": 10, "y": 20, "z": 30, "FOV": 90}
        result = lerp_pos(start, end, 0.0)
        assert result["x"] == 1.0
        assert result["y"] == 2.0
    
    def test_missing_fields_use_defaults(self):
        """フィールドがない場合はデフォルト値(0, FOV=60)が使われる"""
        result = lerp_pos({}, {}, 0.5)
        assert result["x"] == 0.0
        assert result["FOV"] == 60.0


class TestLerpRot:
    def test_interpolation(self):
        start = {"x": 0, "y": 0, "z": 0}
        end = {"x": 90, "y": 180, "z": 45}
        result = lerp_rot(start, end, 0.5)
        assert result["x"] == 45.0
        assert result["y"] == 90.0
        assert result["z"] == 22.5


# ============================================================
# FOV & Distance
# ============================================================

class TestCalcDistanceScale:
    def test_same_fov_no_scaling(self):
        """同じFOVなら距離補正不要"""
        assert calc_distance_scale(10, 10) == pytest.approx(1.0)
    
    def test_wider_fov_scales_farther(self):
        """元FOVが広いほど遠くに配置"""
        scale = calc_distance_scale(60, 10)
        assert scale > 1.0
    
    def test_known_ratio_90_to_10(self):
        """90° → 10° は約 tan(45°)/tan(5°) ≈ 11.43"""
        scale = calc_distance_scale(90, 10)
        expected = math.tan(math.radians(45)) / math.tan(math.radians(5))
        assert scale == pytest.approx(expected, rel=1e-6)
    
    def test_monotonic(self):
        """元FOVが大きいほどスケールも大きい"""
        s30 = calc_distance_scale(30, 10)
        s60 = calc_distance_scale(60, 10)
        s90 = calc_distance_scale(90, 10)
        assert s30 < s60 < s90


class TestScalePosition:
    def test_identity_scale(self):
        pos = {"x": 3.0, "y": 1.5, "z": -4.0}
        result = scale_position(pos, 1.0)
        assert result["x"] == pytest.approx(3.0)
        assert result["y"] == pytest.approx(1.5)
        assert result["z"] == pytest.approx(-4.0)
    
    def test_double_distance(self):
        pos = {"x": 3.0, "y": 1.5, "z": -4.0}
        result = scale_position(pos, 2.0)
        assert result["x"] == pytest.approx(6.0)
        assert result["y"] == pytest.approx(1.5)  # Yはスケールしない
        assert result["z"] == pytest.approx(-8.0)
    
    def test_y_preserved(self):
        """Y座標は高さなのでスケーリングされないことを確認"""
        pos = {"x": 0.0, "y": 5.0, "z": 0.0}
        result = scale_position(pos, 100.0)
        assert result["y"] == 5.0


class TestGetHfov:
    def test_wider_than_vertical(self):
        """16:9画面ではHFOVはVFOVより広い"""
        hfov = get_hfov(60)
        assert hfov > 60
    
    def test_90_vfov(self):
        """VFOV 90° の場合の期待値を検証"""
        hfov = get_hfov(90)
        # 16:9 aspect = 1.778
        expected = 2 * math.degrees(math.atan(math.tan(math.radians(45)) * (1920/1080)))
        assert hfov == pytest.approx(expected, rel=1e-6)


# ============================================================
# Movement Subdivision
# ============================================================

class TestSubdivideMovements:
    def test_single_beat_no_split(self):
        """1ビートに収まるMovementは分割されない"""
        movements = [{"Duration": 0.5, "Delay": 0.0, "StartPos": {"x": 0, "y": 0, "z": 0, "FOV": 60}, "EndPos": {"x": 10, "y": 0, "z": 0, "FOV": 60}}]
        # BPM=120 → 1beat=0.5s → Duration=0.5s → 1subdivision
        result = subdivide_movements(movements, bpm=120)
        assert len(result) == 1
    
    def test_two_beats_split(self):
        """2ビートのMovementは2分割"""
        movements = [{"Duration": 1.0, "Delay": 0.0, "StartPos": {"x": 0, "y": 0, "z": 0, "FOV": 60}, "EndPos": {"x": 10, "y": 0, "z": 0, "FOV": 60}}]
        # BPM=120 → 1beat=0.5s. Duration=1.0s.
        # beats_per_sub=1 -> unit=0.5s -> 2 subs.
        result = subdivide_movements(movements, bpm=120, beats_per_sub=1)
        assert len(result) == 2
    
    def test_duration_preserved(self):
        """分割後の合計Durationが元と一致"""
        movements = [{"Duration": 3.0, "Delay": 0.5}]
        result = subdivide_movements(movements, bpm=120, beats_per_sub=1)
        total_dur = sum(m["Duration"] for m in result)
        total_delay = sum(m.get("Delay", 0) for m in result)
        assert total_dur == pytest.approx(3.0, rel=1e-3)
        assert total_delay == pytest.approx(0.5)  # Delayは最初の分割のみ
    
    def test_delay_only_first(self):
        """Delayは最初のサブ分割にのみ付与"""
        movements = [{"Duration": 2.0, "Delay": 1.0}]
        # Duration=2.0. BeatPerSub=1 -> 0.5s. n=4.
        result = subdivide_movements(movements, bpm=120, beats_per_sub=1)
        assert result[0]["Delay"] == 1.0
        for m in result[1:]:
            assert m["Delay"] == 0.0
    
    def test_interpolation_endpoints(self):
        """分割境界の位置が線形補間で正しく計算される"""
        movements = [{
            "Duration": 1.0,
            "StartPos": {"x": 0, "y": 0, "z": 0, "FOV": 60},
            "EndPos": {"x": 10, "y": 0, "z": 0, "FOV": 60},
        }]
        # Duration=1.0. BeatPerSub=1 -> 0.5s. n=2.
        result = subdivide_movements(movements, bpm=120, beats_per_sub=1)  # 2分割
        # 最初のサブ: StartPos.x=0, EndPos.x=5
        assert result[0]["StartPos"]["x"] == pytest.approx(0.0)
        assert result[0]["EndPos"]["x"] == pytest.approx(5.0)
        # 2番目のサブ: StartPos.x=5, EndPos.x=10
        assert result[1]["StartPos"]["x"] == pytest.approx(5.0)
        assert result[1]["EndPos"]["x"] == pytest.approx(10.0)
    
    def test_camera_effect_first_sub_only(self):
        """CameraEffectは最初のサブ分割にのみコピー"""
        movements = [{
            "Duration": 1.0,
            "CameraEffect": {"enableDoF": True},
        }]
        result = subdivide_movements(movements, bpm=120, beats_per_sub=1)
        assert "CameraEffect" in result[0]
        for m in result[1:]:
            assert "CameraEffect" not in m
    
    def test_beats_per_sub(self):
        """beats_per_sub=2 のとき2ビートごとに1分割"""
        movements = [{"Duration": 2.0}]
        # BPM=120, beats_per_sub=2 → 1beat=0.5s, 2beats=1.0s → 2分割
        result = subdivide_movements(movements, bpm=120, beats_per_sub=2)
        assert len(result) == 2


# ============================================================
# Time Sampling
# ============================================================

class TestGetStateAtTime:
    def test_sample_start(self):
        """t=0 で StartPos が返る"""
        m = [{"Duration": 1.0, "StartPos": {"x": 10}, "EndPos": {"x": 20}}]
        s = get_state_at_time(m, 0.0)
        assert s["x"] == pytest.approx(10.0)
    
    def test_sample_mid(self):
        """t=0.5 で中間値が返る"""
        m = [{"Duration": 1.0, "StartPos": {"x": 10}, "EndPos": {"x": 20}}]
        s = get_state_at_time(m, 0.5)
        assert s["x"] == pytest.approx(15.0)
    
    def test_sample_end(self):
        """t=1.0 手前で EndPos に近づく"""
        m = [{"Duration": 1.0, "StartPos": {"x": 10}, "EndPos": {"x": 20}}]
        s = get_state_at_time(m, 0.999)
        assert s["x"] == pytest.approx(20.0, rel=1e-3)
    
    def test_sample_out_of_bounds_neg(self):
        """t < 0 で StartPos"""
        m = [{"Duration": 1.0, "StartPos": {"x": 10}}]
        s = get_state_at_time(m, -1.0)
        assert s["x"] == pytest.approx(10.0)
    
    def test_sample_out_of_bounds_pos(self):
        """t > duration で EndPos"""
        m = [{"Duration": 1.0, "EndPos": {"x": 20}}]
        s = get_state_at_time(m, 2.0)
        assert s["x"] == pytest.approx(20.0)
    
    def test_multi_segment(self):
        """複数のMovementを横断"""
        # M0: 0-1s, x:0->10
        # M1: 1-2s, x:10->30
        m = [
            {"Duration": 1.0, "StartPos": {"x": 0}, "EndPos": {"x": 10}},
            {"Duration": 1.0, "StartPos": {"x": 10}, "EndPos": {"x": 30}},
        ]
        # t=1.5 (M1の0.5s時点) -> 10 + (30-10)*0.5 = 20
        s = get_state_at_time(m, 1.5)
        assert s["x"] == pytest.approx(20.0)
    
    def test_with_delay(self):
        """Delayがある場合の挙動"""
        # M0: Delay 0.5s, Dur 1.0s. (0.0-0.5s wait, 0.5-1.5s move)
        m = [
            {"Delay": 0.5, "Duration": 1.0, "StartPos": {"x": 10}, "EndPos": {"x": 20}}
        ]
        # t=0.25 (Delay中) -> StartPos
        s_wait = get_state_at_time(m, 0.25)
        assert s_wait["x"] == pytest.approx(10.0)
        
        # t=1.0 (Move中: 0.5開始なので経過0.5s) -> lerp(10,20, 0.5) = 15
        s_move = get_state_at_time(m, 1.0)
        assert s_move["x"] == pytest.approx(15.0)
