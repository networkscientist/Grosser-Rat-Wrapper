# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

sys.path.insert(0, os.path.abspath("../../src"))

project = "Grosser-Rat-Wrapper"
copyright = "2025, Peter Zweifel (networkscientist)"
author = "Peter Zweifel (networkscientist)"
release = "25.1.dev0"
language = "de"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.apidoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",  # For Google and NumPy style docstrings
    "sphinx.ext.viewcode",  # Optional: to include links to source code
    "myst_parser",
]

apidoc_module_dir = "../src/grosserratwrapper"
apidoc_output_dir = "api"
apidoc_excluded_paths = ["tests"]
apidoc_separate_modules = True

autosummary_generate = True  # Turn on sphinx.ext.autosummary

templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
