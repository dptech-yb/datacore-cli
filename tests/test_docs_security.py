from pathlib import Path

import pytest

from scripts.generate_docs import regular_skill_files


def test_skill_publication_rejects_symbolic_links(tmp_path: Path) -> None:
    source = tmp_path / "skill"
    source.mkdir()
    (source / "SKILL.md").write_text("# Safe skill\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("must not be packaged\n", encoding="utf-8")
    link = source / "outside.txt"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symbolic links are unavailable on this platform")

    with pytest.raises(RuntimeError, match="must not contain symbolic links"):
        regular_skill_files(source)
