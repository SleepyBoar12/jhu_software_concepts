Build and publish documentation
===================================

Local build
---------------

From the repository root, after installing ``module_5/requirements.txt``:

.. code-block:: bash

   python -m sphinx -b html -W --keep-going module_5/docs/source module_5/docs/build/html

Open ``module_5/docs/build/html/index.html``. The ``-W`` option makes warnings
fail the build, including broken autodoc imports. Generated HTML is ignored by
Git. Commit the documentation sources and build configuration.

Sphinx imports the actual Python modules for autodoc and viewcode. The modules
do not read credentials, create engines, open connections, start Flask, or run
ETL merely by being imported. The documentation configuration therefore needs
no credentials, dummy environment variables, or import monkeypatches.

Read the Docs
-----------------

The project is `JHU Software Concepts SleepyBoar12
<https://app.readthedocs.org/projects/jhu-software-concepts-sleepyboar12/>`_.
Open the `published HTML documentation <https://jhu-software-concepts-sleepyboar12.readthedocs.io/en/latest/>`_.

The repository-root ``.readthedocs.yaml`` currently publishes the original
Module-4 documentation. To publish this Module-5 copy, a Read the Docs
configuration must install ``module_5/requirements.txt`` and select
``module_5/docs/source/conf.py``. The local command above builds this copy
without changing the existing publication.

1. Sign in to `Read the Docs <https://app.readthedocs.org/>`_. Complete account
   creation and email verification if requested.
2. Choose **Add project** and select the GitHub repository, or choose
   **Configure manually** and use
   ``https://github.com/SleepyBoar12/jhu_software_concepts``.
3. Confirm the repository branch and configuration targeting Module 5.
4. Select **This file exists** when prompted for the configuration file.
5. Wait for the build to finish successfully, then open **View docs**.
6. Link that exact public documentation URL in both repository READMEs.

Read the Docs fetches committed, pushed source from GitHub; it cannot build
uncommitted local edits. With an integration/webhook configured, subsequent
pushes rebuild the documentation. Otherwise use **Build version** explicitly.
The existing ``Documentation`` GitHub Actions workflow checks the original
Module-4 documentation on pull requests and pushes to ``main``.

For current setup details, see the official
`project import guide <https://docs.readthedocs.com/platform/stable/intro/add-project.html>`_
and `configuration reference <https://docs.readthedocs.com/platform/stable/config-file/v2.html>`_.

Troubleshooting publication
-------------------------------

* Read the Docs Community needs a public source repository. If cloning fails
  with an authentication error, use a public documentation-only repository or
  deliberately change the source repository's visibility. Making the source
  repository public exposes its files and Git history, not just the docs.
* Verify that the build uses the intended branch and commit. A successful old
  build does not establish that the new application APIs are documented.
* Missing modules usually mean the requirements installation failed; inspect
  that step before changing autodoc directives.
* Warnings fail the build deliberately. Fix stale member names, headings, or
  cross-references rather than disabling the warning check.
* Database connection errors during autodoc indicate an import-time side
  effect; documentation builds should not need ``DATABASE_URL``.
* A successful build with no automatic updates usually indicates a missing
  webhook or integration. Trigger a manual build until it is configured.

Updating API pages
----------------------

The ``automodule`` directives refresh signatures and docstrings on every build.
Keep the setup, architecture, testing, and operational guides consistent with
those APIs. Scraping and cleaning remain in ``module_2``; Flask, loading,
queries, and database configuration are documented from ``module_5.src``.
