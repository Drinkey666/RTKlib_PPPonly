# 用户明确排除B2b（2026-11-10）

用户要求解算不使用B2b；IQ候选继续暂停。Android/TXT的正式白名单原已排除北斗7D/7P/7Z，本轮在共同 `ppp_signal_supported` 增加同样排除，覆盖RINEX载波入口和各估计器，不添加启用开关。按实际码型排除，不误删同为1207.14MHz的B2I 7I，也不影响B2a 5P。现有B2b识别仅用于保留正确原始身份和诊断，不代表接入解算。

PC `src/ppp.c` 已同步到Android实际编译的 `app/src/main/cpp/ppp_live/rtklib/ppp.c`，对应清单更新；原文件备份在before/。B1C独立槽修复保留，未自动开放B1C。未改R/Q/P0/GIM、产品、Raw或IQ Q策略。

本轮215项既有核心、51项转换与23项专项检查全过。专项覆盖三种B2b码在全部槽被拒绝、另一估计器不能放开、直接构造RINEX式有效P/L也不能初始化B2b模糊度，以及B2I/B2a/GPS/GAL原信号保持支持。单位测试与构建日志在unit/。

PC独立Release/x64构建及Android四ABI Debug构建成功；Android JVM任务为缓存，未计作本轮重新测试。新PC程序位于pc_build/PPP_only.exe，原标准及旧固定钟段程序/对象保留。K70 120期控制除耗时外逐字段复现原缓存。APK未安装，未做现场验收。

AGENTS和CURRENT_STATE已明确记录“不接入B2b”，删除将B2b列作后续待接入的计划。本轮没有继续IQ候选、改变参考坐标或重跑完整精度实验。
