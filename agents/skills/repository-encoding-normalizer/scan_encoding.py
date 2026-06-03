# -*- coding: utf-8 -*-
"""
仓库编码扫描工具
扫描指定目录下所有文本文件，检测原始编码，识别中文字符位置（注释 vs 字符串字面量）。

用法：
    python scan_encoding.py [--root REPO_ROOT] [--out encoding_audit.md]

输出：encoding_audit.md（编码审计报告）
"""
import argparse
import codecs
import os
from pathlib import Path
import json


def get_default_args():
    parser = argparse.ArgumentParser(description="Scan repository text files for encoding and Chinese text locations.")
    parser.add_argument("--root", default=".", help="Repository root directory (default: current directory)")
    parser.add_argument("--out", default="encoding_audit.md", help="Output report file (default: encoding_audit.md)")
    parser.add_argument("--json-out", default="", help="Optional machine-readable JSON audit output path")
    parser.add_argument("--exts", default=".c,.h,.s,.S,.mk,.txt,.bat,.cmd", help="Comma-separated file extensions to scan")
    parser.add_argument(
        "--exclude",
        default="stm32lib,stm32usb,ucos2,Libraries,__pycache__,.git,firmware,release,releases,dist,out,bin,build,.vscode",
        help="Comma-separated directory names to exclude",
    )
    return parser.parse_args()


def should_scan(rel_path, target_exts, exclude_dirs):
    parts = rel_path.replace("\\", "/").split("/")
    for part in parts[:-1]:
        if part in exclude_dirs:
            return False
    _, ext = os.path.splitext(rel_path)
    return ext.lower() in target_exts


def detect_encoding(data):
    if data.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        return "utf-16"
    for encoding in ("utf-8", "gbk", "big5"):
        try:
            data.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    scored = []
    for encoding in ("gbk", "big5"):
        try:
            text = data.decode(encoding, errors="replace")
        except Exception:
            continue
        replacement_count = text.count("\ufffd")
        chinese_count = sum(1 for ch in text if is_chinese_char(ch))
        scored.append((encoding, chinese_count, replacement_count))
    if scored:
        scored.sort(key=lambda item: (-item[1], item[2]))
        best_encoding, best_chinese_count, best_replacement_count = scored[0]
        # 容错策略：当严格解码失败，但按历史本地编码容错解码后仍能恢复大量中文，
        # 应优先按该编码继续扫描，而不是直接退化成 latin-1 把整文件排除出审计结果。
        if best_chinese_count >= 8 and best_replacement_count <= max(16, len(data) // 4096):
            return f"{best_encoding}-lossy"
    return "latin-1"


def is_chinese_char(ch):
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF) or (0x3400 <= cp <= 0x4DBF) or (0xF900 <= cp <= 0xFAFF)


# 编码敏感的特殊符号：这些字符在 GBK/UTF-8 间有不同的字节表示，
# 编码转换时容易遗漏或损坏。涵盖度数、数学、希腊字母、箭头、货币等。
_SPECIAL_RANGES = [
    (0x00A0, 0x00FF),   # Latin-1 Supplement: ° ± ² ³ ´ µ ¶ · × ÷ £ ¥ § © ®
    (0x0370, 0x03FF),   # Greek: Α Β Γ Δ ... Ω α β γ δ ... ω
    (0x2000, 0x206F),   # General Punctuation: – — … ※
    (0x2070, 0x209F),   # Superscripts/Subscripts: ⁰ ⁱ ⁴ ₀ ₁
    (0x20A0, 0x20CF),   # Currency Symbols: € ₠ ₡ ₢ ₣ ₤ ₥ ₦ ₧ ₨ ₩ ₪ ₫
    (0x2100, 0x214F),   # Letterlike Symbols: ℃ ℉ № ℡
    (0x2150, 0x218F),   # Number Forms: ⅓ ⅔ ⅛ ⅜
    (0x2190, 0x21FF),   # Arrows: ← ↑ → ↓ ↔ ↕
    (0x2200, 0x22FF),   # Mathematical Operators: ∀ ∂ ∃ ∀ ∑ − ∕ ∙ √ ∞ ∟ ∠ ∣ ∥
    (0x2260, 0x22FF),   # (subset of math ops, covered above)
    (0x2300, 0x23FF),   # Miscellaneous Technical: ⌂ ⌃ ⌄
    (0x2460, 0x24FF),   # Enclosed Alphanumerics: ① ② ③
    (0x2500, 0x257F),   # Box Drawing: ─ │ ┌ ┐
    (0x2580, 0x259F),   # Block Elements: ▀ ▄ █ ▌
    (0x25A0, 0x25FF),   # Geometric Shapes: ■ □ ▪ ▫ ▬ ▭ ▮ ▯ ▰ ▱ ▲ △ ▴ ▵ ▶ ▷
    (0x2600, 0x26FF),   # Miscellaneous Symbols: ☀ ☁ ★ ☆ ☎ ☏ ☐
    (0x3000, 0x303F),   # CJK Symbols/Punctuation: 、 。 〃 々 〆
    (0xFF00, 0xFFEF),   # Halfwidth/Fullwidth Forms: ！ ＂ ＃ ＄ ％ ＆ ＇
]

# 额外点状列表（不在范围覆盖内的常用单字符）
_EXTRA_SPECIAL_CHARS = set("～‖〓")

def is_special_char(ch):
    """检测编码敏感的非 ASCII 特殊符号（非 CJK 汉字）。"""
    cp = ord(ch)
    if cp <= 0x7F:
        return False
    # 排除 CJK 汉字本体（由 is_chinese_char 单独识别）
    if is_chinese_char(ch):
        return False
    # 排除全角 CJK 标点范围内的常见中文标点（这些跟汉字一样处理）
    if 0x3000 <= cp <= 0x303F:
        return False
    if 0xFF00 <= cp <= 0xFF5E:  # 全角字母数字（Ｆｕｌｌｗｉｄｔｈ）
        return False
    # 检查是否在编码敏感范围内
    for lo, hi in _SPECIAL_RANGES:
        if lo <= cp <= hi:
            return True
    return ch in _EXTRA_SPECIAL_CHARS


def is_notable_char(ch):
    """综合检测：中文 或 编码敏感特殊符号。"""
    return is_chinese_char(ch) or is_special_char(ch)


def classify_file(summary):
    has_comment = summary["comment"] > 0
    has_string = summary["string"] > 0
    has_code = summary["code"] > 0
    has_special_string = summary.get("special_string", 0) > 0
    has_special_comment = summary.get("special_comment", 0) > 0
    has_special_code = summary.get("special_code", 0) > 0
    # 特殊符号在运行期字符串中同样重要
    if (has_string or has_special_string) and (has_comment or has_special_comment):
        return "mixed_comment_and_runtime"
    if has_string or has_special_string:
        return "string_or_runtime"
    if (has_comment or has_special_comment) and (has_code or has_special_code):
        return "mixed_comment_and_code"
    if has_comment or has_special_comment:
        return "comment_only"
    if has_code or has_special_code:
        return "code_only_needs_review"
    return "no_notable_chars"


def finalize_line(lines, line_no, chars):
    if not chars:
        return
    text = "".join(chars)
    lines.append((line_no, text.rstrip("\r"), analyze_line_text(text)))


def analyze_line_text(text):
    results = []
    state = "code"
    quote = None
    i = 0
    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if state == "code":
            if ch == "/" and nxt == "/":
                state = "line_comment"
                i += 1
            elif ch == "/" and nxt == "*":
                state = "block_comment"
                i += 1
            elif ch in ('"', "'"):
                state = "string"
                quote = ch
            elif is_chinese_char(ch):
                results.append((i, ch, "code"))
            elif is_special_char(ch):
                results.append((i, ch, "special_code"))
        elif state == "string":
            if ch == "\\" and i + 1 < len(text):
                i += 1
            elif ch == quote:
                state = "code"
                quote = None
            elif is_chinese_char(ch):
                results.append((i, ch, "string"))
            elif is_special_char(ch):
                results.append((i, ch, "special_string"))
        elif state == "line_comment":
            if is_chinese_char(ch):
                results.append((i, ch, "comment"))
            elif is_special_char(ch):
                results.append((i, ch, "special_comment"))
        elif state == "block_comment":
            if ch == "*" and nxt == "/":
                state = "code"
                i += 1
            elif is_chinese_char(ch):
                results.append((i, ch, "comment"))
            elif is_special_char(ch):
                results.append((i, ch, "special_comment"))
        i += 1
    return results


def analyze_text(text):
    lines = []
    summary = {"comment": 0, "string": 0, "code": 0,
               "special_comment": 0, "special_string": 0, "special_code": 0}
    state = "code"
    quote = None
    current_line = []
    line_hits = []
    line_no = 1
    i = 0

    while i < len(text):
        ch = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        current_line.append(ch)

        if state == "code":
            if ch == "/" and nxt == "/":
                state = "line_comment"
            elif ch == "/" and nxt == "*":
                state = "block_comment"
            elif ch in ('"', "'"):
                state = "string"
                quote = ch
            elif is_chinese_char(ch):
                line_hits.append((len(current_line) - 1, ch, "code"))
                summary["code"] += 1
            elif is_special_char(ch):
                line_hits.append((len(current_line) - 1, ch, "special_code"))
                summary["special_code"] += 1
        elif state == "string":
            if ch == "\\" and i + 1 < len(text):
                current_line.append(nxt)
                i += 1
            elif ch == quote:
                state = "code"
                quote = None
            elif is_chinese_char(ch):
                line_hits.append((len(current_line) - 1, ch, "string"))
                summary["string"] += 1
            elif is_special_char(ch):
                line_hits.append((len(current_line) - 1, ch, "special_string"))
                summary["special_string"] += 1
        elif state == "line_comment":
            if is_chinese_char(ch):
                line_hits.append((len(current_line) - 1, ch, "comment"))
                summary["comment"] += 1
            elif is_special_char(ch):
                line_hits.append((len(current_line) - 1, ch, "special_comment"))
                summary["special_comment"] += 1
        elif state == "block_comment":
            if ch == "*" and nxt == "/":
                state = "code"
            elif is_chinese_char(ch):
                line_hits.append((len(current_line) - 1, ch, "comment"))
                summary["comment"] += 1
            elif is_special_char(ch):
                line_hits.append((len(current_line) - 1, ch, "special_comment"))
                summary["special_comment"] += 1

        if ch == "\n":
            if line_hits:
                lines.append((line_no, "".join(current_line).rstrip("\n").rstrip("\r"), list(line_hits)))
            current_line = []
            line_hits = []
            line_no += 1
            if state == "line_comment":
                state = "code"
        i += 1

    if current_line and line_hits:
        lines.append((line_no, "".join(current_line).rstrip("\r"), list(line_hits)))

    has_notable = any(summary.values())
    return {
        "has_notable": has_notable,
        "lines": lines,
        "summary": summary,
        "file_class": classify_file(summary),
    }


def write_markdown_report(results, out_path):
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("# 仓库原始编码审计\n\n")
        fh.write("| 文件路径 | 原始编码 | 文件分类 | 含中文+特殊符号行数 | 中文:字符串/注释/代码 | 特殊符号:字符串/注释/代码 |\n")
        fh.write("|---|---|---|---|---|---|\n")
        for result in results:
            summary = result["summary"]
            spe_str = summary.get("special_string", 0)
            spe_cmt = summary.get("special_comment", 0)
            spe_cod = summary.get("special_code", 0)
            fh.write(
                f"| {result['path']} | {result['encoding']} | {result['file_class']} | "
                f"{len(result['lines'])} | {summary['string']}/{summary['comment']}/{summary['code']} | "
                f"{spe_str}/{spe_cmt}/{spe_cod} |\n"
            )

        fh.write("\n\n## 文件分类说明\n\n")
        fh.write("- `comment_only`: 只有注释含中文或特殊符号，可优先视为注释保留类文件。\n")
        fh.write("- `string_or_runtime`: 含字符串字面量中文或编码敏感的特殊符号(如℃°±→)，优先视为运行期文本候选。\n")
        fh.write("- `mixed_comment_and_runtime`: 同时含注释中文/特殊符号和字符串中文/特殊符号。\n")
        fh.write("- `mixed_comment_and_code`: 注释区和代码区均有中文或特殊符号，需人工复核。\n")
        fh.write("- `code_only_needs_review`: 中文或特殊符号落在代码区，通常异常，需人工复核。\n")
        fh.write("\n> **注意**: 特殊符号列统计的是编码敏感的非 ASCII 符号，如 ℃、°、±、×、÷、μ、Ω、→、★ 等。\n")
        fh.write("> 这些符号在 GBK/UTF-8 间字节表示不同，编码转换时需同步处理。\n")

        fh.write("\n## 详细清单\n\n")
        for result in results:
            fh.write(f"\n### {result['path']} (原始编码: {result['encoding']}, 分类: {result['file_class']})\n\n")
            for line_no, line_text, hits in result["lines"]:
                counts = {}
                for _, _, loc in hits:
                    counts[loc] = counts.get(loc, 0) + 1
                loc_str = ", ".join(f"{name}:{count}" for name, count in sorted(counts.items()))
                fh.write(f"**Line {line_no}** ({loc_str}): `{line_text}`\n\n")


def write_json_report(results, out_path):
    payload = {"results": results}
    Path(out_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    args = get_default_args()
    repo_root = os.path.abspath(args.root)
    target_exts = set("." + item.strip().lstrip(".").lower() for item in args.exts.split(","))
    exclude_dirs = set(item.strip() for item in args.exclude.split(",") if item.strip())

    files = []
    for root, dirs, filenames in os.walk(repo_root):
        dirs[:] = [name for name in dirs if name not in exclude_dirs]
        for fname in filenames:
            full = os.path.join(root, fname)
            rel = os.path.relpath(full, repo_root)
            if should_scan(rel, target_exts, exclude_dirs):
                files.append(rel)

    results = []
    for rel in sorted(files):
        full = os.path.join(repo_root, rel)
        with open(full, "rb") as fh:
            data = fh.read()
        if not data:
            continue
        encoding = detect_encoding(data)
        try:
            if encoding.endswith("-lossy"):
                text = data.decode(encoding[:-6], errors="replace")
            else:
                text = data.decode(encoding)
        except Exception as exc:
            print(f"WARN: cannot decode {rel} with {encoding}: {exc}")
            continue
        analyzed = analyze_text(text)
        if analyzed["has_notable"]:
            results.append(
                {
                    "path": rel.replace("\\", "/"),
                    "encoding": encoding,
                    "lines": analyzed["lines"],
                    "summary": analyzed["summary"],
                    "file_class": analyzed["file_class"],
                }
            )

    out_path = Path(repo_root) / args.out
    write_markdown_report(results, out_path)
    if args.json_out:
        write_json_report(results, Path(repo_root) / args.json_out)
    print(f"Scanned {len(files)} files, found {len(results)} files with Chinese characters or special symbols.")
    print(f"Report written to {out_path}")


if __name__ == "__main__":
    main()
