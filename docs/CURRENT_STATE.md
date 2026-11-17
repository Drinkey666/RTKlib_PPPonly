# PPP 项目当前状态

2026-11-17 的跨仓库归档见[项目现状与证据索引](PROJECT_STATUS_AND_EVIDENCE_20261117.md)。下文的 APK 安装描述属于 11/10 解算交付。后续 11/11 vivo 已验应用内高德底图、设备标点、拖动和回中，现行版本的实时 PPP 地图切换和新采集闭环仍待现场验收。

本页与根目录AGENTS共同作为新会话入口。最新为2026-11-10按用户要求正式同时接入B1I 2I与B1C 1P，B2a保留、B2b排除、IQ Q问题暂停。370项原生检查通过，Android JVM187通过/9跳过；两机完整接入及新版ATX对照完成。标准PC EXE已更新，Android包已构建未安装；整体精度未改善。

## 当前任务

用户最新明确B1I与B1C都要参与。正式白名单已同时允许2I槽0、1P槽3，5P保留；各自OSB/波长/N/RCB独立，7D/P/Z在准入及共同PPP内核继续排除。两机各120期移除1P控制复现基线；加入1P与仅更换ATX各两机3710期，共四次完整回放无PPP_FAILURE、Q逐期不变。K70/IQ实际接受C1P载波23955/19898行，既有其他信号输入逐字段不变；IQ的Q仍被原策略排除，本轮回放仅验证B1C未恢复Q候选。370项原生全过，Android JVM196项187通过9跳过0失败，四ABI构建通过未安装。原ATX缺C06/07/11/12的C01校准，新版已验证并用版本文件igs20_20261110.atx交付，PC默认/Android内置与实时后处理优先选它，旧文件不覆盖。末300s新配置水平RMS K70/IQ 0.772/0.937m、U均值−0.458/−2.454m，未获得整体精度改善；按用户要求保留B1C，不调参或擅自撤准入。证据validation/b1i_b1c_integration_v1/REPORT.md及summary.json。

用户已授权按规范接入相位OSB并检验，要求不要过度防御。已完成独立候选，见validation/phase_osb_trial_v1/REPORT.md、summary.json、PHASE_OSB_OFF_ON.png和build/trial.exe。仅私有ppp.c新增L类产品加载、corr_meas统一改正及模糊度参考转换，无ABI变化；生产源码/32个旧对象/正式EXE未改。215项既有回归+32项新增通过；两机OFF前120期及完整3710期逐字段复现缓存，ON各3710期，原始adapter观测逐字节相同、Q逐期不变、无PPP_FAILURE。末300s K70/IQ U均值分别−0.490→−0.371m、−2.431→−2.398m，但水平RMS分别0.718→0.784m、0.872→0.911m，IQ全程三维RMS3.234→3.300m。没有消除米级偏差或获得整体改善，候选未晋升正式、Android未移植。

此前相位OSB参与核查仍有效，见validation/oct31_phase_osb_audit_v1/：原BIA有867条码记录和15007条相位记录，正式读取器只识别C记录；删除L副本的两机30期与基线完全一致。新ON行为只在上述候选EXE，不能把源码主路径或旧正式程序说成已默认使用相位OSB。

项目记忆机制及Android实时GNSS→JNI→RTKLIB只读Word教材已交付。最新任务为按用户四点重新解算并对比查找问题，证据在validation/oct31_reference_diagnosis_v1/REPORT.md、summary.json及ENU_COMPARISON.png。两机各3710期新回放除耗时外精确复现缓存；另外完成K70去B2a、IQ去C7I和K70叠加IQ共同信号缺相位模式三次完整回放。三组关闭动作120期控制逐字段一致。四点原件在E:/RTKLIB_Data/10.31/reference_points_20261107.json，每份解分别按本机两个点评价；主图暂选Pt40/Pt42，未取平均。具体点号与时段对应仍未获用户确认，沿用此前WGS84椭球高定义。仍未找到米级偏差的唯一物理根因或正式修复。长期目标仍为多机型严格实时、非组合、文件预报产品PPP及独立验证的抗差/自适应改进。

## 工程身份和Git快照

|对象|核验结果|
|---|---|
|活动PC根目录|E:/GNSS/PPP_only|
|PC分支/HEAD|codex/ppp-robust-ekf / 0fd98a9e21f7aa615194a02f6e143d64c2c00335|
|最近提交|0fd98a9，2026-10-09，卫星钟差回退方差和精度回归；前有e2de9ae普通Huber、93de551 Phase2.5、4715448 Phase2、ac99aba Phase1|
|历史Joseph提交|e2070cd对象仍在本地，但不是当前HEAD祖先。是否有修复要查工作区，不能只看HEAD|
|PC暂存区|空|
|PC未提交|2026-11-10本轮后24个tracked文件修改，1916新增/298删除，含原有大量修改；新增tests/报告/备份未跟踪，不能只迁移tracked|
|Android独立仓库|E:/android/test/FTPGet，main / e67c9ed266bc6c9a725ff4130ec65775b63424f8，2026-11-04 Android UI及PPP实现更新|
|Android工作区|已同步B1C准入与版本天线产品选择，含C核心/清单/Kotlin/测试和新ATX资产的未提交成果；APK已构建未安装，须迁移工作区及新资产|
|本聊天原cwd|E:/GNSS/rtklib_only/rtklib_only，属于旧工程目录；本轮全部PC工作在活动根目录|

建立项目记忆时已存在的tracked修改如下。本轮新增独立验证脚本及证据、维护本页，继续保留这些源文件修改；未改生产内核及默认参数。

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
- 固定钟段独立构建入口为validation/observation_generation_2023_v1/build_pc.cmd；python tests/run_observation_generation_core_tests.py执行5套215项，复用此目录pc_obj；build_native_tests.cmd执行51项，脚本另引用标准build对象，运行前分别检查。
- Android工作目录E:/android/test/FTPGet，JAVA_HOME用E:/Program Files/Android/Android Studio/jbr；执行 ./gradlew.bat :app:testDebugUnitTest :app:assembleDebug --offline --console=plain。设备安装、仪器测试和现场采集分别记验收。
- 归档回放run_ppp.cmd <清单.json> --output <新结果路径>，模板config/b_verified_replay.example.json；预报发布/接收可用性用run_forecast_ppp.cmd。run_b_verified.cmd设置正式预设，实际调用标准EXE。

### 程序文件与源码必须区分

|文件|本轮SHA256及身份|
|---|---|
|x64/Release/PPP_only.exe|3720d038878e33d048e229aea75b75c8d8cfa6fddd9edfdff2a68ccc4a42d29e，2026-11-10当前标准程序：固定钟段/Joseph及B1I+B1C同时准入、B2b排除；默认ATX版本文件。此前063f8335旧程序保存在validation/b1i_b1c_integration_v1/before/standard_PPP_only.exe|
|validation/observation_generation_2023_v1/pc_build/PPP_only.exe|b21c0420e7ebcf85251ede0dd4b06c20a05530cf4fe8560dd027f5d957826944，固定钟段修复独立EXE，后续10/31及跨机型实验复用|

程序身份按上表与实际SHA核对。此前10/31诊断和相位候选阶段仅新增独立程序；2026-11-10 B1I+B1C接入已重建并更新标准EXE，旧标准备份在validation/b1i_b1c_integration_v1/before/standard_PPP_only.exe。旧固定钟段程序及私有对照仍保留原位，不混用。Android当前33份源与PC逐项匹配、四ABI已重编译，APK及版本ATX已校验打包，但未安装、未做现场验收。

## 已完成与验证范围

|事项|有效结论与证据|
|---|---|
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

## 当前问题与适用边界

- 【已完成/用户策略】B1I与B1C独立槽及正式同时准入已完成，不再列为待启用。B2b明确排除，不再安排其接入。旧ATX缺少2026 PRN/C01校准的已知项已通过新版版本文件交付修正，旧文件保留作历史复现；新版日期/身份覆盖不是NRT轨钟+RTS BIA完整参考兼容认证。IQ Q问题暂停，不自动恢复。
- 【IQ Q历史已核实】10/7提交已存在5Q整体拒绝规则；10/18两份IQ RINEX实际C5Q为4406/4229条、L5Q均空，不能把头定义当使用或有效载波证据。10/31正式TXT明确8颗5Q无OSB且被策略排除；不是本次B1C引入。可先保留Q身份接回浮点载波，码待确认；旧候选及215+51+25检查/回放保留，但基于旧B1C/ATX前基线且用户仍暂停。见validation/iq_b2aq_phase_trial_v1/HISTORY_REVIEW_20261110.md。
- 【未解决】多段手机米级偏差与跨时段/设备收敛差异，仍无唯一通用根因或通用实时消除方法。不同样本的现象不能并成一个已证实原因。
- 【本轮缩小范围】10/31两机后段东向均正、IQ持续偏低。三项单因素不足以各自解释约1.94m设备间垂向差；尚未验证联合效应，也未把K70可用性对照外推为IQ的通用因果结论。剩余关注共同信号实际码/相位差异及与电离层/对流层/位置的联合分配，不能据当前证据直接调参或换码型。
- 【输入剩余证据】100ms发射时标冲突仍有拒绝记录；Galileo 7Q原始ADR与距离率积分不一致，当前实时白名单不纳入。与已修256ns台阶分别看待，见观测生成报告。
- 【联合状态模型】部分历史PHYSICAL/vivo负湿或负总延迟需先核实状态定义；电离层时间先验与联合分配有特定因果证据，未获通用默认修改依据。docs/EXTERNAL_PHASE_STATE_CAUSAL_REPORT.md、docs/IONO_OBSERVABLE_RATE_TRIAL_REPORT.md。
- 【产品风险】NRT轨钟+RTS BIA的完整参考兼容性未认证，天线PCO/PCV缺项和参考声明告警保留，过期仍必须失败。
- 【相位OSB候选已验证】当前固定NRT轨钟+RTS BIA组合下，小幅高程变化伴随水平/部分收敛退化，未消除IQ持续偏低。不能再把“先接入相位OSB看看”列为未执行的新建议。原NRT PANDA-CLKDEN与RTS PRIDE BIA的完整参考兼容仍未认证；按PRIDE官方路径尝试取同日匹配RTS轨钟均超时，不能说产品不存在或用结果认证兼容。
- 【现场验证未知】旧观测生成回执记APK未安装、新室外采集未验收；Android之后已有11/04提交，本轮未读取手机安装身份，不能把旧未安装状态当今天事实。
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

0. 按用户明确要求保留B1I 2I与B1C 1P同时参与，B2a保留，B2b继续排除。接入/天线交付/回放均完成，不再把B1C列待启用或按本次精度回退；后续精度归因须保持这些身份清楚，不调参拟合真值。IQ Q仍暂停。当前APK已构建未安装，后续设备验收须单独核对实际安装版本。
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
