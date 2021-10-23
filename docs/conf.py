#!/usr/bin/env python3
# Sphinx config

import sys
import os

_project_dir = os.path.abspath('..')
sys.path.insert(0, _project_dir)

# -- General configuration ------------------------------------------------

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
]

source_suffix = '.rst'
master_doc = 'index'

# General information about the project.
project = 'keybox'
copyright = '2015–2020, Radek Brich'

# The short X.Y version.
version = open(_project_dir + '/VERSION', 'r').read().strip()
# The full version, including alpha/beta/rc tags.
release = version

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all
# documents.
default_role = 'py:obj'

pygments_style = 'sphinx'


# -- Options for HTML output ----------------------------------------------

html_theme = 'classic_globaltoc'
html_theme_path = ['_themes']
html_theme_options = {
#    'collapsiblesidebar': False,
}

# Output file base name for HTML help builder.
htmlhelp_basename = 'keyboxdoc'


# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    'papersize': 'a4paper',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    ('index', 'keybox.tex', 'Keybox manager', 'Radek Brich', 'manual'),
]

# If false, no module index is generated.
latex_domain_indices = False


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'keybox', 'Keybox manager', ['Radek Brich'], 1),
    ('format', 'keybox', 'Keybox file format', ['Radek Brich'], 5),
]
