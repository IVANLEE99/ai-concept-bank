# ai-news-factory 操作 ai-concept-bank 说明

## 结论

`ai-news-factory` 是 `ai-concept-bank` 的**主要视频消费方和使用记录写入方**。

它负责：

- 从已有 `ready` 概念中自动选择专业锚点。
- 检查关键词匹配、冷却期和使用频率。
- 将 `script_15s` 或 `script_60s` 原样插入视频脚本。
- 用户确认脚本后写入 `usage-log.json`。
- 更新概念的 `last_used`、`use_count` 和 `angles.used`。

它自身**不会自动将日报中的“概念候选”批量加入 `concepts.json`**。`linuxdo-daily` v15.1 可在日报生成后受控追加最小 `candidate`，但不生成口播、不晋升 ready。

## 与 linuxdo-daily 的职责对比

| 能力 | `linuxdo-daily` | `ai-news-factory` |
|---|---:|---:|
| 读取 ready 概念 | ✅ | ✅ |
| 匹配新闻关键词 | ✅ | ✅ |
| 使用 `one_liner` | ✅ 日报文字 | 可用于选题说明 |
| 使用 `script_15s` | ❌ | ✅ 原样进入视频 |
| 自动选出 Top 3 | ❌ | ✅ |
| 检查冷却期 | ❌ | ✅ |
| 调 narrator 补台词 | ❌ | ✅ |
| 写 `usage-log.json` | ❌ | ✅ |
| 更新 `last_used/use_count` | ❌ | ✅ |
| 受控追加最小 candidate | ✅ v15.1 可选 | ❌ |

## 完整操作链路

```text
linuxdo-daily 日报
    ↓
ai-news-factory 读取本期事件/趋势
    ↓
读取 ai-concept-bank/concepts.json
    ↓
筛选 eligible 概念
    ↓
关键词匹配 + 冷却过滤 + 打分
    ↓
向用户展示 Top 3
    ↓
用户确认专业锚点
    ↓
原样插入 script_15s/script_60s
    ↓
用户确认完整视频脚本
    ↓
追加 usage-log.json
    ↓
更新 last_used/use_count/angles.used
```

## 1. 自动选题

在选材完成、进入视频脚本生成前，`ai-news-factory` 强制执行 Step 1.6“专业锚点自动选题”。

规则来源：

```text
skills/ai-news-factory/SKILL.md
skills/ai-news-factory/templates/professional-anchor.md
```

它会读取：

```text
ai-concept-bank/concepts.json
ai-concept-bank/usage-log.json
```

只有满足以下条件的概念才参与候选：

```text
status == "ready"
script_15s 或对应模式的 script_60s 非空
script_meta.authored_by == "ai-concept-narrator"
script_meta.reviewed == true
```

按照概念库自身质量门，低置信度概念原则上也不应进入 `ready`。

## 2. 匹配日报事件

`ai-news-factory` 不会简单选择日报中出现的第一个“技术锚点”。

它会把用户确认的事件标题和摘要拼成 `episode_text`，重新匹配每个 eligible 概念的：

- `news_keywords`
- `aliases`
- `name`

例如 `data/reports/2026-07-12.md` 中出现的以下概念都可能成为匹配对象：

- Agent
- Token
- 上下文窗口
- RAG
- Chain-of-Thought
- 多模态

日报中的“技术锚点”可以提供提示，但 `ai-news-factory` 仍应根据最终选材重新运行选择算法。

## 3. 冷却过滤

系统读取 `concepts.json` 顶层配置：

```json
{
  "reuse_gap_days": 14
}
```

冷却规则：

- `last_used == null`：直接通过。
- 同一个角度：默认至少间隔 14 天。
- 更换角度：至少间隔 7 天。
- 冷却不足：可以展示，但不进入默认推荐。
- 换角度必须重新调用 `ai-concept-narrator`，不能复读原来的 `script_15s`。

## 4. 候选打分

| 分数 | 条件 |
|---:|---|
| +100 | 命中本期事件关键词 |
| +40 | `tier == 1` |
| +20 | 从未使用 |
| +10 | 距离上次使用较久 |
| +5 | `use_count` 为 0–2 |
| -30 | 与最近一次使用概念属于同分类 |

最终取 Top 3，并默认推荐第一名。

没有新闻关键词命中时，使用 P3 兜底：

```text
tier1 + last_used 最旧或 null 的 eligible 概念
```

## 5. 必须由用户确认

自动排序后不能直接决定，必须向用户展示候选，例如：

```text
推荐：moe
2. token
3. context_window

冷却跳过：distillation
不合格跳过：xxx

请选择：推荐 / 编号 / 指定 id / 本期不要锚点
```

确认后写入会话变量：

```text
ANCHOR_CONCEPT_ID
ANCHOR_ANGLE
ANCHOR_DURATION_SEC
ANCHOR_SKIP
```

## 6. 把概念口播插入视频

进入 Phase 2 后，重新读取选中的概念条目并验证 eligible。

### 日报视频

```text
使用 script_15s
```

### 周报和月报视频

```text
优先使用 script_60s
没有时使用 script_15s 兜底
```

台词必须**原样使用**。主会话只能增加不超过 15 字的过渡语，例如：

```text
刚才提到 MoE——
```

不得改写库内定义句，也不得自行重新写完整专业解释。

锚点会成为独立 scene：

- 独立 TTS 音频
- 独立画面
- 独立字幕
- 计入分镜数量和渲染校验

## 7. 概念未达到 ready 时

如果用户指定的概念不是 eligible，不能直接使用。

正确处理流程：

```text
调用 ai-concept-narrator
    ↓
按 ai-concept-bank/prompts/script-15s-request.md 生成口播
    ↓
写入 concepts.json，reviewed=false
    ↓
明确审核
    ↓
reviewed=true + status=ready
    ↓
再插入视频
```

注意：不得直接把 narrator 输出自动标记为 `reviewed=true`。必须经过明确审核后才能晋升 `ready`。

## 8. 用户确认后写回概念库

这是 `ai-news-factory` 与 `linuxdo-daily` 最大的区别。

完整视频脚本经用户确认后、进入 Phase 3 分镜生成前，必须追加：

```text
ai-concept-bank/usage-log.json
```

记录格式：

```json
{
  "date": "2026-07-12",
  "concept_id": "agent",
  "angle": "基础定义",
  "mode": "daily",
  "duration_sec": 15,
  "news_trigger": "相关事件标题",
  "report_path": "data/reports/2026-07-12.md",
  "script_path": "news-pipeline/2026-07-12/scripts/script-2026-07-12.md",
  "notes": ""
}
```

随后更新 `concepts.json` 对应概念：

```text
last_used = date
use_count += 1
angles.used 追加本次 angle（不存在时才追加）
```

不得修改：

- `script_15s`
- `status`
- `script_meta.authored_by`
- 历史使用日志

当前库已经有一条实际记录：

```text
concept_id: agent
date: 2026-07-12
mode: daily
angle: 基础定义
```

## 9. 是否自动加入候选概念

`ai-news-factory` **不会**导入日报候选；`linuxdo-daily` v15.1 可以执行受控最小入库。

`data/reports/2026-07-12.md` 中的日报候选包括：

- 多 SubAgent 套娃
- Juice Number 体系
- TUI 优先路线
- Harness 套娃/负优化
- Knowledge Cut-off 错位

`ai-news-factory` 当前不会自动把它们写入 `concepts.json`。若由 `linuxdo-daily` 执行受控入库，也必须先去重和过滤；例如 `多 SubAgent 套娃` 更像 `Agent` 的新角度，`Juice Number 体系` 更像评测衍生，`Knowledge Cut-off 错位` 已标注尚不能上升为概念，不应无条件追加。

它只会：

- 从已有 ready 概念中选择锚点。
- 用户指定非 ready 概念时，调用 narrator 补全。
- 使用后写日志和统计。

`linuxdo-daily` v15.1 已补充以下受控步骤：

```text
读取日报“概念候选”
→ 与 concepts.json 去重
→ 过滤不适合入库的候选
→ 写入 status=candidate
→ 不写口播、不晋升 ready、不写 usage-log
```

## 10. 当前职责划分

```text
linuxdo-daily
  负责发现新候选、生成日报 one_liner 锚点
  可受控追加最小 candidate
  不写口播、不晋升 ready、不写 usage-log

ai-news-factory
  负责选择 ready 概念、使用完整口播
  使用后更新日志和统计
  自身不导入日报候选

ai-concept-narrator
  负责生成或换角度重写口播
  默认 reviewed=false

概念库维护 Agent
  负责复核 candidate，结合 term-frequency 裁定是否晋升 draft
  审核 narrator 输出并晋升 ready
```

当前整体状态：

> **候选发现半自动，视频锚点选题自动，使用回写自动，候选入库仍需专门维护流程。**
