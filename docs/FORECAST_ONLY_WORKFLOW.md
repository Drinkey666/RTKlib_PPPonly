# 预报文件产品专用验证入口

2026-10-20配置统一：本入口现共用`config/b_verified.json`，正式选择B_VERIFIED、PPP_COMMON、LEGACY估计器、nf=4、G/E/C、GLO/E5b关闭。下述原PHYSICAL固定配置记载是2026-10-17历史版本，不再是默认；预报段、EXTCLK及产品接收证据检查保持。归档回放另见`run_ppp.cmd`，不能借归档模式宣称通过历史实时可用性认证。

2026-10-17。当前工作主线为文件预报产品支持的实时非组合PPP；SSR不接入。
既有FIN回放、A/B及数值修复证据保留作回归，不继续用FIN精度代表实时性能。

## 1. 本轮完成的内容

新增独立PC入口`run_forecast_ppp.cmd`与`tools/forecast_ppp.py`，调用原正式EXE的
`--check-files`，然后增加预报及可用性检查。没有修改C源码、工程、正式EXE、
R/Q/P0/GIM/抗差参数或Joseph实现。直接在VS启动原EXE不会自动进入此Python入口。

流程为：原产品检查 → 预报段/钟差来源检查 → 接收时间和文件哈希检查 →
仅在全部通过且显式`--run`时启动正式B_VERIFIED解算。检查失败不会创建pos/trace/stat。
每次使用独立输出目录，既有结果不被覆盖。

检查内容：

1. 复用原C检查器的时间范围、实际产品读取、OSB有效期、天线参考和卫星支持检查。
2. 按原检查器实际看到的卫星及观测时间范围，检查SP3观测区间及两端包围记录的
   轨道P/钟差P标记。不是凭NRT文件名判定；不会要求整份文件都是预报段。
   插值节点允许含同一已接收文件内的历史估计数据。
3. 本版专门支持WUM NRT：独立CLK没有逐记录P标记，因此还要求SP3/CLK同族、
   同起点标识，CLK声明PANDA-EXTCLK，且原检查器确认CLK覆盖。该推断不推广到任意机构。
4. NAV、SP3、CLK、BIA、IONEX、两份VMF、地形和ATX分别提供接收GPST、
   SHA256和接收记录说明；文件版本必须在观测开始前已接收。静态文件可以更早接收。
   不把文件系统修改时间、文件名或生成头当作实际接收证明。
5. 正式运行前再次核对输入哈希，检查后被替换的文件不能继续运行。

固定配置由`config/b_verified.json`统一提供：B_VERIFIED、CORRECTED生命周期、PPP_COMMON钟差、LEGACY估计器、nf=4、G/E/C、GLO/E5b关闭。继承环境中的其他RTK_PPP_*设置被清除，避免混入旧实验。它与`run_ppp.cmd`选择相同正式模型；严格检查本身不代表精度达标。

## 2. 使用方法

从`config/forecast_products.example.json`另存一份配置，填入实际文件及接收记录。
所有路径使用绝对路径。`received_gpst`采用`YYYY-MM-DD HH:MM:SS.ffffff`，
明确为GPS时间，不填UTC/北京时间，也不因没有历史记录而补造接收时间。
`sha256`对应实际输入的未压缩文件，`evidence`注明保存的下载日志/归档记录。
接收记录本身真实性仍取决于保存的原始日志，入口不声称独立认证FTP发布时间。

在项目目录运行：

```bat
run_forecast_ppp.cmd config\your_products.json
run_forecast_ppp.cmd config\your_products.json --run
```

第一条仅检查；第二条全部通过后运行。参数顺序采用“配置路径，再--run”。
默认Python路径是本机`E:\Program Files (x86)\python3\python.exe`，可用
`PPP_FORECAST_PYTHON`指定其他Python 3.11+；此工具仅依赖标准库。
RINEX用`source=rinex,max_epochs=0`处理完整所选文件，不悄悄截断。
TXT用`source=txt-fast`，可设正整数`max_epochs`。OBS键对两种来源都表示唯一观测文件；
工具会将TXT正确传入原程序的`RTK_PPP_TXT`，不会同时设置RINEX输入。

每次记录位于`validation/forecast_sessions/<唯一时间目录>/`：

- `forecast_session.json`：预测标记统计、预报龄期、原产品检查结果、接收时间、哈希和停止原因；
- `native_preflight.products.log`：原产品检查报告副本；
- 检查通过并运行后，另有`solution.pos`等原程序输出及`solver.console.log`。

## 3. 真实历史文件验证结果

见`validation/forecast_only/evidence.json`及各独立session：

| 案例 | 原C产品检查 | 新入口结论 | 是否启动滤波 |
|---|---|---|---|
| 3/17 FIN原输入 | 通过 | 不是预报段；接收记录不明 | 否 |
| 现有20260760500 NRT组合 | 通过 | 观测位于非预报段，CLK为LSQ；接收记录不明 | 否 |
| 20260742000真预报SP3/EXTCLK，保留FIN辅助产品 | 通过 | 预报识别通过；辅助产品等接收记录不足 | 否 |

第三例的SP3区间包围记录共258条，轨道与SP3钟差均为P；预报龄期约9.559小时。
这仅证明预报段识别，不会把保留FIN辅助产品的组合自动认证为实时产品组合。

新增单测24项，包括预报标记、混合段、错误时区、钟差不同批次、缺接收记录、
未来接收、哈希不符、只读性、检查后文件变化、失败不启动、TXT入口和RINEX截断参数。
三个真实文件案例均未生成解算输出。48个冻结正式文件SHA保持一致，无需重建C工程。
早期联调传入RINEX不支持的max_epochs导致停止，已修正入口并增加针对性单测；
历史失败session保留，不冒称其为产品失败。

## 4. 当前边界与后续工作

本轮完成的是**固定初始产品组合的PC检查/启动入口**。尚未实现：
自动下载并记录接收时间、按时间切换产品版本、热更新时保持状态和基准连续性、
Android端接入。未运行新的定位精度回放，也未证明此前米级误差已解决。

现有历史数据无法补造“当时已接收”事实；后续实时验收使用实际同步留存的观测和
接收记录。需要采用其他辅助模型时，先确认配置和物理参考，不自动去掉OSB、
外推过期OSB、把VMF或GIM替换成经验常数来凑齐输入。

今后精度对照优先使用本入口通过的同一文件组合与接收记录，同时供本项目和raPPPid使用。
FIN仅保留必要回归/辅助差异诊断，不再作为实时性能验收主线。新工作不得引入SSR、
信号级eta学习或凭真值调整R/Q/P0。
