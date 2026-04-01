# Packaging

## Local development

```bash
pip install -e .[dev]
```

## GUI development

```bash
pip install -e .[gui,dev]
```

## Package export

应用层支持一键导出 ZIP package，内含：

- trajectory bundle
- benchmark report
- benchmark cases csv
- session json
- manifest.json

后续如需 wheel / desktop bundle，可在现有 `PackageService` 基础上继续扩展。


## Installed runtime contract

- 构建产物现在随包分发 `robot_sim.resources.configs/**`，覆盖 `app.yaml`、`logging.yaml`、`plugins.yaml`、profiles、robots 与 solver 配置。
- 安装态启动优先读取包内资源；源码态仍兼容仓库 `configs/`。
- CI `release_validation` 已增加 wheel 安装后的真实 `bootstrap()` / `build_container()` 烟测，而不是仅做 import 验证。
