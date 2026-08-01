# 中文驾驶语言代理测试集 v1

`commands.jsonl` 是不依赖 CARLA 的冻结代理测试集，覆盖：

- 普通话与同义表达；
- 否定指令；
- 组合指令；
- 模糊目标；
- 目标不存在；
- 危险冲突指令；
- ASR 低置信度。

每条记录只声明期望高层动作和是否需要确认，不包含油门、刹车或方向盘。
该测试集用于协议、提示词和降级逻辑回归，不能称为主办方隐藏测试集。

验证：

```powershell
python tools/validate_language_testset.py `
  datasets/language_v1/commands.jsonl `
  --report artifacts/language_testset_report.json
```
