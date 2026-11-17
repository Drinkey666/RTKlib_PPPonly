# B2b 识别与 B1C 槽位修复（2026-11-10）

用户最新要求：先不处理 IQ，先解决另外两个问题。IQ 私有候选已标记 `validation/iq_b2aq_phase_trial_v1/USER_PAUSED.json`，已有记录保留，不继续评价、部署或自动恢复。本次没有接入 IQ Q 载波或将 Q 改成 P。

## 更正前轮判断

前轮仅依据本地旧 igs20.atx 的 BEIDOU-2G 条目，推断 K70 C01/C02/C03 的 D 标识异常，这一依据不成立。该文件漏了2026年PRN重分配，不能据其认定手机码型错误。

已保存 [IGS 卫星元数据](https://files.igs.org/pub/station/general/igs_satellite_metadata.snx) release2441，按观测日期2026-10-31核对：C01→C231（2026-04-20 16:00起），C02→C229（04-17 17:00起），C03→C230（04-18 11:00起），均为BDS-3 GEO。记录与校验值见 `dated_identity.json`，[IGS星座资料](https://www.igs.org/mgex/constellations/)也列出新旧PRN对应。

因此K70的1207.14MHz+D应识别为B2b 7D，不能改成7I；Android D2同步状态位也不能覆盖实际CodeType，不硬编码“低PRN就是北斗二号”。IQ对同频信号上报I的物理含义保持未确认，本次暂停处理。

## 已改生产源码

1. `gnss_adapter.c`：补齐1207.14MHz D/P/Z→7D/7P/7Z，保留I/Q/X→7I/7Q/7X。共用物理槽1，保持实际码型、OSB查询键和信号历史分离；不改写Raw。
2. B1C 1575.42MHz的1D/1P/1X从槽0移到槽3，与内核code2idx、C01天线槽及独立模糊度一致；B1I保持槽0。非PPP-safe转换可同时保存二者，不再相互覆盖。
3. `gnss_signal_policy.c` / `gnss_replay.c`：诊断正确显示B1C第4槽及B2b精确码型，未启用原因不再描述成B1I同槽竞争。
4. `rtklib.h` / `rtkcmn.c` / `preceph.c`：纠正相关B2I/B2b注释，不改枚举、ABI、实际频率、R/Q/P0/GIM或滤波公式。

五个共用源文件已同步到Android CMake实际目录 `app/src/main/cpp/ppp_live/rtklib`，仅更新相应pc_profile.sha256与pc_snapshot.json记录；PC专用gnss_replay.c不复制到Android。改前文件备份见 `before/`。

## 接入边界与天线数据

识别修复没有自动扩大正式白名单。K70全量10928条D现在按7D识别，实际预检为3颗星、C7D OSB覆盖0颗；ADR也没有VALID且无RESET/SLIP的记录。不能借用C7I/C5P偏差或把非零ADR直接当连续载波。B1C独立槽位已修，但实际启用仍须显式验证精确OSB、已有BDS_C1P RCB、天线及弧段；当前正式策略保持排除。没有宣称新信号已经参与正式PPP。

已单独下载[IGS官方当前igs20.atx](https://files.igs.org/pub/station/general/igs20.atx)，61602416字节，SHA256 `abdda8adc1cfdb3dae1f25fa22843365be2a33747d9131835c3117a559cd035a`。原生读取器按10/31为C01/02/03选中BEIDOU-3G-CAST及正确SVN，含C07而非C05。原 `E:/RTKLIB_Data/Tables/igs20.atx`、历史配置及Android用户产品未覆盖。普通目录的igs20_2438.atx地址返回404，不能据此证明归档不存在。新版完成日期/身份选择验证，尚未认证与本组NRT钟参考完整配套或精度收益；旧天线校准风险独立保留。

## 本轮验证

- 当前生产源码Release/x64独立构建成功：`pc_build/PPP_only.exe`，SHA256 `d0d63dc80e1e52a0cd680b78b98071c0ae4c2505b0e45d45ab3f8d11df41ba4d`。原正式/固定钟段EXE及对象未替换。
- 215项既有核心、51项观测转换、44项新增检查全过。新增覆盖低/高PRN与D2状态不改码、六种1207码型、B1C槽一致、同星B1I/B1C并存/倒序稳定、波长、策略不意外开放及新版ATX日期选择。入口 `tests/verify_bds_identity_fix.py`。
- 使用新对象复核2382项原生断言及现存两机751869行Raw、409451行adapter、283587行接受相位，准入项身份一致，无同星同槽重复。`identity_audit/`是共同代码回归，没有继续IQ候选实验。
- 新EXE的K70 120期控制除耗时外逐字段复现原固定钟段缓存。预检显示1P第4槽、7D三颗星且OSB缺失；没有为保持不变的正式准入重跑全程。
- Android请求`:app:testDebugUnitTest :app:assembleDebug --offline --console=plain`成功，四ABI构建通过；JVM任务是否重新执行以 `android_build.log`为准，不把缓存计作本轮重测。APK未安装、未做现场验收。

已修复B2b识别遗漏、B1C槽位冲突、相关诊断及前轮错误卫星代际推断。未宣称消除米级偏差、完成全部产品校准或启用所有信号。没有提交推送。
