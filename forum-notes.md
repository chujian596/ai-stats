# 公开论坛文字帖 资料来源与复查流程（ismkog 明文后端）

## 1. 来源登记

| 项 | 值 |
|---|---|
| 站点名 | 17图库公开论坛 |
| 后端 BASE | `https://ismkog.xn--n8jaf0byahm4a2c4cybyssjl201en76e.xn--q9jyb4c:21044` |
| 彩种 | 只取澳门（macao），排除港彩（hongkong）、快乐8 |
| 访问方式 | 明文 JSON，CORS `*`，免 token、免登录；`curl -sk --compressed -A <iPhone UA>` 直连（Python urllib 在本环境 502，须走 curl） |
| 列表接口 | `GET /api/v1/forums?lottery=macao&page={page}&per_page=200`（返回 `{data:[]}`；`per_page` 上限 200，传 500 被截回 200；type/kind/category/is_recommended 等筛选参数均被忽略） |
| 详情接口 | `GET /api/v1/forums/{id}`（`data.content` 为 HTML，一行一期，自带约几十期历史与准/错标注；列表只给当期摘要，必须按 id 拉详情） |
| 评论接口 | `GET /api/v1/forums/{id}/comments`（200，但多为短评/图片灌水，次要源，暂未解析） |
| 图库列表 | `GET /api/v1/forums/galleries/macao?page={page}&per_page=50`（**裸数组**，非 `{data:[]}`；只给当期，旧期翻不到） |
| 官方历史 | `GET /api/v1/lotteries/macao/histories?year=2026`，特号=7 球最后一个；缓存 `official-history.json` |

## 2. 查询/抓取流程（forum_reader.py）

1. 翻全部分页（`FORUM_MAX_PAGES`，默认 60 页，每页 200），按帖子 id 去重；本轮全量 5994 帖。
2. 按标题归类：含「杀/禁/亡/绝」且有「肖」→ kill 杀肖；含「肖/中特/平特」→ rec 推荐肖；其余 other。
3. 对 kill/rec 帖按 id 拉详情（`FORUM_DETAIL_CAP`，默认上限 4000，本轮 1500）；详情正文落 `forum-details-cache.json`（可再生中间产物，**不上传仓库**），断点续跑命中缓存不重复下载。
4. 解析：去 HTML 标签、解实体、按期号 `\d{2,3}期` 切段；前半段（「开」之前）提取生肖字（去重保序）；后半段取开肖/号码/站点自标；同期号重复保留首行。
5. 对照官方特肖独立对账，汇总命中率/错误率/分类，登记每条来源与指纹。

## 3. 每条记录的复查字段

全量 `forum-snapshot.json`，精简 `forum-summary.json`（页面只加载汇总）：

栏目级：
- `threadId`、`name`(发布者昵称)、`topic`(标题)、`kind`(kill/rec/other)
- `sourceUrl` / `apiUrl`：详情接口路径，可直接复查
- `fetchedAt` 抓取时间、`rawSha` 内容指纹（改料比对用）
- `hit` 准、`miss` 错、`unresolved` 待开、`total` 已结算样本、`acc` 命中率、`missRate` 错误率、`cls`(good/bad/watch)
- `mismatch` / `mismatchCount`：站点自标「准/对/中」但我方对账为错的期（靠谱度参考）

行级（仅全量快照）：`period` 期号、`zods` 该期生肖、`openedZod`/`openedNum` 站点开肖开号、`selfMark` 站点自标、`officialZod` 官方特肖、`verdict`(hit/miss/null)。

## 4. 对账口径（只对标特号特肖）

- 杀肖 kill：特肖在被杀肖里 → `miss`(错)，否则 `hit`(准)。
- 推荐 rec：特肖在推荐肖里 → `hit`，否则 `miss`。
- 官方未开出（315 期）→ unresolved，不计命中率。
- 分类阈值：已结算样本 ≥10 且命中率 ≥70% = good；<70% = bad；否则 watch。
- 注意：杀肖天然容错高（只杀 1~3 个肖），宽肖推荐（七肖/九肖）覆盖率高、命中率虚高；窄肖（一肖/三肖）命中率更能说明问题。

## 5. 复跑流程

```
FORUM_MAX_PAGES=60 FORUM_DETAIL_CAP=1500 python3 forum_reader.py fetch      # 翻列表→拉详情→解析→对账→写两个 JSON
python3 forum_reader.py reconcile                                            # 只用已缓存详情重算统计
```

- 开奖后重跑 `fetch`：新一期自动对账；命中本地详情缓存，不重复下载。
- `forum-summary.json` 供 `stats.html`「论坛」标签页加载；`forum-snapshot.json` 为全量逐期明细存证。
- 本轮（2026-11-11，315 期未开）：拉详情 1500 帖，对账 1500（杀 73 · 荐 786 · 其他 641）；栏目级 good 119 · bad 306 · watch 434；未结算行 1504（315 期）。

## 6. 已知边界与未接入渠道

- 头/波/尾/段/单双/大小/五行/方位/家禽野兽/成语典故等非生肖维度，解析不出生肖，归 other，不计肖命中率。
- 正文跨年拼接（含上一年高期号如 365/366）：选「最新一期」时优先未开奖行、取距官方最新期最近者；远高于本年的旧年期号不进本期推荐。
- 评论区多为灌水短评/图片，暂未解析；图库图纸频道见 `gallery-notes`（待补）。
- 4901996 族其余 7 个套娃主机均为滑块壳，数据 JS 站点号/ruleId 未枚举，需浏览器过滑块后看网络请求；加密族（bdmijg/352722）未接入。
- 315 期未开奖，相关行 unresolved；当前命中率基于 2026 年已开奖历史。
