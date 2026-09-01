from __future__ import annotations

import pytest

from voice_group.vehicle_nlu.src.b1_service import process_asr_text
from voice_group.nlu_b2.parser import parse_command


@pytest.mark.parametrize(
    "text,expected_speed",
    [
        ("减速至40公里每小时", 40),
        ("将车速减至40公里每小时", 40),
        ("请减速至20公里每小时并保持合适车距", 20),

        ("前车开得比较慢，先按40公里每小时的速度行驶", 40),
        ("前车行驶缓慢，请把速度稳定在20公里每小时", 20),

        ("考虑到前车速度较低，请把本车速度调至35公里每小时", 35),
        ("本车改以35公里每小时行驶", 35),
        ("本车先采用35公里每小时的速度行驶", 35),

        ("车速请调整至40公里每小时", 40),

        ("前方有骑自行车的人，本车先按30公里每小时行驶", 30),
        ("右前方骑行者正在前进，把本车车速调至25公里每小时", 25),
    ],
)
def test_numeric_target_speed_routes_as_set_speed(
    text: str,
    expected_speed: int,
) -> None:
    b1 = process_asr_text(
        request_id="b1-r2-speed",
        text=text,
        asr_confidence=None,
    )

    assert b1["intent"] == "SET_SPEED"
    assert b1["status"] == "valid"
    assert b1["route"] == "fast"

    b2 = parse_command(b1)

    assert b2["intent"] == "SET_SPEED"
    assert b2["status"] == "valid"
    assert b2["slots"]["speed"] == expected_speed
    assert b2["slots"]["unit"] == "km/h"


@pytest.mark.parametrize(
    "text",
    [
        "请减速",
        "前方危险，放慢速度",
        "速度降一点",
    ],
)
def test_relative_nonnumeric_slowdown_remains_slow_down(
    text: str,
) -> None:
    b1 = process_asr_text(
        request_id="b1-r2-relative",
        text=text,
        asr_confidence=None,
    )

    assert b1["intent"] == "SLOW_DOWN"
    assert b1["status"] == "valid"
    assert b1["route"] == "fast"

    b2 = parse_command(b1)

    assert b2["intent"] == "SLOW_DOWN"
    assert b2["status"] == "valid"
    assert b2["slots"]["mode"] == "RELATIVE"


@pytest.mark.parametrize(
    "text,expected_direction",
    [
        ("请变入左侧目标车道", "LEFT"),
        ("请变入右侧目标车道", "RIGHT"),
    ],
)
def test_change_into_target_lane_is_change_lane(
    text: str,
    expected_direction: str,
) -> None:
    b1 = process_asr_text(
        request_id="b1-r2-lane",
        text=text,
        asr_confidence=None,
    )

    assert b1["intent"] == "CHANGE_LANE"
    assert b1["status"] == "valid"
    assert b1["route"] == "fast"

    b2 = parse_command(b1)

    assert b2["intent"] == "CHANGE_LANE"
    assert b2["status"] == "valid"
    assert b2["slots"]["direction"] == expected_direction
