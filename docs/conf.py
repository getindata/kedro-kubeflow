# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))
import re
from pprint import pprint

from pip._vendor import pkg_resources

from kedro_kubeflow import __name__ as _package_name
from kedro_kubeflow import __version__ as release

# -- Project information -----------------------------------------------------

project = "Kedro Kubeflow Plugin"
copyright = "2020, GetInData"
author = "GetInData"

myst_substitutions = {
    "tested_kedro": "0.17.7",
    "release": release,
}

# The full version, including alpha/beta/rc tags
version = re.match(r"^([0-9]+\.[0-9]+).*", release).group(1)
_package_name = _package_name.replace("_", "-")
_package = pkg_resources.working_set.by_key[_package_name]


# Extending keys for subsitutions with versions of package
def update_templates_with_requirements(packages_set, label):
    """Local function for updating template labels with requirements"""
    myst_substitutions.update({label + p.name: str(p) for p in packages_set})

    built_packages = {}
    for p in packages_set:
        try:
            req_label = label + "build_" + p.name
            built_packages[req_label] = pkg_resources.get_distribution(
                p
            ).version
        except pkg_resources.DistributionNotFound:
            pass
        myst_substitutions.update(built_packages)

    conditions = {
        "upper": ["<", "<=", "~=", "==", "==="],
        "lower": [">", ">=", "~=", "==", "==="],
    }
    for k, cond in conditions.items():
        myst_substitutions.update(
            {
                label
                + k
                + "_"
                + p.name: "".join(
                    [
                        "".join(i)
                        for i in filter(lambda x: x[0] in cond, p.specs)
                    ]
                )
                for p in packages_set
            }
        )


base_requirements = set(_package.requires())
extra_requires = {
    extra: set(_package.requires(extras=(extra,))) - base_requirements
    for extra in _package.extras
}
update_templates_with_requirements(base_requirements, "req_")
for extra, reqs in extra_requires.items():
    update_templates_with_requirements(reqs, f"req_{extra}_")


print("Available patterns for substituion:")
pprint(myst_substitutions)

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    # "sphinx.ext.autodoc",
    # "sphinx.ext.napoleon",
    # "sphinx_autodoc_typehints",
    # "sphinx.ext.doctest",
    # "sphinx.ext.todo",
    # "sphinx.ext.coverage",
    # "sphinx.ext.mathjax",
    # "sphinx.ext.ifconfig",
    # "sphinx.ext.viewcode",
    # "sphinx.ext.mathjax",
    "myst_parser",
    "sphinx_rtd_theme",
]
myst_enable_extensions = [
    "replacements",
    "strikethrough",
    "substitution",
]

# Add any paths that contain templates here, relative to this directory.

autosummary_generate = True
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

html_theme_options = {
    "collapse_navigation": False,
    "style_external_links": True,
}


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ["_static"]

language = "en"

pygments_style = "sphinx"
