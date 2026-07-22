# Day20 第一组任务：CARLA + Qwen2.5-VL 多模态驾驶行为决策

## 状态

Day20 第一组任务已完成。

实现链路：

CARLA RGB Camera + SceneState + Driver Instruction → Qwen2.5-VL →
DrivingIntent → Safety Filter → Executor → CarlaControlAdapter →
VehicleControl

## 已完成内容

-   CARLA Town10HD_Opt运行
-   ego vehicle生成
-   front vehicle生成
-   前车减速事件
-   RGB camera采集
-   SceneState构建
-   Qwen2.5-VL视觉语言推理
-   JSON Intent解析
-   DrivingIntent接口统一
-   Safety Filter安全层
-   CARLA闭环控制

## 目录说明

integration/day20/

-   qwen_vl_adapter.py\
    Qwen-VL多模态推理接口

-   scene_builder.py\
    SceneState生成

-   parser.py\
    JSON到DrivingIntent转换

-   schemas.py\
    Action和DrivingIntent定义

-   safety_filter.py\
    安全约束层

-   day20_intent_executor.py\
    高层动作执行转换

-   carla_control_adapter.py\
    CARLA控制适配

-   carla_rgb_qwen_closed_loop.py\
    完整闭环Demo

## 输入接口

SceneState:

``` json
{
 "ego":{
  "speed_kmh":11.77,
  "lane_id":0
 },
 "objects":[
  {
   "object_id":"73",
   "category":"vehicle",
   "distance_m":4.23,
   "direction":"front"
  }
 ]
}
```

## Qwen输出接口

``` json
{
 "actions":[
  {
   "action":"SET_SPEED",
   "target_id":"73",
   "target_speed_kmh":10
  }
 ],
 "confidence":0.9,
 "reason":"front vehicle slowing"
}
```

## 运行

``` bash
python -m integration.day20.carla_rgb_qwen_closed_loop
```

要求：

-   CARLA Server启动
-   Python 3.12环境
-   Qwen2.5-VL模型存在

默认模型：

models/Qwen2.5-VL-7B

## 输出产物

运行后：

artifacts/day20/

包括：

-   scene_xxxx.json
-   qwen_raw_output.json
-   driving_intent.json
-   executor_target.json
-   carla_control.json

## 测试结果

测试：

驾驶员：

前方车辆减速，请降低速度保持安全距离

Qwen输出：

SET_SPEED

最终控制：

throttle/brake/steer由CarlaControlAdapter产生。

## 工程原则

不修改GitHub已有控制接口。

通过Adapter方式接入。

不要提交：

-   模型文件
-   checkpoint
-   artifacts运行结果
-   RGB图片
