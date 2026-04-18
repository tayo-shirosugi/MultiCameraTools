"""
test_effects.py
multicam_effects モジュールの単体テスト。
"""
import sys
import os
import pytest

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multicam_effects import find_effect_for_time, apply_window_visibility


# ============================================================
# Schedule Lookup
# ============================================================

class TestFindEffectForTime:
    """時間ベースのエフェクトスケジュール検索テスト"""
    
    SCHEDULE = [
        {"start": 0, "end": 30, "effect": "mosaic-blink"},
        {"start": 30, "end": 60, "effect": "chronos-cascade", "delay": 0.5},
        {"start": 60, "end": 999999, "effect": "all-visible"},
    ]
    
    def test_first_entry(self):
        result = find_effect_for_time(self.SCHEDULE, 0.0)
        assert result["effect"] == "mosaic-blink"
    
    def test_mid_first_entry(self):
        result = find_effect_for_time(self.SCHEDULE, 15.0)
        assert result["effect"] == "mosaic-blink"
    
    def test_boundary_second_entry(self):
        """30秒ちょうどで次のエントリに切り替わる"""
        result = find_effect_for_time(self.SCHEDULE, 30.0)
        assert result["effect"] == "chronos-cascade"
    
    def test_preserves_params(self):
        """エフェクト固有パラメータ (delay等) が保持される"""
        result = find_effect_for_time(self.SCHEDULE, 45.0)
        assert result["delay"] == 0.5
    
    def test_last_entry(self):
        result = find_effect_for_time(self.SCHEDULE, 120.0)
        assert result["effect"] == "all-visible"
    
    def test_no_match_returns_all_visible(self):
        """スケジュール外の時間はall-visibleを返す"""
        empty = [{"start": 10, "end": 20, "effect": "mosaic-blink"}]
        result = find_effect_for_time(empty, 5.0)
        assert result["effect"] == "all-visible"
    
    def test_empty_schedule(self):
        result = find_effect_for_time([], 10.0)
        assert result["effect"] == "all-visible"
    
    def test_end_exclusive(self):
        """end は排他的 (start <= t < end)"""
        schedule = [
            {"start": 0, "end": 10, "effect": "A"},
            {"start": 10, "end": 20, "effect": "B"},
        ]
        # t=10.0 は A の end=10 に一致 → A には含まれず B に含まれる
        result = find_effect_for_time(schedule, 10.0)
        assert result["effect"] == "B"


# ============================================================
# Mosaic Blink Pattern
# ============================================================

class TestApplyWindowVisibility:
    """市松パターンのVisible判定テスト"""
    
    def test_all_visible_always_true(self):
        entry = {"effect": "all-visible"}
        for cam_i in range(9):
            assert apply_window_visibility(entry, cam_i, 3, 0) is True
            assert apply_window_visibility(entry, cam_i, 3, 1) is True
    
    def test_no_effect_defaults_visible(self):
        """effectキーがなければall-visible扱い"""
        entry = {}
        assert apply_window_visibility(entry, 0, 3, 0) is True
    
    def test_mosaic_blink_checkerboard_3x3(self):
        """3x3 grid の市松パターンを検証"""
        entry = {"effect": "mosaic-blink"}
        # Movement 0 (偶数): 市松パターンA
        pattern_m0 = [apply_window_visibility(entry, i, 3, 0) for i in range(9)]
        # Movement 1 (奇数): 市松パターンB (反転)
        pattern_m1 = [apply_window_visibility(entry, i, 3, 1) for i in range(9)]
        
        # 3x3 checkerboard (movement_idx=0):
        # row0: T F T
        # row1: F T F
        # row2: T F T
        assert pattern_m0 == [True, False, True, False, True, False, True, False, True]
        # 反転
        assert pattern_m1 == [False, True, False, True, False, True, False, True, False]
    
    def test_mosaic_blink_checkerboard_2x2(self):
        """2x2 grid の市松パターンを検証"""
        entry = {"effect": "mosaic-blink"}
        pattern_m0 = [apply_window_visibility(entry, i, 2, 0) for i in range(4)]
        pattern_m1 = [apply_window_visibility(entry, i, 2, 1) for i in range(4)]
        
        # 2x2 checkerboard (movement_idx=0): T F / F T
        assert pattern_m0 == [True, False, False, True]
        assert pattern_m1 == [False, True, True, False]
    
    def test_mosaic_blink_alternates(self):
        """連続するMovementでパターンが反転する"""
        entry = {"effect": "mosaic-blink"}
        for cam_i in range(9):
            v0 = apply_window_visibility(entry, cam_i, 3, 0)
            v1 = apply_window_visibility(entry, cam_i, 3, 1)
            assert v0 != v1, f"cam_i={cam_i} should alternate"
    
    def test_mosaic_blink_period_2(self):
        """周期2: movement 0 と 2 は同じパターン"""
        entry = {"effect": "mosaic-blink"}
        for cam_i in range(9):
            v0 = apply_window_visibility(entry, cam_i, 3, 0)
            v2 = apply_window_visibility(entry, cam_i, 3, 2)
            assert v0 == v2

class TestMosaicShuffle:
    """Mosaic Shuffleの可視状態判定テスト"""

    def test_mosaic_shuffle_density(self):
        """densityによってある程度表示率が変わるか(完全な確率テストは難しいためシード固定で確認)"""
        entry = {"effect": "mosaic-shuffle", "density": 0.5}
        
        # movement 0 の各カメラの可視状態をチェック
        visibilities = [apply_window_visibility(entry, i, 3, 0) for i in range(9)]
        # シードが固定されているため、結果も固定される
        assert any(visibilities) # 全てFalseにはならないはず
        assert not all(visibilities) # 全てTrueにもならないはず

    def test_mosaic_shuffle_zero_density(self):
        """density 0 なら全て非表示"""
        entry = {"effect": "mosaic-shuffle", "density": 0.0}
        visibilities = [apply_window_visibility(entry, i, 3, 0) for i in range(9)]
        assert not any(visibilities)
        
    def test_mosaic_shuffle_full_density(self):
        """density 1 なら全て表示"""
        entry = {"effect": "mosaic-shuffle", "density": 1.0}
        visibilities = [apply_window_visibility(entry, i, 3, 0) for i in range(9)]
        assert all(visibilities)


# ============================================================
# Grid Switching
# ============================================================

from multicam_effects import get_required_grids

class TestGetRequiredGrids:
    def test_default_grid_3(self):
        """cameras 指定なしなら grid_size=3 (9台) + 常に grid_size=1 (範囲外デフォルト) を含む"""
        schedule = [{"start": 0, "end": 10, "effect": "mosaic-blink"}]
        assert get_required_grids(schedule) == {1, 3}
    
    def test_explicit_cameras(self):
        """cameras=1, 4, 9, 16 → grids={1, 2, 3, 4}"""
        schedule = [
            {"start": 0, "end": 10, "cameras": 1},
            {"start": 10, "end": 20, "cameras": 4},
            {"start": 20, "end": 30, "cameras": 9},
            {"start": 30, "end": 40, "cameras": 16},
        ]
        assert get_required_grids(schedule) == {1, 2, 3, 4}
    
    def test_duplicate_grids(self):
        """重複は排除される（+ 常に grid_size=1 を含む）"""
        schedule = [
            {"start": 0, "cameras": 9},
            {"start": 10, "cameras": 9},
        ]
        assert get_required_grids(schedule) == {1, 3}
    
    def test_empty_schedule(self):
        """空スケジュールでも範囲外デフォルト grid_size=1 が返る"""
        assert get_required_grids([]) == {1}

# ============================================================
# Split View Rotation
# ============================================================

from multicam_effects import get_split_view_rotation_offset

class TestSplitViewRotation:
    """Split View用のY軸回転オフセット計算テスト"""

    def test_split_view_left_col(self):
        entry = {"effect": "split-view", "angle": 90.0}
        assert get_split_view_rotation_offset(entry, col=0, grid_size=3) == -90.0

    def test_split_view_center_col(self):
        entry = {"effect": "split-view", "angle": 90.0}
        assert get_split_view_rotation_offset(entry, col=1, grid_size=3) == 0.0

    def test_split_view_right_col(self):
        entry = {"effect": "split-view", "angle": 90.0}
        assert get_split_view_rotation_offset(entry, col=2, grid_size=3) == 90.0
        
    def test_split_view_custom_angle(self):
        entry = {"effect": "split-view", "angle": 45.0}
        assert get_split_view_rotation_offset(entry, col=0, grid_size=3) == -45.0
        assert get_split_view_rotation_offset(entry, col=2, grid_size=3) == 45.0
        
    def test_not_split_view(self):
        entry = {"effect": "all-visible"}
        assert get_split_view_rotation_offset(entry, col=0, grid_size=3) == 0.0

from multicam_effects import get_surround_view_rotation_offset, get_panoptic_view_rotation_offset

class TestSurroundViewRotation:
    """Surround View用のY軸回転オフセット計算テスト"""
    
    def test_surround_view_angles(self):
        entry = {"effect": "surround-view"}
        assert get_surround_view_rotation_offset(entry, cam_i=0, grid_size=2) == 0.0
        assert get_surround_view_rotation_offset(entry, cam_i=1, grid_size=2) == 90.0
        assert get_surround_view_rotation_offset(entry, cam_i=2, grid_size=2) == 180.0
        assert get_surround_view_rotation_offset(entry, cam_i=3, grid_size=2) == -90.0
        
    def test_surround_view_invalid_grid(self):
        entry = {"effect": "surround-view"}
        # Only valid for grid_size=2 (4 cameras)
        assert get_surround_view_rotation_offset(entry, cam_i=0, grid_size=3) == 0.0

class TestPanopticViewRotation:
    """Panoptic View用のY軸回転オフセット計算テスト"""
    
    def test_panoptic_view_center(self):
        entry = {"effect": "panoptic-view"}
        assert get_panoptic_view_rotation_offset(entry, cam_i=4, grid_size=3) == 0.0
        
    def test_panoptic_view_surroundings(self):
        entry = {"effect": "panoptic-view"}
        assert get_panoptic_view_rotation_offset(entry, cam_i=0, grid_size=3) == -135.0
        assert get_panoptic_view_rotation_offset(entry, cam_i=1, grid_size=3) == 180.0
        assert get_panoptic_view_rotation_offset(entry, cam_i=2, grid_size=3) == 135.0
        assert get_panoptic_view_rotation_offset(entry, cam_i=3, grid_size=3) == -90.0
        assert get_panoptic_view_rotation_offset(entry, cam_i=5, grid_size=3) == 90.0
        assert get_panoptic_view_rotation_offset(entry, cam_i=6, grid_size=3) == -45.0
        assert get_panoptic_view_rotation_offset(entry, cam_i=7, grid_size=3) == 0.0
        assert get_panoptic_view_rotation_offset(entry, cam_i=8, grid_size=3) == 45.0
        
    def test_panoptic_view_invalid_grid(self):
        entry = {"effect": "panoptic-view"}
        assert get_panoptic_view_rotation_offset(entry, cam_i=0, grid_size=4) == 0.0

class TestRandomOutlineFill:
    """Test functionality of random-outline-fill effect"""

    def test_random_outline_fill_triggers(self):
        from multicam_effects import get_outline_effect_params
        effect = {'effect': 'random-outline-fill', 'start': 0.0, 'duration_beats': 36}
        grid_size = 3
        bpm = 120 # 1 beat = 0.5s

        trigger_beats = []
        for cam_i in range(9):
            # trigger前はNoneが返る（黒画面バグ回避のため）
            res_pre = get_outline_effect_params(effect, cam_i, grid_size, 0.0, bpm)
            # cam_i=0はtriger=0なのでNoneでない場合もある（シャッフル次第）
            # → 遠い未来（beat=999）はFilled状態（全カメラ完了後）であり必ず返る
            res_post = get_outline_effect_params(effect, cam_i, grid_size, 999.0, bpm)
            assert res_post is not None
            assert res_post['EndOutlineEffect']['outlineEffectOnly'] == 1.0

            # トリガー時刻を探す（Noneでなくなる最初のビート）
            for t in range(50):
                res = get_outline_effect_params(effect, cam_i, grid_size, float(t), bpm)
                if res is not None:
                    trigger_beats.append((cam_i, t))
                    break

        # 9台全カメラがそれぞれ異なるトリガー時刻を持つ（ランダム順の検証）
        assert len(trigger_beats) == 9, "All 9 cameras should have a trigger time"
        assert len(set(t for c, t in trigger_beats)) == 9, "All trigger times should be distinct"
