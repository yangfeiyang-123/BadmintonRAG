# 正手高远球动作诊断 RAG 系统设计

日期：2026-06-08

## 1. 目标

构建一个研究级正手高远球动作诊断知识库系统。系统接收待评估动作的关节角度时序、肌肉激活时序和离散动作后果标签，与正确动作模板进行阶段对齐和偏差检测，输出“哪里错、为什么错、如何改进”，并用已下载文献和官方资料提供证据解释。

第一版只覆盖正手高远球，不覆盖杀球、发球、网前球、蹬跨步或视频姿态估计。

## 2. 非目标

- 不直接从视频识别动作。
- 不训练黑盒错误分类模型。
- 不把书籍预览页、Airiti 元数据页、受限来源摘要当作全文证据。
- 不把没有 EMG 实测证据的文献结论强行写成“某肌肉激活不足”。这类结论只能标为生物力学推断。
- 不做医疗诊断。损伤风险只作为动作机制层面的研究提示。

## 3. 输入数据

系统第一版接收结构化时序数据。每条样本包含：

```json
{
  "sample_id": "clear_001",
  "action_type": "forehand_clear",
  "outcome_label": "ball_high_not_far",
  "time": [0.0, 0.01, 0.02],
  "events": {
    "preparation_start": 0.0,
    "backswing_start": 0.18,
    "acceleration_start": 0.42,
    "impact": 0.63,
    "follow_through_end": 0.92
  },
  "joint_angles": {
    "trunk_rotation": [0.0, 1.2, 2.4],
    "shoulder_abduction": [45.0, 46.2, 47.1],
    "shoulder_internal_rotation": [5.0, 5.4, 5.9],
    "elbow_flexion": [92.0, 91.5, 91.0],
    "wrist_extension": [18.0, 18.7, 19.1],
    "hip_rotation": [0.0, 0.8, 1.5],
    "knee_flexion_drive_side": [28.0, 27.4, 26.8],
    "ankle_plantarflexion_drive_side": [4.0, 4.8, 5.2]
  },
  "muscle_activation": {
    "external_oblique": [0.12, 0.14, 0.16],
    "pectoralis_major": [0.08, 0.09, 0.10],
    "latissimus_dorsi": [0.05, 0.06, 0.07],
    "anterior_deltoid": [0.10, 0.12, 0.15],
    "triceps_brachii": [0.06, 0.07, 0.08],
    "forearm_pronator_group": [0.04, 0.05, 0.06],
    "gluteus_maximus": [0.08, 0.09, 0.11],
    "quadriceps": [0.10, 0.11, 0.12],
    "gastrocnemius": [0.05, 0.05, 0.06]
  }
}
```

字段要求：

- `time` 单位为秒。
- 肌肉激活值默认使用归一化值，例如 MVC 归一化或仿真系统内部归一化；数据源必须记录归一化方法。
- `events.impact` 必须存在，因为诊断以击球瞬间为核心对齐点。
- 如果动作阶段事件不完整，系统可以只用 `impact` 做时间归一化，但报告中必须标记阶段置信度较低。

## 4. 输出格式

系统输出结构化诊断结果：

```json
{
  "sample_id": "clear_001",
  "action_type": "forehand_clear",
  "outcome_label": "ball_high_not_far",
  "primary_diagnosis": "击球阶段向前动量不足，末端释放效率偏低",
  "diagnostic_confidence": "medium",
  "key_deviations": [
    {
      "feature": "trunk_rotation_peak",
      "phase": "acceleration",
      "direction": "below_template",
      "severity": "high",
      "template_value": 42.0,
      "observed_value": 31.0,
      "unit": "degree",
      "interpretation": "躯干旋转参与不足，可能降低近端到远端的动力链传递。"
    }
  ],
  "likely_mechanisms": [
    "躯干带动不足",
    "肩臂代偿提前",
    "肘腕释放滞后或不足",
    "击球方向更偏向上而不是向前"
  ],
  "correction_suggestions": [
    "优先练习蹬地、转髋、转体后再带动肩肘腕释放。",
    "击球点保持在身体前上方，避免击球点过后导致向前穿透不足。",
    "练习击球前后窗口的前臂旋前和腕部释放。"
  ],
  "evidence": [
    {
      "source_id": "CLEAR_ZHAO_LOWER_LIMB",
      "artifact_path": "rag_project/sources/raw/html/CLEAR_ZHAO_LOWER_LIMB.html",
      "evidence_type": "biomechanics_study",
      "claim": "后场正手高远球涉及下肢运动、足底压力和不同水平选手差异。",
      "support_level": "direct_for_lower_limb_indicators"
    }
  ]
}
```

## 5. 系统架构

第一版系统由四层组成。

### 5.1 文献与资料层

来源来自已下载目录：

- `rag_project/sources/raw/pdf`
- `rag_project/sources/raw/html`
- `rag_project/sources/raw/metadata/download_results.csv`
- `rag_project/sources/raw/metadata/acquisition_report.md`

每个 artifact 必须先分类：

- `official_manual`
- `full_text_pdf`
- `full_text_html`
- `abstract_or_metadata_only`
- `book_preview_or_product_page`

只有 `official_manual`、`full_text_pdf`、`full_text_html` 默认进入正文切块。`abstract_or_metadata_only` 和 `book_preview_or_product_page` 只进入参考书目索引，不作为动作机制证据。

### 5.2 正手高远球知识层

知识层记录正手高远球相关的研究与教学知识：

- 标准教学动作：握拍、准备、引拍、击球点、随挥、回位。
- 生物力学指标：躯干旋转、肩关节运动、肘伸展、腕部释放、下肢蹬转、重心转移。
- 专家与新手差异：来自正手高远球或上手击球专家-新手对比文献。
- 后果关联：球只高不远、球速慢、球路偏短、发力不连贯。
- 证据等级：官方规范、直接运动学/动力学研究、直接 EMG 研究、综述、机制推断。

### 5.3 时序诊断层

时序诊断层不依赖大模型直接判断，而是使用可解释规则：

1. 阶段对齐：按 `impact` 和动作阶段事件将时序归一化到固定阶段。
2. 特征提取：计算峰值、谷值、峰值时间、阶段均值、阶段积分、角速度、激活持续时间、近端到远端顺序。
3. 模板对比：将待评估动作与正确模板的均值和容许区间比较。
4. 后果约束：根据离散后果标签筛选最相关偏差。
5. 诊断排序：按偏差严重度、阶段重要性、后果相关性和证据等级排序。

### 5.4 RAG 解释层

RAG 不负责直接分类。RAG 的职责是：

- 根据诊断出的动作阶段、关节、肌肉和后果标签检索文献片段。
- 给出标准动作依据。
- 解释偏差为什么可能导致该后果。
- 区分直接证据和推断证据。
- 给出可追溯引用：`source_id`、文件路径、页码或段落定位。

## 6. 正确模板结构

每个正确模板包含：

```json
{
  "template_id": "forehand_clear_correct_v1",
  "action_type": "forehand_clear",
  "source": "simulation_correct_samples",
  "sample_count": 20,
  "normalization": {
    "time_basis": "impact_aligned_percent_phase",
    "muscle_activation_basis": "mvc_normalized"
  },
  "features": {
    "trunk_rotation_peak": {
      "phase": "acceleration",
      "mean": 42.0,
      "std": 5.0,
      "unit": "degree",
      "lower_bound": 32.0,
      "upper_bound": 52.0
    },
    "forearm_pronator_peak_time_relative_to_impact": {
      "phase": "impact_window",
      "mean": -0.03,
      "std": 0.02,
      "unit": "second",
      "lower_bound": -0.07,
      "upper_bound": 0.01
    }
  }
}
```

模板边界第一版使用均值加减两倍标准差。样本数不足 5 时不计算统计边界，只记录参考曲线并把诊断置信度降为 `low`。

## 7. 后果标签规则库

第一版支持正手高远球的三个离散后果标签。

### 7.1 `ball_high_not_far`

含义：球能飞高，但距离不够或前向穿透不足。

重点检查：

- 躯干旋转峰值不足或峰值过晚。
- 髋-躯干-肩-肘-腕顺序异常。
- 肩部或上肢肌肉激活过早，提示上肢代偿。
- 肘伸展、前臂旋前或腕部释放峰值低于模板。
- 击球窗口内向前发力相关指标不足。

诊断倾向：

- 躯干带动不足。
- 末端释放滞后。
- 发力方向偏上，向前动量不足。

### 7.2 `low_speed`

含义：球速慢，整体出球无力。

重点检查：

- 躯干旋转角速度不足。
- 肩内旋或肩水平内收相关指标不足。
- 肘伸展角速度不足。
- 前臂旋前或腕部释放峰值不足。
- 主要肌群激活峰值整体偏低或激活持续时间不足。

诊断倾向：

- 动力链总输出不足。
- 近端到远端传递效率低。
- 击球阶段力量释放不集中。

### 7.3 `uncoordinated_power`

含义：发力不连贯，动作有明显断点。

重点检查：

- 近端峰值与远端峰值顺序颠倒。
- 肌肉激活峰值明显提前或滞后。
- 躯干、肩、肘、腕角速度峰值时间分散。
- 击球前后窗口内末端释放未集中。

诊断倾向：

- 动作阶段衔接问题。
- 肌肉激活时序不稳定。
- 动力链释放顺序异常。

## 8. 偏差严重度

偏差严重度分为三档：

- `low`：超出模板边界，但偏差幅度小于模板标准差的 1 倍。
- `medium`：偏差幅度为模板标准差的 1 到 2 倍。
- `high`：偏差幅度超过模板标准差的 2 倍，或发生在击球窗口且与后果标签直接相关。

如果没有足够正确样本计算标准差，使用人工阈值时必须把 `threshold_source` 标为 `expert_defined_initial_threshold`。

## 9. 证据等级

RAG 解释必须给每条解释标证据等级：

- `official_instruction`：BWF、Shuttle Time 或正式教材中的动作规范。
- `direct_biomechanics_forehand_clear`：直接研究正手高远球的运动学、动力学或足底压力文献。
- `direct_emg`：直接测量相关动作或相近动作肌电的研究。
- `expert_novice_comparison`：专家与新手对比研究。
- `overhead_stroke_transfer`：上手击球、杀球、吊球等相近动作研究迁移。
- `mechanistic_inference`：由动力链和运动学机制推断，不声称为直接肌肉激活证据。

系统生成回答时，必须避免把 `mechanistic_inference` 写成确定性生理事实。

## 10. 第一版数据与文件规划

建议后续实现创建以下文件：

- `rag_project/diagnostics/schemas.py`：输入样本、模板、偏差、诊断结果的数据结构。
- `rag_project/diagnostics/phase_alignment.py`：动作阶段对齐和时间归一化。
- `rag_project/diagnostics/features.py`：关节角与肌肉激活特征提取。
- `rag_project/diagnostics/templates.py`：正确模板构建与读取。
- `rag_project/diagnostics/rules_forehand_clear.py`：正手高远球后果规则库。
- `rag_project/diagnostics/diagnose.py`：偏差检测、后果约束和诊断排序。
- `rag_project/knowledge/source_classifier.py`：artifact 分类。
- `rag_project/knowledge/extract_text.py`：PDF/HTML 正文抽取。
- `rag_project/knowledge/evidence_index.py`：文献 evidence schema 和检索索引。

## 11. 验收标准

第一版完成后，需要满足：

1. 能读取一个正手高远球待评估样本和一个正确模板。
2. 能按 `impact` 对齐并提取至少 20 个特征。
3. 能对 `ball_high_not_far`、`low_speed`、`uncoordinated_power` 三个后果标签生成诊断。
4. 每条诊断至少包含一个关节角偏差或肌肉激活偏差。
5. 每条改进建议都能关联一个动作机制或文献 evidence。
6. 报告必须区分直接 EMG 证据、运动学证据和机制推断。
7. 对 `metadata_only` 和 `book_preview_or_product_page` 来源不得生成强证据结论。

## 12. 第一版测试用例

### 测试用例 1：球只高不远

输入：

- 后果标签：`ball_high_not_far`
- 躯干旋转峰值低于模板。
- 前臂旋前峰值时间晚于击球后。
- 三角肌激活提前，核心相关激活不足。

期望输出：

- 主诊断包含“向前动量不足”或“末端释放效率偏低”。
- 关键偏差包含躯干旋转、前臂旋前和上肢代偿。
- 建议包含蹬转带动、击球点前上方和前臂/腕部释放。

### 测试用例 2：球速慢

输入：

- 后果标签：`low_speed`
- 躯干旋转角速度、肩内旋相关指标和肘伸展角速度均偏低。

期望输出：

- 主诊断包含“动力链总输出不足”。
- 关键偏差按躯干、肩、肘、腕阶段排序。
- 解释中不得声称没有直接测量的肌肉一定激活不足。

### 测试用例 3：发力不连贯

输入：

- 后果标签：`uncoordinated_power`
- 肩部峰值早于躯干峰值，腕部释放滞后于击球。

期望输出：

- 主诊断包含“近端到远端释放顺序异常”。
- 关键偏差包含峰值顺序颠倒和击球窗口释放滞后。

## 13. 实施顺序

第一阶段先实现数据层和诊断闭环：

1. artifact 分类。
2. 文献正文抽取。
3. 正手高远球样本 schema。
4. 正确模板构建。
5. 特征提取。
6. 三个后果标签规则。
7. 结构化诊断报告。

第二阶段再实现 RAG 检索和文献解释：

1. evidence chunk schema。
2. 正文切块。
3. 混合检索。
4. 诊断结果到 evidence query 的映射。
5. 带引用的中文解释生成。

第三阶段再考虑扩展：

1. 反手高远球。
2. 正手杀球。
3. 更多后果标签。
4. 基于历史样本的统计学习或排序模型。
