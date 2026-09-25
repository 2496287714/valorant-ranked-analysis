# 阶段 3：逐场详情采集记录

## 采集方式（全自动，页面上下文内 fetch）

在战绩页 Console 用登录态直接调用 WeGame 接口（脚本见会话记录，思路如下）：

1. `GetBattleList` 游标分页取全量列表：
   - 请求体：`{"from_src":"valorant_web","size":11,"queueID":"competitive"}`
   - 翻页游标：`"after":"<上页末条 dtEventTime 去掉 -: 空格>"`，如 `20260914164250`
   - 注意：`page` / `offset` 参数无效，`size` 仅 10/11 有效，传 20 直接报 8000002
   - 列表本身已含：地图、特工 id、段位 tier、RR 增减、回合数、时长
2. `GetBattleDetail` 逐场取细项：
   - 请求体：`{"apEventId":"<对局UUID>","from_src":"valorant_web"}`
   - `battle_detail.players` 中按本人 `subject`（`e6a92ccf-…`）定位自己的统计
3. `GetChampion` 取特工 id→中英文名映射（29 名特工）

## 字段清单（battles_detailed）

胜负、地图、特工（中/英）、段位 tier、RR 增减及赛后 RR、回合数、
KDA 及 KDA 比率、表现评分 score、爆头/身体/腿部命中数及爆头率、
总伤害及 ADR、经济评分、首杀、安放/拆除、残局 clutch、王牌、
thrifty、flawless、三/四/五杀、时长、MVP/SVP。

## 已知数据缺口（如实记录）

- **KAST**：接口返回的 `kast` 字段 73 场全部为 0，判断为国服后端未回填，非采集错误。
- **performanceScore**：列表与详情中均为空串，该字段未启用。
- 地图代号全部核实完成（官网/BWIKI/VALORANT Wiki）：
  Ascent 亚海悬城、Triad 隐世修所、Bonsai 霓虹町、Juliett 日落之城、
  Infinity 幽邃地窟、Jam 莲华古城、Foxtrot 微风岛屿、Plummet 天枢云阙。
  共 8 张图（跨赛季图池轮换，故多于单赛季 7 张）。
- 段位 tier 数字（如 11）与国际服 tier 表不一致，未硬编码段位名，数字原样保留。

## 校验结果

- 73/73 场详情成功；与阶段 1-2 数据按日期+KDA 逐项核对，0 处不一致
- 数值范围人工核验：爆头数 ≤ 击杀数；回合 13~30；时长 19.8~55.4 分钟；无异常行
