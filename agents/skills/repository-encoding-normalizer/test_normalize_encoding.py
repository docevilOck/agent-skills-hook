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


class NormalizeEncodingTests(unittest.TestCase):
    # ── 编码检测 ──────────────────────────────────────────────────────

    def test_detect_source_encoding_returns_gbk_lossy_for_mostly_gbk_text(self):
        payload = ("中文注释和字符串" * 6).encode("gbk") + b"\xff"
        self.assertEqual(normalize_encoding.detect_source_encoding(payload), "gbk-lossy")

    def test_detect_source_encoding_returns_big5_lossy_for_mostly_big5_text(self):
        payload = ("中文註解和字串" * 6).encode("big5") + b"\x80"
        self.assertEqual(normalize_encoding.detect_source_encoding(payload), "big5-lossy")

    # ── BOM 判断 ──────────────────────────────────────────────────────

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

    # ── 计划构建（新方案：全部归入 convert_files） ───────────────────

    def test_build_plan_all_non_utf8_go_to_convert_files(self):
        """comment_only 和 string_or_runtime 两类都应归入 convert_files，不再区分 migration_candidates。"""
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
        convert_paths = {item["path"] for item in plan["convert_files"]}
        self.assertIn("src/comment_only.c", convert_paths)
        self.assertIn("src/runtime.c", convert_paths)
        self.assertEqual(len(plan["convert_files"]), 2)
        self.assertNotIn("migration_candidates", plan)
        self.assertEqual(len(plan.get("skipped_files", [])), 0)

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
        self.assertNotIn("migration_candidates", plan)

    def test_build_plan_skips_already_utf8(self):
        audit = {
            "results": [
                {
                    "path": "src/utf8_file.c",
                    "encoding": "utf-8-sig",
                    "file_class": "comment_only",
                    "summary": {"comment": 1, "string": 0, "code": 0},
                    "lines": [],
                },
                {
                    "path": "src/gbk_file.c",
                    "encoding": "gbk",
                    "file_class": "comment_only",
                    "summary": {"comment": 2, "string": 0, "code": 0},
                    "lines": [],
                },
            ]
        }
        plan = normalize_encoding.build_plan(audit, compiler="armcc", no_bom_files=set())
        self.assertEqual(len(plan["convert_files"]), 1)
        self.assertEqual(plan["convert_files"][0]["path"], "src/gbk_file.c")
        self.assertEqual(len(plan["skipped_files"]), 1)
        self.assertEqual(plan["skipped_files"][0]["path"], "src/utf8_file.c")

    # ── 文件转换 ──────────────────────────────────────────────────────

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

    # ── 计划执行 ──────────────────────────────────────────────────────

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

    def test_write_plan_report_outputs_json(self):
        plan = {
            "convert_files": [{"path": "src/a.c", "encoding": "gbk", "target_encoding": "utf-8-sig", "use_bom": True}],
            "skipped_files": [{"path": "src/b.c", "reason": "already utf-8"}],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "plan.json"
            normalize_encoding.write_plan_report(plan, out_path)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["convert_files"][0]["path"], "src/a.c")
        self.assertEqual(payload["skipped_files"][0]["path"], "src/b.c")
        self.assertNotIn("migration_candidates", payload)


if __name__ == "__main__":
    unittest.main()
