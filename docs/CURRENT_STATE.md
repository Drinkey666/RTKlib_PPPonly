# PPP 项目当前状态

本页与根目录 AGENTS 共同作为新会话入口。2026-11-26 PC 标准 EXE 已完成非组合文件产品 PPP 源码精简，保留 11-18 验后编辑边界修复、既有滤波和观测生成。B1I 2I 与 B1C 1P 同时参与，B2a 保留、B2b 排除、IQ Q 暂停。正式配置沿用 `B_VERIFIED_v2_JOSEPH`。[本次验收及 Android 后续同步清单](../validation/pc_ppp_core_prune_20261126/REPORT.md)

## 当前任务

2026-11-19，Redmi K70 Ultra 与 vivo 同场早、晚两段静止采集，以各自经用户确认的参考点评价。小米两段共 1,204 期，初始产品与 vivo 逐字节相同，晚段在小米自己的第 233、440 回调换 NAV。按此时序在 PC 固定严格码 OSB 关闭，仅将现场武大轨钟 321/13 换成 322/09，小米末窗分别多偏南 0.206、0.125 m，低偏分别加重 0.620、0.448 m；水平 RMS 早段 3.668→3.828 m，晚段均约 3.057 m。两路 Q、用星数及接受的卫星载波频槽逐期相同。小米 ARM64 已核实 A 复现现场，B 运行中 ADB 断开，B 的完整数值来自 PC 回放。晚段高程变化在 vivo 上方向相反。[小米双模式及两机同秒对照](../validation/xiaomi_today_paired_20261119/REPORT.md)

2026-11-19 21:17 北京时间复查，武大 MGEX 原 FTP 与 IGN 周目录均无 323 日起算的 WUM0MGXNRT SP3／30 秒 CLK，最新完整配对为 322/11。两段采集开始前有证据可得的最新共同配对为 322/09。323/00 若随后取得，仅可用于这两段的事后产品对照。[323 日配对目录核验](../validation/vivo_wum_doy323_20261119/REPORT.md)

2026-11-19，vivo ARM64 以严格码 OSB 关闭、原晚段两次 NAV 切换重放两段静止 Raw，分别使用现场 11/17 13 时与同源 11/18 09 时完整 SP3＋CLK。新配对在两段开始前已具备武大 MGEX 原 FTP 与 IGN 双站归档证据，采集后 vivo 蜂窝网从武大直接下载并校验。轨道预测时长缩短 20 小时，末 300 回调的共同 Q6 中，早、晚段分别多偏南 0.321、0.303 m，高程低偏分别加重 0.828 m、减轻 0.510 m，水平 RMS 分别从 1.829→2.137、2.355→2.581 m。Q、用星数和载波接受集合均逐历元相同。结果为固定现场 RTS 偏差后整对轨钟的净效应。[真机配对轨钟对照](../validation/vivo_paired_orbclk_20261119/REPORT.md) · [采集时可得性](../validation/vivo_paired_orbclk_20261119/availability/REPORT.md)

2026-11-19 20:43，vivo 已覆盖安装含严格码 OSB 手动开关的 Debug APK，SHA-256 为 `2c07b698e45f1b69f43bdc25fe8b436af5c8845ffdebf0108899a771998d5355`。「定位」页默认关闭。GA 广播星历和 VMF3 可在实时解算中换入。vivo ARM64 按原现场产品切换时序重放两段静止 Raw，关闭时 1,206 期复现旧包。开启后末窗水平 RMS 早段 1.829→1.351 m、晚段 2.355→2.341 m，平均高程差分别 −3.672→−2.432、−5.552→−2.804 m。Q6 逐期相同，仅少用 C10/2I 载波 139、409 条。10/18 K70 早段 RINEX 复核则从 0.765 退至 0.971 m，连续 60 秒水平 ≤1 m 的窗口起点推迟约 91 秒。按设备与产品保留为可选模式。[移植、真机验收及实装](../validation/android_strict_osb_arm64_20261119/REPORT.md)

2026-11-19 晚 vivo 在用户确认的同一静止参考点采集两段，532、674 期全部有解。末 300 个回调中的 Q6 水平 RMS 为 1.83、2.35 m，平均高程差 −3.67、−5.55 m。固定初始 NAV 的正式 PC 对照中，仅打开严格码 OSB，末窗平均高程由 −3.67→−2.43、−5.45→−2.21 m。两段首期均涉及 C02/7I、C10/2I，后者在严格模式下同时失去可初始化的载波弧。晚段接续早段滤波将默认低偏由 −5.45 减至 −4.00 m。四次全机 ADR 失效均只产生一秒 Q5，数米低偏在广播星历切换前已经形成。同一静止点相邻会话的改进未推广为默认。见[现场误差及受控归因](../validation/vivo_ten_min_accuracy_20261119/REPORT.md)与[逐秒曲线](../validation/vivo_ten_min_accuracy_20261119/field_errors.png)。

2026-11-19 18:15 北京时间复核，武大官网对轨钟第 322、323 天均返回零条，321 日 13 时 GPST 为可取的最新配对，手机文件实际共同覆盖至 11-19 20:54:42 北京时间。vivo 第一次 RTS FTP 三次中断后仍完成轨钟下载，随后 Android 于 18:10:50 以 single-cleaner 强停进程。第二次 FTP 在 18:12:57 第三次尝试成功，取得当天 RTS BIA，但目标 10:13:15 GPST 时有效码 OSB 为 861 条，有效相位 OSB 为零。见[本次手机诊断](../validation/android_whu_download_diagnosis_20261119/REPORT.md)。

2026-11-19，vivo 已同签名覆盖安装支持运行中 NAV、VMF3 切换与现场证据留存的 Debug APK，实装 SHA-256 为 `974f4c1b5a6d78a1d523cb136d3efde711f64742ded7e30a4b638e22bbbad9a8`。实时入口按当前观测卫星检查未来 600 秒的广播星历时间覆盖，触发手机自主联网、按历元换入。vivo 从已有历史 Raw 回放 10/25 和 1/4 共 239 期，239 次解算均为 Q6，三次 NAV 和一次 VMF3 切换保留滤波状态。1/4 采用受控 CODE BIA，验证实际 UTC 06:00 格网切换。现场由用户采集。「定位 → 启动实时 PPP」会一起留存 Raw、逐回调去向和排队、产品版本字节及位置解。收回整个 `GNSS_Live` 目录即可逐期分析。现场射频采样及定位精度待新数据评价。[实装与验收](../validation/android_live_nav_vmf_rollover_20261119/REPORT.md) · [采集与回传](../validation/android_live_nav_vmf_rollover_20261119/FIELD_COLLECTION.md)

2026-11-19 含 GA 下载的 Android 正式工程已合入第 17 次最终试算，首回调缺 FullBiasNanos 时保持会话等待；新版 Debug 已同签名覆盖安装 vivo V2507A，实装 SHA-256 为 5458c68c51e14703b6453f11a4cf733863dc5714ed4b0420c1e27ca2a4280c89。实机实际新旧 APK 的 ARM64 实时库处理 10/21 K70 全 1,341 期，原 11 个 Q0 均在原 GPST 恢复为 Q6，失败 11→0，Q6 1327→1338；新版与 PC 全程 Q、使用卫星数及转换观测一致。实机受控缺钟两期后有效的第三期成功初始化，ARM64 215 项核心回归通过。11 个恢复历元水平误差 1.487–1.662 m，首个恢复后共同 Q6 水平 RMS 1.4217→1.4363 m。见 [合入、回放与安装报告](../validation/android_ga_edit17_fullbias_20261119/REPORT.md)。

2026-11-19 完成 Android 实时非差非组合 PPP 全链审查。10/21 K70、10/31 K70/IQ 的三份 Raw 各跑全天混合 NAV、单站小时 NAV、按缺失卫星号补星三组，标准 PC 共 9 次、26,283 条输出。各组 Q6 集相同；10/31 K70 单站→补星全程水平 RMS 1.569→1.148 m、水平持续收敛窗口 681→397 s，IQ 全程水平 0.871→0.726 m 但末 300 期 U 均值 −2.571→−2.965 m。生产算法及手机安装版本沿用原状。见 [审查及验收顺序](../validation/uduc_position_audit_20261119/REPORT.md) 与 [收敛曲线](../validation/uduc_position_audit_20261119/convergence.png)。

2026-11-19 同日 vivo 续验已通过 GA HTTPS 小时 NAV 正常产品下载入口。含 GA 接入的候选 APK SHA‑256 `f1453de3e01cc5a2487353585788acdb06f16d39d9ee37e7bdafa43b421a729c` 已覆盖安装并与手机 base.apk 哈希核对。北京时间 17:06:41 发起，BKG DNS 失败后在约 30 秒内下载并选用当天 `GAMG00KOR_R_20263230700_01H_MN.rnx.gz`，App JNI 确认 GPS 13、Galileo 12、北斗 24 颗健康可选。独立 ARM64 同手机对照确认旧 ESA、CAS 文件当期均为 0/0/0，GA 四站小时文件为 15/13/21。同一会话武大 RTS BIA FTP 成功刷新，武大 HTTP SP3/CLK 按当前目标配对校验通过。本轮验证已有候选 APK 与手机来源，尚无长时间可用率或静态 PPP 精度结论。见 [vivo 续验](../validation/android_nav_vivo_sources_20261119/REPORT.md) 与 [回执](../validation/android_nav_vivo_sources_20261119/summary.json)。

2026-11-19 Android 产品下载新版已安装到 vivo V2507A 并核对 APK SHA‑256，12 个包内原生库与安装前逐字节一致。NAV 改为每个 UTC 日期依次 BKG HTTPS、原 BKG FTP、ESA GSSC，确认 DNS 失败后跳过该主机，HTTPS 目录失败时可试同日 WRD 直链。设备两个 BKG 主机均 DNS 失败，ESA 11-19、11-18 FTP 550，11-17 落盘但在目标 GPST 11-19 04:03:12.986 对 GPS、Galileo、北斗均无可选广播星历。BKG 已公告 10 月停止 FTP，保留原入口符合本轮指定顺序，当前实时 NAV 来源不稳定。武大官网精密目录索引部分 BIA，但无 `WUM0MGXRTS`，直接样本 URL 返回 404 或 200 空响应。RTS 保留 FTP、增加 Bias-SINEX 及码/相位实际覆盖核验。独立手机与 PC 均下载同名 BIA 并核对哈希，手机按钮会话 BIA 仍遇 FTP 中断。轨钟用独立的 11-19 当前目标选取，官网最新 `WUM0MGXNRT_20263211300` 起算于 11-17，SP3/CLK 实际覆盖 11-19 目标。HTTP 已沿用现有实现处理官网附加的 HTML，早期实测 HTTPS 证书错误的证据保留。新版 JVM 198 通过、9 跳过，普通入口已取得四类产品各自结果。详见 [本轮报告](../validation/android_product_download_20261119/REPORT.md)、[汇总和身份](../validation/android_product_download_20261119/summary.json) 与 [前次官网链路验证](../validation/whu_nrt_web_vivo_20261119/verification.json)。

2026-11-18 Android 隔离候选已交付。基于审计快照移植 PC 编辑边界的相同改动，仅改候选 `ppp.c` 和两个快照清单的对应条目。Debug APK 四 ABI 的 8 个库均追溯到候选源码。Android 16 x86_64 模拟器独立验证器完成 10/21 的 358 期新旧对照，原 11 个 Q0 在 PC 相同 GPST 恢复为 Q6，所有转换观测字段相同。边界正负例实际均剔除 16 条、试算 17 次，后验提交 1/0，负例返回 `EDIT_LIMIT=-21`。10/18 原入口两侧各 660 期逐值一致。APK 的两个 x86_64 ELF 已验证加载及 JNI 符号。ARM64、App 实际 JNI 通路及现场仍待实机，生产 Android 工作区保留原版本。见 [Android 候选报告](../validation/android_ppp_edit_boundary_candidate_v1/REPORT.md)。

2026-11-18 仅将已验收的第 16 条剔除后最终验后重算补丁合入 PC `src/ppp.c`。正式 Release/x64 构建通过同批源码和对象的 215 项核心回归。新 EXE 按默认 A 回放 25 组，22712 条输出的 GPST、Q、使用卫星数和坐标逐值匹配候选。10/21 K70 RTS BIA 的 Raw/RINEX 分别有 11/12 期实际剔除 16 条、试算 17 次、验后成功且只提交一次。对旧标准共恢复 23 个 Q6，PPP 失败 23→0，23 个未触发组合逐历元一致。触发后共同 Q6 水平 RMS 为 Raw 1.4217→1.4363 m、RINEX 1.5992→1.6202 m。旧版 EXE 和原 A 回执已归档。见 [正式发布验收](../validation/ppp_postfit_edit_release_v1/REPORT.md) 与 [候选正负边界](../validation/ppp_postfit_edit_boundary_v1/boundary_checks.json)。

2026-11-18 Android 构建核对完成。两套 JNI 目标实编译 `ppp_live/rtklib/ppp.c`，本地 Debug、未签名 Release 和独立重建 Debug 的 24 个解算 ELF 均为旧 16 次试算边界，尚未包含 PC 第 17 次最终试算。Android 快照自校验 33/33 通过，与当前 PC 的差异是 `ppp.c`、`gnss_adapter.c` 和 `preceph.c`。ADB 无连接设备，当前手机安装身份和会话实际配置待查。正式 App 无历史 RAW 注入入口，旧独立验证器定制 10/18 产品及 660 期。10/21 的 358 期短回放对照已锁定，边界行为仍为 PC 已验证。见 [APK/ABI 核对](../validation/android_pc_edit_boundary_audit_v1/REPORT.md) 与 [现场流程](../validation/android_pc_edit_boundary_audit_v1/FIELD_PROTOCOL.md)。

2026-11-17 在 `validation/cross_dataset_osb_bdsvar_v1/` 完成跨样本 A/B/C 回放，排除 10/25、10/31。当时的标准程序 SHA‑256 为 `F8A135FE7FAAE861909F438403DDF6E6E1EB5466383F48B7AE135BE51563F4EC`。27 个归档输入组合运行三组，25 个完成（75 次成功解算），其中 22 个有参考的真实手机组合对应 9 个采集会话。2 个旧 ATX 组合被同一产品预检拒绝，配套历史 ATX 组合另有成功回执。10/21 vivo 的两份历史输入缺本地文件。D 为可选项，该轮未运行。

`-OSBSTRICT=1` 的 B 对 A 在 16/22 个有参考组合逐值相同，另外 6 个由实际缺失码偏差回退保护触发了变化。例如 10/18 IQ 早段 RTS BIA 末 300 共同 Q6 水平 RMS 1.242→0.300 m，K70 早段同组合 0.765→0.971 m。该保护有明确产品适用条件，保留为显式开关。`-BDSCODEVAR=100` 的 C 对 B 有 12 组末段水平改善、10 组变差，K70 早段 RTS BIA 0.971→2.988 m。IQ 早段 Raw 在低 GE 接受且北斗相位较强的 232 个共同 Q6 历元中由 0.617 增至 1.526 m。可用性与精度分开验收，10/21 K70 RTS BIA 两种入口的 C 有更多 Q6，而 RINEX 末段 U 偏差增大。100 倍方差保持候选。10/18 正常高组只评价绝对水平，另有输出椭球高漂移。未取得真实运动轨迹真值。

A 的可读历史对照有 9/13 组逐值一致。10/18 K70 晚段 Raw Q6 656→653，10/21 K70 Raw RTS BIA Q6 1338→1327，后者有 11 次 `PPP_FAILURE`，不能宣布正式默认对历史所有入口无回归。3/17 K80 NRT 的 `sat24 F3` 同历元 OUTAGE/REINIT 1162→0，坐标逐值一致，其他卫星的部分配对事件仍在。证据见 [跨样本报告](../validation/cross_dataset_osb_bdsvar_v1/REPORT.md) 与 [汇总](../validation/cross_dataset_osb_bdsvar_v1/summary.json)。

10/21 K70 Raw RTS BIA 的 1341 期历史与 2026-11-17 标准 A 全部按 GPST 配对，输入产品和生效配置一致。首期 02:22:59.001 的共同观测字段一致，A 新准入 9 条 `C/1P`，首个 PPP 坐标已相差 0.242549 m。02:28:16.002 起恰好 11 个 Q6→Q0，逐次对应 `EDIT_LIMIT=-21`。每期的历史 15 条验后拒绝均被 A 重现，A 唯一额外剔除为有有效码 OSB 的 `C24/1P`，第 16 条剔除后触及试算上限。归因轮独立试验确定多一次重算可恢复 11 个 Q6，C24 大残差的物理来源待证。见 [定向报告](../validation/oct21_k70_raw_rtsbia_first_divergence_v1/REPORT.md) 与 [逐历元证据](../validation/oct21_k70_raw_rtsbia_first_divergence_v1/epoch_diffs.jsonl)。

用户最新明确B1I与B1C都要参与。正式白名单已同时允许2I槽0、1P槽3，5P保留；各自OSB/波长/N/RCB独立，7D/P/Z在准入及共同PPP内核继续排除。两机各120期移除1P控制复现基线；加入1P与仅更换ATX各两机3710期，共四次完整回放无PPP_FAILURE、Q逐期不变。K70/IQ实际接受C1P载波23955/19898行，既有其他信号输入逐字段不变；IQ的Q仍被原策略排除，本轮回放仅验证B1C未恢复Q候选。370项原生全过，Android JVM196项187通过9跳过0失败，四ABI构建通过未安装。原ATX缺C06/07/11/12的C01校准，新版已验证并用版本文件igs20_20261110.atx交付，PC默认/Android内置与实时后处理优先选它，旧文件不覆盖。末300s新配置水平RMS K70/IQ 0.772/0.937m、U均值−0.458/−2.454m，未获得整体精度改善；按用户要求保留B1C，不调参或擅自撤准入。证据validation/b1i_b1c_integration_v1/REPORT.md及summary.json。

用户已授权按规范接入相位OSB并检验，要求不要过度防御。已完成独立候选，见validation/phase_osb_trial_v1/REPORT.md、summary.json、PHASE_OSB_OFF_ON.png和build/trial.exe。仅私有ppp.c新增L类产品加载、corr_meas统一改正及模糊度参考转换，无ABI变化；生产源码/32个旧对象/正式EXE未改。215项既有回归+32项新增通过；两机OFF前120期及完整3710期逐字段复现缓存，ON各3710期，原始adapter观测逐字节相同、Q逐期不变、无PPP_FAILURE。末300s K70/IQ U均值分别−0.490→−0.371m、−2.431→−2.398m，但水平RMS分别0.718→0.784m、0.872→0.911m，IQ全程三维RMS3.234→3.300m。没有消除米级偏差或获得整体改善，候选未晋升正式、Android未移植。

此前相位OSB参与核查仍有效，见validation/oct31_phase_osb_audit_v1/：原BIA有867条码记录和15007条相位记录，正式读取器只识别C记录；删除L副本的两机30期与基线完全一致。新ON行为只在上述候选EXE，不能把源码主路径或旧正式程序说成已默认使用相位OSB。

项目记忆机制及Android实时GNSS→JNI→RTKLIB只读Word教材已交付。最新任务为按用户四点重新解算并对比查找问题，证据在validation/oct31_reference_diagnosis_v1/REPORT.md、summary.json及ENU_COMPARISON.png。两机各3710期新回放除耗时外精确复现缓存；另外完成K70去B2a、IQ去C7I和K70叠加IQ共同信号缺相位模式三次完整回放。三组关闭动作120期控制逐字段一致。四点原件在E:/RTKLIB_Data/10.31/reference_points_20261107.json，每份解分别按本机两个点评价；主图暂选Pt40/Pt42，未取平均。具体点号与时段对应仍未获用户确认，沿用此前WGS84椭球高定义。仍未找到米级偏差的唯一物理根因或正式修复。长期目标仍为多机型严格实时、非组合、文件预报产品PPP及独立验证的抗差/自适应改进。

## 工程身份和Git快照

|对象|核验结果|
|---|---|
|活动PC根目录|E:/GNSS/PPP_only|
|PC 分支|codex/ppp-robust-ekf。当前提交以本机 `git rev-parse HEAD` 为准。精简开工基线为 0fd98a9e21f7aa615194a02f6e143d64c2c00335。|
|精简前提交|0fd98a9，2026-10-09，卫星钟差回退方差和精度回归；前有e2de9ae普通Huber、93de551 Phase2.5、4715448 Phase2、ac99aba Phase1|
|历史Joseph提交|e2070cd对象仍在本地，但不是当前HEAD祖先。是否有修复要查工作区，不能只看HEAD|
|PC 工作区范围|2026-11-26 精简前已有 24 个受跟踪文件修改和 946 条未跟踪记录。正式源文件、测试及配置与本地回放产品、验证数据和历史研究分开维护。[开工状态](../validation/pc_ppp_core_prune_20261126/before_git-status.txt) · [本轮改动](../validation/pc_ppp_core_prune_20261126/change_summary.json)|
|Android独立仓库|E:/android/test/FTPGet，main / e67c9ed266bc6c9a725ff4130ec65775b63424f8，2026-11-04 Android UI及PPP实现更新|
|Android工作区|保留 B1C 准入与版本 ATX 等未提交成果。2026-11-18 本地 APK 及隔离重建已核对，均未包含 PC 编辑边界修复。当前已安装版本待实机只读核查|
|本聊天原cwd|E:/GNSS/rtklib_only/rtklib_only，属于旧工程目录；本轮全部PC工作在活动根目录|

以下保留项目记忆建立时的已跟踪修改记录，用于追溯精简前来源。

```text
PPP_only/PPP_only.vcxproj             PPP_only/PPP_only.vcxproj.filters
PPP_only/ppp_position.c               README.md
docs/PPP_ACCURACY_DIAGNOSIS.md
src/gnss_adapter.c                    src/gnss_adapter.h
src/gnss_raw.h                        src/gnss_replay.c
src/gnss_replay.h                     src/ionex.c
src/pc_file_picker.c                  src/pntpos.c
src/postpos.c                        src/ppp.c
src/preceph.c                        src/rinex.c
src/rnx2rtkp.c                       src/rtkcmn.c
src/rtklib.h                         src/smartphone_ppp_config.c
src/smartphone_ppp_config.h           tests/phase1_regression.c
```

新增源码、tests/tools、config、AGENTS、HANDOFF及Word教材等大量成果未跟踪。只备份上述23文件或clone远程不足以恢复项目。下一次重新执行git status、git log，并读取实际任务相关源文件。

## 模块与正式行为

- PC输入入口为src/rnx2rtkp.c；TXT回放为src/gnss_replay.c；RINEX为src/postpos.c和src/rinex.c；原始量转换为src/gnss_adapter.c、src/gnss_clock_reference.h、src/gnss_signal_policy.c。
- 共同主链为PPP_only/ppp_position.c::rtkpos → src/ppp.c::pppos → 预检/状态预测/建行 → src/rtkcmn.c更新 → 验后和原子提交。
- Android为LivePppController.kt → LivePppNative.kt → app/src/main/cpp/gnss_jni.cpp → app/src/main/cpp/ppp_live/rtklib/。旁边旧cpp/rtklib不能据名字当作实时来源，实际由CMake确认。
- JNI的g_engine长期保存rtk_t/nav_t/adapter。每事件建obsd_t[]，worker串行，原生锁保护更新和释放。
- 正式B_VERIFIED_v2_JOSEPH以config/b_verified.json、tools/ppp_preset.py、Android android_b_verified.h为准。配置为B权重+修正生命周期+PPP_COMMON+LEGACY估计器+Joseph/PSD，NFREQ4、GEC、GLO关、GAL E5b关、恢复QC默认关。仅BASELINE=B是旧B。
- C普通边际Huber已实现。条件/联合Huber、PHYSICAL/IEKF、恢复码QC、TDCP、频差/高阶QC及自适应候选均不因存在文件就成为正式默认，当前正式eta=1。
- 手机文件产品路线使用NRT SP3/CLK、RTS BIA，SSR关闭。时效检查通过与参考兼容性认证是不同验收内容。
- 正式文件BIA实现仍只读取/施加码OSB；相位OSB只在validation/phase_osb_trial_v1独立候选通过RTK_PPP_PHASE_OSB=ON启用。postpos内SSR pbias改正是另一条路径，TXT没有调用。不要混用候选/正式EXE或据BIA文件名推断已施加。
- 相位OSB候选按精确PRN/实际信号、GPST半开有效区间查询，ns转米，N初始化和残差均经同一corr_meas扣除。无记录/过期明确无有效改正，不外推，保留原始浮点载波；仅在有改正/无改正之间转换已存N均值，P不变。普通300s记录更新不自动重启/平移N，不新增门限、等待或全星/整历元拒绝。该候选是独立进程PC验证，未宣称Android多会话生命周期支持。

## 构建与测试方法

PC为VS2022/v143，PPP_only.sln的Release/x64。仅当业务任务需要时构建。

```powershell
Set-Location E:/GNSS/PPP_only
& 'E:/Program Files/Microsoft Visual Studio/2022/Professional/MSBuild/Current/Bin/MSBuild.exe' PPP_only.sln /t:Build /p:Configuration=Release /p:Platform=x64 /verbosity:minimal
```

- 标准EXE为x64/Release/PPP_only.exe，对象为build/PPP_only/x64/Release/。tests/run_phase1_tests.ps1、run_phase2_tests.ps1、run_reliability_tests.ps1、run_product_check_tests.ps1、run_robust_tests.ps1等按修改范围选择，先核对对象新鲜度与ABI。
- 固定钟段独立构建入口为 validation/observation_generation_2023_v1/build_pc.cmd。当前标准 Release 的统一回归命令为 `python -B tests/run_observation_generation_core_tests.py --objects build/PPP_only/x64/Release --extended`，覆盖 215 项核心、51 项观测生成和四套专项。可加 `--antex <ATX路径>` 验版本天线校准。省略 `--objects` 时仍链接原固定钟段验证的历史对象。
- Android工作目录E:/android/test/FTPGet，JAVA_HOME用E:/Program Files/Android/Android Studio/jbr；执行 ./gradlew.bat :app:testDebugUnitTest :app:assembleDebug --offline --console=plain。设备安装、仪器测试和现场采集分别记验收。
- 归档回放run_ppp.cmd <清单.json> --output <新结果路径>，模板config/b_verified_replay.example.json；预报发布/接收可用性用run_forecast_ppp.cmd。run_b_verified.cmd设置正式预设，实际调用标准EXE。

### 程序文件与源码必须区分

|文件|本轮SHA256及身份|
|---|---|
|x64/Release/PPP_only.exe|`0f7e4bdbfc81097681ddf4bde58f8b3301daa63fe1d5d22eabe52b3ef45b7475`，2026-11-26 PC 标准程序，精简原 RTKLIB 死模块。见 [发布回执](../validation/pc_ppp_core_prune_20261126/publication_receipt.json)|
|validation/ppp_postfit_edit_release_v1/staged/bin/PPP_only.exe|`5fb27447bc86ebca3f8dbafb10748194f5c41978ef51fa74c47b9670a0be2d9c`，2026-11-18 PC 标准程序归档，纳入验后编辑边界修复。见 [发布回执](../validation/ppp_postfit_edit_release_v1/publication_receipt.json)|
|validation/ppp_postfit_edit_release_v1/previous_standard/PPP_only.exe|`f8a135fe7faae861909f438403ddf6e6e1eb5466383f48b7ae135be51563f4ec`，2026-11-17 标准 EXE，含 `-OSBSTRICT=1`、`-BDSIONINT=`、`RTK_PPP_CLOCK_REF` 显式开关与 P3 修复。见 [旧版回执](../validation/ppp_postfit_edit_release_v1/previous_standard/receipt.json)|
|validation/observation_generation_2023_v1/pc_build/PPP_only.exe|b21c0420e7ebcf85251ede0dd4b06c20a05530cf4fe8560dd027f5d957826944，固定钟段修复独立EXE，后续10/31及跨机型实验复用|

程序身份按上表与实际 SHA 核对。此前 10/31 诊断和相位候选阶段仅新增独立程序。2026-11-10 B1I+B1C 接入前的 PC 标准备份在 validation/b1i_b1c_integration_v1/before/standard_PPP_only.exe。旧固定钟段程序及私有对照仍保留原位。Android 的 33 份快照源与当时清单一致，其中 30 份与 2026-11-18 PC 相同。本地四 ABI 包和独立重建身份见 [Android 审计](../validation/android_pc_edit_boundary_audit_v1/apk_identity.json)。

## 已完成与验证范围

|事项|有效结论与证据|
|---|---|
|2026-11-26 PC PPP 源码精简|删除 8 个上游模块及失效分支，源码净减 16,179 行、954,955 字节。PPP 启动仍使用迁移到 `pntpos.c` 的同一 MOPS 对流层模型。正式 Release 同批对象 388/388 项通过。10/31 K70 和 10/25 K70 的默认 TXT 共 5,270 期，除耗时外全部字段精确相同。10/21 K70 RTS BIA 的 RINEX 1,341 期 POS、事件与状态文件逐字节一致。[验收报告](../validation/pc_ppp_core_prune_20261126/REPORT.md)|
|卫星/频率身份与B1C同时准入|2026-11-10按IGS日期元数据纠正PRN代际推断，修复B1C独立槽并正式允许2I/1P同时进入，B2b排除。370原生/JVM187通过；两机四次完整接入/天线对照，标准EXE和版本ATX已交付，APK未安装。validation/b1i_b1c_integration_v1/REPORT.md|
|数值与状态安全|NaN/Inf保护、弧段pending、Joseph/PSD原子提交已存在。PHYSICAL原180次无效后验降到0，轨迹只变微米，不能称米级精度已修好。docs/FILTER_COVARIANCE_NUMERICAL_FIX_REPORT.md、docs/B_JOSEPH_INTEGRATION_REPORT.md|
|固定钟段观测生成|同钟段首FullBias/Bias固定，整数纳秒换算，ADR事件只切信号弧。已改PC及Android观测生成源码。docs/ANDROID_OBSERVATION_GENERATION_2023_REPORT.md|
|该修复的历史回执|validation/observation_generation_2023_v1/delivery_summary.json、core_test_results.json、native_test_results.txt记录既有215项和新增51项全过，JVM193项中186通过/7跳过/0失败，PC及四ABI Debug构建成功；244046共同Native行、747871 RINEX数值核验。本轮未重测|
|已修时标台阶|两次256ns约76.8m码参考台阶消除，Raw原字段保留。旧50μs和100ms分星座对齐候选未晋升默认。上项报告及validation_results.json|
|实时输入链|当前回调/JNI/转换/状态传递已核对；历史10/25同窗手机实时与PC Raw在记录精度内输入一致、坐标微米一致，不能外推到所有版本和设备。docs/ANDROID_LIVE_POST_COMPARISON_20261025.md|
|TDCP四组验证|固定清单回放多144次重启无持续收益，未部署闭环在线TDCP。docs/TDCP_CROSS_DEVICE_REPORT.md、validation/tdcp_cross_device_v1/provenance.json|
|频差/高阶码QC|分别多标坏275/30行，9480个PPP解历元状态未变，无通用收敛收益，默认未改。docs/CODE_QC_CROSS_DEVICE_REPORT.md、validation/code_qc_cross_device_v1/provenance.json|
|10/31四点评价与新对照|两机3710期重新回放精确复现缓存；Pt40/Pt42末300s U均值−0.490/−2.431m。同机另一个点分别仅6.227/5mm距离。K70去B2a、IQ去C7I、K70叠加IQ缺相位三项对照末300s ΔU分别+0.090m/+0.000163m/−0.092m，Q未改变；未单独复现两机约1.94m差异。validation/oct31_reference_diagnosis_v1/REPORT.md|
|10/31相位OSB参与核查|2026-11-08源代码及实际EXE确认TXT文件路径只用码OSB；原BIA有15007条L记录但被读取器跳过。删除L记录副本的K70/IQ各30期与原BIA基线前缀字段精确一致，未进行启用相位OSB的精度实验。validation/oct31_phase_osb_audit_v1/REPORT.md|
|相位OSB候选接入与对照|2026-11-08新增独立候选，215+32项实测通过、两机OFF完整复现/ON完整对照。有效相位OSB输入行K70 135160/IQ 107027；1165条原生记录事件经独立Decimal时间解析逐项核验，最大bias误差4.78e−12m。正常产品更新均未平移N。末段高程小幅变化、水平与部分收敛退化，未满足整体收益；无默认/Android移植。validation/phase_osb_trial_v1/REPORT.md|
|最近只读教材|docs/ANDROID_GNSS_TO_RTKLIB_PPP_DATAFLOW.docx为16页/25段源码/G03实测例；docs/GNSS_PPP_DATA_AND_OUTLIER_TUTORIAL.docx为21页/38段源码。另有零基础粗差Word。教材制作未改算法|
|2026-11-17显式开关与问题归因|在`src/ppp.c`、`src/preceph.c`、`src/gnss_adapter.c`、`src/gnss_replay.c`保持正式默认不变并完成三项P3修复（单星异步冲突不丢整历元、`udbias_ppp_ex`跳过已排/缺历/低仰角星消除`sat=135 F3` 3678次虚假`OUTAGE`/`$ARC_REINITIALIZED`、`BDS_C1P`标签），新增显式开关`-OSBSTRICT=1`、`-BDSIONINT=`、`RTK_PPP_CLOCK_REF`。以新构建对象实测既有215+51+`verified_profile`(21)+`b1c`(21)+`b2b`(23)+新增6项全部通过。10/31 IQ~2 m偏低定位为IQ BDS `C2I`/`C1P` 仰角码偏差与缺失OSB（`C01..04,09,10,12`）在1 Hz `-IONCONSINT=1` 夹紧下压入`(U,ZTD)`；`-BDSCODEVAR=100 -OSBSTRICT=1`使末300 s K70/IQ分别达`0.584/0.747 m`（U `+0.567/−0.611 m`），且10/25 U从`+2.313`降至`+0.264 m`（而`-IONCONSINT=300`使10/25恶化至`4.401 m`）。`RTK_PPP_CLOCK_REF=WUM_MODERN`使K70末300 s达`0.553 m`（U `−0.022 m`），但在旧`igs20.atx`（缺E29等校验）会因`SAT_APC_INVALID`剔星。|
|2026-11-18 验后编辑边界|PC 正式发布。实际剔除上限 16 条，最后一次试算通过原判据才提交，仍超限保持 `EDIT_LIMIT` 且零提交。B1C、OSB 和定权保持原实现。正式 215 项及 25 组逐历元验收见 [发布报告](../validation/ppp_postfit_edit_release_v1/REPORT.md)。|

## 当前问题与适用边界

- 【已完成/用户策略】B1I与B1C独立槽及正式同时准入已完成，不再列为待启用。B2b明确排除，不再安排其接入。旧ATX缺少2026 PRN/C01校准的已知项已通过新版版本文件交付修正，旧文件保留作历史复现；新版日期/身份覆盖不是NRT轨钟+RTS BIA完整参考兼容认证。IQ Q问题暂停，不自动恢复。
- 【IQ Q历史已核实】10/7提交已存在5Q整体拒绝规则；10/18两份IQ RINEX实际C5Q为4406/4229条、L5Q均空，不能把头定义当使用或有效载波证据。10/31正式TXT明确8颗5Q无OSB且被策略排除；不是本次B1C引入。可先保留Q身份接回浮点载波，码待确认；旧候选及215+51+25检查/回放保留，但基于旧B1C/ATX前基线且用户仍暂停。见validation/iq_b2aq_phase_trial_v1/HISTORY_REVIEW_20261110.md。
- 【未解决】多段手机米级偏差与跨时段/设备收敛差异，仍无唯一通用根因或通用实时消除方法。不同样本的现象不能并成一个已证实原因。
- 【开发样本和外样本的边界】10/31 IQ 末段 U 偏低的归因记录指向 BDS 码偏差和缺失 OSB 在 `-IONCONSINT=1` 下耦合入 `(U,ZTD)`。10/25 和 10/31 的垂向改善属于开发样本。跨样本验证已找到 100 倍方差在少星、北斗相位较强及重捕窗口的明确退化反例，保留显式候选。`-OSBSTRICT=1` 针对缺失码偏差回退的产品一致性风险，6 个受影响组合有正有负的精度变化，不以精度改善为默认启用依据。10/25 约 +2.2..+2.5 m 东偏在纯 `G`、纯 `E` 及 `-DOPPSM=0` 下仍存在，原始伪距空间模式有方向相关差异，具体环境、接收机和参考点因素仍待区分。
- 【输入剩余证据】`K70_late` 11条`CODE_TIME_OUT_OF_RANGE`均集中于`time_nanos=10012000000`单历元`raw_full_bias` `-100 ms`瞬跳（下历元恢复`diff_ns=0`），保留固定钟段仅拒码留相/多普勒有效；Galileo 7Q仍排除。
- 【联合状态模型】部分历史PHYSICAL/vivo负湿或负总延迟需先核实状态定义；电离层时间先验与联合分配有特定因果证据，未获通用默认修改依据。docs/EXTERNAL_PHASE_STATE_CAUSAL_REPORT.md、docs/IONO_OBSERVABLE_RATE_TRIAL_REPORT.md。
- 【产品风险】NRT轨钟+RTS BIA的完整参考兼容性未认证，天线PCO/PCV缺项和参考声明告警保留，过期仍必须失败。
- 【相位OSB候选已验证】当前固定NRT轨钟+RTS BIA组合下，小幅高程变化伴随水平/部分收敛退化，未消除IQ持续偏低。不能再把“先接入相位OSB看看”列为未执行的新建议。原NRT PANDA-CLKDEN与RTS PRIDE BIA的完整参考兼容仍未认证；按PRIDE官方路径尝试取同日匹配RTS轨钟均超时，不能说产品不存在或用结果认证兼容。
- 【现场验证】vivo 已安装含 GA 下载、第 17 次最终试算与首期缺钟等待的同签名新版，ARM64 历史回放及受控冷启动验证通过。手机实收 GAMG07 的可选健康 G/E/C 随目标时刻从 13/12/24 降至 1/11/23，18:14:24 北京时间起 GPS 为 0。会话初始化后目前不会滚动重载 NAV/VMF3，越过已加载 VMF3 右端会停止。真实回调排队/丢期及运动绝对精度需另行现场验证。见 [真机解算验收](../validation/android_ga_edit17_fullbias_20261119/REPORT.md) 与 [产品时间证据](../validation/uduc_position_audit_20261119/product_check.json)。
- 【Git迁移】PC大量关键实现未提交。只恢复HEAD会丢失本页所述工作区成果。
- 【历史缺失】无法获取全部压缩前聊天、门限初始选择依据或所有未保存实验。代码、配置、输入与日志优先，缺证据不补写。

### 参考坐标修订

- 【当前用户原始点位】2026-11-07提供Pt42和Pt41为iq，纬度30°46′01.8362″、经度103°58′46.1935″，高程分别483.989/483.984m；Pt40为k70，30°46′01.8358″、103°58′46.1843″、483.963m；Pt39为k70，30°46′01.8359″、103°58′46.1841″、483.962m。四点存档E:/RTKLIB_Data/10.31/reference_points_20261107.json。
- 【本轮四点评价】新回放按本机两点分别评价，主图暂用与旧经纬度相同的Pt40/Pt42。K70末ENU(+0.644,−0.313,−0.492)m，IQ末ENU(+0.741,−0.496,−2.405)m；Pt39末U−0.491m、Pt41末U−2.400m。完整依据在validation/oct31_reference_diagnosis_v1/summary.json和reference.json，高程类型继承此前椭球高口径。旧缓存重评保留在evaluation_user_points_20261107/。
- 【历史口径】早期分段/连续报告用486.963m，后续跨机型报告用483.000m。tests/report_tdcp_cross_device.py::REFS及码QC目前仍记录483.000m，tests/process_oct31_segments.py::REFERENCE仍记录486.963m。它们是历史复现脚本，新的评价必须显式读取最新参考，勿直接沿用旧常数。
- 此前两机共用483.963m的评价保留于evaluation_h483963_20261107/，已被本次分机点位取代。相对该次结果，K70不变，IQ高程参考增加0.026m，U减0.026m，E/N数值误差内一致。docs/OCT31_HEIGHT_RESTART_REPORT.md的末U−3.492m属于486.963m历史口径。
- 该实验关于重启额外误差和部分分段首FullBias锚不同的观察仍有价值，但不是某个P0或物理公式错误的唯一证明。
- 最近10/21跨机型口径高程459.788m。其他数据各有高程类型、投影和真值修订，按该组参考文件核实，不设全项目通用真值。

## 已完成排查和否定证据

- P0/R/GIM全程E1–E4已完成，见docs/FILTER_FULL_EPOCH_ABLATION_REPORT.md、docs/FILTER_PRIOR_R_CAUSAL_REPORT.md。无新变量或反例不重复全程。
- Joseph数值缺陷不是所验证样本米级轨迹变化的主要解释。10/25同窗对照也不支持实时JNI额外制造米级差异，不能推广成所有转换问题都已排除。
- 10/31接受载波卫星DOP无几何秩亏，不能单靠DOP解释高程；它也不是完整含码和先验的可观测性认证。docs/OCT31_SEGMENT_DOP_REPORT.md。
- 10/31新三项单因素已完成，不重复：K70移除B2a后末300s U仅+9.0cm；IQ移除C7I码仅+0.16mm；K70仅按同刻IQ共同信号相位缺失置空27278行后U约−9.2cm，其余P/D/时间/LLI/身份和保留相位逐字段不变，B2a不变。两机本段总ZTD全程为正，不能套用历史其他vivo样本的负延迟问题。对照没有证明缺相位、产品或联合状态模型在所有条件下无影响。
- 相位OSB OFF/ON及覆盖/模糊度参考控制已完成，不再重复同组合四次完整回放。原生查询与独立解析一致、无新增PPP失败、ARC_RESET数不变；IQ原有编辑响应导致ARC_REINITIALIZED多2行、拒绝多6行，K70拒绝多1行，未隐藏为“完全无编辑变化”。证据validation/phase_osb_trial_v1/。
- raPPPid同产品非组合、轨钟/OSB/天线、码相闭合和状态混淆已有多轮证据，按HANDOFF/INDEX.md和docs/PPP_DIAGNOSIS_INDEX.md定位，不重做整套静态差分。
- 同段离线码标定不能当作实时/跨段/跨机型提升，见docs/OFFLINE_CODE_CALIBRATION_REPORT.md、docs/PPP_COMMITTED_CODE_REFERENCE_REPORT.md。

## 下一步与验收

Android 第 17 次最终试算、首期缺钟恢复、vivo ARM64 全段回放及安装已完成。后续按既定顺序分别验证手机网络自主取得 NAV 并在有效率衰减前交接，以及 VMF3 跨界更新，要求已有滤波状态连续。精度归因从 10/31 K70/IQ 同刻共同卫星实际码相与先验更新开始，结合 10/21 C24/1P 检验上报码时间不确定度的增量价值，按采集留出。见 [审查与判据](../validation/uduc_position_audit_20261119/REPORT.md) 与 [运动现场流程](../validation/android_pc_edit_boundary_audit_v1/FIELD_PROTOCOL.md)。

0. 按用户明确要求保留B1I 2I与B1C 1P同时参与，B2a保留，B2b继续排除。接入/天线交付/回放均完成，不再把B1C列待启用或按本次精度回退；后续精度归因须保持这些身份清楚，不调参拟合真值。IQ Q仍暂停。11/19 已核对 vivo 产品下载版本，后续解算行为按实际安装包及 ABI 验收。
1. 用户四点存档、两机新回放和三个单因素已完成。原缓存SHA保持；新回放逐字段复现。本机两点均已评价，具体时段点号待确认，不平均测点。证据优先复用validation/oct31_reference_diagnosis_v1/，不重跑本轮完整对照。
2. 若开展版本验证，先确定当前源码、独立修复EXE、标准EXE或已安装APK，验收须给身份、实际配置和对应回执。
3. 若继续采集验证，先核对已安装版本，比较同事件Raw和转换sidecar的time、P/L/D、LLI、sat/code、断弧及跳过原因，单独记录产品覆盖与现场验证范围。
4. 若继续10/31精度诊断，优先针对本段共同卫星/实际信号码相值与真实联合状态更新补最小诊断，区分当期观测和历史先验分配；不重复B2a/C7I/缺相位单因素或旧P0/R/GIM全程。保留框架/产品参考未认证边界，不调参当归因。
   相位OSB候选及现有组合OFF一致性/ON精度对照已完成。只有取得同日匹配RTS钟差/轨道或新的参考兼容证据时，再作隔离产品对照；不因候选末点略好就启用正式默认，不通过新增门限拟合真值。
5. 每次重要阶段更新本页相应条目，旧当前结论被替换，已解决移入已完成；历史报告原位保留，不逐次堆聊天。

## 按需证据索引

- 正式入口与回执格式为docs/B_VERIFIED_SESSION_HARDENING_REPORT.md、docs/FORECAST_ONLY_WORKFLOW.md、config/b_verified.json。
- 大历史索引为HANDOFF/INDEX.md、docs/PPP_DIAGNOSIS_INDEX.md、validation/audit_registry/AUDIT_REGISTRY.json。HANDOFF/CURRENT.md和docs/PPP_VALIDATED_CORRECTIONS.md部分过时，按相关证据使用。
- 压缩日志先查validation/diagnostic_storage_manifest.json及各实验storage清单。不要因只剩.gz而重算。
- 原始数据与产品在E:/RTKLIB_Data。接续文件不是备份，新会话必须实际读取，核对其后发生的变化。
