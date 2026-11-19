# 数值条件化速度Head：开发候选与评分边界

结论：全量数值分支未通过开发回归；收缩为只校准首步SET_SPEED/SLOW_DOWN/FOLLOW的候选后，通过本轮开发验收与CPU ONNX数值校验。**候选尚待独立性能评测及官方部署验证，不替换原robust-v3。**

## 按比赛规则限定范围

核对本机XH-202602初审细则第三、四、六节。初赛算法50分、初审部署50分。挑战50分由FLOPs压缩比15、异构算力利用率10、核心指标衰减15、创新性10组成。FLOPs≤0.5、利用率≥80%、核心指标相对衰减≤3%分别对应相关项最高档，**不是本实验已取得的分数**。

- 核心指标应按同数据、同冻结口径比较原始Teacher与部署Student的应用性能；本报告的速度误差、开发命中及Teacher一致率不能代替语音指令理解与多模态语义对齐的正式指标。未使用B2的独立验证或封存Test训练、调参或宣布通过。
- 自建开发数据保留来源、分组、标签规则、清单、脚本及权重哈希；上一轮336/80是原Train/Val内容绑定RGB上的多档位指令补样，不是新路况、Teacher新采闭环或官方1000帧。
- 保留现有RGB/text/targets/state四路固定输入和十个输出、原多模态主干、其他Head、Adapter、Validator及安全控制。未改正式评分器、容差、验收分母或生产配置。

## 技术实现

在速度Head的logit内加入可训练残差，使用已有state中的数值提示、意图与允许动作标记。SET_SPEED、SLOW_DOWN和FOLLOW各自学习参数；FOLLOW沿用单侧上限损失，不把上限当设定目标。正值提示缺失/为零、待确认、必须停车、动作不允许时残差关闭。**不在Adapter中用提示值替换模型预测**，正常限速与安全规则仍独立生效。

原23,006,581个参数全部冻结。全量试验增加12个参数（首步9个、后续3个），从原robust-v3 SHA `7f379c78c170228713e3d91b8e2eabd04172010ae0ed0b8cf71afe291fe6e805` 起训。GPU 2、1600步，复用原5856/1108 Train/Val冻结特征；用原清单和标签顺序重建state，补样336/80和216组档位配对，沿用原开发选模标准。源码 `23cf364820f91eeb95fdf2c0d4ce46196896514c`。38个检查点通过选模Val，选中1080步；冻结后才复核旧128条探针。

## 失败定位与范围收缩

全量版的后续分支对数字有响应，但旧探针上基线速度logit与补样Val的分布不同，出现整体偏高。例：旧探针请求12/18/24/27 km/h，组合末步新预测均值约21.01/28.17/37.02/42.29。Adapter仍限速，不能挽回指定速度准确率。学习到的末步残差基本保留原logit的偏移（残差中的原logit系数约−0.0365）；这是与观察一致的机制解释，不是已证明的唯一原因。

据此移除3个后续校准权重，**不再拟合、不重选训练步**，保留9个首步残差参数，新版本 `student-v0-r3-numeric-primary-v1-fp32`。转向/换道组合在本分支不匹配首步校准条件，复核中所有组合速度槽与原版逐字节一致。此范围是在看过旧Dev退化后确定的，因此旧128只能叫回归，不能改称独立Test。

| 旧128开发探针（每类32） | 原robust-v3 | 全量数值分支（拒绝） | 首步受限候选 |
| --- | ---: | ---: | ---: |
| 单独设速 | 8 | 32 | 32 |
| 减速至指定值 | 8 | 32 | 32 |
| 换道后设速 | 8 | 0 | 8 |
| 跟车目标和速度上限（原始Head） | 16 | 24 | 24 |

跟车经Adapter的上限/目标命中均为32/32，不代表动态跟车性能。新选模Val每类20条，原版→受限候选分别6→20、0→20、4→4、10→12（跟车原始Head）。原1108 Val速度MAE 0.3782→0.3135 m/s；安全关键0.5315→0.5235；后续步骤约1.0826不变。受限候选在80/128条的9个非速度Head输出逐字节一致；原模型参数也逐字节不变。未证明端到端ASR准确率或行驶闭环提升。

## 部署预检与待办

- 源码 `6582dc9909a5298c416d092682e9e6d37224c748`；57项相关测试通过。诊断FP32 ONNX opset17固定4输入/10输出，11组输入（含掩码检查），110项Torch/ORT CPU数值对照通过，最大绝对误差 `7.6294e-06`。
- 同仓库Conv/Linear口径：基线498,640,896→受限版498,640,914 FLOPs（新增9 MAC、9参数），未包含掩码逐元素运算。对既有保守Teacher下界的分析比值约0.177，**不是官方FLOPs复算或得分证据**。
- 导出图60→139节点，增加48个Constant；新增Add/Cast/Greater/MatMul/Slice/Sub类型。节点计数不是BPU利用率，尚未证明这些新增节点在OpenExplorer上的落点及融合效果。没有INT8、正式A2导出、官方X86 Docker、J6P、功耗或HIL通过结论。
- 下一步：由B2冻结正式同口径Teacher/Student配对评测（不再以正式集调参）；通过后由A2/A4校准、量化、编译并提供算子落点与fallback报告，再按官方环境复测性能保持及异构利用率。组合数值仍待独立解决，不能把8→8写成修好。

## 产物

本机 `artifacts/numeric_speed_conditioned_20261112/`；服务器 `/home/tiaozhansai/carla-driving-challenge/artifacts/numeric_speed_conditioned_20261112/`。

- `trial_01/result.json`、`paired_results.json`、`training.jsonl`：全量拒绝结果及训练证据。全量权重保留服务器，SHA `80a3f2ce15bae1245d242ee908174bf6ba5ca45744e88aca4f7bbb7169023935`。
- `primary_only/student_numeric_primary_fp32.pt`，SHA `20be5f643b54e584beb983e39393c5d4e83f7e6baabaeec5aa58ce68c159c3ef`。
- `primary_only/student_numeric_primary_diagnostic.onnx`，SHA `79327f40e65a58dd484f7c614aa5c964df360455475c919528173388021f5f31`。
- `primary_only/result.json`、`paired_results.json`、`operator_comparison.json`：受限候选指标、逐例结果、算子清单；状态 `PRIMARY_ONLY_DEV_CANDIDATE_PENDING_INDEPENDENT_GATE`。
- 两端证据包SHA `25e37db92677fd24408289f1c858b7d99d64dfb886e18a135f92f0a784955ab1`；受限权重与ONNX两端SHA已核对。

未部署、未签发正式Gate、未推送GitHub。
