from car_control_A.behavior_fsm import BehaviorFSM, BehaviorState
from car_control_A.contracts import DrivingCommand, ExecutionStatus


def command(command_id: str, action: str = "STOP", **kwargs: object) -> DrivingCommand:
    confidence = float(kwargs.pop("confidence", 0.99))
    return DrivingCommand(command_id, 1.0, 10.0, confidence, action, **kwargs)


def test_confirmation_expiry_timeout_and_terminal_uniqueness() -> None:
    fsm = BehaviorFSM(command_timeout_s=2.0)
    confirming = command("confirm", is_ambiguous=True)
    assert fsm.submit(confirming, now_s=2.0).state is BehaviorState.CONFIRMING
    assert fsm.confirm("confirm", approved=True, now_s=3.0).state is BehaviorState.APPROACH_STOP
    succeeded = fsm.complete("confirm", now_s=3.5, detail="stopped")
    assert succeeded.status is ExecutionStatus.SUCCEEDED
    assert fsm.complete("confirm", now_s=4.0, detail="again") is succeeded

    expired = command("expired")
    assert fsm.submit(expired, now_s=11.0).feedback.status is ExecutionStatus.EXPIRED
    active = command("timeout", action="SET_SPEED", target_speed_mps=5.0)
    fsm.submit(active, now_s=2.0)
    assert fsm.tick(now_s=4.1)[0].status is ExecutionStatus.TIMED_OUT


def test_low_confidence_is_confirmed_and_rejection_is_terminal() -> None:
    fsm = BehaviorFSM()
    result = fsm.submit(command("low", confidence=0.1), now_s=2.0)
    assert result.state is BehaviorState.CONFIRMING
    assert fsm.confirm("low", approved=False, now_s=2.1).feedback.status is ExecutionStatus.REJECTED


def test_confirmation_checks_expiry_and_timeout_before_approval() -> None:
    fsm = BehaviorFSM(command_timeout_s=2.0)
    expiring = DrivingCommand("expiry", 1.0, 3.0, 0.1, "STOP")
    fsm.submit(expiring, now_s=1.0)
    assert fsm.confirm("expiry", approved=True, now_s=3.0).feedback.status is ExecutionStatus.EXPIRED
    waiting = DrivingCommand("waiting", 1.0, 10.0, 0.1, "STOP")
    fsm.submit(waiting, now_s=1.0)
    assert fsm.confirm("waiting", approved=True, now_s=3.1).feedback.status is ExecutionStatus.TIMED_OUT


def test_new_command_preempts_old_active_command_without_later_state_change() -> None:
    fsm = BehaviorFSM()
    fsm.submit(command("speed", action="SET_SPEED", target_speed_mps=5.0), now_s=1.0)
    stop = fsm.submit(command("stop"), now_s=2.0)
    assert stop.state is BehaviorState.APPROACH_STOP
    old = fsm.complete("speed", now_s=3.0, detail="stale")
    assert old.status is ExecutionStatus.FAILED
    assert fsm.state is BehaviorState.APPROACH_STOP


def test_complete_and_fail_enforce_expiry_or_timeout_without_prior_tick() -> None:
    expiry_fsm = BehaviorFSM(command_timeout_s=20.0)
    expiry_fsm.submit(DrivingCommand("expiry", 1.0, 3.0, 0.99, "STOP"), now_s=1.0)
    assert expiry_fsm.complete("expiry", now_s=3.0, detail="too late").status is ExecutionStatus.EXPIRED

    timeout_fsm = BehaviorFSM(command_timeout_s=2.0)
    timeout_fsm.submit(DrivingCommand("timeout", 1.0, 10.0, 0.99, "STOP"), now_s=1.0)
    assert timeout_fsm.fail("timeout", now_s=3.1, detail="too late").status is ExecutionStatus.TIMED_OUT


def test_safety_override_is_terminal_and_idempotent() -> None:
    fsm = BehaviorFSM()
    fsm.submit(command("speed", action="SET_SPEED", target_speed_mps=5.0), now_s=1.0)
    overridden = fsm.safety_override("speed", now_s=2.0, detail="LOW_TTC")
    assert overridden is not None
    assert overridden.status is ExecutionStatus.SAFETY_OVERRIDE
    assert fsm.safety_override("speed", now_s=2.1, detail="again") is overridden
