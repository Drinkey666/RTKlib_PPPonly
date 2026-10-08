# Phase 2：只读标准化新息诊断

日期：2026-10-08。参照：已验收 `ac99aba`；本地分支 `codex/phase2-innovation-diag`。
启动时已有两个未跟踪的诊断模块草稿；本阶段继续完成这些草稿，没有丢弃已有修改。参照程序已保存在 `validation/phase2/PPP_only_ac99aba.exe`，SHA256 与 Phase 1 证据中的验收程序一致。

## 1. 实际 S 计算与矩阵布局

`src/rtkcmn.c:1497` 的 `filter_()` 使用列主序：P 为 nx×nx，H 为 nx×nv，R 为 nv×nv。内部 H 的第 i 列是教科书设计矩阵 G 的第 i 行的转置，即 H=Gᵀ。

- P[a+b*nx]，H[a+i*nx]，R[i+j*nv]。
- `F=P*H`，`S=Hᵀ*F+R`，等价于 G P⁻ Gᵀ+R。
- 本项目 `ppp_res()` 填写的 R 为对角矩阵；诊断通用接口和人工单测仍支持非零 R 非对角元素。
- `src/ppp_innovation_diag.c:6` 用稀疏非零 H 系数计算所有交叉协方差项：pred_var_i=ΣₐΣᵦ H[a,i] P[a,b] H[b,i]，Sii=pred_var_i+Rii。
- PC 正常回放只计算边际 Sii，避免申请/计算完整 nv×nv S；单测通过可选独立 full_S 输出逐元素验证完整矩阵。
- u=v/sqrt(Sii)。v、P、H、Rii 非有限、Sii 非正或非有限、u 溢出均标记 invalid 和具体原因，绝不把 NaN 改成零。

人工例：P=[[4,1,.5],[1,9,2],[.5,2,16]]，G=[[1,2,-1],[0,1,3]]，R=[[2,.25],[.25,3]]。
理论 pred_var=[51,165]，S=[[53,-17.25],[-17.25,168]]，v=[10,-6]，代码与理论逐元素完全一致。若丢弃 P 的交叉项，第一项会错误变为 56；单测能检出该问题。

### 活跃状态压缩的限制

`src/rtkcmn.c:1520` 的 filter() 只更新 x!=0 且 Pdiag>0 的状态。诊断按用户要求采用完整 P⁻，没有偷偷压缩。若非零 H 涉及滤波器排除且仍具有协方差的状态，记录 `inactive_state_support=1`；此时完整 S 与实际压缩滤波器 S 可能不同，未来学习必须排除/另行核查。人工测试覆盖该情形；本轮 TXT/RINEX 实际数据中该计数均为 0。

## 2. 如何保证使用 P⁻

`src/ppp.c:3948` 调用 udstate_ppp()，形成现有算法的预测/初始化状态。每次编辑试算都将同一个 rtk->x/P 复制到 xp/Pp；`src/ppp.c:4061` 的 pre-fit ppp_res() 形成 v/H/R 后，`src/ppp.c:4080` 立刻调用只读诊断，随后才调用 filter()。日志延迟到历元结束，但数值已存入独立 trial_value，绝不使用后验重算 S。

所有输入参数 x/P/v/H/R 均 const，输出另行分配。不修改滤波输入、xp/Pp、rtk->x/P、Q、R、权重、reject、质量历史，也不依据 u 决策。`src/rtkcmn.c` 相对 ac99aba 没有改动。B 原有 R-only z0/post-fit 历史判别保持原样。

**统计解释限制：** 这里的 P⁻ 是 RTKLIB 当前实现中调用测量更新之前的 P。udstate_ppp() 内部的新模糊度、部分初始状态会使用当前观测构造种子；这些初始化行不是独立于当前 z 的纯时间预测，不能直接当作 i.i.d. 新息用于未来 eta 学习。首次 SPP 的粗位置/钟差也来自当前观测。本阶段只准确记录其实际更新前量，不重新设计初始化。

## 3. 观测行映射与日志结构

独立 `ppp_innovation_meta_t` 见 `src/ppp_innovation_diag.h`；每个有效 pre-fit nv++ 前写入对应元数据，观察缓冲区不参与估计。

| 内容 | 定义/位置 |
|---|---|
| time/week/tow/epoch | GNSS 观测时间；独立输入历元计数器，不更改 rtk 时间状态 |
| row/trial/sample_scope | 当前残差行（0 起始）、编辑迭代（0 起始）、FIRST_PREFIT/EDIT_RETRY |
| source_obs_index | 传给 ppp_res 的有效 obsd_t 数组索引（0 起始），不是原始 TXT 行号；外层 sanitize 后的输入序号 |
| sat/sys/signal | 卫星编号、星座和实际 code2obs 名称，不能用 frq 推断实际 code |
| frequency_slot/frequency_hz | RTKLIB 槽位（0 起始）与 sat2freq 的真实频率（Hz） |
| signal2/frequency2_hz/combined | IFLC 实际组合的第二信号/频率；组合不能当作单信号学习；CN0 是第一槽信号 CN0 |
| elevation_deg/cn0_dbhz | 角度/度；存储 SNR × SNR_UNIT（.001）得到 dB-Hz |
| measurement_class | GNSS_CODE/GNSS_PHASE/IONO_PRIOR/TROP_PRIOR/OTHER_CONSTRAINT |
| R0_or_R/obs_var | 当前实际 Rii（B 中可能已经包含所有历史处罚） |
| R0 | 现有基础观测模型加产品/大气模型误差的基础方差，虚拟约束为 NaN，明确表示不适用 |
| pred_var/Sii/sqrt_Sii/u | 均由实际 pre-fit P⁻/v/H/R 只读计算；v 为米，方差为平方米，u 无量纲 |
| finite_flag/invalid_reason | u 是否有效；NONFINITE_V/P/H/R/S/U、NONPOSITIVE_S、DIAG_NO_MEMORY |
| slip_flag/arc_status | 记录已有周跳证据和实际弧段；保留 B 在 udbias 中清除前的 slip 快照/计数证据 |
| legacy_reject_flag | 本历元最终 mexc 中，该来源信号/类型是否被原有规则屏蔽；A 也填写该同名列 |
| epoch_failure/solution_status/posterior_committed | 区分失败、输出 Q 和成功提交（成功但载波不足 Q5 仍可能已提交） |
| abs_v/sqrt_Rii/sqrt_pred_var/abs_u | 启动阶段所需直接观察量 |

GNSS 行：`src/ppp.c:3277`；IONEX 行：3383；VMF3/ZWD 行：3443。IONEX 约束是垂直参考 L1 电离层延迟/米，TROP 约束是现有 ZTD/ZWD 等价方程/米。约束 source_obs_index=-1、signal 为空，TROP sat 为空。没有未知未分类行。

弧段状态包含 ACTIVE、ARC_PENDING_INIT、ARC_REINITIALIZED、UNINITIALIZED、LEGACY_ACTIVE、NA；B 的 LEGACY_ACTIVE 仅表示当前存在旧算法状态，不保证已经修复其旧弧段缺陷。P 行也保留弧段信息，以识别相位待初始化时期。完全缺失/未进入残差矩阵的信号没有创新行，仍通过 Phase 1 的 ARC_RESET/ARC_PENDING_INIT 等 trace 观察。

观察器默认关闭。启用方式（产品环境变量仍按原运行配置）：

```powershell
$env:RTK_PPP_BASELINE='A' # 或 B
$env:RTK_PPP_INNOVATION_DIAG='E:\GNSS\PPP_only\validation\phase2\innovation_diag.csv'
./x64/Release/PPP_only.exe --source txt-fast --no-gui --max-epochs 600
Remove-Item Env:RTK_PPP_INNOVATION_DIAG
```

写入/分配失败只关闭或缺失诊断，记录原因，不改变算法结果。CSV 是一个 PC 进程/单回放观察器，尚未设计多 rtk 会话并发日志；Android 本阶段未处理。数值失败若发生在形成有效 pre-fit 矩阵之前，不伪造观测行，其失败依据仍来自 Phase 1 trace。

## 4. A/B 与 ac99aba 的回归

Release x64 构建通过。参照程序 SHA256：`39239e7bf9be538c0fc0207274c9d1d1e2428b28303bbde6637979f5cc23181e`，与 Phase 1 验收证据一致。

| 输入/模式 | 共同输入/有效输出历元 | Q5/Q6 | reject | detector slip | 相对 ac99aba |
|---|---:|---:|---:|---:|---|
| TXT fast A | 600/600 | 2/598 | 0 | 127 | 相同 |
| TXT fast B | 600/600 | 2/598 | 602 | 99 | 相同 |
| RINEX A | 1200/1200 | 3/1197 | 5 | 637 | 相同 |
| RINEX B | 1200/1200 | 3/1197 | 22 | 502 | 相同 |

TXT 比较旧程序、新程序诊断关闭、新程序诊断开启：去掉墙钟耗时后的全部解算 CSV 字段完全一致，XYZ 最大差 0 m，Q/ns 差 0，.stat 和 .obs.csv 分别字节一致，$PPP_STATE 中 XYZ/clock/ZTD 逐条一致，reject/slip/arc/failure 计数一致。RINEX 1200 历元的输入时间记录、结果数值行、.stat 字节和上述事件统计也一致。失败历元均为 0。

A/B 行为定义没有改变。A 仍为 Phase 1 CLEAN_BASELINE，B 仍为 Phase 1 LEGACY_BASELINE；没有把 B 的旧 R-only 标准化替换成新 S 标准化。数值输出比较是同一输入、同一产品、同一模式比较，不比较真值/精度。

## 5. 单测与日志一致性检查

- Phase 1 的 44 项：44 PASS，0 FAIL。
- 新增 Phase 2 的 26 项：26 PASS，0 FAIL。包括理论全 S（含非零交叉 P/R）、Sii 分解、正确 u、所有输入 bitwise 只读、诊断开关下 filter 结果 bitwise 相同、inactive 状态标记、NaN/Inf/零负 S/u 溢出、实际源行映射、编辑后的行重排、P 行 pending 弧段、空 L2 槽下 IFLC 实际 L1/L5 组合、日志打开失败，以及开启观察器后的 PPP NaN / rtkpos Inf 原子失败保护。
- 所有实际有效诊断行检查 Sii=pred_var+Rii、u=v/sqrt(Sii)、Sii>0、finite；无 invalid 行、无负 pred_var、无 inactive_state_support。
- TXT 所有首次 GNSS 行逐条匹配原始适配器 .obs.csv 中 sat/signal/频率槽/CN0；每个 epoch/trial 的 row 均连续。
- RINEX 虚拟约束分类、无信号标记、source=-1 和矩阵身份式均通过。

命令：`tests/run_phase1_tests.ps1`，`tests/run_phase2_tests.ps1`，`python tests/run_phase2_replay.py`，`python tests/run_phase2_rinex.py`，`python tests/summarize_phase2.py`。回放脚本要求本机产品路径和被保留的参照 exe。测试记录见 PHASE2_TEST_RESULTS.txt；完整哈希/证据见 PHASE2_EVIDENCE.json。

## 6. 新息统计摘要

统计对象：TXT fast 600 输入历元。STARTUP 为从首个输入 GNSS 时间起 [0,30) 秒，STEADY 为其后；这只是时间标签，不宣称后者已经收敛。只统计 FIRST_PREFIT；保留原算法随后拒绝的行，避免用最终接受子集掩盖粗差。重复编辑不当作独立样本。std 使用 ddof=1；分位数用排序后线性插值。

| 组别/类型/阶段 | n | mean(v)/m | std(v)/m | mean(u) | std(u) | median(abs(u)) | P95 | P99 | >1/% | >2/% | >3/% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A / P / STARTUP | 1007 | 17.3998 | 18.2080 | 0.2889 | 0.2956 | 0.4255 | 0.5865 | 0.7686 | 0.099 | 0.000 | 0.000 |
| A / P / STEADY | 21779 | -8.9485 | 32.2691 | -0.1481 | 0.5196 | 0.1215 | 1.1342 | 1.5216 | 10.326 | 0.482 | 0.459 |
| A / L / STARTUP | 586 | 17.5125 | 17.0364 | 0.2879 | 0.2735 | 0.4393 | 0.5273 | 0.5397 | 0.000 | 0.000 | 0.000 |
| A / L / STEADY | 12536 | -8.6555 | 25.1289 | -0.1434 | 0.4167 | 0.1087 | 1.0898 | 1.2212 | 9.349 | 0.000 | 0.000 |
| B / P / STARTUP | 990 | -13.4184 | 13.6177 | -0.2213 | 0.2234 | 0.2185 | 0.5936 | 0.7330 | 0.000 | 0.000 | 0.000 |
| B / P / STEADY | 21666 | -15.8109 | 32.6007 | -0.2653 | 0.4504 | 0.1339 | 1.2240 | 1.5650 | 12.799 | 0.189 | 0.000 |
| B / L / STARTUP | 586 | -13.5514 | 11.2680 | -0.2259 | 0.1760 | 0.1991 | 0.4820 | 0.5118 | 0.000 | 0.000 | 0.000 |
| B / L / STEADY | 12329 | -15.5369 | 24.8095 | -0.2581 | 0.4119 | 0.1076 | 1.2055 | 1.3448 | 13.643 | 0.000 | 0.000 |

按 constellation / actual signal / P-L / 阶段的全部 **44 个分组**见 PHASE2_SIGNAL_STATS.csv；各连续卫星信号的时间相关描述见 PHASE2_TEMPORAL_STATS.csv。阈值仅用于统计，没有进入 reject 或权重规则。

- A：总日志 35908 行，FIRST_PREFIT 35908，重试 0；真实 GNSS 35908；分类 {'GNSS_CODE': 22786, 'GNSS_PHASE': 13122}；invalid=0。
- B：总日志 97203 行，FIRST_PREFIT 48832，重试 48371；真实 GNSS 35571；分类 {'GNSS_CODE': 22656, 'GNSS_PHASE': 12915, 'IONO_PRIOR': 12662, 'TROP_PRIOR': 599}；invalid=0。

B 的 Rii 已含历史抗差/持续处罚/平滑统计修正，u 也是该实际算法 R 下的观察量，不能把 A/B u 的差异直接解释为手机原始噪声差异。

## 7. 启动阶段“大 raw residual、较小 u”的实际证据

例：A 第一历元 G10 1C P：v=18.862719 m，sqrt(R)=2.636836 m，sqrt(pred_var)=85.994312 m，sqrt(S)=86.034729 m，u=0.219245。

另一例 A C09 2I P：v=58.383680 m，sqrt(R)=2.413067 m，sqrt(pred_var)=65.690155 m，u=0.888175。A G26 5Q L：v=49.772730 m，sqrt(R)=0.139587 m，sqrt(pred_var)=87.980152 m，u=0.565726。

因此本次确实观察到较大 raw residual 但 |u|<=1。它只说明当前模型给出的预测不确定度很大，不证明该观测无粗差、P 校准正确或定位准确。`src/ppp.c:2021` 的 GPS 接收机钟差每历元以白噪声方差 VAR_CLK=60² m² 初始化，这会使预测方差在启动后也持续偏大；本阶段没有调整它。首次/新弧段使用当期观测构造状态种子也会影响创新统计。

## 8. 非零均值/相关性迹象

A 稳定阶段 P/L mean(u)=-0.1481/-0.1434；B=-0.2653/-0.2581。B C 7I P 稳定阶段 n=483，mean(u)=-0.3777。存在描述性的非零均值和公共变化迹象，不能据此直接做零均值白噪声 eta 拟合。

相关性分析按单颗卫星/实际信号/P-L/阶段形成相邻输入历元对，要求 GNSS dt∈(0,1.5] 秒、无已知 slip/reset/pending/reject/failure/inactive，至少 20 对，然后计算 Pearson 配对相关。不把不同卫星拼成一个时间序列；时间趋势尚未移除，亦未校正多重比较/非独立误差。

A E26 1C L 稳定阶段 245 对 lag-1 配对相关=0.99613，B 同类 249 对=0.99613；A G32 1C P 90 对=0.99263。它们提示显著连续变化/相关迹象，但不能独立证明相关性来自测量噪声。公共钟差、函数模型误差、状态初始值、缓慢变化的大气/码偏差和 B 平滑/先验均可能贡献；因果来源留待独立实验。

## 9. 目前不适合直接进入未来 eta 学习的观测

1. IONO_PRIOR、TROP_PRIOR、OTHER_CONSTRAINT：外部伪观测；B 首次分别含 12662、599 行，不能归入手机信号。
2. IFLC combined 行：两个信号组合，不能作为单个 actual signal 的独立噪声样本。
3. invalid u、Sii<=0、未知 source/signal 或 inactive_state_support 行；本次实际计数为 0，但人工单测覆盖。
4. slip/reset/pending/reinitialized、首次初始化及长间断后重建行：当前观测参与建立状态，不满足独立预测创新的假设；无有效 L 的 pending 信号也不伪造相位创新。
5. 原算法随后拒绝的 FIRST_PREFIT 行、整个更新失败历元、EDIT_RETRY 行：需要明确粗差/选择/重复使用处理，不能直接积累为独立正常样本。本次 B 602 条首次行随后被拒绝。
6. B 含历史膨胀 R、持续质量学习、CMC 处罚、实验性平滑或旧生命周期未验证的行；新 S 不能自动消除这些历史机制。
7. 存在公共偏差、较强时间相关/非零均值、预测方差占主导的区段：需先分离模型/状态不确定度与测量噪声，不能直接用创新平方等同 R。STARTUP/STEADY 标签只是时间划分，尚无收敛准入条件。

以上是后续设计建议，**未启用任何 eta 样本筛选、学习、Huber/IGG、R/Q 自适应或新的拒绝规则**。Phase 2 到此结束，C/D 继续保留未实现状态，等待下一阶段确认。
