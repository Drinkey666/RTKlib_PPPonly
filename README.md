# PPP_only

基于 RTKLIB 改进的 PPP 定位程序。此仓库只包含 Visual Studio 工程实际编译的源码，支持 RINEX 观测文件和 Android 原始 TXT 回放。`PPP_only/ppp_position.c` 是 PPP 专用的单历元定位控制器，核心滤波在 `src/ppp.c`。

## 构建

用 Visual Studio 2022 打开 `PPP_only.sln`，选择 **x64 / Release** 构建。生成的程序位于 `x64/Release/PPP_only.exe`。

## 运行

运行 `PPP_only.exe --help` 查看参数。无界面运行可用 `--no-gui`；先用 `--check-files` 检查观测文件和星历等精密产品路径。输入文件可通过 `RTK_PPP_OBS`（RINEX）或 `RTK_PPP_TXT`（Android TXT）选择，两者不能同时设置。精密产品可通过 `RTK_PPP_NAV`、`RTK_PPP_SP3`、`RTK_PPP_CLK`、`RTK_PPP_BIA`、`RTK_PPP_IONEX`、`RTK_PPP_VMF_FIRST`、`RTK_PPP_VMF_SECOND`、`RTK_PPP_OROGRAPHY` 和 `RTK_PPP_ATX` 指定；结果路径用 `RTK_PPP_OUTPUT` 指定。输入数据与精密产品未包含在仓库中。

PPP 启动仍使用 `pntpos.c` 获取粗位置。RTCM 模块保留了 PPP 可用的 SSR 路径及其链接依赖。其余 RTK、多厂商接收机协议、网络流、数据下载和格式转换模块不进入此工程。

源码保留原 RTKLIB 作者的版权声明。此工程在本地通过了 x64 Release 编译，以及 RINEX 1200 历元和 Android TXT 20 历元相对精简前版本的数值回归验证。
