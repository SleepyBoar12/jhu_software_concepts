Geunyong Son
Johns Hopkins University Fall 2026
------------------------------------------------
I used homebrew to create the postgreSQL
1. I am going to create a postgreSQL database and load it with cleaned grad cafe
2. Answer the questions with SQL queries and then create a pdf for how SQL queries work
3. Create SQLAlchemy ORM of my postgreSQL database
4. Answer the questions again with the SQLAlchemy's functions and sessions
5. Use one question I answered in the readme.md file for differences between raw SQL vs SQLAlchemy.
6. Create a dynamic Flask Webpage with analysis page and a button that can pull data
7. Create a "Update Analysis" button which re-query postgreSQL and display most up to date analysis.
8. Create a written reflection
------------------------------------------------
SQL and SQLAlchemy Comparison

The question I would like to examine is the 1st question:
How many entries in your database are from applicants who applied for Fall 2026?

In SQL:
SELECT COUNT(*) AS fall_2026_entries
FROM applicants
WHERE term = %s;

In SQLAlchemy:
select(func.count(Applicant.p_id)).where(Applicant.term == "Fall 2026")

The clear benefit for using SQLAlchemy is that because this is all interactable with python and not a wall of text, the IDE can pick up the errors and tell me where things went wrong and how functions should be called and informs whether or not I have misspelled. This helps immensely to understand and debug the code when things go wrong. However, setting up SQLAlchemy is a lot more laborious and cumbersome as I had to set up the engine, make sure all the data interact with each other as intended, and that they are mapped appropriately before analysis can be done. Smaller and infrequent queries are demonstrably more suited for psycopg whereas more complex and routine queries that need to work with other systems would be better suited with SQLAlchemy.