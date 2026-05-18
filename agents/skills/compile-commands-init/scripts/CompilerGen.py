import os
import re
import json
import sys
from pathlib import Path

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
    '--preinclude',
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
        if arg.startswith("--cpu="):
            cpu = arg.split("=", 1)[1].lower()
            clang_args.append(f"-mcpu={cpu}")
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

    # 提取源文件（通常是 -c 后面的第一个参数）
    source_match = re.search(r'-c\s+(\S+\.c\b|\S+\.cpp\b)', args_str)
    if not source_match:
        return None

    source_file = source_match.group(1)

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
    生成 .clangd 配置文件以优化 clangd 行为
    """
    clangd_lines = [
        "CompileFlags:",
        "  Remove:",
        "    - --apcs=interwork",
        "    - --multibyte_chars",
        "    - --diag_error=warning",
        "    - --depend=*",
        "    - --preinclude=*",
        "    - --via=*",
        "    - --pd=*",
        "    - --split_sections",
        "    - --feedback=*",
        "    - --keep=*",
        "    - --list=*",
        "  Add:",
        "    - --target=arm-none-eabi",
        "    - -mcpu=cortex-m4",
        "    - -mfpu=fpv4-sp-d16",
        "    - -mfloat-abi=hard",
    ]

    arm_std_include = detect_arm_std_include_from_log(log_lines or [], compiler_name)
    if not arm_std_include:
        arm_std_include = find_arm_std_include(compiler_name)

    if arm_std_include:
        clangd_lines.extend([
            "    - -isystem",
            f"    - {arm_std_include}",
        ])

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
