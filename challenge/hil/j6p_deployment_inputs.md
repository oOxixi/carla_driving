# J6P 部署输入清单：B3 能提供什么（对"首先找谁"表的逐项答复）

> 来源：2026-09-24 收到的需求表（扫描版 Word），共 5 行；其中 4 行的"首先找谁"是 B3。
> 本文件逐项给出**当前能提供的具体值/命令**、**不能提供的原因**与**缺口归属**。
> 状态图例：✅ 现在就能给全｜🔶 能给部分/替代物｜❌ 给不了（依赖硬件或他人）

## 1. J6P 具体型号 —— ❌ 给不了（依赖硬件）

我们没有实物 J6P 板卡，云上板卡（HiL&SiL）目前也申请不到（无自助入口，见
`cloud_board_request.md`）。**不能用别的板型的数字充当 J6P**：论坛里公开案例分到的是
"天准 TADC-J6E/M"，属 **J6E/M**，其板端性能/资源数字不得写作 J6P 成绩。

板卡一旦到位，我们会现场核对并回报（这几项共同决定"这就是那块 J6P"）：

| 核对项 | 取法 |
|---|---|
| SoC 型号 / BSP / 镜像日期 | `uname -a`、`hrut_somstatus`（HiL&SiL 的板卡检测技能也用这两条） |
| BPU 架构 | `hbUCPGetSocName` 或 OE 手册的"平台差异说明"对照 |
| OE / UCP 版本 | 板端 `hbUCPGetVersion`、`/etc/version` 等 |
| 板卡型号标签 | 硬件负责人或平台页面显示的整机型号 |

## 2. OpenExplorer 版本 —— ✅ 现在就能给

**官方当前正式版：Horizon OpenExplorer 3.9.1（release_date 202608）**

| 依据 | 值 |
|---|---|
| 官方版本发布说明（公开页） | https://doc.oe.horizon.auto/guide/release_note.html |
| 模块版本（同一页表格） | HMCT v2.8.4、HORIZON_TC_UI v3.5.16、HORIZON_Plugin_Pytorch v3.3.10、HBDK_Compiler v4.11.11、UCP_Tutorial v3.15.8、J6PH-Linux-Matrix BSP v4.0.0/v3.0.0/v2.0.0/v1.0.0 |
| 官方下载（需登录，12 个文件） | https://oe.horizon.auto/download/oe |
| 我方已装镜像 | `openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1`（本机已 `docker load`，20.9 GB） |

"不能自行猜"这条我们是按官方页取的，不是推测。**若赛事另有指定版本**（例如红头文件指定 3.8.1 等），
请告知版本号，我们按同一路径下载（下载页支持版本切换）。

## 3. J6P SDK 版本 —— 🔶 官方清单现在能给，板端实测值要等板卡

- **官方清单**（来自上面版本发布说明）：J6PH-Linux-Matrix BSP 现列出 **v4.0.0 / v3.0.0 / v2.0.0 / v1.0.0**；
  `UCP_Tutorial v3.15.8`；OpenExplorer 侧不单独提供 "SDK" 包，板端软件由 **BSP + OE 板端工具**组成。
- **板端实际版本**：必须在板上取（`hrut_somstatus`、`hbUCPGetVersion`、`/etc/version`），
  我们拿到板卡后会连同 SoC 型号一起回报。
- 需要注意的绑定关系：某些能力（如含 TopK 模型的推理抢占）**依赖 BSP 版本**
  （官方限制：J6PH-Linux-Matrix ≥ v3.0.0），所以 BSP 版本不能随便选。

## 4. 转换命令 / 已有 Docker 镜像 —— ✅ 现在就能给（这项我们最完整）

**已有 Docker 镜像（本机已导入）**

```text
openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1
```

镜像内：Python 3.10.12；`hb_compile 3.5.16`、`hmct 2.8.4`、`hbdk 4.11.11`；
`hb_model_info` / `hb_verifier` / `hb_analyzer` 在 PATH。

**起容器**（官方 `run_docker.sh` 等价命令）

```bash
# OE 包根目录下
bash run_docker.sh data/ cpu
# 或手动
docker run -it --rm --network host \
  -v <OE包路径>:/open_explorer -v <数据集路径>:/data/horizon_j6/data \
  openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1
```

**模型验证（只查算子/形状，不生成产物）**

```bash
hb_compile --model resnet50.onnx --march nash-p        # J6P 对应 march = nash-p
```

**正式转换（量化 + 编译，产出板端模型）**

```bash
hb_compile -c <config>.yaml                            # config 内指定 march/nput/cal_data_dir 等
```

**我方的实测记录**（同一套命令，2026-09-23 在本机跑通，可作为"命令可用"的证据）：

| 步骤 | 结果 |
|---|---|
| 校准数据预处理 | `bash 02_preprocess.sh` → `calibration_data_rgb/*.rgb.npy` |
| J6P 编译 | `hb_compile -c resnet50_config_j6p.yaml`（march 改 `nash-p`）→ **4m58s**，产出 `resnet50_224x224_nv12.hbm`（26.3 MB），内存需求 26.35 MB，`HBDK hbm perf SUCCESS` |
| 产物 | `*.hbm`、`*_quantized_model.bc`、`*_ptq_model.onnx`、`*_quant_info.json`、`*_node_info.csv`、profiling `*.html` |
| X86 仿真推理 | `04_inference.sh quanti`（用 `.bc`）→ `zebra_cls.jpg` top-1 = `zebra` |

详见 `pc_deployment_plan.md` §6.4。

## 5. 板端运行示例 —— 🔶 官方示例能给，板端实测示例要等板卡；**但 A4 写 `j6p_run.sh` 更需要的是契约**

**官方现成示例**（都在 OE 包里，A4 可直接参考）

```text
samples/ucp_tutorial/                     # UCP 统一计算平台示例
samples/ucp_tutorial/tools/hrt_model_exec # 板端 aarch64 二进制
package/board/install.sh                  # 板端工具安装
```

官方手册给出的板端调用序列（J6P 适用）：

```bash
hrt_model_exec model_info --model_file=xxx.hbm
hrt_model_exec infer --model_file=xxx.hbm --input_file=xxx.bin --enable_dump=true
hrt_model_exec perf  --model_file=xxx.hbm --thread_num 1 --frame_count=1000   # Latency
hrt_ucp_monitor -b -e bpu -d 1000                                            # BPU 占用率
```

以及 `hbm_infer` 的 X86+板端 RPC 模式（官方定位"更适合批量数据集评测"）：

```python
sess = HbmRpcSession(host="<板卡IP>", local_hbm_path="xx.hbm", with_profile=True)
```

**我方额外提供（比示例更硬的部分）**：A4 的 `j6p_run.sh` 要满足的**可执行契约**已经写好并可自检——

| 我们的检查 | 对 A4 的要求 |
|---|---|
| `contract` → `describe_endpoint` | `<命令> --describe` 返回 §4 的 8 个字段，且 `model_sha256` 等于板端实际加载的产物 |
| `contract` → `batch_mode` | 一个进程内喂 2 个请求（逐行），要求回来 2 个计划且回显 `request_id` |
| `contract` → `model_only_mode` | 支持 `--model-only --input <张量目录>`；张量目录由我们的 `dump-tensors` 生成 |
| `contract` → 打点检查 | `trace` 必须包含 T0–T7 且单调（我们已修掉"重复打点"缺陷） |

用法：

```powershell
py -3.12 -m challenge.hil.cli contract --repo . --adapter board `
  --board-command "<A4 runtime command> --trace" `
  --board-artifact <compiled j6p artifact> `
  --frozen <冻结请求集> --out <输出目录>
```

也就是说：**示例能给，但"在本板卡上验证过的运行示例"给不了**（无板）——不过 A4 只要让上面的
契约检查全 PASS，`j6p_run.sh` 就等价于"跑得通且可测量"。

## 6. 汇总（可直接回给队长/硬件负责人）

| 需求项 | 我们（B3）能给 | 需要别人补 |
|---|---|---|
| J6P 具体型号 | ❌（提供核对清单） | 硬件负责人 / 组委会分配的板卡 |
| OpenExplorer 版本 | ✅ **3.9.1（202608）** + 已装镜像 tag | 若赛事指定别版，请给出指定版本号 |
| J6P SDK 版本 | 🔶 官方 BSP/UCP 版本清单 | 板端实际版本（随板卡） |
| 转换命令 / Docker 镜像 | ✅ 全套命令 + `openexplorer/ai_toolchain_ubuntu_22_j6_cpu:v3.9.1` + 实测产物 | — |
| 板端运行示例 | 🔶 官方示例路径 + 可执行契约（describe/batch/model-only/打点） | 板端实测示例（随板卡） |
