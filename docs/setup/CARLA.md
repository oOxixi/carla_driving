# CARLA 0.9.16 启动

CARLA Python API 与项目 Python 环境版本必须匹配。启动服务端后，先运行场景静态验证，
再做短时冒烟，最后执行完整里程。

Windows 示例：

```powershell
Start-Process -FilePath "D:\CARLA_0.9.16\CarlaUE4.exe" `
  -ArgumentList "-quality-level=Low" -WindowStyle Hidden
python tools/validate_official_scenes.py
```

Linux 示例：

```bash
./CarlaUE4.sh -RenderOffScreen -quality-level=Low
python tools/validate_official_scenes.py
```

服务器正式运行步骤见 `docs/runbooks/SECOND_GROUP.md`。
