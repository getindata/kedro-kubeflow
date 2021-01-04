"""kedro_kubeflow module."""

from setuptools import find_packages, setup

with open("README.md") as f:
    readme = f.read()

# Runtime Requirements.
install_requires = ["kedro>=0.17.0", "click", "kfp", "tabulate"]

# Dev Requirements
extra_require = {
    "test": ["pytest", "pytest-cov"],
    "dev": ["pytest", "pytest-cov", "pre-commit"],
}


setup(
    name="kedro-kubeflow",
    version="0.1.6",
    description="Kedro plugin with Kubeflow support",
    long_description=readme,
    long_description_content_type="text/markdown",
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
    packages=find_packages(exclude=["ez_setup", "examples", "tests"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=install_requires,
    extras_require=extra_require,
    entry_points={
        "kedro.project_commands": ["kubeflow = kedro_kubeflow.plugin:commands"]
    },
)
