# -*- coding: utf-8 -*-
"""
编码转换后乱码巡检脚本。
对本次编码转换涉及的文件做快速静态扫描，辅助发现明显乱码迹象。

v2 新增：
- 编码往返验证（UTF-8 → gb18030 → 比对原始字节）
- 语义乱码检测（连续罕见 CJK 字符序列 — UTF-8 被 gb18030 错解的典型指纹）
- --deep 模式开启深度检测
"""
import argparse
import codecs
import os
import re
import sys
from pathlib import Path


SUSPICIOUS_TERMS = ("锟斤拷", "烫烫烫", "屯屯屯")
QUESTION_RUN_RE = re.compile(r"\?{2,}")
EXTENSIONS_WITHOUT_BOM = (".s", ".asm", ".inc")
STARTUP_TOKENS = ("startup_", "startup-", "_startup", "crt0", "vectors", "vector_table")
LITERAL_CONTEXT_MARKERS = (
    "SUSPICIOUS_TERMS =",
    "典型乱码片段",
    "连续 `?`",
    "`??`",
    "`???`",
)

# ============================================================
# 语义乱码检测：UTF-8 被 gb18030 错解的指纹
# ============================================================

# gb18030 将 UTF-8 字节错解后，会产生大量在正常中文文本中
# 极少连续出现的 CJK 字符。以下是高频错解字符的 Unicode 范围。
# 连续 4 个以上来自这些范围的字符 = 极大概率为语义乱码。

# 常见错解产生的字符范围（通过分析 UTF-8→gb18030 错解映射得出）
HIGH_RISK_RANGES = [
    (0x6D60, 0x6D99),   # 浠-涙 区域
    (0x5E80, 0x5EBF),   # 庀-庿
    (0x7D00, 0x7D99),   # 紀-紿
    (0x9340, 0x9399),   # 鍀-鎿
    (0x63C0, 0x63D9),   # 揀-揙
    (0x5C20, 0x5C3F),   # 尠-尿
    (0x9470, 0x9499),   # 鑰-钙
    (0x5BD0, 0x5D3F),   # 峰-崿
    (0x5F40, 0x5F99),   # 彀-徙
    (0x9380, 0x93D9),   # 鎀-鏙
    (0x6300, 0x6319),   # 挀-挙
    (0x5D30, 0x5D39),   # 崰-崹
    (0x7000, 0x7099),   # 瀀-灙
    (0x6900, 0x6999),   # 椀-榙
    (0x4E00, 0x4E1F),   # 一-丧
]


def is_in_high_risk_range(cp):
    """检查码点是否在高风险范围。"""
    for lo, hi in HIGH_RISK_RANGES:
        if lo <= cp <= hi:
            return True
    return False


def find_semantic_mojibake(text):
    """
    检测语义乱码：连续高风险字符序列。

    返回: [(line_no, snippet, sequence), ...]
    """
    findings = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        # 跳过已知标记行
        if any(marker in line for marker in LITERAL_CONTEXT_MARKERS):
            continue
        if "�" in line:
            continue  # 已有 replacement char，不做语义检测

        # 找连续高风险字符
        current_run = []
        run_start = 0

        for i, c in enumerate(line):
            cp = ord(c)
            if is_in_high_risk_range(cp):
                if not current_run:
                    run_start = i
                current_run.append(c)
            else:
                if len(current_run) >= 4:
                    seq = ''.join(current_run)
                    findings.append(("semantic-mojibake", line_no,
                                     line.strip(), seq))
                current_run = []

        if len(current_run) >= 4:
            seq = ''.join(current_run)
            findings.append(("semantic-mojibake", line_no,
                             line.strip(), seq))

    return findings


def roundtrip_verify(rel_path, text):
    """
    编码往返验证：检查文本是否能无损编码到 gb18030 再解码回来。

    如果往返后的字节与原始不同，说明原始数据不是纯 GBK/GB18030，
    可能混入了其他编码（如 UTF-8）的段落。

    返回: [(line_no, original_segment, roundtrip_segment), ...]
    """
    findings = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        # 跳过纯 ASCII 行
        if all(ord(c) < 128 for c in line):
            continue
        # 跳过已知标记行
        if any(marker in line for marker in LITERAL_CONTEXT_MARKERS):
            continue
        if "�" in line:
            continue

        try:
            gb_bytes = line.encode('gb18030', errors='replace')
            roundtrip = gb_bytes.decode('gb18030')
            if line != roundtrip:
                # 找到了！原始行和往返行不一致 → 编码有问题
                findings.append(("roundtrip-fail", line_no,
                                 line.strip(), roundtrip.strip()))
        except Exception:
            pass

    return findings


# ============================================================
# 原有检测逻辑
# ============================================================


def parse_args():
    parser = argparse.ArgumentParser(description="Check converted files for suspicious mojibake patterns.")
    parser.add_argument("--root", default=".", help="Repository root")
    parser.add_argument("--files", default="", help="Comma-separated list of files to inspect")
    parser.add_argument(
        "--allow-question-files",
        default="",
        help="Comma-separated list of files allowed to contain repeated question marks",
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Enable deep checks: round-trip verification and semantic mojibake detection",
    )
    return parser.parse_args()


def parse_csv(value):
    return [item.strip().replace("\\", "/") for item in value.split(",") if item.strip()]


def should_be_bomless(rel_path):
    lowered = rel_path.lower()
    if lowered.endswith((".mk",) + EXTENSIONS_WITHOUT_BOM):
        return True
    if "/startup" in lowered or lowered.startswith("startup"):
        return True
    return any(token in lowered for token in STARTUP_TOKENS)


def scan_text(rel_path, text, allow_question):
    """基础乱码扫描。"""
    findings = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if any(marker in line for marker in LITERAL_CONTEXT_MARKERS):
            continue
        if "�" in line:
            findings.append(("replacement-char", line_no, line.strip()))
        if not allow_question and QUESTION_RUN_RE.search(line):
            findings.append(("question-run", line_no, line.strip()))
        for term in SUSPICIOUS_TERMS:
            if term in line:
                findings.append(("suspicious-term", line_no, line.strip()))
    return findings


def inspect_file(root, rel_path, allow_question=False, deep=False):
    full_path = Path(root) / rel_path
    data = full_path.read_bytes()
    findings = []
    if should_be_bomless(rel_path) and data.startswith(codecs.BOM_UTF8):
        findings.append(("unexpected-bom", 1, "UTF-8 BOM found in BOM-less file"))
    text = data.decode("utf-8", errors="replace")
    findings.extend(scan_text(rel_path, text, allow_question))

    # 深度检测
    if deep:
        # 解码为正确的 UTF-8（如果错误才用 replace）
        try:
            text_clean = data.decode("utf-8")
        except UnicodeDecodeError:
            text_clean = text  # 已有替换字符的版本

        findings.extend(find_semantic_mojibake(text_clean))
        findings.extend(roundtrip_verify(rel_path, text_clean))

    return findings


def main():
    args = parse_args()
    root = os.path.abspath(args.root)
    files = parse_csv(args.files)
    allow_question_files = set(parse_csv(args.allow_question_files))

    if not files:
        print("No files provided. Use --files with converted file list.")
        return 2

    all_findings = []
    for rel_path in files:
        findings = inspect_file(root, rel_path,
                                allow_question=rel_path in allow_question_files,
                                deep=args.deep)
        if findings:
            all_findings.append((rel_path, findings))

    if not all_findings:
        print("No suspicious mojibake patterns found.")
        return 0

    for rel_path, findings in all_findings:
        print("[FILE] {}".format(rel_path))
        for kind, line_no, snippet in findings:
            if kind in ("roundtrip-fail", "semantic-mojibake"):
                # 深度检测项，显示更多信息
                if len(snippet) > 2:
                    print("  - {} @ line {}: {} (suspect: {})".format(
                        kind, line_no, snippet[0][:80], snippet[1][:40]))
                else:
                    print("  - {} @ line {}: {}".format(kind, line_no, snippet[:80]))
            else:
                print("  - {} @ line {}: {}".format(kind, line_no, snippet))
    return 1


if __name__ == "__main__":
    sys.exit(main())
