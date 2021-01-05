"""kedro_kubeflow module."""

from setuptools import find_packages, setup

with open("README.md") as f:
    readme = f.read()


def _parse_requirements(path, encoding="utf-8"):
    with open(path, mode="r", encoding=encoding) as file_handler:
        requirements = [
            x.strip() for x in file_handler if x.strip() and not x.startswith("-r")
        ]
    return requirements

# Runtime Requirements.
install_requires = _parse_requirements("requirements.txt")

# Dev Requirements
extra_require = {
    "test": _parse_requirements("requirements-dev.txt"),
    "dev": _parse_requirements("requirements-dev.txt"),
}



setup(
    name="kedro-kubeflow",
    version="0.1.6",
    description="Kedro plugin with Kubeflow support",
    long_description=readme,
    long_description_content_type="text/markdown",
    license="Apache Software License (Apache 2.0)",
    python_requires=">=3",
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="kedro kubeflow plugin",
    author=u"Mateusz Pytel",
    author_email="mateusz@getindata.com",
    url="getindata.com",
    packages=find_packages(exclude=["ez_setup", "examples", "tests", "docs"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require=extra_require,
    entry_points={
        "kedro.project_commands": ["kubeflow = kedro_kubeflow.plugin:commands"]
    },
)
