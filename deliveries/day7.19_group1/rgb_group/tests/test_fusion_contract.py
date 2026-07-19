from rgb_group.fusion_contract import (
    validate_frame_alignment,
)


def test_same_frame_is_aligned():
    assert validate_frame_alignment(100, 100)


def test_one_frame_gap_is_aligned():
    assert validate_frame_alignment(100, 101)


def test_large_frame_gap_is_stale():
    assert not validate_frame_alignment(100, 103)
