
import pytest
from multicam_effects import normalize_schedule, find_effect_for_time

def test_schedule_overlap():
    schedule = [
        {"start": 0, "end": 30, "effect": "A"},
        {"start": 15, "end": 30, "effect": "B"},
        {"start": 30, "end": 60, "effect": "C"}
    ]
    
    normalize_schedule(schedule)
    # After normalize, sorted by start.
    # [0-30, 15-30, 30-60]
    
    # Time 10 -> Should be A.
    e10 = find_effect_for_time(schedule, 10)
    print(f"Time 10: {e10['effect']}")
    
    # Time 20 -> Should be A or B?
    # Logic: First match.
    # 0 <= 20 < 30 -> Match A.
    # So B is never reached?
    e20 = find_effect_for_time(schedule, 20)
    print(f"Time 20: {e20['effect']}")
    
    # If B is never reached, user's sample script is broken.
    assert e20['effect'] == 'B', "Expected B to override A, but logic might be First-Match-Wins"

if __name__ == "__main__":
    test_schedule_overlap()
