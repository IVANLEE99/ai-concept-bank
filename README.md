# ai-concept-bank

AI 短视频 / 日报 **技术概念库**：可检索、可复用、可防重复。  
服务「今日羊报 AI」的 **每期专业锚点（默认 15 秒）** 与报告中的技术一句。

> **不是** AI 百科、论文笔记或自动爬虫。  
> **是** 内容工具：每个正式概念都要能回答——  
> 1）什么新闻时讲？　2）15 秒怎么讲？　3）最近讲过没？

**仓库**：git submodule → [`IVANLEE99/ai-concept-bank`](https://github.com/IVANLEE99/ai-concept-bank)  
**版本**：1.0.0（20 ready + 27 candidate）

---

## 目录

```text
ai-concept-bank/
├── README.md                 # 本说明（唯一 SOP）
├── concepts.json             # 主库
├── usage-log.json            # 上线使用记录
├── agents/
│   └── ai-concept-narrator.md
├── prompts/
│   └── script-15s-request.md
├── extracts/
│   ├── term-frequency.json   # 全量语料频次（种子来源）
│   └── term-frequency.md
└── _archive/                 # 历史方案草稿（非主库）
```

| 文件 | 谁写 | 谁读 |
|------|------|------|
| `extracts/*` | 定期扫语料 | 裁定 seed 时人 + Agent |
| `concepts.json` | 裁定 + narrator + 审核 | 视频 / 日报 pipeline |
| `usage-log.json` | 每期用完后 | 选题 gap、复盘 |
| narrator agent | 维护人改 prompt | Claude 调 Agent 时 |

**禁止**再建 `news-pipeline/concept-bank/`。下游 skill 只认本目录。

---

## 一、要解决什么问题

全量脚本分析的结论：选题垂直，但技术深度接近 0。「每期塞一个专业解释」若靠临场发挥，会出现：

| 痛点 | 后果 |
|------|------|
| 概念随手抓 | 和当天新闻脱节，像硬上课 |
| 台词各写各的 | 口径不稳、易标题党 |
| 没有使用记录 | 同一概念连讲三天，或永远不讲高频词 |
| 库散落在 social_media / 方案草稿 | 下游 skill 不知道读谁 |

本库服务两条消费线（skill 按下方「下游约定」接入）：

- **日报 / 报告**：技术锚点一句（`one_liner`）
- **短视频**：每期 1 个专业锚点（默认 15s；周月可 30–60s）

---

## 二、设计原则（五条）

### 1. 语料决定「讲什么」

种子来自真实内容反提，不是方案文档拍脑袋。

| 语料 | 路径 |
|------|------|
| 视频脚本 | `news-pipeline/**/scripts/*.{md,txt}` |
| 日报 | `data/reports/*.md`（排除 `*_press.md`） |
| 周报 / 月报 | `data/weekly/*.md`、`data/monthly/*.md` |

提取结果见 [`extracts/term-frequency.json`](extracts/term-frequency.json) / [`.md`](extracts/term-frequency.md)。

**不收录**：公司名 / 型号本体、权益黑话（白嫖、号池…）、无法 15s 定义的八卦。  
**可收录**：能 15s 讲清，且不懂会妨碍理解新闻的技术概念。

重跑提取：内容风格大变或每月维护时，扫一遍语料，更新 `extracts/`，再裁定新 `candidate` / seed。

### 2. Agent 决定「怎么讲」

所有讲解台词 **只由 `ai-concept-narrator` 生产**（见下文铁律）。

### 3. 库只存「审过的成品」

状态机把「发现」和「能上片」拆开（见 status 流）。

### 4. 单一事实源、单一路径

```text
主数据：ai-concept-bank/concepts.json
使用：  ai-concept-bank/usage-log.json
SOP：   ai-concept-bank/README.md（本文件）
```

### 5. 可运营，不追求「一次建完」

日捡候选 → 周补台词 → 月重扫语料。少收录、持续更新，优于一次塞 200 个半成品。

---

## 三、铁律：台词只由 ai-concept-narrator 生产

| 允许 | 禁止 |
|------|------|
| 调用 **ai-concept-narrator** 写 `script_15s` / `script_60s` | 人手从白说库 / 旧草稿直接 copy 标 `ready` |
| 人工 **审核** `reviewed=true` 后改 `status=ready` | 主会话即兴编造长段专业锚点并当成品 |
| 换角度时 **重新** 调 narrator | 同角度 14 天内复读同一条 |

Agent 定义：

- 仓内：[`agents/ai-concept-narrator.md`](agents/ai-concept-narrator.md)
- 已同步：`~/.claude/agents/ai-concept-narrator.md`、项目 `.claude/agents/`
- 请求模板：[`prompts/script-15s-request.md`](prompts/script-15s-request.md)

调用示例（Claude Code）：

```text
使用 agent ai-concept-narrator：
按 prompts/script-15s-request.md 为 id=moe 生产 15s，
Read concepts.json 后返回 JSON；确认后写入并保持 reviewed=false。
```

旧「白说库」只可作 **风格参考**，不能直接 copy 标 ready。

---

## 四、concepts.json 字段设计

| 组 | 字段 | 作用 |
|----|------|------|
| 身份 | `id`, `name`, `aliases` | 稳定主键 + 展示 + 匹配别名 |
| 分层 | `category`, `tier`, `difficulty`, `status` | 选题与难度节奏 |
| 讲解 | `one_liner`, `analogy`, `script_15s`, `script_60s` | 报告一句 / 15s / 深潜 |
| 产线 | `script_meta`（作者、日期、reviewed、angle、confidence） | 可追溯、可拒收 low 置信 |
| 匹配 | `news_keywords` | 当天新闻自动挂钩 |
| 证据 | `corpus`（count、paths） | 证明语料里真出现过 |
| 防重复 | `angles`, `last_used`, `use_count` | 换角度复用、14 天 gap |
| 扩展 | `related_events`, `sources` | 案例与出处（可后补） |

库级：`reuse_gap_days` 默认 **14**（换角度可缩短到 7）；`narrator_agent` 固定为 `ai-concept-narrator`。

### status 流

```text
candidate  语料有、未立项
draft      已立项，台词未审（或未写）
ready      narrator 已写 + reviewed
used       已上视频并记入 usage-log（过 gap 后仍可再选）
stale      定义过时，需重写
```

### 15 秒公式（强制）

```text
概念名点题 → 1 句白话定义 → 1 个生活化比喻 → 1 句价值/与新闻关系
目标 60–80 字，硬上限约 100 字
```

违禁词：佬友、Linuxdo、L站、炸了、炸裂、大瓜、吃瓜、闹鬼、白嫖、薅羊毛、震惊、杀疯了、赢麻…

### ready 质量门

| 检查 | 要求 |
|------|------|
| 作者 | `script_meta.authored_by == "ai-concept-narrator"` |
| 审核 | `reviewed == true` |
| 正文 | `script_15s` 非空，约 60–100 字 |
| 违禁 | 无上表违禁词 |
| 公式 | 含定义 + 比喻 + 价值 |
| 置信 | `confidence` 不为 `low`（low 只许停在 draft） |
| 可追溯 | 尽量有 `corpus` 或明确 `sources` |

---

## 五、端到端数据流

```text
┌─────────────────┐     频次表      ┌──────────────┐
│ 脚本 + 日报语料  │ ─────────────► │ extracts/    │
└─────────────────┘                 └──────┬───────┘
                                           │ 裁定 seed / candidate
                                           ▼
                                    ┌──────────────┐
                                    │ concepts.json│
                                    │ draft/candid.│
                                    └──────┬───────┘
                                           │ ai-concept-narrator
                                           ▼
                                    ┌──────────────┐
                                    │ script_15s   │
                                    │ reviewed→ready
                                    └──────┬───────┘
                         ┌─────────────────┼─────────────────┐
                         ▼                 ▼                 ▼
                  视频专业锚点        报告技术一句        usage-log
                  (ai-news-factory)  (linuxdo-daily)    last_used++
```

---

## 六、每期选题优先级

```text
P1  当日新闻命中 news_keywords，且 gap 满足
P2  近 7 日高频、库中 ready、久未讲
P3  tier=1 中 last_used 最旧或 null
```

约束：

1. 同概念 **同角度** ≥ 14 天  
2. 同 `category` 不连续超过 2 期  
3. 每期专业锚点默认 **1** 个  
4. 灰色 / 权益话题 **不进概念库当 seed**

---

## 七、如何维护更新（实操）

### 7.1 每天（写日报 / 做视频时，2–5 分钟）

1. 看到新黑话：优先写进日报 `## 概念候选（供 concept-bank）`；若执行 `linuxdo-daily` 的受控入库步骤，可去重过滤后只追加最小 `candidate`（不写口播、不晋升 ready）。
2. 本期用了某个 ready 概念：  
   - `usage-log.json` **append** 一条  
   - 更新该概念 `last_used`、`use_count++`  
   - 本次 `angle` 写入 `angles.used`（若还没有）

#### linuxdo-daily 受控入库边界（v15.1）

`linuxdo-daily` 可在日报 Markdown 写入后读取 `## 概念候选（供 concept-bank）`，但只能做最小候选入库：

```text
读取日报候选
  → 与 concepts.json 的 id/name/aliases/news_keywords 去重
  → 过滤营销词、产品名、模型型号、权益黑话、低可信和无法 15s 定义的表达
  → 只追加 status=candidate 的最小条目
  → jq empty ai-concept-bank/concepts.json
  → 等待周维护 / term-frequency 验证
```

禁止在该步骤中调用 narrator、写 `script_15s`、设置 `reviewed=true`、晋升 `draft/ready`、写 `usage-log` 或修改已有 ready 概念。

日报候选负责发现新词；`term-frequency` 负责验证长期价值；维护 Agent 决定后续 `candidate → draft → ready`。

### 7.2 每周（约 15 分钟）

1. 看本周脚本 / `extracts`，有无新高频词。  
2. 值得讲的 `candidate` → `draft`（补全 category、keywords、angles）。  
3. 调 Agent 写台词：

```text
使用 ai-concept-narrator：
按 prompts/script-15s-request.md 为 id=xxx 生产 15s；
先 Read concepts.json；返回 JSON，写入后 reviewed=false，status 保持 draft。
```

4. 抽检：技术对不对、有无违禁词、能不能 TTS。  
5. 通过：`reviewed=true`，`status=ready`。  
6. 检查 tier1 是否有 **>14 天未用** → 排进下周锚点候选。

### 7.3 每月（约 30 分钟）

1. **重跑语料提取**，更新 `extracts/`，裁定新 seed。  
2. 复盘 usage-log：哪类反馈好、是否仍懵 → 换角度或标 `stale`。  
3. 过时定义：`stale` → 再调 narrator。  
4. 可选：高频概念补 `script_60s`（周报 / 月报深潜）。  
5. 子模块 commit + 父仓更新指针（见下文）。

### 7.4 换角度复用（同一概念再讲）

不要复读同一条 `script_15s`。

1. 看 `angles.available` / `used`。  
2. 指定新角度（如 MoE 的「激活参数 vs 总参数」）。  
3. **再调 narrator** 生成新 `script_15s`。  
4. 旧角度进 `used`；冷却：换角度 ≥7 天，同角度 ≥14 天。

### 7.5 库里没有但今天必须讲

```text
当天新闻命中新词
  → 先 candidate/draft 入库（可极简）
  → 立刻调 narrator 写 15s
  → 快审 → ready
  → 进视频锚点
  → 记 usage-log
```

不要在 ai-news-factory 主会话里即兴写一大段专业解释当定稿。

### 日 / 周 / 月一览

| 节奏 | 动作 |
|------|------|
| **每天** | 新词 → 日报候选 / 受控最小 `candidate`；用过 → `usage-log` + `last_used` |
| **每周** | 别名合并；晋升 draft；narrator 补台词；抽检 ready；扫超期未用 tier1 |
| **每月** | 重跑 term-frequency；复盘；stale 重写；可选 script_60s |

### usage-log 一条示例

```json
{
  "date": "2026-07-12",
  "concept_id": "moe",
  "angle": "基础定义",
  "mode": "daily",
  "duration_sec": 15,
  "news_trigger": "某模型使用 MoE 架构",
  "report_path": "data/reports/2026-07-12.md",
  "script_path": "news-pipeline/2026-07-12/scripts/script.md",
  "notes": ""
}
```

---

## 八、与下游 skill 的约定

| 消费方 | 应做 | 不应做 |
|--------|------|--------|
| **linuxdo-daily** Writer | 「技术锚点」匹配 `news_keywords`，可引用 `one_liner`；日报候选可受控追加最小 `candidate` | 论坛标题党当技术解释；自动写口播或晋升 ready |
| **ai-news-factory** Phase 1 | 读本库做锚点候选 + gap | 另起概念库 |
| **ai-news-factory** Phase 2 | 口播用已 `ready` 的 `script_15s`；缺则调 **ai-concept-narrator** | 主会话瞎编长锚点 |

路径（相对项目根）：

```text
ai-concept-bank/concepts.json
ai-concept-bank/usage-log.json
```

---

## 九、设计取舍

| 选项 | 我们的选择 | 原因 |
|------|------------|------|
| 百科式大而全 | 否，少而可上片 | 维护不动等于死库 |
| 纯 Markdown 表 | JSON 主库 + README | skill / 脚本好解析 |
| 人手写全部台词 | narrator 专产 | 口径统一、可扩展 60s |
| 按难度课程表讲 | 新闻优先 + 库兜底 | 避免和日报脱节 |
| 自动升降 tier | MVP 不做 | 先人审，规则写在 SOP |

---

## 十、当前 MVP 状态

- 语料：脚本约 48 + 日报约 50 + 周报 4 + 月报 1（见 extracts）  
- **ready 种子：20**（含 `script_15s`）  
- **candidate：27**（无强制台词）  
- `usage-log` 初始为空  

Ready 列表：

```bash
python3 -c "import json;d=json.load(open('concepts.json'));print([c['id'] for c in d['concepts'] if c['status']=='ready'])"
```

当前 ready：`agent` · `token` · `context_window` · `distillation` · `multimodal` · `cot` · `moe` · `mcp` · `hallucination` · `benchmark` · `data_contamination` · `function_calling` · `open_weights` · `license` · `api_key` · `finetune` · `rag` · `guardrails` · `model_dumbing` · `quantization`

---

## 十一、子模块提交

本目录为 git submodule（`IVANLEE99/ai-concept-bank`）。

```bash
# 1) 子模块内提交并推送
cd ai-concept-bank
git add -A && git status
git commit -m "feat: …"
git push

# 2) 父仓更新指针并推送
cd ..
git add ai-concept-bank
git commit -m "chore: bump ai-concept-bank"
git push
```

Agent 定义若有改动，同步到可调用位置：

```bash
cp ai-concept-bank/agents/ai-concept-narrator.md ~/.claude/agents/
cp ai-concept-bank/agents/ai-concept-narrator.md .claude/agents/
```

---

## 十二、一句话 + 日常三件事

**ai-concept-bank =「从真实脚本/日报长出来的概念库存」+「只准讲解 Agent 写的 15 秒台词」+「使用日志防重复」。**

日常只记三条：

1. **新词先入日报候选，合格才进 candidate**
2. **台词只调 narrator，审完再 ready**  
3. **用过就写 usage-log，并遵守 14 天冷却**

---

## 版本

- **1.0.0** — MVP：语料反提、20 ready 种子、narrator agent、usage-log、设计原则与维护 SOP  
- **1.0.1** — README 补全设计思路与维护更新专章  
- **1.0.2** — 同步 linuxdo-daily v15.1 受控候选入库边界
