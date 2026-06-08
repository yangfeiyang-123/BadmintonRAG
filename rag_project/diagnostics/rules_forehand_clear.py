from __future__ import annotations

from rag_project.diagnostics.schemas import OutcomeLabel


OUTCOME_RULES = {
    OutcomeLabel.BALL_HIGH_NOT_FAR: {
        "primary_diagnosis": "击球阶段向前动量不足，末端释放效率偏低",
        "features": ["trunk_rotation", "forearm_pronation", "wrist", "elbow", "external_oblique", "anterior_deltoid"],
        "mechanisms": ["躯干带动不足", "末端释放滞后或不足", "发力方向偏上，向前动量不足"],
        "suggestions": [
            "优先练习蹬地、转髋、转体后再带动肩肘腕释放。",
            "击球点保持在身体前上方，避免击球点过后导致向前穿透不足。",
            "练习击球前后窗口的前臂旋前和腕部释放。",
        ],
    },
    OutcomeLabel.LOW_SPEED: {
        "primary_diagnosis": "动力链总输出不足",
        "features": ["trunk_rotation_velocity", "shoulder", "elbow", "forearm_pronation", "wrist"],
        "mechanisms": ["动力链总输出不足", "近端到远端传递效率低", "击球阶段力量释放不集中"],
        "suggestions": ["提高蹬转与躯干旋转输出。", "练习肩肘腕在击球窗口集中释放。"],
    },
    OutcomeLabel.UNCOORDINATED_POWER: {
        "primary_diagnosis": "近端到远端释放顺序异常",
        "features": ["peak_time_relative_to_impact", "trunk_rotation", "shoulder", "elbow", "wrist"],
        "mechanisms": ["动作阶段衔接问题", "肌肉激活时序不稳定", "动力链释放顺序异常"],
        "suggestions": ["用慢速分解练习建立蹬转、转体、挥臂的顺序。", "把末端释放集中到击球前后窗口。"],
    },
}
