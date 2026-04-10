from __future__ import annotations

from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.egg_info import egg_info as _egg_info
from setuptools.command.sdist import sdist as _sdist


ROOT = Path(__file__).resolve().parent
ROOT_SKILL = ROOT / "SKILL.md"
PACKAGED_SKILL = ROOT / "src" / "data" / "SKILL.md"


def sync_packaged_skill() -> None:
    if not ROOT_SKILL.exists():
        raise FileNotFoundError(f"Missing root skill file: {ROOT_SKILL}")
    PACKAGED_SKILL.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT_SKILL, PACKAGED_SKILL)


class build_py(_build_py):
    def run(self) -> None:
        sync_packaged_skill()
        super().run()


class egg_info(_egg_info):
    def run(self) -> None:
        sync_packaged_skill()
        super().run()


class sdist(_sdist):
    def run(self) -> None:
        sync_packaged_skill()
        super().run()


setup(
    cmdclass={
        "build_py": build_py,
        "egg_info": egg_info,
        "sdist": sdist,
    }
)
