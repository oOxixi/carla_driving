"""Process/board telemetry sampling with explicit not-measured reporting.

Memory is always measurable for the planner process.  Power and accelerator
utilization require hardware access; when no probe is configured the sampler
emits a single ``NOT_APPLICABLE`` row with a reason instead of a zero, so no
downstream report can silently turn a missing measurement into a number.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
import subprocess
import threading
import time
from typing import Any, Callable


def _now() -> tuple[str, int]:
    # Same high-resolution monotonic base as the latency traces, so telemetry
    # rows can be correlated with stage marks without a clock-domain caveat.
    return datetime.now(timezone.utc).isoformat(), time.perf_counter_ns()


def _memory_backend() -> str:
    try:
        import psutil  # noqa: F401
    except ImportError:
        pass
    else:
        return "psutil"
    if os.path.isdir("/proc/self"):
        return "proc_status"
    return "win32_psapi"


def sample_process_memory(backend: str | None = None) -> dict[str, Any]:
    """Return rss/peak RSS of the current process in KiB.

    ``backend`` is only used by tests to exercise a specific path; production
    callers leave it as ``None`` and get automatic selection.
    """
    backend = backend or _memory_backend()
    if backend not in {"psutil", "proc_status", "win32_psapi"}:
        raise ValueError(f"unknown memory backend: {backend!r}")
    if backend == "psutil":
        try:
            import psutil
        except ImportError as error:  # pragma: no cover - dependency guard
            raise RuntimeError("psutil backend requested but psutil is missing") from error

        info = psutil.Process().memory_info()
        return {
            "rss_kib": info.rss / 1024.0,
            "peak_rss_kib": getattr(info, "peak_wset", info.rss) / 1024.0,
            "source": "psutil",
        }
    if backend == "proc_status":
        values: dict[str, float] = {}
        with open("/proc/self/status", "r", encoding="utf-8") as stream:
            for line in stream:
                if line.startswith("VmRSS:"):
                    values["rss_kib"] = float(line.split()[1])
                elif line.startswith("VmHWM:"):
                    values["peak_rss_kib"] = float(line.split()[1])
        return {
            "rss_kib": values.get("rss_kib"),
            "peak_rss_kib": values.get("peak_rss_kib"),
            "source": "proc_status",
        }
    counters, ok = _read_process_memory_counters()
    if not ok:
        raise OSError("GetProcessMemoryInfo failed")
    return {
        "rss_kib": counters.WorkingSetSize / 1024.0,
        "peak_rss_kib": counters.PeakWorkingSetSize / 1024.0,
        "source": "win32_psapi",
    }


def machine_load_percent(interval_s: float = 0.5) -> float | None:
    """System-wide CPU load over a short window, or None when unavailable.

    A latency measurement taken on a busy machine is not comparable with one
    taken on an idle machine, so the load at the start of a run is part of the
    measurement environment rather than a diagnostic nicety.
    """
    try:
        import psutil
    except ImportError:
        return None
    try:
        return float(psutil.cpu_percent(interval=interval_s))
    except Exception:  # pragma: no cover - platform guard
        return None


def power_source() -> str:
    """``AC`` / ``BATTERY`` / ``UNKNOWN`` for the current host.

    On battery, Windows reduces the CPU clock (observed ~60% of nominal), which
    changes latency by several times over.  A run's power state therefore has to
    travel with its numbers.
    """
    if os.name != "nt":
        return "UNKNOWN"
    import ctypes

    class SYSTEM_POWER_STATUS(ctypes.Structure):
        _fields_ = [
            ("ACLineStatus", ctypes.c_ubyte),
            ("BatteryFlag", ctypes.c_ubyte),
            ("BatteryLifePercent", ctypes.c_ubyte),
            ("SystemStatusFlag", ctypes.c_ubyte),
            ("BatteryLifeTime", ctypes.c_ulong),
            ("BatteryFullLifeTime", ctypes.c_ulong),
        ]

    status = SYSTEM_POWER_STATUS()
    try:
        ok = ctypes.WinDLL("kernel32", use_last_error=True).GetSystemPowerStatus(
            ctypes.byref(status)
        )
    except OSError:  # pragma: no cover - platform guard
        return "UNKNOWN"
    if not ok:
        return "UNKNOWN"
    return {0: "BATTERY", 1: "AC"}.get(int(status.ACLineStatus), "UNKNOWN")


def cpu_frequency_mhz() -> dict[str, float | None]:
    """Best-effort current/max CPU clock; None where the platform hides it."""
    try:
        import psutil
    except ImportError:
        return {"current_mhz": None, "max_mhz": None}
    try:
        frequency = psutil.cpu_freq()
    except Exception:  # pragma: no cover - platform guard
        return {"current_mhz": None, "max_mhz": None}
    if frequency is None:
        return {"current_mhz": None, "max_mhz": None}
    return {
        "current_mhz": float(frequency.current) if frequency.current else None,
        "max_mhz": float(frequency.max) if frequency.max else None,
    }


def cpu_calibration_ms(
    repeats: int = 5, size: int = 512, trials: int = 3
) -> float | None:
    """A fixed multi-threaded CPU workload, reported as the best of N trials.

    Observed on this project: the same ONNX inference measured 2.7 ms, 27 ms and
    92 ms on the same machine at different times, with the OS power state and
    the achieved clock explaining only part of it.  A fixed calibration
    workload is the only reliable way to tell whether two runs are comparable,
    so it travels with the environment instead of being reconstructed later.

    The **minimum** of several trials is reported: transient interference only
    ever makes a trial slower, so the fastest trial is the most stable estimate
    of what the machine can do.  Single-shot sampling was measured to swing
    7.2 -> 18.7 ms between runs on this host, which is too noisy to compare
    against.
    """
    try:
        import numpy as np
    except ImportError:
        return None
    matrix = np.arange(size * size, dtype=np.float32).reshape(size, size)
    other = matrix.T.copy()
    try:
        matrix @ other  # warm up BLAS and thread pool
        best: float | None = None
        for _ in range(max(1, trials)):
            started = time.perf_counter_ns()
            for _ in range(repeats):
                matrix @ other
            elapsed = (time.perf_counter_ns() - started) / 1e6
            best = elapsed if best is None else min(best, elapsed)
    except Exception:  # pragma: no cover - platform guard
        return None
    return best


def _read_process_memory_counters() -> tuple[Any, bool]:
    """Query the Win32 process memory counters with explicit ctypes signatures.

    Without ``argtypes``/``restype`` ctypes marshals the 64-bit process handle
    as a 32-bit int and the call fails with a zero return value, which is
    exactly the bug this function exists to avoid.
    """
    import ctypes
    from ctypes import wintypes

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.GetCurrentProcess.argtypes = []
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    psapi.GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
        wintypes.DWORD,
    ]
    handle = kernel32.GetCurrentProcess()
    ok = bool(psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb))
    return counters, ok


@dataclass(frozen=True, slots=True)
class ProbeCommand:
    """External probe expected to print one JSON object on stdout."""

    name: str
    command: tuple[str, ...]
    fields: tuple[str, ...]
    timeout_s: float = 10.0

    def read(self) -> dict[str, Any]:
        completed = subprocess.run(
            list(self.command),
            capture_output=True,
            text=True,
            timeout=self.timeout_s,
            check=True,
        )
        payload = json.loads(completed.stdout.strip())
        if not isinstance(payload, dict):
            raise ValueError(f"probe {self.name} must print a JSON object")
        return {field: payload.get(field) for field in self.fields}


@dataclass(slots=True)
class TelemetrySpec:
    interval_s: float = 1.0
    power_probe: ProbeCommand | None = None
    power_scope: str = "board_total"
    power_probe_point: str = "NOT_MEASURED"
    utilization_probe: ProbeCommand | None = None
    utilization_scope: str = "board_total"
    temperature_probe: ProbeCommand | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.interval_s, (int, float)) or self.interval_s <= 0:
            raise ValueError("interval_s must be positive")


class BackgroundMonitor:
    """Sample memory every interval; power/utilization only if probed."""

    def __init__(self, spec: TelemetrySpec | None = None, *, run_id: str = "", round_index: int = 0) -> None:
        self.spec = spec or TelemetrySpec()
        self.run_id = run_id
        self.round_index = round_index
        self.memory_rows: list[dict[str, Any]] = []
        self.power_rows: list[dict[str, Any]] = []
        self.utilization_rows: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._index = 0
        self._cpu_sampler: Callable[[], float | None] = self._cpu_percent_sampler()

    @staticmethod
    def _cpu_percent_sampler() -> Callable[[], float | None]:
        try:
            import psutil
        except ImportError:
            return lambda: None
        process = psutil.Process()
        process.cpu_percent(None)
        return lambda: process.cpu_percent(None)

    def start(self) -> None:
        self.sample_once()
        self._thread = threading.Thread(target=self._loop, name="b3-telemetry", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        while not self._stop.wait(self.spec.interval_s):
            self.sample_once()

    def sample_once(self) -> None:
        wall, monotonic = _now()
        index = self._index
        self._index += 1
        try:
            memory = sample_process_memory()
        except Exception as error:  # pragma: no cover - platform guard
            self.errors.append(f"memory: {type(error).__name__}: {error}")
        else:
            self.memory_rows.append(
                {
                    "run_id": self.run_id,
                    "round": self.round_index,
                    "sample_index": index,
                    "wall_time_utc": wall,
                    "monotonic_ns": monotonic,
                    "scope": "planner_process",
                    "rss_kib": memory["rss_kib"],
                    "peak_rss_kib": memory["peak_rss_kib"],
                    "source": memory["source"],
                    "notes": "",
                }
            )
        self.power_rows.append(self._power_row(wall, monotonic, index))
        self.utilization_rows.append(self._utilization_row(wall, monotonic, index))

    def _power_row(self, wall: str, monotonic: int, index: int) -> dict[str, Any]:
        if self.spec.power_probe is None:
            return {
                "run_id": self.run_id,
                "round": self.round_index,
                "sample_index": index,
                "wall_time_utc": wall,
                "monotonic_ns": monotonic,
                "scope": self.spec.power_scope,
                "source": "NOT_APPLICABLE",
                "probe_point": self.spec.power_probe_point,
                "voltage_v": "",
                "current_a": "",
                "power_w": "",
                "notes": "no_power_probe_configured",
            }
        row: dict[str, Any] = {
            "run_id": self.run_id,
            "round": self.round_index,
            "sample_index": index,
            "wall_time_utc": wall,
            "monotonic_ns": monotonic,
            "scope": self.spec.power_scope,
            "source": self.spec.power_probe.name,
            "probe_point": self.spec.power_probe_point,
            "voltage_v": "",
            "current_a": "",
            "power_w": "",
            "notes": "",
        }
        try:
            row.update(
                {
                    key: ("" if value is None else value)
                    for key, value in self.spec.power_probe.read().items()
                }
            )
        except Exception as error:
            row["source"] = "PROBE_ERROR"
            row["notes"] = f"{type(error).__name__}: {error}"
            self.errors.append(f"power: {type(error).__name__}: {error}")
        return row

    def _utilization_row(self, wall: str, monotonic: int, index: int) -> dict[str, Any]:
        cpu_percent = self._cpu_sampler()
        row: dict[str, Any] = {
            "run_id": self.run_id,
            "round": self.round_index,
            "sample_index": index,
            "wall_time_utc": wall,
            "monotonic_ns": monotonic,
            "scope": self.spec.utilization_scope,
            "source": "psutil" if cpu_percent is not None else "NOT_APPLICABLE",
            "cpu_percent": "" if cpu_percent is None else cpu_percent,
            "bpu_percent": "",
            "ddr_bandwidth_gbps": "",
            "notes": "" if cpu_percent is not None else "process_cpu_percent_unavailable",
        }
        if self.spec.utilization_probe is not None:
            row["source"] = self.spec.utilization_probe.name
            try:
                for key, value in self.spec.utilization_probe.read().items():
                    row[key] = "" if value is None else value
            except Exception as error:
                row["source"] = "PROBE_ERROR"
                row["notes"] = f"{type(error).__name__}: {error}"
                self.errors.append(f"utilization: {type(error).__name__}: {error}")
        elif row["bpu_percent"] == "":
            row["notes"] = (row["notes"] + ";bpu_not_measured").strip(";")
        return row

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=15.0)
        self.sample_once()

    def summary(self) -> dict[str, Any]:
        def values(rows: list[dict[str, Any]], key: str) -> list[float]:
            return [
                float(row[key])
                for row in rows
                if isinstance(row.get(key), (int, float))
            ]

        rss = values(self.memory_rows, "rss_kib")
        peak = values(self.memory_rows, "peak_rss_kib")
        power = values(self.power_rows, "power_w")
        bpu = values(self.utilization_rows, "bpu_percent")
        cpu = values(self.utilization_rows, "cpu_percent")
        return {
            "memory": {
                "sample_count": len(self.memory_rows),
                "rss_kib_max": max(rss) if rss else None,
                "peak_rss_kib_max": max(peak) if peak else None,
                "peak_rss_mib_max": (max(peak) / 1024.0) if peak else None,
                "source": self.memory_rows[0]["source"] if self.memory_rows else None,
            },
            "power": {
                "sample_count": len(power),
                "power_w_mean": (sum(power) / len(power)) if power else None,
                "power_w_max": max(power) if power else None,
                "source": self.power_rows[0]["source"] if self.power_rows else None,
                "probe_point": self.spec.power_probe_point,
                "measured": bool(power),
            },
            "utilization": {
                "sample_count": len(self.utilization_rows),
                "cpu_percent_max": max(cpu) if cpu else None,
                "bpu_percent_mean": (sum(bpu) / len(bpu)) if bpu else None,
                "bpu_percent_max": max(bpu) if bpu else None,
                "bpu_measured": bool(bpu),
            },
            "errors": list(self.errors),
        }


__all__ = [
    "ProbeCommand",
    "TelemetrySpec",
    "BackgroundMonitor",
    "sample_process_memory",
]
