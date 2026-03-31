from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig


class MainlineRuntimeDoctorService:
    """Unify runtime-side contracts into a single operator-facing readiness verdict.

    This service intentionally does not replace the official runtime/core verdict.
    It summarizes whether the *governance shell* around the official SDK mainline
    is internally aligned: single control source, session freeze, motion/runtime
    contract, model authority, and deployment constraints.
    """

    def inspect(
        self,
        *,
        config: RuntimeConfig,
        sdk_runtime: dict[str, Any] | None = None,
        backend_link: dict[str, Any] | None = None,
        model_report: dict[str, Any] | None = None,
        session_governance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sdk_runtime = dict(sdk_runtime or {})
        backend_link = dict(backend_link or {})
        model_report = dict(model_report or {})
        session_governance = dict(session_governance or {})

        blockers: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        sections: dict[str, Any] = {}

        def push(target: list[dict[str, Any]], section: str, name: str, detail: str) -> None:
            target.append({"section": section, "name": name, "detail": detail})

        control = dict(sdk_runtime.get("control_governance_contract", {}))
        runtime_alignment = dict(sdk_runtime.get("runtime_alignment", {}))
        clinical = dict(sdk_runtime.get("clinical_mainline_contract", {}))
        capability = dict(sdk_runtime.get("capability_contract", {}))
        model_authority = dict(sdk_runtime.get("model_authority_contract", {}))
        motion = dict(sdk_runtime.get("motion_contract", {}))
        session_freeze = dict(sdk_runtime.get("session_freeze", {}))
        session_drift = dict(sdk_runtime.get("session_drift_contract", {}))
        hardware_lifecycle = dict(sdk_runtime.get("hardware_lifecycle_contract", {}))
        rt_kernel = dict(sdk_runtime.get("rt_kernel_contract", {}))
        release_contract = dict(sdk_runtime.get("release_contract", {}))
        deployment = dict(sdk_runtime.get("deployment_contract", {}))
        environment = dict(sdk_runtime.get("environment_doctor", {}))
        controller_evidence = dict(sdk_runtime.get("controller_evidence", {}))
        dual_state_machine = dict(sdk_runtime.get("dual_state_machine_contract", {}))
        mainline_executor = dict(sdk_runtime.get("mainline_executor_contract", {}))
        mainline_task_tree = dict(sdk_runtime.get("mainline_task_tree", {}))

        expected_rt_mode = str(clinical.get("clinical_mainline_mode") or config.rt_mode)
        actual_rt_mode = str(motion.get("rt_mode") or config.rt_mode)
        if expected_rt_mode and actual_rt_mode and expected_rt_mode != actual_rt_mode:
            push(blockers, "clinical_mainline", "rt_mode_mismatch", f"runtime rt_mode={actual_rt_mode}, expected={expected_rt_mode}")

        if bool(control.get("single_control_source_required", config.requires_single_control_source)):
            ownership = dict(backend_link.get("control_plane", {})).get("control_authority", {}) or {}
            ownership_state = str(ownership.get("summary_state", ""))
            if ownership_state == "blocked":
                push(blockers, "control_governance", "control_authority_conflict", str(ownership.get("detail", "控制权冲突")))
            elif ownership_state in {"degraded", "warning"}:
                push(warnings, "control_governance", "control_authority_degraded", str(ownership.get("detail", "控制权非严格收敛")))

        session_locked = bool(session_freeze.get("session_locked"))
        if session_locked and not bool(control.get("session_binding_valid", True)):
            push(blockers, "session_freeze", "session_binding_invalid", str(control.get("detail") or "session 已锁定但 plan_hash/runtime bind 不一致"))
        elif not session_locked:
            push(warnings, "session_freeze", "session_not_locked_yet", "会话尚未冻结；启动链会在正式执行前完成 lock_session。")

        if session_locked and not bool(control.get("runtime_config_bound", False)):
            push(warnings, "session_freeze", "runtime_config_unbound", "运行时配置尚未形成冻结绑定。")

        final_verdict = dict(model_report.get("final_verdict", {}))
        if final_verdict and not bool(final_verdict.get("accepted", False)):
            push(blockers, "model_precheck", "final_verdict_rejected", str(final_verdict.get("reason", "runtime final verdict rejected")))
        elif model_report.get("authority_source") == "python_advisory_fallback":
            push(warnings, "model_precheck", "advisory_only", "当前仅有 Python advisory 预检，尚未拿到 runtime authoritative verdict。")

        if not bool(model_authority.get("planner_supported", True)) or not bool(model_authority.get("xmate_model_supported", True)):
            push(warnings, "model_authority", "official_model_unavailable", "当前运行环境未确认官方 Planner/xMateModel 权威可用。")

        if environment.get("summary_state") == "blocked":
            push(blockers, "environment", "sdk_environment_blocked", str(environment.get("detail", "SDK 环境检查未通过。")))
        elif environment.get("summary_state") in {"warning", "degraded"}:
            push(warnings, "environment", "sdk_environment_warning", str(environment.get("detail", "SDK 环境存在告警。")))

        if runtime_alignment.get("sdk_available") is False:
            push(warnings, "runtime_alignment", "sdk_not_live", "当前为 contract/mock 对齐环境，未确认实机 SDK 已接管。")

        if bool(motion.get("nrt_contract", {}).get("degraded_without_sdk", False)):
            push(warnings, "motion_contract", "nrt_degraded", "NRT 主线仍处于 contract/degraded 包装态。")
        if bool(motion.get("rt_contract", {}).get("degraded_without_sdk", False)):
            push(warnings, "motion_contract", "rt_degraded", "RT 主线仍处于 contract/degraded 包装态。")

        if dual_state_machine:
            if not bool(dual_state_machine.get("execution_and_clinical_aligned", True)):
                push(blockers, "state_machine", "dual_state_machine_misaligned", str(dual_state_machine.get("detail", "执行状态机与临床任务状态机未对齐。")))
            elif str(dual_state_machine.get("summary_state", "ready")) in {"warning", "degraded"}:
                push(warnings, "state_machine", "dual_state_machine_warning", str(dual_state_machine.get("detail", "双层状态机存在告警。")))

        if mainline_executor:
            if not bool(mainline_executor.get("task_tree_aligned", True)):
                push(blockers, "mainline_executor", "task_tree_executor_misaligned", str(mainline_executor.get("detail", "executor 合同与任务树阶段不一致。")))
            if dict(mainline_executor.get("rt_executor", {})).get("summary_state") in {"warning", "degraded"}:
                push(warnings, "mainline_executor", "rt_executor_warning", str(dict(mainline_executor.get("rt_executor", {})).get("detail", "RT executor degraded")))
            if dict(mainline_executor.get("nrt_executor", {})).get("summary_state") in {"warning", "degraded"}:
                push(warnings, "mainline_executor", "nrt_executor_warning", str(dict(mainline_executor.get("nrt_executor", {})).get("detail", "NRT executor degraded")))

        if mainline_task_tree:
            if str(mainline_task_tree.get("summary_state", "ready")) == "blocked":
                push(blockers, "mainline_task_tree", "task_tree_blocked", str(mainline_task_tree.get("detail", "临床主线任务树阻塞。")))
            elif str(mainline_task_tree.get("summary_state", "ready")) == "warning":
                push(warnings, "mainline_task_tree", "task_tree_warning", str(mainline_task_tree.get("detail", "临床主线任务树告警。")))


        if session_drift and str(session_drift.get("summary_state", "ready")) == "blocked":
            push(blockers, "session_freeze", "session_freeze_drift", str(session_drift.get("detail", "session freeze drift detected")))

        if hardware_lifecycle:
            if str(hardware_lifecycle.get("summary_state", "ready")) == "blocked":
                push(blockers, "hardware_lifecycle", "hardware_lifecycle_blocked", str(hardware_lifecycle.get("detail", "hardware lifecycle blocked")))
            elif str(hardware_lifecycle.get("summary_state", "ready")) in {"warning", "degraded"}:
                push(warnings, "hardware_lifecycle", "hardware_lifecycle_warning", str(hardware_lifecycle.get("detail", "hardware lifecycle warning")))

        if rt_kernel:
            if bool(rt_kernel.get("monitors", {}).get("reference_limiter")) is False:
                push(blockers, "rt_kernel", "reference_limiter_missing", "RT kernel 缺少 reference limiter。")
            if bool(rt_kernel.get("monitors", {}).get("freshness_guard")) is False:
                push(blockers, "rt_kernel", "freshness_guard_missing", "RT kernel 缺少 freshness guard。")
            if bool(rt_kernel.get("monitors", {}).get("jitter_monitor")) is False:
                push(warnings, "rt_kernel", "jitter_monitor_missing", "RT kernel 未声明 jitter monitor。")
            if str(rt_kernel.get("summary_state", "ready")) in {"warning", "degraded"}:
                push(warnings, "rt_kernel", "rt_kernel_warning", str(rt_kernel.get("detail", "rt kernel warning")))

        if session_governance.get("summary_state") == "blocked":
            push(blockers, "session_governance", "session_governance_blocked", str(session_governance.get("detail", "会话治理阻塞。")))
        elif session_governance.get("summary_state") == "warning":
            push(warnings, "session_governance", "session_governance_warning", str(session_governance.get("detail", "会话治理告警。")))

        if release_contract.get("summary_state") == "blocked":
            if session_locked or bool(release_contract.get("compile_ready")) or bool(release_contract.get("ready_for_approach")) or bool(release_contract.get("ready_for_scan")):
                push(blockers, "release_contract", "release_gate_blocked", str(release_contract.get("detail", "release contract blocked")))
            else:
                push(warnings, "release_contract", "release_gate_pending", str(release_contract.get("detail", "release contract pending until session lock")))

        if deployment.get("summary_state") in {"warning", "degraded"}:
            push(warnings, "deployment", "deployment_profile_warning", str(deployment.get("detail", deployment.get("summary_label", "deployment degraded"))))

        if controller_evidence and not str(controller_evidence.get("last_event", "")):
            push(warnings, "controller_evidence", "no_recent_controller_event", "尚未形成可关联的 controller event/evidence。")

        sections["control_governance"] = {
            "summary_state": "ready" if not any(item["section"] == "control_governance" for item in blockers + warnings) else ("blocked" if any(item["section"] == "control_governance" for item in blockers) else "warning"),
            "summary_label": "唯一控制源" if bool(control.get("single_control_source_required", config.requires_single_control_source)) else "控制源可共享",
            "detail": str(control.get("detail", "single control source contract")),
            "contract": control,
        }
        sections["session_freeze"] = {
            "summary_state": "ready" if session_locked and bool(control.get("session_binding_valid", True)) else ("warning" if not session_locked else "blocked"),
            "summary_label": "会话冻结已绑定" if session_locked else "会话待冻结",
            "detail": str(session_drift.get("detail") or control.get("detail") or session_governance.get("detail") or "session freeze contract"),
            "contract": {**session_freeze, "drift": session_drift},
        }
        sections["clinical_mainline"] = {
            "summary_state": "ready" if expected_rt_mode == actual_rt_mode else "blocked",
            "summary_label": "临床主线对齐",
            "detail": f"expected_rt_mode={expected_rt_mode}, runtime_rt_mode={actual_rt_mode}",
            "contract": clinical,
        }
        sections["model_authority"] = {
            "summary_state": "ready" if final_verdict.get("accepted", False) else ("warning" if model_report.get("authority_source") == "python_advisory_fallback" else "blocked"),
            "summary_label": "模型权威裁决",
            "detail": str(final_verdict.get("reason") or model_report.get("detail") or "model authority contract"),
            "contract": model_authority,
        }
        sections["runtime_alignment"] = {
            "summary_state": "ready" if runtime_alignment.get("sdk_available") else "warning",
            "summary_label": "SDK 运行时对齐",
            "detail": str(runtime_alignment.get("source", "runtime alignment contract")),
            "contract": runtime_alignment,
        }
        sections["state_machine"] = {
            "summary_state": str(dual_state_machine.get("summary_state", "unknown")),
            "summary_label": str(dual_state_machine.get("summary_label", "双层状态机")),
            "detail": str(dual_state_machine.get("detail", "dual state machine contract")),
            "contract": dual_state_machine,
        }
        sections["mainline_executor"] = {
            "summary_state": str(mainline_executor.get("summary_state", "unknown")),
            "summary_label": str(mainline_executor.get("summary_label", "主线执行器")),
            "detail": str(mainline_executor.get("detail", "mainline executor contract")),
            "contract": mainline_executor,
        }
        sections["mainline_task_tree"] = {
            "summary_state": str(mainline_task_tree.get("summary_state", "unknown")),
            "summary_label": str(mainline_task_tree.get("summary_label", "临床主线任务树")),
            "detail": str(mainline_task_tree.get("detail", "mainline task tree contract")),
            "contract": mainline_task_tree,
        }
        sections["environment"] = {
            "summary_state": str(environment.get("summary_state", "unknown")),
            "summary_label": str(environment.get("summary_label", "SDK 环境")),
            "detail": str(environment.get("detail", "SDK environment doctor")),
            "contract": environment,
        }

        sections["hardware_lifecycle"] = {
            "summary_state": str(hardware_lifecycle.get("summary_state", "unknown")),
            "summary_label": str(hardware_lifecycle.get("summary_label", "硬件生命周期")),
            "detail": str(hardware_lifecycle.get("detail", "hardware lifecycle contract")),
            "contract": hardware_lifecycle,
        }
        sections["rt_kernel"] = {
            "summary_state": str(rt_kernel.get("summary_state", "unknown")),
            "summary_label": str(rt_kernel.get("summary_label", "RT 内核")),
            "detail": str(rt_kernel.get("detail", "rt kernel contract")),
            "contract": rt_kernel,
        }

        summary_state = "ready"
        if blockers:
            summary_state = "blocked"
        elif warnings:
            summary_state = "warning"

        return {
            "summary_state": summary_state,
            "summary_label": {
                "ready": "运行主线治理通过",
                "warning": "运行主线治理告警",
                "blocked": "运行主线治理阻塞",
            }[summary_state],
            "detail": "官方 SDK 主线、会话冻结、唯一控制源、模型裁决与环境检查的统一治理结果。",
            "blockers": blockers,
            "warnings": warnings,
            "sections": sections,
            "expected_rt_mode": expected_rt_mode,
            "runtime_rt_mode": actual_rt_mode,
            "session_locked": bool(session_freeze.get("session_locked")),
            "final_verdict_accepted": bool(final_verdict.get("accepted", False)),
            "single_control_source_required": bool(control.get("single_control_source_required", config.requires_single_control_source)),
            "sdk_live": bool(runtime_alignment.get("sdk_available", False)),
            "hardware_lifecycle_live": bool(hardware_lifecycle.get("live_takeover_ready", False)),
            "session_freeze_drift_count": len(session_drift.get("drifts", [])),
        }
