### Take cleaned applicant data and load it to a PostgreSQL database or create one. It should take in link to the SQL server and load the data from the cleaned applicant JSON file into the SQL.

# Create a connection to the SQL server

from pathlib import Path
import psycopg

## Getting connection to database
connection = psycopg.connect(
    dbname="heliumdb", 
    user="postgres")

# Cursor creation
with connection.cursor() as cur:

    # Insert JSON from module_2 into SQL
    module_2_cleaned_path = Path(__file__).resolve().parent.parent/"module_2/cleaned"
    
    cur.execute(
        """INSERT * FROM applicants"""
    )
    print(cur.fetchall())
