"""Build text hashes from a real frozen Test export. No labels, RGB or raw text in output."""
import argparse
import hashlib
import json
import re
from pathlib import Path

from .data import baseline_guard, load_jsonl, output_directory, text_hash


def registry(rows, publisher, version, *, role, source_revision, frozen):
    if not publisher.strip() or not version.strip():
        raise ValueError('real publisher and frozen Test version are required')
    if role not in {'FROZEN_TEST', 'INDEPENDENT_VALIDATION'} or frozen is not True or not re.fullmatch('[0-9a-f]{40}', source_revision):
        raise ValueError('declare actual frozen set role and exact source revision; Validation is not Test')
    texts = []
    for row in rows:
        text = row.get('source_text')
        if not isinstance(text, str) or not text.strip():
            raise ValueError('every row must contain the exact model-input source_text')
        texts.append(text_hash(text))
    if not texts:
        raise ValueError('cannot sign an empty or fabricated exclusion registry')
    return {'registry_schema_version':2, 'protected_set_role':role, 'frozen':True, 'source_revision':source_revision,
            'normalization':'nfkc_casefold_remove_whitespace_v1', 'publisher':publisher,
            'test_version':version, 'input_rows':len(rows), 'unique_texts':len(set(texts)),
            'text_sha256':sorted(set(texts)), 'publisher_identity_verified_by_tool':False,
            'note':'Exact normalized text exclusion only; semantic paraphrases still need group review.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--publisher', required=True)
    parser.add_argument('--test-version', required=True)
    parser.add_argument('--role', choices=['FROZEN_TEST','INDEPENDENT_VALIDATION'], required=True)
    parser.add_argument('--source-revision', required=True)
    parser.add_argument('--frozen', action='store_true', required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args=parser.parse_args()
    if not baseline_guard()['passed']:
        raise ValueError('baseline guard failed')
    output=output_directory(args.output_dir)
    payload=registry(load_jsonl(args.input), args.publisher, args.test_version,
                     role=args.role, source_revision=args.source_revision, frozen=args.frozen)
    payload['input_file_sha256']=hashlib.sha256(args.input.read_bytes()).hexdigest()
    output.mkdir(parents=True, exist_ok=False)
    (output/'exclusion_registry.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output':str(output), 'unique_texts':payload['unique_texts']}))


if __name__=='__main__':
    main()
