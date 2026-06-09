# 使用说明：从 musclemimic 到 BadmintonRAG 的评估全流程

本文档说明如何把 **musclemimic** 的仿真/策略输出，喂给 **BadmintonRAG** 做正手高远球动作诊断，并得到带文献证据（`[Sxx]`）的报告。

```
musclemimic 仿真(.npz)
   │  export_forehand_clear_rag_csv.py   ← 在 musclemimic 侧导出
   ▼
forehand_clear CSV（符合 BadmintonRAG 数据契约）
   │  data_contract（校验） → batch / trial_run（诊断+检索）
   ▼
诊断报告（Markdown / JSON / 网页）  +  [Sxx] 文献证据（直接高远球 vs 杀球类比分层）
```

两个项目目录：
- musclemimic：`/data3/yangfeiyang/WorkSpace/musclemimic`（自带 `.venv`）
- BadmintonRAG：`/data3/yangfeiyang/WorkSpace/BadmintonRAG`（自带 `.venv`）

> 约定：下面用 `MM=/data3/yangfeiyang/WorkSpace/musclemimic`、`BR=/data3/yangfeiyang/WorkSpace/BadmintonRAG`。

---

## 第 0 步（一次性）：确认环境

```bash
MM=/data3/yangfeiyang/WorkSpace/musclemimic
BR=/data3/yangfeiyang/WorkSpace/BadmintonRAG

# BadmintonRAG 单元测试应全过
cd "$BR" && .venv/bin/python -m pytest -q          # 期望 82 passed

# 若要用 hybrid 检索（推荐），安装其依赖（一次）：
.venv/bin/python -m pip install -r requirements-hybrid.txt
# 首次使用 hybrid 会自动下载 bge-m3 模型(~2.3GB)到 BR/.models/，无 GPU 也能跑(CPU)。
```

---

## 第 1 步：在 musclemimic 侧导出 CSV

导出脚本：`MM/BadmintonMimic/scripts/export_forehand_clear_rag_csv.py`，把 MuJoCo rollout（`.npz`）转成 BadmintonRAG 契约 CSV。

**推荐用法（对照式：好动作做模板，待评估动作做诊断）**

```bash
cd "$MM"
.venv/bin/python BadmintonMimic/scripts/export_forehand_clear_rag_csv.py \
  --correct-input path/to/good_rollouts.npz \      # ≥5 条“标准/优秀”动作作参考模板
  --eval-input    path/to/eval_rollouts.npz \       # 待诊断的动作（有缺陷/真人/新策略）
  --outcome-label ball_high_not_far \               # 反映 eval 动作的真实结果（见下表）
  --semantic-muscles-only \                          # 只保留 4 个语义肌群，去掉 354 个 actuator 噪声
  --output "$MM/outputs/rag_alignment/my_trial.csv"
```

**快速用法（单文件，episode 0 当模板、其余当 eval）**

```bash
.venv/bin/python BadmintonMimic/scripts/export_forehand_clear_rag_csv.py \
  --input "$MM/trajectory_data/your_rollout.npz" \
  --semantic-muscles-only \
  --output "$MM/outputs/rag_alignment/my_trial.csv"
```

常用参数：
- `--outcome-label {ball_high_not_far, low_speed, uncoordinated_power}`：必须反映 eval 动作的**真实**后果，否则诊断只会套用该标签对应的故障规则。
- `--impact-frame N` / `--impact-time T`：若已知真实击球帧/时刻，传入更准（否则脚本按峰值角速度自动推断）。
- `--semantic-muscles-only`：**强烈建议加上**，否则会写出 354 列 `muscle_actuator_*` 噪声。

已有现成示例：`$MM/outputs/rag_alignment/forehand_clear_simulation.csv`（可直接拿来跑通流程）。

---

## 第 2 步：在 BadmintonRAG 侧校验数据契约

```bash
cd "$BR"
.venv/bin/python -m rag_project.diagnostics.data_contract \
  --csv-dataset "$MM/outputs/rag_alignment/my_trial.csv"
```

输出一段 JSON（行数、样本数、correct/eval 数、动作类型、信号列数）。**必须满足**：至少 1 个 `correct` 和 1 个 `eval` 样本，列含 `event_impact`，动作为 `forehand_clear`。详见 `docs/simulation_data_contract.md`。

---

## 第 3 步：诊断（核心）

### 方式 A：一键 trial（契约校验 + 诊断 + 生成网页索引）

```bash
cd "$BR"
bash scripts/run-csv.sh "$MM/outputs/rag_alignment/my_trial.csv" \
     rag_project/outputs/my_trial hybrid
# 参数：<csv> [输出目录] [keyword|vector|hybrid] [--llm]
```

输出目录会有：`diagnosis_reports.json`、`reports/*.md`、`report_index.html`。

### 方式 B：直接调 batch（更细控制）

```bash
cd "$BR"
.venv/bin/python -m rag_project.diagnostics.batch \
  --csv-dataset "$MM/outputs/rag_alignment/my_trial.csv" \
  --output-dir rag_project/outputs/my_trial \
  --retrieval-backend hybrid
```

**检索后端选择**：

| 后端 | 说明 |
|---|---|
| `keyword` | 旧的关键词重叠（默认，最快，无额外依赖） |
| `vector` | 本地 TF-IDF |
| `hybrid` | **推荐**：S01–S21 概念知识库 + BM25 + bge-m3 dense + 证据加权。证据带 `[Sxx]` 与分层标签（直接高远球 / 杀球类比），并落实“轨迹像≠肌肉对”“不展开手指”等护栏 |

> 加 `--llm` 可调用 OpenAI 兼容模型生成自然语言报告（需在 `.env` 设 `BADMINTON_LLM_BASE_URL/API_KEY/MODEL`）。不加则用确定性模板渲染，无需联网。

---

## 第 4 步：查看报告

**命令行**：直接看 `rag_project/outputs/my_trial/reports/<sample>.md`。每份报告含：诊断结论、关键偏差、可能机制、改进建议、**文献证据（`[S06]` + 证据层标签 + 摘要）**、证据边界。

**网页**：启动服务后用浏览器看（可加载/上传 CSV、调用诊断、渲染偏差与证据）：

```bash
cd "$BR"
bash scripts/serve.sh 127.0.0.1 8765      # 注意是位置参数：host port
# 浏览器打开 http://127.0.0.1:8765/ ，检索后端可选“混合(概念KB)”
# 关闭：Ctrl+C（前台）或  kill $(lsof -t -i:8765)
```

---

## 第 5 步（可选）：检索质量评测

```bash
cd "$BR"
.venv/bin/python -m rag_project.knowledge.evaluate_kb --k 10        # bm25+dense
.venv/bin/python -m rag_project.knowledge.evaluate_kb --no-dense --k 5   # BM25 基线
```

输出 recall@k / MRR / hit_rate 与复现元数据。当前 hybrid：recall@5≈0.85、MRR≈0.88（阈值见 `badminton_forehand_clear_RAG_package/citation_rubric.md`）。

---

## 数据契约速查

CSV 每行 = 一个样本的一个时间点；相同 `sample_id` 的行归为一个样本。

| 列 | 必需 | 含义 |
|---|---|---|
| `sample_id` | 是 | 样本唯一 id |
| `split` | 是 | `correct`=参考模板；`eval`=待诊断 |
| `action_type` | 是 | 目前固定 `forehand_clear` |
| `outcome_label` | 是 | `ball_high_not_far` / `low_speed` / `uncoordinated_power` |
| `time` | 是 | 秒 |
| `event_*` | 是（含 `event_impact`） | 事件时刻，秒 |
| `joint_*` | 是 | 关节角，度 |
| `muscle_*` | 是 | 肌肉激活，0–1 |

---

## 让评估“科学有效”的注意事项

这些来自对 musclemimic↔BadmintonRAG 数据契约的核查，直接影响诊断是否有意义：

1. **outcome_label 要真实**：导出时所有样本会被打上同一个 `--outcome-label`。它必须反映 eval 动作的真实结果，否则诊断只会机械套用该标签的故障规则。
2. **correct 与 eval 要有对比**：不要用同一条 rollout 的不同 episode 互相当模板和评估（动作几乎相同→检不出偏差）。用一批“标准/优秀”动作作 `--correct-input`，另一批“有缺陷/真人/新策略”作 `--eval-input`。
3. **参考样本 ≥5 条**：单个 correct 样本会让模板方差为 0、边界退化为 ±10%。≥5 条才有统计意义。
4. **加 `--semantic-muscles-only`**：去掉 354 个 actuator 噪声列，只用 4 个语义肌群。
5. **核对关节符号**：`joint_wrist_extension` 映射到 MuJoCo `flexion_r` 可能为负，符号约定若与文献相反会让偏差方向解读反掉，建议复核 `JOINT_SIGNAL_TO_MYO` 映射。

---

## 常见问题

- **hybrid 第一次很慢**：在下载 bge-m3(~2.3GB) + 首次编码 53 个 chunk（CPU 约数分钟），之后 embedding 缓存复用。想免依赖就用 `keyword`。
- **dense 用不了 / 没装依赖**：hybrid 会自动降级为 BM25+证据加权，不报错（报告里后端显示 `hybrid:bm25`）。
- **报告里没有证据**：keyword/vector 走的是 legacy HTML 语料；hybrid 走 S01–S21 概念库，证据更稳、带 `[Sxx]` 分层。
- **CUDA 驱动告警**：无害，torch 自动用 CPU。

更多：仓库根 `SYSTEM.md`（系统总览）、`badminton_forehand_clear_RAG_package/INTEGRATION.md`（集成细节）、`docs/simulation_data_contract.md`（契约全文）。
