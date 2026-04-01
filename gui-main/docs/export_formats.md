# Export Formats

## trajectory bundle (`.npz`)

包含字段：

- `t`
- `q`
- `qd`
- `qdd`
- `ee_positions`（若有）
- `joint_positions`（若有）
- `ee_rotations`（若有）
- `manifest_json`
- `metadata_json`
- `quality_json`
- `feasibility_json`

## benchmark report (`.json`)

包含字段：

- `robot`
- `num_cases`
- `success_rate`
- `cases`
- `aggregate`
- `metadata`
- `comparison`

## benchmark cases (`.csv`)

按 case 明细导出，每行一个 benchmark case 结果。

## session (`.json`)

保存当前机器人、位姿、IK 结果、trajectory 概要、benchmark 概要与 playback 状态。

## package (`.zip`)

包含一组实验复现文件及 `manifest.json`。
