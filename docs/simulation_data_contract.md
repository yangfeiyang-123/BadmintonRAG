# Simulation Data Contract

This contract defines how real joint-angle and muscle-activation simulation data enters the forehand-clear diagnostic system.

## CSV Shape

Each CSV row is one time point for one action sample. Rows with the same `sample_id` are grouped into one sample.

Required metadata columns:

| Column | Required | Meaning |
| --- | --- | --- |
| `sample_id` | yes | Unique action sample id. |
| `split` | yes | Use `correct` for reference-template samples and `eval` for samples to diagnose. |
| `action_type` | yes | Currently `forehand_clear`. |
| `outcome_label` | yes | Discrete consequence label. Supported values are `ball_high_not_far`, `low_speed`, and `uncoordinated_power`. |
| `time` | yes | Time in seconds. Values are sorted inside each sample before conversion. |

Required signal prefixes:

| Prefix | Target group | Unit hint | Example |
| --- | --- | --- | --- |
| `event_` | `events` | seconds | `event_impact` |
| `joint_` | `joint_angles` | degrees | `joint_trunk_rotation` |
| `muscle_` | `muscle_activation` | normalized 0 to 1 | `muscle_external_oblique` |

At least one column with each required prefix must be present. `event_impact` is required by the downstream diagnostic schema because all phase features are aligned around impact.

All `joint_` and `muscle_` values must be numeric on every row. `event_` values may be blank for sparse event columns, but every non-blank event value must be numeric.

## Mapping Examples

| Simulation output | CSV column |
| --- | --- |
| trunk rotation angle | `joint_trunk_rotation` |
| forearm pronation angle | `joint_forearm_pronation` |
| shoulder internal rotation angle | `joint_shoulder_internal_rotation` |
| elbow flexion angle | `joint_elbow_flexion` |
| wrist extension angle | `joint_wrist_extension` |
| external oblique activation | `muscle_external_oblique` |
| anterior deltoid activation | `muscle_anterior_deltoid` |
| triceps brachii activation | `muscle_triceps_brachii` |
| forearm pronator group activation | `muscle_forearm_pronator_group` |
| impact event time | `event_impact` |
| acceleration-start event time | `event_acceleration_start` |
| follow-through-end event time | `event_follow_through_end` |

## Validate Before Diagnosis

Run the contract validator before batch diagnosis:

```powershell
.\.venv\Scripts\python.exe -m rag_project.diagnostics.data_contract `
  --csv-dataset rag_project\examples\forehand_clear_simulation.csv
```

The command prints a JSON summary with row count, sample count, split counts, action types, outcome labels, signal counts, and field specs.

Then run diagnosis:

```powershell
.\.venv\Scripts\python.exe -m rag_project.diagnostics.batch `
  --csv-dataset rag_project\examples\forehand_clear_simulation.csv `
  --output-dir rag_project\outputs\batch_forehand_clear_csv `
  --retrieval-backend keyword
```
