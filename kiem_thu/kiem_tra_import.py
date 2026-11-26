"""Kiểm tra các import nội bộ trỏ tới module/package có thật."""

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PACKAGES = {"ui", "database"}


def _module_exists(path):
    return path.with_suffix(".py").is_file() or (path / "__init__.py").is_file()


class LocalImportTests(unittest.TestCase):
    def test_local_import_targets_exist(self):
        missing = []

        for source in (ROOT / "ui").rglob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))

            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue

                if node.level:
                    target = source.parent
                    for _ in range(node.level - 1):
                        target = target.parent
                    if node.module:
                        target = target.joinpath(*node.module.split("."))
                elif node.module and node.module.split(".", 1)[0] in LOCAL_PACKAGES:
                    target = ROOT.joinpath(*node.module.split("."))
                else:
                    continue

                if not _module_exists(target):
                    missing.append(
                        f"{source.relative_to(ROOT)}:{node.lineno} -> {node.module or '.'}"
                    )

        self.assertEqual(missing, [], "Import nội bộ không tồn tại:\n" + "\n".join(missing))


if __name__ == "__main__":
    unittest.main()
