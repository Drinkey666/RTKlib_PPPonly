# PPP_only

[2026-11-17 项目现状、代码定位与回放数据](docs/PROJECT_STATUS_AND_EVIDENCE_20261117.md)

## 当前正式运行入口（2026-10-20）

正式主线是 **B_VERIFIED_v2_JOSEPH**，恢复码质控仍为独立候选。`BASELINE=B`单独设置是旧B；下文的A/PHYSICAL/融合入口保留作历史研究，不代表当前推荐。

- 可追溯归档回放：`run_ppp.cmd <文件清单.json> --output <新的结果.pos>`，默认调用正式VS EXE。模板为`config/b_verified_replay.example.json`，只更换输入路径；TXT将`OBS`改为`TXT`并选择`txt-fast`/`txt-realtime`。
- 预报发布/接收可用性严格检查：`run_forecast_ppp.cmd <含接收记录的清单.json> [--run]`。两入口共用`config/b_verified.json`正式预设；归档回放不能充当历史实时可用性证明。
- 新会话级恢复质控：`run_recovery_session_trial.cmd <文件清单.json> --output <新的结果.pos>`，使用独立trial.exe，未合入正式VS或Android。
- 原`run_b_verified.cmd`和VS使用`RTK_PPP_PROFILE=B_VERIFIED`的方式仍可用。

新入口记录输入/EXE/预设SHA256、实际PPP_CONFIG及结果状态，拒绝覆盖旧结果。工程化四组与旧BRIDGE3结果精确一致，未声称新的精度改善。详见[入口及会话质控工程化报告](docs/B_VERIFIED_SESSION_HARDENING_REPORT.md)。

当前验证主线：**文件预报产品支持的实时非组合PPP，SSR关闭**。
新增入口为`run_forecast_ppp.cmd`，要求预报段及产品接收记录检查通过后才运行。
说明与配置模板见[预报专用流程](docs/FORECAST_ONLY_WORKFLOW.md)。原VS入口及历史A/B/FIN基线保留；
直接运行原EXE不自动启用Python专用入口。

基于 RTKLIB 改进的 PPP 定位程序。此仓库只包含 Visual Studio 工程实际编译的源码，支持 RINEX 观测文件和 Android 原始 TXT 回放。`PPP_only/ppp_position.c` 是 PPP 专用的单历元定位控制器，核心滤波在 `src/ppp.c`。

## 构建

用 Visual Studio 2022 打开 `PPP_only.sln`，选择 **x64 / Release** 构建。生成的程序位于 `x64/Release/PPP_only.exe`。

## 运行

运行 `PPP_only.exe --help` 查看参数。无界面运行可用 `--no-gui`；先用 `--check-files` 检查观测文件和星历等精密产品路径。输入文件可通过 `RTK_PPP_OBS`（RINEX）或 `RTK_PPP_TXT`（Android TXT）选择，两者不能同时设置。精密产品可通过 `RTK_PPP_NAV`、`RTK_PPP_SP3`、`RTK_PPP_CLK`、`RTK_PPP_BIA`、`RTK_PPP_IONEX`、`RTK_PPP_VMF_FIRST`、`RTK_PPP_VMF_SECOND`、`RTK_PPP_OROGRAPHY` 和 `RTK_PPP_ATX` 指定；结果路径用 `RTK_PPP_OUTPUT` 指定。输入数据与精密产品未包含在仓库中。

PPP 启动仍使用 `pntpos.c` 获取粗位置。RTCM 模块保留了 PPP 可用的 SSR 路径及其链接依赖。其余 RTK、多厂商接收机协议、网络流、数据下载和格式转换模块不进入此工程。

源码保留原 RTKLIB 作者的版权声明。此工程在本地通过了 x64 Release 编译，以及 RINEX 1200 历元和 Android TXT 20 历元相对精简前版本的数值回归验证。

## 文件目录清理

本项目的 `src` 只保留实际构建源码。旧副本 `E:\GNSS\rtklib_only\rtklib_only` 中不被 PPP 与现有测试工程引用的源码已实际移至项目外归档，带原路径、SHA256 和恢复脚本；历史算法、测试和未提交修改保留。范围与验证见 [文件清理记录](docs/FILE_CLEANUP.md)。

## Phase 1：A/B 基线与回归

历史参照为 `97a57a9`，本地标签 `legacy/current-robust-97a57a9`。
PC 直接运行默认保持 **B / LEGACY**，以复现历史算法；A 使用修正后的周跳弧段和连续 PPP 钟差。运行日志中的 `PPP_CONFIG` 会明确写出实际模式。

```powershell
$env:RTK_PPP_BASELINE = 'A'             # CLEAN_BASELINE，需显式选择
Remove-Item Env:RTK_PPP_LIFECYCLE -ErrorAction SilentlyContinue
# 使用现有产品环境变量，再运行 PPP_only.exe --source txt-fast --no-gui

$env:RTK_PPP_BASELINE = 'B'             # LEGACY_BASELINE；也是直接运行的默认值
# 如需明确记录：$env:RTK_PPP_CLOCK = 'LEGACY_SPP'
# 对照修正后的生命周期时显式改为 CORRECTED，并标注为 B+CORRECTED
```

数值失败保护在两组中均生效。A 的 eta 恒为 1，关闭历史抗差、质量学习、平滑和虚拟大气约束；C/D 尚未实现，选择时直接报错。有效基线、生命周期和实际策略打印在 `PPP_CONFIG` / `PPP_POLICY`，定权层记录在 `$PPP_R`。

`-ARCGAP=30` 是修正生命周期的时间中断阈值（秒，默认 30）；`maxout` 仍为缺测历元数，两者单位独立。非空 `RTK_PPP_OPTS` 仍然整体替换旧选项串。

构建 Release x64 后运行：

```powershell
./tests/run_phase1_tests.ps1
# 同输入回放需本机测试产品和 validation/phase1/PPP_only_97a57a9.exe
# Python 路径以本机运行时为准
python tests/run_phase1_replay.py
python tests/run_phase1_rinex.py
```

实施、验证结果和未处理问题见 [Phase 1 报告](docs/PHASE1_REPORT.md)。

## Phase 2：只读新息诊断

以已验收 `ac99aba` 为参照，A/B 算法保持不变。设置 `RTK_PPP_INNOVATION_DIAG` 为独立 CSV 文件路径可开启诊断；未设置时关闭。每条有效 pre-fit 行记录实际 signal/source 映射、pred_var、Rii、Sii 和 u=v/sqrt(Sii)，虚拟大气约束单独分类。日志区分首次 pre-fit 与编辑重试，不按 u 改权或拒绝。

实施、同输入回归、统计解释限制及后续学习不适用样本见 [Phase 2 报告](docs/PHASE2_REPORT.md)。测试：`tests/run_phase2_tests.ps1`；回放与离线统计：`tests/run_phase2_replay.py`、`tests/run_phase2_rinex.py`、`tests/summarize_phase2.py`。诊断需要独立输出路径；原始数据/运行日志保存在本地 validation，不进入仓库。

## Phase 2.5：学习资格与异常证据审计

保持 `4715448` 的A/B结果，诊断日志增加当期SPP/模糊度初始化来源及P/L分别维护的连续弧段标签；离线分类不反馈滤波。当前600历元样本没有严格可学习伪距：当期SPP钟差重建或来源不确定违反独立预测要求。分析、五种lag相关、10/30/60窗口与ESS限制见 [Phase 2.5 报告](docs/PHASE2_5_REPORT.md)。

测试/回放/离线分析：`tests/run_phase2_5_tests.ps1`、`tests/test_phase2_5_analysis.py`、`tests/run_phase2_5_replay.py`、`tests/run_phase2_5_rinex.py`、`tests/analyze_phase2_5.py`。R/Q、权重、reject、eta均未改变。

## 普通抗差卡尔曼滤波 C

先按 [PPP运行准入](docs/PPP_OPERATIONAL_GATE.md) 核对当前PC非组合PPP，再用 `RTK_PPP_BASELINE=C` 显式启用一次验前Huber权重EKF。C沿用A的函数模型、固定Q/R0和正确弧段处理；每条真实GNSS码/相位行使用 `u=v/sqrt(hP^-h^T+R)`，当前历元按固定截止值1.5计算权重。直接运行默认B；显式A/B/C各自算法不变。D和信号级eta未启用。实施及TXT/RINEX对照见 [普通抗差报告](docs/PPP_ROBUST_KALMAN_REPORT.md)。

测试命令：`tests/run_robust_tests.ps1`；同输入回放：`tests/run_robust_replay.py`；诊断核对：`tests/run_robust_diag.py`。

## 3/17 与 3/21 精度差异诊断

TRACE 显示历史 B 的逐历元 SPP 钟差重置会造成全星座共同的验前新息偏移并触发载波方差 25 倍放大；3/17 同样有此现象，不能单靠它解释两天高程差异。用户 `test4.pos` 的同产品回放已逐行复现 A 在 3/17 启动段超过 2 m 的高程偏差；只改钟差或弧段都不能消除峰值。曾尝试将直接运行默认改为 A，现已撤回。后续须继续核查对流层、IONEX 先验及产品/观测模型的耦合。详见 [TRACE 核查报告](docs/MAR21_TRACE_ROOT_CAUSE.md) 和 [精度诊断报告](docs/PPP_ACCURACY_DIAGNOSIS.md)。

## 手机实时抗差 PPP APP 路线

当前项目能力、基础可靠性问题、实时产品链、共享核心/JNI 建议和分阶段验收见 [项目提升建议](docs/PROJECT_IMPROVEMENT_ROADMAP.md)。该报告为审查建议，不改变现有算法；当前 C 已实现普通验前 Huber 加权，早期 Phase 1 的 C/D 状态仅代表当时版本。

2026-10-09 基础可靠性修复：SPP 失败候选解隔离、Android 时钟/ADR 重置事件跨缺测保留；沿用 SP3/CLK/BIA 文件产品路径，没有接入 SSR。修复范围、正常回归与 TXT 异常路径变化见 [修复报告](docs/RELIABILITY_FIX_REPORT.md)。

2026-10-10 统一产品检查：正常选择文件运行时，自动检查产品内容、时间覆盖和实际观测卫星/信号的可用性，生成 `<结果文件名>.products.log`。`--check-files` 现在执行同样的内容检查而不启动解算；严重错误停止，局部缺失明确警告。实时路线使用预报产品文件，不需要 SSR 流。检查范围、限制及回归证据见 [统一产品检查报告](docs/PRODUCT_CHECK_REPORT.md)。

2026-10-10 普通抗差验证：现有 C Huber 的公式、权重、数值保护与重复回放通过验证；受控异常发现当期 SPP 钟差初始化会影响其他观测权重，尚不能据此宣称精度优于 A。C 的启用方式和证据见 [普通抗差验证报告](docs/ORDINARY_ROBUST_VERIFICATION.md)。

2026-10-10 钟差交接修复：A/C 以已提交的 PPP 钟差继续预测，在滤波前由不同卫星的有效连续相位或码残差估计公共钟差位置；显式 B 保留旧 SPP 路径。双击 `run_huber_ppp.cmd` 可用 C + 新路径处理文件。旧路径 9 次同输入回放逐项一致；单星码异常下，C 首次试算对其他未改写行的连带降权从 540 降至 0；持续公共钟跳仍可响应。实施、边界与证据见 [钟差交接报告](docs/CLOCK_HANDOFF_REPORT.md)。

## 精密产品参考模型

使用 WUM NRT 的 SP3/CLK/BIA 时，选择 BIA `APC_MODEL` 声明的 ANTEX 版本（现有 3/17、3/21 产品均为 `E:\RTKLIB_Data\Tables\igs20_2408.atx`）。程序现在从 BIA 读取钟差参考频率，按物理频率合成卫星参考 APC，并对每条信号应用相对 PCO 和对应频率的 PCV；码 OSB 按有效期和 Bias-SINEX 符号应用。产品版本冲突会在 `<输出>.products.log` 给出明确错误。`RTK_PPP_REFERENCE_MODEL=LEGACY` 仅用于复现旧的固定参考频率与 DCB 回退，它与 A/B/C 抗差模式分别设置。

公式、来源、单元测试与 3/17、3/21、TXT 回放见 [精密产品参考模型报告](docs/PRODUCT_REFERENCE_MODEL.md)。此修复没有消除 3/21 的米级高程偏差；后续仍需按报告中的未证实项目排查。

2026-10-11 IONEX 时间修复：地图保存 UTC，GPST 查询在核心统一转换为 UTC，用于时间插值和日固坐标补偿；覆盖诊断使用同一查询域，最后地图的精确历元可用。默认 A/B/C 都使用修正路径；`RTK_PPP_IONEX_TIME=LEGACY` 可复现旧时间处理，独立于产品参考与抗差模式。实现和验证见 [IONEX 时间修复报告](docs/IONEX_TIME_FIX_REPORT.md)。

## 非组合 PPP 的 raPPPid 参考融合

2026-10-11：新增可选的接收机码对基准、模型湿延迟＋估计改正、固定预测先验的历元内 IEKF。保留逐频 P/L，未使用 IF 组合或在线 eta。

双击 `run_integrated_huber_ppp.cmd` 启用三项融合与已有普通抗差；`run_integrated_ppp.cmd` 使用同一融合模型及 A 固定基础 R。VS 调试环境设置 `RTK_PPP_BASELINE=C`、`RTK_PPP_CLOCK=PPP_COMMON`、`RTK_PPP_ESTIMATOR=INTEGRATED`（各一行，无引号）。原启动入口显式保留原估计模型，直接运行仍默认 B。

新码偏差基准改变了有效电离层与先验/过程模型语义，暂作为实验路径；3/21 高程偏差仍约 −3.10 m，3/17 末高程因该基准移动约 −0.407 m，不能宣称精度问题已解决。43 项新测试、旧测试与同输入回放、因果前缀对照通过。使用、配置、数学定义、限制和结果见 [融合报告](docs/RAPPPID_ESTIMATOR_REPORT.md)。

## GLONASS G1 可选路径

新融合配置现支持 RINEX 中的 GLONASS C1C/L1C 单频，与 GPS/Galileo/BDS 联合处理。使用 `run_integrated_huber_glo_ppp.cmd`；默认系统保持 G/E/C。G2/G3、Android 原始 TXT/JNI 的 GLONASS 转换尚未接入。3/21 米级高程偏差仍存在，启用 GLONASS 不代表问题已解决。

模型范围、启用步骤及回归结果见 [GLONASS G1 接入报告](docs/GLONASS_G1_INTEGRATION.md)。
