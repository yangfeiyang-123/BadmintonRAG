# S01–S21 知识库 ↔ rag_project 集成（已完成）

本包是面向用户引用的**权威知识库**（S01–S21 + 概念级 chunk + 证据分层）。`rag_project` 是诊断/检索实现（legacy 字符串 ID）。下面 6 步已全部落地，详见仓库根 `SYSTEM.md`。

| 步骤 | 状态 | 落地文件 |
|---|---|---|
| 1. 引用层 legacy→[Sxx] 翻译 + 证据层标签 [INTEG-06] | ✅ | `diagnostics/llm_report.py`、`explain.py`、`knowledge/concept_kb.py` |
| 2. 概念 chunk 进检索库 [INTEG-03] | ✅ | `knowledge/concept_kb.py`（加载 `data/chunks.jsonl` 为检索单元） |
| 3. PDF 抽取 [INTEG-04] | ✅ | `knowledge/extract_text.py`（`extract_pdf_text`/`extract_text`）；keyword 后端 `include_pdf=True` 启用 |
| 4. Hybrid 检索 [INTEG-05] | ✅ | `knowledge/hybrid_retrieval.py`（BM25+bge-m3 dense+metadata filter+§10.2 证据加权+query 扩展）；`batch.py` 加 `--retrieval-backend hybrid` |
| 5. 统一评测入口 [EVAL-01] | ✅ | `knowledge/evaluate_kb.py`（消费 gold 集，缺失源记 `missing_from_corpus`） |
| 6. catalog 证据层字段 [INTEG-02] | ✅ | `sources/processed/metadata/source_catalog_enriched.csv` |

## 设计要点
- **概念 KB 为主检索语料**：hybrid 后端检索 53 个概念 chunk（带证据分层、关节/肌肉 metadata），legacy HTML 机械滑窗 corpus 保留作原文回链。
- **向后兼容**：keyword/vector 后端与默认行为完全不变（PDF 为 opt-in）；hybrid 是新增选项。全部 74 单元测试通过。
- **dense 优雅降级**：bge-m3 不可用时自动退到 BM25+证据加权，不硬失败。
- **crosswalk**：9 条 S↔legacy 映射（S01/S04/S05/S06/S07/S09/S10/S11/S12）；诊断输出经其把 legacy id 译成 `[Sxx]`。

## 仍可继续（可选）
- 扩展 dense 到 reranker（cross-encoder）做二阶段重排。
- 补抓 gold 必需但 rag_project legacy 缺失的源（S02/S03/S13/S14/S16 等）到 legacy corpus（概念 KB 已覆盖其知识）。
- 把机械滑窗 corpus 也用概念切分重建。
