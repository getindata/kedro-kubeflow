"""kedro_kubeflow module."""
from setuptools import find_packages, setup

with open("README.md") as f:
    README = f.read()

# Runtime Requirements.
INSTALL_REQUIRES = [
    "kedro>=0.18.1, <0.19.0",
    "click>=8.0.4",
    "kfp>=1.8.12,<2.0",
    "tabulate>=0.8.7",
    "semver~=2.10",
    "google-auth<2.0dev",
    "fsspec<=2022.1,>=2021.4",
]

# Dev Requirements
EXTRA_REQUIRE = {
    "mlflow": ["kedro-mlflow~=0.11.1"],
    "tests": [
        "pytest>=5.4.0, <8.0.0",
        "pytest-cov>=2.8.0, <4.0.0",
        "pytest-subtests>=0.5.0, <1.0.0",
        "tox==3.25.1",
        "pre-commit==2.20.0",
        "responses>=0.13.4",
    ],
    "docs": [
        "sphinx~=5.0.2",
        "sphinx_rtd_theme==1.0.0",
        "myst-parser==0.18.0",
    ],
    "gcp": [
        "google-auth<3",
        "gcsfs<=2022.1,>=2021.4",
    ],
}

setup(
    name="kedro-kubeflow",
    version="0.7.0",
    description="Kedro plugin with Kubeflow support",
    long_description=README,
    long_description_content_type="text/markdown",
    license="Apache Software License (Apache 2.0)",
    python_requires=">=3",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    keywords="kedro kubeflow plugin",
    author="Mateusz Pytel, Mariusz Strzelecki",
    author_email="mateusz@getindata.com",
    url="https://github.com/getindata/kedro-kubeflow/",
    packages=find_packages(exclude=["ez_setup", "examples", "tests", "docs"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRA_REQUIRE,
    entry_points={
        "kedro.project_commands": ["kubeflow = kedro_kubeflow.cli:commands"],
        "kedro.hooks": [
            "kubeflow_mlflow_tags_hook = kedro_kubeflow.hooks:mlflow_tags_hook",
        ],
    },
)
