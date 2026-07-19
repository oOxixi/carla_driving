# Day19 RGB Perception + Safety Integration Delivery

## 项目说明

本交付包对应7月19日任务完成版本。

完成内容： - CARLA RGB视觉感知 - ONNX目标检测接口 - 感知结果结构化输出 -
Safety安全仲裁 - CARLA控制链路验证

系统原则： - RGB只提供视觉事实 - 高层决策只输出驾驶意图 -
不直接输出油门、刹车、方向盘 - D安全模块拥有最终否决权

## RGB视觉模块

支持： - 前方车辆检测 - 行人检测 - 交通灯检测 - Sensor
unavailable安全降级

输出字段： - category - confidence - bbox_xyxy - image_region -
in_danger_zone - traffic_light - scene_summary

## ONNX模型

模型位置：

models/yolov8n.onnx

支持类别： - VEHICLE - PEDESTRIAN - TRAFFIC_LIGHT

## Safety模块

完成： - Command验证 - Vehicle State接口 - Risk接口 - SafetySupervisor -
CARLA控制集成

流程：

视觉/状态输入 -\> 高层动作 -\> SafetySupervisor -\> 最终车辆控制

## 验证结果

RGB测试：

pytest rgb_group/tests

结果：

13 passed

前车：

VEHICLE 10/10 frames

行人：

PEDESTRIAN 5/5 frames

Sensor unavailable：

正常进入UNAVAILABLE状态

CARLA：

python -m integration.demo_day19_full_stack

运行通过。

## 调用

安装：

pip install -r requirements_rgb.txt

RGB测试：

python test_onnx_image.py --model models/yolov8n.onnx --image image.jpg

CARLA测试：

python -m integration.demo_day19_full_stack

## 限制

ONNX YOLO当前负责目标检测。

交通灯颜色分类： - CARLA GT支持 - ONNX颜色分类后续扩展。
