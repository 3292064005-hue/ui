from __future__ import annotations

import platform
import shutil
import sys
from dataclasses import dataclass, field
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.sdk_vendor_locator import SdkVendorLocator


@dataclass
class DoctorCheck:
    name: str
    ok: bool
    severity: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ok": bool(self.ok),
            "severity": self.severity,
            "detail": self.detail,
        }


@dataclass
class SdkEnvironmentDoctorSnapshot:
    summary_state: str = "unknown"
    summary_label: str = "环境未检查"
    detail: str = "尚未执行环境检查。"
    blockers: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    checks: list[dict[str, Any]] = field(default_factory=list)
    toolchain: dict[str, Any] = field(default_factory=dict)
    sdk_paths: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary_state": self.summary_state,
            "summary_label": self.summary_label,
            "detail": self.detail,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
            "checks": list(self.checks),
            "toolchain": dict(self.toolchain),
            "sdk_paths": dict(self.sdk_paths),
        }


class SdkEnvironmentDoctorService:
    """Local environment preflight for the xCore desktop+core mainline."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = Path(root_dir or Path(__file__).resolve().parents[2])
        self.snapshot = SdkEnvironmentDoctorSnapshot()
        self.locator = SdkVendorLocator(self.root_dir)

    def inspect(self, config: RuntimeConfig) -> dict[str, Any]:
        checks: list[DoctorCheck] = []
        python_ok = sys.version_info >= (3, 11)
        checks.append(self._check(
            "Python 版本",
            python_ok,
            "blocker",
            f"Python {platform.python_version()}" + ("" if python_ok else "，主线要求 3.11+"),
        ))
        ubuntu_ok = platform.system() == "Linux"
        checks.append(self._check(
            "主机操作系统",
            ubuntu_ok,
            "warning",
            f"{platform.system()} {platform.release()} / {platform.version()}",
        ))
        checks.extend(self._toolchain_checks())
        checks.extend(self._sdk_mount_checks())
        checks.extend(self._tls_checks())
        checks.extend(self._network_checks(config))

        blockers = [item.to_dict() for item in checks if item.severity == "blocker" and not item.ok]
        warnings = [item.to_dict() for item in checks if item.severity == "warning" and not item.ok]
        summary_state = "ready"
        if blockers:
            summary_state = "blocked"
        elif warnings:
            summary_state = "warning"
        summary_label = {
            "ready": "环境主线就绪",
            "warning": "环境存在告警",
            "blocked": "环境主线阻塞",
        }[summary_state]
        detail = "本机已满足 xCore 桌面/核心主线前提。" if summary_state == "ready" else (
            "需要先补齐本机依赖、vendored SDK 结构或 TLS 材料，才能进入真实 robot_core 主线。" if summary_state == "blocked" else "存在非阻塞告警，建议在进入实机前修正。"
        )
        layout = self.locator.locate()
        self.snapshot = SdkEnvironmentDoctorSnapshot(
            summary_state=summary_state,
            summary_label=summary_label,
            detail=detail,
            blockers=blockers,
            warnings=warnings,
            checks=[item.to_dict() for item in checks],
            toolchain={
                "python": platform.python_version(),
                "cmake": shutil.which("cmake") or "",
                "g++": shutil.which("g++") or shutil.which("clang++") or "",
                "protoc": shutil.which("protoc") or "",
                "node": shutil.which("node") or "",
                "npm": shutil.which("npm") or "",
                "openssl": shutil.which("openssl") or "",
            },
            sdk_paths={
                **layout.to_dict(),
                "tls_runtime_dir": str(self.root_dir / "configs" / "tls" / "runtime"),
            },
        )
        return self.snapshot.to_dict()

    def _toolchain_checks(self) -> list[DoctorCheck]:
        protobuf_header = Path("/usr/include/google/protobuf/message.h")
        openssl_header = Path("/usr/include/openssl/ssl.h")
        return [
            self._check("CMake", shutil.which("cmake") is not None, "blocker", shutil.which("cmake") or "未找到 cmake"),
            self._check("C++ 编译器", shutil.which("g++") is not None or shutil.which("clang++") is not None, "blocker", shutil.which("g++") or shutil.which("clang++") or "未找到 g++/clang++"),
            self._check("Protobuf 编译器", shutil.which("protoc") is not None, "warning", shutil.which("protoc") or "未找到 protoc"),
            self._check("Protobuf 开发头文件", protobuf_header.exists(), "blocker", str(protobuf_header) if protobuf_header.exists() else "未找到 protobuf 头文件"),
            self._check("OpenSSL", shutil.which("openssl") is not None, "warning", shutil.which("openssl") or "未找到 openssl"),
            self._check("OpenSSL 开发头文件", openssl_header.exists(), "blocker", str(openssl_header) if openssl_header.exists() else "未找到 openssl 头文件"),
        ]

    def _sdk_mount_checks(self) -> list[DoctorCheck]:
        layout = self.locator.locate()
        return [
            self._check("xCore SDK 根目录", layout.sdk_root is not None, "blocker", str(layout.sdk_root) if layout.sdk_root else "未找到 vendored SDK"),
            self._check("xCore SDK include", layout.include_dir is not None, "blocker", str(layout.include_dir) if layout.include_dir else "include 缺失"),
            self._check("xCore SDK external", layout.external_dir is not None, "blocker", str(layout.external_dir) if layout.external_dir else "external 缺失"),
            self._check("xCore SDK 静态库", layout.static_lib is not None, "blocker", str(layout.static_lib) if layout.static_lib else "libxCoreSDK.a 缺失"),
            self._check("xMateModel 静态库", layout.xmate_model_available, "warning", str(layout.xmate_model_lib) if layout.xmate_model_lib else "libxMateModel.a 缺失"),
        ]

    def _tls_checks(self) -> list[DoctorCheck]:
        runtime_dir = self.root_dir / "configs" / "tls" / "runtime"
        material = list(runtime_dir.glob("*.pem")) + list(runtime_dir.glob("*.crt")) + list(runtime_dir.glob("*.key"))
        return [
            self._check("TLS runtime 目录", runtime_dir.exists(), "blocker", str(runtime_dir)),
            self._check("TLS 证书材料", bool(material), "warning", f"{runtime_dir} / {len(material)} files"),
        ]

    def _network_checks(self, config: RuntimeConfig) -> list[DoctorCheck]:
        same_subnet = self._same_subnet(config.remote_ip, config.local_ip)
        return [
            self._check("remote/local IP 配置", bool(config.remote_ip and config.local_ip), "blocker", f"remote={config.remote_ip}, local={config.local_ip}"),
            self._check("直连网段一致性", same_subnet, "warning", f"remote={config.remote_ip}, local={config.local_ip}"),
            self._check("主线链路", config.preferred_link == "wired_direct", "blocker", f"preferred_link={config.preferred_link}"),
        ]

    @staticmethod
    def _check(name: str, ok: bool, severity: str, detail: str) -> DoctorCheck:
        return DoctorCheck(name=name, ok=bool(ok), severity=severity, detail=detail)

    @staticmethod
    def _same_subnet(remote_ip: str, local_ip: str) -> bool:
        try:
            remote = IPv4Address(remote_ip)
            local = IPv4Address(local_ip)
        except Exception:
            return False
        return remote.packed[:3] == local.packed[:3]
