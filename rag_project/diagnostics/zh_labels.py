"""Chinese labels for diagnostic structured output.

Translates the English joint/muscle signal names, phases, feature types, directions,
severities, units and outcome labels that flow from the simulation CSV into the
structured suggestions (correction plan / explanation links). Unknown names fall
back to the original string so nothing is ever dropped.
"""
from __future__ import annotations

# Joint + muscle base signal names (the part before the feature suffix).
SIGNAL_ZH: dict[str, str] = {
    # joints / DOF
    "trunk_rotation": "躯干旋转",
    "trunk_axial_rotation": "躯干轴向旋转",
    "trunk_flexion": "躯干屈曲",
    "trunk_lateral_flexion": "躯干侧屈",
    "pelvis_yaw": "骨盆旋转",
    "pelvis_tilt": "骨盆前后倾",
    "hip_extension": "髋伸展",
    "hip_flexion": "髋屈曲",
    "hip_rotation": "髋旋转",
    "knee_extension": "膝伸展",
    "knee_flexion": "膝屈曲",
    "ankle_plantarflexion": "踝跖屈",
    "ankle_dorsiflexion": "踝背屈",
    "shoulder_internal_rotation": "肩内旋",
    "shoulder_external_rotation": "肩外旋",
    "shoulder_horizontal_adduction": "肩水平内收",
    "shoulder_abduction": "肩外展",
    "shoulder_flexion": "肩屈曲",
    "elbow_extension": "肘伸展",
    "elbow_flexion": "肘屈曲",
    "forearm_pronation": "前臂旋前",
    "forearm_supination": "前臂旋后",
    "wrist_extension": "腕背伸",
    "wrist_flexion": "腕屈",
    # muscles / groups
    "external_oblique": "腹外斜肌",
    "internal_oblique": "腹内斜肌",
    "rectus_abdominis": "腹直肌",
    "erector_spinae": "竖脊肌",
    "anterior_deltoid": "三角肌前束",
    "middle_deltoid": "三角肌中束",
    "posterior_deltoid": "三角肌后束",
    "pectoralis_major": "胸大肌",
    "latissimus_dorsi": "背阔肌",
    "teres_major": "大圆肌",
    "subscapularis": "肩胛下肌",
    "infraspinatus": "冈下肌",
    "supraspinatus": "冈上肌",
    "rotator_cuff": "肩袖",
    "serratus_anterior": "前锯肌",
    "trapezius": "斜方肌",
    "triceps_brachii": "肱三头肌",
    "biceps_brachii": "肱二头肌",
    "brachialis": "肱肌",
    "pronator_teres": "旋前圆肌",
    "pronator_quadratus": "旋前方肌",
    "forearm_pronator_group": "前臂旋前肌群",
    "gluteus_maximus": "臀大肌",
    "gluteus_medius": "臀中肌",
    "quadriceps": "股四头肌",
    "hamstrings": "腘绳肌",
    "gastrocnemius": "腓肠肌",
    "soleus": "比目鱼肌",
}

PHASE_ZH: dict[str, str] = {
    "backswing": "引拍蓄力",
    "acceleration": "前挥加速",
    "impact_window": "击球窗口",
    "impact": "击球",
    "follow_through": "随挥恢复",
    "all": "全程",
    "preparation": "准备",
    "movement_to_rearcourt": "后场移动",
}

FEATURE_GROUP_ZH: dict[str, str] = {
    "joint_angle": "关节角",
    "muscle_activation": "肌肉激活",
    "unknown": "未知",
}

DIRECTION_ZH: dict[str, str] = {
    "below_template": "低于正确模板",
    "above_template": "高于正确模板",
    "within_template": "模板范围内",
}

SEVERITY_ZH: dict[str, str] = {"high": "高", "medium": "中", "low": "低", "none": "无"}

UNIT_ZH: dict[str, str] = {
    "degree": "度",
    "degree_per_second": "度/秒",
    "second": "秒",
    "normalized_activation": "归一化激活",
}

OUTCOME_ZH: dict[str, str] = {
    "ball_high_not_far": "球过高不够远",
    "low_speed": "球速过低",
    "uncoordinated_power": "发力不协调",
}

# Feature-name suffixes, longest first so the most specific match wins.
_FEATURE_SUFFIX_ZH: list[tuple[str, str]] = [
    ("_activation_peak_time_relative_to_impact", "激活相对击球的峰值时刻"),
    ("_peak_time_relative_to_impact", "相对击球的峰值时刻"),
    ("_velocity_peak", "角速度峰值"),
    ("_activation_peak", "激活峰值"),
    ("_peak", "峰值"),
]


def zh_signal(name: str) -> str:
    return SIGNAL_ZH.get(name, name)


def zh_phase(phase: str) -> str:
    return PHASE_ZH.get(phase, phase)


def zh_group(group: str) -> str:
    return FEATURE_GROUP_ZH.get(group, group)


def zh_direction(direction: str) -> str:
    return DIRECTION_ZH.get(direction, direction)


def zh_severity(severity: str) -> str:
    return SEVERITY_ZH.get(severity, severity)


def zh_unit(unit: str) -> str:
    return UNIT_ZH.get(unit, unit)


def zh_outcome(outcome: str) -> str:
    return OUTCOME_ZH.get(outcome, outcome)


def zh_feature(feature: str) -> str:
    """Translate a full feature name, e.g. 'trunk_rotation_velocity_peak' -> '躯干旋转·角速度峰值'."""
    for suffix, suffix_zh in _FEATURE_SUFFIX_ZH:
        if feature.endswith(suffix):
            signal = feature[: -len(suffix)]
            return f"{zh_signal(signal)}·{suffix_zh}"
    return zh_signal(feature)
