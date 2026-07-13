#!/usr/bin/env python3
"""
extract-term-frequency.py
─────────────────────────
扫描语料（视频脚本 + 日报 + 周报 + 月报），输出：
  ai-concept-bank/extracts/term-frequency.json
  ai-concept-bank/extracts/term-frequency.md

用法：
  python3 ai-concept-bank/scripts/extract-term-frequency.py [--root /path/to/learn-claude-code]

输出字段与初始 seed 的 term-frequency.json 完全对齐（count_scripts / count_reports /
count_daily / count_weekly / count_monthly / count_total / files_scripts / files_reports /
file_coverage / sample_contexts / example_paths / suggested_label / category / difficulty）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ──────────────────────────────────────────────
# 0. 术语词典：term → normalized_id, category, difficulty
#    可按需扩展；脚本也收集「未命中词典但频率明显高」的残余。
# ──────────────────────────────────────────────
DICTIONARY: list[dict] = [
    # --- 模型架构 ---
    {"term": "MoE",             "ids": ["MoE", "MOE", "Mixture of Experts", "混合专家"],
     "normalized_id": "moe",    "category": "模型架构", "difficulty": "中等"},
    {"term": "Attention",       "ids": ["Attention", "注意力机制", "Self-Attention", "Multi-Head Attention"],
     "normalized_id": "attention", "category": "模型架构", "difficulty": "中等"},
    {"term": "Transformer",     "ids": ["Transformer", "Transformer架构"],
     "normalized_id": "transformer", "category": "模型架构", "difficulty": "入门"},
    {"term": "KV Cache",        "ids": ["KV Cache", "KVcache", "kv cache", "KV缓存"],
     "normalized_id": "kv_cache", "category": "推理部署", "difficulty": "中等"},
    {"term": "Embedding",       "ids": ["Embedding", "embedding", "向量嵌入", "文本嵌入"],
     "normalized_id": "embedding", "category": "模型架构", "difficulty": "入门"},
    {"term": "Tokenizer",       "ids": ["Tokenizer", "tokenizer", "分词器", "BPE"],
     "normalized_id": "tokenizer", "category": "模型架构", "difficulty": "入门"},

    # --- 训练与对齐 ---
    {"term": "Fine-tune / 微调", "ids": ["Fine-tune", "Finetune", "fine-tune", "fine tune", "微调", "finetune"],
     "normalized_id": "finetune", "category": "训练对齐", "difficulty": "入门"},
    {"term": "RLHF",            "ids": ["RLHF", "RLHF对齐", "从人类反馈中强化学习"],
     "normalized_id": "rlhf",   "category": "训练对齐", "difficulty": "中等"},
    {"term": "蒸馏",            "ids": ["蒸馏", "知识蒸馏", "distillation", "Distillation"],
     "normalized_id": "distillation", "category": "训练对齐", "difficulty": "中等"},
    {"term": "对齐",            "ids": ["对齐", "alignment", "Alignment", "价值对齐"],
     "normalized_id": "alignment", "category": "训练对齐", "difficulty": "入门"},

    # --- 推理与部署 ---
    {"term": "量化",            "ids": ["量化", "quantization", "Quantization", "INT8", "INT4", "4-bit", "8-bit", "GGUF", "GPTQ", "AWQ"],
     "normalized_id": "quantization", "category": "推理部署", "difficulty": "中等"},
    {"term": "上下文窗口",      "ids": ["上下文窗口", "上下文长度", "context window", "Context Window", "Context Length"],
     "normalized_id": "context_window", "category": "推理部署", "difficulty": "入门"},
    {"term": "推理",            "ids": ["推理", "inference", "Inference", "推理效率", "推理加速"],
     "normalized_id": "inference", "category": "推理部署", "difficulty": "入门"},
    {"term": "Rate Limit / 配额", "ids": ["Rate Limit", "rate limit", "限流", "配额", "额度", "速率限制"],
     "normalized_id": "rate_limit", "category": "推理部署", "difficulty": "入门"},

    # --- AI Agent ---
    {"term": "Agent",           "ids": ["Agent", "智能体", "AI Agent", "agent", "Agent能力"],
     "normalized_id": "agent",  "category": "AI应用", "difficulty": "入门"},
    {"term": "MCP",             "ids": ["MCP", "Model Context Protocol", "mcp"],
     "normalized_id": "mcp",    "category": "AI应用", "difficulty": "中等"},
    {"term": "Function Calling","ids": ["Function Calling", "function calling", "工具调用", "Tool Use", "tool use"],
     "normalized_id": "function_calling", "category": "AI应用", "difficulty": "中等"},

    # --- 检索增强 ---
    {"term": "RAG",             "ids": ["RAG", "检索增强生成", "检索增强", "Retrieval Augmented"],
     "normalized_id": "rag",    "category": "AI应用", "difficulty": "入门"},

    # --- 多模态 ---
    {"term": "多模态",          "ids": ["多模态", "multimodal", "Multimodal", "视觉语言", "VLM"],
     "normalized_id": "multimodal", "category": "多模态", "difficulty": "入门"},

    # --- 安全与风险 ---
    {"term": "幻觉",            "ids": ["幻觉", "hallucination", "Hallucination", "胡说"],
     "normalized_id": "hallucination", "category": "安全风险", "difficulty": "入门"},
    {"term": "提示注入",        "ids": ["提示注入", "prompt injection", "Prompt Injection", "越狱", "jailbreak"],
     "normalized_id": "prompt_injection", "category": "安全风险", "difficulty": "中等"},
    {"term": "API Key / 密钥",  "ids": ["API Key", "API key", "API密钥", "密钥泄露", "api key"],
     "normalized_id": "api_key", "category": "安全风险", "difficulty": "入门"},
    {"term": "Guardrails",      "ids": ["Guardrails", "guardrails", "护栏", "安全护栏", "安全策略"],
     "normalized_id": "guardrails", "category": "安全风险", "difficulty": "中等"},

    # --- 编程与开发工具 ---
    {"term": "编码 / Code",     "ids": ["编码", "Code能力", "代码生成", "AI编程", "coding", "code model",
                                         "编程模型", "编程能力"],
     "normalized_id": "coding", "category": "开发工具", "difficulty": "入门"},

    # --- 评测与基准 ---
    {"term": "Benchmark",       "ids": ["Benchmark", "benchmark", "评测", "跑分", "基准测试", "排行榜"],
     "normalized_id": "benchmark", "category": "评测基准", "difficulty": "入门"},
    {"term": "数据污染",        "ids": ["数据污染", "data contamination", "Data Contamination", "评测作弊"],
     "normalized_id": "data_contamination", "category": "评测基准", "difficulty": "中等"},

    # --- 商业与生态 ---
    {"term": "开源协议",        "ids": ["开源协议", "Apache 2.0", "Apache", "MIT License", "开源许可", "许可协议",
                                         "License", "license", "商用许可"],
     "normalized_id": "license", "category": "商业生态", "difficulty": "入门"},
    {"term": "Open Weights / 开源", "ids": ["Open Weights", "open weights", "开源模型", "开源权重",
                                             "开源", "Open Source"],
     "normalized_id": "open_weights", "category": "商业生态", "difficulty": "入门"},

    # --- 概念延伸（扩展种子） ---
    {"term": "Token",           "ids": ["Token", "token", "token数", "tokens"],
     "normalized_id": "token",  "category": "模型架构", "difficulty": "入门"},
    {"term": "Prompt",          "ids": ["Prompt", "prompt", "提示词", "提示工程", "Prompt Engineering"],
     "normalized_id": "prompt", "category": "AI应用", "difficulty": "入门"},
    {"term": "Chain of Thought","ids": ["Chain of Thought", "CoT", "COT", "思维链", "逐步推理"],
     "normalized_id": "cot",    "category": "训练对齐", "difficulty": "中等"},
    {"term": "Diffusion",       "ids": ["Diffusion", "diffusion", "扩散模型"],
     "normalized_id": "diffusion", "category": "模型架构", "difficulty": "中等"},
    {"term": "降智",            "ids": ["降智", "变笨", "能力下降", "退步"],
     "normalized_id": "model_dumbing", "category": "推理部署", "difficulty": "入门"},
    {"term": "账户风控",        "ids": ["封号", "封号潮", "KYC", "二验", "二次验证", "验证风暴",
                                         "账号风控", "风控"],
     "normalized_id": "account_risk", "category": "商业生态", "difficulty": "入门"},
    {"term": "API",             "ids": ["API", "接口", "api"],
     "normalized_id": "api",    "category": "开发工具", "difficulty": "入门"},
    {"term": "SD / SSD Bug",    "ids": ["SSD", "SSD写入", "磁盘磨损", "日志膨胀"],
     "normalized_id": "ssd_bug", "category": "安全风险", "difficulty": "入门"},
    {"term": "AI搜索",          "ids": ["AI搜索", "AI Search", "搜索引擎", "搜索增强"],
     "normalized_id": "ai_search", "category": "AI应用", "difficulty": "入门"},
    {"term": "语音",            "ids": ["语音", "TTS", "语音合成", "语音模型", "Voice", "ASR"],
     "normalized_id": "voice",  "category": "多模态", "difficulty": "入门"},
    {"term": "图像生成",        "ids": ["图像生成", "文生图", "图生图", "Image Generation", "DALL-E", "Midjourney"],
     "normalized_id": "image_gen", "category": "多模态", "difficulty": "入门"},
    {"term": "自动驾驶",        "ids": ["自动驾驶", "无人驾驶", "L3", "L4", "智能驾驶"],
     "normalized_id": "autonomous_driving", "category": "AI应用", "difficulty": "入门"},
    {"term": "AI编程工具",      "ids": ["Codex", "Cursor", "Claude Code", "Windsurf", "Copilot", "Kiro",
                                         "编程工具", "AI IDE", "Code Harness"],
     "normalized_id": "coding_tools", "category": "开发工具", "difficulty": "入门"},
    {"term": "开源模型",        "ids": ["GLM", "DeepSeek", "Qwen", "Kimi", "MiniMax", "盘古", "混元",
                                         "豆包", "Grok", "Gemma", "Llama", "Mistral"],
     "normalized_id": "open_models", "category": "商业生态", "difficulty": "入门"},
]

# ──────────────────────────────────────────────
# 1. 语料发现
# ──────────────────────────────────────────────
def discover_corpus(root: Path):
    """返回 (scripts, daily, weekly, monthly) 路径列表，按规范排除。"""
    scripts: list[Path] = []
    for p in root.glob("news-pipeline/**/scripts/*"):
        if p.is_file() and p.suffix in (".md", ".txt") and "node_modules" not in p.parts:
            scripts.append(p)
    # 顶层 legacy
    for p in (root / "news-pipeline" / "scripts").glob("*"):
        if p.is_file() and p.suffix in (".md", ".txt"):
            if p not in scripts:
                scripts.append(p)

    daily: list[Path] = []
    for p in (root / "data" / "reports").glob("*.md"):
        name = p.name
        if name.endswith("_press.md") or "press" in name:
            continue
        if name.startswith("2026-W"):   # week file in reports/ (press)
            continue
        daily.append(p)

    weekly: list[Path] = []
    for p in (root / "data" / "weekly").glob("*.md"):
        if "press" not in p.name:
            weekly.append(p)

    monthly: list[Path] = []
    for p in (root / "data" / "monthly").glob("*.md"):
        if "press" not in p.name:
            monthly.append(p)

    return scripts, daily, weekly, monthly


def read_text_safe(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except (UnicodeDecodeError, ValueError):
            continue
    return ""

# ──────────────────────────────────────────────
# 2. 匹配引擎
# ──────────────────────────────────────────────
def compile_patterns(dictionary: list[dict]) -> list[dict]:
    """为每个 term 编译一组 regex pattern，支持英文大小写词边界 + 中文子串。"""
    compiled = []
    for entry in dictionary:
        patterns = []
        for alias in entry["ids"]:
            if re.search(r"[A-Za-z]", alias):
                # 英文：词边界，大小写不敏感（保留原形用于 sample 匹配）
                patterns.append(re.compile(r"\b" + re.escape(alias) + r"\b", re.IGNORECASE))
            else:
                # 中文/数字混合：子串匹配
                patterns.append(re.compile(re.escape(alias)))
        compiled.append({**entry, "_patterns": patterns})
    return compiled


def scan_file(text: str, file_path_str: str, compiled: list[dict],
              term_stats: dict, max_contexts: int = 3, context_radius: int = 120):
    """扫描单个文件，更新 term_stats。"""
    for entry in compiled:
        tid = entry["normalized_id"]
        st = term_stats[tid]
        hits = 0
        for pat in entry["_patterns"]:
            for m in pat.finditer(text):
                hits += 1
                # sample context（每 term 最多 max_contexts 条）
                if len(st["_sample_ctxs"]) < max_contexts:
                    start = max(0, m.start() - context_radius)
                    end   = min(len(text), m.end() + context_radius)
                    ctx   = text[start:end].replace("\n", " ").strip()
                    if ctx and ctx not in st["_sample_ctxs"]:
                        st["_sample_ctxs"].append(ctx)
        if hits > 0:
            st["_count"] += hits
            st["_files"][file_path_str] += hits


def run_extraction(root: Path, dictionary: list[dict]) -> dict:
    compiled = compile_patterns(dictionary)

    # init stats
    term_stats: dict[str, dict] = {}
    for entry in compiled:
        tid = entry["normalized_id"]
        if tid not in term_stats:
            term_stats[tid] = {
                "_count": 0,
                "_count_scripts": 0, "_count_reports": 0,
                "_count_daily": 0, "_count_weekly": 0, "_count_monthly": 0,
                "_files_scripts": set(), "_files_reports": set(),
                "_files": Counter(),    # all files
                "_sample_ctxs": [],
                "_category": entry["category"],
                "_difficulty": entry["difficulty"],
                "_term": entry["term"],
            }

    scripts, daily, weekly, monthly = discover_corpus(root)

    # per-file-category counters
    for path in scripts:
        text = read_text_safe(path)
        if not text:
            continue
        rel = str(path.relative_to(root))
        for entry in compiled:
            tid = entry["normalized_id"]
            before = term_stats[tid]["_count"]
        scan_file(text, rel, compiled, term_stats)
        for entry in compiled:
            tid = entry["normalized_id"]
            pass  # count is updated in scan_file
        # track which category each path belongs to — done below per term

    # Better approach: scan per category
    scripts_paths = {str(p.relative_to(root)) for p in scripts}
    daily_paths   = {str(p.relative_to(root)) for p in daily}
    weekly_paths  = {str(p.relative_to(root)) for p in weekly}
    monthly_paths = {str(p.relative_to(root)) for p in monthly}

    # Reset and rescan properly
    for tid in term_stats:
        term_stats[tid]["_count"] = 0
        term_stats[tid]["_count_scripts"] = 0
        term_stats[tid]["_count_reports"] = 0
        term_stats[tid]["_count_daily"] = 0
        term_stats[tid]["_count_weekly"] = 0
        term_stats[tid]["_count_monthly"] = 0
        term_stats[tid]["_files"] = Counter()
        term_stats[tid]["_files_scripts"] = set()
        term_stats[tid]["_files_reports"] = set()
        term_stats[tid]["_sample_ctxs"] = []

    all_paths = scripts + daily + weekly + monthly
    for path in all_paths:
        text = read_text_safe(path)
        if not text:
            continue
        rel = str(path.relative_to(root))
        scan_file(text, rel, compiled, term_stats)
        # post-scan: attribute hits to category
        for tid, st in term_stats.items():
            hits = st["_files"].get(rel, 0)
            if hits == 0:
                continue
            if rel in scripts_paths:
                st["_count_scripts"] += hits
                st["_files_scripts"].add(rel)
            if rel in daily_paths:
                st["_count_daily"] += hits
            if rel in weekly_paths:
                st["_count_weekly"] += hits
            if rel in monthly_paths:
                st["_count_monthly"] += hits
            if rel in daily_paths or rel in weekly_paths or rel in monthly_paths:
                st["_count_reports"] += hits
                st["_files_reports"].add(rel)

    # Build output
    terms = []
    for tid, st in term_stats.items():
        total = st["_count_scripts"] + st["_count_reports"]
        if total == 0:
            continue
        file_cov = len(st["_files_scripts"]) + len(st["_files_reports"])
        # rank sample contexts by relevance (longer first)
        ctxs = sorted(st["_sample_ctxs"], key=len, reverse=True)[:3]
        # top paths by hit count
        top_paths = [p for p, _ in st["_files"].most_common(5)]

        terms.append({
            "term":            st["_term"],
            "normalized_id":   tid,
            "category":        st["_category"],
            "difficulty":      st["_difficulty"],
            "count_scripts":   st["_count_scripts"],
            "count_reports":   st["_count_reports"],
            "count_daily":     st["_count_daily"],
            "count_weekly":    st["_count_weekly"],
            "count_monthly":   st["_count_monthly"],
            "count_total":     total,
            "files_scripts":   len(st["_files_scripts"]),
            "files_reports":   len(st["_files_reports"]),
            "file_coverage":   file_cov,
            "sample_contexts": ctxs,
            "example_paths":   top_paths,
            "suggested_label": st["_term"],
        })

    terms.sort(key=lambda t: t["count_total"], reverse=True)

    generated_at = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    sources = {
        "scripts":      len(scripts),
        "daily_reports": len(daily),
        "weekly":       len(weekly),
        "monthly":      len(monthly),
    }

    return {
        "generated_at":    generated_at,
        "sources":         sources,
        "dictionary_size": len(dictionary),
        "terms":           terms,
    }


# ──────────────────────────────────────────────
# 3. 输出 JSON + MD
# ──────────────────────────────────────────────
def write_json(data: dict, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] JSON → {out}  ({len(data['terms'])} terms, {sum(t['count_total'] for t in data['terms'])} total hits)")


def write_md(data: dict, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# 术语频次表（自动生成）",
        "",
        f"> 生成时间：{data['generated_at']}  ",
        f"> 词典大小：{data['dictionary_size']} 个条目  ",
        f"> 语料来源：脚本 {data['sources']['scripts']} · 日报 {data['sources']['daily_reports']} · 周报 {data['sources']['weekly']} · 月报 {data['sources']['monthly']}  ",
        f"> 有效术语：{len(data['terms'])} 个（命中 ≥1 次）  ",
        "",
        "## 频次排序（降序）",
        "",
        "| # | 术语 | id | 类别 | 难度 | 脚本 | 报告 | 日 | 周 | 月 | 总计 | 文件覆盖 |",
        "|---|------|----|------|------|------|------|----|----|----|------|----------|",
    ]
    for i, t in enumerate(data["terms"], 1):
        lines.append(
            f"| {i} | {t['term']} | `{t['normalized_id']}` | {t['category']} | {t['difficulty']} "
            f"| {t['count_scripts']} | {t['count_reports']} | {t['count_daily']} "
            f"| {t['count_weekly']} | {t['count_monthly']} | **{t['count_total']}** "
            f"| {t['file_coverage']} |"
        )

    lines += [
        "",
        "## 无命中术语（词典中但语料未发现）",
        "",
    ]
    hit_ids = {t["normalized_id"] for t in data["terms"]}
    for entry in sorted(DICTIONARY, key=lambda e: e["normalized_id"]):
        if entry["normalized_id"] not in hit_ids:
            lines.append(f"- `{entry['normalized_id']}` {entry['term']}")

    lines += [
        "",
        "---",
        "",
        f"## Sample Contexts（top {min(5, len(data['terms']))} 术语）",
        "",
    ]
    for t in data["terms"][:5]:
        lines.append(f"### {t['term']}（{t['normalized_id']}）")
        for ctx in t["sample_contexts"][:2]:
            lines.append(f"> {ctx[:200]}{'…' if len(ctx) > 200 else ''}")
            lines.append("")
        lines.append(f"Top paths：`{'`, `'.join(t['example_paths'][:3])}`")
        lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[OK] MD   → {out}")


# ──────────────────────────────────────────────
# 4. CLI
# ──────────────────────────────────────────────
def find_root() -> Path:
    """尝试从脚本位置向上推断项目根目录。"""
    script_dir = Path(__file__).resolve().parent          # ai-concept-bank/scripts/
    candidate  = script_dir.parent.parent                 # learn-claude-code/
    if (candidate / "data" / "reports").is_dir():
        return candidate
    # fallback: cwd
    cwd = Path.cwd()
    if (cwd / "data" / "reports").is_dir():
        return cwd
    print("[ERR] 无法定位项目根，请用 --root 指定", file=sys.stderr)
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Extract term-frequency from corpus")
    parser.add_argument("--root", type=Path, default=None, help="项目根目录（默认自动推断）")
    parser.add_argument("--out",  type=Path, default=None, help="JSON 输出路径（默认 ai-concept-bank/extracts/）")
    parser.add_argument("--no-md", action="store_true", help="不生成 .md 报告")
    args = parser.parse_args()

    root = args.root or find_root()
    print(f"[INFO] 项目根：{root}")
    print(f"[INFO] 词典条目：{len(DICTIONARY)}")

    data = run_extraction(root, DICTIONARY)

    out_dir = args.out or (root / "ai-concept-bank" / "extracts")
    write_json(data, out_dir / "term-frequency.json")
    if not args.no_md:
        write_md(data, out_dir / "term-frequency.md")

    # print top 10
    print("\n[Top 10]")
    for i, t in enumerate(data["terms"][:10], 1):
        print(f"  {i:2d}. {t['term']:<25s} scripts={t['count_scripts']:4d}  reports={t['count_reports']:4d}  total={t['count_total']:4d}  files={t['file_coverage']}")


if __name__ == "__main__":
    main()
