"""Kiểm tra import nội bộ trên toàn bộ mã nguồn."""

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LOCAL_PACKAGES = {"core", "database", "ui"}
IGNORED_DIRECTORIES = {".git", ".venv", "venv", "__pycache__", "build", "dist"}


def _module_exists(path):
    """Hỗ trợ module Python, package thường và namespace package."""
    return path.with_suffix(".py").is_file() or path.is_dir()


class LocalImportTests(unittest.TestCase):
    """Đảm bảo import nội bộ trỏ tới module hoặc package tồn tại."""

    def test_local_import_targets_exist(self):
        missing = []
        source_files = (
            source for source in ROOT.rglob("*.py")
            if not any(part in IGNORED_DIRECTORIES for part in source.relative_to(ROOT).parts)
        )

        for source in source_files:
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

        self.assertEqual(
            missing,
            [],
            "Import nội bộ không tồn tại:\n" + "\n".join(missing),
        )

    def test_legacy_compatibility_packages_are_removed(self):
        self.assertFalse((ROOT / "core" / "repositories").exists())
        self.assertFalse((ROOT / "core" / "services").exists())

    def test_empty_root_package_initializers_are_removed(self):
        for package in ("core", "database", "ui"):
            self.assertFalse((ROOT / package / "__init__.py").exists())


if __name__ == "__main__":
    unittest.main()
