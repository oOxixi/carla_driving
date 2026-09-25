"""Compare the quantisation thresholds of several hb_compile builds.

Usage: python3 thresholds_report.py <label=path> [<label=path> ...]
"""
import json
import sys


def main() -> int:
    print(f"{'build':<28}{'layers':>7}{'values':>7}{'distinct':>9}{'min':>10}{'max':>8}"
          f"{'==1.0':>8}")
    for spec in sys.argv[1:]:
        label, path = spec.split("=", 1)
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        flat = [float(x) for entry in data.values()
                for group in (entry.get("thresholds") or []) for x in group]
        if not flat:
            print(f"{label:<28}{len(data):>7}{0:>7}{'-':>9}{'-':>10}{'-':>8}{'-':>8}")
            continue
        distinct = len({round(v, 6) for v in flat})
        ones = sum(1 for v in flat if v == 1.0)
        print(f"{label:<28}{len(data):>7}{len(flat):>7}{distinct:>9}"
              f"{min(flat):>10.4g}{max(flat):>8.4g}{f'{ones}/{len(flat)}':>8}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
