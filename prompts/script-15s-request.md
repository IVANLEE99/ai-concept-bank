# 任务：生产 15 秒概念口播

为概念 `{id}` / `{name}` 生产 15 秒「黑话白说」口播，供 ai-concept-bank 使用。

## 语料依据

- 频次 count_total：`{count_total}`
- 上下文摘录：
  {sample_contexts}
- 路径示例：
  {example_paths}

## 角度

`{angle}`  
（默认：`基础定义`。若该角度已在 `angles.used` 中，换一个 `angles.available` 中未用的。）

## 可选今日新闻（可空）

```
{news_snippet}
```

## 约束

1. 严格公式：**概念名点题 → 白话定义 → 生活化比喻 → 价值/新闻关系**  
2. `script_15s` 目标 60–80 字，≤100 字  
3. 输出 **仅一个** JSON 对象，字段：

```json
{
  "id": "{id}",
  "one_liner": "",
  "analogy": "",
  "script_15s": "",
  "script_60s": null,
  "angle": "{angle}",
  "news_hook_optional": null,
  "confidence": "high",
  "facts_to_verify": [],
  "forbidden_check": "pass"
}
```

4. 先 Read `ai-concept-bank/concepts.json` 对应条目，避免与已有角度重复  
5. 违禁词：佬友、Linuxdo、L站、炸了、炸裂、大瓜、吃瓜、闹鬼、白嫖、薅羊毛、震惊  
6. 除非明确要求写入，否则只返回 JSON，不改文件；若要求写入，`script_meta.reviewed` 保持 `false`，`status` 保持 `draft`  

## 风格

说人话、可 TTS、技术正确；不确定则 `confidence: low` 并列出 `facts_to_verify`。
