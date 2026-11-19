import json

import jsonschema

from experiments.semantic_sft.data import HERE, text_hash
from experiments.semantic_sft.recover_existing_data import packet_for, partition_train


def teacher(text, group='g', quality=True):
    return dict(model_request=dict(source_text=text), metadata=dict(group_key=group),
                quality=dict(valid_for_training=quality, training_exclusion_reasons=[], training_role='POSITIVE'))


def test_all_release_evaluation_text_and_group_protection_precede_dedup():
    entries = [(teacher('held text', 'a'), {'line': 1}), (teacher('new text', 'held_group'), {'line': 2}),
               (teacher('kept', 'safe'), {'line': 3}), (teacher('kept', 'other'), {'line': 4}),
               (teacher('existing'), {'line': 5}), (teacher('invalid', quality=False), {'line': 6})]
    kept, excluded = partition_train(entries, {text_hash('held text')}, {'held_group'}, {text_hash('existing')})
    assert list(kept) == [text_hash('kept')] and len(kept[text_hash('kept')]) == 2
    reasons = {reason for row in excluded for reason in row['reasons']}
    assert reasons == {'EVALUATION_OR_PROMPT_TEXT', 'EVALUATION_SOURCE_GROUP',
                       'ALREADY_IN_APPROVED_SEMANTIC_TRAIN', 'TEACHER_QUALITY_OR_ROLE_NOT_TRAINABLE'}


def test_recovered_outer_record_is_current_schema_without_fabricated_labels_or_reviews():
    packet = packet_for('UNIT_RECOVERED_SOURCE', text_hash('UNIT_RECOVERED_SOURCE'))
    jsonschema.Draft202012Validator(json.loads((HERE / 'record.schema.json').read_text())).validate(packet)
    assert packet['label'] is None and packet['reviews'] == [] and packet['annotation_status'] == 'DRAFT'
    assert packet['split'] == 'UNASSIGNED' and 'proposal' not in packet
    assert packet['origin']['kind'] == 'EXTRACTED_EXISTING_TRAIN_REQUIRES_REVIEW'
