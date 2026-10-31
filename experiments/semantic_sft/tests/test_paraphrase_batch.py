from experiments.semantic_sft.batches.paraphrase_v1.build import packets
from experiments.semantic_sft.data import HERE, audit_rows, load_jsonl, protected_hashes, text_hash


def test_wording_expansion_preserves_group_boundaries_and_never_creates_approvals():
    rows=packets()
    old=load_jsonl(HERE/'seeds.jsonl')+load_jsonl(HERE/'batches/negative_v1/seeds.jsonl')
    assert len(rows)==12 and len({r['semantic_family'] for r in rows})==6
    assert len({r['group_id'] for r in rows})==6
    assert {r['group_id'] for r in rows}<={r['group_id'] for r in old}
    assert not {r['sample_id'] for r in rows}&{r['sample_id'] for r in old}
    texts={text_hash(r['source_text']) for r in rows}
    assert len(texts)==12 and not texts&({text_hash(r['source_text']) for r in old}|protected_hashes())
    assert all(r['label'] is None and not r['reviews'] and r['split']=='UNASSIGNED' for r in rows)
    report=audit_rows(rows)
    assert report['issue_counts']['MISSING_LABEL']==12 and not report['ready_for_training']
