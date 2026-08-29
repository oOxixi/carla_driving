from car_control_D.benchmark import run_control_safety_benchmark


def test_control_safety_benchmark_has_machine_readable_acceptance() -> None:
    report = run_control_safety_benchmark(iterations=200, warmup=20, threshold_ms=50.0)
    assert report["benchmark"] == "control_safety_hot_path"
    assert report["results"]["safety_arbitration"]["samples"] == 200
    assert report["results"]["integrated_control_step"]["samples"] == 200
    assert report["acceptance"]["passed"] is True
