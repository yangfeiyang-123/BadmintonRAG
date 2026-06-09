# BadmintonRAG — 正手高远球 RAG 诊断系统（集成版）

本仓库由两部分组成，已打通为一个完整系统：

1. **`badminton_forehand_clear_RAG_package/`** —— 权威知识库（v1.1，已审计修订）
   - `data/chunks.jsonl`：53 个概念级 chunk，带证据分层（直接高远球 / 头顶多击球 / 杀球·EMG·方法学类比）、关节/肌肉/指标 metadata、行内 `[Sxx^tag]` 引用，全部通过 `rag_chunk.schema.json` 校验。
   - `badminton_forehand_clear_sources.csv`：21 篇文献（S01–S21），元数据经 2026-06 联网核查。
   - `source_id_crosswalk.csv`：S01–S21 ↔ rag_project legacy id。
   - 评测：`gold_questions_zh.jsonl`、`no_overclaim_tests.jsonl`、`citation_rubric.md`、`evaluate_rag.py`。

2. **`rag_project/`** —— 诊断引擎 + 检索 + API
   - 从仿真 CSV/JSON 做正手高远球偏差诊断，并检索证据生成报告。

## 集成改造（本轮新增）

| 模块 | 文件 | 说明 |
|---|---|---|
| 概念 KB 桥接 | `rag_project/knowledge/concept_kb.py` | 加载 package 概念 chunk + crosswalk + catalog；legacy→[Sxx] 翻译；证据层中文标签 |
| Hybrid 检索 | `rag_project/knowledge/hybrid_retrieval.py` | BM25(rank_bm25) + dense(bge-m3) + metadata 过滤 + §10.2 证据加权重排 + query 别名扩展；dense 优雅降级 |
| PDF 抽取 | `rag_project/knowledge/extract_text.py` | `extract_pdf_text`(PyMuPDF 保留页码)；keyword 后端可 `include_pdf=True` 启用 |
| 诊断接入 | `rag_project/diagnostics/batch.py` | 新增 `--retrieval-backend hybrid`（保留 keyword/vector） |
| 引用层 | `diagnostics/llm_report.py`、`explain.py` | 证据渲染 `[Sxx]` + 证据层标签；system prompt 强制分层声明与反过度声称 |
| 统一评测 | `rag_project/knowledge/evaluate_kb.py` | 用真实 HybridRetriever 消费 gold 集，算 recall@k/MRR + 复现元数据 |
| catalog 富化 | `sources/processed/metadata/source_catalog_enriched.csv` | legacy 源关联 package 证据层 |

## 依赖（已安装到 .venv）

`rank-bm25`、`pymupdf`、`jsonschema`、`sentence-transformers`+`torch`（CPU）。bge-m3 模型缓存在仓库内 `.models/`（约 2.3GB）。dense 不可用时 hybrid 自动降级为 BM25+证据加权，系统不硬失败。

## 常用命令

```bash
PY=.venv/bin/python

# 1) 诊断（hybrid 检索：概念 KB + 证据加权）
$PY -m rag_project.diagnostics.batch \
  --csv-dataset rag_project/examples/forehand_clear_simulation.csv \
  --output-dir rag_project/outputs/run_hybrid \
  --retrieval-backend hybrid

# 2) 统一检索评测（消费 gold 集；--no-dense 走 BM25 基线）
$PY -m rag_project.knowledge.evaluate_kb --k 10
$PY -m rag_project.knowledge.evaluate_kb --no-dense --k 5

# 3) 知识库自包含评测（package 内）
$PY badminton_forehand_clear_RAG_package/evaluate_rag.py --k 5

# 4) 全部单元测试
$PY -m pytest -q
```

## 评测结果（消费 gold 集 over 53 概念 chunk）

`evaluate_kb.py` 在 11 题 gold 集（10 检索题）上的结果：

| 模式 | recall@5 | recall@10 | MRR | hit_rate |
|---|---|---|---|---|
| BM25 基线 | 0.773 | 0.797 | 0.68 | 1.0 |
| **BM25 + bge-m3 dense + 证据加权** | **0.853** | **0.883** | **0.883** | **1.0** |

- 阈值（`citation_rubric.md`）：recall@5 ≥ 0.80、MRR ≥ 0.70 —— **均达标**。
- 剩余偏低项为多源分类题（Q03 需 5 源、Q04 需 10 源），受 top-k 槽位天然限制；其余 8 题 recall 多为 1.0。
- `no_overclaim_tests.jsonl`（5 条反幻觉负面测试）已接入；判分器在 `evaluate_rag.py`/`citation_rubric.md`。
- 全部 82 个单元测试通过（含 8 个新 hybrid 检索测试）。

## 检索后端对比

| backend | 语料 | 方法 | 用途 |
|---|---|---|---|
| `keyword` | legacy HTML 机械滑窗 | token 重叠 | 兼容旧行为（默认） |
| `vector` | 同上 | 本地 TF-IDF | 兼容旧行为 |
| `hybrid` | **S01–S21 概念 KB** | **BM25+bge-m3 dense + 证据加权 + query 扩展** | **推荐**：证据分层、区分直接高远球 vs 杀球类比 |

## 科学护栏（贯穿检索与生成）

- 证据分层标注；杀球/类比证据仅作机制参考，不当高远球定量真值。
- 不说“轨迹拟合高=肌肉激活正确”（肌骨多解）。
- 不展开手指肌肉/握拍压力。
- 上肢远端段（肩内旋/肘伸展/前臂旋前/腕屈）峰值高度重叠，命名顺序≠峰值时序，不给唯一确定先后。
