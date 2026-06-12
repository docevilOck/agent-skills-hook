import os
import re
import json
import sys
from pathlib import Path

GBK_SOURCE_CACHE = {}

# 支持的编译器正则表达式
COMPILER_PATTERNS = {
    "armcc": r'(?:armcc|armcc\.exe)\s+(.*?)\s+-o\s+(\S+\.o)',
    "armclang": r'(?:armclang|armclang\.exe)\s+(.*?)\s+-o\s+(\S+\.o)',
    "gcc": r'(?:gcc|arm-none-eabi-gcc)\s+(.*?)\s+-o\s+(\S+\.o)'
}

# ARMCC特有的需要移除的参数
ARMCC_SPECIFIC_FLAGS = [
    '--apcs=interwork',
    '--multibyte_chars',
    '--diag_error=warning',
    '--depend',
    '--via',
    '--pd',
    '--split_sections',
    '--feedback',
    '--keep',
    '--list'
]

TEMP_ARTIFACTS = [
    "build_log.txt",
]

HEADER_EXTENSIONS = {".h", ".hh", ".hpp", ".hxx"}

ARM_STD_INCLUDE_CANDIDATES = {
    "armclang": [
        Path("C:/Keil_v5/ARM/ARMCLANG/include"),
        Path("C:/Keil_v5/ARM/ARMCC/include"),
    ],
    "armcc": [
        Path("C:/Keil_v5/ARM/ARMCC/include"),
        Path("C:/Keil_v5/ARM/ARMCLANG/include"),
    ],
    "gcc": [
        Path("C:/Keil_v5/ARM/ARMCLANG/include"),
        Path("C:/Keil_v5/ARM/ARMCC/include"),
    ],
}

COMPILER_EXECUTABLE_PATTERNS = {
    "armcc": re.compile(r'(?P<path>[^\s"\']*armcc(?:\.exe)?)', re.IGNORECASE),
    "armclang": re.compile(r'(?P<path>[^\s"\']*armclang(?:\.exe)?)', re.IGNORECASE),
    "gcc": re.compile(r'(?P<path>[^\s"\']*(?:arm-none-eabi-)?gcc(?:\.exe)?)', re.IGNORECASE),
}

LOG_COMPILER_PRIORITY = ["armclang", "armcc", "gcc"]


def strip_wrapping_quotes(value):
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def try_convert_preinclude_arg(arg, next_arg=None):
    if arg.startswith("--preinclude="):
        return ["-include", strip_wrapping_quotes(arg.split("=", 1)[1])], False

    if arg == "--preinclude" and next_arg:
        return ["-include", strip_wrapping_quotes(next_arg)], True

    if arg == "-include" and next_arg:
        return ["-include", strip_wrapping_quotes(next_arg)], True

    if arg.startswith("-include") and len(arg) > len("-include"):
        return ["-include", strip_wrapping_quotes(arg[len("-include"):])], False

    return None, False


def convert_arm_cpu_flag(arg):
    if not arg.startswith("--cpu="):
        return None

    raw_cpu = strip_wrapping_quotes(arg.split("=", 1)[1]).lower()
    suffixes = raw_cpu.split(".")
    base_cpu = suffixes[0]
    converted = [f"-mcpu={base_cpu}"]

    if ".fp" in raw_cpu:
        fpu_map = {
            "cortex-m4": "fpv4-sp-d16",
            "cortex-m7": "fpv5-d16",
            "cortex-r4": "vfpv3-d16",
            "cortex-r5": "vfpv3-d16",
        }
        fpu = fpu_map.get(base_cpu)
        if fpu:
            converted.extend([f"-mfpu={fpu}", "-mfloat-abi=softfp"])

    return converted

def convert_to_clang_flags(args_str):
    """
    将任意编译器的标志转换为 clang 兼容格式
    """
    args = args_str.split()
    clang_args = []
    i = 0
    
    while i < len(args):
        arg = args[i]
        skip = False

        converted_preinclude, consume_next = try_convert_preinclude_arg(
            arg,
            args[i + 1] if i + 1 < len(args) else None,
        )
        if converted_preinclude:
            clang_args.extend(converted_preinclude)
            i += 2 if consume_next else 1
            continue
        
        # 处理需要移除的ARMCC特定参数
        for flag in ARMCC_SPECIFIC_FLAGS:
            if arg.startswith(flag):
                skip = True
                # 如果参数没有用=连接值，跳过下一个参数
                if '=' not in arg and not arg.startswith('--'):
                    i += 1
                break
        
        if skip:
            i += 1
            continue
            
        # 转换常见标志
        converted_cpu = convert_arm_cpu_flag(arg)
        if converted_cpu:
            clang_args.extend(converted_cpu)
        elif arg.startswith("--fpu="):
            fpu = arg.split("=", 1)[1]
            clang_args.append(f"-mfpu={fpu}")
        elif arg.startswith("--float-abi="):
            abi = arg.split("=", 1)[1]
            clang_args.append(f"-mfloat-abi={abi}")
        elif arg.startswith("-O"):
            clang_args.append(arg)
        elif arg.startswith("--std=") or arg.startswith("-std="):
            std = arg.split("=", 1)[1] if "=" in arg else arg[5:]
            clang_args.append(f"-std={std}")
        elif arg == "--gnu":
            clang_args.append("-std=gnu99")
        elif arg == "--c99":
            clang_args.append("-std=c99")
        elif arg.startswith("--target="):
            # 保留目标架构但使用clang标准格式
            target = arg.split("=", 1)[1]
            clang_args.append(f"--target={target}")
        elif arg.startswith("-D") and len(arg) > 2:
            # -DDEFINE 格式
            clang_args.append(arg)
        elif arg == "-D" and i + 1 < len(args):
            # -D DEFINE 格式
            clang_args.extend([arg, args[i+1]])
            i += 1
        elif arg == "-c" and i + 1 < len(args):
            i += 1
        elif arg == "-o" and i + 1 < len(args):
            i += 1
        elif arg.startswith("-I") and len(arg) > 2:
            # -Ipath 格式
            clang_args.append(arg)
        elif arg == "-I" and i + 1 < len(args):
            # -I path 格式
            clang_args.extend([arg, args[i+1]])
            i += 1
        else:
            # 保留未识别标志（但排除ARMCC特定参数）
            is_armcc_specific = any(arg.startswith(flag) for flag in ARMCC_SPECIFIC_FLAGS)
            if not is_armcc_specific:
                clang_args.append(arg)
        
        i += 1

    return clang_args

def normalize_clang_arg(arg):
    """
    清理从构建日志直接保留下来的 shell 转义，避免写入 arguments 后继续污染 clangd。
    """
    if arg.startswith("-D") and '\\"' in arg:
        return arg.replace('\\"', '"')
    return arg

def find_arm_std_include(compiler_name):
    """
    按编译器优先级，为 clangd 找一个当前机器上真实存在的 ARM C 标准头目录。
    """
    candidates = ARM_STD_INCLUDE_CANDIDATES.get(compiler_name, [])
    for candidate in candidates:
        if candidate.exists():
            return candidate.as_posix()
    return None

def parse_compile_command(log_line, compiler_name):
    """
    解析日志中的一行，提取编译命令并转换为 clang 兼容格式
    """
    pattern = COMPILER_PATTERNS.get(compiler_name)
    if not pattern:
        print(f"不支持的编译器: {compiler_name}")
        return None

    match = re.search(pattern, log_line)
    if not match:
        return None

    args_str = match.group(1)
    output_file = match.group(2)

    # 提取源文件 armclang 中 -c 可能在 -o 之后，从完整行匹配
    source_match = re.search(r'-c\s+(\S+\.c\b|\S+\.cpp\b)', log_line)
    if not source_match:
        return None

    source_file = remap_gbk_source(source_match.group(1), os.getcwd())

    # 构建 clang 兼容命令
    command = ["clang", "-c", source_file, "-o", output_file]

    # 转换所有标志
    converted_flags = convert_to_clang_flags(args_str)
    command.extend(converted_flags)

    # 确保有目标架构
    if not any(arg.startswith("--target=") for arg in command):
        command.append("--target=arm-none-eabi")

    command = [normalize_clang_arg(arg) for arg in command]

    return {
        "directory": os.getcwd(),
        "file": source_file,
        "output": output_file,
        "arguments": command
    }

def read_build_log(log_file="build_log.txt"):
    """
    读取 build_log.txt 文件内容
    """
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            return f.readlines()
    except Exception as e:
        print(f"[ERROR] 无法读取 {log_file}: {e}")
        return []

def detect_compiler_from_log(log_lines):
    """
    从构建日志中自动识别当前主编译器，避免每次手工传参。
    """
    for line in log_lines:
        lowered = line.lower()
        for compiler_name in LOG_COMPILER_PRIORITY:
            if compiler_name in lowered and " -c " in lowered:
                return compiler_name

    return None

def detect_arm_std_include_from_log(log_lines, compiler_name):
    """
    优先根据构建日志里的真实编译器路径反推出标准头目录，避免只靠硬编码候选目录。
    """
    if not compiler_name:
        return None

    executable_pattern = COMPILER_EXECUTABLE_PATTERNS.get(compiler_name)
    if not executable_pattern:
        return None

    for line in log_lines:
        if compiler_name not in line.lower():
            continue

        match = executable_pattern.search(line)
        if not match:
            continue

        executable_path = Path(match.group("path").replace("\\", "/"))
        derived_candidates = []

        if compiler_name == "armclang":
            derived_candidates.append(executable_path.parent.parent / "include")
        elif compiler_name == "armcc":
            derived_candidates.extend([
                executable_path.parent.parent / "ARMCC" / "include",
                executable_path.parent / "include",
            ])
        elif compiler_name == "gcc":
            derived_candidates.extend([
                executable_path.parent.parent / "arm-none-eabi" / "include",
                executable_path.parent.parent / "include",
            ])

        for candidate in derived_candidates:
            if candidate.exists():
                return candidate.as_posix()

    return None

def generate_clangd_config(compiler_name=None, log_lines=None):
    """
    生成 .clangd 配置文件。

    compile_commands.json 已携带目标架构、FPU、系统头等真实编译参数。
    这里不要再通过 Add 注入目标参数，否则容易和不同项目/芯片的
    编译数据库冲突，导致 clangd 索引残缺。
    """
    clangd_lines = [
        "CompileFlags:",
        "  Remove:",
        "    - --apcs=interwork",
        "    - --multibyte_chars",
        "    - --diag_error=warning",
        "    - --depend=*",
        "    - --via=*",
        "    - --pd=*",
        "    - --split_sections",
        "    - --feedback=*",
        "    - --keep=*",
        "    - --list=*",
    ]

    clangd_lines.append("  CompilationDatabase: .")
    clangd_config = "\n".join(clangd_lines) + "\n"
    
    try:
        with open(".clangd", "w", encoding="utf-8") as f:
            f.write(clangd_config)
        print("成功生成 .clangd 配置文件")
    except Exception as e:
        print(f"[ERROR] 无法生成 .clangd 配置文件: {e}")


def cleanup_temp_artifacts(preserve_build_log=False):
    """
    清理本脚本生成流程使用的临时产物，只保留最终需要的输出文件
    """
    removed = []

    for artifact in TEMP_ARTIFACTS:
        if artifact == "build_log.txt" and preserve_build_log:
            continue

        path = Path(artifact)
        if not path.exists():
            continue

        try:
            if path.is_file():
                path.unlink()
                removed.append(str(path))
        except Exception as e:
            print(f"[WARN] 无法清理临时产物 {path}: {e}")

    if removed:
        print("已清理临时产物: " + ", ".join(removed))

def generate_compile_commands(compiler_name, preserve_build_log=False):
    """
    生成 compile_commands.json 文件
    """
    print(f"使用编译器: {compiler_name}")
    print("开始解析 build_log.txt...")

    log_lines = read_build_log()

    compile_commands = []
    for line in log_lines:
        lowered = line.lower()
        if compiler_name in lowered and "-c" in lowered:
            cmd = parse_compile_command(line, compiler_name)
            if cmd:
                compile_commands.append(cmd)
                print(f"找到编译命令: {cmd['file']}")

    if compile_commands:
        # 直接生成优化后的 compile_commands.json
        optimize_and_save(compile_commands)
        cleanup_temp_artifacts(preserve_build_log=preserve_build_log)
        print(f"成功生成 compile_commands.json，共 {len(compile_commands)} 条编译命令")
    else:
        print("未找到任何编译命令，请检查 build_log.txt 内容")

def is_source_file(path):
    return Path(path).suffix.lower() in {".c", ".cc", ".cpp", ".cxx"}

def is_header_file(path):
    return Path(path).suffix.lower() in HEADER_EXTENSIONS

def split_include_arg(arg):
    if arg.startswith("-I") and len(arg) > 2:
        return arg[2:]
    return None

def extract_include_dirs(args):
    include_dirs = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "-I" and i + 1 < len(args):
            include_dirs.append(args[i + 1])
            i += 2
            continue

        include_dir = split_include_arg(arg)
        if include_dir:
            include_dirs.append(include_dir)

        i += 1

    return include_dirs

def source_language_flag(source_file):
    suffix = Path(source_file).suffix.lower()
    if suffix == ".c":
        return "c-header"
    if suffix in {".cc", ".cpp", ".cxx"}:
        return "c++-header"
    return "c-header"

def normalize_path_for_db(path):
    return Path(path).as_posix()


def remap_gbk_source(source_file, directory):
    normalized = normalize_path_for_db(source_file)
    marker = "/gbk_src/"
    if marker not in normalized:
        return normalized

    cached = GBK_SOURCE_CACHE.get(normalized)
    if cached:
        return cached

    suffix = Path(normalized.split(marker, 1)[1])
    search_root = Path(directory).resolve()

    for candidate in search_root.rglob(suffix.name):
        candidate_posix = candidate.as_posix()
        if "/gbk_src/" in candidate_posix:
            continue

        candidate_parts = candidate.parts
        if len(candidate_parts) < len(suffix.parts):
            continue

        if tuple(candidate_parts[-len(suffix.parts):]) != suffix.parts:
            continue

        try:
            remapped = normalize_path_for_db(candidate.relative_to(search_root))
        except ValueError:
            remapped = candidate_posix

        GBK_SOURCE_CACHE[normalized] = remapped
        print(f"GBK 源映射: {normalized} -> {remapped}")
        return remapped

    GBK_SOURCE_CACHE[normalized] = normalized
    print(f"[WARN] 未找到 GBK 源对应原始文件，保留原路径: {normalized}")
    return normalized

def resolve_header(include_name, source_file, include_dirs, directory):
    candidates = []
    source_dir = Path(directory) / Path(source_file).parent
    candidates.append(source_dir / include_name)

    for include_dir in include_dirs:
        inc = Path(include_dir)
        if not inc.is_absolute():
            inc = Path(directory) / inc
        candidates.append(inc / include_name)

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue

        if resolved.exists() and resolved.is_file() and is_header_file(resolved):
            try:
                return normalize_path_for_db(resolved.relative_to(Path(directory).resolve()))
            except ValueError:
                return normalize_path_for_db(resolved)

    return None

def find_direct_headers(entry):
    source_file = entry.get("file")
    directory = entry.get("directory", os.getcwd())
    if not source_file or not is_source_file(source_file):
        return []

    source_path = Path(directory) / source_file
    if not source_path.exists():
        return []

    args = entry.get("arguments", [])
    include_dirs = extract_include_dirs(args)
    include_pattern = re.compile(r'^\s*#\s*include\s+"([^"]+)"')
    headers = []
    seen = set()

    try:
        with open(source_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                match = include_pattern.match(line)
                if not match:
                    continue

                header = resolve_header(match.group(1), source_file, include_dirs, directory)
                if header and header not in seen:
                    headers.append(header)
                    seen.add(header)
    except Exception as e:
        print(f"[WARN] 无法扫描头文件依赖 {source_file}: {e}")

    return headers

def make_header_entry(source_entry, header_file):
    args = list(source_entry.get("arguments", []))
    if not args:
        return None

    new_args = []
    skip_next = False
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue

        if arg == "-c" and i + 1 < len(args):
            new_args.extend(["-x", source_language_flag(source_entry.get("file", "")), "-c", header_file])
            skip_next = True
            continue

        if arg == "-o" and i + 1 < len(args):
            output = Path(source_entry.get("output", ""))
            stem = Path(header_file).stem
            suffix = output.suffix or ".o"
            if output.parent:
                header_output = output.parent / f"{stem}.header{suffix}"
            else:
                header_output = Path(f"{stem}.header{suffix}")
            new_args.extend(["-o", normalize_path_for_db(header_output)])
            skip_next = True
            continue

        new_args.append(arg)

    return {
        "directory": source_entry.get("directory", os.getcwd()),
        "file": header_file,
        "output": normalize_path_for_db(Path(source_entry.get("output", "")).with_name(Path(header_file).stem + ".header.o")) if source_entry.get("output") else "",
        "arguments": new_args,
    }

def add_header_compile_commands(compile_commands):
    header_entries = []
    seen_files = {normalize_path_for_db(entry.get("file", "")) for entry in compile_commands}

    for entry in compile_commands:
        for header in find_direct_headers(entry):
            if header in seen_files:
                continue

            header_entry = make_header_entry(entry, header)
            if not header_entry:
                continue

            header_entries.append(header_entry)
            seen_files.add(header)

    compile_commands.extend(header_entries)
    if header_entries:
        print(f"已补充头文件编译命令: {len(header_entries)} 条")

def optimize_and_save(compile_commands):
    """
    优化编译命令并保存到 compile_commands.json
    """
    # 处理每个编译命令条目
    for entry in compile_commands:
        new_args = ["clang"]  # 确保使用 clang 作为编译器
        args = entry.get("arguments", [])[1:]  # 移除原始编译器
        
        # 提取关键参数
        source_file = None
        output_file_arg = None
        
        # 查找源文件和输出文件
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-c" and i + 1 < len(args):
                source_file = args[i + 1]
                i += 2
                continue
            elif arg == "-o" and i + 1 < len(args):
                output_file_arg = args[i + 1]
                i += 2
                continue
            i += 1
        
        # 添加源文件和输出文件参数
        if source_file:
            new_args.extend(["-c", source_file])
        if output_file_arg:
            new_args.extend(["-o", output_file_arg])
            
        # 添加其他参数，但要避免重复和不兼容参数
        added_includes = set()
        added_defines = set()
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            # 跳过要移除的参数
            if any(arg.startswith(flag) for flag in ARMCC_SPECIFIC_FLAGS):
                if '=' not in arg and i + 1 < len(args) and not args[i + 1].startswith('-'):
                    i += 2  # 跳过参数和其值
                else:
                    i += 1  # 只跳过参数
                continue
            
            # 处理包含路径，避免重复
            if arg.startswith("-I"):
                if arg not in added_includes:
                    new_args.append(arg)
                    added_includes.add(arg)
            # 处理定义，避免重复
            elif arg.startswith("-D"):
                if arg not in added_defines:
                    new_args.append(arg)
                    added_defines.add(arg)
            # 保留其他参数，但避免重复添加 -c 和 -o
            elif arg not in ["-c", "-o", "clang"] and (i == 0 or args[i-1] not in ["-c", "-o"]):
                # 检查是否是 -c 或 -o 的参数值
                if args[i-1] not in ["-c", "-o"]:
                    new_args.append(arg)
            
            i += 1
        
        # 确保目标架构参数
        if not any(arg.startswith("--target=") for arg in new_args):
            new_args.append("--target=arm-none-eabi")
            
        entry["arguments"] = [normalize_clang_arg(arg) for arg in new_args]

    add_header_compile_commands(compile_commands)

    # 写入文件
    try:
        with open("compile_commands.json", "w", encoding="utf-8") as f:
            json.dump(compile_commands, f, indent=2, ensure_ascii=False)
        print("成功生成 compile_commands.json")
    except Exception as e:
        print(f"[ERROR] 无法生成 compile_commands.json: {e}")

def main():
    log_lines = read_build_log()

    if len(sys.argv) < 2:
        compiler_name = detect_compiler_from_log(log_lines)
        if not compiler_name:
            print("未能从 build_log.txt 自动识别编译器，请显式传入编译器名")
            print(f"支持的编译器: {', '.join(COMPILER_PATTERNS.keys())}")
            sys.exit(1)

        generate_clangd_config(compiler_name, log_lines=log_lines)
        generate_compile_commands(compiler_name, preserve_build_log=True)
        return

    if sys.argv[1] == "--generate-config":
        compiler_name = detect_compiler_from_log(log_lines)
        generate_clangd_config(compiler_name, log_lines=log_lines)
        return

    compiler_name = sys.argv[1].lower()
    if compiler_name not in COMPILER_PATTERNS:
        print(f"不支持的编译器: {compiler_name}")
        print(f"支持的编译器: {', '.join(COMPILER_PATTERNS.keys())}")
        sys.exit(1)

    preserve_build_log = "--keep-build-log" in sys.argv[2:]

    # 生成两个文件
    generate_clangd_config(compiler_name, log_lines=log_lines)
    generate_compile_commands(compiler_name, preserve_build_log=preserve_build_log)

if __name__ == "__main__":
    main()
