# Phase 2.5：新息可学习性与异常证据审计

2026-10-08；验收参照 `4715448`；分支 `codex/phase2-5-learnability`。开始时工作区干净，参照可执行程序已另存 `validation/phase2_5/PPP_only_4715448.exe`，并保留标签 `phase2/accepted-4715448`。

## 结论与九个验收问题

1. **44 个阶段分组中严格适合当前 R 学习的组：0。** 44 包含 A/B、P/L 和 STARTUP/STABLE 分层；去阶段后是 22 个基线×星座×信号×P/L 组，其中 P 为 12 个基线×实际信号组（每组 A/B 各 6）。不能把 44 当成 44 个独立实际信号。
2. 首次 P 行 A=22786、B=22656；仅排 startup/实际弧段初始化/原算法 reject 后 A=21583、B=20835，共42418条。这些只是结构筛查存活样本，**不是学习资格通过样本**；严格资格均为0。
3. 稳定阶段所有 12 个伪距分组 mean(v) 均为负；尤其 B 的 C7I、G1C、C2I 同号比例较高。存在非零均值/持续偏差候选证据，未进行假定 IID 的显著性检验。
4. 按连续弧段去均值后的 22 个稳定 P/L 组中，21 个 |rho1|>0.9，其中 P 为11/12个；B C7I P 是例外。高相关组不等于有资格学习的组。
5. 旧约0.996主要来自 **E26 / Galileo 1C / L** 的多个短弧段聚合。固定207个共同有效相邻配对支持，pooled Pearson仍约0.996；逐弧段均值中心化后 A/B为0.7080/0.6964。另有 G32 1C P 旧约0.993/0.995。其含义见第5节，不声称证明测量噪声因果来源。
6. `mean(v²)-Var(v)=mean(v)²`。稳定 P 组该抬高量 A=12.13–248.36m²、B=74.33–532.58m²。12组两种候选噪声量都为负，原值保留，不裁零、不反馈。
7. 当前观测参与初始化、初始化来源未知、启动/新弧段/周跳/间断恢复、拒绝/编辑重试、虚拟约束、IFLC、B历史变权/平滑和持续偏差候选均不能直接入 eta；L 不进入计划中的第一阶段 P 学习池。
8. 所有6个实际 P 信号都有名义结构样本，但**没有严格可学习样本**。高相关使名义N远大于有限lag ESS；不能凭数百/数千行声称足以支撑信号级 R 学习。
9. 本阶段不合并不同 actual signal。合并不能修复当期观测依赖/均值偏差/相关性；过细组先保留“不足以估计”的结论。尤其 B C7I P 的诊断序列碎片化，应先获得更多独立、有效连续弧段证据，再讨论合并条件。

## 1. 只读边界与实际改动

没有修改 R、Q、robust weight、eta、filter数学或reject。源码只在原有事件执行之后调用独立观察器；观察器状态与rtk->x/P/ssat/滤波输入分离，离线脚本只读CSV。坐标不作为筛选或调参依据，未使用真值。

| 文件/函数 | 本阶段用途 |
|---|---|
| PPP_only/ppp_position.c / rtkpos | :302 记录当期SPP尝试及成功与否，不改变其返回/回退逻辑 |
| src/ppp.c / udpos_ppp、udclk_ppp、udbias_ppp | :1939等记录真正执行的当期观测初始化；:2472记录legacy当期P/L共同offset调整；:2525记录模糊度实际播种 |
| src/ppp.c / ppp_res | 记录pre-fit clock/ISB/iono/trop/ambiguity及对角协方差；只读现有x和P |
| src/ppp.c / pppos | :3914开始独立观察器；:3977记录原检测器事件；:4108在filter前固定每行来源/连续性 |
| src/ppp_innovation_diag.h/.c | 扩展元数据、P/L独立创新轨迹、原始信号轨迹、CSV；原S计算不变 |
| tests/analyze_phase2_5.py | 资格多标签、矩、分弧lag相关、滚动窗口、ESS、代表弧段；无估计器依赖 |
| tests/phase2_5_regression.c、test_phase2_5_analysis.py | 生命周期边界/只读深比较和独立合成统计测试 |

## 2. 最关键的当前观测依赖

`PPP_only/ppp_position.c:9` 的 `STD_PREC_VAR_THRESH=0`；`:297` 对正常P[0]>0的历元执行当期SPP。`src/pntpos.c:539–553` 从当期伪距写入SPP位置/钟差。`src/ppp.c:2034` 的 udclk_ppp 每历元重新以 `CLIGHT*sol.dtr[0]` 初始化公共钟差，方差 `VAR_CLK=60²=3600 m²`。每条真实GNSS行H都含公共钟差列。

所以即使时间标签是STABLE、观测弧段NORMAL_CONTINUOUS，成功SPP历元的x⁻也使用了当期z。Phase2计算仍准确等于实际filter前的 HᵀP⁻H+R；**这并不能自动保证该新息是独立时间预测误差或满足噪声学习的矩关系**。

- A首次P22786条：全部 `state_init_from_current_obs=1`，且 `state_init_affects_row=1`。
- B首次P22656条：22049条成功SPP直接影响该行；22191条x⁻存在某项当期观测初始化（含额外模糊度播种）。
- B另607条SPP尝试失败，初始化来源不能可靠确认。`estpos()` 可能在valsol失败前已写 sol.dtr；当前回退只恢复位置/时间，未恢复钟差。所以这些行 `provenance_valid=0`，不能将 `state_init_from_current_obs=0`解释为独立预测已获证明。607与22191存在重叠，不能相加。

位置/速度若实际来自当期SPP则记录当期初始化；FIXED位置、固定ISB/RCB/加速度种子不冒充观测初始化。当前电离层初始化是IONEX/广播模型，**没有双频P差初始化**。大气产品/模型初始化的几何也可能间接使用当期SPP位置，这一限制仍需保守解释。模糊度由当前改正后的P/L播种，次频可能使用参考频P，真实执行点单独记录。Legacy共同P/L offset调整是另一类当期数据依赖，不冒充init。

本阶段没有修复/替换SPP或钟差过程模型；上述来源限制保留为后续方法设计的前置问题。

## 3. 生命周期与资格字段

原Phase2全部45个日志列保留。新增：

- `lifecycle_tags`：STARTUP/STABLE、ARC_INIT、ARC_RESTART、ARC_RECOVERY、POST_GAP、EDIT_RETRY、NORMAL_CONTINUOUS，允许多标签。
- `state_init_from_current_obs`：本次预测状态中任一状态实际用当期GNSS观测初始化；按用户要求，哪怕不在该行H支持内也排除。
- `state_init_affects_row`：该行H的非零项是否直接涉及被当期观测初始化的状态。
- `ambiguity_init_from_current_obs`：该卫星/频槽的实际模糊度播种事件；P行也记录，但P的H不含IB。
- `same_epoch_reentry`：trial>0或同GNSS时刻再次进入。重复不增加弧号/年龄/连续次数，即使携带slip/init。
- `arc_id/arc_age/continuous_epochs`：sat+slot+actual signal+P/L的**实际pre-fit行**连续轨迹。arc_age单位为GNSS秒；缺P只断P序列，缺L只断L；已知slip/reset/switch断相关分析弧。
- `raw_arc_id/raw_arc_age/raw_continuous_epochs/raw_lifecycle_bits`：只要原始P或L仍有效的共享信号轨迹，明确区别于创新行连续性。
- `gap_flag/signal_switch_flag`，`spp_from_current_obs/spp_attempted/provenance_valid`，`legacy_current_obs_adjustment`。
- `clock_m/clock_var/isb_m/isb_var/iono_m/iono_var/trop_m/trop_var/ambiguity_m`：调用filter之前的状态快照，状态单位m、方差m²；iono为垂直参考L1电离层延迟，trop为ZTD。不能把钟差m当秒。
- `observer_learning_label`：任一当期初始化时直接为NOT_ELIGIBLE_FOR_R_LEARNING；其他情况UNASSESSED，绝不表示已获学习资格。

STARTUP=[首输入时间,首输入+30s)，其后STABLE只是时间分层，**没有实施收敛判据**。C观察器gap>1.5s针对当前1Hz回放；离线分段还要求相邻输入epoch和实际时间步长（本次median=1s，容差1%），不跨missing epoch拼接。日志仍为单实例/单回放观察器。ARC_RESTART是诊断断弧标签，不意味着本阶段修复了B历史弧段算法；真正的播种由独立init字段证明。

最终逐行资格在 `validation/phase2_5/annotated_innovations.csv`：

ELIGIBLE_CANDIDATE；INELIGIBLE_STARTUP、ARC_INIT、SLIP、GAP、REJECT、RETRY、CURRENT_OBS_INIT、PERSISTENT_BIAS、CONSTRAINT、IFLC、OTHER。

资格为多理由集合，计数可重叠。OTHER进一步注明来源未知、非有限/非法创新、未提交历元、信号未知/切换、inactive状态、L不进入第一阶段池、B历史随机模型/处罚/平滑等原因。INELIGIBLE_PERSISTENT_BIAS是临时候选证据标签，未确立最终偏差门限。

## 4. 均值、同号比例与学习前置矩验证

只取FIRST_PREFIT；所有有效真实观测均进入描述统计，包括原算法随后拒绝的行。STARTUP和STABLE分别计算N、mean/median/std/RMS(v)、mean/median/std(u)、正/负/零比例。std为样本标准差(ddof=1)；用于矩分解的Var(v)为1/N的样本均值中心化二阶矩，二者明确区分。

稳定伪距摘要（完整含startup/L统计见 INNOVATION_LEARNABILITY_STATS.csv）：

| 基线 | 星座/实际信号 | N | mean(v)/m | median(v)/m | std(v)/m | 负号/% | mean(v)²/m² |
|---|---|---:|---:|---:|---:|---:|---:|
| A | C 2I | 7879 | -10.362 | -1.202 | 26.842 | 54.06 | 107.37 |
| A | C 7I | 591 | -15.760 | -6.964 | 26.864 | 67.34 | 248.36 |
| A | E 1C | 3819 | -3.483 | 0.395 | 51.058 | 48.44 | 12.13 |
| A | E 5Q | 3410 | -8.472 | 0.963 | 25.411 | 45.43 | 71.78 |
| A | G 1C | 3230 | -11.428 | -1.809 | 27.275 | 57.09 | 130.60 |
| A | G 5Q | 2850 | -8.713 | 0.704 | 25.420 | 45.72 | 75.91 |
| B | C 2I | 7879 | -19.059 | -8.378 | 27.807 | 77.47 | 363.26 |
| B | C 7I | 483 | -23.078 | -14.398 | 26.958 | 87.58 | 532.58 |
| B | E 1C | 3815 | -8.621 | -5.792 | 51.133 | 74.52 | 74.33 |
| B | E 5Q | 3410 | -13.567 | -4.668 | 25.427 | 70.91 | 184.07 |
| B | G 1C | 3229 | -18.018 | -8.178 | 26.595 | 85.88 | 324.63 |
| B | G 5Q | 2850 | -15.407 | -5.795 | 25.034 | 78.67 | 237.39 |

B C7I P负号占87.58%、G1C P85.88%、C2I P77.47%；A部分组mean为负而median略正，说明不能只看组均值判断“整条弧一直有偏差”。需结合具体弧段、同号窗口和公共变化。高相关/当前观测条件化使IID均值显著性检验不成立，本报告使用“非零均值迹象/候选证据”，不作统计显著性断言。

按每组/每完整窗口记录：A=mean(v²)，B=mean((v-mean(v))²)，C=mean(pred_var)，候选1=A-C，候选2=B-C；二者差=A-B=mean(v)²。12个稳定伪距组均有A-C<0且B-C<0。mean(pred_var)约3600–4130m²，mean(v²)约717–2688m²；**不能将负数裁到小正数以强行更新R**。这表明当前直接套用矩估计的前提未建立；并非说明观测真实噪声为负，也不是调Q的依据。

## 5. 连续弧段相关性与旧0.996复核

只对STABLE、NORMAL_CONTINUOUS、FIRST_PREFIT真实观测做时间分析。按数据集/基线/sat/slot/actual signal/P-L/arc拆段；缺行、时间步不连续、slip/reset/init、signal switch、reject/reentry都断开。仍保留当期初始化或来源未知的行用于**解释相关性**，它们不会因此获得学习资格。

对段a自己的完整段均值μa，定义Ck=ΣaΣt(y[a,t]-μa)(y[a,t+k]-μa)，分别积累两侧平方和Ek,left/Ek,right；rho(k)=Ck/sqrt(Ek,left*Ek,right)。没有跨段配对，也不混用不同星的均值。这是明确的逐段中心化、归一化lag交叉乘积诊断；不冒充以完整段总方差作分母的biased ACF。v和u均计算lag1/2/5/10/30，并记录每lag有效配对数。

| 基线 | 伪距信号 | 连续诊断N | 最大连续长度 | rho_u(1) | rho_u(2) | rho_u(5) | rho_u(10) | rho_u(30) | ESS_u近似 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A | C 2I | 7798 | 570 | 0.9543 | 0.9069 | 0.8383 | 0.7286 | 0.3659 | 463.22 |
| A | C 7I | 586 | 434 | 0.9496 | 0.9099 | 0.8560 | 0.7557 | 0.4272 | 32.81 |
| A | E 1C | 3769 | 570 | 0.9432 | 0.8846 | 0.7976 | 0.6623 | 0.2656 | 298.91 |
| A | E 5Q | 3380 | 570 | 0.9431 | 0.8867 | 0.8056 | 0.6744 | 0.2850 | 265.71 |
| A | G 1C | 3202 | 409 | 0.9501 | 0.8997 | 0.8189 | 0.6896 | 0.2864 | 168.96 |
| A | G 5Q | 2848 | 570 | 0.9590 | 0.9169 | 0.8523 | 0.7458 | 0.3936 | 95.34 |
| B | C 2I | 7331 | 570 | 0.9486 | 0.8962 | 0.8193 | 0.7030 | 0.3127 | 626.78 |
| B | C 7I | 351 | 130 | 0.2259 | 0.4040 | 0.4727 | 0.4864 | 0.1703 | 47.54 |
| B | E 1C | 3695 | 570 | 0.9533 | 0.9055 | 0.8353 | 0.7166 | 0.3118 | 176.75 |
| B | E 5Q | 3406 | 570 | 0.9536 | 0.9068 | 0.8398 | 0.7346 | 0.3778 | 137.68 |
| B | G 1C | 3202 | 409 | 0.9529 | 0.9051 | 0.8320 | 0.7122 | 0.3071 | 155.24 |
| B | G 5Q | 2850 | 570 | 0.9586 | 0.9164 | 0.8528 | 0.7503 | 0.3967 | 73.34 |

完整rho_v与rho_u/有效配对/弧长分布见CORRELATION_STATS.csv。B C7I P 351行拆为113段，多数1–2行，最大130行；其ESS只覆盖179行，不能将表中47.54解释为全部351行的有效独立样本数。

### 旧E26 1C L的固定支持对照

| 基线 | 旧支持pairs | 旧pooled Pearson(u) | 共同严格支持pairs | 同支持pooled | 同支持逐弧中心化 |
|---|---:|---:|---:|---:|---:|
| A | 245 | 0.996129 | 207 | 0.996109 | 0.708021 |
| B | 249 | 0.996134 | 207 | 0.996105 | 0.696434 |

严格E26 1C L轨迹两组各44段，最大连续37行；旧245/249pairs不是一条完整连续长弧。旧Phase2虽然没有直接跨gap配对，仍将不同弧段的均值放在一个Pearson统计中。固定支持的对照显示中心化口径会明显改变该数值，**不能把旧0.996当作单连续弧段噪声rho，更不能据此推导eta公式**。这是统计口径细化，不是滤波修复或精度变化。

自动选择高|rho1|组的强相关弧、最长弧及旧E26/G32来源弧，共71段。完整time/v/u/Rii/pred_var/Sii/CN0/elevation/age/clock/iono/trop序列见本地 `validation/phase2_5/representative_arcs.csv`；摘要在REPRESENTATIVE_ARC_EVIDENCE.csv；E26实际逐行案例另保存在PHASE2_5_E26_ARCS.csv。

代表E26 1C L：epochs81–117为37行，A/B mean(v)=-7.546/-10.854m；epochs340–363为24行，A/B=-65.677/-72.838m。后一段linear drift=-0.369/-0.393m/s，段内rho_u1=0.896/0.906，prediction share=99.9997%/99.9921%。

该后段v与CN0关联约0.504/0.506，与高度角0.848/0.860，与clock_m0.848/0.860；与iono/trop也有共同变化，Rii区间A0.00964–0.01360m²、B0.24103–0.34008m²。另有前半/后半方差、R范围、状态方差范围、同号streak等摘要。它们分别提供慢漂、同号bias、方差变化、CN0/高度角同步和P/R贡献证据；趋势未去除、变量存在公共时间变化与初始化依赖，**不能区分其因果来源已经被证明**。prediction share/R share只说明模型里的方差组成，并不证明真实噪声校准。

## 6. 10/30/60窗口持续偏差候选

滚动统计仅在上述真实连续诊断段内进行，不跨缺行或断弧。每个完整窗口记录mean/median/std(v)、mean(u)、sign persistence、连续同号次数、二阶矩/中心化方差/pred_var和差异。

候选选择仅为“完整窗口所有v同一非零符号”，目的为选取可检查的证据；未设置最终sigma/MAD/绝对米数偏差门限，未进行实时分类控制。平滑、漂移、公共钟差变化也能产生这些窗口，不等于已证明接收机测量偏差。

| 窗口/epochs | 完整窗口数（P/L合计） | 全同号候选窗口数 |
|---|---:|---:|
| 10 | 60962 | 41285 |
| 30 | 52803 | 19459 |
| 60 | 44064 | 8029 |

PERSISTENT_BIAS_CANDIDATES.csv按“真实连续段×窗口长度”汇总可审查候选，包含全部窗口端点数量与同号比例、rolling mean/median范围、最大streak及代表窗口矩分解。每一个端点的完整统计保存在本地 `validation/phase2_5/rolling_window_evidence.csv`，并非丢弃非候选窗口。

持续偏差候选标签只出现在窗口有完整支持的端点；它不是已确立的永久质量标签，更不会进入滤波历史。L只作对照观察。

## 7. ESS与分组是否足够

每段按dense lag1..min(30,N-1)计算rho。有限长度权重(1-k/N)，依次检查相邻正相关对(1,2)、(3,4)…，首个加权对和非正时截断；tau=max(1,1+2Σ(1-k/N)rho_k)，ESS=clip(N/tau,1,N)。这只是明确实现的有限lag诊断近似，不称其为正式完整Geyer算法，不向更长lag外推，也不产生eta更新公式。

例如G5Q P：A名义2848、ESS_u≈95.34；B2850、≈73.34。段间求和仍隐含“段相互独立”的未验证假设；公共SPP钟差也可能使不同卫星同时间相关。因此这些数值不是已证明的独立样本数、置信区间或有效自由度。趋势/非平稳进一步限制ESS解释。

已有数据足以描述每个signal的行为和暴露风险；当前不足以证明任一分组可以进行噪声学习。尤其短弧/稀疏信号的lag30和60历元滚动窗口支持不足。合并不同星座/实际信号/频率不会消除公共偏差、当期初始化或相关性，本阶段保持原细分，只报告不足。

## 8. 严格回归与测试

Release x64构建成功。下表比较最终版本与保留的4715448程序：

| 输入/基线 | 共同/有效历元 | Q5/Q6 | reject | detector slip | 坐标/状态/事件 |
|---|---:|---:|---:|---:|---|
| TXT fast A | 600/600 | 2/598 | 0 | 127 | 全部一致 |
| TXT fast B | 600/600 | 2/598 | 602 | 99 | 全部一致 |
| RINEX A | 1200/1200 | 3/1197 | 5 | 637 | 全部一致 |
| RINEX B | 1200/1200 | 3/1197 | 22 | 502 | 全部一致 |

TXT同时比较诊断关闭/开启：数值CSV（除walltime）逐字段一致、XYZ最大差0m、Q/ns差0，.stat/.obs.csv字节一致，$PPP_STATE全部一致，reject/slip/arc/failure计数一致。RINEX输入时间记录、结果数值、.stat字节和事件统计一致。所有失败历元为0。

另外A/B Phase2原45个创新CSV字段逐行字符串完全一致，包括v、R、pred_var、Sii、u和旧观测身份；只追加诊断标签。src/rtkcmn.c没有改动。

- Phase1 C：44/44通过。
- Phase2 C：26/26通过。
- Phase2.5 C：20/20通过。包括首初始化、连续P-only、编辑/同时间重入、同时间slip/init去重、gap/switch/missing、模糊度实际seed、失败SPP未知、legacy调整、缺P不影响L、rtk结构与x/P/H深度bitwise只读。
- Phase2.5 Python：31/31通过。包括手算矩、正负零比例、分阶段、多理由资格、P-only池、B历史R、重试/缺行/信号返回断弧、lag30支持、滚动窗口与0符号、ESS、两弧均值混合伪高相关、结果可复现与有限JSON。

命令：

```powershell
./tests/run_phase1_tests.ps1
./tests/run_phase2_tests.ps1
./tests/run_phase2_5_tests.ps1
python tests/test_phase2_5_analysis.py
python tests/run_phase2_5_replay.py
python tests/run_phase2_5_rinex.py
python tests/analyze_phase2_5.py
```

回放依赖本机产品路径和被保留的4715448参照exe。原始观测、产品、exe和完整运行明细不入Git；证据JSON包含所有输入/输出/源码哈希，测试输出在PHASE2_5_TEST_RESULTS.txt。所有配置与数值失败保护保持原样。

## 9. 产物与未启用内容

- PHASE2_5_REPORT.md：本报告。
- INNOVATION_LEARNABILITY_STATS.csv：44阶段分组的矩、比例、排除理由/候选计数、结构样本对照。
- PERSISTENT_BIAS_CANDIDATES.csv：10/30/60窗口候选证据摘要。
- CORRELATION_STATS.csv：逐弧rho_v/rho_u五种lag、连续样本支持与有限lag ESS。
- REPRESENTATIVE_ARC_EVIDENCE.csv、PHASE2_5_E26_ARCS.csv：代表弧摘要与旧高相关来源逐行案例。
- PHASE2_5_EVIDENCE.json、PHASE2_5_TEST_RESULTS.txt：复现证据和测试结果。
- validation/phase2_5：全量逐行资格、滚动窗口、代表时序、每段统计与旧rho固定支持对照。

本阶段没有启用Huber/IGG、任何R/Q修改、eta更新、新reject、坐标调整、信号合并或C/D算法。学习资格标签没有被PPP消费。后续首先需要解决/验证独立预测与当前SPP/初始化条件化的关系，再讨论学习公式；本阶段到此停止，等待确认。
