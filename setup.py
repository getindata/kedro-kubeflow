"""kedro_kubeflow module."""

from setuptools import find_packages, setup

with open("README.md") as f:
    README = f.read()

# Runtime Requirements.
INSTALL_REQUIRES = ["kedro>=0.16,<=0.18", "click", "kfp", "tabulate", "semver"]

# Dev Requirements
EXTRA_REQUIRE = {
    "mlflow": ["kedro-mlflow"],
    "test": ["pytest", "pytest-cov"],
    "dev": ["pytest", "pytest-cov", "pre-commit"],
}

setup(
    name="kedro-kubeflow",
    version="0.1.10",
    description="Kedro plugin with Kubeflow support",
    long_description=README,
    long_description_content_type="text/markdown",
    license="Apache Software License (Apache 2.0)",
    python_requires=">=3",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
    ],
    keywords="kedro kubeflow plugin",
    author=u"Mateusz Pytel, Mariusz Strzelecki",
    author_email="mateusz@getindata.com",
    url="https://github.com/getindata/kedro-kubeflow/",
    packages=find_packages(exclude=["ez_setup", "examples", "tests", "docs"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=INSTALL_REQUIRES,
    extras_require=EXTRA_REQUIRE,
    entry_points={
        "kedro.project_commands": [
            "kubeflow = kedro_kubeflow.plugin:commands"
        ],
        "kedro.hooks": [
            "kubeflow_cfg_hook = kedro_kubeflow.hooks:register_templated_config_loader",
        ],
    },
)
