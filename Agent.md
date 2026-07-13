# ai-concept-bank Agent 维护指南

> 面向负责维护 `ai-concept-bank` 的大模型。本文是可执行手册；详细背景和完整 SOP 见 [`README.md`](README.md)。

## 1. 目标与边界

这是一个服务 AI 日报、周报、月报和短视频的**技术概念工具库**，不是百科、论文笔记或自动爬虫。

每个进入 `ready` 的概念都必须能够回答：

1. 它适合在哪类新闻中使用？
2. 普通观众能否在约 15 秒内听懂？
3. 最近是否已经讲过，是否需要换角度？

### 维护边界

- 主库：`ai-concept-bank/concepts.json`
- 使用记录：`ai-concept-bank/usage-log.json`
- 语料提取：`ai-concept-bank/extracts/`
- 口播 Agent：`ai-concept-bank/agents/ai-concept-narrator.md`
- 口播请求模板：`ai-concept-bank/prompts/script-15s-request.md`
- 人类维护 SOP：`ai-concept-bank/README.md`

不要新建或使用 `news-pipeline/concept-bank/`。下游只认 `ai-concept-bank/`。

除非用户明确要求，不修改 `concepts.json`、`usage-log.json` 以外的业务系统，不修改 `linuxdo-daily` 或 `ai-news-factory` 的实现逻辑，不自动提交 Git。

## 2. 开始任务前的必读与检查

先读取：

```text
ai-concept-bank/README.md
ai-concept-bank/concepts.json
ai-concept-bank/usage-log.json
ai-concept-bank/agents/ai-concept-narrator.md
```

根据任务再读取：

```text
ai-concept-bank/extracts/term-frequency.json
ai-concept-bank/prompts/script-15s-request.md
skills/ai-news-factory/templates/professional-anchor.md
skills/linuxdo-daily/SKILL.md
```

用命令确认主库和 JSON 可解析：

```bash
test -f ai-concept-bank/concepts.json
test -f ai-concept-bank/usage-log.json
jq empty ai-concept-bank/concepts.json
jq empty ai-concept-bank/usage-log.json
```

没有 `jq` 时，可改用 `python3 -m json.tool <文件> >/dev/null`。

如果主库不存在，先提示：

```bash
git submodule update --init ai-concept-bank
```

不要在主库缺失时创建一个空库来覆盖问题。

## 3. 数据职责与状态机

### 文件职责

| 文件 | 用途 | 写入规则 |
|---|---|---|
| `concepts.json` | 概念定义、口播、状态、冷却和统计 | 修改已有条目时保留未知字段；不改稳定 `id` |
| `usage-log.json` | 每次实际上线的历史记录 | 只能追加，不覆盖历史记录 |
| `extracts/term-frequency.*` | 从真实脚本和日报提取候选词及上下文 | 重跑提取后再人工裁定入库 |
| `agents/ai-concept-narrator.md` | 口播生成规则 | 只有维护 Agent 明确要求时才改 |

### 概念状态

```text
candidate → draft → ready → used
                         ↘ stale → draft
```

- `candidate`：发现了词，但尚未确认是否值得讲；可以只有 `id`、`name`、`news_keywords`。
- `draft`：值得维护，已补充基本元数据，但口播未审核完成。
- `ready`：口播由 `ai-concept-narrator` 生成，且已经审核通过，可供下游消费。
- `used`：曾经上线并已写入 `usage-log.json`。当前库也可能继续使用 `status=ready` 的条目，具体以现有数据和 README 约定为准；不要仅因使用一次就破坏下游的 `ready` 筛选。
- `stale`：定义、案例或表达可能过时；必须重新核实并重新生成口播后才能回到 `draft`/`ready`。

不要把未审核、低置信度或主会话即兴写出的台词标为 `ready`。

## 4. Agent 分工铁律

### `ai-concept-narrator` 负责

- 根据概念、语料和指定角度生成 `one_liner`、`analogy`、`script_15s`。
- 遵守 15 秒结构、字数、口语化和违禁词规则。
- 对不确定事实返回 `confidence: low` 和 `facts_to_verify`。

### 主维护 Agent 负责

- 读取现有条目和历史角度，避免重复。
- 判断概念是否值得入库、是否命中新闻、是否满足冷却期。
- 调用 narrator，审核返回 JSON，并按 schema 写回。
- 用户确认脚本后追加使用记录并更新统计。
- 写入后重新解析 JSON 并检查数据一致性。

### 禁止

- 从旧白说库、归档草稿或其他模型输出直接复制并标记为成品。
- 主会话即兴编写长专业口播并标记 `ready`。
- 擅自把 `script_meta.reviewed` 设为 `true`。
- 为了绕过冷却期覆盖 `last_used` 或删除历史日志。
- 擅自修改 `script_meta.authored_by`、稳定 `id` 或清空 `corpus`。

## 5. 口播质量门

15 秒口播必须遵循：

```text
概念名点题 → 白话定义 → 一个生活化比喻 → 价值或新闻关系
```

默认要求：

- `script_15s` 非空，目标 60–80 字，硬上限约 100 字。
- 全程可口播，最多夹带一个次级术语。
- 技术事实准确；不确定时降低置信度，不猜数字、来源或机制。
- 不出现违禁词，包括：`佬友`、`Linuxdo`、`L站`、`炸了`、`炸裂`、`大瓜`、`吃瓜`、`闹鬼`、`白嫖`、`薅羊毛`、`震惊`、`杀疯了`、`赢麻`。

只有同时满足以下条件，概念才是下游 eligible：

```text
status == "ready"
script_15s 非空
script_meta.authored_by == "ai-concept-narrator"
script_meta.reviewed == true
script_meta.confidence != "low"
```

并且应尽量具备 `corpus` 或明确 `sources`，以便追溯。

## 6. 任务流程

### 6.1 新概念入库

适用于日报、周报或语料中发现新技术词。新词有两种入口：

- `linuxdo-daily` 日报候选受控入库：只允许从 `## 概念候选（供 concept-bank）` 追加最小 `candidate`。
- 维护 Agent 裁定入库：结合 `extracts/term-frequency.json`、日报候选和原始上下文判断是否值得长期维护。

执行规则：

1. 先搜索 `concepts.json` 的 `id`、`name`、`aliases`、`news_keywords`，先合并同义词，禁止重复建卡。
2. 排除公司名、型号本体、产品名、营销词、权益黑话、低可信单日传闻和无法在 15 秒内解释的表达。
3. 若只是日报候选受控入库，只追加最小 `candidate`，并保持 `one_liner`、`analogy`、`script_15s` 为空，`script_meta.reviewed=false`。
4. 若能匹配 `extracts/term-frequency.json` 的 `normalized_id`，可复制精简 `corpus`；否则只记录日报路径到 `sources`，等待月度频次验证。
5. 如果维护 Agent 确认值得长期维护，再补齐 `category`、`tier`、`difficulty`、`angles`、`sources`、`corpus`，升为 `draft`。
6. 不要在候选入库阶段调用 narrator、伪造 `script_meta`、写口播、晋升 `ready` 或写 `usage-log`。

### 6.2 为概念生成 15 秒口播

1. 读取目标条目，检查 `angles.used` 和 `angles.available`。
2. 选择未使用角度；若没有可用角度，先新增一个明确、可验证的角度。
3. 按模板调用 narrator：

```text
使用 agent ai-concept-narrator。
按 ai-concept-bank/prompts/script-15s-request.md 为 id={id} 生产 15s。
先 Read ai-concept-bank/concepts.json 中的目标条目，避免复用已有角度。
返回一个 JSON 对象；不要自行写入其他文件。
```

4. 检查返回值的 `id`、角度、字数、公式、违禁词和置信度。
5. 用户要求写入时，只更新目标概念的讲解字段及 `script_meta`：
   - `script_meta.authored_by = "ai-concept-narrator"`
   - `script_meta.authored_at = 当前 ISO 日期`
   - `script_meta.reviewed = false`
   - `script_meta.angle = 本次角度`
   - 保持 `status` 为 `draft`，除非后续审核明确通过。
6. 保留原有 `corpus`、历史角度和其他未知字段。

### 6.3 审核并晋升为 `ready`

审核者应逐项确认：

```text
[ ] 台词来自 ai-concept-narrator
[ ] reviewed 已明确审核后才改为 true
[ ] script_15s 非空且长度合适
[ ] 含定义、比喻、价值/新闻关系
[ ] 无违禁词和标题党表达
[ ] 技术事实可核实
[ ] confidence 不是 low
[ ] 有 corpus 或 sources 追溯信息
[ ] angle 未与近期使用重复
```

全部通过后，才可以：

```json
{
  "status": "ready",
  "script_meta": {
    "reviewed": true
  }
}
```

若存在事实疑问，保持 `confidence: "low"` 或 `status: "draft"`，并在 `facts_to_verify` 写明待核实项。

### 6.4 选择日报、周报、月报专业锚点

下游选题顺序：

1. 本期事件标题或摘要命中 `news_keywords`、`aliases` 或 `name` 的 eligible 概念。
2. `tier=1` 且长期未使用或从未使用的 eligible 概念。
3. 没有命中时使用 P3 兜底，不要为了命中而改写关键词。

读取 `reuse_gap_days`，默认同角度冷却 14 天；换角度冷却至少 7 天，并且必须重新调用 narrator，不能复读旧台词。

选择时优先考虑：

- 新闻关联度
- 不解释该概念是否会影响理解
- 近期热度
- 15 秒可讲性
- 与上次使用的时间间隔
- 与最近概念的分类重复情况

每期默认只能使用一个专业锚点。用户明确跳过时设置跳过，不要强行插入。

### 6.5 用户确认后写入使用记录

只有脚本获得用户确认、且确实进入成片或报告流程后，才写入使用记录。追加 `usage-log.json` 的 `log` 数组，不覆盖已有记录：

```json
{
  "date": "YYYY-MM-DD",
  "concept_id": "moe",
  "angle": "基础定义",
  "mode": "daily",
  "duration_sec": 15,
  "news_trigger": "命中的事件标题或趋势名",
  "report_path": "data/reports/YYYY-MM-DD.md",
  "script_path": "news-pipeline/YYYY-MM-DD/scripts/script.md",
  "notes": ""
}
```

随后更新 `concepts.json` 对应条目：

- `last_used = date`
- `use_count += 1`
- 将本次 `angle` 加入 `angles.used`（不存在时才追加）
- 不修改 `script_15s`、`script_meta.authored_by` 或历史 `corpus`

`mode` 只能使用 `daily`、`weekly`、`monthly` 之一；月报默认消费对应月报产物，不重新抓取或重复聚合。

### 6.6 换角度复用

1. 检查 `last_used` 和 `usage-log.json`。
2. 同角度距离上次使用至少 `reuse_gap_days` 天，默认 14 天。
3. 换角度至少间隔 7 天，并重新调 narrator。
4. 旧角度保留在 `angles.used`，新角度追加到 `angles.used`。
5. 不覆盖旧日志，不把新角度伪装成旧角度。

### 6.7 概念过时或必须临时补充

- 定义、案例、产品行为或数字可能过时：标记 `stale`，核实事实后重新调 narrator，回到 `draft`，审核通过再回到 `ready`。
- 今日必须讲但库中没有：先以最小字段加入 `candidate/draft`，调 narrator，快速审核通过后再使用，并照常写 `usage-log`。
- 不要绕过概念库，在 `ai-news-factory` 主流程中直接写一段未经审核的专业解释。

## 7. 数据完整性与写入后校验

每次修改前后都执行以下规则：

1. 不修改稳定 `id`；同义词优先合并到 `aliases`。
2. 不删除或覆盖 `usage-log.json.log` 中的历史记录。
3. `use_count` 应等于该概念在 `usage-log.json` 中的历史使用次数；如果历史数据已不一致，先报告差异，不能静默抹平。
4. `last_used` 应对应该概念最新一次日志日期。
5. `angles.used` 不重复追加；历史使用角度不能删除。
6. 不清空 `corpus`、`sources` 或其他未参与本次任务的字段。
7. 写入后重新解析两个 JSON 文件，并确认目标 `id`、状态和日志条目存在。

建议校验命令：

```bash
jq empty ai-concept-bank/concepts.json
jq empty ai-concept-bank/usage-log.json
```

没有 `jq` 时，可改用 `python3 -m json.tool <文件> >/dev/null`。

如需检查 eligible 概念：

```bash
python3 - <<'PY'
import json
from pathlib import Path

path = Path("ai-concept-bank/concepts.json")
data = json.loads(path.read_text())
eligible = []
for concept in data.get("concepts", []):
    meta = concept.get("script_meta", {})
    if (
        concept.get("status") == "ready"
        and concept.get("script_15s")
        and meta.get("authored_by") == "ai-concept-narrator"
        and meta.get("reviewed") is True
        and meta.get("confidence") != "low"
    ):
        eligible.append(concept["id"])
print("eligible:", eligible)
PY
```

## 8. 异常处理

| 情况 | 处理 |
|---|---|
| `concepts.json` 不存在 | 提示初始化 submodule；不要创建空主库覆盖问题 |
| JSON 无法解析 | 停止写入，报告文件和解析错误，先修复格式 |
| 没有 eligible 概念 | 跳过锚点，或经用户同意后调 narrator 补写并审核 |
| 所有 eligible 概念都在冷却期 | 展示冷却原因；由用户选择换概念、强制使用并在 `notes` 说明，或跳过 |
| 本期没有关键词命中 | 使用 tier1 + 最久未用的 P3 候选，不修改关键词制造命中 |
| 今日必须讲但没有概念卡 | 先建立 candidate/draft，再调 narrator、审核、使用和记账 |
| narrator 返回 `confidence=low` | 不得标 `ready`；补充 `facts_to_verify` 并等待核实 |
| 用户未确认脚本 | 不写 `usage-log`，不更新 `last_used` 和 `use_count` |
| 写入后校验失败 | 停止后续流程，报告差异；不要继续生成下游产物 |

## 9. 日、周、月维护清单

### 每天

- 新词先进入日报候选；如执行 `linuxdo-daily` 受控入库，只追加最小 `candidate`，避免重复建卡。
- 使用概念前检查关键词、角度和冷却期。
- 用户确认并实际上线后追加日志、更新统计。

### 每周

- 从脚本、日报和 `extracts/` 检查新高频词。
- 合并别名，清理无持续价值的营销词。
- 将高价值候选升为 `draft`，调 narrator 补台词。
- 审核 draft，只有通过质量门才升为 `ready`。
- 检查 tier1 中长期未使用的概念和分类覆盖情况。

### 每月

- 重跑语料提取并更新 `extracts/`。
- 复盘 `usage-log.json`：使用频率、角度、反馈和重复情况。
- 核实过时事实，将必要条目标记 `stale` 并重写。
- 为高价值概念按需补充 `script_60s`。
- 如这是独立 submodule，按 README 流程提交子模块，再由父仓更新指针；不要静默提交。

## 10. 完成任务前最终检查

```text
[ ] 只修改了任务要求范围内的文件
[ ] 没有使用旧路径 news-pipeline/concept-bank/
[ ] concepts.json 和 usage-log.json 均可解析
[ ] 没有重复 id、重复 alias 或重复 angle
[ ] 没有覆盖历史使用记录
[ ] ready 概念通过全部 eligible 质量门
[ ] usage-log 的日期、mode、路径和 concept_id 正确
[ ] 新口播由 ai-concept-narrator 生成并经过审核
[ ] 没有把低置信度内容标为 ready
[ ] 已向用户说明剩余风险、未核实事实或跳过项
```

如果只是维护文档，不需要修改数据文件；如果修改了数据文件，应在交付说明中列出文件、字段变化和校验结果。
