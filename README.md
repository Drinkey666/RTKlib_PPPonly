# PPP_only

基于 RTKLIB 改进的 PPP 定位程序。此仓库只包含 Visual Studio 工程实际编译的源码，支持 RINEX 观测文件和 Android 原始 TXT 回放。`PPP_only/ppp_position.c` 是 PPP 专用的单历元定位控制器，核心滤波在 `src/ppp.c`。

## 构建

用 Visual Studio 2022 打开 `PPP_only.sln`，选择 **x64 / Release** 构建。生成的程序位于 `x64/Release/PPP_only.exe`。

## 运行

运行 `PPP_only.exe --help` 查看参数。无界面运行可用 `--no-gui`；先用 `--check-files` 检查观测文件和星历等精密产品路径。输入文件可通过 `RTK_PPP_OBS`（RINEX）或 `RTK_PPP_TXT`（Android TXT）选择，两者不能同时设置。精密产品可通过 `RTK_PPP_NAV`、`RTK_PPP_SP3`、`RTK_PPP_CLK`、`RTK_PPP_BIA`、`RTK_PPP_IONEX`、`RTK_PPP_VMF_FIRST`、`RTK_PPP_VMF_SECOND`、`RTK_PPP_OROGRAPHY` 和 `RTK_PPP_ATX` 指定；结果路径用 `RTK_PPP_OUTPUT` 指定。输入数据与精密产品未包含在仓库中。

PPP 启动仍使用 `pntpos.c` 获取粗位置。RTCM 模块保留了 PPP 可用的 SSR 路径及其链接依赖。其余 RTK、多厂商接收机协议、网络流、数据下载和格式转换模块不进入此工程。

源码保留原 RTKLIB 作者的版权声明。此工程在本地通过了 x64 Release 编译，以及 RINEX 1200 历元和 Android TXT 20 历元相对精简前版本的数值回归验证。

## Phase 1：A/B 基线与回归

历史参照为 `97a57a9`，本地标签 `legacy/current-robust-97a57a9`。
默认保持 **B / LEGACY**，以复现当前项目算法；A 使用修正后的周跳弧段和连续历史。

```powershell
$env:RTK_PPP_BASELINE = 'A'             # CLEAN_BASELINE
Remove-Item Env:RTK_PPP_LIFECYCLE -ErrorAction SilentlyContinue
# 使用现有产品环境变量，再运行 PPP_only.exe --source txt-fast --no-gui

$env:RTK_PPP_BASELINE = 'B'             # LEGACY_BASELINE，默认生命周期 LEGACY
$env:RTK_PPP_LIFECYCLE = 'LEGACY'       # 保留历史弧段/GF 行为，仅作历史复现
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

先按 [PPP运行准入](docs/PPP_OPERATIONAL_GATE.md) 核对当前PC非组合PPP，再用 `RTK_PPP_BASELINE=C` 显式启用一次验前Huber权重EKF。C沿用A的函数模型、固定Q/R0和正确弧段处理；每条真实GNSS码/相位行使用 `u=v/sqrt(hP^-h^T+R)`，当前历元按固定截止值1.5计算权重。默认仍为B，A/B结果不变；D和信号级eta未启用。实施及TXT/RINEX对照见 [普通抗差报告](docs/PPP_ROBUST_KALMAN_REPORT.md)。

测试命令：`tests/run_robust_tests.ps1`；同输入回放：`tests/run_robust_replay.py`；诊断核对：`tests/run_robust_diag.py`。
