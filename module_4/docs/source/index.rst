GradCafe application
====================

This application stores graduate admissions records in PostgreSQL and displays
eleven analyses through Flask. These docs describe the code and tests in
`jhu_software_concepts <https://github.com/SleepyBoar12/jhu_software_concepts>`_.

Start with :doc:`overview` to configure the database and run the application.
See :doc:`architecture` for the data flow, :doc:`api/index` for documentation
generated from the Python modules, and :doc:`testing` for pytest commands and
fixtures. :doc:`publishing` explains how this documentation is built and hosted.

.. note::

   Scraping and HTML cleaning currently live in ``module_2``. Module 4 contains
   loading, SQL/ORM queries, Flask, and all of its tests. Its
   ``run_pull_pipeline()`` hook raises ``NotImplementedError`` during normal
   operation; tests replace it with predictable pulls. The API reference
   documents the actual Module 2 scraper and cleaner as well as Module 4.

.. toctree::
   :maxdepth: 2
   :caption: Contents

   overview
   architecture
   api/index
   testing
   publishing

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
