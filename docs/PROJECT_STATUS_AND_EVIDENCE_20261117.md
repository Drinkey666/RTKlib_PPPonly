# 手机实时 PPP 项目现状与证据索引

核对日期为 **2026-11-17**。目标是在安卓手机上用原始 GNSS 观测做严格实时、非组合 PPP，以文件预报产品供给实时解算。安卓端同时支持 Raw 采集、实时解算、文件后处理和地图显示。PC 端负责同内核回放、精度评价和隔离试验。两端当前以 `B_VERIFIED_v2_JOSEPH` 为正式配置。[正式预设](../config/b_verified.json) · [PC 回放入口](../tools/run_ppp_session.py#L15) · [严格预报入口](../tools/forecast_ppp.py) · [安卓代码索引](https://github.com/Drinkey666/Android_GNSS_FTP_APP/blob/9ea3947446ff6fbd24501dbbe51a114e80a9ec6a/docs/PROJECT_VALIDATION_INDEX.md)

## 当前问题与下一步

| 优先级与问题 | 已经验证的范围 | 代码、数据与下一步 |
| --- | --- | --- |
| **P1 · 当前版本真机闭环待验** | 10/25 旧版本真机与同窗 PC Raw 的 1549 历元、64345 条观测一致，Q 和卫星数一致，XYZ 最大分量差 5.819 μm。11/11 vivo 已验证应用内高德底图、设备标点、拖动与回中。当前内核与采集、地图改动组合后的新鲜实时会话仍待验。 | [实时控制器](https://github.com/Drinkey666/Android_GNSS_FTP_APP/blob/9ea3947446ff6fbd24501dbbe51a114e80a9ec6a/app/src/main/java/com/example/ftpget/LivePppController.kt#L82) · [JNI 入口](https://github.com/Drinkey666/Android_GNSS_FTP_APP/blob/9ea3947446ff6fbd24501dbbe51a114e80a9ec6a/app/src/main/cpp/gnss_jni.cpp#L477) · [地图来源与刷新](https://github.com/Drinkey666/Android_GNSS_FTP_APP/blob/9ea3947446ff6fbd24501dbbe51a114e80a9ec6a/app/src/main/java/com/example/ftpget/MainActivity.kt#L458) · [旧真机报告](ANDROID_LIVE_POST_COMPARISON_20261025.md) · [实机输出](../validation/android_live_20261025_v1/live/) · [PC 同窗核验](../validation/android_live_20261025_v1/same_window_input_control.json)。下一步用同一会话同时采集 Raw 和实时解，比较两端输出并验收地图切换。 |
| **P1 · 10/31 双机仍有米级偏差** | B1I、B1C 同时接入并更新 ATX 后，K70／IQ 在末 300 秒的水平 RMS 为 **0.772／0.937 m**，U 均值为 **−0.458／−2.454 m**。历史单项对照中，K70 去 B2a、IQ 去 C7I、K70 模拟 IQ 相位缺失，末段 U 变化约 +0.090 m、+0.00016 m、−0.092 m。两机约 2 m 的垂向差尚未归因。 | [状态预测](../src/ppp.c#L2852) · [观测和残差](../src/ppp.c#L3500) · [信号与弧段诊断](../src/ppp.c#L4145) · [新版回放报告](../validation/b1i_b1c_integration_v1/REPORT.md) · [单项对照](../validation/oct31_reference_diagnosis_v1/REPORT.md) · [逐历元误差](../validation/oct31_reference_diagnosis_v1/paired_device_errors.csv)。按共同历元、卫星、实际信号和连续弧段对齐，沿预测→建行→更新跟踪码相残差在高程、电离层、对流层与模糊度之间的分配。 |
| **P2 · 10/25 水平东偏仍未解释到底** | 已定位偏差进入码方程的路径。共同集合上，原始码与名义模型得到约 +1.992 m 东向分量，实际接受码方程约 +2.418 m。替换 ATX、改用 NRT BIA 的对照未消除偏差，事后 RTS 轨钟的固定参考投影变化约 0.06 m。物理根因仍待定位。 | [码改正](../src/ppp.c#L1156) · [诊断报告](OCT25_EAST_BIAS_SOURCE_REPORT.md) · [同窗回放输出](../validation/android_live_20261025_v1/pc_live_window/) · [10/25 原始数据及产品](../validation/android_live_20261025_v1/inputs/)。后续优先查原始码误差及与接收机状态的联合分配。 |
| **P2 · NRT 轨钟与 RTS BIA 的参考兼容性待核验** | 产品实际有效期已检查。正式 Bias-SINEX 读取路径处理 `Cxx` 码偏差。`Lxx` 相位 OSB 已做独立开关对照，Q 逐历元一致，末 300 秒两机水平 RMS 均变差，当前正式配置仍使用码 OSB。此前取得同日匹配 RTS 轨钟的请求超时。 | [产品预检](../src/ppp_product_check.c#L345) · [BIA 读取及参考声明](../src/preceph.c#L714) · [正式改正](../src/ppp.c#L1156) · [相位候选代码](../validation/phase_osb_trial_v1/build/ppp.c) · [正式参与核查](../validation/oct31_phase_osb_audit_v1/REPORT.md) · [候选报告与 OFF/ON](../validation/phase_osb_trial_v1/REPORT.md) · [配套产品请求记录](../validation/phase_osb_trial_v1/product_reference/download_receipts.json)。取得参考定义明确且时段覆盖的配套产品后，做独立产品对照。 |
| **P3 · 剩余原始观测异常** | 固定钟段观测生成已消除两次 256 ns 码参考台阶。样本中仍有 11 条晚段约 100 ms 发射时标冲突被拒绝。历史 Galileo `7Q` 的 ADR 与距离率积分差异已存在于原始数据，当前实时白名单排除该频点。 | [钟段参考](../src/gnss_clock_reference.h#L41) · [时标拒绝位置](../src/gnss_adapter.c#L303) · [观测转换报告](ANDROID_OBSERVATION_GENERATION_2023_REPORT.md) · [逐项核验证据](../validation/observation_generation_2023_v1/validation_results.json)。先定位异常的原始事件及钟段，保留拒绝原因。 |
| **暂缓 · IQ 的北斗 `5Q`** | `5Q` 识别和正式拒绝原因已核对。10/18 的两份 RINEX 有 `C5Q` 行，`L5Q` 实际为空。10/31 的原偏差产品缺相关 `C5Q` 记录。该候选仍按指示暂停。 | [正式信号策略及拒绝原因](../src/gnss_signal_policy.c#L4) · [历史核查](../validation/iq_b2aq_phase_trial_v1/HISTORY_REVIEW_20261110.md) · [暂停状态](../validation/iq_b2aq_phase_trial_v1/USER_PAUSED.json)。 |

10/31 的参考点评价以 **K70 Pt40／IQ Pt42** 为主，并保留 K70 Pt39、IQ Pt41 两个同机参考点的单独评价。Pt40 为 483.963 m，Pt42 为 483.989 m，采用原评价的 WGS84 椭球高口径。参考点和实际采集时段的逐段对应仍待确认，评价未平均点位。10/25 的参考单独保存。[10/31 四个参考点](../validation/oct31_reference_diagnosis_v1/reference.json) · [10/25 参考点](../validation/android_live_20261025_v1/reference.json)

## 已完成并验证的工作

- **北斗信号身份与新版天线标定。** B1I `2I` 槽 0、B1C `1P` 槽 3 独立，同保留 B2I `7I`、B2a `5P`，B2b `7D/7P/7Z` 明确排除。B1C 的两机完整对照均有实际接受的 `1P` 载波。新版 `igs20_20261110.atx` 补齐本组 PRN 的相应标定。精度结论见上表。[PC 信号策略](../src/gnss_signal_policy.c#L4) · [B2b 排除证据](../validation/b2b_exclusion_v1/REPORT.md) · [ATX 覆盖](../validation/b1i_b1c_integration_v1/B1C_antenna_coverage.json) · [安卓内置 ATX](https://github.com/Drinkey666/Android_GNSS_FTP_APP/blob/9ea3947446ff6fbd24501dbbe51a114e80a9ec6a/app/src/main/assets/gnss_products/igs20_20261110.atx)
- **状态连续性与数值安全。** 正式路径已有 Joseph 协方差更新、PSD 检查、预检和失败时的状态保护。固定钟段转换已同步到 PC 和安卓。既有验证覆盖相关数值回归和逐字段观测核验。[Joseph 报告](B_JOSEPH_INTEGRATION_REPORT.md) · [数值修复](FILTER_COVARIANCE_NUMERICAL_FIX_REPORT.md) · [逐历元 PPP 入口](../PPP_only/ppp_position.c#L255) · [数值实现](../src/rtkcmn.c) · [观测转换验证回执](../validation/observation_generation_2023_v1/delivery_summary.json)
- **采集定时和高德底图。** 默认 10 分钟一档，定时到达时完成 Raw 保存。地图使用设备、实时或后处理坐标，显示时转换为 GCJ‑02，应用内直接加载高德底图。[采集入口](https://github.com/Drinkey666/Android_GNSS_FTP_APP/blob/9ea3947446ff6fbd24501dbbe51a114e80a9ec6a/app/src/main/java/com/example/ftpget/MainActivity.kt#L538) · [地图转换](https://github.com/Drinkey666/Android_GNSS_FTP_APP/blob/9ea3947446ff6fbd24501dbbe51a114e80a9ec6a/app/src/main/java/com/example/ftpget/MapPosition.kt#L28) · [地图界面](https://github.com/Drinkey666/Android_GNSS_FTP_APP/blob/9ea3947446ff6fbd24501dbbe51a114e80a9ec6a/app/src/main/java/com/example/ftpget/ui/MapScreen.kt#L40)

## 数据与文件在哪里

| 数据组 | 文件位置和用途 |
| --- | --- |
| 10/31 两台手机原始采集 | [K70 Raw](../validation/oct31_reference_diagnosis_v1/inputs/raw/RawData_20261031_101334.txt.gz) · [IQ Raw](../validation/oct31_reference_diagnosis_v1/inputs/raw/RawData_20261031_101333.txt.gz) · [10/31 产品目录](../validation/oct31_reference_diagnosis_v1/inputs/products/) · [原参考坐标](../validation/oct31_reference_diagnosis_v1/reference.json) |
| 10/31 当前配置结果 | [K70 结果](../validation/b1i_b1c_integration_v1/k70_with_b1c_new_atx/solution.csv) · [IQ 结果](../validation/b1i_b1c_integration_v1/iq_with_b1c_new_atx/solution.csv) · [样本图](../validation/b1i_b1c_integration_v1/B1I_B1C_COMPARISON.png) · [K70 回执](../validation/b1i_b1c_integration_v1/k70_with_b1c_new_atx/run.json) · [IQ 回执](../validation/b1i_b1c_integration_v1/iq_with_b1c_new_atx/run.json) |
| 10/25 K70 真机采集 | [原始 Raw](../validation/android_live_20261025_v1/inputs/RawData_20261025_133353.txt.gz) · [对齐实时窗口的 Raw](../validation/android_live_20261025_v1/inputs/live_window_raw.txt.gz) · [观测 RINEX](../validation/android_live_20261025_v1/inputs/GEOL00CHN_R_20262980533_00U_01S_MO.rnx.gz) · [产品](../validation/android_live_20261025_v1/inputs/) · [实机输出](../validation/android_live_20261025_v1/live/) · [PC 对照回执](../validation/android_live_20261025_v1/pc_live_window/solution.csv.session.json) · [东偏归因证据](../validation/oct25_east_bias_v1/) |
| 相位 OSB 与剩余异常 | [OSB 候选产物和记录](../validation/phase_osb_trial_v1/) · [观测生成验证](../validation/observation_generation_2023_v1/) · [10/18 和 10/21 的原始采集](../validation/observation_generation_2023_v1/inputs/) · [历史审计索引](../validation/audit_registry/AUDIT_REGISTRY.json) |
| 文件完整性 | [数据清单](../validation/PROJECT_DATA_MANIFEST.json)列出 25 个原始输入压缩文件、压缩和解压后的 SHA‑256，以及回放时各文件的用途。10/25 和 10/31 共同的旧 ATX 和地形文件复用一份。 |

原始采集、坐标参考及回放产品存放在私有 PC 仓库。公开安卓仓库归档应用源码、验收索引和应用内置的 IGS 天线文件。各历史 `run.json` 和 `.session.json` 保留当次的原路径和程序指纹。历史审计索引覆盖更广的本机实验，本分支上传了与本报告对应的证据。

## 用 GitHub 上的数据回放

在 PC 归档分支根目录用 VS2022 编译 `Release|x64`，再按下例准备输入。恢复工具校验文件 SHA‑256 并生成 PC 实际能读取的清单。`oct31_iq_current` 可按同样方式运行。`oct25_live_window_current_core` 使用历史同窗输入和当前内核，原真机闭环结果见历史回执。

```powershell
python tools/restore_project_evidence.py oct31_k70_current validation/local_replay/k70
.\run_ppp.cmd validation/local_replay/k70/manifest.json --output validation/local_replay/k70/solution.csv
```

[解压及校验工具](../tools/restore_project_evidence.py) · [归档回放清单示例](../config/b_verified_replay.example.json) · [正式回放和输出回执](../tools/run_ppp_session.py#L50)

## 当前真机验收怎么做

1. 选 vivo 或 K70，记录安装 APK 的 SHA‑256、内核配置与手机实际加载的产品。确认完整测试时段受产品覆盖。
2. 手机静置，先启 Raw 采集，再启动实时 PPP，保持前台。保留 `.profile.txt`、`.tracking.csv`、`.obs.csv`、`.solution.csv`、`.trace` 和已保存的 Raw。实时 PPP 使用独立停止按钮。
3. PC 用手机实用产品，从同一实际起始事件回放。对齐 GPS 周、周内秒、卫星和实际信号，先比 P/L/D、频槽和 LLI，再查 Q、使用卫星数和 XYZ。若出现差异，定位第一条分叉记录。对启动时间、缺历元和中途停机会话单独记录。
4. 地图依次检查设备定位、有效实时解、停止后的设备定位。实时解质量通过 Q 值记录，Q=6 可作为 PPP 出解的验收点。计算绝对误差时再关联已确认的测点与椭球高。

## 本次归档范围

PC 来源为本地 `codex/ppp-robust-ekf` 的 `0fd98a9` 与相关工作区源码。安卓来源为 `main` 的 `e67c9ed` 与相关工作区源码。两个仓库都用 `codex/project-evidence-20261117` 发布。旧工程 `RTKlib_mix` 仅作为历史入口。归档快照通过 PC Release/x64 构建、Android Debug 构建和 JVM 测试（191 项通过、9 项跳过）。10/31 K70、10/31 IQ 和 10/25 同窗三组已解压并核对 SHA-256并通过回放准备检查。解算统计来自文中链接的历史实测和回放。本轮未新增真机现场采集记录。
