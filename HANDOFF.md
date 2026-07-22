# Day20 第一组任务 Handoff

## 完成状态

Day20 第一组任务完成。

## 完成模块

### CARLA

完成：

-   ego车辆
-   前车
-   RGB camera
-   SceneState
-   前车制动场景

### Qwen-VL

输入：

-   RGB image
-   驾驶员语音指令
-   SceneState

输出：

DrivingIntent。

### 数据流

    QwenVLAdapter
            |
            v
    parser
            |
            v
    DrivingIntent
            |
            v
    SafetyFilter
            |
            v
    Executor
            |
            v
    CarlaControlAdapter

## 验证命令

``` bash
python -m integration.day20.carla_rgb_qwen_closed_loop
```

## 已验证案例

前车减速：

输入：

    前方车辆减速，请降低速度保持安全距离

输出：

    SET_SPEED
    target_speed_kmh=10

控制：

    CARLA VehicleControl

## 后续任务

等待Day20第二组任务交付后继续。

不要提前修改：

-   GitHub基础接口
-   control模块
-   schemas定义

## Git提交建议

commit message:

    Add Day20 multimodal Qwen-VL CARLA closed loop

上传：

-   integration/day20代码
-   README.md
-   HANDOFF.md

不要上传：

-   artifacts
-   模型
-   checkpoint
