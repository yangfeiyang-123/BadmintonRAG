# Badminton Forehand Clear RAG Package

本包用于构建“羽毛球正手高远球 / 后场正手高远球”中文 RAG 知识库。

> **v1.1（已审计修订）**：文献元数据按 2026-06 联网核查修正、生物力学时序与边界纠正、schema 硬化、并已生成可运行工件。详见知识库文档头部"修订说明"。

## 文件

- `badminton_forehand_clear_RAG_knowledge_base.md`：完整知识库设计文档（v1.1）。
- `badminton_forehand_clear_sources.csv`：文献 source catalog（已去 BOM、已修正元数据；主键列名为 `id`）。
- `source_id_crosswalk.csv`：S01–S21 ↔ rag_project legacy id 映射。
- `rag_chunk.schema.json` / `rag_source.schema.json`：chunk/source JSON Schema。chunk 的 `evidence_level` 是**粗粒度证据层**，与 source 的细粒度标签解耦（映射见知识库 §8.2）。
- `data/chunks.jsonl`：**已生成的 53 个概念级 chunk**，全部通过 chunk schema 校验，S01–S21 无孤儿。
- `gold_questions_zh.jsonl`：评测问题（11 题，含 type/forbidden_points）。
- `no_overclaim_tests.jsonl`：反幻觉/反过度声称负面测试（5 条）。
- `citation_rubric.md`：评测判分规则与可复现协议（检索/内容/引用/反幻觉四组指标 + 阈值）。
- `evaluate_rag.py`：自包含 BM25+证据加权检索评测入口（消费 gold 集 over chunks.jsonl）。
- `INTEGRATION.md`：接入 rag_project 的分步路线图。

## 实现要求

1. 读取 source catalog，稳定使用 `S01` 等 ID。
2. 抽取公开 PDF/HTML；对非开放全文只保存 metadata 和链接。
3. 按概念 chunk：动作阶段、肌肉、关节、指标、来源限制。
4. 每个 chunk 必须包含 source_ids、evidence_level、stroke、phase、body_region、joint_dof、muscle_groups、metrics、limits_of_evidence。
5. 检索使用 BM25 + multilingual dense embedding + metadata filter + reranker。
6. 回答必须输出 `[Sxx]` 引用，且区分直接高远球证据与杀球类比证据。
7. 用户排除手和手指时，不展开手指肌肉、握拍压力和掌指/指间关节。
8. 不允许说“动作轨迹正确，所以肌肉激活一定正确”。

## 最小命令建议

```bash
python scripts/ingest_sources.py --catalog corpus/00_source_catalog.csv --out data/raw
python scripts/chunk_documents.py --in data/clean --schema schemas/rag_chunk.schema.json --out data/chunks.jsonl
python scripts/build_hybrid_index.py --chunks data/chunks.jsonl --out data/index
python scripts/evaluate_rag.py --questions eval/gold_questions_zh.jsonl --index data/index
```
