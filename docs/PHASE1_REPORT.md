# Phase 1 实施与回归报告

日期：2026-10-08。工作目录：`E:\GNSS\PPP_only`。本阶段只实施基础修复和 A/B 拆分，未实现 C/D 算法。

保护记录：开始时 HEAD=`97a57a92552d6d7efe7c855c82b9809e28a5bd17`，未提交内容只有 `docs/` 审计产物；未丢弃任何修改。历史源码保留在 `legacy/current-robust-97a57a9` 标签，原可执行文件保留在 `validation/phase1/PPP_only_97a57a9.exe`。实施分支为 `codex/phase1-baselines`；原 `main` 和旧工作目录未改写。审计文档单独提交为 `e634352`，其中行号仍指向审计前源码；本报告行号指向 Phase 1 源码。

## 1. 实际修改文件和函数

| 文件 | 函数/位置 | 修改 |
|---|---|---|
| `src/rtkcmn.c` | `numeric_finite` 1459，`numeric_covariance` 1466，`filter_reason` 1482，`filter_` 1497，`filter` 1520 | 有限性、协方差基本有效性、失败原子性；保留原算式和运算顺序 |
| `src/ppp.c` | `varerr` 881，`invalidate_arc_ppp` 994，`ppp_input_failure_arcs` 1012，`udbias_ppp` 2308 | 防止 R0 下限吞掉 NaN；旧弧失效、pending、重建；拒绝输入中的已确认 LLI 事件仍保留 |
| `src/ppp.c` | `detslp_ll` 1511，`detslp_gf` 1547，`detslp_mw` 1603，`precheck_obs_ppp` 1678 | 实际检测证据、持续历史、GF 仅向已执行 Doppler 检测让渡、时间 gap |
| `src/ppp.c` | `signal_weight_ppp`、`prepare_signal_quality_ppp`、`doppsm_factor`、`statistical_model_ppp`、`udtrop_ppp`、`udiono_ppp` | 统一策略控制经验定权、质量学习、平滑和实验性先验 |
| `src/ppp.c` | `apply_legacy_robust_ppp` 2908，`reject_postfit_ppp` 2924，`ppp_res` 2928，`pppos` 3807，`update_stat` | 分开 R0、历史层、当期抗差与拒绝；数值失败、预测回滚、后验提交检查及状态日志 |
| `PPP_only/ppp_position.c` | `rtkinit`、`startup_qc_enabled` 201，`rtkpos` 241 | 初始化失败原因，输入边界保护，NaN/Inf 整历元拒绝，连续历史保存，失败返回 0 |
| `src/rtklib.h` | `prcopt_t` 1105，`ssat_t` 1264，`rtk_t` 1303，数值诊断声明 1508 起 | 模式/生命周期、pending/reset/证据、失败原因字段与接口 |
| `src/smartphone_ppp_config.h/.c` | `smartphone_ppp_policy` 20，`smartphone_ppp_select` 38，`validate` 91，`describe` 122，`log` | 唯一 A/B 策略来源，明确拒绝 C/D，秒单位 ARCGAP，有效配置日志 |
| `src/rnx2rtkp.c` | `main` 配置校验前，`help` | TXT/RINEX 共用模式选择环境变量和帮助说明 |
| `README.md`、`tests/`、本报告及证据 JSON | 构建、测试和运行入口 | 可重跑的回归、冻结的有限数据旧滤波参考、哈希和实测结果 |

没有修改 `filter` 的更新公式，没有删除 B 的算法，没有新增自适应过程。

## 2. 两个 Critical 修复

### C01：NaN/Inf 假成功

原 `filter_` 只用矩阵求逆状态判断成功。创新 `v` 不参与创新协方差的求逆，因此 NaN 创新可在求逆成功后产生 NaN 后验，但仍返回 0；随后 `NaN > THRES_REJECT` 为假，验后编辑也可能通过。

现行为：

- 输入检查 `x/P/H/v/R`；计算后的创新协方差、后验 `xp/Pp` 也检查。
- `ppp_res` 在残差和方差形成处发现非有限值立即返回负错误码；调用者区别 `<0` 数值失败、`0` 无观测/编辑未通过、`>0` 接受。
- `pppos` 提交前复核 `xp/Pp`、本次实际使用的 `v/H/R` 和重算的验后残差。
- `varerr` 原先的 `MAX(NaN,floor)` 会选择方差下限，现将异常传播给失败检查，不用 0 或方差下限掩盖。
- 原始 NaN/Inf 观测被整历元拒绝；有限但超出原输入范围的观测仍按原筛选规则处理。
- 所有非有限失败均输出 Q0，不提交后验，`rtk->ppp_failure` 与 `$PPP_FAILURE` 给出 `NAN_INPUT/NAN_STATE/NAN_COV`。这些标签同时涵盖 Inf；另有 `BAD_COV/BAD_DIM/NO_ACTIVE_STATE/NO_VALID_OBS/EDIT_LIMIT/SINGULAR_INNOVATION_COV`。

### C02：confirmed slip 后旧 ambiguity 存活

原逻辑先检查 bias seed，再决定 reset。缺 P 时 seed 为 0，旧模糊度仍活跃；下一历元 slip 清除后旧弧继续使用。

CORRECTED 生命周期在尝试形成 seed **之前**清空模糊度和 P 的对应整行/列，设 `ppp_arc_pending=1`。新 seed 不可用则保持 `x=0/P=0`，相位方程不能使用旧弧；后续有限 P/L 和模型足够时才初始化新弧、清除 pending。LLI 标记但无相位值，以及因 NaN 被拒绝的输入包内明确的 LLI_SLIP，同样使旧弧失效。数值回滚也不能恢复已确认失效的旧弧。

诊断为 `$ARC_RESET`、`$ARC_PENDING_INIT`、`$ARC_REINITIALIZED`。B/LEGACY 显式保留原缺码旧弧行为，用于历史复现；A 与 B+CORRECTED 使用修复，C/D 当前不可运行。

## 3. GF 历史与执行证据

CORRECTED 生命周期在 `rtkpos` 中持续保存有效相位/时间，不再随 STARTQC 的 30 秒窗口关闭；缺相位时保留上次有效历史以识别中断。信号切换仍清旧历史。

先形成并执行原有单信号 Doppler 检查，再执行 GF。只有本历元两频的相位历史、Doppler 历史、时间范围和系统同伴数量都满足、且两条检查实际执行，GF 才能让渡。缺历史、缺同伴和缺 Doppler 都不能声明已经测试。没有引入新检测器或改已有 GF/MW/Doppler 门限。

`$SLIP_CHECK` 分别记录 `LLI_ADR/GF/MW/Doppler/gap` 和最终 slip；全为 0 就表示没有可用连续性证据。LLI_ADR 指输入 LLI 承载的事件，TXT 适配层的 ADR 转换未修改，也不代表本阶段验证了 JNI。

`-ARCGAP=` 是秒单位的连续性中断门限，默认 30 s；`maxout` 保持原来的缺测**历元数**，不把二者混用。时间倒退也中断旧弧。B/LEGACY 保留旧历史窗口和 GF-ready 让渡，B+CORRECTED 是单独的对照条件。

## 4. filter 失败保护与状态策略

`filter` 仅在 `info==0` 且后验检查通过时复制压缩后的状态/协方差。矩阵求逆失败的 `Pp_` 不再被读取；失败时传入的 `x/P` 保持逐位不变。

协方差检查：所有元素 finite、对角非负、基本对称性。对称容差为 `1e-7 * max(1,max(diag(P)))`，只检查，不对称化、不截断负方差。这不是完整 PSD 证明，也未改 Joseph 更新；正常接受数据仍为原 `(I-KH')P`。

PPP 状态策略：

1. 原始输入或卫星产品非有限：不进行测量提交，保留已有有限状态及必要弧段失效事件。
2. 预测有效、测量更新/验后失败：保留本历元有限预测（含固定 Q、合法初始化和弧段重启），输出 Q0；不把预测称为成功后验。
3. 预测本身非有限/非法协方差：回到 `udstate` 前的可信状态快照，恢复产品先验消费时间；已确认旧弧再次清空并保持 pending。

同历元每次残差编辑仍从同一个预测开始，只提交一次通过验后的测量更新。新增数值日志和检查使运行时间增加，不用墙钟时间比较算法数值结果。

## 5. A/B 最终定义与 R 分层

| 项目 | A：CLEAN_BASELINE | B：LEGACY_BASELINE |
|---|---|---|
| 默认选择 | `RTK_PPP_BASELINE=A` | 未设变量或 `RTK_PPP_BASELINE=B` |
| 弧段/历史 | 始终 CORRECTED | 默认 LEGACY；显式 `RTK_PPP_LIFECYCLE=CORRECTED` 可对照 |
| 函数模型、产品改正、实际信号筛选 | 保留 | 保留 |
| 基础 R0 | 固定的既有基础式、el/CN0 参数和模型方差 | 保留历史基础式及可选旧随机模型 |
| 固定 Q | 保留现有固定过程噪声 | 原样保留 |
| residual/持续/CMC 抗差与质量学习、quarantine | 关闭 | 全部保留其原启用条件 |
| 实验性平滑、额外码方差、BDS warm 权重、共同码相偏移保护 | 关闭 | 保留 |
| STARTQC 的实验性 SPP/空间/码相门限 | 关闭；必要输入安全检查保留 | 保留 |
| IONEX/VMF3 初始产品先验及持续虚拟观测 | 关闭；使用原 SBAS/BRDC 粗初值 | 保留，包括 STATMOD=3 默认 |
| 确定性 VMF3 ZHD/mapping、天线/钟差/潮汐等 | 保留必要模型 | 保留 |
| 数值安全保护 | 开启 | 开启 |
| C/D、eta/R/Q 学习 | 不实现，eta=1 | 不实现，eta=1 |

A 的固定 R0 不是常数：它可以依赖当前高度角和 C/N0，但无在线学习或残差反馈。仍保留既有 `varerr` 基础式、星座/频带参数、C/N0 分段及码/相位基础下限；它不是声称完全回退官方原版 RTKLIB。可选 WGTELCN、SIGW、额外码膨胀在 A 中禁用。

模式在初始化前选择，每组使用新建的独立 `rtk_t`；不支持在运行中改 `rtk->opt` 并复用另一组的滤波或质量历史。当前 PC 两入口均按一次运行/一个初始化的模式执行。

分层位置：`varerr` 与模型误差组成 R0；`apply_legacy_robust_ppp` 隔离旧处罚；`reject_postfit_ppp` 独立保留原固定 8-sigma 验后拒绝门限。A 中 `w=1, eta=1, R_eff=R0`。

B 必须保留历史平滑及持续质量行为，所以额外显式记录 `legacy_random`（原 SIGW/码因子作用后的旧物理方差）、`legacy_time_add`（平滑随机模型附加）、`w_history`（CMC/持续质量处罚）与当期 `w`。其关系为：

```text
A: R_eff = eta * R0 / w                       (eta=1, w=1)
B: R_eff = (legacy_random + legacy_time_add) / w_history / w
```

B 实际实现继续使用原来的顺序乘法，避免改为除法引入舍入差异；不会把历史或平滑因素混称为当期 robust weight。B 的 `|res|/sqrt(R)` 与旧处罚不是新 C 组的 `S=HPH'+R` 标准化创新，也不能称为普通 EKF。

## 6. B 与 97a57a9 的复现结果

| 对照 | 共同输入/有效解历元 | Q | 坐标/状态差 | reject | 周跳检测日志事件 / SLIP 重建日志 |
|---|---:|---|---|---:|---:|
| TXT 原版 vs B/LEGACY | 180 / 180 | 两者 Q5=1，Q6=179 | CSV 除计时列完全相同；坐标最大差 0 m；`.stat` 字节相同 | 111 / 111 | 20 / 20；重建 20 / 20 |
| RINEX 原版 vs B/LEGACY | 1200 / 1200 | 两者 Q5=3，Q6=1197 | 全部数值输出行相同；`.stat` 字节相同 | 22 / 22 | 502 / 502；重建 501 / 501 |

TXT 的各组 `.obs.csv` SHA256 相同；RINEX 的 `rtkpos` 输入时间/观测数记录逐行相同。输入/产品和可执行文件哈希见 `PHASE1_EVIDENCE.json`。

“状态相同”指现有 `.stat` 输出项及其记录精度相同，不冒充每个未输出的 P 元素都已与旧程序逐位比较。有限滤波的最小标量/矩阵回归单独做了与冻结旧函数逐位比较。全数据结果只覆盖这两组输入，不能据此宣称所有异常输入也复现旧假成功。

## 7. 因修复或显式模式改变而变化的结果

- 人工 NaN/Inf 创新：从原来的返回成功并污染后验改为明确失败、不回写。NaN R0 不再被下限掩盖；求逆失败不再复制未初始化 Pp。这些是 A/B 共用的故意变化。
- A 与 B+CORRECTED：缺码 slip、长期中断、GF 错误让渡及持续相位历史均按新生命周期处理，不能要求继续产生旧弧结果。
- B+CORRECTED 的 180 历元均有解，Q/ns 未变化；相对原版最大三维坐标差 `0.06015606995 m`，reject 111→108，周跳检测日志事件 20→25。生命周期修复保留当前 slip 证据，还会改变 B 的持续质量诊断；此条件必须单独命名，不能混入 B/LEGACY 的历史复现结果。
- A 关闭历史算法后的坐标差来自定义变化，不用于评价“精度提高”。本阶段未使用真值，也未调 R/Q 参数以改善坐标。

## 8. 新增测试与实测结果

### 最小回归

`tests/phase1_regression.c` 44 项全部通过，完整名称和结果见 `PHASE1_TEST_RESULTS.txt`。

覆盖 NaN/±Inf innovation、正常标量与矩阵逐位旧函数对照、求逆失败、NaN P/Inf R/NaN H/Inf prior、负方差/不对称 P、有限输入算术溢出、后验状态溢出、无活跃状态；连续相位、完整 P/L slip、缺 P slip、下一历元仍缺 P、恢复 P/L、长 gap、outc 超限、缺 L 的 LLI、含 NaN 的 slip 包；B 旧弧/GF 恢复、GF 缺历史不让渡、实际 Doppler 成对归因、启动后历史保留；预测失败回滚仍断旧弧、无观测保留有限预测、post-fit NaN 与 R0 NaN；A/B 策略和实际处罚层、拒绝独立、秒/历元单位分离、C/D 拒绝。

### A PC fast 重复运行

两次均处理 180 历元、有效解 180、Q5=1/Q6=179；失败历元 0，所有输出数值 finite；CSV 除计时列一致，`.stat` SHA256 均为 `e20fcf314f201184fa522f87a4fe57b44e8daaac5ed359fbf25ca0730fb63d4b`。

末历元（GPS week 2437，TOW 195645.001000064）：

| 项目 | 数值 |
|---|---|
| ECEF XYZ (m) | -1332883.371554185，5325278.632981899，3237401.837651132 |
| 纬度/经度 (deg)，椭球高 (m) | 30.698161929889，104.052077024342，465.604859 |
| Q / ns | 6 / 17 |
| GPS 钟差状态 (m) | 45452.177539586242 |
| ZTD 状态 (m) | 2.223417338436 |
| 位置标准差 XYZ (m) | 0.557711，1.260992，0.559312 |
| ARC_RESET / ARC_PENDING_INIT / ARC_REINITIALIZED 日志数 | 33 / 14 / 54 |

重建数包含初始建立，pending 是历元日志条数，检测器日志事件也不是独立卫星弧总数，不混用这些分母。每次 20,682 条 R 日志（包含 pre/post 与编辑试算）均验证 `R_eff=R0,w=1,w_history=1,eta=1,legacy_time_add=0`。

回归脚本：`tests/run_phase1_tests.ps1`、`tests/run_phase1_replay.py`、`tests/run_phase1_rinex.py`。两个回放脚本含结果断言；本机产品未纳入仓库。原日志、CSV、状态和输入转储在 `validation/phase1/`，摘要已存入版本控制的证据 JSON。

构建验证为 Visual Studio 2022 Release x64；保留原编译器的其他文件警告，未验证 Debug/Win32、Android/JNI 或实时设备期限。

## 9. 尚未处理的 High/Medium

| 优先级 | 事项/位置 | 本阶段状态 |
|---|---|---|
| High | B 的 R-only 残差标准化及旧当期处罚：`apply_legacy_robust_ppp` / `ppp_res` | 保留历史算法；S=HPH'+R、Huber/IGG 等等待 C 独立实现 |
| High | B 的 CMC/持续/当期叠加处罚：同上 | 只分层、记录，未重设计 |
| High | IONEX/VMF3 缓变先验重复使用和相关性：`ppp_res` 虚拟观测分支 | A 关闭，B 保留；未建立新相关性模型 |
| High | 近似 VMF3 mapping 与正式 VMF3 b/c 的差异：`vmf3_mapf` / `trop_model_prec` | 未改模型 |
| High | TXT/RINEX 信号筛选一致性：`gnss_signal_policy.c` / `ppp_signal_supported` | 本次只验证各入口内部复现，未合并信号策略 |
| High | 产品到达时刻与真正实时可用性：`load_products` / `postpos` | 本次 fast/后处理验证不证明实时到达条件 |
| Medium | IFLC 实际选择频对一致性：`corr_meas` / `seliflc` | 默认非组合 PPP 回归未覆盖所有 IFLC 组合 |
| Medium | 非零状态活跃哨兵、固定 ISB/RCB Q、完整 PSD 检查 | 保留并明确限制；未改 Q、Joseph 或通用活跃状态设计 |
| Medium | VMF3 静态缓存、多实例/线程并发与反向滤波 | 未扩展验证 |
| Medium | 魔数的全面参数化、日志 IO 成本与性能优化 | 新 ARCGAP 和协方差容差已记账；其余按原魔数审计保留 |

待下一阶段明确确认后才能实现 C/D；本次没有 eta 学习、自适应 R/Q、新抗差算法、Joseph 默认化或基于真值的调参。

### Phase 1 新增数值参数账本

| 参数 | 数值/单位 | 来源与作用 | 配置性 |
|---|---|---|---|
| `PPP_ARC_GAP_SECONDS_DEFAULT` | 30 s | 明确命名的持续历史中断门限；与既有 1 Hz/30 历元使用条件一致，没有按真值调参 | `-ARCGAP=` 可覆盖；正且 finite |
| 基本对称容差 | `1e-7 * max(1,max diag)` | 新数值检查工程容差，非文献噪声参数；拒绝，不修补 P；不是 PSD 证明 | 通用数值层固定；若需调整应作为独立数值验证 |
| `eta` | 1，无量纲 | 不实现学习，仅在日志说明固定 R | 本阶段不可学习或调整 |

原 `MAGIC_NUMBER_AUDIT.md` 是 97a57a9 快照，以上增量不覆盖旧审计。
