---
title: 羽毛球正手高远球分析 RAG 知识库构建文档
author: ChatGPT
lang: zh-CN
date: 2026-06-09
---

# 羽毛球正手高远球分析 RAG 知识库构建文档

**版本**：v1.1  
**日期**：2026-06-09  
**修订说明**：v1.1 经独立审计修订——(1) 修正上肢峰值时序表述（肩内旋 vs 肘伸展改为带不确定性的重叠区间，区分高远球直接证据与杀球/头顶类比）；(2) 区分"前臂旋前"与"腕屈"两个不同自由度，按来源原文如实表述；(3) 收紧"不考虑手指"边界，肌肉层排除手指外在肌；(4) 区分"模型诊断启发式阈值"与"生物力学定量真值"；(5) 行内类比标注（如 `[S11^smash]`）；(6) 新增 §8.2 来源标签→chunk 证据层映射、§9.1 文件名↔source_id 映射；(7) 文献元数据按 2026-06 联网核查修正（见 `badminton_forehand_clear_sources.csv` notes 与 `source_id_crosswalk.csv`）。  
**目标用途**：为“羽毛球正手高远球 / 后场正手高远球 / Forehand Overhead Clear / Backcourt Forehand Clear”构建一个可供 Codex、Claude 或其他工程代理实现的 RAG 知识库。知识库面向三类问题：

1. **动作技术分析**：高远球目的、阶段、关键动作、训练反馈。
2. **运动生物力学分析**：关节角、角速度、体段加速度、动力学、足底压力、近端到远端发力链。
3. **SMPL/肌骨模型/PPO mimic 策略验证**：如何从“看起来像”推进到“运动学、动力学、肌肉生理约束上合理”。

> **边界条件**：本文档按你的要求，**不重点讨论手和手指发力**。腕部只作为可选远端关节变量；手指屈伸、握拍压力、掌指/指间关节和精细抓握肌群不作为核心知识项。
>
> **肌肉层边界（重要）**：在"肌群"层面，只保留**纯腕动器**（桡侧腕屈肌 flexor carpi radialis、尺侧腕屈肌 flexor carpi ulnaris、桡侧腕长/短伸肌 extensor carpi radialis longus/brevis、尺侧腕伸肌 extensor carpi ulnaris）。**显式排除手指外在肌**：指浅屈肌（flexor digitorum superficialis）、指深屈肌（flexor digitorum profundus）、指总伸肌（extensor digitorum）、以及全部手内在肌（蚓状肌、骨间肌等）——这些虽位于前臂/手部并跨腕，但其主功能是驱动手指，属本库排除范围。chunk 的 `excluded_muscle_groups` 字段应显式登记上述被排除肌肉。若未来要加入球拍握把压力、手指发力或拍面微调，应单独建一个 `grip_hand_fingers` 子库。

---

## 1. 核心结论摘要

正手高远球不是“单靠手腕甩拍”的动作。更稳妥的生物力学描述是：**支撑脚蹬地与下肢稳定提供起始动量，髋/骨盆和躯干旋转完成近端能量传递，肩关节内旋、水平内收与肩胛稳定完成上肢主加速，肘伸展、（桡尺）前臂旋前与腕屈在击球瞬间高度重叠共同完成远端释放，击球后由肩袖、肱二头肌、躯干和下肢进行减速与恢复**。[S01][S05][S04^mixed][S08^mixed]

> 证据级别提示：上式中下肢、骨盆、躯干与阶段划分有高远球**直接证据**支持（[S01][S05][S06][S07]）；而**肩内旋、肘伸展、前臂旋前/腕屈的定量细节与相对先后**主要来自含杀球的头顶击球证据（[S04][S08]）与杀球类比（[S11^smash][S12^smash]），属"混合/类比"证据。**不要把它当作高远球已测定的唯一时序真值**（详见 §5.2 的重叠区间表述）。

在 RAG 中，必须把证据分为四类：

- **直接高远球证据**：例如 BWF/教学资料、clear strokes 论文、后场正手高远球下肢/IMU 研究。[S01][S02][S05][S06][S07]
- **正手头顶多击球证据**：同时包含 clear、smash、drop，可用于比较高远球与杀球/吊球的差异。[S08]
- **杀球/跳杀类比证据**：可用于近端到远端链、躯干旋转、肩内旋、前臂旋前、EMG/肌骨模型方法，但不能把杀球的定量峰值直接当高远球真值。[S11][S12][S13][S14][S17]
- **数据集和方法证据**：用于动作识别、体段传感器、EMG/MSK、RAG 实验评估，而不是直接给动作规范结论。[S16][S17]

最重要的 RAG 保护规则是：**动作轨迹拟合度高不能证明具体肌肉激活唯一正确**。肌骨模型存在力分配多解；RAG 应输出“当前模型与约束下的生理合理性证据”，而不是“真实肌肉激活真值”。[S17]

---

## 2. 术语、别名和检索词表

> 术语规范与英文文献对应可参考羽毛球生物力学综述《The Science of Badminton》进行交叉核对与文献定位。[S10^review]

### 2.1 中文术语

- 正手高远球
- 高远球
- 后场正手高远球
- 正手头顶高远球
- 进攻型高远球
- 防守型高远球
- 头顶正手击球
- 后场头顶击球

### 2.2 英文术语

- forehand clear
- forehand overhead clear
- backcourt forehand clear
- overhead forehand clear
- high clear
- attacking clear
- defensive clear
- overhead forehand stroke
- badminton clear stroke

### 2.3 RAG 查询扩展建议

当用户查询“高远球肌肉顺序”时，检索器应自动扩展为：

```text
正手高远球 OR 后场正手高远球 OR forehand overhead clear OR backcourt forehand clear
AND muscle OR EMG OR musculoskeletal model OR shoulder internal rotation OR forearm pronation
AND phase OR proximal-distal sequence OR kinetic chain
```

当用户查询“角度顺序/关节角顺序”时，检索器应自动扩展为：

```text
forehand overhead clear OR overhead forehand stroke
AND pelvis rotation OR trunk rotation OR shoulder internal rotation OR elbow extension OR forearm pronation
AND angular velocity OR joint angle OR segment acceleration
```

### 2.4 概念归一化表

| 用户说法 | 标准概念ID | 备注 |
|---|---|---|
| 高远球、正手高远、头顶高远 | `forehand_overhead_clear` | 主任务对象 |
| 后场正手高远球 | `backcourt_forehand_clear` | 与后场移动、支撑脚、下肢压力强相关 |
| 进攻高远 | `attacking_clear` | 通常轨迹较低、更快，目的是压迫对方身后 [S01] |
| 防守高远 | `defensive_clear` | 通常轨迹更高，目的是获得恢复时间 [S01][S02] |
| 鞭打链 | `proximal_distal_sequence` | 近端到远端：下肢/骨盆→躯干→肩→肘→前臂/腕 |
| 手腕发力 | `distal_release_misconception` | 应转写为前臂旋前、肩内旋、腕部末端控制；不要只归因于手腕 [S04] |
| 肌骨模型解 | `musculoskeletal_solution` | 必须标注多解/冗余限制 |

---

## 3. 高远球的目的、类型和动作阶段

### 3.1 技术目的

高远球的基本目标是把球从己方后场击到对方后场，使对手被迫后退。教学资料通常把高远球分为进攻型和防守型：**进攻型高远球**更低、更快，目标是让球越过对手可触及范围并落到其身后；**防守型高远球**更高，给自己更多回位和恢复时间。[S01][S02][S03]

RAG 回答时应避免把“clear”简单翻译为“挑高球”。在中文羽毛球语境中，“高远球”既有高且远的防守/过渡意图，也可能有较快较平的进攻高远意图。应根据上下文判断：

- 用户说“正手高远球”：默认 `forehand_overhead_clear`。
- 用户说“后场高远球”：优先 `backcourt_forehand_clear`。
- 用户说“进攻高远/防守高远”：分别检索 `attacking_clear` 与 `defensive_clear`。

### 3.2 动作阶段模型

建议把正手高远球分为六个阶段。这个阶段模型既适合技术分析，也适合 SMPL/肌骨模型日志切分。

| 阶段ID | 中文名称 | 英文名称 | 事件边界 | 关键观察 |
|---|---|---|---|---|
| P0 | 后场移动与选位 | movement to rear court | 从启动到后场站位成形 | 步法、重心、支撑脚落点、身体是否侧身 |
| P1 | 准备/侧身 | preparation | 到达击球位置并建立侧身姿态 | 非持拍臂上举、持拍肩后引、膝髋轻度加载 |
| P2 | 引拍与蓄力 | backswing/loading | 拍臂后引到前向加速开始 | 骨盆/躯干“关闭”、肩外旋、肘屈曲、身体反向旋转 |
| P3 | 前挥加速 | forward swing/acceleration | 骨盆/躯干启动到击球前 | 近端到远端：下肢→骨盆→躯干→肩→肘→前臂 |
| P4 | 击球 | impact/contact | 拍面接触羽毛球 | 击球点高且略在持拍肩前；肘伸展、肩内旋、前臂旋前/腕屈在击球瞬间高度重叠并接近各自峰值（相对先后见 §5.2，缺高远球直接测量时不给唯一顺序） |
| P5 | 随挥与恢复 | follow-through/recovery | 击球后到回位 | 肩/肘/躯干离心减速；后脚落地成为新的前脚；准备下一拍 |

BWF 教练资料把正手高远球的技术描述为：准备时采用基本握拍、拍在头上方准备、前臂上举、侧身；引拍时后腿向上向前驱动、后髋向前、后肩和肘向上向前、上臂/前臂外旋；前挥时上臂/前臂内旋，并在持拍肩上方略前的位置击球；随挥时球拍动量带动手臂内旋并放松。[S01]

---

## 4. 不考虑手和手指时的主要肌肉知识库

> 本节是“肌群级”知识，不应被 RAG 当作每块肌肉真实激活曲线。高远球直接 EMG 证据有限，许多肌肉时序来自头顶杀球或正手头顶击球类比，必须在输出中标注证据级别。[S13][S14][S15][S17]

### 4.1 下肢与骨盆：启动、稳定、蹬伸

| 肌群 | 主要功能 | 对高远球的意义 | RAG 标签 |
|---|---|---|---|
| 臀大肌 | 髋伸展、骨盆控制 | 支撑腿蹬伸和骨盆打开；防止只靠上肢抡拍 | `gluteus_maximus`, `hip_extension` |
| 臀中肌/小肌 | 骨盆侧向稳定、髋外展 | 控制单脚/交叉步支撑时骨盆塌陷 | `gluteus_medius`, `pelvic_stability` |
| 股四头肌 | 膝伸展 | 下肢加载后蹬伸，支撑身体上移和转体 | `quadriceps`, `knee_extension` |
| 腘绳肌 | 髋伸展、膝稳定 | 与臀肌共同参与髋伸展，控制膝关节稳定 | `hamstrings`, `hip_extension`, `knee_stability` |
| 腓肠肌/比目鱼肌 | 踝跖屈 | 蹬地末端发力、支撑脚推出 | `gastrocnemius`, `soleus`, `ankle_plantarflexion` |
| 胫骨前肌/腓骨肌群 | 踝稳定、足部控制 | 控制落地、足底压力和踝内外翻 | `ankle_stability`, `foot_pressure` |
| 髋内收/外旋/内旋肌群 | 骨盆旋转与重心控制 | 帮助“侧身—打开”的髋/骨盆转换 | `hip_rotation`, `pelvis_yaw` |

直接下肢证据应优先检索后场正手高远球研究。[S06][S07] Zhao 与 Li 直接研究了后场正手高远球的下肢运动学和足底压力，适合用于支撑脚、前足压力、踝关节控制等验证。[S06] Huang 等使用足、小腿、大腿、髋、肩、上臂、前臂等多体段 IMU 数据比较新手与有经验者，适合用于体段加速度和稳定性评价。[S07]

### 4.2 躯干与核心：能量传递和姿态控制

| 肌群 | 主要功能 | 对高远球的意义 | RAG 标签 |
|---|---|---|---|
| 腹外斜肌/腹内斜肌 | 躯干轴向旋转 | 近端到远端链的核心环节；骨盆启动后带动胸廓和肩带 | `obliques`, `trunk_rotation` |
| 腹直肌 | 躯干前屈、核心收紧 | 击球阶段从后伸/反向旋转过渡到前屈/正向旋转 | `rectus_abdominis`, `trunk_flexion` |
| 竖脊肌/多裂肌 | 躯干伸展、抗旋转、减速 | 引拍保持躯干后伸；击球后控制随挥与回位 | `erector_spinae`, `multifidus`, `deceleration` |
| 背阔肌 | 肩内收/内旋、躯干—上肢连接 | 连接躯干与上肢，参与肩关节加速与随挥 | `latissimus_dorsi`, `shoulder_adduction_internal_rotation` |

躯干不是可有可无的装饰动作。技能等级研究显示，成熟的头顶正手动作更强调躯干动作，X-factor/躯干旋转研究也提示躯干旋转与近端到远端鞭打链有关。[S09^overhead][S11^smash]（S09 为头顶正手通用、非高远球专项；S11 为杀球类比）对高远球 RAG 来说，躯干应被视为**能量传递与时序判断变量**，而不是只看上肢末端轨迹。

### 4.3 肩胛与肩关节：上肢主加速平台

| 肌群 | 主要功能 | 对高远球的意义 | RAG 标签 |
|---|---|---|---|
| 胸大肌 | 肩水平内收、肩内旋 | 挥拍前向加速的重要肌群 | `pectoralis_major`, `shoulder_horizontal_adduction`, `shoulder_internal_rotation` |
| 背阔肌/大圆肌 | 肩内收、肩内旋 | 配合胸大肌与肩胛稳定完成加速 | `latissimus_dorsi`, `teres_major` |
| 三角肌前束 | 肩屈曲、肩水平内收 | 在头顶高外展位主要贡献**肩水平内收/上臂前向带入**（横/水平面），而非纯矢状面肩屈曲；后者对拍头线速度贡献有限 | `anterior_deltoid`, `shoulder_horizontal_adduction` |
| 三角肌中束 | 肩外展 | 维持头顶击球所需上臂高度 | `middle_deltoid`, `shoulder_abduction` |
| 三角肌后束 | 肩伸展/水平外展、减速 | 击球后制动和回收 | `posterior_deltoid`, `deceleration` |
| 肩胛下肌 | 肩内旋 | 肩内旋主力之一 | `subscapularis`, `rotator_cuff_internal_rotation` |
| 冈下肌/小圆肌 | 肩外旋、离心制动 | 引拍外旋控制与击球后减速 | `infraspinatus`, `teres_minor`, `eccentric_deceleration` |
| 冈上肌 | 肩外展起始、关节稳定 | 肩袖稳定 | `supraspinatus`, `glenohumeral_stability` |
| 前锯肌/斜方肌 | 肩胛上旋、前伸、后缩与稳定 | 提供稳定肩胛平台，避免“肩关节孤立甩动” | `serratus_anterior`, `trapezius`, `scapular_upward_rotation` |

Tsai 等在正手头顶杀球、高远球和吊球对比中报告，肩内旋角速度是重要上肢变量之一。[S08] Waddell 与 Gowitzke 对头顶力量击球的综述也强调肩旋转与前臂旋前/旋后对球速的重要性。[S04] 因此，对于肌骨模型验证，肩内旋、肩水平内收、肩胛稳定和击球后离心减速是比“手腕动作像不像”更高优先级的指标。

### 4.4 肘与前臂：远端释放，但不纳入手指抓握

| 肌群 | 主要功能 | 对高远球的意义 | RAG 标签 |
|---|---|---|---|
| 肱三头肌 | 肘伸展 | 击球前远端加速，配合肩内旋和前臂旋前 | `triceps_brachii`, `elbow_extension` |
| 肱二头肌/肱肌 | 肘屈曲、离心制动 | 引拍维持屈肘，击球后控制肘伸过快 | `biceps_brachii`, `brachialis`, `elbow_deceleration` |
| 旋前圆肌/旋前方肌 | 前臂旋前 | 正手击球远端释放和拍面方向控制；属于前臂，不是手指发力 | `pronator_teres`, `pronator_quadratus`, `forearm_pronation` |
| 纯腕动器（桡/尺侧腕屈肌、桡/尺侧腕伸肌） | 腕关节稳定、掌屈/背伸、尺偏/桡偏 | 在本库中作为可选远端 DOF；**仅限纯腕肌**，显式排除指浅/指深屈肌、指总伸肌等手指外在肌（见 §0 边界） | `flexor_carpi_radialis`, `flexor_carpi_ulnaris`, `extensor_carpi_radialis`, `extensor_carpi_ulnaris`, `wrist_optional`, `distal_stabilization` |

高远球 RAG 回答应把“手腕发力”转写为更专业的远端机制：**肘伸展 +（桡尺）前臂旋前 + 腕屈/尺偏**，三者在击球瞬间高度重叠共同完成远端释放。Waddell 与 Gowitzke 特别强调前臂旋前/旋后，认为不能把羽毛球力量击球简化为“wrist snap”。[S04^mixed]

> 区分两个不同自由度：**前臂旋前（forearm pronation，桡尺关节）**与**腕屈（wrist flexion，腕关节）**是不同动作，不能互换。头顶击打研究普遍提示肩内旋是拍头速度的主要贡献者、前臂旋前次之（**具体贡献比例因研究而异**，不应把某篇杀球研究的定量拆分直接当高远球真值）；而杀球运动学序列研究 [S12^smash] 报告的**远端终末事件是腕屈**。因此远端释放应同时记录旋前与腕屈，**不要把"前臂旋前"单列为唯一终末段**，也不要以旋前替换 S12 原文的"腕屈"结论。

---

## 5. 主要关节角、角速度和顺序

### 5.1 关节角变量优先级

| 区域 | 关节角/自由度 | 推荐优先级 | 用途 |
|---|---|---:|---|
| 踝 | 背屈/跖屈 | 高 | 下肢加载、蹬地末端释放 |
| 踝 | 内翻/外翻、内外旋 | 中 | 落地和足底压力/踝稳定，特别是后场支撑 |
| 膝 | 屈曲/伸展 | 高 | 下肢加载和蹬伸 |
| 髋 | 屈曲/伸展 | 高 | 支撑腿发力、骨盆启动 |
| 髋 | 内旋/外旋 | 高 | 髋带动骨盆打开 |
| 髋 | 外展/内收 | 中 | 骨盆稳定、重心控制 |
| 骨盆 | yaw 轴旋转 | 高 | “侧身—打开”的核心变量 |
| 骨盆 | 前倾/后倾 | 中 | 躯干—下肢协同 |
| 躯干 | 轴向旋转 | 高 | 能量传递与近端到远端链 |
| 躯干 | 屈曲/伸展 | 高 | 引拍蓄力到击球释放 |
| 躯干 | 侧屈 | 中 | 击球点调整和平衡 |
| 肩胛 | 上旋/前伸/后缩 | 中/高 | 若模型支持，评估肩带平台 |
| 肩 | 外展/内收 | 高 | 头顶击球高度与姿态 |
| 肩 | 屈曲/伸展 | 中 | 主要为姿态/引拍与上臂挥动轨迹，非头顶击球加速主变量（主加速看水平内收与内旋） |
| 肩 | 水平外展/水平内收 | 高 | 前挥加速 |
| 肩 | 外旋/内旋 | 高 | 上肢主加速核心变量 |
| 肘 | 屈曲/伸展 | 高 | 远端释放 |
| 前臂 | 旋后/旋前 | 高 | 拍面释放和前臂远端加速 |
| 腕 | 掌屈/背伸、尺偏/桡偏 | 可选 | 不考虑手指时可作为末端稳定变量 |

### 5.2 推荐的关节角速度峰值顺序

正手高远球的关节顺序不是完全串行，而是重叠的链式传递。RAG 回答应使用“峰值时序”而不是“某关节动完下一个才动”的说法。

**近端段（有较强共识，可作推荐顺序）**：

```text
支撑脚接触/加载
→ 踝跖屈、膝伸展、髋伸展/旋转
→ 骨盆 yaw 旋转速度峰值
→ 躯干轴向旋转速度峰值
→ 〔上肢远端段，见下方重叠区间〕
→ 击球后肩、肘、躯干和下肢离心减速
```

**上肢远端段（峰值高度重叠；命名/启动顺序 ≠ 峰值时序；缺高远球直测，不给唯一串行顺序）**：

> 肩内旋、肘伸展、前臂旋前/腕屈的速度峰值都集中在击球前后的极短窗口内、彼此高度重叠。这里必须区分两个**不同的变量**，不要混为一谈：
>
> - **链条命名/启动顺序（proximal→distal naming）**：因肩比肘更近端，描述发力链时常按"肩内旋 → 肘伸展 → 前臂旋前/腕屈"列举（羽毛球杀球序列研究即按此列举）[S12^smash]。这是关节的近端到远端**命名/启动**次序，**不等于各关节的峰值角速度时刻**。
> - **峰值角速度时刻（peak-velocity timing）**：跨领域的头顶击打证据（网球发球、投掷，以及羽毛球杀球）较一致地提示**肩内旋的峰值偏晚——约在肘伸展峰值之后、接近触球瞬间，且常是最快的远端贡献者**；S12 自报的远端**终末峰值事件是腕屈**[S12^smash]，与"肩内旋并非更早达峰"自洽。
>
> 因此本库的处理是：**不要把命名顺序当成峰值顺序**，尤其**不要断言"肩内旋先于肘伸展达峰"**（这是 v1.0 的错误）。若 mimic 验证需要一个先验，可弱采用"肩内旋峰值偏晚（约在肘伸展之后）"，但须注明这是**头顶/投掷 + 杀球类比的弱证据**、且**缺高远球直接 3D 上肢时序测量**。RAG 应按 §6.1 **相对击球时刻**报告各关节峰值时间，由数据/个体参考建立分位区间，**不给固定毫秒顺序**。

高远球和杀球都属于头顶正手击球，近端到远端链具有共性；但杀球通常更强调下压和最大速度，高远球更强调击球高度、出球角度、后场落点和恢复时间。因此，RAG 必须把来自杀球的 trunk→shoulder→elbow→wrist 序列标注为 `smash_analogy`，把来自网球发球/投掷的顺序标注为 `overhead/throwing analogy`，二者都**不能替代高远球直接测量**。[S11^smash][S12^smash]

### 5.3 与不同技能水平相关的运动学特征

可供 RAG 使用的技能分析要点：

- 高水平或有经验者通常表现出更成熟的躯干参与和上肢动作组织。[S09^overhead]（S09 为头顶正手通用、非高远球专项，作动作成熟度参考）
- 直接后场正手高远球 IMU 研究显示，新手和有经验球员在足、小腿、大腿、髋、肩、上臂、前臂的加速度幅值和稳定性上存在差异；有经验球员更强调稳定、有效的能量传递，而不是下肢和躯干无效波动。[S07]
- 高远球的“好动作”不能只看末端轨迹相似，还要看支撑脚、骨盆、躯干、肩肘前臂的时序是否合理。[S05][S07]

---

## 6. 动力学、接触与肌骨模型验证指标

本节面向你的 SMPL/肌骨模型/PPO mimic 工作。RAG 回答不应只说“轨迹拟合度高”，而应提供多层验证框架。

### 6.1 运动学指标

| 指标 | 计算对象 | 用途 | 注意事项 |
|---|---|---|---|
| MPJPE / 关节点位置误差 | 全身或上肢/下肢分区 | 判断动作轨迹拟合 | 不能证明动力学和肌肉正确 |
| 关节角 RMSE | 踝、膝、髋、骨盆、躯干、肩、肘、前臂 | 判断关键 DOF 是否贴近参考 | 注意角度定义和坐标系一致 |
| 角速度峰值时间 | 骨盆、躯干、肩、肘、前臂 | 判断近端到远端时序 | 建议相对击球时刻归一化 |
| 末端/拍头速度 | 手腕、球拍或代理点 | 判断击球前加速是否合理 | 没有球拍模型时只能近似 |
| 击球点高度和位置 | 手腕/拍头/球 | 判断是否在高处、略在持拍肩前 | 需要定义 contact event |
| COM 轨迹 | 全身重心 | 判断是否存在不自然跳变 | 与接触力一起看 |

### 6.2 接触和地面反作用力指标

| 指标 | 用途 | 对模型的意义 |
|---|---|---|
| 支撑脚接触时序 | 判断后场加载、蹬地、落地恢复 | 防止模型靠非物理 root force 完成挥拍 |
| 足底滑移 | 检查脚是否在接触期间滑动 | 足滑大说明物理不可信 |
| GRF 垂直/水平分量 | 验证蹬地和重心转移 | 可与力板/文献/估计模型对比 |
| CoP / 足底压力分布 | 验证前足支撑、踝控制 | Zhao & Li 的后场正手高远球下肢/足底压力研究可作参考 [S06] |
| 落地冲击与稳定 | 随挥后回位 | 防止动作结束阶段不稳定 |

如果当前系统只有视频，没有力板或真实外力，RAG 应建议至少报告：足底滑移、接触切换、root residual、重心连续性和关节力矩异常峰值。未来可加入 BadmintonGRF 类预印本/数据集作为视频到 GRF 的扩展，但应标注预印本状态。[S21]

### 6.3 关节力矩、功率和能量传递

建议记录：

- 踝、膝、髋、腰/胸、肩、肘、前臂/腕的净关节力矩。
- 关节功率：`power = torque × angular_velocity`。
- 近端到远端功率峰值顺序：髋/骨盆、躯干、肩、肘、前臂。注意 `power = torque × angular_velocity`，**功率峰值时序与角速度峰值时序不必一致**（近端段力矩大、远端段角速度大），应分别报告；上肢远端段的肩-肘相对先后沿用 §5.2 的"重叠/不确定"处理，不给唯一串行顺序。
- 是否存在异常尖峰：例如肩关节力矩远高于相邻帧，或依赖 root residual。
- 下肢功率是否能解释上肢末端速度的一部分，而不是上肢孤立发力。

RAG 回答应强调：逆动力学得到的是**净关节力矩**，并不能唯一决定每块肌肉激活。肌骨模型中的肌肉分配还取决于优化目标、肌腱模型、被动弹性、接触力和约束。[S17]

### 6.4 肌肉激活合理性指标

| 指标 | 计算方式 | 解释 |
|---|---|---|
| 激活饱和比例 | 每块肌肉 `a_i > 0.95` 的时间比例 | 大量长期饱和可能是“暴力解” |
| 总努力 | `mean(sum(a_i))` 或 `mean(sum(a_i^2))` | 防止高能耗解 |
| 平滑性 | `mean(∥a_t - a_(t-1)∥)` 或频谱高频能量 | 人体激活不应高频抖动 |
| 拮抗共同收缩 | 例如肱二头肌-肱三头肌、股四头肌-腘绳肌 | 过高会造成异常关节负荷 |
| 肌腱长度/速度范围 | 肌肉-肌腱长度、收缩速度 | 检查是否长期处于极端区间 |
| 肌群时序 | 下肢/躯干/肩/肘/前臂激活峰值 | 只能证明合理性，不能证明唯一真值 |
| 肌肉协同 | NMF synergy、VAF、协同时间权重 | 可借鉴 EMG+MSK 协同研究思路 [S17^msk] |

> **诊断阈值 ≠ 生物力学真值（重要）**：本节给出的具体数值（如激活饱和 `a_i > 0.95` 的比例、平滑性范数、共同收缩"过高"等）是**模型/工程诊断启发式（heuristic）**，用于在你自己的仿真数据上筛查"暴力解/不自然解"，**不是来自文献的生理定量真值**。使用时应：(1) 按你自己的数据集分布**分位标定**这些阈值，而非照搬 0.95 等魔数；(2) 在输出中标注其为"诊断性启发式结论"。这与 §10.3 "不输出无来源的精确角度/毫秒真值" 并不矛盾——前者是可给但需标注的诊断阈值，后者是不可凭空给出的生物力学真值，二者必须区分。

### 6.5 扰动鲁棒性指标

一个只会“背轨迹”的策略，可能在轻微扰动下崩溃。建议 RAG 中加入如下验证问题：

1. 初始姿态扰动：骨盆 yaw、躯干角、肩外旋初值扰动后能否恢复。
2. 接触扰动：地面摩擦系数、支撑脚接触点、脚底高度微扰。
3. 身体参数扰动：质量、肢段长度、关节阻尼、肌肉最大等长力小范围变化。
4. 目标扰动：击球点时间提前/推迟、轨迹缩放、出球方向微调。
5. 动作泛化：不同球员、不同速度、进攻/防守高远之间的迁移。

---

## 7. 阶段—肌肉—关节—指标映射表

| 阶段 | 关键动作 | 主要肌群（不含手指） | 主要关节角/速度 | 推荐验证指标 | 主要证据 |
|---|---|---|---|---|---|
| P0 后场移动 | 移动到后场、建立支撑 | 臀中肌、股四头肌、腘绳肌、踝稳定肌 | 髋/膝/踝、骨盆位置 | 步法、接触、COM、足滑 | [S01][S06][S07] |
| P1 准备/侧身 | 侧身、非持拍臂上举、持拍臂后引 | 竖脊肌、斜肌、三角肌、肩袖、肱二头肌 | 躯干反向旋转/后伸、肩外展/外旋、肘屈曲 | 侧身角、肩外旋角、肘屈曲角 | [S01][S02][S03] |
| P2 蓄力 | 后腿加载、骨盆关闭、肩肘准备 | 臀大肌、股四头肌、腓肠肌、斜肌、肩袖 | 膝/髋屈伸、骨盆 yaw、躯干旋转 | 下肢加载、骨盆-胸廓分离 | [S05][S06][S11] |
| P3 前挥加速 | 下肢蹬伸、骨盆打开、躯干带肩、上肢加速 | 臀大肌、股四头肌、腓肠肌、斜肌、胸大肌、背阔肌、三角肌前束、肩胛下肌、肱三头肌、旋前肌 | 踝跖屈、膝伸、髋伸/旋转、骨盆 yaw、躯干旋转、肩内旋/水平内收、肘伸、前臂旋前/腕屈（远端段重叠，§5.2） | 角速度峰值顺序、功率峰值、末端速度 | [S05][S07] · [S04^m][S08^m] · [S12^s] |
| P4 击球 | 高点击球，略在持拍肩前 | 肩内旋肌群、肱三头肌、旋前肌、肩袖稳定 | 肩内旋、肘伸展、前臂旋前/腕屈在击球瞬间重叠近峰（§5.2） | 击球点高度、末端速度、出球角度 | [S01][S03] · [S04^m][S08^m] |
| P5 随挥恢复 | 手臂内旋随挥、后脚落地、回位 | 冈下肌、小圆肌、三角肌后束、肱二头肌、竖脊肌、下肢稳定肌 | 肩/肘/躯干减速，步法恢复 | 离心减速、关节负荷、落地稳定 | [S01] · [S14^s] · [S18^inj] |

> 证据类型图例（与 §8.3 一致）：无标记=高远球直接证据；`^m`=含杀球的头顶 power strokes / 混合证据（S04/S08）；`^s`/`^smash`=杀球类比（smash_analogy，S11–S15）；`^inj`=伤病/安全背景（S18，不用于定义技术动作）。注：`[S14^s]` 为杀球/吊球上肢 EMG，其原始记录侧重腕/前臂肌且属类比，**不向手指外在肌延伸**；若"离心减速"需更稳的支撑，优先用 S04/S08。

---

## 8. 文献与资料索引

本表中的“浏览地址”和“下载/DOI”在 DOCX 中显示为可点击链接；原始 URL 同时保存在 `badminton_forehand_clear_sources.csv`。RAG 构建时请把 `source_id` 固定为稳定主键，不要用标题字符串作为主键。

| ID | 年份 | 文献/资料 | RAG证据标签 | 浏览地址 | 下载/DOI |
|---|---:|---|---|---|---|
| S01 | n.d. | BWF Coach Education Level 1 Manual / Badminton Coaches Manual | official_coaching_direct_clear | [浏览](https://www.badminton-israel.co.il/wp-content/uploads/2022/11/Badminton-Coaches-Manual.pdf) | [下载/DOI](https://www.badminton-israel.co.il/wp-content/uploads/2022/11/Badminton-Coaches-Manual.pdf) |
| S02 | n.d. | Forehand & Backhand Clear | teaching_direct_clear | [浏览](https://raider.pressbooks.pub/badminton/chapter/forehand-backhand-clear/) | [下载/DOI](https://raider.pressbooks.pub/badminton/chapter/forehand-backhand-clear/) |
| S03 | n.d. | How to Hit a Forehand Overhead Clear | teaching_direct_clear | [浏览](https://www.sikana.tv/en/sport/badminton/how-to-hit-a-forehand-overhead-clear) | [下载/DOI](https://www.sikana.tv/en/sport/badminton/how-to-hit-a-forehand-overhead-clear) |
| S04 | 2000 | Biomechanical Principles Applied to Badminton Power Strokes | biomechanics_overhead_power_strokes | [浏览](https://ojs.ub.uni-konstanz.de/cpa/article/view/2233) | [下载/DOI](https://ojs.ub.uni-konstanz.de/cpa/article/download/2233/2089/) |
| S05 | 2010/2011 | A Biomechanical Analysis of Clear Strokes in Badminton Executed by Youth Players of Different Skill Levels | peer_reviewed_direct_clear | [浏览](https://vbn.aau.dk/en/publications/a-biomechanical-analysis-of-clear-strokes-in-badminton-executed-b/) | [下载/DOI](https://projekter.aau.dk/projekter/files/42678547/articledone.pdf) |
| S06 | 2019 | A Biomechanical Analysis of Lower Limb Movement on the Backcourt Forehand Clear Stroke among Badminton Players of Different Levels | peer_reviewed_direct_clear_lower_limb | [浏览](https://onlinelibrary.wiley.com/doi/abs/10.1155/2019/7048345) | [下载/DOI](https://pmc.ncbi.nlm.nih.gov/articles/PMC6348812/) |
| S07 | 2025 | Differences in backcourt forehand clear stroke between novice players and experienced badminton players: based on body segment acceleration data | peer_reviewed_direct_clear_IMU | [浏览](https://link.springer.com/article/10.1186/s13102-025-01163-w) | [下载/DOI](https://link.springer.com/content/pdf/10.1186/s13102-025-01163-w.pdf) |
| S08 | 2008 | Biomechanical Analysis of Different Badminton Forehand Overhead Strokes of Taiwan Elite Female Players | peer_reviewed_overhead_forehand_multi_stroke | [浏览](https://ojs.ub.uni-konstanz.de/cpa/article/view/1997) | [下载/DOI](https://ojs.ub.uni-konstanz.de/cpa/article/download/1997/1865/0) |
| S09 | 2009 | Steps for Arm and Trunk Actions of Overhead Forehand Stroke Used in Badminton Games across Skill Levels | skill_level_overhead_forehand | [浏览](https://pubmed.ncbi.nlm.nih.gov/19831099/) | [下载/DOI](https://journals.sagepub.com/doi/abs/10.2466/PMS.109.1.177-186) |
| S10 | 2015 | The Science of Badminton: Game Characteristics, Anthropometry, Physiology, Visual Fitness and Biomechanics | badminton_biomechanics_review | [浏览](https://pubmed.ncbi.nlm.nih.gov/25549780/) | [下载/DOI](https://www.worldbadminton.com/reference/research/documents/The_Science_of_Badminton_Game.pdf) |
| S11 | 2016 | The Influence of X-Factor (Trunk Rotation) and Experience on the Quality of the Badminton Forehand Smash | smash_analogy_trunk_rotation | [浏览](https://pmc.ncbi.nlm.nih.gov/articles/PMC5260572/) | [下载/DOI](https://opus.uleth.ca/items/2bcecf18-5b66-4c29-8e03-c53755aa56fb) |
| S12 | 2023 | Biomechanical Insights for Developing Evidence-Based Training Programs: Unveiling the Kinematic Secrets of the Overhead Forehand Smash in Badminton through Novice-Skilled Player Comparison | smash_analogy_kinematic_sequence | [浏览](https://www.mdpi.com/2076-3417/13/22/12488) | [下载/DOI](https://www.mdpi.com/2076-3417/13/22/12488/pdf) |
| S13 | 2005/2008 | The Surface EMG Activity Analysis between Badminton Smash and Jump Smash | EMG_smash_analogy | [浏览](https://ojs.ub.uni-konstanz.de/cpa/article/view/1095) | [下载/DOI](https://ojs.ub.uni-konstanz.de/cpa/article/view/1095) |
| S14 | 2005 | Biomechanical Analysis of EMG Activity Between Badminton Smash and Drop Shot | EMG_smash_drop_analogy | [浏览](https://isbweb.org/images/conf/2005/abstracts/0439.pdf) | [下载/DOI](https://isbweb.org/images/conf/2005/abstracts/0439.pdf) |
| S15 | 2000 | Muscle activity and accuracy of performance of the smash stroke in badminton with reference to skill and practice | EMG_smash_analogy_skill | [浏览](https://pubmed.ncbi.nlm.nih.gov/11144867/) | [下载/DOI](https://doi.org/10.1080/026404100750017832) |
| S16 | 2024 | MultiSenseBadminton: Wearable Sensor-Based Biomechanical Dataset for Evaluation of Badminton Performance | dataset_forehand_clear | [浏览](https://www.nature.com/articles/s41597-024-03144-z) | [下载/DOI](https://springernature.figshare.com/collections/MultiSenseBadminton_Wearable_Sensor_Based_Biomechanical_Dataset_for_Evaluation_of_Badminton_Performance/6725706) |
| S17 | 2025 | Muscle synergy analysis during badminton forehand overhead smash: integrating electromyography and musculoskeletal modeling | MSK_EMG_smash_analogy | [浏览](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2025.1596670/full) | [下载/DOI](https://doi.org/10.3389/fspor.2025.1596670) |
| S18 | 2020 | Badminton Injuries in Elite Athletes: A Review of Epidemiology and Biomechanics | injury_review_badminton | [浏览](https://pmc.ncbi.nlm.nih.gov/articles/PMC7205924/) | [下载/DOI](https://pmc.ncbi.nlm.nih.gov/articles/PMC7205924/) |
| S19 | 2022 | Risk Factors for, and Prediction of, Shoulder Pain in Young Badminton Players: A Prospective Cohort Study | shoulder_risk_badminton | [浏览](https://www.mdpi.com/1660-4601/19/20/13095) | [下载/DOI](https://www.mdpi.com/1660-4601/19/20/13095/pdf) |
| S20 | 2021 | Shoulder rotational strength profiles of Danish national level badminton players | shoulder_strength_badminton | [浏览](https://ijspt.scholasticahq.com/article/21531-shoulder-rotational-strength-profiles-of-danish-national-level-badminton-players) | [下载/DOI](https://ijspt.scholasticahq.com/article/21531-shoulder-rotational-strength-profiles-of-danish-national-level-badminton-players/attachment/54619.pdf) |
| S21 | 2026 | BadmintonGRF: A Multimodal Dataset and Benchmark for Markerless Ground Reaction Force Estimation in Badminton | preprint_dataset_GRF | [浏览](https://arxiv.org/abs/2605.01876) | [下载/DOI](https://arxiv.org/pdf/2605.01876) |

### 8.1 文献使用优先级

1. **优先级 A：直接高远球证据**  
   `[S01][S02][S03][S05][S06][S07]`。用于回答“高远球是什么、怎么做、下肢/体段加速度/技能差异如何”。

2. **优先级 A-/混合：含杀球的头顶 power strokes**  
   `[S04]`。Waddell & Gowitzke 的 power strokes 综述同时涵盖高远球与杀球，可支撑"远端释放靠肩旋转+前臂旋前而非单纯手腕"的**机制**，但**不提供高远球的定量真值**；引用时按混合证据（`^m`）处理，介于 A 与 C 之间。

3. **优先级 B：正手头顶多击球证据**  
   `[S08]`。用于回答高远球与杀球/吊球的运动学差异，尤其是肩内旋、击球初速度、COM 等变量。其结论多为三类头顶击球对比，行内按 `^m` 标注。

4. **优先级 C：头顶杀球类比证据**  
   `[S11][S12][S13][S14][S15][S17]`。用于解释近端到远端链、躯干旋转、EMG/MSK 方法、肌肉协同。输出时必须说明“该证据来自杀球/跳杀，不能直接当作高远球定量真值”。其中 **S17 主归 C（杀球类比机制）**，在 D 中仅作方法学复用。

5. **优先级 D：数据集和方法证据**  
   `[S16][S21]`（方法学上亦含 `S17`）。用于 RAG 实验、传感器数据、动作识别、肌骨模型验证。S21 是预印本，应默认低于已发表同行评审文献。

6. **优先级 E：伤病/安全背景**  
   `[S18][S19][S20]`。用于解释肩肘踝负荷、肩内外旋活动范围和强度平衡，不用于定义高远球技术动作。

7. **优先级 F：综述/文献导航**  
   `[S10]`。Phomsoupha & Laffaye《The Science of Badminton》综述，用于术语规范与文献定位（见 §2 术语表），不替代具体高远球研究、不作为定量真值。

### 8.2 来源标签 → chunk 证据层映射

`sources.csv` 的 `evidence_level` 是**来源级细粒度标签**（每篇一种）；而 chunk 的 `evidence_level` 是一套**粗粒度证据层**（`rag_chunk.schema.json` 的枚举），二者**不是同一词表**。下表把每个来源映射到 chunk 证据层与 §8.1 优先级，供切分脚本给 chunk 赋 `evidence_level` 时使用（也对应 `source.evidence_layer` 字段）。

| source | source.evidence_level（细） | → chunk.evidence_level（粗） | §8.1 优先级 |
|---|---|---|---|
| S01 | official_coaching_direct_clear | `coaching_direct_clear` | A |
| S02 | teaching_direct_clear | `coaching_direct_clear` | A |
| S03 | teaching_direct_clear | `coaching_direct_clear` | A |
| S04 | biomechanics_overhead_power_strokes | `mixed_direct_and_analogy` | A-/混合 |
| S05 | peer_reviewed_direct_clear | `peer_reviewed_direct_clear` | A |
| S06 | peer_reviewed_direct_clear_lower_limb | `peer_reviewed_direct_clear` | A |
| S07 | peer_reviewed_direct_clear_IMU | `peer_reviewed_direct_clear` | A |
| S08 | peer_reviewed_overhead_forehand_multi_stroke | `overhead_multi_stroke` | B |
| S09 | skill_level_overhead_forehand | `skill_level_overhead` | （头顶通用）|
| S10 | badminton_biomechanics_review | `review` | F |
| S11 | smash_analogy_trunk_rotation | `smash_analogy` | C |
| S12 | smash_analogy_kinematic_sequence | `smash_analogy` | C |
| S13 | EMG_smash_analogy | `emg_smash_analogy` | C |
| S14 | EMG_smash_drop_analogy | `emg_smash_analogy` | C |
| S15 | EMG_smash_analogy_skill | `emg_smash_analogy` | C |
| S16 | dataset_forehand_clear | `dataset` | D |
| S17 | MSK_EMG_smash_analogy | `msk_methodological`（主归 C 的类比机制，D 作方法学）| C/D |
| S18 | injury_review_badminton | `injury_review` | E |
| S19 | shoulder_risk_badminton | `injury_review` | E |
| S20 | shoulder_strength_badminton | `injury_review` | E |
| S21 | preprint_dataset_GRF | `dataset` | D（预印本，降权）|

### 8.3 行内类比标注规范

为让"直接 vs 类比"的边界在 chunk 级检索后**仍然存活**，正文与 chunk `text` 中的引用应在类比来源上加后缀标记：

- 无标记 = 高远球直接证据（A）。
- `[Sxx^m]` = 含杀球的头顶/混合证据（S04、S08）。
- `[Sxx^smash]` 或 `[Sxx^s]` = 杀球类比（S11–S15）。
- `[Sxx^msk]` = EMG+肌骨方法学（S17）。
- `[Sxx^overhead]` = 头顶正手通用、非高远球专项（S09）。
- `[Sxx^review]` = 综述/导航（S10）。
- `[Sxx^inj]` = 伤病/安全背景（S18–S20）。

---

## 9. RAG 知识库结构设计

### 9.1 推荐目录结构

```text
badminton-clear-rag/
  README.md
  corpus/
    00_source_catalog.csv                         # = badminton_forehand_clear_sources.csv
    source_id_crosswalk.csv                        # S01-S21 ↔ rag_project legacy id
    01_coaching/
      bwf_forehand_clear.md                        # S01
      uga_forehand_clear.md                        # S02
      sikana_forehand_overhead_clear.md            # S03
    02_biomechanics_direct_clear/
      sorensen_clear_strokes.md                    # S05
      zhao_lower_limb_backcourt_clear.md           # S06
      huang_body_segment_acceleration_clear.md     # S07
    03_biomechanics_overhead_analog/
      waddell_power_strokes.md                     # S04 (^m 混合，含杀球)
      tsai_forehand_overhead_strokes.md            # S08
      wang_overhead_arm_trunk_steps.md             # S09 (^overhead 非高远球专项)
      zhang_xfactor_smash.md                       # S11 (^smash)
      li_overhead_smash_sequence.md                # S12 (^smash)
    04_emg_msk/
      tsai_emg_smash_jumpsmash.md                  # S13 (^smash, smash vs jump-smash)
      tsai_emg_smash_dropshot.md                   # S14 (^smash, smash vs drop-shot)
      sakurai_smash_emg.md                         # S15 (^smash)
      tajik_synergy_msk.md                         # S17 (^msk)
    05_datasets/
      multisensebadminton.md                       # S16
      badminton_grf_preprint.md                    # S21 (预印本，降权)
    06_validation_framework/
      smpl_msk_ppo_validation.md                   # 实现/方法 (implementation)
      metrics_definitions.md                       # 实现/方法 (implementation)
    07_review/
      phomsoupha_science_of_badminton.md           # S10 (^review)
    08_injury_safety/
      pardiwala_injury_review.md                   # S18 (^inj)
      cejudo_shoulder_pain.md                      # S19 (^inj)
      stausholm_shoulder_strength.md               # S20 (^inj)
  schemas/
    rag_chunk.schema.json
    rag_source.schema.json
  data/
    chunks.jsonl                                   # 概念级 chunk（本包已生成）
  eval/
    gold_questions_zh.jsonl
    no_overclaim_tests.jsonl                       # 反幻觉负面测试
    citation_rubric.md                             # 判分规则
  scripts/
    ingest_sources.py
    clean_pdf_text.py
    chunk_documents.py
    build_hybrid_index.py
    evaluate_rag.py
```

> 文件名后的 `# Sxx` 即对应 `00_source_catalog.csv` 的稳定主键 `id`，切分脚本据此填 chunk 的 `source_ids`，不要用标题字符串作主键。`tsai_emg_*` 原先一个文件无法在 S13/S14 间二选一，已拆为 jumpsmash(S13) 与 dropshot(S14) 两个文件（S14 标题经核查实为 smash vs drop shot，见 sources.csv）。

### 9.2 Chunk 粒度

推荐每个 chunk 控制在 **400–800 个中文字符**，并遵循“一块只讲一个概念”的原则。不要按 PDF 页码机械切分。优先按以下概念切分：

- `definition_chunk`：高远球定义、目的、类型。
- `phase_chunk`：P0–P5 阶段，每阶段一个或多个 chunk。
- `joint_chunk`：关节角/角速度/时序变量。
- `muscle_chunk`：肌群、功能、证据等级。
- `metric_chunk`：验证指标、公式、阈值建议。
- `source_note_chunk`：单篇文献摘要和限制。
- `limitation_chunk`：不能过度推断的内容。
- `implementation_chunk`：RAG 架构、检索、评估、prompt。

### 9.3 Chunk metadata schema

```yaml
chunk_id: bh_clear_phase_p3_forward_swing_001
text: "正手高远球前挥阶段应表现为支撑脚蹬伸、骨盆打开、躯干旋转、肩内旋/水平内收，远端的肘伸展与前臂旋前/腕屈在击球瞬间高度重叠完成释放。近端段(下肢→骨盆→躯干)的近端到远端时序有高远球直接证据支持[S05][S07]；上肢远端段肩-肘相对先后存在分歧，属混合/类比证据[S04^m][S08^m][S12^smash]，不给唯一串行顺序。"
source_ids: ["S04", "S05", "S07", "S08", "S12"]
stroke: forehand_overhead_clear
stroke_aliases: ["正手高远球", "后场正手高远球", "forehand overhead clear", "backcourt forehand clear"]
phase: forward_swing_acceleration
phase_id: P3
body_region: ["lower_limb", "pelvis", "trunk", "shoulder", "elbow", "forearm", "wrist"]
joint_dof: ["ankle_plantarflexion", "knee_extension", "hip_extension", "pelvis_yaw", "trunk_axial_rotation", "shoulder_internal_rotation", "shoulder_horizontal_adduction", "elbow_extension", "forearm_pronation", "wrist_flexion"]
muscle_groups: ["gluteus_maximus", "quadriceps", "gastrocnemius_soleus", "obliques", "pectoralis_major", "latissimus_dorsi", "subscapularis", "triceps_brachii", "pronator_teres_quadratus"]
excluded_muscle_groups: ["flexor_digitorum_superficialis", "flexor_digitorum_profundus", "extensor_digitorum", "hand_intrinsics"]
metrics: ["peak_angular_velocity_timing", "joint_power_peak_timing", "segment_acceleration", "contact_height"]
evidence_level: mixed_direct_and_analogy
confidence: medium
claim_type: ["kinematics", "validation"]
retrieval_tags: ["proximal_distal_sequence", "kinetic_chain", "joint_order", "mimic_validation"]
limits_of_evidence: "近端段时序有高远球直接证据；上肢远端段肩内旋vs肘伸展相对先后存在头顶/杀球类比间的分歧，缺高远球直接3D测量，不要输出固定毫秒顺序或阈值。"
content_hash: "<sha256_of_text>"
chunk_schema_version: "1.1"
created_at: "2026-06-09"
```

### 9.4 Source metadata schema

```yaml
id: S05                                    # 主键即 id；chunk.source_ids 引用此 id（不要写成 source_id）
legacy_id: CLEAR_SORENSEN                   # 对应 rag_project 字符串 ID，见 source_id_crosswalk.csv
title: "A Biomechanical Analysis of Clear Strokes in Badminton Executed by Youth Players of Different Skill Levels"
authors: "Sørensen, K.; de Zee, M.; Rasmussen, J."
year: "2010/2011"                          # 字符串；允许 'n.d.' 与年份区间
source_type: "conference paper / PDF"
evidence_level: "peer_reviewed_direct_clear"   # 来源级细粒度标签
evidence_layer: "peer_reviewed_direct_clear"   # 粗粒度 chunk 证据层（见 §8.2）
stroke_scope: "forehand clear and backhand clear"
browse_url: "https://vbn.aau.dk/en/publications/a-biomechanical-analysis-of-clear-strokes-in-badminton-executed-b/"
download_url: "https://projekter.aau.dk/projekter/files/42678547/articledone.pdf"
doi: ""
license_or_access: "university repository / open PDF"
content_hash: "<sha256_of_fetched_pdf>"
notes: "直接高远球证据；适合动作链、技能水平和能量传递问题。"
```

---

## 10. 检索策略和排序规则

### 10.1 混合检索

建议使用 **BM25 + dense embedding + metadata filter + reranker**：

1. **Query rewrite**：把中文问题扩展为中英文别名。例如“高远球发力顺序”扩展到 `forehand overhead clear + proximal-distal sequence + pelvis/trunk/shoulder/elbow/forearm`。
2. **Metadata filter**：先按 `stroke`、`phase`、`body_region`、`evidence_level` 粗过滤。
3. **BM25**：保留术语精确命中，如 `forearm pronation`、`shoulder internal rotation`、`backcourt forehand clear`。
4. **Dense retrieval**：召回语义相关内容，如“鞭打链”“近端远端传递”“躯干带肩”。
5. **Rerank**：提升直接高远球证据，降低杀球类比证据。
6. **Answer synthesis**：输出时必须保留 `[Sxx]` 引用和证据标签。

### 10.2 Evidence ranking

建议打分：

```text
score = semantic_similarity
      + 0.20 * direct_clear_boost
      + 0.10 * official_coaching_boost
      + 0.10 * peer_reviewed_boost
      + 0.08 * exact_variable_match
      - 0.15 * smash_analogy_penalty_when_question_requires_clear
      - 0.20 * no_source_or_uncertain_penalty
```

对于用户问“高远球肌肉顺序”，不要只召回杀球 EMG。排序应当：

1. BWF/高远球动作阶段 `[S01]`
2. Clear strokes 直接研究 `[S05]`
3. 后场正手高远球下肢/IMU 研究 `[S06][S07]`
4. 正手头顶多击球对比 `[S08]`
5. 杀球 EMG/MSK 类比 `[S13][S14][S17]`

### 10.3 Answer guardrails

RAG 生成器必须遵守：

- 不说“轨迹正确就说明肌肉正确”。
- 不把杀球研究的定量结果直接套到高远球。
- 不在用户要求排除手/手指时展开手指肌肉或握拍压力；在肌群层不引入指浅/指深屈肌、指总伸肌等手指外在肌（见 §0）。
- 不输出没有来源的“标准角度范围”或“精确毫秒峰值”。若没有数据，只能说“建议相对击球时刻计算，并用数据集或个体参考建立分位区间”。
- **区分"模型诊断启发式阈值"与"生物力学定量真值"**：诊断阈值（如激活饱和比例、平滑性等，§6.4）可以给，但必须标注为 heuristic、需按数据分位标定；生物力学真值（角度/毫秒峰值）无来源不得给。
- **不为上肢远端段（肩内旋 vs 肘伸展）给出唯一确定的峰值先后**：该段峰值高度重叠；链条命名/启动顺序 ≠ 峰值时序；跨领域类比弱提示肩内旋峰值偏晚（约在肘伸展之后），但缺高远球直测，故不断言唯一顺序、尤其**不可断言"肩内旋先于肘伸展达峰"**（见 §5.2）。
- 回答必须区分：`直接高远球证据`、`头顶击球共同机制`、`杀球类比`、`模型验证建议`。
- 若来源是教学资料而非论文，应标注“教学动作线索，不是动力学定量证据”。

---

## 11. 面向 Codex/Claude 的实现指令

下面这段可以直接作为给 Codex 或 Claude 的任务说明。

### 11.1 任务目标

请根据本知识库文档和 `badminton_forehand_clear_sources.csv`，搭建一个关于羽毛球正手高远球分析的 RAG 系统。系统需要支持中文问答，能够回答动作阶段、主要肌肉、关节角顺序、运动学/动力学指标、SMPL/肌骨模型验证、相关文献来源等问题。系统必须输出来源引用，并严格区分直接高远球证据与杀球类比证据。

### 11.2 必须实现的模块

1. **Source catalog loader**  
   读取 `00_source_catalog.csv`，为每个来源生成稳定 `source_id`，保存浏览/下载路径、证据等级、许可状态、用途和限制。

2. **Document ingestion**  
   - PDF：优先使用 PyMuPDF 或 GROBID 抽取标题、摘要、正文、表格、参考文献。保留页码。
   - HTML：抽取正文，不保留导航、广告、脚本。
   - Dataset：索引 README、字段说明、数据字典和 DOI，不默认把大文件全部向量化。
   - 版权：对非开放全文只保存 metadata、摘要级笔记和链接；不要将受限全文提交到公开仓库。

3. **Chunk generation**  
   按第 9.2 节的概念粒度切分。每个 chunk 必须包含 `source_ids`、`evidence_level`、`stroke`、`phase`、`body_region`、`joint_dof`、`muscle_groups`、`metrics`、`limits_of_evidence`。

4. **Hybrid retrieval**  
   建立 BM25 与 dense embedding 双索引。查询时先做中英文别名扩展，再用 metadata filter 限定范围，最后 rerank。

5. **Answer generation**  
   回答中文用户时，先给结论，再给证据分层，最后给验证/实现建议。每个关键断言后附 `[Sxx]`。

6. **Evaluation**  
   使用 `gold_questions_zh.jsonl` 做最小评测。评测指标包括：是否召回 direct_clear 来源、是否正确引用、是否误把杀球当高远球、是否遵守“不讨论手指发力”的范围。

### 11.3 推荐伪代码

```python
from rag.schemas import Source, Chunk
from rag.ingest import load_source_catalog, fetch_open_sources, extract_text
from rag.chunking import concept_chunk
from rag.index import build_bm25, build_dense, hybrid_search, rerank
from rag.answer import synthesize_answer

sources = load_source_catalog("corpus/00_source_catalog.csv")
raw_docs = fetch_open_sources(sources, respect_license=True)
clean_docs = [extract_text(doc) for doc in raw_docs]
chunks = concept_chunk(clean_docs, schema="schemas/rag_chunk.schema.json")

bm25 = build_bm25(chunks)
dense = build_dense(chunks, embedding_model="bge-m3-or-current-multilingual")

query = "不考虑手指，正手高远球主要肌肉和发力顺序是什么？"
expanded = rewrite_query_with_aliases(query)
retrieved = hybrid_search(expanded, bm25=bm25, dense=dense, filters={"stroke": ["forehand_overhead_clear", "backcourt_forehand_clear", "overhead_forehand_general", "smash_analogy"]})
ranked = rerank(retrieved, prefer_direct_clear=True, penalize_analogy=True)
answer = synthesize_answer(query, ranked, citation_style="[Sxx]", guardrails="no_overclaim")
print(answer)
```

### 11.4 Prompt 模板

#### 检索前 query rewrite prompt

```text
你是羽毛球生物力学 RAG 检索器。请把用户问题扩展为中英文关键词。
要求：
1. 保留用户原意。
2. 加入高远球别名：正手高远球、后场正手高远球、forehand overhead clear、backcourt forehand clear。
3. 若问题涉及肌肉/顺序，加入 proximal-distal sequence、shoulder internal rotation、forearm pronation、trunk rotation。
4. 若用户排除手/手指，不要加入 finger、grip pressure、hand intrinsic muscles。
输出 JSON：{{"queries": [...], "metadata_filters": {{...}}}}
```

#### 回答生成 prompt

```text
你是羽毛球正手高远球运动生物力学助手。只能使用给定 RAG chunks 回答。
输出规则：
- 用中文回答。
- 先给直接结论，再给分层解释。
- 每个重要结论后必须引用 [Sxx]。
- 必须区分：直接高远球证据、正手头顶多击球证据、杀球类比证据。
- 不得说动作轨迹正确就证明肌肉激活正确。
- 用户排除手和手指时，不展开手指肌肉、握拍压力或掌指关节。
- 若没有直接证据，明确说“这是类比证据”。
```

---

## 12. 知识图谱设计

建议构建轻量知识图谱，辅助检索和答案可解释性。

### 12.1 节点类型

| 节点类型 | 示例 |
|---|---|
| `Stroke` | `forehand_overhead_clear`, `attacking_clear`, `defensive_clear` |
| `Phase` | `preparation`, `backswing_loading`, `forward_swing_acceleration`, `impact`, `follow_through_recovery` |
| `BodySegment` | `lower_limb`, `pelvis`, `trunk`, `scapula`, `shoulder`, `elbow`, `forearm` |
| `JointDOF` | `pelvis_yaw`, `trunk_axial_rotation`, `shoulder_internal_rotation`, `elbow_extension`, `forearm_pronation` |
| `MuscleGroup` | `gluteus_maximus`, `obliques`, `pectoralis_major`, `rotator_cuff`, `triceps_brachii` |
| `Metric` | `peak_angular_velocity_timing`, `joint_power`, `GRF`, `foot_slip`, `activation_smoothness` |
| `Source` | `S01`, `S05`, `S07`, `S17` |
| `Claim` | “近端到远端发力链应由下肢/骨盆传向躯干、肩、肘、前臂” |

### 12.2 边类型

| 边 | 含义 | 示例 |
|---|---|---|
| `has_phase` | 击球包含阶段 | `forehand_overhead_clear -> P3_forward_swing` |
| `requires_joint_motion` | 阶段需要关节动作 | `P3 -> shoulder_internal_rotation` |
| `activates_muscle_group` | 阶段涉及肌群 | `P3 -> pectoralis_major` |
| `evaluated_by_metric` | 用指标验证 | `proximal_distal_sequence -> peak_angular_velocity_timing` |
| `supported_by` | 来源支持断言 | `claim_kinetic_chain -> S05` |
| `analogous_to` | 类比而非直接证据 | `forehand_clear_chain -> smash_sequence_S12` |
| `limited_by` | 证据限制 | `muscle_activation_claim -> no_full_body_EMG` |

---

## 13. 针对论文/报告的标准表述

### 13.1 推荐表述

> 本研究将正手高远球划分为准备、引拍蓄力、前挥加速、击球和随挥恢复阶段。根据羽毛球教学资料和生物力学研究，动作应体现由下肢蹬伸、髋/骨盆旋转、躯干旋转、肩关节内旋与水平内收、肘伸展、前臂旋前与腕屈组成的近端到远端发力链。[S01][S04^m][S05][S08^m]

> 由于缺少全身肌电真值，且肌骨系统存在肌肉冗余和力分配多解，本研究不声称轨迹拟合可以唯一证明真实肌肉激活。我们通过运动学误差、接触质量、关节力矩/功率、肌肉激活平滑性、激活饱和比例、拮抗共同收缩和扰动鲁棒性来验证策略的生物力学合理性。[S17]

### 13.2 不推荐表述

> “轨迹拟合度高，所以肌肉激活一定正确。”  
> 问题：动作轨迹不能唯一决定肌肉激活。

> “高远球主要靠手腕爆发。”  
> 问题：高远球远端释放涉及前臂旋前、肘伸展、肩内旋与肩胛/躯干链式传递；“手腕爆发”过于粗糙。[S04]

> “杀球论文中的峰值角速度就是高远球标准值。”  
> 问题：杀球和高远球目标不同，杀球类比只能作为头顶正手机制参考。[S11][S12]

---

## 14. 最小可用 RAG 评测题

`gold_questions_zh.jsonl` 已单独生成。评测时至少覆盖以下能力：

1. 能定义正手高远球目的、阶段、进攻/防守差异。
2. 能在不考虑手指的条件下列出主要肌群。
3. 能说明近端到远端发力顺序，并给出如何用角速度/功率/体段加速度验证。
4. 能区分直接高远球证据和杀球类比证据。
5. 能解释为什么动作拟合不能证明肌肉激活唯一正确。
6. 能给出 SMPL/肌骨/PPO 策略验证指标。
7. 能引用 MultiSenseBadminton 等数据集作为扩展资源。[S16]

---

## 15. 知识库搭建路线图

### 第 1 步：资料入库

- 使用 `badminton_forehand_clear_sources.csv` 作为 source catalog。
- 对每个来源生成 `source_id` 和 `content_hash`。
- PDF/HTML 原文只存本地；公开仓库只放 metadata、摘录和链接。
- 把教学资料、直接高远球论文、类比论文、数据集、伤病背景分目录存放。

### 第 2 步：结构化抽取

每篇文献至少抽取：

- 研究对象与样本。
- 动作类型：clear/smash/drop/overhead general。
- 设备：Vicon、IMU、EMG、足底压力、OpenSim/MSK 等。
- 关键变量：关节角、角速度、COM、GRF、足底压力、肌肉激活、肌肉协同。
- 关键结论。
- 限制：是否不是高远球、是否样本少、是否只含上肢、是否只有表面肌电。

### 第 3 步：概念 chunk 化

按动作阶段和概念切分；每个 chunk 保留 source_id。不要把整篇论文简单切成固定字数，否则很难进行“直接证据 vs 类比证据”的过滤。

### 第 4 步：检索和生成

- 中文问题先进行术语扩展。
- 使用 hybrid retrieval。
- 对 high-clear 问题默认提升 `direct_clear`。
- 对肌肉/肌电问题允许召回 `EMG_smash_analogy`，但生成时必须加限制说明。

### 第 5 步：评估和迭代

- 用 `gold_questions_zh.jsonl` 做回归测试。
- 增加“反幻觉测试”：故意问“高远球是否只靠手腕？”、“动作像是否证明肌肉正确？”、“杀球数据是否能直接等同高远球？”
- 检查回答是否明确否定不正确推断。

---

## 16. 推荐输出风格

当 RAG 回答用户问题时，建议结构如下：

```text
结论：……

证据分层：
1. 直接高远球证据：…… [S05][S06][S07]
2. 正手头顶多击球证据：…… [S08]
3. 杀球类比证据：…… [S12][S17]

用于你的肌骨模型：
- 看哪些关节角/角速度
- 看哪些肌群/激活合理性
- 看哪些接触和动力学指标

限制：……
```

对于“正手高远球主要肌肉和顺序”这样的问题，推荐回答：

```text
不考虑手和手指，主要链条是：支撑脚蹬地 → 髋/骨盆打开 → 躯干旋转 →〔肩内旋/水平内收、肘伸展、前臂旋前/腕屈在击球瞬间高度重叠，相对先后不确定〕→ 随挥减速。
主要肌群包括：臀大肌、臀中肌、股四头肌、腘绳肌、腓肠肌/比目鱼肌；腹内外斜肌、腹直肌、竖脊肌；胸大肌、背阔肌、大圆肌、三角肌、肩袖、前锯肌/斜方肌；肱三头肌、肱二头肌、旋前圆肌/旋前方肌。（仅前臂层，不含手指外在肌）
其中下肢和高远球体段加速度有直接高远球证据[S05][S06][S07]；肩/前臂和 EMG 细节较多来自含杀球的头顶击球[S04^m][S08^m]或杀球类比[S14^smash][S17^msk]，需要标注限制，且不要把肩内旋排在肘伸展之前当成确定顺序。
```

---

## 17. 局限性和后续扩展

1. 高远球直接生物力学研究少于杀球研究，因此 RAG 不能把所有杀球结论直接迁移。
2. 公开 EMG 研究多集中在上肢和表面肌，不能覆盖深层肌、全身肌肉和真实肌力。
3. 肌骨模型解存在多解；RAG 应强调“合理性验证”而不是“真值证明”。
4. 不同球员、不同身高臂展、步法、持拍手、击球目的会改变动作细节。
5. 如果未来加入球拍和羽毛球飞行模型，应新建 `racket_shuttle_dynamics` 模块，包括拍面姿态、出球角、初速度、飞行落点。
6. 如果未来加入手和手指，应新建 `grip_hand_fingers` 模块，不要混入当前高远球主体链条。

---

## 18. 附录：可直接入库的知识断言样例

> 下列为**断言核心（claim core）**，演示 `evidence_level`（已采用 §8.2 的 chunk 级粗粒度词表）、`source_ids` 与 `retrieval_tags` 的填法。切分脚本会把它们补全为符合 `rag_chunk.schema.json` 的完整 chunk（追加 `chunk_id`/`stroke`/`phase`/`body_region`/`joint_dof`/`muscle_groups`/`metrics`/`limits_of_evidence` 等必填字段）。已生成的完整、可校验 chunk 见 `data/chunks.jsonl`。

### Claim A：高远球技术目的

```yaml
claim_id: claim_clear_purpose_001
text: "正手高远球的目标是将球从己方后场击向对方后场；进攻型高远球通常更低更快以压迫对手身后，防守型高远球通常更高以争取回位时间。"
source_ids: ["S01", "S02", "S03"]
evidence_level: coaching_direct_clear          # chunk 级粗粒度词表（见 §8.2）
confidence: high
retrieval_tags: ["clear_purpose", "attacking_clear", "defensive_clear"]
```

### Claim B：主要发力链

```yaml
claim_id: claim_clear_kinetic_chain_001
text: "不考虑手和手指时，正手高远球可描述为支撑脚蹬地、髋/骨盆打开、躯干旋转、肩内旋与水平内收、肘伸展和前臂旋前组成的近端到远端发力链。"
source_ids: ["S01", "S04", "S05", "S08", "S12"]
evidence_level: mixed_direct_and_analogy
confidence: medium
limits_of_evidence: "直接高远球研究支持阶段和协调；肩/肘/前臂的部分时序证据来自头顶击球或杀球类比。"
retrieval_tags: ["kinetic_chain", "proximal_distal_sequence", "joint_order"]
```

### Claim C：肌骨模型验证限制

```yaml
claim_id: claim_msk_multisolution_001
text: "动作轨迹拟合度高不能唯一证明肌肉激活正确；肌骨模型存在肌肉冗余和力分配多解，应结合动力学、接触、肌肉激活合理性和扰动鲁棒性验证策略。"
source_ids: ["S17"]
evidence_level: msk_methodological             # chunk 级粗粒度词表（见 §8.2）
confidence: high
retrieval_tags: ["musculoskeletal_model", "multi_solution", "validation", "no_overclaim"]
```

---

**结束。**
