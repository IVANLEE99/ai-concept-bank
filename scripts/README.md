# extract-term-frequency.py 使用说明

> 扫描全量语料，输出术语频次表到 `ai-concept-bank/extracts/`。  
> 子模块内路径：`ai-concept-bank/scripts/extract-term-frequency.py`  
> 配套 SOP：`ai-concept-bank/prompts/refresh-and-promote.md`

---

## 快速开始

```bash
# 在 learn-claude-code 根目录执行（脚本会自动找项目根）
python3 ai-concept-bank/scripts/extract-term-frequency.py

# 指定项目根（如不在根目录）
python3 ai-concept-bank/scripts/extract-term-frequency.py --root /path/to/learn-claude-code

# 只生成 JSON，不生成 MD 报告
python3 ai-concept-bank/scripts/extract-term-frequency.py --no-md
```

---

## 语料范围

| 类型 | 扫描路径 | 排除规则 |
|------|----------|----------|
| 视频脚本 | `news-pipeline/**/scripts/*.{md,txt}` + `news-pipeline/scripts/*.md` | 排除 `node_modules` |
| 日报 | `data/reports/*.md` | 排除 `*_press.md`、`2026-W*.md`（周报格式） |
| 周报 | `data/weekly/*.md` | 排除含 `press` 的文件名 |
| 月报 | `data/monthly/*.md` | 排除含 `press` 的文件名 |

---

## 输出

### JSON — `extracts/term-frequency.json`

```json
{
  "generated_at": "2026-07-13",
  "sources": { "scripts": 50, "daily_reports": 50, "weekly": 5, "monthly": 1 },
  "dictionary_size": 42,
  "terms": [
    {
      "term": "MoE",
      "normalized_id": "moe",
      "category": "模型架构",
      "difficulty": "中等",
      "count_scripts": 2,
      "count_reports": 8,
      "count_daily": 8,
      "count_weekly": 0,
      "count_monthly": 0,
      "count_total": 10,
      "files_scripts": 2,
      "files_reports": 4,
      "file_coverage": 5,
      "sample_contexts": ["..."],
      "example_paths": ["news-pipeline/.../script.md", "data/reports/..."],
      "suggested_label": "MoE"
    }
  ]
}
```

**字段说明：**

| 字段 | 含义 |
|------|------|
| `count_scripts` | 在视频脚本中的命中次数 |
| `count_reports` | 在日报+周报+月报中的命中次数 |
| `count_daily/weekly/monthly` | 分类别计数（= count_reports 的拆分） |
| `count_total` | = count_scripts + count_reports |
| `files_scripts` | 命中过的脚本文件数 |
| `files_reports` | 命中过的报告文件数 |
| `file_coverage` | 总文件覆盖数 |
| `sample_contexts` | 最多 3 条上下文摘录（按长度降序） |
| `example_paths` | 命中次数 top 5 的文件路径 |

### MD — `extracts/term-frequency.md`

可读报告，含频次排序表、无命中词典条目、top 5 sample contexts。

---

## 词典（内置 42 条）

脚本内置术语词典，覆盖以下类别：

| 类别 | 示例术语 |
|------|----------|
| 模型架构 | MoE, Transformer, Attention, Token, Embedding |
| 训练对齐 | Fine-tune, 蒸馏, RLHF, CoT |
| 推理部署 | 量化, KV Cache, 上下文窗口, Rate Limit, 降智 |
| AI应用 | Agent, MCP, RAG, Function Calling, AI搜索 |
| 多模态 | 多模态, 语音, 图像生成, Diffusion |
| 安全风险 | 幻觉, API Key, Guardrails, 提示注入 |
| 开发工具 | 编码/Code, AI编程工具, API |
| 评测基准 | Benchmark, 数据污染 |
| 商业生态 | 开源协议, Open Weights, 账户风控, 开源模型 |

每个术语支持 **多个别名**（英文大小写词边界 + 中文子串匹配）：

```python
# 示例：MoE 的匹配模式
{
  "term": "MoE",
  "ids": ["MoE", "MOE", "Mixture of Experts", "混合专家"],  # 任一命中即计数
  "normalized_id": "moe"
}
```

---

## 如何扩展词典

在脚本 `DICTIONARY` 列表中添加条目：

```python
{"term": "新术语名",
 "ids": ["别名1", "别名2", "Alias3"],   # 必须填，至少 1 个
 "normalized_id": "new_term_id",        # snake_case，唯一
 "category": "模型架构",                 # 从现有类别选或新建
 "difficulty": "入门"}                   # 入门 / 中等 / 较难
```

重新运行即生效，无需改其他代码。

---

## 与概念库的关系

```text
本脚本                    ai-concept-bank 主流程
──────                    ─────────────────────
term-frequency.json  ───→ 人工/Agent 读取，裁定 candidate → draft
term-frequency.md    ───→ 月维护时 review 新增/归零术语
                           ↓
                      concepts.json（draft → ready via narrator）
                           ↓
                      ai-news-factory Phase1.6 / linuxdo-daily Writer
```

**本脚本只做频次统计，不直接改 `concepts.json`**。  
晋升 candidate / ready 需由人或 Agent 根据频次 + 判断裁定，再调 `ai-concept-narrator` 补台词。

---

## 运行频率（月维护）

| 时机 | 操作 |
|------|------|
| **每月至少 1 次** | 重跑脚本，对比新旧 `term-frequency.json` |
| 新黑话扎堆时 | 随时可跑 |
| 内容风格大变 | 考虑扩展词典后重跑 |

---

## 首次运行（2026-07-13 基线）

| 指标 | 值 |
|------|-----|
| 语料 | 脚本 50 + 日报 50 + 周报 5 + 月报 1 |
| 词典 | 42 条 |
| 有效术语 | 36（命中 ≥1 次） |
| 无命中 | 6 条（Embedding, RLHF, alignment, KV Cache, Attention, Transformer） |
| 总命中 | 4494 |
| Top 3 | 开源模型 1000 / AI编程工具 665 / Rate Limit 404 |

---

## 注意事项

- **运行目录**：建议在 `learn-claude-code/` 根目录执行；`--root` 可覆盖  
- **编码兼容**：自动尝试 UTF-8 → UTF-8-sig → GBK → Latin-1  
- **输出覆盖**：每次运行**覆盖** `extracts/` 下同名文件（非追加）  
- **不含自动晋升**：频次表是输入，不是命令；concepts.json 的变更需人审  
- **子模块脏态**：重跑后 `ai-concept-bank/` 会 dirty，需手动 commit + 父仓 bump  

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `ai-concept-bank/scripts/extract-term-frequency.py` | 本脚本 |
| `ai-concept-bank/extracts/term-frequency.json` | JSON 输出（运行时覆盖） |
| `ai-concept-bank/extracts/term-frequency.md` | MD 报告（运行时覆盖） |
| `ai-concept-bank/prompts/refresh-and-promote.md` | 术语频次 → candidate → ready 全流程 SOP |
| `ai-concept-bank/concepts.json` | 概念主库 |
| `ai-concept-bank/README.md` | 概念库总 SOP |
