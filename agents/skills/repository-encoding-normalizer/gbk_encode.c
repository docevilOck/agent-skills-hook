/*
 * gbk_encode.c — 扫描含中文运行期字面量的 .c/.h 源文件，生成 GBK 编码副本。
 *
 * 纯 C 实现，启动 <5ms（vs Python/PyInstaller ~1.4s）。
 * 用法: gbk_encode -s DIR -o DIR [-x DIR] [--mtime-filter STAMP]
 *                 [--full-scan-threshold N] [--force] [--list] [-q] [-- FILE...]
 *
 * 编译 (MinGW-w64 / MSVC):
 *   gcc    -O2 -s -static -o gbk_encode.exe gbk_encode.c
 *   cl     /O2 /MT /Fe:gbk_encode.exe gbk_encode.c /link /SUBSYSTEM:CONSOLE
 *
 * 依赖: 仅 kernel32.dll（Windows 自带），无任何外部运行时。
 */
#define _CRT_SECURE_NO_WARNINGS
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

/* ── 类型定义 ────────────────────────────────────────────────────────────── */

typedef enum {
    SCAN_OK = 0,
    SCAN_ERR_ARGS,
    SCAN_ERR_SRC_NOT_FOUND,
    SCAN_ERR_IO,
    SCAN_ERR_OOM,
} scan_status_t;

typedef struct {
    const char *src;        /* -s 源根目录 */
    const char *out;        /* -o 输出目录 */
    const char *mtime_filt; /* --mtime-filter 参考文件 */
    const char **excludes;  /* -x 排除目录列表 */
    int    exclude_count;
    const char **files;     /* 显式文件列表 */
    int    file_count;
    int    full_scan_threshold; /* --full-scan-threshold */
    int    force;               /* --force */
    int    list_only;           /* --list */
    int    quiet;               /* -q */
} gbk_cfg_t;

/* ── CJK Unicode 范围 ───────────────────────────────────────────────────── */

static int is_cjk_codepoint(unsigned int cp)
{
    return (cp >= 0x4E00 && cp <= 0x9FFF)
        || (cp >= 0x3400 && cp <= 0x4DBF)
        || (cp >= 0xF900 && cp <= 0xFAFF)
        || (cp >= 0xFF00 && cp <= 0xFFEF)
        || (cp >= 0x3000 && cp <= 0x303F)
        || (cp >= 0xFE30 && cp <= 0xFE4F);
}

/* ── UTF-8 解码 ──────────────────────────────────────────────────────────── */

static unsigned int utf8_decode(const unsigned char **pp, const unsigned char *end)
{
    const unsigned char *p = *pp;
    unsigned int cp;

    if (p >= end) { (*pp)++; return 0; }

    if ((p[0] & 0x80) == 0) {
        cp = p[0]; *pp = p + 1; return cp;
    }
    if ((p[0] & 0xE0) == 0xC0 && p + 1 < end) {
        cp = ((p[0] & 0x1F) << 6) | (p[1] & 0x3F);
        *pp = p + 2; return cp;
    }
    if ((p[0] & 0xF0) == 0xE0 && p + 2 < end) {
        cp = ((p[0] & 0x0F) << 12) | ((p[1] & 0x3F) << 6) | (p[2] & 0x3F);
        *pp = p + 3; return cp;
    }
    if ((p[0] & 0xF8) == 0xF0 && p + 3 < end) {
        cp = ((p[0] & 0x07) << 18) | ((p[1] & 0x3F) << 12)
           | ((p[2] & 0x3F) << 6) | (p[3] & 0x3F);
        *pp = p + 4; return cp;
    }
    /* 无效字节：跳过但不产生 U+FFFD（避免误匹配 CJK 范围） */
    (*pp)++; return 0;
}

/* ── 快速预检：是否含 CJK 前导字节 ──────────────────────────────────────── */

static int has_cjk_lead_bytes(const unsigned char *data, size_t len)
{
    for (size_t i = 0; i < len; i++) {
        if (data[i] >= 0xE4 && data[i] <= 0xE9) return 1;
    }
    return 0;
}

/* ── CJK 检测（仅检查双引号字符串字面量）────────────────────────────────── */

static int has_chinese_in_strings(const unsigned char *data, size_t len)
{
    /* Strip BOM */
    if (len >= 3 && data[0] == 0xEF && data[1] == 0xBB && data[2] == 0xBF) {
        data += 3; len -= 3;
    }

    if (!has_cjk_lead_bytes(data, len)) return 0;

    /* 快速 UTF-8 校验：非 UTF-8 文件（如 ISO-8859）不可能含中文 */
    if (MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS,
                             (LPCCH)data, (int)len, NULL, 0) <= 0)
        return 0;

    int in_string = 0, in_char = 0, in_line_comment = 0, in_block_comment = 0;
    int escape = 0, has_cjk = 0;
    const unsigned char *p = data;
    const unsigned char *end = data + len;

    while (p < end) {
        unsigned char c = *p;
        unsigned char nxt = (p + 1 < end) ? p[1] : 0;

        if (in_line_comment) {
            if (c == '\n') in_line_comment = 0;
            p++; continue;
        }
        if (in_block_comment) {
            if (c == '*' && nxt == '/') { in_block_comment = 0; p += 2; continue; }
            p++; continue;
        }
        if (in_char) {
            if (escape) { escape = 0; p++; continue; }
            if (c == '\\') { escape = 1; p++; continue; }
            if (c == '\'') { in_char = 0; }
            p++; continue;
        }
        if (in_string) {
            if (escape) { escape = 0; p++; continue; }
            if (c == '\\') { escape = 1; p++; continue; }
            if (c == '"') { in_string = 0; p++; continue; }
            /* 检查 CJK */
            if ((c & 0x80) && !has_cjk) {
                unsigned int cp = utf8_decode(&p, end);
                if (is_cjk_codepoint(cp)) has_cjk = 1;
                continue;
            }
            p++; continue;
        }

        if (c == '/' && nxt == '/') { in_line_comment = 1; p += 2; continue; }
        if (c == '/' && nxt == '*') { in_block_comment = 1; p += 2; continue; }
        if (c == '\'') { in_char = 1; escape = 0; p++; continue; }
        if (c == '"') { in_string = 1; escape = 0; }
        p++;
    }
    return has_cjk;
}

/* ── UTF-8 → GBK 转换（Windows MultiByteToWideChar）────────────────────── */

static unsigned char *utf8_to_gbk(const unsigned char *utf8_data, size_t len,
                                   size_t *out_len)
{
    /* UTF-8 → UTF-16 */
    int wlen = MultiByteToWideChar(CP_UTF8, 0,
                                    (LPCCH)utf8_data, (int)len, NULL, 0);
    if (wlen <= 0) return NULL;
    wchar_t *wide = malloc((wlen + 1) * sizeof(wchar_t));
    if (!wide) return NULL;
    MultiByteToWideChar(CP_UTF8, 0,
                         (LPCCH)utf8_data, (int)len, wide, wlen);
    wide[wlen] = 0;

    /* UTF-16 → GBK (CP936) */
    int glen = WideCharToMultiByte(936, 0, wide, wlen, NULL, 0, NULL, NULL);
    if (glen <= 0) { free(wide); return NULL; }
    unsigned char *gbk = malloc(glen + 1);
    if (!gbk) { free(wide); return NULL; }
    WideCharToMultiByte(936, 0, wide, wlen, (LPSTR)gbk, glen, NULL, NULL);
    gbk[glen] = 0;
    *out_len = glen;

    free(wide);
    return gbk;
}

/* ── 字符串内 LF→\n 转义修复 ────────────────────────────────────────────── */

static size_t fix_newlines(unsigned char *data, size_t len)
{
    size_t w = 0;
    int in_string = 0, in_char = 0, in_line = 0, in_block = 0, esc = 0;

    for (size_t r = 0; r < len; r++) {
        unsigned char c = data[r];
        unsigned char nxt = (r + 1 < len) ? data[r + 1] : 0;

        if (in_line)   { data[w++] = c; if (c == '\n') in_line = 0; continue; }
        if (in_block)  { data[w++] = c; if (c == '*' && nxt == '/') { data[w++] = nxt; r++; in_block = 0; } continue; }
        if (in_char)   { data[w++] = c; if (esc) esc = 0; else if (c == '\\') esc = 1; else if (c == '\'') in_char = 0; continue; }
        if (in_string) {
            if (c == '\n') { data[w++] = '\\'; data[w++] = 'n'; esc = 0; continue; }
            data[w++] = c;
            if (esc) esc = 0; else if (c == '\\') esc = 1; else if (c == '"') in_string = 0;
            continue;
        }
        if (c == '/' && nxt == '/') { data[w++] = c; data[w++] = nxt; r++; in_line = 1; continue; }
        if (c == '/' && nxt == '*') { data[w++] = c; data[w++] = nxt; r++; in_block = 1; continue; }
        data[w++] = c;
        if (c == '\'') in_char = 1;
        else if (c == '"') in_string = 1;
    }
    return w;
}

/* ── 文件时间戳获取 ──────────────────────────────────────────────────────── */

static long long file_mtime(const char *path)
{
    struct _stat64 st;
    if (_stat64(path, &st) != 0) return 0;
    return st.st_mtime;
}

/* ── 目录创建（递归）─────────────────────────────────────────────────────── */

static void mkdir_recursive(char *path)
{
    for (char *p = path; *p; p++) {
        if (*p == '/' || *p == '\\') {
            char saved = *p; *p = 0;
            CreateDirectoryA(path, NULL);
            *p = saved;
        }
    }
    CreateDirectoryA(path, NULL);
}

/* ── 字符串列表 ──────────────────────────────────────────────────────────── */

#define MAX_FILES 16384
#define MAX_PATH_LEN 1024

typedef struct {
    char  *items[MAX_FILES];
    int    count;
    int    cap;
} strlist_t;

static void strlist_init(strlist_t *sl, int cap) {
    sl->count = 0; sl->cap = cap;
}

static void strlist_add(strlist_t *sl, const char *s) {
    if (sl->count >= sl->cap) return;
    sl->items[sl->count++] = _strdup(s);
}

static void strlist_free(strlist_t *sl) {
    for (int i = 0; i < sl->count; i++) free(sl->items[i]);
    sl->count = 0;
}

static int strlist_cmp(const void *a, const void *b) {
    return strcmp(*(const char **)a, *(const char **)b);
}

/* ── 路径拼接 ────────────────────────────────────────────────────────────── */

static void path_join(char *dst, size_t dst_size, const char *a, const char *b)
{
    int len = snprintf(dst, dst_size, "%s", a);
    if (len > 0 && dst[len - 1] != '\\' && dst[len - 1] != '/') {
        snprintf(dst + len, dst_size - len, "\\%s", b);
    } else {
        snprintf(dst + len, dst_size - len, "%s", b);
    }
}

/* ── 路径相对化 ──────────────────────────────────────────────────────────── */

static const char *relpath(const char *full, const char *base)
{
    size_t blen = strlen(base);
    if (_strnicmp(full, base, blen) == 0) {
        const char *r = full + blen;
        while (*r == '\\' || *r == '/') r++;
        return r;
    }
    return full;
}

/* ── 目录排除检查 ────────────────────────────────────────────────────────── */

static int is_excluded(const char *dir, const char *src_root,
                       const char **excludes, int exclude_count)
{
    const char *rel = relpath(dir, src_root);
    for (int i = 0; i < exclude_count; i++) {
        const char *ex = excludes[i];
        size_t exlen = strlen(ex);
        if (_strnicmp(rel, ex, exlen) == 0) {
            char c = rel[exlen];
            if (c == 0 || c == '\\' || c == '/') return 1;
        }
    }
    return 0;
}

/* ── 文件扫描 ────────────────────────────────────────────────────────────── */

static void scan_files(const char *dir, const char *src_root,
                        const char **excludes, int exclude_count,
                        strlist_t *all, strlist_t *changed,
                        long long filter_ts)
{
    char pattern[MAX_PATH_LEN];
    snprintf(pattern, sizeof(pattern), "%s\\*", dir);

    WIN32_FIND_DATAA fd;
    HANDLE h = FindFirstFileA(pattern, &fd);
    if (h == INVALID_HANDLE_VALUE) return;

    do {
        if (strcmp(fd.cFileName, ".") == 0 || strcmp(fd.cFileName, "..") == 0)
            continue;

        char full[MAX_PATH_LEN];
        path_join(full, sizeof(full), dir, fd.cFileName);

        if (fd.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY) {
            if (!is_excluded(full, src_root, excludes, exclude_count))
                scan_files(full, src_root, excludes, exclude_count,
                           all, changed, filter_ts);
        } else {
            const char *name = fd.cFileName;
            size_t nlen = strlen(name);
            if (nlen < 2) continue;
            const char *ext = name + nlen - 2;
            if (strcmp(ext, ".c") != 0 && strcmp(ext, ".h") != 0) continue;

            strlist_add(all, full);

            if (filter_ts > 0) {
                long long mtime;
                /* Get file mtime via FindFirstFile is in ftLastWriteTime */
                ULARGE_INTEGER ul;
                ul.LowPart  = fd.ftLastWriteTime.dwLowDateTime;
                ul.HighPart = fd.ftLastWriteTime.dwHighDateTime;
                mtime = (long long)(ul.QuadPart / 10000000ULL - 11644473600ULL);
                if (mtime > filter_ts) {
                    strlist_add(changed, full);
                }
            } else {
                strlist_add(changed, full);
            }
        }
    } while (FindNextFileA(h, &fd));
    FindClose(h);
}

/* ── 文件读取 ────────────────────────────────────────────────────────────── */

static unsigned char *read_file(const char *path, size_t *len)
{
    FILE *f = fopen(path, "rb");
    if (!f) return NULL;
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz <= 0) { fclose(f); return NULL; }
    unsigned char *buf = malloc(sz + 1);
    if (!buf) { fclose(f); return NULL; }
    *len = fread(buf, 1, sz, f);
    fclose(f);
    buf[*len] = 0;
    return buf;
}

/* ── 文件写入 ────────────────────────────────────────────────────────────── */

static int write_file(const char *path, const unsigned char *data, size_t len)
{
    char tmp[MAX_PATH_LEN + 4];
    int n = snprintf(tmp, sizeof(tmp), "%s.tmp", path);
    if (n < 0 || (size_t)n >= sizeof(tmp)) return -1;

    /* 确保目录存在 */
    char dir[MAX_PATH_LEN];
    strcpy(dir, path);
    char *slash = strrchr(dir, '\\');
    if (!slash) slash = strrchr(dir, '/');
    if (slash) { *slash = 0; mkdir_recursive(dir); }

    FILE *f = fopen(tmp, "wb");
    if (!f) return -1;
    if (fwrite(data, 1, len, f) != len) { fclose(f); DeleteFileA(tmp); return -1; }
    fclose(f);

    DeleteFileA(path);
    if (!MoveFileA(tmp, path)) { DeleteFileA(tmp); return -1; }
    return 0;
}

/* ── 输出路径生成 ────────────────────────────────────────────────────────── */

static void make_out_path(char *dst, size_t dst_size,
                           const char *out_root, const char *src_root,
                           const char *filepath)
{
    const char *rel = relpath(filepath, src_root);
    path_join(dst, dst_size, out_root, rel);
}

/* ── 文件转换 ────────────────────────────────────────────────────────────── */

static int convert_file(const char *src_root, const char *out_root,
                         const char *filepath, int force, int *converted)
{
    *converted = 0;

    char out_path[MAX_PATH_LEN];
    make_out_path(out_path, sizeof(out_path), out_root, src_root, filepath);

    if (!force) {
        long long src_mt = file_mtime(filepath);
        long long dst_mt = file_mtime(out_path);
        if (dst_mt > 0 && dst_mt >= src_mt) return 0; /* 已是最新 */
    }

    size_t len;
    unsigned char *data = read_file(filepath, &len);
    if (!data) { fprintf(stderr, "ERROR: cannot read %s\n", filepath); return -1; }

    /* Strip BOM */
    if (len >= 3 && data[0] == 0xEF && data[1] == 0xBB && data[2] == 0xBF) {
        memmove(data, data + 3, len - 3); len -= 3;
    }

    size_t gbk_len;
    unsigned char *gbk = utf8_to_gbk(data, len, &gbk_len);
    free(data);
    if (!gbk) { fprintf(stderr, "ERROR: encode failed %s\n", filepath); return -1; }

    gbk_len = fix_newlines(gbk, gbk_len);

    if (write_file(out_path, gbk, gbk_len) != 0) {
        fprintf(stderr, "ERROR: cannot write %s\n", out_path);
        free(gbk); return -1;
    }
    free(gbk);
    *converted = 1;
    return 0;
}

/* ── CJK 检测（文件内容）─────────────────────────────────────────────────── */

static int check_cjk_file(const char *filepath)
{
    size_t len;
    unsigned char *data = read_file(filepath, &len);
    if (!data) return 0;
    int result = has_chinese_in_strings(data, len);
    free(data);
    return result;
}

/* ── 清理陈旧副本 ────────────────────────────────────────────────────────── */

static void prune_stale(const char *out_root, strlist_t *active)
{
    strlist_t out_files;
    strlist_init(&out_files, MAX_FILES);
    scan_files(out_root, out_root, NULL, 0, &out_files, &out_files, 0);

    /* 构建 active 集合 */
    typedef struct { char *key; } set_t;
    set_t *active_set = malloc(active->count * sizeof(set_t));
    if (!active_set) { strlist_free(&out_files); return; }
    for (int i = 0; i < active->count; i++) {
        char norm[MAX_PATH_LEN];
        const char *rel = relpath(active->items[i], out_root);
        /* normalize slashes */
        int j = 0;
        for (const char *s = rel; *s; s++) {
            norm[j++] = (*s == '/') ? '\\' : *s;
        }
        norm[j] = 0;
        active_set[i].key = _strdup(norm);
    }

    for (int i = 0; i < out_files.count; i++) {
        const char *fn = out_files.items[i];
        const char *rel = relpath(fn, out_root);
        char norm[MAX_PATH_LEN];
        int j = 0;
        for (const char *s = rel; *s; s++)
            norm[j++] = (*s == '/') ? '\\' : *s;
        norm[j] = 0;

        int found = 0;
        for (int k = 0; k < active->count; k++) {
            if (active_set[k].key && _stricmp(norm, active_set[k].key) == 0)
                { found = 1; break; }
        }
        if (!found) DeleteFileA(fn);
    }

    for (int i = 0; i < active->count; i++) free(active_set[i].key);
    free(active_set);
    strlist_free(&out_files);
}

/* ── 参数解析 ────────────────────────────────────────────────────────────── */

static scan_status_t parse_args(int argc, char *argv[], gbk_cfg_t *cfg)
{
    memset(cfg, 0, sizeof(*cfg));
    cfg->full_scan_threshold = 0;

    static const char *exclude_buf[32];
    static const char *file_buf[MAX_FILES];
    cfg->excludes = exclude_buf;
    cfg->files    = file_buf;

    int i = 1;
    while (i < argc) {
        if (strcmp(argv[i], "-s") == 0 && i + 1 < argc) {
            cfg->src = argv[++i];
        } else if (strcmp(argv[i], "-o") == 0 && i + 1 < argc) {
            cfg->out = argv[++i];
        } else if (strcmp(argv[i], "-x") == 0 && i + 1 < argc) {
            if (cfg->exclude_count < 32)
                cfg->excludes[cfg->exclude_count++] = argv[++i];
        } else if (strcmp(argv[i], "--mtime-filter") == 0 && i + 1 < argc) {
            cfg->mtime_filt = argv[++i];
        } else if (strcmp(argv[i], "--full-scan-threshold") == 0 && i + 1 < argc) {
            cfg->full_scan_threshold = atoi(argv[++i]);
        } else if (strcmp(argv[i], "--force") == 0) {
            cfg->force = 1;
        } else if (strcmp(argv[i], "--list") == 0) {
            cfg->list_only = 1;
        } else if (strcmp(argv[i], "-q") == 0) {
            cfg->quiet = 1;
        } else if (strcmp(argv[i], "--") == 0) {
            i++;
            while (i < argc && cfg->file_count < MAX_FILES)
                cfg->files[cfg->file_count++] = argv[i++];
            break;
        } else if (strcmp(argv[i], "--help") == 0 || strcmp(argv[i], "-h") == 0) {
            puts("gbk_encode -s DIR -o DIR [-x DIR] [--mtime-filter STAMP]");
            puts("             [--full-scan-threshold N] [--force] [--list] [-q] [-- FILE...]");
            return SCAN_ERR_ARGS;
        } else if (argv[i][0] != '-') {
            if (cfg->file_count < MAX_FILES)
                cfg->files[cfg->file_count++] = argv[i];
        } else {
            i++;
        }
        i++;
    }
    if (!cfg->src || !cfg->out) return SCAN_ERR_ARGS;
    return SCAN_OK;
}

/* ── 主函数 ──────────────────────────────────────────────────────────────── */

int main(int argc, char *argv[])
{
    gbk_cfg_t cfg;
    if (parse_args(argc, argv, &cfg) != SCAN_OK) return 1;

    /* 计算绝对路径 */
    char src_abs[MAX_PATH_LEN], out_abs[MAX_PATH_LEN];
    if (!GetFullPathNameA(cfg.src, sizeof(src_abs), src_abs, NULL)) {
        fprintf(stderr, "ERROR: source directory not found: %s\n", cfg.src);
        return 1;
    }
    if (!GetFullPathNameA(cfg.out, sizeof(out_abs), out_abs, NULL)) {
        fprintf(stderr, "ERROR: invalid output directory: %s\n", cfg.out);
        return 1;
    }
    /* 确保 out 目录存在 */
    mkdir_recursive(out_abs);

    /* 确定文件列表 */
    strlist_t cjk_files;
    strlist_init(&cjk_files, MAX_FILES);

    long long filter_ts = 0;
    if (cfg.mtime_filt) {
        filter_ts = file_mtime(cfg.mtime_filt);
    }

    if (cfg.file_count > 0) {
        /* 显式文件 */
        for (int i = 0; i < cfg.file_count; i++) {
            char full[MAX_PATH_LEN];
            path_join(full, sizeof(full), src_abs, cfg.files[i]);
            if (cfg.list_only || check_cjk_file(full)) {
                strlist_add(&cjk_files, cfg.files[i]);
            }
        }
    } else {
        /* 扫描目录 */
        if (!cfg.quiet) fprintf(stderr, "[gbk_encode] Scanning: %s ...\n", src_abs);

        strlist_t all_files, changed_files;
        strlist_init(&all_files, MAX_FILES);
        strlist_init(&changed_files, MAX_FILES);

        scan_files(src_abs, src_abs, cfg.excludes, cfg.exclude_count,
                    &all_files, &changed_files, filter_ts);

        /* --full-scan-threshold 判定 */
        strlist_t *candidates = &changed_files;
        int is_full_scan = 0;
        if (filter_ts > 0 && cfg.full_scan_threshold > 0
            && changed_files.count > cfg.full_scan_threshold) {
            candidates = &all_files;
            is_full_scan = 1;
        }

        if (candidates->count == 0) {
            if (!cfg.quiet) puts("[gbk_encode] No files with Chinese runtime strings found.");
            strlist_free(&all_files);
            strlist_free(&changed_files);
            return 0;
        }

        /* CJK 检测 */
        for (int i = 0; i < candidates->count; i++) {
            if (check_cjk_file(candidates->items[i])) {
                const char *rel = relpath(candidates->items[i], src_abs);
                strlist_add(&cjk_files, rel);
            }
        }

        /* 日志 */
        if (!cfg.quiet && cfg.mtime_filt && cfg.full_scan_threshold > 0) {
            const char *mode = is_full_scan ? "full-scan" : "incremental";
            fprintf(stderr, "[gbk_encode] mtime-filter: %d changed (%s, threshold=%d)\n",
                    changed_files.count, mode, cfg.full_scan_threshold);
        }

        strlist_free(&all_files);
        strlist_free(&changed_files);
    }

    if (cjk_files.count == 0) {
        if (!cfg.quiet) puts("[gbk_encode] No files with Chinese runtime strings found.");
        return 0;
    }

    /* --list 模式 */
    if (cfg.list_only) {
        qsort(cjk_files.items, cjk_files.count, sizeof(char *), strlist_cmp);
        for (int i = 0; i < cjk_files.count; i++)
            puts(cjk_files.items[i]);
        strlist_free(&cjk_files);
        return 0;
    }

    /* 剪枝（仅全量扫描时） */
    if (cfg.file_count == 0 && cfg.mtime_filt == NULL) {
        prune_stale(out_abs, &cjk_files);
    }

    /* 转换 */
    if (!cfg.quiet)
        fprintf(stderr, "[gbk_encode] %d file(s) with Chinese strings\n", cjk_files.count);

    int converted = 0, skipped = 0;
    for (int i = 0; i < cjk_files.count; i++) {
        int was_converted = 0;
        if (convert_file(src_abs, out_abs, cjk_files.items[i],
                          cfg.force, &was_converted) != 0) {
            strlist_free(&cjk_files);
            return 1;
        }
        if (was_converted) {
            converted++;
            if (!cfg.quiet) fprintf(stderr, "  GBK  %s\n", cjk_files.items[i]);
        } else {
            skipped++;
        }
    }

    if (!cfg.quiet) {
        char buf[256];
        int off = snprintf(buf, sizeof(buf), "[gbk_encode] Done: %d converted", converted);
        if (!cfg.force && skipped > 0)
            off += snprintf(buf + off, sizeof(buf) - off, ", %d skipped (up-to-date)", skipped);
        snprintf(buf + off, sizeof(buf) - off, ", %d total\n", cjk_files.count);
        fputs(buf, stderr);
    }

    strlist_free(&cjk_files);
    return 0;
}
