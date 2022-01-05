"""kedro_kubeflow module."""
from setuptools import find_packages, setup

with open("README.md") as f:
    README = f.read()

# Runtime Requirements.
INSTALL_REQUIRES = [
    "kedro>=0.16,<=0.18",
    "click<8.0",
    "kfp~=1.6.0",
    "tabulate>=0.8.7",
    "semver~=2.10",
    "google-auth<2.0dev",
    "protobuf<3.18.0",
]

# Dev Requirements
EXTRA_REQUIRE = {
    "mlflow": ["kedro-mlflow>=0.4.1"],
    "tests": [
        "pytest>=5.4.0, <7.0.0",
        "pytest-cov>=2.8.0, <3.0.0",
        "tox==3.23.1",
        "pre-commit==2.9.3",
        "responses>=0.13.4",
    ],
    "docs": [
        "sphinx==3.4.2",
        "recommonmark==0.7.1",
        "sphinx_rtd_theme==0.5.1",
    ],
    "vertexai": [
        "google-cloud-scheduler>=2.3.2",
    ],
}

setup(
    name="kedro-kubeflow",
    version="0.4.7",
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
        "kedro.project_commands": ["kubeflow = kedro_kubeflow.cli:commands"],
        "kedro.hooks": [
            "kubeflow_cfg_hook = kedro_kubeflow.hooks:register_templated_config_loader",
            "kubeflow_mlflow_tags_hook = kedro_kubeflow.hooks:mlflow_tags_hook",
        ],
    },
)
