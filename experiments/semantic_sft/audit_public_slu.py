"""Pinned public SLU inventory. This tool never emits current-task SFT labels."""
import hashlib
import json
from pathlib import Path
import urllib.request
import zipfile
import re
from collections import Counter, defaultdict

from .data import ROOT, output_directory, protected_hashes, text_hash
from .prepare import external_registry
from .release import write_rows
from .recover_existing_data import source_text

SOURCES = {
    'mac': ('a6ff836e735de975451dfccefa33237d9dd7f2b5', {
        'README.md': 'https://huggingface.co/datasets/Gatsby1984/MAC_SLU/resolve/{revision}/README.md',
        'train.jsonl': 'https://huggingface.co/datasets/Gatsby1984/MAC_SLU/resolve/{revision}/label/train_set.jsonl',
    }),
    'mivs': ('d1055a58d673468b4471e020626e8306ae6e4cb6', {
        'README.md': 'https://raw.githubusercontent.com/X-LANCE/MIVS_BIRGAT/{revision}/README.md',
        'LICENSE': 'https://raw.githubusercontent.com/X-LANCE/MIVS_BIRGAT/{revision}/LICENSE',
        'aispeech.zip': 'https://raw.githubusercontent.com/X-LANCE/MIVS_BIRGAT/{revision}/data/aispeech.zip',
    }),
}


def fetch(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'public-slu-provenance-audit/1'})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def acquire(out):
    manifest = []
    for source, (revision, files) in SOURCES.items():
        directory = out / 'sources' / source
        directory.mkdir(parents=True)
        for name, template in files.items():
            url = template.format(revision=revision)
            content = fetch(url)
            (directory / name).write_bytes(content)
            manifest.append(dict(source=source, revision=revision, path=str(directory / name),
                url=url, bytes=len(content), sha256=hashlib.sha256(content).hexdigest()))
    (out / 'source_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


def records(content):
    # Upstream MIVS uses JSONL despite a .json extension.
    return [json.loads(line) for line in content.decode('utf-8-sig').splitlines() if line.strip()]


def frames(row, dataset):
    if dataset == 'mac':
        result = []
        for index, frame in row['semantics'].items():
            for domain, slots in (frame or {}).items():
                intent = next((s['value'] for s in slots if s['name'] == 'intent'), None)
                if intent:
                    result.append(dict(domain=domain, intent=intent, source_index=index,
                        slots=[s for s in slots if s['name'] != 'intent']))
        return result
    return [dict(domain=d['domain'], intent=i['intent'], slots=i.get('slots', []))
            for d in row['semantics'] for i in d['intents']]


def normalized(text):
    import unicodedata
    return ''.join(unicodedata.normalize('NFKC', text).casefold().split())


def phrase_index(texts):
    index = defaultdict(set)
    for text in texts:
        value = normalized(text)
        if len(value) >= 8:
            index[value[:8]].add(value)
    return index


def contained_protected(text, index):
    value = normalized(text)
    return any(phrase in value for offset in range(max(0, len(value) - 7))
               for phrase in index.get(value[offset:offset+8], ()))


def row_issues(text, row, semantic_frames, dataset):
    issues = []
    if not text.strip() or len(text) > 1000:
        issues.append('INVALID_TEXT_LENGTH')
    if not semantic_frames:
        issues.append('NO_LABELED_INTENT_NOT_A_NEGATIVE_LABEL')
    if dataset == 'mac' and len(row.get('split_sens', [])) != len(semantic_frames):
        issues.append('CLAUSE_FRAME_COUNT_MISMATCH_REVIEW')
    if any(not isinstance(s.get('value'), str) or not s['value'] or s['value'] not in text
           for frame in semantic_frames for s in frame['slots']):
        issues.append('NON_LITERAL_SLOT_NOT_CURRENT_SPAN_LABEL')
    if re.search('自动紧急|自动刹车|碰撞预警|车道保持|车道偏离|侧向制动|辅助驾驶|自适应巡航', text):
        issues.append('SAFETY_FEATURE_CONTROL_REVIEW_NOT_MANEUVER')
    if re.search('变道|换道|超车|超越|避让|让行|跟车|左转|右转|靠边|停车|车速|巡航|公里每小时|千米每小时', text):
        issues.append('DRIVING_LEXEME_REVIEW_NOT_AUTO_ACTION')
    return issues


def verify_sources(source_dir):
    manifest = json.loads((source_dir / 'source_manifest.json').read_text(encoding='utf-8'))
    for item in manifest:
        path = source_dir / 'sources' / item['source'] / Path(item['path']).name
        if hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise ValueError('downloaded source changed: ' + str(path))
    return manifest


def prior_evaluation_texts(inventory_path):
    inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
    roots = {'carla-driving-qwen-semantic-adaptation/': ROOT,
             'carla-driving-challenge/': ROOT.parent / 'carla_driving_challenge_a3_prep'}
    texts, verified = [], []
    for item in inventory['inventory']:
        if item['role'] not in {'EVALUATION_ONLY', 'QUARANTINE_ONLY'}:
            continue
        candidates = [root / item['path'].split(prefix, 1)[1]
                      for prefix, root in roots.items() if prefix in item['path']]
        path = candidates[0] if candidates else Path(item['path'])
        content = path.read_bytes()  # Missing/stale prior protected resources fail closed.
        digest = hashlib.sha256(content).hexdigest()
        lf_digest = hashlib.sha256(content.replace(b'\r\n', b'\n')).hexdigest()
        if item['sha256'] not in {digest, lf_digest}:
            raise ValueError('prior evaluation resource changed: ' + str(path))
        rows = records(content) if path.suffix == '.jsonl' else json.loads(content)
        texts.extend(t for r in rows if (t := source_text(r)))
        verified.append(dict(path=str(path.resolve()), sha256=digest, role=item['role'],
            prior_sha256=item['sha256'], match='EXACT_BYTES' if digest == item['sha256'] else 'CRLF_TO_LF_ONLY'))
    return texts, verified


def audit(source_dir, out, release):
    manifest = verify_sources(source_dir)
    protected = set(protected_hashes())
    exclusion_files = []
    for name, role in [('test_exclusion_registry.json', 'FROZEN_TEST'),
                       ('supplemental_exclusion_registry.json', 'INDEPENDENT_VALIDATION')]:
        path = release / name
        protected.update(external_registry(path, role=role))
        exclusion_files.append(dict(path=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    reviewed = records((release / 'reviewed_rows.jsonl').read_bytes())
    existing = {text_hash(r['source_text']) for r in reviewed if r['split'] == 'train'}
    protected.update(text_hash(r['source_text']) for r in reviewed if r['split'] == 'val')
    for path in (release / 'quarantine.jsonl',):
        protected.update(text_hash(r['source_text']) for r in records(path.read_bytes()))
    # Prior inventory includes all Teacher Train texts blocked by evaluation/quality;
    # not a replacement for the independently frozen registries above.
    prior = ROOT / 'artifacts/semantic_sft/existing_data_inventory_20261107_03/blocked_text_audit.jsonl'
    protected.update(r['normalized_text_sha256'] for r in records(prior.read_bytes()))
    for path in (release / 'reviewed_rows.jsonl', release / 'quarantine.jsonl', prior):
        exclusion_files.append(dict(path=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    prior_texts, verified = prior_evaluation_texts(prior.parent / 'inventory_report.json')
    exclusion_files.extend(verified)
    protected.update(text_hash(t) for t in prior_texts)
    eval_texts, upstream_splits = [], []
    # Evaluation labels never become examples, reports, prompts or exported artifacts.
    revision = SOURCES['mac'][0]
    for split in ('dev', 'test'):
        url = f'https://huggingface.co/datasets/Gatsby1984/MAC_SLU/resolve/{revision}/label/{split}_set.jsonl'
        content = fetch(url)
        texts = [r['query'] for r in records(content)]
        eval_texts.extend(texts)
        upstream_splits.append(dict(source='mac', split=split, url=url, rows=len(texts),
            sha256=hashlib.sha256(content).hexdigest(), revision=revision))
    train = [('mac', 'label/train_set.jsonl', i+1, r, r['query']) for i, r in enumerate(
        records((source_dir / 'sources/mac/train.jsonl').read_bytes()))]
    with zipfile.ZipFile(source_dir / 'sources/mivs/aispeech.zip', metadata_encoding='utf-8') as archive:
        for name in sorted(archive.namelist()):
            if not name.startswith('aispeech/') or not name.endswith('.json') or name == 'aispeech/ontology.json':
                continue
            split = name.split('/')[1]
            if split not in {'train', 'valid', 'test'}:
                raise ValueError('unexpected upstream split: ' + name)
            content = archive.read(name)
            parsed = records(content)
            upstream_splits.append(dict(source='mivs', split=split, member=name, rows=len(parsed),
                sha256=hashlib.sha256(content).hexdigest(), revision=SOURCES['mivs'][0]))
            if split == 'train':
                train.extend(('mivs', name, i+1, r, r['input']) for i, r in enumerate(parsed))
            else:
                eval_texts.extend(r['input'] for r in parsed)
    protected.update(text_hash(t) for t in eval_texts)
    all_eval_texts = eval_texts + prior_texts
    fragments = [part for text in all_eval_texts for part in re.split(r'然后|并且|还有|以及|同时|顺便|并|再|，|,', text)
                 if len(normalized(part)) >= 8]
    upstream_index = phrase_index(all_eval_texts + fragments)
    write_rows(out / 'eval_exclusion_hashes.jsonl', [dict(normalized_text_sha256=h)
        for h in sorted(protected | {text_hash(t) for t in fragments})])
    summaries, ledger, auxiliary, driving_review = {}, [], [], []
    seen = set()
    for dataset, member, line, row, text in train:
        summary = summaries.setdefault(dataset, dict(rows=0, issues=Counter(), dispositions=Counter(),
            intents=Counter(), domains=Counter(), intent_count=Counter(), unique=set(),
            auxiliary_intent_count=Counter()))
        semantic_frames = frames(row, dataset)
        digest = text_hash(text)
        issues = row_issues(text, row, semantic_frames, dataset)
        if digest in protected:
            issues.append('PROTECTED_EXACT_TEXT')
        if contained_protected(text, upstream_index):
            issues.append('UPSTREAM_EVAL_TEXT_OR_CONNECTOR_FRAGMENT_CONTAINED')
        if digest in existing:
            issues.append('ALREADY_APPROVED_CURRENT_TRAIN')
        if digest in seen:
            issues.append('DUPLICATE_TRAIN_TEXT_CROSS_CORPORA')
        seen.add(digest)
        disposition = 'QUARANTINE_REVIEW' if issues else 'AUXILIARY_ONLY_PENDING_NEW_CONTRACT_AND_GROUP_AUDIT'
        ref = dict(dataset=dataset, member=member, line=line, source_id=row.get('id'),
            normalized_text_sha256=digest, disposition=disposition, issues=issues)
        ledger.append(ref)
        if not issues:
            auxiliary.append(ref)
            summary['auxiliary_intent_count'][len(semantic_frames)] += 1
        elif 'DRIVING_LEXEME_REVIEW_NOT_AUTO_ACTION' in issues and not any('PROTECTED' in x or 'EVAL_' in x for x in issues):
            driving_review.append(dict(**ref, source_text=text, upstream_frames=semantic_frames,
                current_task_label=None, annotation_status='UNREVIEWED'))
        summary['rows'] += 1
        summary['unique'].add(digest)
        summary['issues'].update(issues)
        summary['dispositions'][disposition] += 1
        summary['intents'].update(f['intent'] for f in semantic_frames)
        summary['domains'].update(f['domain'] for f in semantic_frames)
        summary['intent_count'][len(semantic_frames)] += 1
    for summary in summaries.values():
        summary['unique_texts'] = len(summary.pop('unique'))
    write_rows(out / 'train_screening_ledger.jsonl', ledger)
    write_rows(out / 'auxiliary_reference_inventory.jsonl', auxiliary)
    write_rows(out / 'driving_lexeme_review.jsonl', driving_review)
    report = dict(scope='PUBLIC_TRAIN_AUDIT_NOT_SFT_RELEASE', datasets=summaries,
        source_manifest=manifest, upstream_split_inventory=upstream_splits,
        existing_exclusions=exclusion_files, protected_exact_hashes=len(protected),
        upstream_phrase_min_chars=8, upstream_phrase_filter='exact + full phrase/connector fragment containment; conservative, not semantic disjointness proof',
        direct_current_contract_admitted=0, auxiliary_reference_count=len(auxiliary),
        driving_lexeme_review_rows=len(driving_review),
        admission_blockers=['No verified mapping to 14 maneuver actions / 1-8 ordered steps',
            'No approved evidence/condition/target/prohibition/confirmation labels for current task',
            'No original semantic-family/component grouping; exact/substring screening is insufficient',
            'Auxiliary task contract and owner approval not provided',
            'MIVS repository MIT found; data-specific authorization not independently established'],
        training_started=False, production_changed=False, evaluation_examples_exported_to_training=False,
        original_mivs_archive_contains_evaluation_labels=True,
        prior_evaluation_resources_verified=len(verified),
        safety_and_driving_regex_are_conservative_review_triggers_not_complete_detectors=True)
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(dict(train_rows=len(train), auxiliary_references=len(auxiliary),
        direct_current_contract_admitted=0, driving_review_rows=len(driving_review)), indent=2))


def seal(out):
    document = Path(__file__).with_name('PUBLIC_SLU_SCORING_AUDIT_20261108.md')
    (out / 'REPORT.md').write_bytes(document.read_bytes())
    scoring = Path('D:/weixinliaotian/xwechat_files/wxid_ezk4tav2rdcs22_0f69/msg/file')
    pdfs = [scoring / '2026-08/XH-202602-面向智能驾驶的大模型应用场景研究比赛方案.pdf',
            scoring / '2026-09/2026年度中国青年科技创新“揭榜挂帅”擂台赛人工智能领域主擂台赛-初审评比方式及评分细则.pdf']

    def entry(path):
        content = path.read_bytes()
        return dict(path=str(path.resolve()), bytes=len(content), sha256=hashlib.sha256(content).hexdigest())

    manifest = dict(scope='AUDIT_EVIDENCE_NOT_TRAINING_OR_OFFICIAL_GATE',
        artifacts=[entry(p) for p in sorted(out.iterdir()) if p.is_file()],
        implementation=[entry(Path(__file__)), entry(document),
            entry(Path(__file__).parent / 'tests/test_public_slu_audit.py')],
        scoring_sources=[entry(p) for p in pdfs])
    (out / 'artifact_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--source-dir', type=Path, help='Reuse and verify an immutable prior download')
    parser.add_argument('--release-dir', type=Path, required=True)
    args = parser.parse_args()
    out = output_directory(args.output_dir)
    out.mkdir(parents=True)
    if args.source_dir is None:
        acquire(out)
    audit(args.source_dir or out, out, args.release_dir)
    seal(out)


if __name__ == '__main__':
    main()
