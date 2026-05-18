#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def now_stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_cmd(command: list[str], cwd: Optional[Path], log_path: Path) -> Dict[str, Any]:
    start = time.time()
    proc = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    elapsed = round(time.time() - start, 3)
    payload = {
        "command": command,
        "cwd": str(cwd) if cwd else None,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "elapsed_sec": elapsed,
    }
    log_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**payload, "log_path": str(log_path)}


def run_json_cmd(command: list[str], cwd: Optional[Path], log_path: Path) -> Dict[str, Any]:
    result = run_cmd(command, cwd, log_path)
    stdout = result.get("stdout", "")
    try:
        result["json"] = json.loads(stdout) if stdout.strip() else {}
    except json.JSONDecodeError:
        result["json"] = {
            "ok": False,
            "error_type": "invalid_json",
            "error_message": "stdout is not valid json",
            "stdout": stdout,
        }
    return result


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_serial_defaults(config_path: Path) -> Dict[str, Any]:
    parser = configparser.ConfigParser()
    if not parser.read(config_path, encoding="utf-8"):
        raise FileNotFoundError(f"config not found: {config_path}")
    if not parser.has_section("serial"):
        return {}

    def get(key: str, fallback: str = "") -> str:
        if parser.has_option("serial", key):
            return parser.get("serial", key)
        return fallback

    return {
        "port": get("port", "").strip(),
        "baudrate": int(get("baudrate", "115200")),
        "timeout": float(get("timeout", "1.0")),
        "parity": get("parity", "N").strip() or "N",
        "bytesize": int(get("bytesize", "8")),
        "stopbits": float(get("stopbits", "1.0")),
        "rtscts": parse_bool(get("rtscts", "false")),
        "dsrdtr": parse_bool(get("dsrdtr", "false")),
        "xonxoff": parse_bool(get("xonxoff", "false")),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generic embedded debug workflow orchestrator. "
            "Serial capture is opened before flash or USB actions. "
            "USB/test commands are expected to run serially; parallel command sending is forbidden unless the user explicitly requires it."
        )
    )
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--artifacts-dir", default="artifacts")
    parser.add_argument("--build-cmd", nargs="+")
    parser.add_argument("--flash-cmd", nargs="+")
    parser.add_argument("--device-config")
    parser.add_argument("--serial-tool")
    parser.add_argument("--serial-port")
    parser.add_argument("--serial-baudrate", type=int, default=115200)
    parser.add_argument("--serial-timeout", type=float, default=1.0)
    parser.add_argument("--serial-parity", default="N")
    parser.add_argument("--serial-bytesize", type=int, default=8)
    parser.add_argument("--serial-stopbits", type=float, default=1.0)
    parser.add_argument("--serial-rtscts", action="store_true")
    parser.add_argument("--serial-dsrdtr", action="store_true")
    parser.add_argument("--serial-xonxoff", action="store_true")
    parser.add_argument("--serial-start-delay", type=float, default=0.5)
    parser.add_argument("--serial-poll-interval", type=float, default=1.0)
    parser.add_argument("--serial-poll-count", type=int, default=3)
    parser.add_argument("--serial-peek-lines", type=int, default=80)
    parser.add_argument("--serial-cursor-name", default="orchestrator")
    parser.add_argument("--wait-text", action="append", default=[])
    parser.add_argument("--stop-after-text", action="append", default=[])
    parser.add_argument("--max-wait-seconds", type=float, default=0.0)
    parser.add_argument("--usb-after-text", action="append", default=[])
    parser.add_argument("--usb-cmd", nargs="+")
    parser.add_argument("--usb-delay", type=float, default=0.5)
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    artifacts_root = (workspace / args.artifacts_dir).resolve()
    run_dir = artifacts_root / f"debug_orchestrator_{now_stamp()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "summary.json"
    summary: Dict[str, Any] = {
        "ok": False,
        "run_dir": str(run_dir),
        "steps": [],
        "serial_session": None,
        "serial_polls": [],
        "serial_tool": None,
        "device_config": None,
    }

    if args.device_config:
        device_config = Path(args.device_config).resolve()
        serial_defaults = load_serial_defaults(device_config)
        summary["device_config"] = str(device_config)
        if not args.serial_port and serial_defaults.get("port"):
            args.serial_port = serial_defaults["port"]
        if args.serial_baudrate == 115200 and "baudrate" in serial_defaults:
            args.serial_baudrate = serial_defaults["baudrate"]
        if args.serial_timeout == 1.0 and "timeout" in serial_defaults:
            args.serial_timeout = serial_defaults["timeout"]
        if args.serial_parity == "N" and "parity" in serial_defaults:
            args.serial_parity = serial_defaults["parity"]
        if args.serial_bytesize == 8 and "bytesize" in serial_defaults:
            args.serial_bytesize = serial_defaults["bytesize"]
        if args.serial_stopbits == 1.0 and "stopbits" in serial_defaults:
            args.serial_stopbits = serial_defaults["stopbits"]
        if not args.serial_rtscts and serial_defaults.get("rtscts", False):
            args.serial_rtscts = True
        if not args.serial_dsrdtr and serial_defaults.get("dsrdtr", False):
            args.serial_dsrdtr = True
        if not args.serial_xonxoff and serial_defaults.get("xonxoff", False):
            args.serial_xonxoff = True

    skill_root = Path(__file__).resolve().parents[1]
    if args.serial_tool:
        serial_tool = Path(args.serial_tool).resolve()
    else:
        serial_tool = skill_root.parent / "serial-log-debug" / "serial_tool.py"
    if not serial_tool.exists():
        summary["error"] = (
            "serial_tool_not_found: provide --serial-tool when serial-log-debug is not located next to embedded-debug-workflow"
        )
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 6

    summary["serial_tool"] = str(serial_tool)

    if args.build_cmd:
        build_result = run_cmd(args.build_cmd, workspace, run_dir / "build.json")
        summary["steps"].append({"name": "build", **build_result})
        if build_result["returncode"] != 0:
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 2

    open_cmd = [
        sys.executable,
        str(serial_tool),
        "open",
        "--baudrate",
        str(args.serial_baudrate),
        "--timeout",
        str(args.serial_timeout),
        "--parity",
        args.serial_parity,
        "--bytesize",
        str(args.serial_bytesize),
        "--stopbits",
        str(args.serial_stopbits),
        "--output-dir",
        str(run_dir / "serial"),
    ]
    if args.serial_port:
        open_cmd.extend(["--port", args.serial_port])
    if args.serial_rtscts:
        open_cmd.append("--rtscts")
    if args.serial_dsrdtr:
        open_cmd.append("--dsrdtr")
    if args.serial_xonxoff:
        open_cmd.append("--xonxoff")

    open_result = run_json_cmd(open_cmd, workspace, run_dir / "serial_open.json")
    summary["serial_session"] = open_result.get("json", {})
    if open_result["returncode"] != 0 or not summary["serial_session"].get("ok", False):
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 4

    session_path = summary["serial_session"]["session_path"]
    time.sleep(args.serial_start_delay)

    if args.flash_cmd:
        flash_result = run_cmd(args.flash_cmd, workspace, run_dir / "flash.json")
        summary["steps"].append({"name": "flash", **flash_result})
        if flash_result["returncode"] != 0:
            stop_cmd = [sys.executable, str(serial_tool), "stop", "--session-path", session_path]
            stop_result = run_json_cmd(stop_cmd, workspace, run_dir / "serial_stop.json")
            summary["serial_stop"] = stop_result.get("json", {})
            summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 3

    if args.usb_cmd:
        summary["usb_triggered"] = False

    waited_sec = 0.0
    matched_wait_text = None
    matched_stop_text = None
    usb_trigger_text = None

    for index in range(args.serial_poll_count):
        time.sleep(args.serial_poll_interval)
        waited_sec += args.serial_poll_interval
        status_cmd = [sys.executable, str(serial_tool), "status", "--session-path", session_path]
        read_cmd = [
            sys.executable,
            str(serial_tool),
            "read-new",
            "--session-path",
            session_path,
            "--cursor-name",
            args.serial_cursor_name,
            "--max-lines",
            str(args.serial_peek_lines),
        ]
        status_result = run_json_cmd(status_cmd, workspace, run_dir / f"serial_status_{index + 1}.json")
        read_result = run_json_cmd(read_cmd, workspace, run_dir / f"serial_read_new_{index + 1}.json")
        new_lines = read_result.get("json", {}).get("new_lines", []) or []
        joined_new = "\n".join(new_lines)

        for token in args.wait_text:
            if token and token in joined_new:
                matched_wait_text = token
                break

        for token in args.stop_after_text:
            if token and token in joined_new:
                matched_stop_text = token
                break

        if args.usb_cmd and not summary.get("usb_triggered", False):
            should_trigger = False
            if not args.usb_after_text:
                should_trigger = index == 0
            else:
                for token in args.usb_after_text:
                    if token and token in joined_new:
                        should_trigger = True
                        usb_trigger_text = token
                        break
            if should_trigger:
                time.sleep(args.usb_delay)
                usb_result = run_cmd(args.usb_cmd, workspace, run_dir / "usb.json")
                summary["steps"].append({"name": "usb", **usb_result})
                summary["usb_triggered"] = True

        summary["serial_polls"].append(
            {
                "index": index + 1,
                "status": status_result.get("json", {}),
                "read_new": read_result.get("json", {}),
            }
        )
        if matched_stop_text:
            break
        if matched_wait_text:
            break
        if args.max_wait_seconds > 0 and waited_sec >= args.max_wait_seconds:
            break

    stop_cmd = [sys.executable, str(serial_tool), "stop", "--session-path", session_path]
    stop_result = run_json_cmd(stop_cmd, workspace, run_dir / "serial_stop.json")
    summary["serial_stop"] = stop_result.get("json", {})
    summary["matched_wait_text"] = matched_wait_text
    summary["matched_stop_text"] = matched_stop_text
    summary["usb_trigger_text"] = usb_trigger_text
    summary["waited_sec"] = waited_sec
    summary["ok"] = bool(
        summary["serial_session"].get("ok", False)
        and summary["serial_stop"].get("status") in {"stopped", "stop_requested"}
        and (not args.build_cmd or any(step["name"] == "build" and step["returncode"] == 0 for step in summary["steps"]))
        and (not args.flash_cmd or any(step["name"] == "flash" and step["returncode"] == 0 for step in summary["steps"]))
        and (not args.usb_cmd or any(step["name"] == "usb" and step["returncode"] == 0 for step in summary["steps"]))
    )

    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 5


if __name__ == "__main__":
    raise SystemExit(main())
