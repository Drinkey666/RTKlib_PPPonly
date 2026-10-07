# PPP 数值参数与硬编码审计

对象、版本和行号同 [BASELINE_AUDIT.md](BASELINE_AUDIT.md)，本轮不调整任何数值。来源分类：**RTK**=官方b34可定位到同类逻辑/常数；**历史**=当前扩展，未找到项目标定记录，不能宣称有文献证明该具体取值；**模型**=物理/经验公式常数，保留公式来源；**结构**=维度/编码；**数值**=程序保护，不代表统计置信水平。RTK出处是[官方PPP源码](https://raw.githubusercontent.com/tomojitakasu/RTKLIB/v2.4.3-b34/src/ppp.c)，这里只核对继承，不认定每个手机参数已获科学标定。

“应配置化”指将来统一实验配置/manifest应记录，不表示本轮已新增开关。单位为标准差的参数，使用时通常要平方；倍率明确分为方差倍率或标准差倍率。同一个数在不同位置不能共享一个含义。

## 1. R0 和各类倍率

| 参数/数值 | 单位 | 文件/函数/行号 | 控制与实际生效 | 来源/依据 | 后续配置化 |
|---|---|---|---|---|---|
| err[1]=0.008，err[2]=0.012 | m，phase sigma项 | smartphone_ppp_config.c:30；ppp.c varerr912–914 | a²+b²/sin²(el) | 历史；结构有RTK依据，具体手机取值标定未提供 | 是，共同R0固定 |
| eratio=100,70,60,100 | 码/相位标准差比 | config:31–32；varerr904–914 | 噪声band对应a/b先乘后平方；不是方差×100 | 历史profile；概念RTK | 是，按实际code/band日志 |
| eratio fallback=100 | 标准差倍率 | ppp.c varerr906 | 无有效比值时回退 | 历史/防缺参，不是数据估计 | 是/非法参应显式报告 |
| IFLC fact×3 | 标准差倍率 | varerr909 | 方差近似×9 | RTK家族近似，当前IFLC非主方法 | 记录，后续与真实组合传播分开 |
| 5° | deg | varerr911；udiono2176 | sin高度角下限 | 历史数值保护；默认elmin15°一般更强 | 是 |
| 码floor=1²，相位floor=0.01² | m² | varerr956/973 | 方差下限，不覆盖随后模型误差 | 历史，具体值无标定证据 | 是，单独命名 |
| CN0=40,35,30,25 | dB-Hz | varerr965–969 | 分段定权拐点 | 历史经验 | 是 |
| CN0斜率0.2,0.4,0.8 | 方差倍率/(dB-Hz) | varerr966–968 | 1→2→4→8 | 历史经验 | 是 |
| CN0低于25→12；缺失→4 | 方差倍率 | varerr969/971 | 低CN0/缺测降权；25处8与低于25的12不连续 | 历史经验，无具体检验来源 | 是；先记录不改 |
| 35.0回退 | dB-Hz | ppp_res3038 | 无可表示frq时回退，未乘SNR_UNIT | 数值/历史；正常frq读实值 | 记录，未发现单位错误 |
| SIGW默认1，允许1..100 | 方差倍率 | signal_weight_ppp851/861–863 | 各实际signal的码/相位标定倍率 | 历史可选，不按真值默认设偏好 | 已有，应入统一配置 |
| WGTELCN=0（可选1/2） | 模型选择 | config:15；varerr922–928 | 默认不启用联合模型 | 历史 | 已有 |
| 35.0833,0.1365,-0.0005 | dB-Hz，dB-Hz/deg，dB-Hz/deg² | varerr883/930–936/948 | CN0高度角二次拟合 | 注释指Li等Sensors2022,22,2804小米MI8；本轮未独立核验该公式全部系数，对当前机型适用性未知 | 已有WGTCNA/B/C，需标定出处 |
| 10..90°；CNmax45/40，CNmin25/20 | deg，dB-Hz | varerr939–946 | 联合模型夹限及归一化 | 历史/论文注释，非本机验证 | 是 |
| CN0有效上限100；系数界100/10/1 | dB-Hz；相应系数单位 | varerr926/938 | 联合模型数值检查 | 数值/历史 | 统一验证，不调优 |
| BDSCODEVAR=1，范围1..100 | 方差倍率 | config:15；ppp_res2815–2820/3042 | BDS码额外倍率 | 历史，当前默认无放大 | 已有 |
| BDSCODEWARM=120，夹0..600 | s | config:15；ppp_res2821–2833 | BDS倍率从1渐变；factor=1时不影响 | 历史经验 | 已有，完整B需记录 |
| CODENOPH默认1，范围1..100 | 方差倍率 | ppp_res2799/2810–2814/3043–3044 | 同星无相位且非warmup额外码方差 | 历史，默认无影响 | 已有 |
| GLO_IFB=0.6² | m² | ppp.c:133；ppp_res3050 | GLO码模型误差 | RTK；默认未开GLO | 记录 |
| 对流层模型sigma=0.01 | m | trop_model_prec2489 | EST剩余模型方差 | RTK家族 | 记录，勿与相位floor混同 |
| ERR_SAAS=0.3 | m | ppp.c:135；model_trop2503 | SAAS模型sigma | RTK | 记录 |
| ERR_BRDCI=0.5 | 无量纲sigma比例 | ppp.c:136；model_iono2539/2545 | 广播电离层sigma=|I|×0.5 | RTK家族 | 记录 |
| TEC失败BRDC sigma最低2 | m | model_iono2539 | TEC缺失回退的宽松方差 | 历史保护，EST默认不走 | 是 |

## 2. 当前抗差、持续处罚和隔离

| 参数/数值 | 单位 | 位置（ppp.c，除另注） | 控制 | 来源/依据 | 后续配置化 |
|---|---|---|---|---|---|
| THRES_ROBUST=4 | R-only标准差倍数 | 118；ppp_res3088 | 当前历元平方处罚起点 | 历史；非标准Huber权 | 是，A关B保留 |
| THRES_REJECT=8 | R-only标准差倍数 | 119；ppp_res3108 | 验后硬拒绝 | 历史，官方b34同名值4，不能沿用相同检验解释 | 是 |
| penalty上限25 | 方差倍率 | ppp_res3090 | 最大当前历元降权 | 历史经验 | 是 |
| MAX_ITER=16 | 编辑轮次 | 115；pppos3796 | 每轮最多删一行；超限不提交 | 历史（b34不同），不是额外独立观测 | 是 |
| SIGQC默认1；SIGQCPH默认0 | 开关 | prepare_signal1404；persistent2614/2618 | 残差历史检测，默认只自动处罚码 | 历史隐式默认 | 已有，须入manifest |
| persistent factor=4 | 方差倍率 | persistent_variance_factor2619 | weak持续处罚 | 历史经验 | 是 |
| weak进入5次且跨度≥4 | 次；s | signal_quality_step2594 | 坏检测迟滞 | 历史，无标定证据 | 是 |
| 恢复10次且跨度≥9 | 次；s | signal_quality_step2600 | 好检测迟滞 | 历史 | 是 |
| quality重置gap5；prepare重置gap10 | s | signal_quality_step2588；prepare1405 | 间断/倒序清历史，不同层间隔不同 | 历史 | 是/明确差别 |
| count饱和255 | 次/uint8容量 | quality2593/2599；CMC2735；quarantine3373 | 防计数溢出 | 结构/数值 | 常量命名即可 |
| peers≥5；MAD因子1.4826 | 星；无量纲 | update_signal2661/2664 | 同sys+signal+type空间检测 | 历史；1.4826为高斯MAD尺度，5星门限无验证出处 | 是（MAD转换可固定） |
| 坏：>max(4sigma,6MAD)；好：z<2 | sigma/MAD倍数 | update_signal2669 | 质量迟滞证据 | 历史经验 | 是 |
| SIGCMCDRIFT默认0，允许0..30 | m | update_cmc2694–2695 | 漂移阈值，0关闭 | 历史实验，默认关闭 | 已有 |
| CMC weak×4 | 方差倍率 | ppp_res3079 | 下一历元码处罚 | 历史经验，可能与SIGQC叠加 | 是 |
| CMC EMA0.10；第10次设参考；成熟30次 | 无量纲；次 | update_cmc2734/2738/2744 | 均值/参考/启动持续检测 | 历史经验，不是eta学习 | 是 |
| CMC恢复threshold×0.5 | 无量纲 | update_cmc2746 | 恢复迟滞 | 历史 | 是 |
| CMC gap=max(3,2.5|tt|) | s；无量纲 | update_cmc2725；diag3478 | 弧连续性/诊断重置 | 历史 | 是 |
| PPPQUAR=3,120；触发至少2，至20 | 次；s | config:16；quarantine3335–3338 | 连续历元相位拒绝后隔离 | 历史经验 | 已有 |
| 隔离hold≤120，backoff≤600，等级≤7 | s；等级 | quarantine3338/3378/3383–3384 | 重复坏弧延长隔离 | 历史经验 | 是 |
| 正常连续120；拒绝间隔>5重置streak | s | quarantine3361/3369 | 清退避/连续性 | 历史 | 是 |

## 3. 周跳、预检、SPP 与数据入口

| 参数/数值 | 单位 | 位置 | 控制 | 来源/依据 | 后续配置化 |
|---|---|---|---|---|---|
| GF thresslip=0.20 | m | config:34；ppp.c1504/1517 | GF跳变 | 历史手机参数；GF方法RTK | 已有 |
| DOPPSLIP=0.50，范围0..10 | m | config:14；precheck1638 | phase-Doppler差（去系统共模） | 历史经验；30s后检测可能失效H-01 | 已有 |
| CODEJUMP=30，范围0..1000 | m | config:14；precheck1639/1717 | code-Doppler局部异常 | 历史经验 | 已有 |
| MWTHRES=5，范围0..100 | m | config:14；detslp_mw1554 | MW跳变 | 方法RTK，阈值历史 | 已有 |
| Doppler测试dt=0.2..5 | s | detslp_gf1531；MW1570；precheck1669 | 时间连续性准入 | 历史 | 是 |
| 相位/Doppler时间对齐0.05 | s | precheck1675 | 历史时间一致性 | 历史经验 | 是 |
| 同系统共模至少3星；中位至少3行 | 星；行 | precheck1693–1699/1708/1717 | 允许共模/单星检测 | 历史；行和distinct星计数不同 | 是 |
| 共模码相差max(5,CODEJUMP) | m | precheck1701 | 大共同钟跳只重置码平滑 | 历史经验 | 是 |
| STARTQC默认1、PREPROC默认0(profile1) | 开关 | ppp_position201–206；ppp.c3696 | SPP启动、预检总开关 | 历史 | 已有，必要与实验策略应拆 |
| 启动窗口30 | s | ppp_position274/278/328；ppp.c1636/1772 | SPP/启动码质控及历史保存窗口 | 历史，与开题多指标稳定阶段定义不同 | 是 |
| startup spatial peers4(码对)/5(绝对码) | 星/观测组行 | precheck_startup1817 | 启动空间检验 | 历史 | 是 |
| 启动MAD1.4826、6倍；最小30 | 无量纲；m | startup1820–1821 | 动态门限下限/组散度 | 历史；MAD换算数学依据 | 是 |
| 启动位置门控4sqrt(sum qr) | 无量纲×m | startup1776 | 位置不确定度粗门控 | 历史，不是完整hPh投影 | 是 |
| SPP min dof2、30m且z>6 | 自由度；m；标准化残差 | pntpos.c594/608 | 杠杆值修正验后启动剔除 | 历史 | 是 |
| leverage floor0.05 | 无量纲 | pntpos.c607 | 防近1杠杆值分母过小 | 数值/历史 | 是/明确影响 |
| SPP FDE最多3；score改善至×0.5；初次阈9 | 轮；无量纲 | pntpos.c626/629 | 启动有限试排除和改善判据 | 历史 | 是 |
| maxout=30；GAP_RESION=120 | 缺测历元数（ep），非秒 | config:37/12；ppp.c2250/2133 | ambiguity/ion outage重置 | RTK机制，profile历史 | 已有，变采样时标注 |
| outc最小搜索哨兵1,000,000,000 | 次 | udiono2129 | 多频缺测计数最小值初始化 | 数值/结构 | 命名，不调优 |
| 0.0005*c，k≥2 | 0.5ms对应米；条数 | udbias2348 | 大共同码相偏移修正 | RTK逻辑（不是普通米级残差校正） | 记录 |
| GPST×10 round mod864000 | 0.1s刻度/日界 | udbias2231 | posopt[5]日界保护 | RTK继承；非实际钟跳检测 | 记录/profile默认关闭 |
| P范围1E6..1E8；L绝对值≤1E12 | m；周 | ppp_position220–227 | 原始观测数值筛选 | 历史/数值 | 统一保护 |
| D绝对值≤20000 | Hz | ppp_position229；ppp.c1293/1529/1666/1734 | 极端D拒绝/平滑无效 | 历史/数值 | 是/准入共用 |
| 地心坐标norm>1E6 | m | ppp.c1302/1774 | 合法粗位置保护 | 数值/历史 | 命名 |
| STD_PREC_VAR_THRESH=0 | m² | PPP_only/ppp_position.c:7/272 | P[0]>0时仍每历元调用SPP，不是达到PPP精度就跳过SPP；影响粗解/钟差/sol.time | 历史硬编码 | 是/记录，不本轮改变调用节奏 |
| elmin=15 | deg（内部rad） | smartphone_ppp_config.c:35；ppp_res2855 | 高度角准入，区别varerr内部5°下限 | profile历史；常见默认不等于本机标定 | 已有/成对固定 |
| ADR uncertainty默认1.0 | m标准差准入 | adapter59；pc_txt_replay39；adapter255 | 手机相位准入，不直接构造R | 历史 | 已有，RINEX同类信息缺失需记录 |
| receivedSVtime uncertainty≤500 | ns | adapter171/225 | 码时标准入 | 历史 | 是 |
| range-rate uncertainty≤10 | m/s | adapter243 | Doppler准入，不直接作为R | 历史 | 是 |
| flight time0.001..0.200 | s | adapter234 | 伪距飞行时合法性 | 数值/历史宽门限 | 是 |
| ADR magnitude>1E-4 | m | adapter174/251 | 排除零相位哨兵 | 数值 | 命名 |
| signal selection score100/40/10/5/CN0≤60 | 无量纲分数；dB-Hz上限 | adapter168–179 | 同sat槽优选一signal | 历史；不是EKF权重 | 记录，入口策略固定 |
| SNR_UNIT=0.001、uint16上限65535 | dB-Hz/整数刻度 | rtklib.h168；adapter220–221；rinex899 | 35dB-Hz存35000；adapter饱和至65.535dB-Hz | RTK数据结构；不是35再×0.001的回退错误 | 结构共用，RINEX读溢出极端值待防护 |
| GALE5BPHASE=0 | 信号准入开关 | config16；ppp.c289–296 | 默认排除GAL7Q；其他7I/X另有路径 | 历史依据为源码所称多数据集表现，本轮未复核标签/标定集 | 已有/冻结信号清单 |

## 4. 初始协方差与 Q

| 参数/值 | 单位 | ppp.c位置/函数 | 控制 | 来源/依据 | 后续配置化 |
|---|---|---|---|---|---|
| VAR_POS=60² | m² | 123；udpos1853/1869/1877 | 位置初值、过大P复位 | RTK | 是/记录 |
| VAR_VEL=10² | (m/s)² | 124；udpos1855/1880 | 速度初值 | RTK | 记录 |
| VAR_ACC=10² | (m/s²)² | 125；udpos1856/1881 | 加速度初值 | RTK | 记录 |
| VAR_CLK=60² | m² | 126；udclk1944/1957 | GPS白噪声/ISB初值 | RTK家族，ISB连续语义历史 | 是 |
| VAR_GRA=0.01² | 梯度状态量的方差 | 128；udtrop2005 | ESTG初始化；dtdx形式中梯度是湿映射的相对梯度参数，不宜无条件标成m² | RTK家族；默认EST不启用 | 记录语义 |
| VAR_IFB=10² | m² | 130；uddcb2199 | 实际signal RCB初值 | 历史 | 是 |
| VAR_BIAS=60² | m² | 131；udbias2390 | 浮点phase bias初值/重启 | RTK | 是 |
| VAR_IONO=10² | L1垂直延迟m² | 132；udiono2170 | 无IONEX时广播初值宽方差 | 历史（状态语义/具体方差不同于官方），无手机标定证据 | 是 |
| profile prn[0]=1E-4，[1]=1E-3，[2]=1E-4 | 相应状态单位/√s | config36；udbias2364/udiono2177/udtrop2009 | 固定bias/ion/ZTD随机游走 | RTK传播结构，profile历史 | 已有/同组固定 |
| ISB过程sigma=0.10 | m/√s | udclk1961 | 相对钟偏连续随机游走 | 历史写死 | 是，不调参 |
| RCB过程sigma=0.01 | m/√s | uddcb2204 | 接收机码偏差随机游走 | 历史写死 | 是，不调参 |
| 梯度Q sigma×0.1 | 标准差倍率 | udtrop2013 | 估计梯度过程噪声 | RTK | 记录 |
| prn[3]=0.1，[4]=0.01，[5]=0 | 加速度单位/√s；位置m/√s | rtkcmn.c216；udpos1921–1922/1862 | 动态加速度Q/静态位置Q；当前静态位置Q0 | 当前默认继承，不是在线学习 | 同组冻结 |
| thresar[1]=0.25 | 平均位置方差m²门限 | rtkcmn218；udpos1897 | 动态模式是否加入加速度位移项 | 历史/demo分支风格，默认静态不走 | 单独命名配置，不复用AR名字 |
| fixed坐标P=1E-8 | m² | udpos1848 | PPP_FIXED硬固定坐标 | RTK；非研究默认静态 | 记录，不把真值设固定 |
| 近零状态1E-6；bias0替代1E-4 | 对应状态单位 | udpos1856；udclk1957；udiono2155/2169；uddcb2199；udbias2338 | 激活x!=0压缩滤波 | 数值哨兵，不是测量误差/学习尺度 | 命名保留，监测 |
| ion近零判据1E-8，巨大判据1E4 | m | ionex_prior2099；udiono2155/2168–2169 | 先验合法性/激活 | 数值/历史 | 是 |
| variance计算floor1E-12 | m² | ppp_res3054/3177；smooth1339 | 防标准化分母0 | 数值，MAX宏不替代NaN检查 | 命名/有效性检查 |

## 5. 大气产品和时间信息

| 参数/数值 | 单位 | 位置（ppp.c除另注） | 控制 | 来源/依据 | 后续配置化 |
|---|---|---|---|---|---|
| IONCONS sigma=1.5，夹0.20..10 | L1垂直延迟m | 146–148；ion_constraint_sigma2020–2036；config12 | GIM先验方差下限；0不能关约束 | 历史经验，RMS缺失保护 | 已有；另加on/off |
| IONCONSINT默认/配置1，范围1..86400 | s | 149；ion_constraint_interval2041–2051；config12 | information=min(1,dt/interval)，默认1Hz每历元一份 | 历史；非实测相关时间 | 已有 |
| ION_CONSTR_ROBUST=3，MAXPEN=25 | R-prior sigma倍数；方差倍率 | 150–151；ppp_res3179–3182 | 虚拟电离层残差软化 | 历史经验，无hPh分母 | 是 |
| VMF3SIG默认0.20，profile0.15，夹0.05..2 | 总ZTD m标准差 | 159–161；vmf3_init_sigma526–534；config12 | ZTD初始化P，实际用0.15²；不是连续约束sigma | 历史 | 已有 |
| VMF3ZWDSIG默认0，profile0.30，夹0.05..2 | 湿先验m标准差 | sigma542–553；config13 | 0关VMF虚拟观测，profile开 | 历史经验 | 已有 |
| VMF3ZWDINT=300，夹1..3600 | s | interval558–568；config13 | 先验信息预算，1Hz无抗差时R=27m² | 历史近似；非严格相关模型 | 已有 |
| VMF3_ZWD_ROBUST=3，MAXPEN=25 | sigma倍数；方差倍率 | 162–163；ppp_res3243–3251 | 湿先验软化 | 历史经验 | 是 |
| legacy dt floor0.1 | s | ppp_res3185/3249 | STATMOD0的interval/dt保护 | 历史数值；dt太长VMF可能过度给信息 | 记录旧路径 |
| STATMOD默认3，范围0..7，位1/2/4 | 位掩码 | statistical_model1174 | 平滑统计、先验记账、可选时间相关膨胀；B当前不是0 | 历史 | 已有/显式默认 |
| DOPPSM profile0.90，夹0..0.995 | 1s旧预测保留比例 | config13；doppsm1126–1134 | alpha=factor^dt；0关 | 历史经验 | 已有 |
| DOPPWARM默认/profile0，夹0..300 | s | warmup1138–1146/1235；config13 | 码阶段，切入相位重置ambiguity | 历史固定时长；不符合开题全部稳定条件 | 已有 |
| 平滑reset dt>5；STATMOD0 dt<0.2 | s | uddoppsm1314 | 因果缓存连续性 | 历史经验 | 是 |
| Doppler sigma err[4]=1 fallback | Hz | rtkcmn214；uddoppsm1311–1313 | ratevar=(λsigmaD)² | 当前通用配置，不含每signal安卓rate uncertainty | 已有/日志 |
| VMF3格网36×72，87.5/2.5/5 | 行列；deg | 156–158；interp429–445 | 5°格点顺序/经度周期 | 产品结构；readvmf3读取lat/lon但未验证顺序，只按行号使用 | 验证格式，非噪声调参 |
| VMF3 bh0.0029/ch0.0620/bw0.00146/cw0.04391 | 无量纲映射系数 | vmf3_trop498–507 | 固定b/c近似，非完整官方VMF3 | 历史近似；[官方代码](https://vmf.geo.tuwien.ac.at/codes/vmf3.m)实际按位置/季节求b/c | 模型版本化，先不替换 |
| height mapping aht2.53E-5/bht5.49E-3/cht1.14E-3；h/1E3 | 无量纲；m转km | vmf3_trop500/508–509 | 静力映射高度改正 | Niell类模型常数，源码注释；不是手机经验R | 保留出处，不标定 |
| 0.00266，0.00000028，0.0022768 | 无量纲、m⁻¹、m/hPa | interp461–465 | ZHD/压力高程归算 | 源码注明Kouba(2008)模型，未逐篇重核 | 保留公式 |
| 0.0000226，5.225；湿标高2000 | m⁻¹；幂；m | interp463/466 | 干延迟高程律、湿指数归算 | 模型近似，非在线学习 | 保留模型版本 |
| 合法ZHD1.5..3.0、ZWD0..1.5 | m | interp478–479 | 气象产品有效性保护 | 历史宽门限 | 是/产品校验 |
| 40.30E16/FREQL1² | m/TECU | ionex.c383/412–413 | TECU→L1米，并正确平方传播RMS | 标准一阶电离层物理公式 | 物理常数不调优 |
| REL_HUMI0.7 | 相对湿度0..1 | ppp.c138；model_trop2502 | SAAS估算 | RTK经验默认；非ZWD单位转换 | 记录 |

## 6. 结构、物理常数与未生效宏

| 值/参数 | 单位 | 位置 | 作用/生效 | 来源 | 配置建议 |
|---|---|---|---|---|---|
| NFREQ4、MAXOBS96、MAXSAT197、NCLK5、NIFB5 | 维度 | rtklib.h160/251/256；ppp.c192/206–223 | 本构建999状态、最多968预留行 | 结构/当前模型，改变需重新分配所有状态 | 构建/manifest记录，不做运行时自由切换 |
| MIN_NSAT_SOL4 | 星 | ppp.c117；update_stat3572；degraded3899 | 载波/码降级可用性 | RTK家族几何最低数；不能代表完整rank验证 | 记录 |
| MAX_STD_FIX0.15 | 3D位置sigma范数m | ppp.c116/3873 | AR后判定固定 | RTK，当前AR OFF且ppp_ar返回0 | 记录，不默认实验 |
| VAR_ZTD0.15²、VAR_DCB30²、ERR_CBIAS0.3、THRES_MW_JUMP10、EFACT_GPS_L5 10 | m²、m²、m、MW阈米、标准差倍率 | ppp.c127/129/137/121/165 | **仅定义未被本文件执行逻辑引用**；实际ZTD从VMF3SIG、MW从MWTHRES等取值 | 混合继承/历史；不能据宏名认定生效 | 标明死宏，低优先级整理 |
| MUDOT0.00836/0.00888×D2R，EPS13.5/14.2°，POSTSHADOW1800s，QZS_EC_BETA20° | rad/s、rad、s、deg | ppp.c167–172 | 仅定义；yaw_angle731仅名义yaw，不使用这些完整姿态阈值 | RTK头部遗留 | 不误当调优开关 |
| yaw近零1E-12 | rad | yaw_nominal723 | 避免几何退化 | 数值/RTK家族 | 命名 |
| acos夹[-1,1] | 无量纲 | testeclipse707；model_phw811等 | 浮点定义域保护，不能替代全模型非有限检查 | 数值/RTK | 保留 |
| freq差平方<1 | Hz² | corr_meas1110 | IFLC除零保护 | 数值 | 命名 |
| c、fL1、卫星实际freq、π、D2R/R2D、RE_WGS84、OMGE | m/s、Hz、rad/deg、m、rad/s | rtklib.h；ppp各改正函数 | 物理量，不是可按真值调节的经验阈值 | 物理/标准模型 | 不调优，记录模型版本 |
| 1E9、1E-9、604800、14s | s/ns转换、周长、BDT与GPST差 | pppoutstat619；gnss_adapter113–115/228；gnss_raw.h | 输出钟差ns及输入时标换算 | 时间系统定义/结构 | 验证单位不拟合 |
| 0.005；900；无条件var×100 | 示例值/逻辑 | 对当前ppp.c的逐字搜索 | **未发现当前PPP执行路径存在用户示例**；100多处为eratio或可选倍率上限，不能混称 | 不作为错误报告 | 无需新增这些参数 |

## 7. 完整字面量索引与检索边界

随附 [MAGIC_NUMBER_OCCURRENCES.csv](MAGIC_NUMBER_OCCURRENCES.csv) 是本轮生成的**源码字面量索引**：覆盖 `ppp.c`、`ppp_position.c`、共用profile、adapter、signal policy、pntpos全部非注释数字及字符串（故包括pppopt默认值），并补充 rtklib.h/rtkcmn.c/ionex.c/rinex.c/preceph.c。列为文件、函数上下文、行号、字面量、该行源码。字符串中的数字只是文本/格式，也列出防遗漏，不等于其执行为算法参数；注释历史日期不列入。索引还保留循环0/1、矩阵维度、printf精度和协议编码等结构数字，它们不是必须可调的magic number。

上表对研究相关的阈值/先验/R/Q/单位/结构已给出语义、单位和来源；其余星历、ANTEX、RINEX/RTCM协议及物理模型内部常数不视为本轮手机噪声参数调优对象。索引共11,497条出现记录；函数列只是最近函数声明上下文，跨全局声明时不能当作完整C语法解析结果。索引支持查同值多位置，不能自动替代数值来源证明。所有“历史”参数在没有独立标定文件/文献公式核验时保留为经验，后续配置化也不能赋予其科学有效性。

改变阈值前必须固定标定/验证分割，记录默认值、实验覆盖值和实际生效值。当前本轮仅审计，不依据测试真值反向调R。
