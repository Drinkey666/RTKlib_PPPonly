# PPP 科研基线审计与实验拆分设计

## 0. 结论和审计边界

日期：2026-10-08。本轮完成源码审计、开题方案比对及三个最小故障探针；**没有修改生产源码、配置默认值、滤波器或现有可执行程序；没有实现 A/B/C/D 开关，没有实现 eta 学习；没有提交或推送此次文档。** 下述设计须用户确认后才实施。

审计项目为已上传 GitHub 的独立工程 `E:/GNSS/PPP_only`。当前客户端工作目录属于原复制工程；二者 `ppp.c` SHA256 相同。所有源码位置均相对独立工程根目录，行号是审计前源码的一基行号。原工程仍存在未提交修改，已记录在 [AUDIT_SNAPSHOT.json](AUDIT_SNAPSHOT.json)，未丢弃、暂存或覆盖。

主要结论：

- **Critical C-01**：NaN 新息可被 `filter()` 当成成功，PPP 提交前没有数值有效性检查。
- **Critical C-02**：周跳历元缺少可用初始化码时旧模糊度继续存活，下一历元又清除 slip，弧段事件丢失。
- **High H-01**：启动窗口后 GF 可能将跳变交给事实上无法执行的相位/Doppler 检测，造成周跳漏检。
- **High H-02–H-06**：R-only 残差标准化、跨历元处罚叠加、简式协方差与错误返回契约、大气相关先验、跨入口信号不一致，妨碍实验归因。

SNR `35×0.001` 回退错误、`var=0.005²/sin(el)` 覆盖全部相位方差、无条件 `var*=100`，**本次当前代码均未发现**。不能把用户提供的排查例子写成已发现错误。

### 审计前版本保护

| 项目 | 记录 |
|---|---|
| 独立仓库 | `E:/GNSS/PPP_only`，main，审计开始工作树干净 |
| 审计前提交 / B 历史参照 | `97a57a92552d6d7efe7c855c82b9809e28a5bd17` |
| 远端配置 | `https://github.com/Drinkey666/RTKlib_PPPonly.git`；本轮不操作远端 |
| ppp.c SHA256 | `3DD71F3B778E62D42149AD43A67037FB5105142C12CAD1118FC427B9B0BF3CC1` |
| 原复制工程 | `E:/GNSS/rtklib_only/rtklib_only`；含 `src/ppp.c`、工程改名、VS 缓存、构建产物和实验输出等未提交变化 |
| 保护方式 | 记录全部审计前 tracked 文件哈希、Git 状态和现有 exe 哈希；测试只写 `validation/audit`。建议确认后给上述提交建 `legacy/current-robust` 标签，修改在 `codex/baseline-split` 分支进行 |

记录提交不等于保证所有历史数据都被追踪；原工程未提交实验输出仍只在本地。本轮未替用户提交这些文件。

### 开题报告依据

已读取 `E:/大论文撰写/开题报告/智能手机实时PPP抗差自适应滤波开题报告_v6_原技术路线图版.docx` 的段落、表格和 OOXML 内容。以下定位用“表2行号”指 DOCX 第二张表的逻辑行，不冒充分页页码：

| 依据 | 内容 |
|---|---|
| 表2第25、31行 | 成对实验固定输入、产品、状态模型、Q；R0 按系统/信号/码相/高度角/CN0设置 |
| 表2第35–38行 | 标准化新息使用 S=HP⁻Hᵀ+R；同系统同信号共模检查；Huber，IGG-III独立对照；周跳重启；同一预测试算、一次提交、Joseph及数值检查 |
| 表2第39–41行 | 先当前抗差，再以合格历史新息更新下一历元信号级尺度；持续偏差冻结学习，周跳隔离 |
| 表2第42–45行 | 平滑与大气先验独立实验；A普通EKF、B已有抗差、C分层抗差、D在C上增加有界自适应，各组必要周跳预处理一致 |
| 表2第47–49行 | 独立会话、可核验异常标签、全部历元无解比例、覆盖率与新息统计 |

Android 工程按用户回复暂不审计。未对所有外部论文公式逐项重实现；只有代码中可确认的事实列为确定错误。

## 1. 当前 PPP 流程

完整入口和调用位置见 [PPP_CALL_CHAIN.md](PPP_CALL_CHAIN.md)。核心是：`rtkpos:320 -> pppos:3653 -> udstate_ppp:3711 -> ppp_res:3802 -> filter:3808 -> ppp_res(post):3815 -> 提交:3825 -> update_stat:3880`。

预测前已有换信号清历史、LLI/GF/Doppler/MW/启动码检查及 Doppler 平滑。R 在 `ppp_res` 内构造，既含测量/模型方差，也含历史降权和当前残差处罚。验后每次最多排除一条码或相位行，从同一预测重算，最多16轮；试算不是把同一观测连续提交16次。首次验后快照用于未来质量状态，最终快照用于输出。必要轨道、钟差、天线、相位缠绕、潮汐和码偏差改正仍存在。

当前默认由 `smartphone_ppp_config.c:12–46` 决定：静态、G/E/C、nf4、浮点、估电离层/ZTD、平滑0.90、PREPROC1、Doppler周跳0.50m、码跳30m、MW5m、隔离3次/120s。隐式默认 `STATMOD=3`（ppp.c:1174）、SIGQC=1（2614）、SIGQCPH=0（2618）、SIGCMCDRIFT=0（2694）、CODENOPH=1（2799），也属于 B 的行为。**B 不能设置 STATMOD=0 后声称复现“当前版本”**；那只是更早数值支路。

## 2. 确定错误与优先级

### C-01 非有限后验可被提交（Critical）

位置：`src/rtkcmn.c:1459–1477 filter_`、`:1485–1500 filter`；`src/ppp.c:3015,3054–3055,3108,3808,3825–3827`。

事实：`filter_` 只用 `matinv(S)` 的返回值判成功，新息 v 为 NaN 而 S 有限可逆时返回0，xp变NaN；`filter` 和 PPP 都不检查 xp/Pp 是否有限。验后 `z0>8` 对 NaN 为假，因而不能充当数值检查。模型函数也未统一拒绝 NaN。

实际源码探针：x=P=H=R=1、v=NaN，输出 `NAN_FILTER info=0 x_finite=0 P_finite=1`。这是有限状态输入经过一个非有限观测后的确定错误契约；不意味着此前正常数据已经发生坐标NaN，也不是“矩阵逆失败会被提交”（非零info路径已阻止提交）。

建议第一批修复：PPP方程检查 v/H/R 数值及正方差，提交前检查 xp/Pp 有限、P对称性/对角有效性；`filter` 非零info时禁止复制未定义的 Pp_（H-04）。不在此轮大改 filter/Joseph。错误防护使异常输入的行为改变，应记录修复ID；未修复历史提交永久保留，不能声称异常样本下逐位等价。

### C-02 周跳但缺码时旧弧继续使用（Critical）

位置：`src/ppp.c:1642 precheck_obs_ppp`（下一历元清slip）；`:2279,2293,2307–2315,2331–2334,2366–2391 udbias_ppp`；`:3007–3009 ppp_res`。

事实：周跳已记录在 slip，但因没有同频/参考初始化码、码被OSB过期/预检禁用，或模型不可用，bias[i]保持0。2366先 `continue`，2370的模糊度重建根本不执行；也没有先 `initx(...,0,0)` 断弧。ppp_res仍可使用旧非零模糊度。下一历元1642清slip后，事件无法保证重放。

实际源码两历元探针：旧B=100m；第1历元 LLI_SLIP=1、L有效、P缺测，输出 `ambiguity=100 variance=1 slip=1`；第2历元LLI=0、P恢复，新弧种子=-100m，却输出 `ambiguity=100 slip=0`。与开题表2第37行“明确周跳必须重启受影响弧段”冲突。

建议：检测到明确周跳立即清旧模糊度及相关，暂不具备种子时保持 inactive/待重建；种子恢复再初始化。原始事件单独保留到诊断和质量模块，不能用清过的slip作为唯一事件来源。各实验组共享基本修复，但保存历史B提交作精确回放。

### H-01 启动结束后 GF 检测让渡给未执行的检测（High）

位置：`PPP_only/ppp_position.c:325–335`（30s后清pt/ph）；`src/ppp.c:1635–1646`（再次清历史）；`:1525–1534 detslp_gf`（只查Doppler readiness即让渡）；`:1673–1676`（TD相位必须有ph/pt）；`:1708–1710`（组内至少3星才实际检测）；`:1568–1571`（MW同样依赖pt）。

因此30s后 Doppler 本身有历史，不等于相位/Doppler检验已执行；稀疏星座即便窗口内也可能让渡后没有足够同组证据。实际源码探针在第40秒，两频GF从0.25变1m、Doppler dt=1s，但pt/ph为0，结果 `slip_L1=0 slip_L5=0 phase_history=0`。LLI仍可独立起作用，所以不能声称全部周跳检测关闭。

建议先保证只有实际执行且能归因的检测才能让渡；是否启用全会话TD历史是另一个需标注的算法行为变化，不能悄悄纳入 B。

### H-02 当前抗差统计量不是开题标准化新息（High）

位置：`src/ppp.c:3038–3055,3088–3091,3108`。z0=|res|/sqrt(R_physical)，没有 hP⁻hᵀ；GPS钟白噪声、初始位置/模糊度宽松先验会使合法新息大于观测热噪声。当前处罚 p=min(25,(z0/4)²)，权 w=1/p；它与经典Huber的 w=min(1,k/|z|)不同，也没有IGG-III三段式。验后继续用R-only统计而非后验残差协方差，8σ不是经验证的检验概率。

B完整保留；A取消该残差处罚和实验性验后硬门控；C预留使用预测S、共模和Huber的入口，本轮不实现。不得把现有函数改名“Huber”并写成开题方法已完成。

### H-03 同一异常可能被多重处罚（High）

位置：`src/ppp.c:973,3040–3055,3079–3091,2631–2674,2688–2757`。

当前顺序（默认/可选必须区分）：

```text
R_meas = max(elevation_variance * C/N0_factor, floor) * SIGW
R_physical = R_meas * BDSCODEVAR * CODENOPH + trop + C²*iono + sat + GLO_IFB
z0 = |res| / sqrt(R_physical)
R_eff = (R_physical + positive_smoothing_inflation)
        * CMC_factor * persistent_factor * min(25,max(1,(z0/4)²))
```

SIGW默认1；BDSCODEVAR默认1；CODENOPH未配置时1；CMC默认关闭；SIGQC默认开、码weak乘4；相位历史自动降权默认关。启用CMC并已weak时，同码可能先×4，再SIGQC×4，再当前处罚至×25，共×400（不含可选固定倍率）；这是可能的路径，不是当前默认每条观测×400。历史处罚乘的是加完产品/大气后的总方差，并非只改热噪声。

CN0与当前残差不是同一证据；合理基础定权不应一概叫重复处罚。真正需消融的是CMC/历史残差/当前残差之间的证据重叠和延迟恢复，以及这些模块是否在无有效最终解时仍更新历史（3916只检查本地stat，最终Q可能0）。A关闭持续处罚/CMC/隔离；B保留并逐因子输出。

### H-04 filter 错误分支读取未定义协方差，且不是 Joseph（High）

位置：`src/rtkcmn.c:1463,1470–1474,1495–1500`。逆矩阵失败时filter_不写Pp，外层却无条件从未初始化的Pp_复制回P，这是确定错误分支。PPP使用试算Pp且3810 break，故正常PPP非零info路径不会把该垃圾P提交到rtk；其他调用者必须逐一检查。

正常P更新为 `(I-KHᵀ)P`，没有Joseph、对称化或有效性验证，与开题表2第38行目标有差距。简式继承RTKLIB，不自动等于错误；病态情况下风险高。先修失败复制/提交保护，Joseph作为明确版本化的后续共同数值实现，不借此重写整个filter。

### H-05 缓变大气先验以1Hz持续进入，相关性未建模（High）

位置：`src/ppp.c:1987–1992,2154–2158,3140–3209,3225–3262,3830–3833`；默认参数 `smartphone_ppp_config.c:12–13`。

IONEX默认interval=1s，下一1Hz历元information=1，基本等于每秒加入完整先验；同一GIM或相邻插值值不代表独立误差。每星先验之间也共享格网信息。VMF3默认300s，dt=1s时R=0.30²×300=27m²（无额外抗差），每秒仍追加一行，但已做信息折减。

STATMOD位2确实阻止初始化同历元重复使用，并只在成功提交后记时间；编辑试算也从同一P重来。因此不能笼统声称“16次编辑重复提交同一先验”。其信息预算是近似，不等于估计了产品真实相关时间；累计多分钟仍可能过度自信。旧STATMOD0路径初始化/约束可能同历元双计，VMF3在dt>interval时还可给予超过一份信息。暂不修改；A可关闭虚拟行，B保留；大气一致性实验另固定主滤波器。

### H-06 相同核心但入口采用信号集合不同（High）

位置：`src/pc_txt_replay.c:38–39`；`src/gnss_signal_policy.c:4–23`；`src/gnss_adapter.c:46–47,80–87`；`src/rtkcmn.c:689`；`src/ppp.c:259–260,293–296`。

TXT ppp-safe不让B1C进入，adapter通用映射把B1C与B1I放同槽0；RINEX和PPP则支持B1C槽3。默认nf4不意味着TXT有第四频。部分GAL 7I/7X能通过PPP前三槽检查，7Q默认被关闭；adapter ppp-safe只允许1C/5Q。实验必须保存实际采用 `(epoch,sat,code,type)` 清单，跨入口等价对照先用同采集的共同观测集合；不能仅核对配置hash。本轮不扩大准入范围。

## 3. 其他风险（不擅自修参数）

| ID / 优先级 | 位置及理由 | 处置建议 |
|---|---|---|
| H-07 VMF3名称与完整模型不符 / High | `ppp.c:498–507` 固定bh/ch/bw/cw，官方VMF3实现用位置与季节相关的b/c；这里只用VMF3格网a与延迟。对照[官方VMF3代码](https://vmf.geo.tuwien.ac.at/codes/vmf3.m)与[产品说明](https://vmf.geo.tuwien.ac.at/products.html)可确认实现差异，不能声称完整标准VMF3 | 标明近似模型；A/B保持同函数模型；完整替换需单独版本和对照，不在本轮静默改正 |
| H-08 仅按观测时标验证产品 / High（实时论证） | `gnss_replay.c:343–371,800–805` 全部产品预加载并检查覆盖，没有产品发布时间/实际到达时刻；`ppp.c:422–424` 允许用夹住时刻的第二份气象产品，是否实时可得未知；原默认产品有FIN字样 | 回放因果观测不代表实时产品可得，下一阶段记录发布/到达/有效区间；预报FC与事后OP/EI区分，见[官方产品说明](https://vmf.geo.tuwien.ac.at/products.html) |
| M-01 弧段事件过早清除 / Medium | `ppp.c:2391` 重建后清slip；`2645`检查obs.LLI或剩余slip，`2726`仅检查obs.LLI。GF/Doppler/MW事件可能不能触发质量/CMC历史清理；默认CMC关，相位处罚关 | 事件独立快照给诊断和未来学习资格；与C-02一起设计 |
| M-02 IFLC分支选频可能不一致 / Medium | `corr_meas:1108–1115` 优先实际槽1，否则槽2；`udbias:2295`与`rtkcmn.c:3748–3751 seliflc`对GAL nf≥3固定槽2，组合相位与slip关联可能不同；IFLC R使用近似×3而非实际组合系数传播 | 默认非组合未受此支路影响；本轮报告，后续限定研究入口为非组合，保留历史IFLC |
| M-03 零状态哨兵 / Medium | `rtkcmn.c:1486` x==0不估计；`ppp.c:1957,2155,2199,2338`用小非零激活。初始化保证，不代表所有后验都不会恰好到0 | 记录活跃状态判据，暂不改变压缩策略 |
| M-04 输入保护与配置耦合 / Medium | `ppp_position.c:248–250`清洗仅PREPROC/STARTQC同时开时执行；`ppp.c:2145,1476,3678`等直接用sat-1；rtkinit145–146有nf钳制，validate:56–58有检查 | 已验证正常两入口sat/count/nf约束；关质控或直接调用pppos缺统一边界保护，不能认定默认越界。将基础输入合法性保护抽为所有组共同项 |
| M-05 Q中有不可单独配置的经验值 / Medium | `ppp.c:1961` ISB0.10m/√s；2204 RCB0.01m/√s；1897用thresar[1]切加速度项；2177垂直电离层Q仍按1/sin(el)变化 | 固定系数不等于整个矩阵常数；A/B/C/D同Q公式与参数。配置化硬编码，但不标定/调优 |
| M-06 状态重置与时间异常 / Medium | `ppp.c:2231`按10Hz取整GPST午夜“钟跳”是继承的日界保护，不是实时观测钟跳检测；outc/maxout/gap均历元计数，dt为sol.time差；逆序用abs(tt)加Q | 报告epoch/s单位，主实验单向正序；不把maxout30称30s（仅1Hz近似） |
| M-07 全局产品缓存 / Medium | `ppp.c:317–319,399–404` VMF3为进程static，重新加载会影响其他rtk实例 | A/B并行实验用独立进程；Android另审线程安全 |
| M-08 失败输出不能只看返回1 / Medium | `ppp_position.c:340`总返回1；`gnss_replay.c:819–840`仍输出Q0坐标/协方差；Q5同时可指SPP回退或成功码更新 | 输出状态来源、失败原因、预测来源；评价用全部输入历元，按Q和来源分类 |
| L-01 死宏与注释 / Low | `ppp.c:121,127,129,137,165` THRES_MW_JUMP/VAR_ZTD/VAR_DCB/ERR_CBIAS/EFACT_GPS_L5仅定义，实际阈值由别处给定 | 文档区别“存在宏”与“实际生效”，不本轮删除 |
| L-02 可运行范围 / Low | 既有验证是VS Release x64；vcxproj存在Win32/Debug条目但配置依赖未等价核实 | 后续声明已支持构建，不扩大测试或声称Android已可构建 |

## 4. 非原始逻辑逐项清单

判定参照为[官方 RTKLIB v2.4.3-b34 ppp.c](https://raw.githubusercontent.com/tomojitakasu/RTKLIB/v2.4.3-b34/src/ppp.c)。此仓库含其他分支风格的扩展，不能仅凭RTKLIB头注释认定完全原版。表中“历史”只说明相对官方存在差异，不推断作者、日期或正确性；目的按代码解释，效果未经真值实验确认。

### 4.1 代码事实与目的

| ID / 项目 | 文件 / 函数 / 行号 | 当前逻辑与目的 |
|---|---|---|
| N01 CN0定权 | ppp.c varerr 964–973；联合模型922–956 | 分段方差×1/2/4/8/12，缺CN0×4；联合模型可选，成功直接返回，不再叠加分段因子；用于手机低CN0降权 |
| N02 高度角 | ppp.c varerr 911–914 | a²+b²/sin²(el)，最低5°；联合模型夹10–90°；几何相关基础误差 |
| N03 码额外倍率 | ppp.c signal_weight_ppp 842–868；ppp_res 2810–2833、3040–3045 | SIGW实际信号倍率，BDSCODEVAR及渐变，CODENOPH无相位卫星倍率；默认均1，不是无条件×100 |
| N04 相位方差 | ppp.c varerr 956/973；ppp_res 3038–3050 | 最低0.01²m²，仍加卫星/大气方差；不存在0.005强制覆盖 |
| N05 残差penalty | ppp.c ppp_res 3054–3091 | R-only z0>4时平方处罚，至25；抑制当前异常影响 |
| N06 Huber/IGG | ppp.c ppp_res 3088–3091 | 没有经典Huber或IGG；上述平方倍率不能等同论文Huber |
| N07 pre-fit拒绝 | ppp.c precheck_obs_ppp 1624–1742；precheck_startup_code_ppp 1761–1828；ppp_position.c sanitize 209–236；pntpos.c startup_fde 615–655 | 时间差码跳、启动同signal/MAD门控及SPP启动排除；ppp_res中不使用maxinno作为GNSS prefit阈值；信号/产品/几何筛选在2924–2950 |
| N08 post-fit拒绝 | ppp.c ppp_res 3108–3117、3274–3305 | z0>8按z排序每次拒绝一行，mexc保留其他信号；16轮；可选未来历元相位隔离3330–3387 |
| N09 周跳 | ppp.c detslp_ll 1469；detslp_gf 1502；detslp_mw 1550；precheck 1673–1715 | LLI/半周状态变化、GF、MW及相位-Doppler；共模按系统聚合而非全部同signal；窗口后的历史缺失见H-01 |
| N10 ambiguity reset | ppp.c prepare_signal_quality 1425；reset_ambiguities 1217；udbias 2248–2267、2366–2391；quarantine3387 | 换signal/中断/日界/warmup切换/隔离/可初始化周跳清相关；缺种子周跳存在C-02 |
| N11 Hatch / Doppler平滑 | ppp.c uddoppsm 1269–1346；applydoppsm 1352；warmup1235 | 当前是因果Doppler平滑，不是Hatch相位平滑；α=factor^dt；共享D样本的方差交叉项；保留rawR下限，可选相关膨胀；warmup默认0 |
| N12 IONEX约束 | ppp.c ionex_vertical_prior 2083；udiono2154；ppp_res3140–3209 | 垂直L1米状态初值/每星虚拟先验，sigma至少1.5m；先验冲突平方处罚至25 |
| N13 VMF3/ZTD约束 | ppp.c vmf3_trop495；ppp_res3225–3262 | 用格网a/ZHD和近似映射；ZWDproduct-(ZTD-ZHD)虚拟行，sigma0.30m、间隔300s、冲突×25 |
| N14 电离层虚拟行 | ppp.c ppp_res3149–3172、3184–3188 | 一颗卫星一行H[II]=1，每历元重复应用（初始化历元默认不双计），没有按每频复制 |
| N15 ZTD初值 | ppp.c udtrop1973–2005；vmf3_init_sigma526 | 优先ZHD+ZWD，profile sigma0.15m；否则SBAS天顶；不是每秒强制覆盖ZTD |
| N16 Q | ppp.c udpos1862/1921；udclk1961；udtrop2009；udiono2177；uddcb2204；udbias2364 | prn²×abs(tt)，ISB/RCB经验随机游走；电离层随高度角；未见在线Q学习 |
| N17 数值保护 | ppp.c initx981；varerr911/973；udpos1877；pppos3808；ppp_position145–146/209 | 先验重置、方差下限、边界钳制、失败不提交；基本保护与实验降权不同，但NaN保护缺口C-01 |
| N18 经验阈值 | 上述函数及MAGIC_NUMBER_AUDIT | 抗差4/8/25、码30、Doppler0.5、GF0.2、MW5、启动30s、隔离、质量迟滞等；未见本项目独立标定证据 |
| N19 持续残差质量 | ppp.c signal_quality_step2582；update_signal_quality2631；persistent_variance_factor2611 | 同system+signal+type至少5星，去中位/MAD，5坏≥4s进入weak、10好≥9s恢复；码×4，相位默认仅监测；不是eta估计 |
| N20 CMC质量 | ppp.c update_cmc_quality2688–2757；ppp_res3079 | 可选CMC漂移迟滞，下历元码×4；默认关，CMC混有电离层/偏差/模糊度，非纯噪声 |
| N21 码偏差与信号模型 | ppp.c corr_meas1074–1095；ppp_ifb_index245；udclk1937；rtkcmn681 | 按sat+code+epoch使用码OSB，过期禁码；RCB五状态、GPS+ISB钟模型、B1C槽3；是当前必要函数模型，不因“非原版”而删除 |

### 4.2 来源、开题关系、重叠和分组

| ID | 标准RTKLIB / 当前历史差异 | 与开题方案关系 | 重复加权/处罚 | 分组建议 |
|---|---|---|---|---|
| N01 | b34基础没有此分段或联合CN0；历史扩展 | 可作为预先固定R0；联合系数设备依赖，不能冒充新自适应 | 与残差质量可能同受遮挡，但非同一统计证据 | A/B共享选定固定R0；联合模型单独消融；C/D继承 |
| N02 | a²+b²/sin²为标准家族；角度夹限/联合路径历史 | 基础定权符合；参数固定 | 不与大气映射简单判为重复 | A/B/C/D共用 |
| N03 | 历史额外倍率 | 任意经验渐变不符合干净A；固定标定SIGW可归R0 | 可与N01/N05/N19叠加 | A禁BDS/CODENOPH额外处罚；B全部保留可恢复 |
| N04 | 标准方差模型上加历史下限 | 未发现覆盖错误；下限需标定来源 | 与N01是同一基础模型里的下限，不是追加次数 | A/B共用已声明R0，不静默调相位参数 |
| N05–06 | 当前历史平方处罚，非标准Huber/IGG | 与拟议C统计及权函数不同 | N19/N20后再罚；postfit再拒绝 | B；A关；C/D接口预留 |
| N07 | 基本健康/信号门控标准；启动/码跳/MAD为历史 | 部分诊断方向符合，尚非完整分层方案 | 码跳与残差门控可能同异常双决策 | 所有组共用合法性/必要弧质控；实验码门控B保留A关 |
| N08 | 官方有验后编辑，当前改阈值/按行/z排序及隔离 | B已有方案；C需新统计 | 与N05快速降权、N19历史处罚相关 | B保留；A仅合法性/数值失败拒绝，残差门控按协议另记 |
| N09–10 | LLI/GF/MW/重建家族标准，历史加归因/半周/Doppler等 | 必须同组共用必要预处理；C-02冲突 | GF/MW让渡不是叠加R，但漏检 | 基本修复共同；精确旧B另存；隔离/warmup属于B |
| N11 | 历史平滑/STATMOD/warmup | 开题要求独立平滑相关实验 | 历史复用产生时间相关，rawR下限不能消除 | 干净A主试验关闭；B完整保留；相关实验另轴固定主组 |
| N12–14 | 官方有TEC模型；此垂直EST和虚拟约束历史 | 开题要求独立大气一致性实验 | 同源初始化和约束/1Hz相关风险H-05 | A关闭虚拟行；B保留；函数状态语义各组一致，单独登记初值政策 |
| N15 | VMF初值历史；SBAS回退标准家族 | 初值/P不同可改变启动归因 | STATMOD3已防同历元双计 | A/B共同初值须选定记录；B历史产品初值始终可恢复 |
| N16 | 多数prn传播标准家族；ISB/RCB等历史 | 固定Q符合；不实现Q自适应 | Q与R同时变化会混淆，不是重复处罚 | A/B/C/D固定同Q公式/系数 |
| N17 | 混合标准保护与历史参数 | 必要保护应共同；不能让经验R代替数值检查 | 若以放R防崩与N05叠加会混淆 | 共同确定错误修复，历史数值参照另存 |
| N18 | 标准/历史逐值见数值表 | 标定集确定、验证集固定要求尚未满足证据 | 相同异常多阈值可能联合筛选 | B全记录，A只保留声明必要值；C/D未定参数不实现 |
| N19–20 | 历史持续质量状态机，无在线eta | 比开题慢速噪声学习更粗；不能当D已实现 | 残差/CMC/当前处罚证据交叉 | A关闭；B保留；C/D资格/历史接口预留，不直接复用为eta |
| N21 | 标准框架上的历史多signal/OSB/ISB扩展 | 必要非差非组合函数模型 | 不应以调R掩盖偏差模型缺失 | A/B/C/D共同函数模型，码偏差准入要固定 |

## 5. 单位、索引和方差专项检查

| 核查项 | 实际代码位置 / 结论 |
|---|---|
| SNR存储与35健康值 | rtklib.h:168 SNR_UNIT=0.001；gnss_adapter:220–221写CN0/0.001；rinex:899同样写；ppp:3038读×0.001。35000→35dB-Hz，正确。回退直接35.0，不再×0.001；默认合法frq路径通常读实际SNR，SNR=0由varerr971处理 |
| 相位 | adapter:256 ADR米/λ→周；ppp:1052 周×λ→米并去phw周×λ，GF:1003与MW:1020结果米。没有把米当周的已证错误 |
| Doppler | adapter:244 D=-range_rate/λ Hz；ppp:1325–1326积分-λDdt；1313 (λ*Hz_sigma)²为(m/s)²，1206配dt²得到m²，量纲一致；安卓rate uncertainty未进入R，只用于准入243 |
| ZTD/ZWD | ppp:520初值ZHD+ZWD；2490湿项xZTD-ZHD；3241虚拟残差ZWD-(ZTD-ZHD)，单位米，未见混用；H-07是模型系数问题不是单位错误 |
| IONEX | ionex.c:383、412–413 TECU×40.30E16/fL1²→L1斜延迟米；ppp:2093–2094除mapf/mapf²→垂直米/m²；2550乘mapf，2953再频率平方缩放，2991偏导一致 |
| clock | adapter:113/232纳秒→秒，P乘CLIGHT；ppp:1944 SPP秒→米；3015卫星dts秒×c，3602–3606接收机状态米/c输出秒。sol.dtr[1..4]是相对GPS的ISB秒，不是独立绝对钟差；注释/消费者必须知道 |
| sigma/var | eratio是标准差倍率，904–914在a/b中应用后平方；SIGW/SNR/persistent/penalty是方差倍率；sigma0=sqrt(var)；气象sigma输入平方后使用。未发现这几处错误开方/再平方；变量命名与日志需保持区别 |
| nf与边界 | rtkinit145–146先钳制1..NFREQ再分配nx；validate检查nf；NFREQ=4,NEXOBS=0；默认nf4，NX=3+5+1+197+5+4*197=999。直接改已分配rtk->opt.nf/iono/trop/dynamics不安全，禁止运行中改变状态布局 |
| sat/II/IT/IB | 默认入口sanitize/adapter/RINEX限定sat1..MAXSAT；II垂直电离层、IT总ZTD、IB按存储槽。多个底层函数不自检sat，直调pppos或关输入保护是潜在越界入口M-04，尚无默认正常路径越界证据 |
| frq与code | ppp:829 code2idx决定噪声band；245实际code决定RCB；2950实际code决定freq。核心没有把NFREQ序号直接当物理频率。TXT的B1C槽和RINEX不同属于H-06 |
| v/H/R维度 | ppp:2789容量96*2*4+197+3=968；3789按n*nf*2+MAXSAT+3分配；H[k+nx*nv]、R[i+i*nv]列主序；3149去重虚拟行、3168/3238容量检查。经rtkinit限制且n≤MAXOBS的默认路径未发现容量越界；filter接口H方向是状态×观测，应与报告常规H转置约定区分 |

没有证据时不修：联合CN0经验系数、VAR_IONO/ZTD的合理大小、0.5m周跳和4/8σ阈值、VMF3近似实际引起的定位量级，均需后续独立实验。

## 6. 随机模型与抗差的拆分设计（尚未实施）

统一实验配置建议放 `smartphone_ppp_config.h/.c`（不借用 `opt->mode`，该字段已表示定位模式）：

```c
typedef enum {
    MODE_A_BASELINE,
    MODE_B_LEGACY_ROBUST,
    MODE_C_NEW_ROBUST,
    MODE_D_ADAPTIVE_R
} ppp_experiment_mode_t;
```

首个实现默认B；C/D被请求时应明确报“本阶段未实现”，不可静默回退B。eta本阶段严格恒1，无学习窗口/更新。

建议测量行结构保存 `epoch/sat/code/type/storage_slot/noise_band`、R0测量项、模型方差、prior_kind、原始统计量、各旧倍率、w、R_eff、reject_reason、arc_event、trial_id。分层接口：

```text
基础输入/弧段合法性检查
  -> 函数模型/固定Q预测
  -> build_R0()                  固定系数的信号/码相/el/CN0随机模型
  -> build_model_variance()      轨道/钟差/大气剩余模型误差
  -> reject_policy()             拒绝/保留以及理由
  -> legacy_robust_policy()      B的旧处罚顺序；C入口暂未实现
  -> R_base = eta * R0           本阶段eta=1
  -> R_eff = R_base / w
  -> filter()试算 -> 验后规则 -> 一次提交
```

对于本仓库B，旧处罚有的发生在加入模型方差前，有的发生在后，平滑另有加法修正；不能机械地把全部因子移动到R0前。可把 `R0_row` 定义为该旧行在抗差前的测量+模型总方差，同时另保留measurement/model子项；旧R_eff计算结果可反算 `w_legacy=R0_row/R_eff`，用于统一日志。**B的实现必须保留原运算顺序**，不因数学上等价而改变浮点路径。D将来eta应只缩放信号观测噪声子项还是总R必须在方法协议明确，建议测量子项与模型/产品误差分开，不能让eta学习卫星/大气偏差。

虚拟先验另用row_kind和独立R0/抗差策略，不纳入信号噪声学习样本。Reject与Robust独立：reject不返回隐含无限方差，Robust不偷偷修改观测/残差。诊断日志也不能参与真值反馈。

## 7. A/B/C/D 定义及实验归因

| 组 | 定义 | 本阶段状态 |
|---|---|---|
| A MODE_A_BASELINE | 固定参数R0、必要PPP模型/改正/筛选/周跳基本处理、固定Q、必要数值失败保护，无当前残差处罚和持续质量处罚 | 仅设计，未启用 |
| B MODE_B_LEGACY_ROBUST | 审计前当前工程全部行为：profile及隐式默认、平方处罚、验后编辑、平滑/大气/历史质量/隔离；不能称普通EKF | 历史提交97a57a9永久保留；配置恢复完整特殊逻辑 |
| C MODE_C_NEW_ROBUST | 预留预测S、组共模、拟议Huber及事件隔离；A相同函数/Q/R0 | 未实现，禁止运行伪结果 |
| D MODE_D_ADAPTIVE_R | 预留C后合格历史的新息样本及下一历元eta提交 | 未实现，eta=1；禁止Q自适应 |

“固定R”在此表示模型公式和参数固定，没有残差驱动尺度学习；el/CN0随观测变化不等于eta自适应。开题本身也保留el/CN0基准定权。若用户另需全时恒常R矩阵，应单独定义实验，不与A混名。

### A 建议保留/关闭清单

| 保留共同项 | 关闭候选（用户确认后配置化，不删除B代码） |
|---|---|
| 多系统GPS+ISB、实际code频率/RCB/OSB、垂直电离层状态语义、估计ZTD、轨道钟差/天线/潮汐/缠绕，健康产品/频率合法性检查 | 当前z0平方penalty、实验残差硬拒绝与跨历元隔离 |
| LLI、半周/信号切换、必要GF/MW/独立连续性检测，确定周跳断弧修复 | SIGQC/SIGQCPH/CMC历史降权，BDSCODEVAR/CODENOPH人为倍率和渐变 |
| 固定R0系数，声明方差下限/标定出处；固定Q公式及ISB/RCB经验系数先保持，不调参 | DOPPSM/warmup/STATMOD相关膨胀等实验平滑，IONEX/VMF3虚拟观测（函数改正和初值政策另记录） |
| 输入边界/非有限保护，试算失败不提交 | 把在线持续质量状态机误当成“eta恒1却仍在学习R”的隐藏模块 |

### 已有开关不能构造完整 A

`SIGQC=0`、`SIGQCPH=0`、`SIGCMCDRIFT=0`、`DOPPSM=0`、`VMF3ZWDSIG=0`可关闭对应模块；不写PPPQUAR关闭隔离。BDSCODEVAR/CODENOPH设1去额外倍率。可是当前GNSS平方处罚/验后阈值没有开关；IONCONS最小0.20，设0并不能关虚拟约束；PREPROC同时控制必要周跳与实验码跳，不能整体关来制造A。`RTK_PPP_OPTS`整体替换字符串（rnx2rtkp352–356），删某选项还会回到隐式默认。所以必须设计统一配置、日志和细分策略后才可运行A。

### 历史复现与严格归因的边界

完整B默认有平滑/大气约束，而干净A关闭它们，A对完整B比较是“整个历史算法包”的差异，**不能把全部增益归因于抗差函数**。开题要求主要A/B/C/D对照固定输入/状态/Q，并把平滑和大气独立实验，需两份清楚的协议：

1. 历史复现协议：B_HIST=上述提交和全部当时行为，对既有数据先验证等价；对A的整包比较明确混合因素。
2. 主方法对照协议：声明共同输入、初值/P、Q、函数模型、基础R0、必要弧处理及平滑/先验开关。对B模块做关闭平滑/先验的受控消融，标成 **B的受控配置**，完整B始终可恢复；不得把受控配置结果当成原始B复现。若某配置不是审计前默认，run manifest必须写清。

初值也会消耗IONEX/VMF先验，只关虚拟行仍不是完全“无外部先验”。先拟定共同初值政策再做成对比较；保留B历史初值模式。这解决A清洁与B保存的要求，不通过删除B获得A。

## 8. 第一批修改建议（等待确认）

| 顺序 / 文件 | 建议范围 | 验证门槛 |
|---|---|---|
| 1 `src/ppp.c` | 修C-02缺种子断弧、保留事件快照；PPP方程/提交数值检查；修H-01“让渡仅基于实际检测” | 缺码周跳两历元、GF无TD证据、NaN不提交；正常会话变更有原因日志 |
| 2 `src/rtkcmn.c` | filter非零info不回写未初始化P；必要有限性错误返回，保留现有测量更新主体 | 奇异S不破坏输入；非有限新息不能返回成功；不在第一批重写Joseph |
| 3 `src/smartphone_ppp_config.h/.c` | 统一实验枚举、B默认、明确隐式参数，A策略逐项开关、C/D保留但拒绝执行、eta=1 | 配置解析/签名包含mode与全部策略；未知组合报错 |
| 4 `PPP_only/ppp_position.c` | 基础输入合法性与STARTQC独立、事件历史/失败来源日志；不要改变Q和SPP初值流程 | 关实验启动质控仍有边界保护；Q0/Q5来源可辨 |
| 5 `src/ppp.c`测量部分 | R0/Robust/Reject职责拆开，B旧路径计算顺序保留；IONEX虚拟行独立开关 | B正常路径与冻结输出/状态对照；A没有残差处罚和历史学习；模型方差不能丢失 |
| 6 `src/rnx2rtkp.c`、`src/gnss_replay.c` | 传模式、run manifest、逐行权重/拒绝理由、输入产品hash/时标；无需首批修改adapter准入 | TXT/RINEX分别列采用信号集合，不能以同核心替代输入等价验证 |

优先级：Critical先处理；High需在实验基线可信前定政策；Medium配置化/事件接口/支路覆盖；Low注释、未用宏、非主要构建项后处理。任何安全修复导致历史异常行为改变，要以source_revision/fix_set标注；保持未修复历史B可checkout复现，不能通过“修了但是B完全逐位不变”的文字掩盖差异。

## 9. 本轮验证、证据与限制

本轮未运行真值坐标调参、精度优化或自适应算法。最小探针直接包含审计前 `src/ppp.c` 调用静态函数，链接既有Release x64对象，生产源码哈希未变。探针在独立 `validation/audit` 目录编译，未覆盖主exe；确切源hash与对象hash见snapshot。探针针对确定风险，不代替全产品端到端会话。

```text
NAN_FILTER info=0 x_finite=0 P_finite=1
SLIP_MISSING_CODE ambiguity=100.000000 variance=1.000000 slip=1
NEXT_EPOCH ambiguity=100.000000 slip=0 expected_seed=-100.0
STEADY_GF_JUMP slip_L1=0 slip_L5=0 phase_history=0
```

复现材料保存在 `E:/GNSS/PPP_only/validation/audit/audit_probe.c`、`compile.cmd`、`compile.rsp`、`probe_results.txt`（validation被Git忽略，不随本轮报告自动上传）。从项目根目录运行 `validation/audit/compile.cmd`、`validation/audit/audit_probe.exe`。工具链 VS2022 Professional，/O2 /Gy /MD /DENAGLO /DWIN32 /DTRACE；对象来自审计前Release构建，两个首频观测及电离层5m的精确设定在probe源码。确认后的修复应把这些用例整理为可追踪测试。

此前模块裁剪阶段已有 Release x64 编译、TXT20历元以及RINEX1200历元与旧程序输出等价检查；这是历史证据，**本轮没有重跑，也不把等价运行当成统计模型正确的证明**。Android、跨日期精度、相关性实测、产品实时到达均未在本轮验证。

参数详表和无遗漏字面量位置索引见 [MAGIC_NUMBER_AUDIT.md](MAGIC_NUMBER_AUDIT.md)。每个发现都应以源码/探针和条件解释，不依据预期精度反推R。
