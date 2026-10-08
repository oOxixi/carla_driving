# 当前 Student 同次演示与摄像头录像

安装：将本 overlay 的 `payload` 内容合并复制到完整材料包根目录，保留 `06_评测说明与冻结方案`、`07_演示材料` 等相对目录。脚本从自身位置推导包根目录，不绑定开发者机器路径。本 overlay 不包含源码主体、模型、音频、原始评测数据，不能单独启动完整演示。

这两份脚本用于在具备 CARLA 服务端、匹配的 CARLA Python API、ONNX Runtime、语音前端依赖及 ffmpeg/libx264 的演示机上实录。它们没有在本机执行仿真或产生演示视频。缺依赖会明确退出，不生成替代视频。

从本目录执行：

```powershell
python run_student_demo.py --dry-run
python run_student_demo.py --frames 1200 --realtime --follow-spectator
python run_student_demo.py --audio "./recordings/command.mp3" --host 127.0.0.1 --port 2000 --service-port 8100 --frames 1200 --realtime
```

默认输入是包内现有 `voice_group/test_samples/mandarin/0003.mp3`，文本为“速度设为30公里。”，属于 TTS 音频。指定 `--audio` 可改用已有录音，清单会记录实际文件和 SHA-256。脚本不添加 `--qwen-remote`，也不输入预制文本冒充 ASR。

默认场景明确为 runner 内置 `--scenario cruise`，使用 CARLA 当前地图的生成路线，不读取 `scenarios/*.json`，不是 83 场验收套件复跑。其所需 `source/config/driving_policy.json` 必须存在，启动前会检查。复跑验收套件则还需要另行安装完整 `source/scenarios/acceptance_suite/` 等场景文件，并使用对应场景运行命令；不能将本演示称为验收套件结果。

Linux/PulseAudio 现场口述：

```bash
python run_student_demo.py --live-mic --live-mic-source @DEFAULT_SOURCE@ --frames 2400 --realtime --follow-spectator
```

现场录音模式要求 `parecord`，同时保存麦克风 WAV。不要把 `--live-mic` 与 `--audio` 或 scenario-file 结合。启动器不提供 scenario-file 参数，以避免旁路音频链路。

输出默认在 `07_演示材料/runs/UTC时间/`：当前模型 SHA-256、输入音频/麦克风 WAV、服务健康与输出日志、runner 原生证据、摄像头与 ffmpeg 日志、对应 CARLA frame/sim_time 的逐帧索引，以及成功封装的 `camera/camera.mp4`。服务原生日志只复制本次启动后更新的文件；并行运行时使用不同服务端口，服务原生共享日志目录仍应避免同 variant 并发。

摄像头等待角色 `acceptance84:ego`，附着车后方，只录 CARLA RGB 数据，不录桌面、不调用 world.tick、不改同步设置。MP4 是无声车辆画面；音频单独留存，逐帧时间和 runner 日志用于同次核对。视频按 20 FPS 编码，队列丢帧会记录在 camera_result.json；不可据固定播放时长推断真实时延。没有自动拼接离线结果或虚构音画同步。

所有子进程在结束或异常时清理；外部已经运行的 CARLA 服务器不会被关闭。完成录像只标为 `EXECUTED_REQUIRES_CONTENT_REVIEW`，还须查看同次日志确认 ASR 转写、Student 请求/计划和实际车辆控制；不据文件存在宣称任务成功。

也可对已经运行的车辆独立录像：

```powershell
python record_carla_camera.py --host 127.0.0.1 --port 2000 --output-dir "./camera_output"
```

在 output-dir 创建名为 `STOP` 的文件即可正常结束并封装视频。服务预热失败、找不到 ego、ASR 缺依赖、ffmpeg 编码失败均保留实际错误，不交付伪录像。
