# 联盟站文字墙 资料来源与复查流程（4901996）

## 1. 来源登记

| 项 | 值 |
|---|---|
| 站点名 | 澳门大联盟 4901996 |
| 页面主机 | `https://yyaann490137.4901996gg.app:8450` |
| 站点号 | `490137` |
| 栏目页 | `{页面主机}/book-detail?ruleId={ruleId}&lotteryType=1` |
| 数据 JS | `https://h3.wanpz.com/script/490137/dynamic_{ruleId}_1.js` |
| 彩种 | 只取澳门（macao），排除港彩、快乐8 |
| 访问方式 | 数据 JS 为静态文件，`curl -sk --compressed -A <iPhone UA>` 直连，免 token、免登录；页面首屏有滑块拼图，但数据 JS 不随滑块 |
| 解码方式 | JS 体 `var G_xxx=JSON.parse(__ras(atob('<b64>')))`：base64 解码 → JSON；`html` 字段是二次 JSON 串需再 `json.loads`；`__ras` 本族实测恒等，无需再解 |
| 栏目清单 | `textwall-rules.json`（ruleId → 标题，67 栏，来自详情页相关链接） |

## 2. 每条记录的复查字段（textwall-snapshot.json）

栏目级：
- `sourceUrl` / `jsUrl`：页面与数据 JS 路径，可直接复查
- `siteNo`、`fetchedAt`、`rawBytes`、`rawSha`：抓取时间、原始字节数、内容指纹（改料比对用）
- `kind`：kill 杀肖 / rec 推荐肖 / other 非生肖维度
- `hit` `miss` `unresolved` `total` `acc`(命中率) `missRate`(错误率) `cls`(good/bad/watch)
- `missingPeriods` / `missingCount`：近期窗口内源站漏发（未更新）的期号；`expected` 应发期数；`coverage` 覆盖率=已发/应发
- `changed` / `changedPeriods`：与上一次快照逐期比对，历史期生肖被改动即标记（改料）
- `mismatch`：站点自标「准/错」与我方独立对账不一致的期（靠谱度参考）

行级：`period` 期号、`zods` 该期生肖、`openedText` 站点开号文本、`openedZod` 站点开肖、`officialZod` 官方特肖、`verdict`(hit/miss/null)、`selfMark` 站点自标。

## 3. 对账口径（只对标特号特肖）

- 官方历史：`ismkog...:21044/api/v1/lotteries/macao/histories?year=2026`，特号=7 球最后一个，特肖按号码生肖表换算；缓存 `official-history.json`。
- 杀肖 kill：特肖在被杀肖里 → `miss`(错)，否则 `hit`(准)。
- 推荐 rec：特肖在推荐肖里 → `hit`，否则 `miss`。
- 官方未开出（315 期）→ `unresolved`，不计命中率。
- **缺更计错**：源站某期没发资料（漏更/藏掉错期），视为未交付，计入 `miss`；窗口取最晚期号往前回溯该栏目已发期数那么多期，避免早年串入期号或上墙截断把旧期误算成缺更。`miss` 含缺更期，命中率=命中/(已发+缺更)。
- 分类阈值：已结算样本 ≥10 且命中率 ≥70% = good；<70% = bad；否则 watch。
- 注意：杀肖天然容错高（只杀 1~3 个肖），宽肖推荐（七肖/六肖）覆盖率高、命中率虚高；窄肖（一肖/三肖）命中率更能说明问题。

## 4. 复跑流程

```
python3 textwall_reader.py fetch      # 拉全部 JS → 解码解析 → 对账 → 写 textwall-snapshot.json
python3 textwall_reader.py reconcile  # 只用已落盘结果重算统计
```

- 开奖后重跑 `fetch` 即可：新一期自动对账；历史期若被站点改动，`changedPeriods` 会标出。
- 新增套娃镜像站：在 `textwall_reader.py` 的 `SOURCE` 追加站点号/主机/JS 模板，ruleId 清单另存 rules 文件即可复用同一套解析对账逻辑。

## 5. 已知边界

- 尾/波/头/段/单双/大小/五行/方位/家禽野兽/成语典故等非生肖维度，解析不出生肖，标 other/nonZodiac，不计肖命中率。
- 部分码类栏目（⑨码/六码复式/16码/五码）只给号码不给生肖，按号码资料另算。
- 315 期未开奖，全部 unresolved；当前命中率基于 294~314 期历史。
- 其它套娃镜像站的站点号与 ruleId 尚未枚举，待接入。
