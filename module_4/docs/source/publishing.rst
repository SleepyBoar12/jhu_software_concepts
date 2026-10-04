Build and publish documentation
===============================

Local build
-----------

Install ``module_4/requirements.txt``, activate the virtual environment, and
build from ``module_4``:

.. code-block:: bash

   cd module_4
   make -C docs html

Open ``docs/build/html/index.html``. The Makefile passes ``-W --keep-going``
so warnings fail the build, including broken autodoc imports. ``docs/build``
is ignored by Git; commit ``docs/source``, the build scripts, and configuration.
On Windows, run ``docs\make.bat html``.

``docs/source/conf.py`` selects ``sphinx_rtd_theme``, enables autodoc, and links
to highlighted Python source with viewcode.
It imports the real Module 4 modules under
temporary documentation-only environment settings. During those imports it
bypasses the local environment-file check and disables dotenv loading. It
does not read private credentials, create ``.env``, connect to PostgreSQL,
start Flask, or perform ETL. Optional Selenium and BeautifulSoup imports are
mocked for the earlier Module 2 API pages.

Read the Docs integration
--------------------------

The repository remote is
``git@github.com:SleepyBoar12/jhu_software_concepts.git``. Read the Docs uses
``.readthedocs.yaml`` at the repository root. It installs
``module_4/requirements.txt`` with Python 3.14 on Ubuntu 24.04 and builds
``module_4/docs/source/conf.py`` with warnings treated as errors.

1. Commit and push the documentation sources and ``.readthedocs.yaml`` to
   ``main``. The repository must be public for the community hosting service.
2. Sign in at `Read the Docs <https://app.readthedocs.org/>`_.
3. Add a project and import the GitHub repository, or enter the public
   repository URL manually if GitHub is not connected.
4. Set the default branch to ``main``. Read the Docs discovers the root
   configuration file and builds the ``latest`` version.
5. Confirm the build succeeds and use **View docs** to open its public URL.
   Add that exact URL to the repository README.

Enable the repository webhook/integration so new commits trigger Read the Docs
builds. If no webhook is connected, use the project's **Build version** control
after a push. ``.github/workflows/documentation.yml`` independently checks
documentation builds on pull requests and pushes to ``main``; a manual
**Run workflow** is also available. No database service or application secrets
are required to build docs. See
`the Read the Docs Sphinx guide <https://docs.readthedocs.com/platform/stable/intro/sphinx.html>`_
and `configuration reference <https://docs.readthedocs.com/platform/stable/config-file/v2.html>`_.

Updating API pages
------------------

API pages use ``automodule`` directives, so function signatures and docstrings
are refreshed from Python when Sphinx runs. Update the surrounding examples
and architecture/testing guides whenever behavior changes. The scraper and
cleaner pages reference their existing ``module_2`` locations. If they move
into Module 4 later, update those import paths and the architecture guide.
