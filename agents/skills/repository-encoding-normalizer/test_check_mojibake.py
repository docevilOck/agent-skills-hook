import importlib.util
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("check_mojibake.py")
SPEC = importlib.util.spec_from_file_location("check_mojibake", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
check_mojibake = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_mojibake)


class CheckMojibakeTests(unittest.TestCase):
    def test_scan_text_finds_replacement_and_question_run(self):
        findings = check_mojibake.scan_text("src/a.c", "正常\n乱码�\n???\n", allow_question=False)
        kinds = [item[0] for item in findings]
        self.assertIn("replacement-char", kinds)
        self.assertIn("question-run", kinds)

    def test_scan_text_ignores_literal_pattern_documentation_lines(self):
        findings = check_mojibake.scan_text(
            "SKILL.md",
            "对每个变更文件优先检查是否出现 `�`、连续 `?`、`??`、`???`、`锟斤拷`\n",
            allow_question=False,
        )
        self.assertFalse(findings)

    def test_should_be_bomless_matches_assembly_and_startup(self):
        self.assertTrue(check_mojibake.should_be_bomless("src/startup.s"))
        self.assertTrue(check_mojibake.should_be_bomless("boot/STARTUP.S"))
        self.assertTrue(check_mojibake.should_be_bomless("platform/vector_table.inc"))
        self.assertFalse(check_mojibake.should_be_bomless("src/module.c"))

    def test_inspect_file_flags_bom_on_bomless_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            target = root / "src" / "startup.s"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"\xef\xbb\xbfMOV R0, R0\n")
            findings = check_mojibake.inspect_file(str(root), "src/startup.s")
        self.assertTrue(any(item[0] == "unexpected-bom" for item in findings))


if __name__ == "__main__":
    unittest.main()
