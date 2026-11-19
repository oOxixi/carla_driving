"""User-authorized synthetic-only Qwen/LoRA pipeline check; never a business-data trainer."""
import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
import urllib.request

from .data import PLAN, baseline_guard, output_directory
from .environment import assistant_token_mask


def synthetic_messages(value):
    return [{'role': 'system', 'content': 'Synthetic pipeline unit check, not driving. Return the requested JSON.'},
            {'role': 'user', 'content': f'SYNTHETIC_PIPELINE_UNIT_{value}: output integer {value} as JSON unit_value.'},
            {'role': 'assistant', 'content': json.dumps({'unit_value': value})}]


def production_health():
    with urllib.request.urlopen('http://127.0.0.1:18005/health', timeout=10) as response:
        result = json.load(response)
    if result['status'] != 'READY' or result['model_id'] != PLAN['base_model']:
        raise ValueError('production baseline must remain healthy')
    return {key: result.get(key) for key in ('status', 'model_id', 'model_revision', 'artifact_sha256')}


def select_gpu():
    line = subprocess.check_output(['nvidia-smi', '-i', '1', '--query-gpu=uuid,memory.used',
                                    '--format=csv,noheader,nounits'], text=True).strip()
    uuid, used = [part.strip() for part in line.split(',')]
    if not uuid.startswith('GPU-') or int(used) > 1024:
        raise ValueError('physical GPU1 is not idle; never stop another job')
    return uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-path', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    if not baseline_guard()['passed']:
        raise ValueError('baseline guard failed')
    if PLAN['synthetic_smoke_entrypoint'] != 'experiments.semantic_sft.synthetic_smoke':
        raise ValueError('synthetic smoke is not authorized by the isolated plan')
    output = output_directory(args.output_dir)
    model_path = args.model_path.resolve(strict=True)
    protected = Path('/home/tiaozhansai/carla-driving-2B/models/Qwen3.5-2B').resolve()
    if model_path != protected:
        raise ValueError('only the existing read-only pinned 2B directory is allowed')
    gpu_uuid = select_gpu()
    health_before = production_health()
    os.environ['CUDA_VISIBLE_DEVICES'] = gpu_uuid
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    os.environ['HF_HUB_OFFLINE'] = '1'
    output.mkdir(parents=True, exist_ok=False)
    report = {'scope': 'SYNTHETIC_PIPELINE_CHECK_NOT_SEMANTIC_ACCURACY_OR_GATE',
        'status': 'RUNNING', 'physical_gpu': 1, 'gpu_uuid': gpu_uuid,
        'base_model': PLAN['base_model'], 'expected_revision': PLAN['base_revision'],
        'base_fingerprint_verified_by_this_run': False, 'business_samples_used': 0,
        'new_unreviewed_samples_used': 0, 'training_steps': [], 'adapter_only': True,
        'production_health_before': health_before, 'formal_gate_passed': False,
        'started_at_unix': time.time()}
    def save():
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    save()
    try:
        import importlib.metadata as md
        import torch
        from transformers import AutoModelForImageTextToText, AutoTokenizer
        from peft import LoraConfig, PeftModel, get_peft_model
        torch.manual_seed(20261101)
        if torch.cuda.device_count() != 1:
            raise ValueError('exactly one isolated training GPU must be visible')
        report['packages'] = {name: md.version(name) for name in ['torch', 'transformers', 'peft', 'accelerate']}
        report['python_prefix'] = __import__('sys').prefix
        tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True, trust_remote_code=False)
        if not tokenizer.chat_template:
            tokenizer.chat_template = (model_path/'chat_template.jinja').read_text()
        records = [assistant_token_mask(tokenizer, synthetic_messages(value), max_length=512) for value in (17, 23, 31)]
        (output / 'synthetic_samples.json').write_text(json.dumps([synthetic_messages(v) for v in (17,23,31)], indent=2), encoding='utf-8')
        def load_base():
            return AutoModelForImageTextToText.from_pretrained(str(model_path), local_files_only=True,
                trust_remote_code=False, dtype=torch.bfloat16, device_map={'': 'cuda:0'}, attn_implementation='eager')
        model = get_peft_model(load_base(), LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05,
            bias='none', target_modules=PLAN['candidate_lora']['target_modules_regex'], task_type='CAUSAL_LM'))
        model.config.use_cache = False
        trainable = {name: parameter for name, parameter in model.named_parameters() if parameter.requires_grad}
        if not trainable or any('.lora_' not in name or '.model.language_model.' not in name for name in trainable):
            raise ValueError('only language-main LoRA parameters may train')
        report['trainable_parameters'] = sum(p.numel() for p in trainable.values())
        if report['trainable_parameters'] != 417792:
            raise ValueError('unexpected LoRA parameter count')
        before = {name: parameter.detach().float().cpu().clone() for name, parameter in trainable.items()}
        optimizer = torch.optim.AdamW(trainable.values(), lr=1e-4)
        def batch(record, labels=True):
            result = {key: torch.tensor([record[key]], device='cuda:0') for key in ('input_ids', 'labels') if labels or key != 'labels'}
            result['attention_mask'] = torch.ones_like(result['input_ids'])
            return result
        model.train()
        for step in range(2):
            optimizer.zero_grad(set_to_none=True)
            loss = model(**batch(records[step]), use_cache=False).loss
            if not torch.isfinite(loss):
                raise ValueError('non-finite loss')
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(trainable.values(), 1.0, error_if_nonfinite=True)
            optimizer.step()
            report['training_steps'].append({'step': step+1, 'loss': loss.item(), 'gradient_norm': float(norm)})
            save()
            print(json.dumps(report['training_steps'][-1]), flush=True)
        changed = sum(not torch.equal(before[name], parameter.detach().float().cpu()) for name,parameter in trainable.items())
        if not changed:
            raise ValueError('optimizer did not change any adapter parameters')
        report['changed_adapter_tensors'] = changed
        model.eval()
        with torch.no_grad():
            validation_loss = model(**batch(records[2]), use_cache=False).loss.item()
            reference = model(**batch(records[2], labels=False), use_cache=False, logits_to_keep=1).logits.float().cpu()
        if not math.isfinite(validation_loss):
            raise ValueError('non-finite synthetic validation loss')
        model.save_pretrained(output/'adapter', safe_serialization=True)
        report['synthetic_validation_loss'] = validation_loss
        report['peak_cuda_bytes'] = torch.cuda.max_memory_allocated()
        del model, optimizer, trainable, before
        gc.collect()
        torch.cuda.empty_cache()
        reloaded = PeftModel.from_pretrained(load_base(), str(output/'adapter'), is_trainable=False)
        reloaded.eval()
        with torch.no_grad():
            actual = reloaded(**batch(records[2], labels=False), use_cache=False, logits_to_keep=1).logits.float().cpu()
        error = (reference-actual).abs().max().item()
        if not torch.allclose(reference, actual, atol=0.05, rtol=0.01):
            raise ValueError('adapter reload output mismatch')
        report['reload_max_absolute_logit_error'] = error
        report['adapter_sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (output/'adapter').iterdir() if p.is_file()}
        report['production_health_after'] = production_health()
        if report['production_health_after'] != health_before:
            raise ValueError('production identity/health changed during smoke')
        report['status'] = 'PASS'
    except Exception as exc:
        report['status'] = 'FAILED'
        report['error'] = type(exc).__name__ + ': ' + str(exc)
        raise
    finally:
        report['finished_at_unix'] = time.time()
        save()
    print(json.dumps({'status':report['status'], 'output':str(output), 'formal_gate_passed':False}), flush=True)


if __name__ == '__main__':
    main()
