"""Build optional cython modules."""

import logging
import os
from distutils.command.build_ext import build_ext
from pathlib import Path

_LOGGER = logging.getLogger(__name__)

try:
    from setuptools import Extension
except ImportError:
    from distutils.core import Extension


TO_CYTHONIZE = [
    "src/dbus_fast/aio/message_reader.py",
    "src/dbus_fast/message.py",
    "src/dbus_fast/message_bus.py",
    "src/dbus_fast/service.py",
    "src/dbus_fast/signature.py",
    "src/dbus_fast/unpack.py",
    "src/dbus_fast/_private/address.py",
    "src/dbus_fast/_private/marshaller.py",
    "src/dbus_fast/_private/unmarshaller.py",
]

EXTENSIONS = [
    Extension(
        ext.removeprefix("src/").removesuffix(".py").replace("/", "."),
        [ext],
        language="c",
        extra_compile_args=["-O3", "-g0"],
    )
    for ext in TO_CYTHONIZE
]


class BuildExt(build_ext):
    def build_extensions(self):
        if self.parallel is None:
            self.parallel = os.cpu_count() or 1
        if not self.inplace:
            # Poetry's wheel build directory uses the interpreter cache tag,
            # which is shared by the regular and free-threaded builds.
            for extension in self.extensions:
                output = Path(self.get_ext_fullpath(extension.name))
                module = extension.name.rsplit(".", 1)[-1]
                for artifact in output.parent.glob(f"{module}.*"):
                    if artifact != output and artifact.suffix in {".so", ".pyd"}:
                        artifact.unlink(missing_ok=True)
        try:
            super().build_extensions()
        except Exception:
            if os.environ.get("REQUIRE_CYTHON"):
                raise
            _LOGGER.debug("Failed to build extensions", exc_info=True)


def build(setup_kwargs):
    if os.environ.get("SKIP_CYTHON"):
        return
    try:
        from Cython.Build import cythonize  # noqa: PLC0415

        setup_kwargs.update(
            {
                "ext_modules": cythonize(
                    EXTENSIONS,
                    compiler_directives={"language_level": "3"},  # Python 3
                ),
                "cmdclass": {"build_ext": BuildExt},
            }
        )
        setup_kwargs["exclude_package_data"] = {
            pkg: ["*.c"] for pkg in setup_kwargs["packages"]
        }
    except Exception:
        if os.environ.get("REQUIRE_CYTHON"):
            raise
