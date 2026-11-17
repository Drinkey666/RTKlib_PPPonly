# B_VERIFIED Joseph 正式整合验收

日期：2026-10-19。用户授权正式整合。此前确定根因与32次原始矩阵证据见 B_COVARIANCE_SYMMETRY_REPORT.md，未重复大范围数值定位。

1. src/rtkcmn.c `filter_verified()`新增明确正式入口：filter_masked(...,allow_zero=0,physical=1)，复用既有Joseph和PSD检查，保持B活动规则；原filter/filter_active/filter_physical均保留。
2. src/rtklib.h导出该入口。src/ppp.c的ppp_verified_joseph/ppp_safe_covariance仅对B_VERIFIED的LEGACY估计器启用；预测前后、试更新、验后提交及AR候选均使用尺度化有效性门槛。失败不提交试算x/P；预测失败恢复此前可信状态，观测更新失败保留合法预测。
3. src/smartphone_ppp_config.c输出 B_VERIFIED_v2、covariance=JOSEPH_B_MASK。run_b_verified.cmd仍调用正式Release程序，提示更新；run_b_legacy.cmd原样复现旧B。未设置PROFILE的A/旧B/PHYSICAL行为不变。
4. Release/Debug均构建通过。当前套件341项断言和11项Joseph专项通过；结果逐套保存在validation/b_joseph_integration/unit_results.json和unit/*.results.txt。不是根据历史口头计数填入测试数。
5. 正式EXE十组完整对照：四B_VERIFIED的POS/STAT/事件与已验证独立Joseph输出精确一致；四旧B、一A、一PHYSICAL与原正式输出精确一致。4个B_VERIFIED成功内部更新仍是2736次，严格门槛全部通过。相对修复前B最大轨迹变化沿用已验证值0.244微米；未改善米级误差。
6. 本轮修改前源码/EXE在validation/b_joseph_integration/before；旧52SHA在baseline_freeze_v1.json，新52SHA在baseline_freeze_v2.json及validation/verified_integration/baseline_freeze.json。integration.patch只含本轮源码差异，保留已有其他脏工作。

未修改R、Q、P0、GIM和原抗差策略。没有提交或推送。新的IRLS抗差仍只在私有试验中，见 JOINT_HUBER_VALIDATION_REPORT.md。

正式使用：VS调试环境设置 `RTK_PPP_PROFILE=B_VERIFIED`，或运行根目录run_b_verified.cmd。单独 `RTK_PPP_BASELINE=B` 仍是历史B，不能误认为自动启用验证修复。
