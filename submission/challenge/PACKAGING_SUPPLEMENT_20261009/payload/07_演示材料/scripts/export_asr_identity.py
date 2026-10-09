"""Offline identity inventory only: no ASR imports, model loading or downloads."""
import argparse
from datetime import datetime, timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()


def file_record(path):
    if not path.is_file():
        return {'path': str(path), 'status': 'missing'}
    return {'path': str(path.resolve()), 'status': 'present', 'bytes': path.stat().st_size, 'sha256': sha(path)}


def directory_record(path):
    result = {'path': str(path), 'status': 'missing', 'files': []}
    if not path.is_dir():
        return result
    result['status'] = 'present_inventory_only'
    # Walk only this explicitly selected model directory, never its cache parent.
    for current, dirs, names in os.walk(path, followlinks=False):
        dirs[:] = [n for n in sorted(dirs) if not n.startswith('.') and n not in {'__pycache__', 'cache'} and not (Path(current) / n).is_symlink()]
        for name in sorted(names):
            if name.startswith('.') or name.endswith(('.pyc', '.pyo')):
                continue
            record = file_record(Path(current) / name)
            record['relative_path'] = (Path(current) / name).relative_to(path).as_posix()
            result['files'].append(record)
    return result


def flag(name, default='1'):
    return os.environ.get(name, default).strip().lower() in {'1', 'true', 'yes', 'on'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    package = args.package_root.resolve()
    voice = package / '02_源码与部署/source/voice_group'
    if not voice.is_dir():
        raise SystemExit('Existing voice_group source directory required')
    output = (args.output or package / '07_演示材料/scripts/asr_identity.json').resolve()
    if not output.is_relative_to(package):
        raise SystemExit('Output must remain inside the material package')
    home = Path.home()
    model_cache = home / '.cache/modelscope/models'
    sense = Path(os.environ.get('SENSEVOICE_MODEL_PATH', str(model_cache / 'iic--SenseVoiceSmall/snapshots/master'))).expanduser()
    vad = Path(os.environ.get('FSMN_VAD_MODEL_PATH', str(model_cache / 'iic--speech_fsmn_vad_zh-cn-16k-common-pytorch/snapshots/master'))).expanduser()
    cascade_model = os.environ.get('VOICE_CASCADE_MODEL', 'small')
    cascade = Path(cascade_model).expanduser()
    revision = None
    if not cascade.is_dir() and cascade_model == 'small':
        hub = Path(os.environ.get('HF_HUB_CACHE', str(Path(os.environ.get('HF_HOME', str(home / '.cache/huggingface'))) / 'hub')))
        cache = hub / 'models--Systran--faster-whisper-small'
        reference = cache / 'refs/main'
        if reference.is_file():
            revision = reference.read_text(encoding='utf-8').strip()
            if len(revision) == 40 and all(c in '0123456789abcdef' for c in revision.lower()):
                cascade = cache / 'snapshots' / revision
            else:
                raise SystemExit('Unexpected Hugging Face cached revision; no cache traversal performed')
        else:
            cascade = cache / 'snapshots/MISSING_MAIN_REFERENCE'
    calibration = Path(os.environ.get('VOICE_CASCADE_CALIBRATION', str(voice / 'models/faster_whisper_small_confidence.json'))).expanduser()
    components = {
        'sensevoice': {**directory_record(sense), 'model_id': 'iic/SenseVoiceSmall', 'resolution': 'explicit SENSEVOICE_MODEL_PATH or exact source default cache path; remote fallback not loaded'},
        'fsmn_vad': {**directory_record(vad), 'enabled': flag('VOICE_VAD_ENABLED'), 'model_id': 'fsmn-vad', 'resolution': 'explicit FSMN_VAD_MODEL_PATH or exact source default cache path; remote fallback not loaded'},
        'lora': {**directory_record(voice / 'lora_dialect'), 'enabled': flag('VOICE_USE_LORA')},
        'faster_whisper': {**directory_record(cascade), 'enabled': flag('VOICE_CASCADE_ENABLED'), 'configured_model': cascade_model, 'cached_revision': revision},
        'cascade_calibration': file_record(calibration),
    }
    configs = {name: os.environ.get(name, default) for name, default in {
        'VOICE_USE_LORA': '1', 'VOICE_VAD_ENABLED': '1', 'VOICE_USE_ITN': '1', 'VOICE_ASR_LANGUAGE': 'auto',
        'VOICE_CASCADE_ENABLED': '1', 'VOICE_CASCADE_MODEL': 'small', 'VOICE_CASCADE_DEVICE': 'cuda',
        'VOICE_CASCADE_COMPUTE_TYPE': 'int8_float16', 'VOICE_CASCADE_MIN_CONFIDENCE': '0.90',
    }.items()}
    packages = {}
    for name in ('funasr', 'modelscope', 'torch', 'peft', 'faster-whisper', 'ctranslate2'):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = 'missing'
    report = {'schema_version': '1.0', 'created_utc': datetime.now(timezone.utc).isoformat(),
              'status': 'OFFLINE_IDENTITY_INVENTORY_NOT_A_RUN_BINDING',
              'scope': 'current files and current environment; does not attest historical ASR results or completeness/loadability',
              'package_root': str(package), 'configuration': configs, 'asr_device_source_default': 'cuda:0',
              'components': components, 'installed_package_versions': packages,
              'source_files': [file_record(voice / name) for name in ('asr_vad.py', 'asr_cascade.py', 'pipeline.py')],
              'asr_inference_executed': False, 'download_performed': False, 'same_batch_metrics_claimed': False}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Identity inventory written; ASR/model loading was not performed.')
    for name, component in components.items():
        print(name, component['status'])


if __name__ == '__main__':
    main()
