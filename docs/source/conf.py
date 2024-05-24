# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from sphinx.ext.autodoc import between

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.append(os.path.abspath('../../'))
sys.path.append(os.path.abspath('../../qmiotools/'))
sys.path.append(os.path.abspath('../../qmiotools/integrations'))


def setup(app):
    app.add_config_value('toc_filter_exclude', [], 'html')
    app.connect('autodoc-process-docstring',
                between('^.*SIGNATURE.*$', exclude=True))
    # app.add_css_file('css/custom.css')
    # app.add_js_file('js/custom.js')

    return app

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Qmiotools'
copyright = '2024, Andrés Gómez (CESGA)'
author = 'Andrés Gómez (CESGA)'
release = '0.1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = []

extensions = [
   'sphinx.ext.duration',
   'sphinx.ext.doctest',
   'sphinx.ext.autodoc',
   'sphinx.ext.autosummary',
   'sphinx.ext.doctest', 
   'sphinx.ext.mathjax',
   'sphinx.ext.napoleon',
]
autodoc_mock_imports = [ "numpy","scipy", "pandas", "psutil",
    "qiskitqmio","tkbackend", "qiskit", "qiskit_aer", "pytket", "qmio-run", "networkx"]

autodoc_default_options = {
    'members': '',
    'member-order': 'bysource',
    'undoc-members': '',
    'exclude-members': 'version'
}
exclude_paterns = ["**/qmiotools.version.rst"]

master_doc = 'index'
napoleon_google_docstring = True
# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'classic'
html_static_path = ['_static']

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
html_show_sphinx = False

html_logo = "logo_Qmio_v5-azul-300x80.png"
html_show_sourcelink = False
