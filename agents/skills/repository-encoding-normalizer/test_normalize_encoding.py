import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("normalize_encoding.py")
SPEC = importlib.util.spec_from_file_location("normalize_encoding", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
normalize_encoding = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(normalize_encoding)


class NormalizePlanTests(unittest.TestCase):
    def test_detect_source_encoding_returns_gbk_lossy_for_mostly_gbk_text(self):
        payload = ("中文注释和字符串" * 6).encode("gbk") + b"\xff"
        self.assertEqual(normalize_encoding.detect_source_encoding(payload), "gbk-lossy")

    def test_detect_source_encoding_returns_big5_lossy_for_mostly_big5_text(self):
        payload = ("中文註解和字串" * 6).encode("big5") + b"\x80"
        self.assertEqual(normalize_encoding.detect_source_encoding(payload), "big5-lossy")

    def test_build_plan_separates_convert_and_migration_candidates(self):
        audit = {
            "results": [
                {
                    "path": "src/comment_only.c",
                    "encoding": "gbk",
                    "file_class": "comment_only",
                    "summary": {"comment": 4, "string": 0, "code": 0},
                    "lines": [],
                },
                {
                    "path": "src/runtime.c",
                    "encoding": "shift_jis",
                    "file_class": "string_or_runtime",
                    "summary": {"comment": 0, "string": 2, "code": 0},
                    "lines": [
                        [10, 'printf("中文");', [[8, "中", "string"], [9, "文", "string"]]],
                    ],
                },
            ]
        }
        plan = normalize_encoding.build_plan(audit, compiler="armcc", no_bom_files=set())
        self.assertEqual(len(plan["convert_files"]), 1)
        self.assertEqual(plan["convert_files"][0]["path"], "src/comment_only.c")
        self.assertEqual(len(plan["migration_candidates"]), 1)
        self.assertEqual(plan["migration_candidates"][0]["path"], "src/runtime.c")
        self.assertEqual(plan["migration_candidates"][0]["encoding"], "shift_jis")
        self.assertTrue(plan["migration_candidates"][0]["old_string_literals"])

    def test_build_plan_marks_mk_files_no_bom(self):
        audit = {
            "results": [
                {
                    "path": "src/inc_config.mk",
                    "encoding": "gbk",
                    "file_class": "comment_only",
                    "summary": {"comment": 2, "string": 0, "code": 0},
                    "lines": [],
                }
            ]
        }
        plan = normalize_encoding.build_plan(audit, compiler="armcc", no_bom_files=set())
        self.assertFalse(plan["convert_files"][0]["use_bom"])

    def test_should_use_bom_disables_bom_for_assembly_and_startup_files(self):
        self.assertFalse(normalize_encoding.should_use_bom("src/startup.s", "armcc", set()))
        self.assertFalse(normalize_encoding.should_use_bom("src/boot/STARTUP.S", "armcc", set()))
        self.assertFalse(normalize_encoding.should_use_bom("startup_stm32f10x_hd.s", "armcc", set()))
        self.assertFalse(normalize_encoding.should_use_bom("platform/vector_table.inc", "armcc", set()))
        self.assertTrue(normalize_encoding.should_use_bom("src/module.c", "armcc", set()))

    def test_plain_text_files_convert_directly(self):
        audit = {
            "results": [
                {
                    "path": "docs/readme.md",
                    "encoding": "gbk",
                    "file_class": "string_or_runtime",
                    "summary": {"comment": 0, "string": 4, "code": 0},
                    "lines": [[1, "这是说明文档", [[0, "这", "string"]]]],
                },
                {
                    "path": "notes/todo.txt",
                    "encoding": "big5",
                    "file_class": "mixed_comment_and_runtime",
                    "summary": {"comment": 1, "string": 3, "code": 0},
                    "lines": [[1, "待办事项", [[0, "待", "string"]]]],
                },
            ]
        }
        plan = normalize_encoding.build_plan(audit, compiler="armcc", no_bom_files=set())
        convert_paths = {item["path"] for item in plan["convert_files"]}
        self.assertIn("docs/readme.md", convert_paths)
        self.assertIn("notes/todo.txt", convert_paths)
        self.assertFalse(plan["migration_candidates"])

    def test_write_plan_report_outputs_json(self):
        plan = {
            "convert_files": [{"path": "src/a.c", "encoding": "gbk", "target_encoding": "utf-8-sig", "use_bom": True}],
            "migration_candidates": [{"path": "src/b.c", "encoding": "gbk", "reason": "contains runtime Chinese strings", "string_lines": [3]}],
            "skipped_files": [],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "plan.json"
            normalize_encoding.write_plan_report(plan, out_path)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["convert_files"][0]["path"], "src/a.c")
        self.assertEqual(payload["migration_candidates"][0]["path"], "src/b.c")

    def test_replace_string_in_source_uses_explicit_source_encoding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "runtime.c"
            text = '#include "includes.h"\nvoid f(void){printf("中文");}\n'
            source_path.write_bytes(text.encode("shift_jis", errors="replace"))
            normalize_encoding.replace_string_in_source(
                str(source_path),
                '#include "includes.h"',
                "texts.h",
                '"中文"',
                "TXT_HELLO",
                source_encoding="shift_jis",
            )
            rewritten = source_path.read_text(encoding="utf-8-sig")
        self.assertIn('#include "texts.h"', rewritten)
        self.assertIn("TXT_HELLO", rewritten)

    def test_convert_file_decodes_gbk_lossy_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "comment_only.c"
            original_text = "/* 中文注释中文注释中文注释 */\n"
            source_path.write_bytes(original_text.encode("gbk") + b"\xff")
            normalize_encoding.convert_file(str(source_path), use_bom=True)
            rewritten = source_path.read_text(encoding="utf-8-sig")
        self.assertIn("中文注释中文注释中文注释", rewritten)
        self.assertIn("\ufffd", rewritten)

    def test_convert_file_decodes_big5_lossy_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "comment_only_big5.c"
            original_text = "/* 中文註解中文註解中文註解 */\n"
            source_path.write_bytes(original_text.encode("big5") + b"\x80")
            normalize_encoding.convert_file(str(source_path), use_bom=False)
            rewritten = source_path.read_text(encoding="utf-8")
        self.assertIn("中文註解中文註解中文註解", rewritten)
        self.assertIn("\ufffd", rewritten)

    def test_replace_string_in_source_supports_explicit_lossy_encoding(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source_path = Path(tmpdir) / "runtime.c"
            text = '#include "includes.h"\nvoid f(void){printf("中文中文中文中文");}\n'
            source_path.write_bytes(text.encode("gbk") + b"\xff")
            normalize_encoding.replace_string_in_source(
                str(source_path),
                '#include "includes.h"',
                "texts.h",
                '"中文中文中文中文"',
                "TXT_HELLO",
                source_encoding="gbk-lossy",
            )
            rewritten = source_path.read_text(encoding="utf-8-sig")
        self.assertIn('#include "texts.h"', rewritten)
        self.assertIn("TXT_HELLO", rewritten)

    def test_apply_plan_converts_lossy_audit_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            source_path = root / "src" / "comment_only.c"
            source_path.parent.mkdir(parents=True, exist_ok=True)
            original_text = "/* 中文注释中文注释中文注释 */\n"
            source_path.write_bytes(original_text.encode("gbk") + b"\xff")

            audit = {
                "results": [
                    {
                        "path": "src/comment_only.c",
                        "encoding": "gbk-lossy",
                        "file_class": "comment_only",
                        "summary": {"comment": 12, "string": 0, "code": 0},
                        "lines": [],
                    }
                ]
            }

            plan = normalize_encoding.build_plan(audit, compiler="armcc", no_bom_files=set())
            normalize_encoding.apply_plan(str(root), plan)
            rewritten = source_path.read_text(encoding="utf-8-sig")

        self.assertEqual(plan["convert_files"][0]["encoding"], "gbk-lossy")
        self.assertIn("中文注释中文注释中文注释", rewritten)
        self.assertIn("\ufffd", rewritten)


if __name__ == "__main__":
    unittest.main()
