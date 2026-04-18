
import pytest
from multicam_utils import calc_distance_scale

def test_tiling_scale_logic():
    # Original behavior (Current Code)
    # Scale based on 60 -> 10 directly
    orig_fov = 60.0
    tile_fov = 10.0
    grid_size = 3
    
    # Current implementation
    current_scale = calc_distance_scale(orig_fov, tile_fov)
    # tan(30) / tan(5) = 0.577 / 0.087 = 6.63
    print(f"Current Scale (60->10): {current_scale}")
    
    # Proposed behavior (Mosaic Logic)
    # We want the composite 3x3 grid to cover 60 degrees.
    # So each tile covers 60 / 3 = 20 degrees.
    # We map this 20-degree slice to a 10-degree camera.
    # Scale = tan(10) / tan(5) = 0.176 / 0.087 = 2.02
    
    eff_fov = orig_fov / grid_size
    proposed_scale = calc_distance_scale(eff_fov, tile_fov)
    print(f"Proposed Scale (20->10): {proposed_scale}")
    
    # Check what creates a 'Zoomed In' effect?
    # Scale determines distance from origin.
    # Standard Pos: z = -3.0.
    # Current Scale (6.6) -> z = -3.0 * 6.6 = -19.8m. (Far away)
    # Proposed Scale (2.0) -> z = -3.0 * 2.0 = -6.0m. (Closer)
    
    # Visual check:
    # At 19.8m, a 10-degree FOV sees height H_far.
    # H_far = 2 * 19.8 * tan(5) = 39.6 * 0.087 = 3.44m.
    # At 1x (3m), a 60-degree FOV sees height H_orig.
    # H_orig = 2 * 3.0 * tan(30) = 6.0 * 0.577 = 3.46m.
    # They match! 
    # So 'Current Scale' makes ONE tile see the SAME HEIGHT as the original.
    
    # If 3x3 grid uses Current Scale:
    # Center Tile sees 3.44m height (Full Avatar).
    # Top Tile sees another 3.44m above it. Bottom sees 3.44m below.
    # Total Grid Height = ~10m.
    # Original Height = 3.46m.
    # Conclusion: Current Logic creates a ZOOMED OUT (Wide Angle / Panorama) view.
    # The avatar appears SMALL in the context of the full 3x3 grid.
    
    # User says: "Avatar is 90% displayed" (Zoomed In?)
    # "Generally avatar is 90% displayed"
    # Maybe they mean "90% of the avatar is visible" (i.e. cut off)?
    # Or "Avatar occupies 90% of the screen"?
    
    # If I use 'Proposed Scale' (2.0x, 6m distance):
    # One tile (10 deg) at 6m sees height:
    # H_prop = 2 * 6.0 * tan(5) = 12.0 * 0.087 = 1.04m.
    # Original Height was 3.46m.
    # So one tile sees ~1/3 of the height.
    # 3 stacked tiles see ~3.12m. (Roughly 1.0x Original).
    # So 'Proposed Scale' correctly recreates the Original Framing across the grid.
    
    # Why does the user verify "Avatar is 90% displayed" as "Not original"?
    # If using Current Logic, one tile sees 3.44m.
    # The avatar (say 1.8m) occupies ~50% of the center tile.
    # If using Proposed Logic, one tile sees 1.04m.
    # The avatar's torso (1.0m) fills the center tile.
    # The legs (1.0m) fill the bottom tile.
    
    # If the user sees "Avatar is 90% displayed", maybe they are looking at the **Center Tile Only**?
    # Or maybe the Grid View on their monitor shows the avatar taking up most of the space?
    
    # Re-reading: "Originally shooting from back... but this script ... basically avatar is 90% displayed."
    # "Center of camera reflected?"
    
    # Ideally, 9 cameras (3x3) should look like 1 big camera.
    # So 'Proposed Scale' is the mathematically correct one for "Tiling".
    
    # Let's assert that we want Proposed Scale logic.
    assert abs(proposed_scale - 2.0) < 0.1
