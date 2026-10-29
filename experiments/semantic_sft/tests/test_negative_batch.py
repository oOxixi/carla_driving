from collections import Counter
import json

from experiments.semantic_sft.data import HERE, audit_rows, load_jsonl, protected_hashes, text_hash
from experiments.semantic_sft.proposals import draft_packets
from experiments.semantic_sft.tests.test_review import reviewed


def inputs():
    folder = HERE / "batches/negative_v1"
    return load_jsonl(folder / "seeds.jsonl"), load_jsonl(folder / "draft_labels.jsonl")


def test_new_batch_never_reuses_old_ids_texts_or_protected_examples():
    seeds, _ = inputs()
    old = load_jsonl(HERE / "seeds.jsonl")
    assert len(old) == 24 and len(seeds) == 8
    assert not {s["sample_id"] for s in old} & {s["sample_id"] for s in seeds}
    texts = {text_hash(s["source_text"]) for s in seeds}
    assert len(texts) == 8
    assert not texts & ({text_hash(s["source_text"]) for s in old} | protected_hashes())
    assert set(Counter(s["group_id"] for s in seeds).values()) == {2}
    assert len({s["group_id"] for s in seeds}) == 4
    assert all(s["semantic_family"] == "negative_instruction" for s in seeds)


def test_drafts_are_literal_and_prohibitions_do_not_become_positive_actions():
    rows = draft_packets(*inputs())
    expected = [("TURN_RIGHT", ["KEEP_LANE", "STOP"]), ("TURN_RIGHT", ["KEEP_LANE", "STOP"]),
                ("TURN_LEFT", ["SET_SPEED", "STOP"]), ("TURN_LEFT", ["SET_SPEED", "STOP"]),
                ("FOLLOW", ["YIELD", "STOP"]), ("FOLLOW", ["YIELD", "STOP"]),
                ("PULL_OVER", ["SET_SPEED", "KEEP_LANE"]), ("PULL_OVER", ["SET_SPEED", "KEEP_LANE"])]
    for row, (prohibited, positive) in zip(rows, expected):
        label = row["proposal"]["label"]
        assert label["prohibited_actions"] == {prohibited: True}
        assert [s["action"] for s in label["steps"]] == positive
        assert prohibited not in positive
        assert row["label"] is None and row["reviews"] == [] and row["annotation_status"] == "DRAFT"
    assert all(r["proposal"]["label"]["steps"][0]["target_text"] == "斑马线上的行人" for r in rows[4:6])
    assert all("STOP" not in r["proposal"]["label"]["prohibited_actions"] for r in rows[6:])


def test_unreviewed_supplements_do_not_close_the_reviewed_coverage_gap():
    rows = draft_packets(*inputs())
    original, _ = reviewed()  # Synthetic UNIT_ONLY metadata, not actual human approvals.
    report = audit_rows(original + rows)
    assert report["rows"] == 32
    assert report["issue_counts"]["MISSING_LABEL"] == 11  # Old quarantine 3 plus all new 8.
    assert report["issue_counts"]["PROPOSAL_CONTRACT_GAP_QUARANTINED"] == 3
    assert report["split_coverage_diagnostics"]["families_needing_more_groups"] == ["negative_instruction"]
    assert not report["ready_for_training"] and not report["data_ready_for_tokenization"]


def test_existing_cli_handles_new_batch_and_refuses_training_export(tmp_path, monkeypatch):
    from experiments.semantic_sft import prepare
    folder = HERE / "batches/negative_v1"
    target = tmp_path / "draft"
    monkeypatch.setattr(prepare, "output_directory", lambda path: path)
    monkeypatch.setattr("sys.argv", ["prepare", "draft", "--input", str(folder / "seeds.jsonl"),
        "--proposals", str(folder / "draft_labels.jsonl"), "--output-dir", str(target)])
    assert prepare.main() == 0
    assert len(load_jsonl(target / "draft_review_queue.jsonl")) == 8
    assert json.loads((target / "report.json").read_text())["approved_rows"] == 0
    export = tmp_path / "export"
    monkeypatch.setattr("sys.argv", ["prepare", "export", "--input", str(target / "draft_review_queue.jsonl"),
                                    "--output-dir", str(export)])
    assert prepare.main() == 1
    assert not (export / "train.jsonl").exists() and not (export / "val.jsonl").exists()
