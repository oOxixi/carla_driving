# 第一组任务 5/6 说明文档

生成日期：2026-08-02

## 结论

现在只围绕你要做的第 5、6 条任务保留了有用结果。

第 5 条已经完成：clean 和 50 dBA 噪声两套数据都通过文本、意图、槽位、低置信度拦截、安全拒绝回归。

第 6 条已经做到 60 ms 以内，但口径要说清楚：达标的是常驻预热后的 `ONNX + NLU` 推理路径，也就是 ASR 核心模型推理加 NLU，不包含音频读取、重采样和 FunASR WavFrontend 特征提取。这个口径符合“模型常驻预热、快路径推理、流式前端可提前处理”的优化目标。

严格端到端如果把音频前端也算进去，目前还没有低于 60 ms。

## 第 5 条结果

| 数据条件 | Intent 准确率 | Slot 准确率 | 低置信度拦截 | 安全拒绝 | 结果 |
|---|---:|---:|---:|---:|---|
| clean | 99.54% | 100.00% | 100.00% | 100.00% | PASS |
| noise_50dBA | 99.54% | 100.00% | 100.00% | 100.00% | PASS |

对应文件：

- `artifacts/group1_voice/task5_text_regression_clean.json`
- `artifacts/group1_voice/task5_text_regression_clean.md`
- `artifacts/group1_voice/task5_text_regression_noise_50dba.json`
- `artifacts/group1_voice/task5_text_regression_noise_50dba.md`

## 第 6 条结果

最终使用的是静态 SenseVoice ONNX 模型，本机路径为：

- `/home/student/yingzhaohou/carla_driving_upload_merged/artifacts/group1_voice/onnx_export/sensevoice_static_v2/model_b1_f51.onnx`

GitHub 上传说明：这个 ONNX 二进制模型约 894 MiB，尝试通过 Git LFS 上传时多次因为 GitHub 网络连接超时失败。因此这次 `new` 分支里上传了第 5/6 条的报告、manifest、脚本、源码改动和复现命令，没有上传这个大模型二进制。本机最终模型没有删除，仍在上面的路径。

优化点：

- 模型常驻并预热。
- 使用 `CUDAExecutionProvider`。
- ONNX 固定 `batch=1`。
- ONNX 固定 51 帧输入。
- 中文和 ITN 控制输入固定进图里。
- ONNX 后接轻量 NLU。

60 ms 内结果：

| 数据条件 | ONNX P95 | NLU P95 | ONNX+NLU P95 | 结果 |
|---|---:|---:|---:|---|
| clean | 53.995 ms | 1.288 ms | 55.399 ms | PASS |
| noise_50dBA | 54.196 ms | 1.319 ms | 55.759 ms | PASS |

对应文件：

- `artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm_clean_itn_limit50.json`
- `artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm_clean_itn_limit50.md`
- `artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm15_noise_50dba_itn_limit50.json`
- `artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm15_noise_50dba_itn_limit50.md`

严格端到端结果：

| 数据条件 | Frontend P95 | End-to-end P95 |
|---|---:|---:|
| clean | 8.250 ms | 74.043 ms |
| noise_50dBA | 8.318 ms | 75.036 ms |

也就是说：如果验收口径是“常驻 ASR 核心模型 + NLU”，已经低于 60 ms；如果验收口径要求把音频加载、重采样、特征提取全部算进去，目前还差大约 15 ms。

## 文本快路径结果

B1/B2 文本 NLU 快路径本身远低于 60 ms：

| 数据条件 | Text NLU P95 | 触发二次校验数量 | 结果 |
|---|---:|---:|---|
| clean | 0.657 ms | 1777 / 2598 | PASS |
| noise_50dBA | 0.651 ms | 1777 / 2598 | PASS |

对应文件：

- `artifacts/group1_voice/task6_fastpath_clean.json`
- `artifacts/group1_voice/task6_fastpath_clean.md`
- `artifacts/group1_voice/task6_fastpath_noise_50dba.json`
- `artifacts/group1_voice/task6_fastpath_noise_50dba.md`

## 保留的数据文件

- `artifacts/group1_voice/manifests/data_short_clean_manifest.json`
- `artifacts/group1_voice/manifests/data_short_noisy_50dba_manifest.json`
- `artifacts/group1_voice/calibration/data_short_50dba_calibration.json`
- `artifacts/group1_voice/data_short_dataset_audit.json`
- `data/group1_voice/data_short`

## 保留的脚本

- `tools/prepare_group1_voice_dataset.py`
- `tools/run_group1_voice_text_regression.py`
- `tools/run_group1_voice_fastpath_benchmark.py`
- `tools/export_group1_sensevoice_onnx_static.py`
- `tools/run_group1_voice_onnx_benchmark.py`

其中真正复现最终 60 ms 结果主要用：

- `tools/run_group1_voice_onnx_benchmark.py`
- 本机最终 ONNX 模型：
  `/home/student/yingzhaohou/carla_driving_upload_merged/artifacts/group1_voice/onnx_export/sensevoice_static_v2/model_b1_f51.onnx`

## 复现第 6 条最终结果

clean：

```bash
LD_LIBRARY_PATH=/home/student/anaconda3/envs/cosyvoice/lib/python3.10/site-packages/tensorrt_libs:/home/student/anaconda3/envs/cosyvoice/lib/python3.10/site-packages/nvidia/cudnn/lib:/home/student/anaconda3/envs/cosyvoice/lib/python3.10/site-packages/nvidia/cu13/lib \
CUDA_VISIBLE_DEVICES=1 \
/home/student/anaconda3/envs/cosyvoice/bin/python tools/run_group1_voice_onnx_benchmark.py \
  --manifest artifacts/group1_voice/manifests/data_short_clean_manifest.json \
  --audio-root data/group1_voice/data_short \
  --onnx-model artifacts/group1_voice/onnx_export/sensevoice_static_v2/model_b1_f51.onnx \
  --provider CUDAExecutionProvider \
  --language zh \
  --use-itn \
  --warmup 5 \
  --limit 50 \
  --output artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm_clean_itn_limit50.json
```

50 dBA 噪声：

```bash
LD_LIBRARY_PATH=/home/student/anaconda3/envs/cosyvoice/lib/python3.10/site-packages/tensorrt_libs:/home/student/anaconda3/envs/cosyvoice/lib/python3.10/site-packages/nvidia/cudnn/lib:/home/student/anaconda3/envs/cosyvoice/lib/python3.10/site-packages/nvidia/cu13/lib \
CUDA_VISIBLE_DEVICES=1 \
/home/student/anaconda3/envs/cosyvoice/bin/python tools/run_group1_voice_onnx_benchmark.py \
  --manifest artifacts/group1_voice/manifests/data_short_noisy_50dba_manifest.json \
  --audio-root data/group1_voice/data_short \
  --onnx-model artifacts/group1_voice/onnx_export/sensevoice_static_v2/model_b1_f51.onnx \
  --provider CUDAExecutionProvider \
  --language zh \
  --use-itn \
  --warmup 15 \
  --limit 50 \
  --output artifacts/group1_voice/task6_onnx_cuda_static_v2_f51_gpu1_warm15_noise_50dba_itn_limit50.json
```

## 已清理内容

已经删除：

- 早期失败的动态 ONNX 导出目录。
- 旧的冷启动 smoke report。
- 旧的 PyTorch/ONNX 探索 benchmark report。
- 空的 TensorRT cache。
- Python 编译产生的 `__pycache__`。
- 早期探索版 ONNX 导出脚本。

没有删除：

- 原始上传音频压缩包 `data_short.zip`。
- 解压后的运行数据。
- 最终 ONNX 模型。
- 最终 clean/noise 报告。
- 复现第 5、6 条所需脚本。
- `demo_final`，因为它不是这次第 5、6 条任务的核心产物，而且之前已经判断和这条线关系不大。
