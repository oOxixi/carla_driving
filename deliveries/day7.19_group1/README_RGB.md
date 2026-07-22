# CARLA 0.9.16 RGB感知交付包

## 安装

在现有 `voice` 环境中：

```bash
cd /home/dcase_task2/dongfeng_voice/carla_driving
python -m pip install --upgrade pip
python -m pip install opencv-python-headless pytest
```

不要为本模块安装 `ultralytics`；运行时只依赖 `onnxruntime`。先运行：

```bash
python check_rgb_environment.py
python -m pytest -q rgb_group/tests
```

## CARLA服务端

在CARLA 0.9.16安装目录启动：

```bash
./CarlaUE4.sh -RenderOffScreen -nosound -quality-level=Low -carla-rpc-port=2000
```

另开终端执行即时可运行的仿真GT版本：

```bash
cd /home/dcase_task2/dongfeng_voice/carla_driving
conda activate voice
python demo_rgb_carla.py --backend carla_gt --frames 300 --spawn-npc 20
```

## ONNX版本

把模型放到 `models/yolov8n.onnx`，然后：

```bash
python demo_rgb_carla.py \
  --backend onnx \
  --model models/yolov8n.onnx \
  --frames 300 \
  --spawn-npc 20
```

## Git建议

```bash
git checkout -b feature/rgb-perception
git add rgb_group demo_rgb_carla.py check_rgb_environment.py requirements_rgb.txt models/README.md HANDOFF_RGB.md README_RGB.md
git commit -m "feat(rgb): add CARLA RGB perception and unified VisionObservation"
git push -u origin feature/rgb-perception
```
