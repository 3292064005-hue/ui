from __future__ import annotations

from copy import deepcopy


class SchemaError(ValueError):
    pass


class ConfigSchema:
    @staticmethod
    def validate_app_config(config: dict) -> dict:
        validated = deepcopy(config)
        window = validated.setdefault("window", {})
        plots = validated.setdefault("plots", {})
        ConfigSchema._require_positive_int(window, "width")
        ConfigSchema._require_positive_int(window, "height")
        ConfigSchema._require_positive_int(plots, "max_points")
        for key in ("splitter_sizes", "vertical_splitter_sizes"):
            if key in window:
                values = window[key]
                if not isinstance(values, list) or not values or any(int(v) <= 0 for v in values):
                    raise SchemaError(f"window.{key} must be a non-empty list of positive ints")
        return validated

    @staticmethod
    def validate_solver_config(config: dict) -> dict:
        validated = deepcopy(config)
        ik = validated.setdefault("ik", {})
        traj = validated.setdefault("trajectory", {})
        if str(ik.get("mode", "dls")) not in {"pinv", "dls", "lm", "analytic_6r"}:
            raise SchemaError("ik.mode must be 'pinv', 'dls', 'lm' or 'analytic_6r'")
        for key in ("max_iters", "retry_count", "random_seed"):
            if key in ik and int(ik[key]) < 0:
                raise SchemaError(f"ik.{key} must be >= 0")
        for key in (
            "pos_tol",
            "ori_tol",
            "damping_lambda",
            "step_scale",
            "joint_limit_weight",
            "manipulability_weight",
            "orientation_weight",
            "max_step_norm",
            "singularity_cond_threshold",
            "min_damping_lambda",
            "max_damping_lambda",
            "orientation_relaxation_pos_multiplier",
            "orientation_relaxation_ori_multiplier",
        ):
            if key in ik and float(ik[key]) < 0.0:
                raise SchemaError(f"ik.{key} must be >= 0")
        if "min_damping_lambda" in ik and "max_damping_lambda" in ik:
            if float(ik["min_damping_lambda"]) > float(ik["max_damping_lambda"]):
                raise SchemaError("ik.min_damping_lambda must be <= ik.max_damping_lambda")
        if "duration" in traj and float(traj["duration"]) <= 0.0:
            raise SchemaError("trajectory.duration must be > 0")
        if "dt" in traj and float(traj["dt"]) <= 0.0:
            raise SchemaError("trajectory.dt must be > 0")
        return validated

    @staticmethod
    def _require_positive_int(section: dict, key: str) -> None:
        if key not in section:
            return
        if int(section[key]) <= 0:
            raise SchemaError(f"{key} must be > 0")
