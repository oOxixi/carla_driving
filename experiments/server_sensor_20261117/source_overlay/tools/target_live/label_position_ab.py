from pathlib import Path
import copy, json, sys, time, hashlib
from collections import Counter
from datetime import datetime, timezone
from PIL import Image
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from qwen_service.client import QwenServiceClient

LOG = ROOT / 'artifacts/runtime/target_live/logs/P0_REAL_TARGET_DEMO_20261103_215505_560214.jsonl'
OUT = ROOT / 'artifacts/runtime/target_live/label_ab'
OUT.mkdir(parents=True, exist_ok=True)
with LOG.open(encoding='utf-8') as f:
    request = next(item['payload']['orchestration']['model_request'] for line in f
                   if (item := json.loads(line)).get('record_type') == 'canonical_routing'
                   and item.get('phase') == 'SUBMIT')
original = Image.open(ROOT / request['rgb_ref']).convert('RGB')
assert original.size == (224, 224)
a = original.copy()
b = original.copy()
b.paste(original.crop((56, 0, 112, 16)), (0, 0))
b.paste(original.crop((0, 0, 56, 16)), (56, 0))
for name, picture in [('a', a), ('b', b)]:
    picture.save(OUT / f'{name}.jpg', quality=100, subsampling=0)
a_pixels = np.array(Image.open(OUT / 'a.jpg').convert('RGB'))
b_pixels = np.array(Image.open(OUT / 'b.jpg').convert('RGB'))
assert np.array_equal(a_pixels[16:], b_pixels[16:]), 'Image content below the label strip changed'
assert np.array_equal(a_pixels[:16, 112:], b_pixels[:16, 112:]), 'Image content outside swapped labels changed'
assert np.array_equal(a_pixels[:16, :56], b_pixels[:16, 56:112]), 'Label tile was altered'
assert np.array_equal(a_pixels[:16, 56:112], b_pixels[:16, :56]), 'Label tile was altered'
assert not np.array_equal(a_pixels, b_pixels), 'Two variants are identical'
client = QwenServiceClient('http://127.0.0.1:18006', timeout_s=30)
print('health:', json.dumps(client.health(), ensure_ascii=False), flush=True)
results = []
for index, variant in enumerate('ABBAABBAAB', 1):
    payload = copy.deepcopy(request)
    payload['rgb_ref'] = str((OUT / f'{variant.lower()}.jpg').relative_to(ROOT))
    payload['created_at_ns'] = time.monotonic_ns()
    payload['deadline_ns'] = payload['created_at_ns'] + 25_000_000_000
    payload['request_id'] = f'label-position-ab-{index:02d}'
    start = time.perf_counter()
    try:
        response = client.infer(payload)
        ground = response.get('model_grounding') or {}
        row = {'sequence': index, 'variant': variant, 'raw_choice': ground.get('raw_choice'),
               'target_id': ground.get('target_id'), 'abstained': ground.get('abstained'),
               'elapsed_ms': round((time.perf_counter()-start)*1000), 'response': response}
    except Exception as exc:
        row = {'sequence': index, 'variant': variant, 'error': str(exc),
               'elapsed_ms': round((time.perf_counter()-start)*1000)}
    results.append(row)
    print(json.dumps({k:v for k,v in row.items() if k != 'response'}, ensure_ascii=False), flush=True)
    data = {'source_log': LOG.name, 'source_image': request['rgb_ref'], 'frame_id': request['scene_summary']['frame_id'],
            'instruction': request['source_text'], 'model': 'Qwen/Qwen3.5-2B', 'temperature': 0,
            'candidate_mapping': request['target_grounding']['visual_candidates'],
            'variants': {'A': '左 T1，右 T2', 'B': '左 T2，右 T1'},
            'pixel_check': '两张发送图片在顶部 112×16 像素以外完全一致，且两个标签区域完全互换',
            'image_sha256': {v: hashlib.sha256((OUT / f'{v.lower()}.jpg').read_bytes()).hexdigest() for v in ['A','B']},
            'created_at_utc': datetime.now(timezone.utc).isoformat(), 'expected_calls': 10, 'results': results}
    tmp = OUT / 'result.tmp'; tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'); tmp.replace(OUT / 'result.json')
