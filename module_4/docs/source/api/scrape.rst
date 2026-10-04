scrape.py — extraction
==========================

Location: ``module_2/scrape.py``. The scraper checks robots.txt and saves survey
pages with headless Chrome. Execute it only when the site permits access.
The configurable defaults request five pages and save command-line output
under ``module_2/test``. ``scrape_data()`` always quits its driver on exit.

Selenium and Chrome are required to execute this component; the documentation
build imports the module without starting a browser. The Module 4 tests do not
perform live scraping.

.. automodule:: module_2.scrape
   :members: scraping_is_allowed, create_driver, scrape_data, scrape_latest_pages
