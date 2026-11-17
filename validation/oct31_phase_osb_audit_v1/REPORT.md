# 10/31 TXT 解算相位 OSB 参与核查

结论：本次 K70/IQ 文件产品解算没有施加 BIA 相位 OSB；码 OSB 有参与。原 BIA 中有 867 条 C 类码 OSB、15007 条 L 类相位 OSB，文件存在相位记录不等于程序使用。

## 路径证据

- src/gnss_replay.c::load_products 调用 readdcb 读取 BIA，TXT 逐期直接进入 rtkpos。
- src/preceph.c::readbiaf 只识别以 C 开头的三字符观测名，L 记录没有 obs1，直接跳过；存储/查询为 codeosb_t/codeosb_at。
- src/ppp.c::corr_meas 的 L 改正为 L_raw*c/f − 卫星天线项 − 接收机天线项 − 相位缠绕项，没有 BIA 相位 OSB；P 分支调用 codeosb_at 并减去码 OSB。
- src/postpos.c::corr_phase_bias_ssr 使用 nav->ssr[].pbias，属于另一条 SSR 调度路径；本次 TXT 不经过该函数，日志明确 FILE_PRODUCTS_ONLY / SSR=OFF。不能把 BIA 相位 OSB 与 SSR pbias 混为一谈。

## 实际 EXE 验证

原 BIA 和所有生产文件不动，另存一份只移除 15007 条 L 记录的 BIA。867 条 C 记录按字节核对完全相同，其余元数据保持。使用本次实际 EXE（SHA b21c0420e7ebcf85251ede0dd4b06c20a05530cf4fe8560dd027f5d957826944）对 K70 和 IQ 各回放前 30 历元，预检均通过，结果除 processing_ms 外所有字段与原 BIA 基线逐字段相同。完整命令及 SHA 在各 run.json，统计在 summary.json。

## 解释边界

这确认当前路径未使用相位 OSB，不代表已经证明它是约 2 m 高程偏差的根因。本次没有启用相位 OSB、没有修改算法或产品原件，也未进行完整精度对照。历史 raPPPid 路径曾在 phase=off 字段下实际施加相位 OSB，不能把该字段或其行为套用到本项目。若后续验证相位 OSB，应另行核对精确轨钟参考、相位有效期和跳变、信号身份、模糊度初始化/连续性；不能只加一个相位减项便宣称修复。
