# PPP PHYSICAL 后验协方差数值修复报告

日期：2026-10-13。基于本轮开始的实际工作区（HEAD 0fd98a9，已有未提交修改保留）。本轮没有提交或推送。

## 结论与范围

确定缺陷是：原简化式在高动态范围更新中丢失 PSD，原有限性/对角/对称性检查不足，filter 返回成功并提交。**PHYSICAL 正式路径改用同一 K 的 Joseph 协方差计算，并增加只读、按状态尺度归一化的 PSD 事务门。** 没有修改求逆方法、增益/状态更新方程、R、Q、GIM预算、抗差策略或 E1–E4 参数。

主数据最终非PSD提交 **180→0**，所有 2426 次试更新均通过尺度判据；vivo 全部 1502 次更新通过。原回归176项+新增39项全部通过。A/B坐标、状态文件、Q、reject/slip、输入历元逐项完全一致。修复并未解决米级坐标误差，不能将PSD改善宣传为定位精度提升。

## 1. 第23历元实际证据与根因

第23期=2026/03/17 05:33:56.001，日志内部epoch=22；trial=0、IEKF iteration=1、call=2 是首次异常最终提交。第18期有异常试更新，但最终提交合法。
此操作 nx(full)=999、active=95、nv=119。压缩 H=95×119，完整 H=999×119，均为列主序，观测雅可比 Hᵀ。活动索引随保存数据记录。

| 矩阵 | 原尺度最小对称特征值 | 归一化最小特征值 | 归一化舍入预算 | 最大非对称元素 | 最小/最大对角 | PSD |
|---|---:|---:|---:|---:|---:|---|
| P minus | 6.5654871e-06 | 5.0851089e-06 | 4.4830079e-11 | 7.9354991e-08 | 0.022247478 / 3600.22 | True |
| R | 0.00033001873 | 1 | 1.6910917e-12 | 0 | 0.00033001873 / 8100 | True |
| S | 0.0003504698 | 9.7300724e-08 | 1.5875074e-10 | 8.5615284e-09 | 3601.9223 / 8101.3625 | True |
| P plus original | -1.8471392e-06 | -2.3563333e-06 | 4.5877352e-11 | 7.7469188e-08 | 0.022231629 / 3600.22 | False |
| P plus same-K C Joseph | 3.5436042e-06 | 4.5352897e-06 | 4.5877348e-11 | 7.7477168e-08 | 0.022231629 / 3600.22 | True |

特征值针对矩阵对称部分；仅诊断使用该对称部分，输入和输出均未强制对称、截断或修复。不同单位的原尺度特征值不能独立用于门限；上表归一化采用 C=D⁻¹PD⁻¹，Dii=sqrt(Pii)，属于合法对角合同变换。原P+的负特征值约为预算的 51362 倍，显著超出舍入误差。

S条件数 966090638；KS−P⁻H相对后向残差 1.56281025e-10。与原简化式独立重建的最大差 6.74460487e-13；x+−x−−Kv最大差 3.65709721e-09 来自大ECEF坐标加减舍入。K对独立直接求解最大元素差3.32e−8，不能由“小残差”声称前向误差为零；未发现明确求解失败。本轮保留原 matinv，不使用伪逆/正则化。

根因证据：P−、R、S合法；用同一原 K 的 Joseph 已得到合法P+，x+逐位相同。简化式依赖近似K的精确抵消，高尺度比情况下不能保持PSD；旧gate仅检查有限、非负对角和基本对称性，不检查负方向方差，因此返回0。

源码：[src/rtkcmn.c](E:/GNSS/PPP_only/src/rtkcmn.c:1575)；原gate [src/rtkcmn.c](E:/GNSS/PPP_only/src/rtkcmn.c:1470)。原实现保存于 [before/rtkcmn.c](E:/GNSS/PPP_only/validation/filter_covariance_fix/before/rtkcmn.c)。

矩阵逐项核对：S=HᵀP⁻H+R；K=P⁻H S⁻¹；矩阵乘法的NN/TN/NT索引和95×119尺寸一致。原和修复压缩内核的ASan均无内存错误。此结论限保存操作及其数值内核，并非对全项目内存安全的证明。
PHYSICAL活动状态依据Pii>0，允许x=0；非活动状态保留原x、零方差行，若零方差却存在交叉协方差则拒绝。未更改活动集，也未把999维占位零状态当作“需要正定”的状态。

保存：[完整9矩阵及同K Joseph](E:/GNSS/PPP_only/validation/filter_covariance_fix/epoch23_original_and_joseph.npz)，包含X/P/H/V/R/S/K/XP/PP及活动索引；[数值证据](E:/GNSS/PPP_only/validation/filter_covariance_fix/epoch23_evidence.json)；[原滤波精确输入/输出](E:/GNSS/PPP_only/validation/filter_full_ablation/numeric_repro/BASE_NEW_certificate_1.input.bin)。原负方向还已有60位Decimal证书，不是JSON截断或特征求解器偶然误差。

## 2. 原公式与修复公式

原：A=I−KHᵀ，P+=AP⁻。
PHYSICAL：P+=AP⁻Aᵀ+KRKᵀ。
计算步骤AP、AP·Aᵀ、KR、KR·Kᵀ使用现有矩阵函数；K、matinv、x+=x−+Kv均保持原实现。

在第18/23/864期三个原缺陷快照中，S、K、x+逐位一致，Joseph协方差均合法。第23期协方差最大元素变化 2.45095988e-05，与独立NumPy Joseph最大差 6.77236045e-14。
对原1200个最终提交逐个同K离线重算：P−全部尺度合法，原180个异常全部复核、Joseph异常为0。[逐期表](E:/GNSS/PPP_only/validation/filter_covariance_fix/old_1200_same_K_joseph.csv)。
离线同K结果不是完整递归回放；正式递归会因P改变影响后续K和状态，下一节单独验证。

## 3. 正式调用路径与失败提交保护

1. [src/rtkcmn.c](E:/GNSS/PPP_only/src/rtkcmn.c:1677)：专用PHYSICAL入口，先验证x/v/H有限和P−/R的PSD，再在压缩临时数组求解；验证S和P+，仅全部成功才写回x/P。临时失败结果不复制。
2. [src/ppp.c](E:/GNSS/PPP_only/src/ppp.c:4349)：PHYSICAL每次迭代调用新入口；同一固定预测先验和R，IEKF最终收敛才复制到外部trial，后续迭代失败不会提交前次成功候选。
3. [src/ppp.c](E:/GNSS/PPP_only/src/ppp.c:4393)：PPP入口、预测后、验后提交及可选AR候选检查PHYSICAL的PSD。A/B保留旧门，不更换全部filter调用。
4. 测量更新失败：当前Q=0，RINEX不输出有效解行；保留合法预测，产品先验消费时间仅成功时提交，下一期仍按既有预测与真实周跳规则传播，不重置全部状态。预测失败则保留回滚后的合法旧先验；日志明确LEGAL_PREDICTION_OR_PRIOR。

失败码/日志：NON_PSD_PRIOR(-31)、NON_PSD_R(-32)、NON_PSD_S(-33)、NON_PSD_POSTERIOR(-34)；现有NAN/Inf原因继续有效。失败记录PPP_FAILURE；进入清理路径的测量/预测失败另记录PPP_UPDATE_SKIPPED，入口/旧先验早返回使用原有stage日志。回放汇总failure_records/failure_reasons计数，成功有COMMITTED记录。没有额外实时质量学习计数进入算法。

PSD检查：[src/rtkcmn.c](E:/GNSS/PPP_only/src/rtkcmn.c:1515)。只读C的完整对角选主元Schur补检查，近零剩余块整体∞范数受控；预算64·DBL_EPSILON·active_n·max(1,||C||∞)。64为数值舍入安全余量，没有用定位结果校准；不裁剪负特征值、不加jitter、不改对角，不对失败输入静默做PSD投影。原基本对称性门及归一化非对称性检查亦保留。

完整PPP故障注入（仅隔离validation源码）：第23期把R改成有限非PSD，返回−32、Q0，无COMMITTED；rtk完整预测x以及P对角逐位延续到下一期，trial完整P与rtk P的memcmp相同，第24期正常提交。原trial已有同历元clock centering，trial clock比预测钟差−739.8830803m；该试算钟差不应在失败时提交，下一期保留原预测钟差。测试已区分trial与实际保留状态，未修改钟差模型。[证据](E:/GNSS/PPP_only/validation/filter_covariance_fix/skip_recovery_evidence.json)。

## 4. 主数据1200历元正式递归

输入产品、环境和3/17参考与上一轮完全一致；真值未传入解算器。参考沿用精确ECEF和椭球高假设，详见原全程消融报告。
旧/新均1200输出，1197Q6+3Q5；第300期等3个Q5是成功降级更新，非数值失败。
reject 13→13（码2/相位11），detector slip 806→806；
reset聚合数量均 18659。无新NaN/Inf、异常重启或失败。

| 指标 | 修复前 | 修复后 |
|---|---:|---:|
| 非PSD最终提交 | 180 | 0 |
| 非PSD试更新 | 352 | 0 |
| 更新失败历元 | 0 | 0 |
| 最小后验原尺度特征值 | −1.2891402e−5 | 1.678174e-06 |
| 最大S条件数 | 1.0694508e9 | 1.0694508e+09 |
| 最大KS−PH相对后向残差 | 3.4603389e−9 | 3.9922035e-09 |
| 后验相对非对称性最大值 | 2.7606851e-09 | 3.765454e-14 |

正式状态的全程最大ECEF轨迹差 **2.49707421e-06m**；.pos转回ECEF的最大差 0.000110873884m，主要包含输出纬经度/高程的舍入阶跃，不能误读为状态跳变。最大总ZTD变化 6.58421682e-07m；电离层/钟差变化逐期保留。最大一次位置更新 7.67759934m，原段有正常启动大更新，未出现新的异常跳变。

初中后期采用相同Q6窗口：

| 路径 | 窗口 | N | 水平RMS m | 高程RMS m | 3D RMS m | 最大3D m |
|---|---|---:|---:|---:|---:|---:|
| OLD | early | 120 | 4.3428554 | 2.222106 | 4.8783346 | 6.1027317 |
| OLD | middle | 479 | 2.8801414 | 0.743641 | 2.9745952 | 3.7250004 |
| OLD | late | 598 | 2.36601 | 0.9462531 | 2.5482147 | 2.7712158 |
| OLD | all | 1197 | 2.8296469 | 1.0787167 | 3.0282885 | 6.1027317 |
| FIXED | early | 120 | 4.3428554 | 2.222106 | 4.8783346 | 6.1027317 |
| FIXED | middle | 479 | 2.8801419 | 0.74364029 | 2.9745955 | 3.7250004 |
| FIXED | late | 598 | 2.3660101 | 0.94625056 | 2.5482138 | 2.7712158 |
| FIXED | all | 1197 | 2.8296471 | 1.0787154 | 3.0282882 | 6.1027317 |

| 路径 | 历元 | Q | 水平 m | 有符号U m | 3D m | 总ZTD m |
|---|---:|---:|---:|---:|---:|---:|
| OLD | 1 | 6 | 1.1138844 | 1.4885002 | 1.8591319 | 2.3080748 |
| OLD | 6 | 6 | 2.6687261 | 1.1121998 | 2.8912087 | 2.326594 |
| OLD | 23 | 6 | 5.0801542 | 3.1546983 | 5.9799739 | 2.3384061 |
| OLD | 60 | 6 | 4.995221 | 2.8353984 | 5.7438417 | 2.2924437 |
| OLD | 300 | 5 | 2.819386 | 0.74719971 | 2.9167182 | 2.135715 |
| OLD | 1200 | 6 | 2.149938 | 1.0586 | 2.3964281 | 2.1408055 |
| FIXED | 1 | 6 | 1.1138844 | 1.4885002 | 1.8591319 | 2.3080748 |
| FIXED | 6 | 6 | 2.6687261 | 1.1121998 | 2.8912087 | 2.326594 |
| FIXED | 23 | 6 | 5.0801542 | 3.1546983 | 5.9799739 | 2.3384061 |
| FIXED | 60 | 6 | 4.995221 | 2.8353984 | 5.7438417 | 2.2924437 |
| FIXED | 300 | 5 | 2.819386 | 0.74719971 | 2.9167182 | 2.1357154 |
| FIXED | 1200 | 6 | 2.149938 | 1.0586 | 2.3964281 | 2.1408059 |

沿用1m/60期Q6持续窗口，水平和3D仍未收敛，高程首窗口仍第99期。结果几乎不变，不能宣称该数值修复解决米级精度问题。逐期状态差、iono、创新、GIM、增益与PSD证据位于 [validation目录](E:/GNSS/PPP_only/validation/filter_covariance_fix)。

![坐标误差与PSD对比](E:/GNSS/PPP_only/docs/FILTER_COVARIANCE_NUMERICAL_FIX.png)

## 5. vivo独立600历元

同样使用已有9/22 vivo V2507A和NRT产品，缺少可信真值，**仅报告轨迹差**。
旧/新均598Q6+2Q5，600有效输出，更新失败0；所有1502次试更新P−/R/S/P+均合法；最小P+特征值 7.2161869e-06，最大S条件数 3.5387117e+08、相对求解残差 9.5351701e-10。
reject 151→151，detector slip 171→171，
arc_reset 508→508，arc_pending 3023→3023，arc_reinitialized 471→471。
最大3D轨迹差 1.64343374e-06m，最大ZTD差 2.67026479e-08m，末期3D差 4.81548035e-07m。未证明绝对精度或收敛时间变化，未用此段调参数。

## 6. 构建、测试与可追溯性

原45+26+58+47=176项通过；新增39项通过，覆盖SPD正常更新、显著非PSD、零状态/非活动交叉协方差、秩亏PSD、尺度等价、舍入边界、相关R非对角项、半正定R/奇异S、NaN/Inf、有限输入溢出、失败原子性、后续恢复、多次IEKF部分成功后失败、最终提交门与明确原因。
额外三个真实缺陷快照精确桥接、原/新ASan、整段故障注入恢复测试通过；它们不计入39项以免重复计数。

VS x64 Release/Debug均构建成功；原可运行EXE保留 [Release](E:/GNSS/PPP_only/validation/filter_covariance_fix/before/Release/PPP_only.exe)/[Debug](E:/GNSS/PPP_only/validation/filter_covariance_fix/before/Debug/PPP_only.exe)。
正式Release的1200主数据和600vivo输出与隔离诊断关闭版的坐标、完整状态文件、Q、reject/slip、失败统计一致。诊断ON/OFF也逐项一致。最终正式源码仅失败日志文案较候选版更精确（LEGAL_PREDICTION_OR_PRIOR）；最终正式回放验证数值一致。Debug另通过30历元PHYSICAL有限性/成功更新检查。全部215项已再次针对最终源码构建执行，结果保存在final_regression。

正式修改：

- [src/rtkcmn.c](E:/GNSS/PPP_only/src/rtkcmn.c:1515)：PSD检测、PHYSICAL Joseph更新、原子写回、失败原因；filter/filter_active原正常有限运算保留。
- [src/ppp.c](E:/GNSS/PPP_only/src/ppp.c:4349)：PHYSICAL路由、预测/后验PSD门与失败跳过日志。
- [src/rtklib.h](E:/GNSS/PPP_only/src/rtklib.h:1547)：专用API和错误码。无rtk_t结构布局改变。

新增tests脚本：diagnose_covariance_joseph.py、build_covariance_fix.py、run_covariance_fix.py、check_covariance_fix_exact.py、analyze_covariance_fix.py、check_covariance_fix_skip.py、check_covariance_memory.py、deploy_covariance_fix.py、report_covariance_fix.py及covariance_fix_regression.c。
新增产物限定validation/filter_covariance_fix与本报告/图，没有修改选项或E1–E4正式配置。最终文件SHA清单见deployment_evidence.json，诊断关闭代码不含故障注入。

运行（项目根目录，PowerShell；默认Python路径按当前机器）：

1. 原快照只读Joseph复核：python tests/diagnose_covariance_joseph.py。
2. 隔离构建及215项：python tests/build_covariance_fix.py。
3. 真缺陷精确更新：python tests/check_covariance_fix_exact.py；ASan：python tests/check_covariance_memory.py。
4. 主数据/独立数据：python tests/run_covariance_fix.py；每个运行要求独立目录，不覆盖既有证据。重跑前设置环境变量RTK_COVARIANCE_VALIDATION_DIR到一个新目录（例如E:/GNSS/PPP_only/validation/covariance_repeat），再按1→2→3→4→5执行。不会改变PPP选项或正式EXE。
5. 全段分析：python tests/analyze_covariance_fix.py NEW；同理VIVO_NEW；一致性：--equivalence。
6. 故障注入：python tests/check_covariance_fix_skip.py；已有故障日志只读核验：--audit-existing。

ENABLE_FILTER_DIAGNOSTIC控制矩阵观察日志；正式安全修复不依赖该宏。故障注入只在check_covariance_fix_skip.py生成的validation/fault.c中，不存在正式源码/选项中。

## 7. 保留问题与下一步

- 新模型米级水平偏差/完整收敛问题仍存在；本修复不提供其主要因果解释，也不调整任何模型参数。
- A/B为行为保持本轮未切换Joseph/新增PSD门；此前172/1个非PSD提交风险仍保留，不能称全项目所有filter调用已修复。扩大到A/B需单独验证历史基线影响。
- 高S条件数仍存在。实测求解后向残差小、S正定，没有新求逆失败；不据此替换求逆算法，也不证明所有前向误差可忽略。
- 归一化PSD门有O(active³)成本；当前PC回放已验证，Android实时性能尚需独立性能测试。
- PSD是必要数值有效性条件，不代表协方差已经统计校准；持续偏差、相关GIM信息与米级坐标误差需独立处理。

本轮确定数值缺陷已修复；不引入新的物理参数、不将E1–E4晋升默认、不开始eta或新增抗差方法。
