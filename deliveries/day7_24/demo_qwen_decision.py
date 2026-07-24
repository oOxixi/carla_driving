"""Qwen决策演示 — 加载Day22真实Qwen运行结果.

从 integration/day22/day22_qwen_runtime_results.json 加载12个真实案例,
展示Qwen输入/输出/校验/决策追踪的完整流程。
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

ALLOWED_ACTIONS = {
    "START","STOP","SET_SPEED","TURN_LEFT","TURN_RIGHT",
    "CHANGE_LANE_LEFT","CHANGE_LANE_RIGHT","AVOID_OBJECT",
    "EMERGENCY_BRAKE","RETURN_TO_LANE",
}


def load_day22_results():
    """加载Day22真实Qwen运行时结果."""
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "integration", "day22", "day22_qwen_runtime_results.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def summarize_result(r: dict) -> dict:
    """从Day22结果中提取摘要."""
    raw = r.get("qwen_raw_output", {})
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            raw = {}
    actions = raw.get("actions", [{}]) if isinstance(raw, dict) else [{}]
    return {
        "case": r.get("case", "?"),
        "expected": r.get("expected_final_action", "?"),
        "qwen_actions": [a.get("action", "?") for a in actions],
        "qwen_confidence": raw.get("confidence", "?"),
        "qwen_reason": raw.get("reason", "")[:60],
        "qwen_validation": r.get("qwen_validation", "?"),
        "final_decision": r.get("final_decision", "?"),
        "correct": r.get("final_action_correct", False),
        "latency_s": r.get("latency_s", 0),
    }


def main():
    ev_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence")
    os.makedirs(ev_dir, exist_ok=True)

    print("=" * 60)
    print("  Qwen决策演示 — Day22真实Qwen运行结果")
    print("=" * 60)

    results = load_day22_results()
    print(f"\n  加载 {len(results)} 个真实Qwen运行时案例")
    print(f"  数据来源: integration/day22/day22_qwen_runtime_results.json")
    print(f"  Prompt版本: day23-final-v1")
    print(f"  动作白名单: {sorted(ALLOWED_ACTIONS)}")

    correct = 0
    for i, r in enumerate(results[:8]):
        s = summarize_result(r)
        is_ok = "OK" if s["correct"] else "FAIL"
        print(f"\n  [{i+1}] {s['case']}")
        print(f"      预期: {s['expected']}")
        print(f"      Qwen输出: {s['qwen_actions']} (conf={s['qwen_confidence']})")
        print(f"      Qwen解释: {s['qwen_reason']}")
        print(f"      校验: {s['qwen_validation']}")
        print(f"      最终决策: {s['final_decision']}")
        print(f"      结果: {is_ok} | 延迟: {s['latency_s']:.2f}s")
        if s["correct"]:
            correct += 1

    print(f"\n{'=' * 60}")
    print(f"  汇总: {correct}/{min(8, len(results))} 案例正确")
    print(f"  剩余 {len(results)-8} 个案例见完整数据文件")
    print(f"{'=' * 60}")

    # 保存摘要
    summary = [summarize_result(r) for r in results]
    with open(os.path.join(ev_dir, "demo_qwen_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\n  摘要已保存: evidence/demo_qwen_summary.json")


if __name__ == "__main__":
    main()
