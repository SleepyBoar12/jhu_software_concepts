clean.py — transformation
=========================

Location: ``module_2/clean.py``. The cleaner groups applicant main, details,
and comment rows from saved ``data_*.html`` pages. It extracts badges for term,
nationality, GRE, and GPA, and returns dictionaries with source field names.
``save_data()`` writes a JSON array, rather than JSON Lines.

BeautifulSoup is required to execute the cleaner; its import is mocked only
for the documentation build.

.. automodule:: module_2.clean
   :members: clean_data, save_data, load_data, _get_badge_value, _parse_html_file
   :private-members: _get_badge_value, _parse_html_file
