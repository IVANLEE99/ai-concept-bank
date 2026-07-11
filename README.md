# ai-concept-bank

AI 短视频 / 日报 **技术概念库**：可检索、可复用、可防重复。  
服务「今日羊报 AI」的 **每期专业锚点（默认 15 秒）** 与报告中的技术一句。

> **不是** AI 百科、论文笔记或自动爬虫。  
> **是** 内容工具：每个正式概念都要能回答——什么新闻时讲？15 秒怎么讲？最近讲过没？

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

**禁止**再建 `news-pipeline/concept-bank/`。下游 skill 只认本目录。

---

## 种子从哪来

种子 **不是** 拍脑袋，而是：

| 语料 | 路径 |
|------|------|
| 视频脚本 | `news-pipeline/**/scripts/*.{md,txt}` |
| 日报 | `data/reports/*.md`（排除 `*_press.md`） |
| 周报 / 月报 | `data/weekly/*.md`、`data/monthly/*.md` |

提取结果见 [`extracts/term-frequency.json`](extracts/term-frequency.json)。  
收录时跳过：公司名/型号本体、权益黑话、无法 15s 定义的八卦。

重跑提取：内容风格大变或每月维护时，用同样规则扫一遍语料，更新 `extracts/`，再裁定新 `candidate` / `seed`。

---

## 铁律：台词只由 ai-concept-narrator 生产

| 允许 | 禁止 |
|------|------|
| 调用 **ai-concept-narrator** 写 `script_15s` / `script_60s` | 人手从白说库/旧草稿直接 copy 标 `ready` |
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

---

## concepts.json 要点

| 字段 | 说明 |
|------|------|
| `id` | 稳定主键 |
| `status` | `candidate` → `draft` → `ready` → `used` / `stale` |
| `tier` | 1 优先讲解 · 2/3 候补 |
| `script_15s` | TTS 成品；`ready` 时必填 |
| `script_meta.authored_by` | 固定 `ai-concept-narrator` |
| `script_meta.reviewed` | 人工/主会话抽检通过 |
| `news_keywords` | 日报/脚本匹配 |
| `corpus` | 反提频次与样例路径 |
| `angles` | 可讲角度 / 已讲角度 |
| `last_used` / `use_count` | 与 usage-log 双写 |
| `reuse_gap_days` | 库级默认 **14**；换角度可缩短到 7 |

### status 流

```text
candidate  语料有、未立项
draft      已立项，台词未审
ready      narrator 已写 + reviewed
used       已上视频并记入 usage-log（过 gap 后仍可再选）
stale      定义过时，需重写
```

---

## 每期选题优先级

```text
P1  当日新闻命中 news_keywords，且 gap 满足
P2  近 7 日高频、库中 ready、久未讲
P3  tier=1 中 last_used 最旧或 null
```

约束：

1. 同概念 **同角度** ≥ 14 天  
2. 同 `category` 不连续超过 2 期  
3. 每期专业锚点默认 **1** 个  

---

## 日 / 周 / 月维护

| 节奏 | 动作 |
|------|------|
| **每天** | 写日报/脚本时记下新词 → `candidate`；若使用某概念 → 写 `usage-log` 并更新 `last_used` |
| **每周** | 合并别名；`candidate` 晋升 `draft`；调 narrator 补台词；抽检 → `ready`；看超 14 天未用的 tier1 |
| **每月** | 重跑或增量 term-frequency；复盘掉线/追问；`stale` 重写；可选补 `script_60s` |

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

## 与下游 skill 的约定（预留）

| 消费方 | 用法 |
|--------|------|
| **linuxdo-daily** Writer | 「技术锚点」优先匹配 `news_keywords`，可引用 `one_liner` |
| **ai-news-factory** Phase 1 | 读本库做锚点候选 + gap |
| **ai-news-factory** Phase 2 | 口播优先用已 `ready` 的 `script_15s`；缺则调 **ai-concept-narrator**，禁止主会话瞎编 |

路径（相对项目根）：

```text
ai-concept-bank/concepts.json
ai-concept-bank/usage-log.json
```

---

## 15 秒公式

```text
概念名点题 + 1 句白话定义 + 1 个生活化比喻 + 1 句价值/新闻关系
```

违禁：佬友、Linuxdo、L站、炸了、炸裂、大瓜、吃瓜、闹鬼、白嫖、薅羊毛、震惊…

---

## 当前 MVP 状态

- 语料：脚本约 48 + 日报约 50 + 周报 4 + 月报 1（见 extracts）  
- **ready 种子：20**（`status=ready`，含 `script_15s`）  
- **candidate：若干**（无强制台词）  
- `usage-log` 初始为空  

查看 ready 列表：

```bash
python3 -c "import json;d=json.load(open('concepts.json'));print([c['id'] for c in d['concepts'] if c['status']=='ready'])"
```

---

## 子模块提交

本目录为 git submodule（`IVANLEE99/ai-concept-bank`）。

```bash
# 在子模块内
cd ai-concept-bank
git add -A && git status
git commit -m "feat: concept bank MVP + narrator agent + corpus extract"
git push

# 回父仓更新指针
cd ..
git add ai-concept-bank
git commit -m "chore: bump ai-concept-bank submodule"
```

（仅在你明确要求 commit 时执行。）

---

## 版本

- **1.0.0** — MVP：语料反提、20 ready 种子、narrator agent、usage-log、SOP  
