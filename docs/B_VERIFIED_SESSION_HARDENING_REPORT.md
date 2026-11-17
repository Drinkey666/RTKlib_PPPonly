# 正式入口统一与恢复码质控会话工程化

日期：2026-10-20；活动项目：E:/GNSS/PPP_only。

## 结论

“统一正式配置”和“完善恢复质控工程实现”已完成。四组新会话版与旧BRIDGE3的坐标、完整状态、事件、质控决定和最终观测使用精确一致；没有新的精度提升。新时段独立验收尚缺已确认的数据/产品/参考集合，未将旧四组冒充独立验证，未晋升候选。

正式C/VS/EXE、R/Q/P0/GIM、抗差门限、Joseph和52个保护文件均未修改；未部署新质控到Android。

## 1. 统一正式入口

- 新增`config/b_verified.json`，提供现有B_VERIFIED_v2_JOSEPH、PPP_COMMON、LEGACY估计器、nf=4、G/E/C、GLO/E5b关闭，恢复QC默认OFF。
- 新增`run_ppp.cmd`→`tools/run_ppp_session.py`及共享`tools/ppp_preset.py`。继承的RTK_PPP_*实验变量被清除；文件清单只能换文件/来源，不允许注入真值、模型/Q/R覆盖或静默截断。
- 原`tools/forecast_ppp.py`固定选择A+PHYSICAL/GLO=1，是旧研究配置。本轮将其工具默认选择统一到同一正式B预设，严格预报/接收证据门禁保留。这是有意改变工具选择，不是新物理公式修复，也不声称旧PHYSICAL数值不变。
- 记录输入、EXE和预设SHA256、实际PPP_CONFIG、输出历元/Q；拒绝覆盖POS、trace/stat、events、obs.csv及旧压缩明细。`--prepare-only`只检查/打印，不解算、不写结果。COMPLETE表示进程/配置/输出检查完成，不代表精度达标。
- 原`run_b_verified.cmd`、VS配置、旧研究入口和正式52文件不动。模板：`config/b_verified_replay.example.json`。

## 2. 恢复质控的会话生命周期

新`tests/recovery_session_adapter.h`复用原BRIDGE3 kernel。3σ、5颗不同卫星的同星座同signal同伴、原30秒时限、64帧及0.2～1.5秒采样连续性规则不变。

1. 历史、临时cells、统计计数归属各自rtk_t，rtkinit创建、rtkfree释放；去掉原型的进程owner、全局共享历史/临时数组、文件级Doppler表和未来查找。
2. RINEX给当前obsd_t附加选中Doppler的actual signal元数据；P/L都缺失时仍可识别当前D。原P/L/D/code/LLI字段不改；缺D时元数据清零，换信号不继承旧字段。TXT既有adapter本就提供当前signal，未改变其门限。
3. 时间回退依原kernel清空历史；同历元重入不重复累计；长间断/积分中断/信号改变沿用UNAVAILABLE，不新增拒绝。原因日志区分LONG_GAP、RATE_OR_TIME_DISCONTINUITY、INSUFFICIENT_SAME_SIGNAL_PEERS、CURRENT_CODE_UNAVAILABLE以及BLOCK/RELEASE。
4. 双滤波器交错处理不相互污染。不据此声称整个RTKLIB、trace或产品加载已线程安全。
5. 仅私有构建在`ENABLE_RECOVERY_SESSION`下扩展rtk_t/obsd_t；**32个编译单元全部以同一私有ABI重建**。私有对象/结构不可混进正式VS、旧trial或Android .so。关闭宏时ppp/rinex/ppp_position的.text与正式源码相同。

私有源：`validation/recovery_session/build/source/`；EXE：同目录上级`trial.exe`。只有新`run_recovery_session_trial.cmd`或统一入口显式加`--recovery-trial`才启用。旧候选及历史证据保留。

## 3. 测试及完整回归

|检查|结果|
|---|---|
|原有C回归（含18项RINEX原合同）|341通过|
|Joseph数值断言|11通过|
|未改BRIDGE3 kernel|77通过，源码哈希与旧测试构建一致|
|新会话隔离/重入/回退/重启/只读/弧段保护|27通过|
|当前D身份/缺D清零/换signal元数据|3通过|
|新增统一入口Python合同|24通过|
|原严格预报门禁Python合同|24通过|

合计459个C断言及48个Python测试通过。RINEX元数据探针仅在测试中修正了大nav_t放栈造成的探针栈溢出，改为堆分配；不是生产定位缺陷。

为核查ABI/元数据工程改造，进行了4次新会话版完整回放，与已存旧BRIDGE3比较：POS、STAT、reject/slip/重置/失败等事件、每条BLOCK/RELEASE/UNAVAILABLE数值及最终码相使用均精确一致。2736次提交finite/尺度PSD，无新增失败。另通过统一入口运行K70晚正式B，POS/STAT/事件与原正式B精确一致。没有重跑旧ON/OFF八组或重新调参。

|数据|正式B 60s后水平RMS/m|旧候选＝新会话候选/m|候选末水平/m|
|---|---:|---:|---:|
|K70_early|1.631525|1.631271|0.910535|
|K70_late|1.169475|1.165332|0.437172|
|IQ_early|0.519978|0.519978|0.621337|
|IQ_late|2.191495|2.168273|1.067465|

因此仍保留原候选局限：K70晚只提前约5秒，首60秒/60～350秒略退化；启动最大误差未解决、IQ晚仍未持续1m。没有新的普适性能证据。历史四组真值高程是正常高，只复用水平评价；Android界面后来新增椭球高输入不改变旧参考。

## 4. 严格预报与归档回归

新归档入口要求WUM NRT同issue轨道钟差，无FIN自动替换。现有四组CLK实际标头PANDA-CLKDEN，不能仅凭文件名认证预报属性或历史接收可用性。四组以显式`usage=ARCHIVED_REGRESSION`做等价控制，未认证为“观测当时已经可用的实时产品”。

相同K70晚文件交给严格`forecast_ppp.py --run`，实际预检后按FORECAST_CLK_PROVENANCE_UNCONFIRMED和PRODUCT_AVAILABILITY_NOT_ESTABLISHED停止，filter_started=false，无解算输出。严格门禁未为跑通旧资料放宽。

## 5. 新时段验收尚缺材料

只读盘点E:/RTKLIB_Data/OBS、k70、iq10.17的17份RINEX：7份被所扫历史清单明确使用过，10份不能由该有限索引认定；“未索引”不等于独立数据，部分亦无匹配NRT和可信参考。详见`independent_inventory.json`。本轮未获得已核实具备新时段、设备身份、匹配可用预报产品和独立参考的完整验收集，已请求用户提供路径。

收到后冻结本轮规则，不调3σ/等待秒数；正式OFF与候选ON比较完整曲线、首60秒/60～350秒/后期RMS、既有持续60秒/H<1m时间、Q/有效历元、可识别误拒证据及finite/PSD。旧四组仅作回归，不作为新的独立证明。

## 6. 使用、证据及范围

```bat
rem 复制模板并替换实际文件路径，结果必须是新路径
run_ppp.cmd config\my_files.json --output E:\RTKLIB_Data\PPP_Result\new_formal.pos
run_recovery_session_trial.cmd config\my_files.json --output E:\RTKLIB_Data\PPP_Result\new_trial.pos
run_forecast_ppp.cmd config\my_forecast_products.json --run
```

TXT将OBS键改为TXT，source为txt-fast/txt-realtime。本轮完整控制是RINEX四组，未重跑此前TXT 1x，也未做新Android/JNI认证。正式APP仍使用已验证正式B。

日志：`<结果>.session.json`、`.console.log`、`.trace`、`.stat`、`.products.log`；本轮大明细校验压缩为.gz。汇总：`validation/recovery_session/summary.json`；每组`comparison.json`保存精确对照；`regression/`保存断言结果，`strict_gate/verification.json`保存原生负向门禁证据。未复制原观测/产品，未写F盘，未提交/推送。

新文件：config/b_verified.json、b_verified_replay.example.json；tools/ppp_preset.py、run_ppp_session.py；run_ppp.cmd、run_recovery_session_trial.cmd；tests/recovery_session_adapter.h、recovery_session_regression.c、build_recovery_session.py、verify_recovery_session.py、inventory_independent_validation.py、report_recovery_session.py、test_ppp_session_entry.py。本轮已存在文件的改动限tools/forecast_ppp.py、README、预报流程及接续说明。

复核：`python tests/verify_recovery_session.py`完整验证（既有回放有回执缓存）；可用`--entry-tests-only`、`--rinex-only`限制范围。`python tests/report_recovery_session.py`只汇总，不解算。私有源改变时构建指纹拒绝覆盖，应保存旧构建并另开明确实验目录。
