# PPP_only 项目规则与会话入口

## 开始任务

- 新会话先读本文件和 `docs/CURRENT_STATE.md`，再核对工作目录、Git HEAD 和工作区状态。
- 只按用户当前任务定位代码和证据。整理文档不自动恢复旧业务任务。
- `docs/CURRENT_STATE.md` 是统一当前状态页。`HANDOFF/CURRENT.md`、`HANDOFF/INDEX.md`、`PROJECT_HANDOFF.md`、`NEW_CODEX_PROMPT.md` 和 `PROJECT_CONTINUATION/` 保留为历史证据和按需索引，其中旧的“首次只读”“下一步”不再指挥当前任务。
- 不一次性加载全部历史报告、聊天或长日志。按主题读取，核对结论适用的代码、输入、配置和参考版本。

## 项目与模块

- 活动PC工程 `E:/GNSS/PPP_only`，Android工程 `E:/android/test/FTPGet`，观测及产品主要在 `E:/RTKLIB_Data`。
- `E:/GNSS/rtklib_only/rtklib_only/rtklib_Project2` 是旧工程路径，`PROJECT_CONTINUATION/project/` 是历史快照，不能代替当前工作区。
- 目标为手机严格实时、非组合PPP，文件预报产品路线，SSR流关闭。Android下载RTS BIA，SP3/CLK仍NRT。
- PC入口为 `src/rnx2rtkp.c`、`src/gnss_replay.c`、`src/postpos.c`；观测转换在 `src/gnss_adapter.c` 及钟参考/信号策略文件；单历元控制为 `PPP_only/ppp_position.c`；PPP与数值内核为 `src/ppp.c`、`src/rtkcmn.c`。
- Android实时链为 `LivePppController.kt` → `LivePppNative.kt` → `app/src/main/cpp/gnss_jni.cpp` → `app/src/main/cpp/ppp_live/rtklib/`。跨工程修改前读该工程AGENTS，以CMake确认实际编译来源。

## 正式行为与开发边界

- 正式预设 `B_VERIFIED_v2_JOSEPH`，以 `config/b_verified.json`、`run_b_verified.cmd` 和实际PPP_CONFIG为准。单设BASELINE=B是旧B。
- 用户2026-11-10明确要求解算不使用B2b：北斗7D/7P/7Z在Android/TXT准入及共同PPP内核（含RINEX）均排除，不自动规划接入。B2I 7I和B2a 5P分别按原策略保留；IQ候选仍暂停。
- 用户2026-11-10进一步明确B1I与B1C都要参与：正式准入同时使用2I槽0与1P槽3，不把B1C再当作未启用候选。按实际码型查询各自OSB、保留独立N/RCB；不按精度结果擅自删除B1C。PC与Android默认优先版本化igs20_20261110.atx，原天线文件保留。
- 保留Joseph/PSD安全提交、弧段及连续性修复、固定钟段观测生成。旧“正式52文件全部不变”已被授权的观测生成修复部分取代，不据旧SHA回退源码。
- 未获当前任务授权和证据支持，不改默认R/Q/P0/GIM、抗差门限、产品模型，不按真值拟合正式参数。候选采用显式开关、独立输出及可回退方式。
- C普通Huber已存在；D/信号级eta未作为正式路径启用。旧报告“C未实现”只适用于当时版本。
- OSB过期明确失败，不外推，不绕过产品和参考检查。NRT轨钟+RTS BIA的覆盖不等于完整参考兼容认证。
- 参考坐标仅用于事后评价。每份结果记录框架、经纬度、高程类型、来源及版本。10/31高程修订见状态页，不混用旧图表。
- 尚无通用米级偏差实时修复。局部敏感性、固定点投影、同段标定和离线未来信息不能当成完整实时改善。

## 构建和验证

- PC用VS2022/v143，打开 `PPP_only.sln`，Release/x64。标准EXE与固定钟段修复独立EXE的区别及命令见状态页。
- 改C核心前核对NFREQ、ENAGLO、头文件和链接对象，不能混用不同实验.obj。按改动运行相关测试；数值/模型改动覆盖既有215项，观测转换另加51项及逐字段验证。
- Android目录使用Android Studio JBR，按需执行 `gradlew.bat :app:testDebugUnitTest :app:assembleDebug --offline --console=plain`。
- 测试历史通过数和本轮执行结果分开写。文档任务无需重构建/回放，不把跳过计作通过。
- 回放选新输出，保存输入/EXE/预设身份、状态和日志。先查.gz、缓存与存储清单，不因明文不在而重跑。

## 文件和Git安全

- PC有大量未提交和未跟踪成果。禁止reset/clean/丢弃、整文件覆盖他人修改；不自动提交推送，不删除原始观测、产品、正式文件和有效否定证据。
- HEAD、工作区、构建产物、已安装APK分别核验。clone远程或checkout旧提交不足以恢复当前成果。
- 临时产物只写E，不写F，控制日志体积。只清理已核验可再生的本轮临时文件，保留原始输入和有效证据。
- 用户没有这些手机数据的同期测量型接收机RINEX，不重复索取。重采/室外验证按新授权和设备条件执行。
- 不把账号密码、令牌或其他凭据写入接续文件或新会话启动指令。

## 维护项目记忆

- 重要开发、验证、决定或发现完成后更新 `docs/CURRENT_STATE.md` 相应条目，替换过时结论，保留证据引用，不能只在末尾追加聊天摘要。
- 状态页维护任务、Git/工作区身份、事实/假设、已完成、风险、已排除方向、验证范围和下一步验收。解决项移入已完成，候选不自动晋升正式。
- 旧报告保留原位，详情只提供索引。新审计沿用 `validation/audit_registry/`、`tests/save_ppp_audit_registry.py`，不新建平行历史体系。
- 代码、配置、输入或参考改变后先判断旧结论适用性。只有新的触发条件才重验对应环节，不自动重跑旧批量排查。
- 接续文档不是备份。换电脑需迁移未提交源码、必要证据、输入和路径映射；同机换账号使用实际工程目录。
