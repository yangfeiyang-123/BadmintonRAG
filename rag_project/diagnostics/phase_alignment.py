from __future__ import annotations

from dataclasses import dataclass

from rag_project.diagnostics.schemas import DiagnosticSample


@dataclass(frozen=True)
class PhaseWindow:
    name: str
    start: float
    end: float


def phase_windows(sample: DiagnosticSample) -> list[PhaseWindow]:
    impact = sample.events["impact"]
    return [
        PhaseWindow(
            "backswing",
            sample.events.get("backswing_start", sample.time[0]),
            sample.events.get("acceleration_start", impact),
        ),
        PhaseWindow("acceleration", sample.events.get("acceleration_start", sample.time[0]), impact),
        PhaseWindow("impact_window", impact - 0.05, impact + 0.05),
        PhaseWindow("follow_through", impact, sample.events.get("follow_through_end", sample.time[-1])),
    ]
