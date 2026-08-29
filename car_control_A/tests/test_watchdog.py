import pytest

from car_control_A.watchdog import RuntimeWatchdog


def test_watchdog_brakes_on_timeout_and_module_failure() -> None:
    watchdog = RuntimeWatchdog(timeout_s=1.0)
    watchdog.heartbeat("perception", now_s=1.0)
    assert watchdog.check(now_s=1.5) is None
    assert watchdog.check(now_s=2.1).brake == 1.0
    watchdog.heartbeat("perception", now_s=3.0)
    assert watchdog.module_failed("perception", RuntimeError("boom")).brake == 1.0
    with pytest.raises(ValueError):
        watchdog.heartbeat("", now_s=1.0)


def test_required_module_that_never_heartbeats_brakes_after_grace_and_timeout() -> None:
    watchdog = RuntimeWatchdog(timeout_s=1.0, required_modules=("perception",), startup_grace_s=0.5, started_at_s=10.0)
    assert watchdog.check(now_s=11.49) is None
    assert watchdog.check(now_s=11.5).brake == 1.0


def test_external_pause_does_not_consume_module_timeout_or_startup_grace() -> None:
    watchdog = RuntimeWatchdog(
        timeout_s=1.0,
        required_modules=("perception", "control"),
        startup_grace_s=0.5,
        started_at_s=10.0,
    )
    watchdog.heartbeat("perception", now_s=10.1)
    watchdog.heartbeat("control", now_s=10.1)
    watchdog.pause(now_s=10.2)
    watchdog.resume(now_s=15.2)
    assert watchdog.check(now_s=16.09) is None
    assert watchdog.check(now_s=16.11).brake == 1.0

    startup = RuntimeWatchdog(
        timeout_s=1.0,
        required_modules=("perception",),
        startup_grace_s=0.5,
        started_at_s=10.0,
    )
    startup.pause(now_s=10.2)
    startup.resume(now_s=15.2)
    assert startup.check(now_s=16.49) is None
    assert startup.check(now_s=16.5).brake == 1.0


def test_watchdog_pause_protocol_rejects_invalid_state_transitions() -> None:
    watchdog = RuntimeWatchdog(timeout_s=1.0)
    with pytest.raises(RuntimeError, match="not paused"):
        watchdog.resume(now_s=1.0)
    watchdog.pause(now_s=1.0)
    with pytest.raises(RuntimeError, match="already paused"):
        watchdog.pause(now_s=1.1)
    with pytest.raises(RuntimeError, match="while watchdog is paused"):
        watchdog.heartbeat("control", now_s=1.1)
    with pytest.raises(RuntimeError, match="while it is paused"):
        watchdog.check(now_s=1.1)
    with pytest.raises(ValueError, match="must not precede"):
        watchdog.resume(now_s=0.9)
    watchdog.resume(now_s=1.2)
    watchdog.heartbeat("control", now_s=1.2)
