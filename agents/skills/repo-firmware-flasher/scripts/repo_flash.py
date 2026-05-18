#!/usr/bin/env python3
"""Repository-driven firmware flashing helper for Windows USBPRINT devices.

Open serial logging before real flashing when the device may reboot or emit
short-lived startup logs needed for judging the result.
"""

from __future__ import annotations

import argparse
import configparser
import ctypes
import os
import struct
import sys
import time
import winreg
import zlib
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

    def first_non_empty(*values, fallback=""):
        for value in values:
            if value is None:
                continue
            if isinstance(value, str):
                if value.strip():
                    return value
            else:
                return value
        return fallback

    cfg = {
        "config_path": path,
        "transport": first_non_empty(
            get("device", "flash_transport", ""),
            get("device", "boot_transport", ""),
            get("device", "transport", "usbprint"),
        ).strip().lower(),
        "vid": first_non_empty(
            get("device", "flash_vid", ""),
            get("device", "boot_vid", ""),
            get("device", "vid", ""),
        ).strip().upper(),
        "pid": first_non_empty(
            get("device", "flash_pid", ""),
            get("device", "boot_pid", ""),
            get("device", "pid", ""),
        ).strip().upper(),
        "path_hint": first_non_empty(
            get("device", "flash_path_hint", ""),
            get("device", "boot_path_hint", ""),
            get("device", "path_hint", ""),
        ).strip(),
        "firmware": first_non_empty(
            get("firmware", "firmware", ""),
            get("firmware", "artifact_path", ""),
        ).strip(),
        "artifact_type": get("firmware", "artifact_type", "auto").strip().lower(),
        "allow_raw": parse_bool(get("firmware", "allow_raw", "false")),
        "header_size": int(get("firmware", "header_size", "12")),
        "chunk_size": int(first_non_empty(get("firmware", "chunk_size", ""), get("protocol", "chunk_size", "8192"))),
        "crc_type": first_non_empty(
            get("firmware", "crc_type", ""),
            get("protocol", "crc_type", "crc32_init_ffffffff"),
        ).strip().lower(),
        "command_prefix": bytes.fromhex(get("protocol", "command_prefix_hex", "")),
        "pack_length_command": decode_escaped_ascii(get("protocol", "pack_length_command", "")),
        "ota_command": decode_escaped_ascii(get("protocol", "ota_command", "")),
        "query_pack_length": parse_bool(get("protocol", "query_pack_length", "true"), True),
        "query_response_length": int(get("protocol", "query_response_length", "4")),
        "ack_prefix": bytes.fromhex(get("protocol", "ack_prefix_hex", "")),
        "ack_length": int(get("protocol", "ack_length", "8")),
        "ack_offset_pos": int(get("protocol", "ack_offset_pos", "3")),
        "ack_status_pos": int(get("protocol", "ack_status_pos", "7")),
        "ack_endian": get("protocol", "ack_endian", "little").strip().lower(),
        "delay": float(get("protocol", "delay", "0.05")),
        "query_retries": int(get("protocol", "query_retries", "2")),
        "query_settle_delay": float(get("protocol", "query_settle_delay", "0.2")),
        "io_timeout_ms": int(get("protocol", "io_timeout_ms", "5000")),
    }
    validate_config(cfg)
    return cfg


def validate_config(cfg: dict) -> None:
    if cfg["transport"] != "usbprint":
        raise ValueError(f"unsupported transport: {cfg['transport']}")
    if not cfg["vid"] or not cfg["pid"]:
        raise ValueError("vid/pid must be provided in config")
    if cfg["header_size"] < 12:
        raise ValueError("header_size must be >= 12")
    if cfg["crc_type"] != "crc32_init_ffffffff":
        raise ValueError(f"unsupported crc_type: {cfg['crc_type']}")
    if cfg["ack_endian"] != "little":
        raise ValueError(f"unsupported ack_endian: {cfg['ack_endian']}")
    if cfg["query_pack_length"] and not cfg["pack_length_command"]:
        raise ValueError("pack_length_command is required when query_pack_length=true")
    if not cfg["ota_command"]:
        raise ValueError("ota_command is required")
    if not cfg["ack_prefix"]:
        raise ValueError("ack_prefix_hex is required")


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


def write_all(handle, data: bytes, timeout_ms: int = 5000):
    _ = timeout_ms
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
            time.sleep(0.05)
            continue
        data.extend(buf.raw[: read.value])
    return bytes(data)


def crc32_prt(data: bytes) -> int:
    return zlib.crc32(data, 0xFFFFFFFF) & 0xFFFFFFFF


def make_command(prefix: bytes, body: bytes) -> bytes:
    return prefix + body


def make_ota_packet(offset: int, payload: bytes, cfg: dict) -> bytes:
    if cfg["header_size"] != 12:
        raise ValueError("only 12-byte OTA header is currently supported")
    return struct.pack("<III", offset, len(payload), crc32_prt(payload)) + payload


def iter_ota_packets(data: bytes, chunk_size: int, cfg: dict):
    for offset in range(0, len(data), chunk_size):
        payload = data[offset : offset + chunk_size]
        yield offset, make_ota_packet(offset, payload, cfg)


def detect_artifact(data: bytes, cfg: dict) -> bool:
    artifact_type = cfg["artifact_type"]
    if artifact_type == "raw":
        return cfg["allow_raw"]
    if artifact_type == "packed":
        return True
    return cfg["allow_raw"] or len(data) > cfg["header_size"]


def create_artifact_dir(base: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = base / f"repo_flash_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def parse_ack(data: bytes, cfg: dict):
    if len(data) != cfg["ack_length"] or not data.startswith(cfg["ack_prefix"]):
        raise ValueError(f"unexpected ack frame: {data.hex(' ')}")
    offset = struct.unpack_from("<I", data, cfg["ack_offset_pos"])[0]
    status = data[cfg["ack_status_pos"]]
    return {"offset": offset, "status": status}


def query_pack_length(handle, cfg: dict, log: TextIO | None):
    query = make_command(cfg["command_prefix"], cfg["pack_length_command"])
    last_error = None
    for attempt in range(1, cfg["query_retries"] + 1):
        try:
            write_all(handle, query, cfg["io_timeout_ms"])
            time.sleep(cfg["query_settle_delay"])
            pack_length = struct.unpack(
                "<I", read_exact(handle, cfg["query_response_length"], cfg["io_timeout_ms"])
            )[0]
            log_line(log, f"queried_pack_length={pack_length} attempt={attempt}")
            return pack_length
        except (TimeoutError, OSError) as exc:
            last_error = exc
            log_line(log, f"pack_length_query_failed attempt={attempt} error={exc}")
            time.sleep(cfg["query_settle_delay"])
    raise last_error if last_error is not None else RuntimeError("pack length query failed")


def send_ota_transaction(handle, packet: bytes, cfg: dict):
    frame = make_command(cfg["command_prefix"], cfg["ota_command"]) + packet
    write_all(handle, frame, cfg["io_timeout_ms"])
    time.sleep(cfg["delay"])
    return frame


def resolve_firmware(args, cfg: dict) -> Path:
    firmware = args.firmware or cfg["firmware"]
    if not firmware:
        raise ValueError("firmware path is required")
    return Path(firmware)


def resolve_paths(cfg: dict) -> list[str]:
    paths = list(unique(iter_device_paths(cfg["vid"], cfg["pid"])))
    if cfg["path_hint"]:
        hinted = [path for path in paths if cfg["path_hint"].lower() in path.lower()]
        if hinted:
            return hinted
    return paths


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


def cmd_inspect(args):
    cfg = load_config(Path(args.config))
    firmware_path = resolve_firmware(args, cfg)
    data = firmware_path.read_bytes()
    print(f"path={firmware_path}")
    print(f"size={len(data)}")
    print(f"artifact_type={cfg['artifact_type']}")
    print(f"allow_raw={cfg['allow_raw']}")
    print(f"header_size={cfg['header_size']}")
    print(f"chunk_size={cfg['chunk_size']}")
    print(f"looks_flashable={detect_artifact(data, cfg)}")
    return 0


def cmd_make_packets(args):
    cfg = load_config(Path(args.config))
    firmware_path = resolve_firmware(args, cfg)
    data = firmware_path.read_bytes()
    out = Path(args.out)
    packet_blob = bytearray()
    for _, packet in iter_ota_packets(data, args.chunk_size or cfg["chunk_size"], cfg):
        if args.with_ota_command:
            packet_blob.extend(make_command(cfg["command_prefix"], cfg["ota_command"]))
        packet_blob.extend(packet)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(packet_blob)
    print(f"firmware={len(data)} bytes")
    print(f"chunk_size={args.chunk_size or cfg['chunk_size']}")
    print(f"packet_blob={out} {len(packet_blob)} bytes")
    print(f"with_ota_command={args.with_ota_command}")
    return 0


def cmd_flash(args):
    cfg = load_config(Path(args.config))
    if not args.yes:
        print("Refusing to flash without --yes.")
        return 2
    firmware_path = resolve_firmware(args, cfg)
    data = firmware_path.read_bytes()
    if not detect_artifact(data, cfg):
        print("artifact does not satisfy current config rules")
        print("check firmware.artifact_type / allow_raw / firmware path in cfg")
        return 2
    paths = resolve_paths(cfg)
    if not paths:
        print(f"No paths found for VID_{cfg['vid']}&PID_{cfg['pid']}")
        return 1
    path = args.path or paths[0]
    artifact_dir = create_artifact_dir(Path(args.artifacts_dir))
    log_path = artifact_dir / "session.log"
    ack_path = artifact_dir / "acks.log"
    handle = open_device(path)
    chunk_size = args.chunk_size or cfg["chunk_size"]
    with log_path.open("w", encoding="utf-8") as log_fp, ack_path.open("w", encoding="utf-8") as ack_fp:
        try:
            log_line(log_fp, f"config={cfg['config_path']}")
            log_line(log_fp, f"firmware={firmware_path}")
            log_line(log_fp, f"device_path={path}")
            log_line(log_fp, f"artifact_dir={artifact_dir}")
            if cfg["query_pack_length"] and not args.skip_query_pack_length:
                pack_length = query_pack_length(handle, cfg, log_fp)
            else:
                pack_length = chunk_size
                log_line(log_fp, "queried_pack_length=skipped")
            if chunk_size > pack_length:
                log_line(log_fp, f"chunk_size={chunk_size} exceeds pack_length={pack_length}")
                return 2
            for index, (offset, packet) in enumerate(iter_ota_packets(data, chunk_size, cfg), start=1):
                if args.max_packets and index > args.max_packets:
                    log_line(log_fp, f"stopped after --max-packets={args.max_packets}")
                    break
                frame = send_ota_transaction(handle, packet, cfg)
                log_line(log_fp, f"sent packet={index} offset={offset} payload={len(packet) - cfg['header_size']} frame={len(frame)}")
                ack = parse_ack(read_exact(handle, cfg["ack_length"], cfg["io_timeout_ms"]), cfg)
                ack_msg = f"ack packet={index} offset={ack['offset']} status={ack['status']}"
                log_line(log_fp, ack_msg)
                ack_fp.write(ack_msg + "\n")
                ack_fp.flush()
                if ack["offset"] != offset:
                    log_line(log_fp, f"unexpected ack offset expected={offset} actual={ack['offset']}")
                    return 1
                if ack["status"] != 0:
                    log_line(log_fp, "flash aborted on non-zero ack status")
                    return 1
        finally:
            CloseHandle(handle)
    print(f"logs={artifact_dir}")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        description="Repository-driven firmware flashing helper. Start serial capture before real flashing if reboot or startup logs matter."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("probe", help="probe matching device paths from repository-derived config")
    p.add_argument("--config", required=True)
    p.set_defaults(func=cmd_probe)

    p = sub.add_parser("inspect-firmware", help="inspect the configured firmware artifact without writing to the device")
    p.add_argument("--config", required=True)
    p.add_argument("firmware", nargs="?")
    p.set_defaults(func=cmd_inspect)

    p = sub.add_parser("make-packets", help="build OTA packet blobs from the firmware artifact")
    p.add_argument("--config", required=True)
    p.add_argument("firmware", nargs="?")
    p.add_argument("--out", required=True)
    p.add_argument("--chunk-size", type=int)
    p.add_argument("--with-ota-command", action="store_true")
    p.set_defaults(func=cmd_make_packets)

    p = sub.add_parser("flash", help="perform real flashing; open serial capture first if the device may reboot or emit key startup logs")
    p.add_argument("--config", required=True)
    p.add_argument("firmware", nargs="?")
    p.add_argument("--path")
    p.add_argument("--chunk-size", type=int)
    p.add_argument("--max-packets", type=int, default=0)
    p.add_argument("--skip-query-pack-length", action="store_true")
    p.add_argument("--artifacts-dir", default="artifacts")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_flash)

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
