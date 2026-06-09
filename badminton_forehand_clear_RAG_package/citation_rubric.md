# RAG 评测判分规则与可复现协议（citation_rubric）

本文件固化"羽毛球正手高远球 RAG"的科学评测协议，供 `evaluate_rag.py` 实现。覆盖检索、内容、引用与证据分层、反幻觉四组指标，以及可复现性元数据与基线门控。配套数据：`gold_questions_zh.jsonl`（检索/生成题）与 `no_overclaim_tests.jsonl`（负面题）。

## 0. 证据层真值（来自知识库 §8.1 / §8.2）

判分用的来源→证据层映射（唯一真值）：

| 层 | 来源 |
|---|---|
| direct_clear（直接高远球） | S01, S02, S03, S05, S06, S07 |
| overhead_multi_stroke（头顶多击球，含 clear） | S08 |
| mixed（含杀球的 power strokes） | S04 |
| skill_level_overhead（头顶通用） | S09 |
| review（综述） | S10 |
| smash_analogy（杀球类比） | S11, S12, S13, S14, S15 |
| msk_methodological（EMG+肌骨方法学） | S17 |
| dataset | S16, S21 |
| injury_review（伤病/肩负荷背景） | S18, S19, S20 |

"最危险错误"= 把 smash_analogy / msk / mixed 来源当作 direct_clear 确定真值（analogy 误标）。

## 1. 组 A：检索指标（仅对 `type=retrieval` 且 must_retrieve 非空的题）

对每题，设 R = 检索 top-k 的 source_id 集合，G = must_retrieve（金标）。

- **recall@k** = |R∩G| / |G|（多源按比例，不要用"有交集即 1"）。
- **hit_rate@k** = mean(1 if R∩G≠∅ else 0)（原实现误称 recall，应改名）。
- **MRR** = mean(1 / 第一个相关源的排名)。
- **nDCG@k**：二元相关性，rel=1 当 source∈G。
- 同时报 per-question 与 macro 平均。
- **通过阈值**：recall@5 ≥ 0.80，MRR ≥ 0.70。

> 注意：含 must_retrieve 中 rag_project 当前缺失的源（见 `source_id_crosswalk.csv` 中 match_type=none 的 S02/S03/S08/S13/S14/S15/S16/S17/S18-S21）的题，在补全语料前必然漏召；评测须先用 crosswalk 把 Sxx 映射到 legacy id，并对缺失源显式记 `missing_source` 而非静默计 0。

## 2. 组 B：内容正确性（expected_points / forbidden_points）

- **point_coverage** = 命中 expected_points 数 / 总数。判分器：固定 LLM-as-judge（temperature=0、固定模型 ID），对每个 point 输出 0/1 与依据；保留一个确定性后备（同义词归一化 + 子串匹配，作为可复现下界）。阈值 ≥ 0.80。
- **scope_compliance**（范围/越界）：答案若出现该题任一 `forbidden_points`（如手指外在肌、握拍压力、无来源精确角度/毫秒顺序），记违规。阈值 = 1.0（零违规）。
- `type=generation` 题（Q08）：不计检索；按 §9.3 必填字段覆盖率 **field_coverage ≥ 0.9** 判分。

## 3. 组 C：引用与证据分层

- **citation_precision** = 模型引用的 [Sxx] 中"与所支撑断言相符"的比例。阈值 ≥ 0.90。
- **citation_layer_accuracy** = 模型对引用证据层（direct/overhead/smash_analogy/...）标注正确的比例，真值用 §0 映射。阈值 ≥ 0.90。
- **analogy_mislabel_rate** = 把 smash_analogy/msk/mixed 来源当作 direct_clear 确定真值的比例。阈值 ≤ 0.05（越低越好）。
- **analogy_guardrail_pass_rate**：凡引用 S04/S08/S11–S15/S17 的句子，必须同时出现类比/限定词（"类比""杀球""非高远球真值""混合证据"等）或行内 `^` 标记，否则记 overclaim 违规。可用正则 + NLI 检测。阈值 = 1.0。

## 4. 组 D：反幻觉（`no_overclaim_tests.jsonl`）

对每条负面题：

- **negate_pass**：答案必须包含 `must_negate` 的否定语义（命中任一即视为已否定错误前提）。
- **reframe_pass**：答案应包含 `must_reframe` 的正确改述要点（覆盖 ≥ 1 项，建议 ≥ 2 项）。
- **forbidden_phrase_violation**：答案若出现 `forbidden_phrases` 任一，记违规。
- **通过条件**：negate_pass_rate = 1.0（全部正确否定）且 forbidden_phrase_violation = 0。

## 5. 可复现性元数据（每次评测结果 JSON 顶层必记）

```json
"run_metadata": {
  "git_commit": "...", "run_timestamp": "...", "seed": 0,
  "retrieval_backend": "keyword|vector|hybrid",
  "embedding_model": "name+version | none(tf-idf)",
  "reranker": "none|...",
  "n_chunks": 0, "chunks_sha256": "...", "gold_set_sha256": "...",
  "judge_model": "...", "judge_temperature": 0,
  "chunk_schema_version": "1.1"
}
```

- 每个 chunk 带 `content_hash`（text 的 sha256）与 `chunk_schema_version`，把一次评测绑定到确定的 `chunks.jsonl`。
- LLM 判分固定 temperature=0 并记录模型 ID。
- 当前实现若仍为 TF-IDF（非文档承诺的 BM25+dense+rerank），必须在 `retrieval_backend` 与报告中显式标注"当前为 TF-IDF 基线，非目标 hybrid 架构"，避免误读为已验证 hybrid。

## 6. 基线与门控（回归闭环）

- `eval/baseline.json` 存各指标当前基线值。
- 评测脚本末尾做门控：任一指标低于阈值，或低于基线容差（如 recall@5 < baseline−0.02），则 `exit(1)`。
- 有意提升基线时显式更新 `baseline.json` 并在提交信息记录原因。

## 7. 最小通过线（汇总）

| 组 | 指标 | 阈值 |
|---|---|---|
| A 检索 | recall@5 / MRR | ≥0.80 / ≥0.70 |
| B 内容 | point_coverage / scope_compliance / field_coverage(Q08) | ≥0.80 / =1.0 / ≥0.90 |
| C 引用 | citation_precision / citation_layer_accuracy / analogy_mislabel_rate / analogy_guardrail_pass_rate | ≥0.90 / ≥0.90 / ≤0.05 / =1.0 |
| D 反幻觉 | negate_pass_rate / forbidden_phrase_violation | =1.0 / =0 |

> 前置条件：组 A/B/C 能成立的前提是 EVAL-01（统一 ID、让评测真正消费 gold 集）已打通；组 D 依赖 `no_overclaim_tests.jsonl`（已提供）。
