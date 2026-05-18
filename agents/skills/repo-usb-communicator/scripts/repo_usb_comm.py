#!/usr/bin/env python3
"""Repository-driven USB communication helper for Windows USBPRINT devices.

Open serial logging before USB actions when the device may reboot, re-enumerate,
or emit short-lived startup logs that are needed for judging success.
"""

from __future__ import annotations

import argparse
import configparser
import ctypes
import os
import time
import winreg
from datetime import datetime
from pathlib import Path
from typing import TextIO

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

USBPRINT_GUID = "28d78fad-5a12-11d1-ae5b-0000-f803a8c2"
USB_DEVICE_GUID = "a5dcbf10-6530-11d2-901f-00c04fb951ed"

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
CreateFileW = kernel32.CreateFileW
CreateFileW.argtypes = [
    ctypes.c_wchar_p,
    ctypes.c_uint32,
    ctypes.c_uint32,
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.c_uint32,
    ctypes.c_void_p,
]
CreateFileW.restype = ctypes.c_void_p

WriteFile = kernel32.WriteFile
WriteFile.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint32),
    ctypes.c_void_p,
]
WriteFile.restype = ctypes.c_int

ReadFile = kernel32.ReadFile
ReadFile.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint32),
    ctypes.c_void_p,
]
ReadFile.restype = ctypes.c_int

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [ctypes.c_void_p]
CloseHandle.restype = ctypes.c_int


def parse_bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


def decode_escaped_ascii(value: str) -> bytes:
    return value.encode("utf-8").decode("unicode_escape").encode("ascii")


def load_config(path: Path) -> dict:
    parser = configparser.ConfigParser()
    if not parser.read(path, encoding="utf-8"):
        raise FileNotFoundError(f"config not found: {path}")

    def get(section: str, key: str, fallback=None):
        if parser.has_option(section, key):
            return parser.get(section, key)
        return fallback

    cfg = {
        "config_path": path,
        "transport": (
            get("device", "usb_transport", "")
            or get("device", "app_transport", "")
            or get("device", "transport", "usbprint")
        ).strip().lower(),
        "vid": (get("device", "usb_vid", "") or get("device", "app_vid", "") or get("device", "vid", "")).strip().upper(),
        "pid": (get("device", "usb_pid", "") or get("device", "app_pid", "") or get("device", "pid", "")).strip().upper(),
        "path_hint": (get("device", "usb_path_hint", "") or get("device", "app_path_hint", "") or get("device", "path_hint", "")).strip(),
        "command_prefix": bytes.fromhex(get("protocol", "command_prefix_hex", "")),
        "default_mode": get("usb_comm", "default_mode", "text").strip().lower(),
        "default_payload_hex": get("usb_comm", "default_payload_hex", "").strip(),
        "default_text": get("usb_comm", "default_text", ""),
        "text_encoding": get("usb_comm", "text_encoding", "ascii").strip(),
        "append_crlf": parse_bool(get("usb_comm", "append_crlf", "false")),
        "read_length": int(get("usb_comm", "read_length", "0")),
        "read_timeout_ms": int(get("usb_comm", "read_timeout_ms", "3000")),
        "request_delay": float(get("usb_comm", "request_delay", "0.05")),
    }
    validate_config(cfg)
    return cfg


def validate_config(cfg: dict) -> None:
    if cfg["transport"] != "usbprint":
        raise ValueError(f"unsupported transport: {cfg['transport']}")
    if not cfg["vid"] or not cfg["pid"]:
        raise ValueError("vid/pid must be provided in config")
    if cfg["default_mode"] not in {"text", "hex"}:
        raise ValueError(f"unsupported default_mode: {cfg['default_mode']}")


def log_line(log: TextIO | None, message: str) -> None:
    print(message)
    if log is not None:
        log.write(message + "\n")
        log.flush()


def normalize_symbolic_name(value: str) -> str:
    if value.startswith("\\??\\"):
        return "\\\\?\\" + value[4:]
    if value.startswith("\\\\?\\"):
        return value
    return value


def walk_registry_for_paths(key, key_path: str, needle: str):
    try:
        symbolic, _ = winreg.QueryValueEx(key, "SymbolicName")
        if needle in symbolic.upper():
            yield normalize_symbolic_name(symbolic)
    except FileNotFoundError:
        pass

    if "##?#" in key_path and needle in key_path.upper():
        suffix = key_path.rsplit("\\", 1)[-1]
        if suffix.startswith("##?#"):
            yield "\\\\?\\" + suffix[4:]

    index = 0
    while True:
        try:
            sub = winreg.EnumKey(key, index)
        except OSError:
            break
        index += 1
        try:
            with winreg.OpenKey(key, sub) as child:
                yield from walk_registry_for_paths(child, key_path + "\\" + sub, needle)
        except OSError:
            continue


def iter_device_paths(vid: str, pid: str):
    needle = f"VID_{vid.upper()}&PID_{pid.upper()}"
    roots = [
        rf"SYSTEM\CurrentControlSet\Enum\USB\{needle}",
        rf"SYSTEM\CurrentControlSet\Control\DeviceClasses\{{{USBPRINT_GUID}}}",
        rf"SYSTEM\CurrentControlSet\Control\DeviceClasses\{{{USB_DEVICE_GUID}}}",
    ]
    for root in roots:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, root) as key:
                yield from walk_registry_for_paths(key, root, needle)
        except FileNotFoundError:
            continue


def unique(items):
    seen = set()
    for item in items:
        low = item.lower()
        if low not in seen:
            seen.add(low)
            yield item


def resolve_paths(cfg: dict) -> list[str]:
    paths = list(unique(iter_device_paths(cfg["vid"], cfg["pid"])))
    if cfg["path_hint"]:
        hinted = [path for path in paths if cfg["path_hint"].lower() in path.lower()]
        if hinted:
            return hinted
    return paths


def open_device(path: str):
    handle = CreateFileW(
        path,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    if handle == INVALID_HANDLE_VALUE:
        err = ctypes.get_last_error()
        raise OSError(err, f"CreateFile failed for {path}")
    return handle


def write_all(handle, data: bytes):
    buf = ctypes.create_string_buffer(data)
    written = ctypes.c_uint32(0)
    ok = WriteFile(handle, buf, len(data), ctypes.byref(written), None)
    if not ok:
        err = ctypes.get_last_error()
        raise OSError(err, "WriteFile failed")
    if written.value != len(data):
        raise OSError(0, f"WriteFile wrote {written.value}/{len(data)} bytes")


def read_exact(handle, size: int, timeout_ms: int) -> bytes:
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    data = bytearray()
    while len(data) < size:
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Read timed out waiting for {size} bytes")
        chunk_size = size - len(data)
        buf = ctypes.create_string_buffer(chunk_size)
        read = ctypes.c_uint32(0)
        ok = ReadFile(handle, buf, chunk_size, ctypes.byref(read), None)
        if not ok:
            err = ctypes.get_last_error()
            raise OSError(err, "ReadFile failed")
        if read.value == 0:
            time.sleep(0.02)
            continue
        data.extend(buf.raw[: read.value])
    return bytes(data)


def read_until_idle(handle, timeout_ms: int, idle_timeout_ms: int, max_length: int = 0) -> bytes:
    deadline = time.monotonic() + (timeout_ms / 1000.0)
    idle_deadline = None
    data = bytearray()
    while True:
        now = time.monotonic()
        if now >= deadline:
            break
        if idle_deadline is not None and now >= idle_deadline:
            break
        if max_length > 0 and len(data) >= max_length:
            break

        chunk_size = 256
        if max_length > 0:
            chunk_size = min(chunk_size, max_length - len(data))
            if chunk_size <= 0:
                break

        buf = ctypes.create_string_buffer(chunk_size)
        read = ctypes.c_uint32(0)
        ok = ReadFile(handle, buf, chunk_size, ctypes.byref(read), None)
        if not ok:
            err = ctypes.get_last_error()
            raise OSError(err, "ReadFile failed")
        if read.value == 0:
            time.sleep(0.02)
            continue
        data.extend(buf.raw[: read.value])
        idle_deadline = time.monotonic() + (idle_timeout_ms / 1000.0)
    return bytes(data)


def create_artifact_dir(base: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = base / f"repo_usb_comm_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def build_payload(args, cfg: dict) -> bytes:
    if args.hex:
        body = bytes.fromhex(args.hex)
    elif args.text is not None:
        body = args.text.encode(args.encoding or cfg["text_encoding"])
    elif cfg["default_mode"] == "hex" and cfg["default_payload_hex"]:
        body = bytes.fromhex(cfg["default_payload_hex"])
    else:
        body = cfg["default_text"].encode(args.encoding or cfg["text_encoding"])

    if args.append_crlf or (args.append_crlf is None and cfg["append_crlf"]):
        body += b"\r\n"
    if args.no_prefix:
        return body
    return cfg["command_prefix"] + body


def cmd_probe(args):
    cfg = load_config(Path(args.config))
    paths = resolve_paths(cfg)
    if not paths:
        print(f"No paths found for VID_{cfg['vid']}&PID_{cfg['pid']}")
        return 1
    for path in paths:
        print(f"path={path}")
        try:
            handle = open_device(path)
        except OSError as exc:
            print(f"open=failed {exc}")
        else:
            print("open=ok")
            CloseHandle(handle)
    return 0


def cmd_open(args):
    cfg = load_config(Path(args.config))
    paths = resolve_paths(cfg)
    if not paths:
        print(f"No paths found for VID_{cfg['vid']}&PID_{cfg['pid']}")
        return 1
    path = args.path or paths[0]
    handle = open_device(path)
    CloseHandle(handle)
    print(f"open=ok path={path}")
    return 0


def cmd_send(args):
    cfg = load_config(Path(args.config))
    paths = resolve_paths(cfg)
    if not paths:
        print(f"No paths found for VID_{cfg['vid']}&PID_{cfg['pid']}")
        return 1
    path = args.path or paths[0]
    payload = build_payload(args, cfg)
    artifact_dir = create_artifact_dir(Path(args.artifacts_dir))
    log_path = artifact_dir / "session.log"
    handle = open_device(path)
    with log_path.open("w", encoding="utf-8") as log_fp:
        try:
            log_line(log_fp, f"config={cfg['config_path']}")
            log_line(log_fp, f"device_path={path}")
            log_line(log_fp, f"tx_len={len(payload)}")
            log_line(log_fp, f"tx_hex={payload.hex(' ')}")
            write_all(handle, payload)
            log_line(log_fp, "send=ok")
        finally:
            CloseHandle(handle)
    print(f"logs={artifact_dir}")
    return 0


def cmd_request(args):
    cfg = load_config(Path(args.config))
    paths = resolve_paths(cfg)
    if not paths:
        print(f"No paths found for VID_{cfg['vid']}&PID_{cfg['pid']}")
        return 1
    path = args.path or paths[0]
    payload = build_payload(args, cfg)
    read_length = args.read_length if args.read_length is not None else cfg["read_length"]
    if read_length <= 0:
        print("read_length must be > 0 for request")
        return 2
    artifact_dir = create_artifact_dir(Path(args.artifacts_dir))
    log_path = artifact_dir / "session.log"
    handle = open_device(path)
    with log_path.open("w", encoding="utf-8") as log_fp:
        try:
            log_line(log_fp, f"config={cfg['config_path']}")
            log_line(log_fp, f"device_path={path}")
            log_line(log_fp, f"tx_len={len(payload)}")
            log_line(log_fp, f"tx_hex={payload.hex(' ')}")
            write_all(handle, payload)
            time.sleep(args.request_delay if args.request_delay is not None else cfg["request_delay"])
            rx = read_exact(handle, read_length, args.read_timeout_ms or cfg["read_timeout_ms"])
            log_line(log_fp, f"rx_len={len(rx)}")
            log_line(log_fp, f"rx_hex={rx.hex(' ')}")
            if args.print_text:
                try:
                    print(rx.decode(args.encoding or cfg["text_encoding"], errors="replace"))
                except LookupError:
                    print(rx.decode("utf-8", errors="replace"))
        finally:
            CloseHandle(handle)
    print(f"logs={artifact_dir}")
    return 0


def cmd_exchange(args):
    cfg = load_config(Path(args.config))
    paths = resolve_paths(cfg)
    if not paths:
        print(f"No paths found for VID_{cfg['vid']}&PID_{cfg['pid']}")
        return 1
    path = args.path or paths[0]
    payload = build_payload(args, cfg)
    artifact_dir = create_artifact_dir(Path(args.artifacts_dir))
    log_path = artifact_dir / "session.log"
    handle = open_device(path)
    with log_path.open("w", encoding="utf-8") as log_fp:
        try:
            log_line(log_fp, f"config={cfg['config_path']}")
            log_line(log_fp, f"device_path={path}")
            log_line(log_fp, f"tx_len={len(payload)}")
            log_line(log_fp, f"tx_hex={payload.hex(' ')}")
            write_all(handle, payload)
            time.sleep(args.request_delay if args.request_delay is not None else cfg["request_delay"])
            rx = read_until_idle(
                handle,
                args.read_timeout_ms or cfg["read_timeout_ms"],
                args.idle_timeout_ms,
                args.max_read_length or 0,
            )
            log_line(log_fp, f"rx_len={len(rx)}")
            log_line(log_fp, f"rx_hex={rx.hex(' ')}")
            if args.print_text:
                try:
                    print(rx.decode(args.encoding or cfg["text_encoding"], errors="replace"))
                except LookupError:
                    print(rx.decode("utf-8", errors="replace"))
        finally:
            CloseHandle(handle)
    print(f"logs={artifact_dir}")
    return 0


def cmd_read(args):
    cfg = load_config(Path(args.config))
    paths = resolve_paths(cfg)
    if not paths:
        print(f"No paths found for VID_{cfg['vid']}&PID_{cfg['pid']}")
        return 1
    path = args.path or paths[0]
    artifact_dir = create_artifact_dir(Path(args.artifacts_dir))
    log_path = artifact_dir / "session.log"
    handle = open_device(path)
    with log_path.open("w", encoding="utf-8") as log_fp:
        try:
            log_line(log_fp, f"config={cfg['config_path']}")
            log_line(log_fp, f"device_path={path}")
            rx = read_until_idle(
                handle,
                args.read_timeout_ms or cfg["read_timeout_ms"],
                args.idle_timeout_ms,
                args.max_read_length or 0,
            )
            log_line(log_fp, f"rx_len={len(rx)}")
            log_line(log_fp, f"rx_hex={rx.hex(' ')}")
            if args.print_text:
                try:
                    print(rx.decode(args.encoding or cfg["text_encoding"], errors="replace"))
                except LookupError:
                    print(rx.decode("utf-8", errors="replace"))
        finally:
            CloseHandle(handle)
    print(f"logs={artifact_dir}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Repository-driven USB communication helper. Start serial capture before USB actions that may reboot, re-enumerate, or change device state."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe", help="probe matching USB device paths from repository-derived config")
    p.add_argument("--config", required=True)
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("open", help="verify the configured USB device can be opened")
    p.add_argument("--config", required=True)
    p.add_argument("--path")
    p.set_defaults(func=cmd_open)

    def add_payload_args(p):
        p.add_argument("--config", required=True)
        p.add_argument("--path")
        p.add_argument("--text")
        p.add_argument("--hex")
        p.add_argument("--encoding")
        p.add_argument("--append-crlf", dest="append_crlf", action="store_true", default=None)
        p.add_argument("--no-append-crlf", dest="append_crlf", action="store_false")
        p.add_argument("--no-prefix", action="store_true")

    p = sub.add_parser("send", help="send a USB command without reading a response")
    add_payload_args(p)
    p.add_argument("--artifacts-dir", default="artifacts")
    p.set_defaults(func=cmd_send)

    p = sub.add_parser("request", help="send a USB command and read a fixed-length response; open serial capture first if device state may change")
    add_payload_args(p)
    p.add_argument("--read-length", type=int)
    p.add_argument("--read-timeout-ms", type=int)
    p.add_argument("--request-delay", type=float)
    p.add_argument("--print-text", action="store_true")
    p.add_argument("--artifacts-dir", default="artifacts")
    p.set_defaults(func=cmd_request)

    p = sub.add_parser("exchange", help="send a USB command and read until idle; open serial capture first if device state may change")
    add_payload_args(p)
    p.add_argument("--read-timeout-ms", type=int)
    p.add_argument("--idle-timeout-ms", type=int, default=200)
    p.add_argument("--max-read-length", type=int)
    p.add_argument("--request-delay", type=float)
    p.add_argument("--print-text", action="store_true")
    p.add_argument("--artifacts-dir", default="artifacts")
    p.set_defaults(func=cmd_exchange)

    p = sub.add_parser("read", help="read current USB device output without sending a new command")
    p.add_argument("--config", required=True)
    p.add_argument("--path")
    p.add_argument("--encoding")
    p.add_argument("--read-timeout-ms", type=int)
    p.add_argument("--idle-timeout-ms", type=int, default=200)
    p.add_argument("--max-read-length", type=int)
    p.add_argument("--print-text", action="store_true")
    p.add_argument("--artifacts-dir", default="artifacts")
    p.set_defaults(func=cmd_read)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if os.name != "nt":
        print("This helper requires Windows.")
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
