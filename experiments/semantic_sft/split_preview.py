"""Label-blind group split proposal, not a frozen release or training export."""
from collections import defaultdict
import copy

from .data import PLAN, audit_rows, canonical_hash

SEED = 20261101


def split_preview(rows, *, external_protected=None, supplemental_protected=None, protected_groups=None):
    initial = audit_rows(rows, external_protected=external_protected, supplemental_protected=supplemental_protected,protected_groups=protected_groups)
    issues = {issue['sample_id']: set(issue['errors']) for issue in initial['issues']}
    eligible, quarantine = [], []
    for row in rows:
        errors = issues.get(row.get('sample_id'), set())
        if any(error.startswith('INVALID_RECORD_SCHEMA:') for error in errors):
            raise ValueError('invalid review record schema')
        gap = row.get('proposal', {}).get('contract_gap') is True
        permitted = {'SPLIT_UNASSIGNED'}
        if gap:
            permitted |= {'HUMAN_REVIEW_NOT_APPROVED', 'MISSING_LABEL', 'PROPOSAL_CONTRACT_GAP_QUARANTINED'}
        if errors - permitted or row.get('split') != 'UNASSIGNED':
            raise ValueError('split preview needs valid unassigned, reviewed records; cannot silently resplit or skip invalid data')
        (quarantine if gap else eligible).append(copy.deepcopy(row))
    families = defaultdict(set)
    group_family = {}
    required = set(PLAN['data_smoke_thresholds']['required_families'])
    for row in eligible:
        group, family = row['group_id'], row['semantic_family']
        if family not in required:
            raise ValueError('unknown semantic family')
        # shortcut: current reviewed groups each have one family; reject mixed-family groups rather than split them.
        if group in group_family and group_family[group] != family:
            raise ValueError('mixed-family group needs explicit split design')
        group_family[group] = family
        families[family].add(group)
    if any(len(families[family]) < 2 for family in required):
        raise ValueError('both splits need at least two independent groups per family')
    validation_groups = {min(families[family], key=lambda group: canonical_hash([SEED, family, group]))
                         for family in required}
    for row in eligible:
        row['split'] = 'val' if row['group_id'] in validation_groups else 'train'
    eligible.sort(key=lambda row: row['sample_id'])
    quarantine.sort(key=lambda row: row['sample_id'])
    audit = audit_rows(eligible, external_protected=external_protected, supplemental_protected=supplemental_protected,protected_groups=protected_groups)
    if audit['issues'] or audit['overlapping_groups']:
        raise ValueError('candidate violates record or group boundaries')
    report = {'scope': 'SPLIT_PREVIEW_NOT_FROZEN_RELEASE_TRAINING_OR_TEST', 'seed': SEED,
        'selection': 'One Val group per family, lowest SHA256(seed,family,group); no labels or model scores used.',
        'ratio_note': 'Coverage-oriented small-sample preview, not a target 80/20 ratio or representative validation proof.',
        'candidate_rows': len(eligible), 'quarantined_rows': len(quarantine),
        'sample_counts': audit['splits'], 'family_counts': audit['families'],
        'group_assignments': {group: 'val' if group in validation_groups else 'train' for group in sorted(group_family)},
        'candidate_audit': audit, 'split_frozen': False, 'test_independence_verified': False,
        'data_ready_for_tokenization': False, 'ready_for_training': False}
    return eligible, quarantine, report
