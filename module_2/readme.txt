Geunyong Son
JHED ID: gson3@jh.edu
JHU Modern Software Concepts Fall 2026
-----------------------------------------------------------------
Explanation and robots.txt. Skip to implementation below

My strategy for this assignment is to first scrape 5 pages from the 
website see if scraper can run smoothly. Once I have confirmed that it can, I will
collect 3,000 pages. My goal is 60,000 rows, and since 1 page contains
20 data points, then the number of pages I need to go through is 60,000/20 which is
3,000 pages to get roughly around 60,000 data points.

I have read (www.thegradcafe.com/robots.txt), for the User_Agent: * where Content-Signal
is search = yes. The definition of search being:

"building a search index and providing search results (e.g., returning
hyperlinks and short excerpts from your website's contents). Search does not
include providing AI-generated search summaries." Which directly corresponds to my intended
use case.

For my goal of 3,000 pages, I would like to conduct an early test.
Once I have seen that the test result came as expected I will implement the code with
the larger webscraping, cleaning, and running it through the LLM.

The workflow basically was HTTPS -> HTML -> JSON

I used Chrome browser with Selenium to get past the Cloudflare to scrape the data. As for
HTTPS handling, I used URLLIB3 to manage certificates, handle requests, and manage errors.
However, when it comes to checking permission to scrape, I used URLLIB as there already was an
easy method for me to do that with robotparser() and can_fetch(). This was the step for the HTTPS.

As for getting HTTPS into HTML, I simply just copy/pasted page_source from Selenium into the
"collected" pile and used Path to portion all of them together. It took me around 40 minutes to get
3000 pages. I made the WebDriver wait until the next button appeared and use that for my next location
for my browser to go to. Rinse and repeat until every page is sourced.

I then used BeautifulSoup to parse the HTML. As for the selection of the fields and the strategy
to accumulate them, I asked ChatGPT to create the method for me to catch the fields. I tweaked the
locations to test on a small subset before using it on the entire collected pool of HTML.

Afterwards, I downloaded all the required files from llm_hosting with REPL Python and followed the
instructions for using app.py in llm_hosting on Bash. Once I could create the sample_output.json successfully,
I tried it with the "test", and then the entire collected set.

-----------------------------------------------------------------
IMPLEMENTATION HERE*

NOTE* IMPORTANT:
I have 3 folders:
- "collected": where the product of scrape.py goes to
- "cleaned": where the product of clean.py AND where the LLM scraping goes to
- "test": where I troubleshoot and test the programs of scrape, clean, and LLM with

*** Need to change "location" value in both clean.py and scrape.py to direct where
*** the files end up in!

To get started:
- write the folder path for "location" in scrape.py and clean.py
    - location can be either "test" or "collected" for scrape.py
    - location_to can be either "test" or "cleaned" for clean.py
    - location_from can be either "test" or "collected" for clean.py
- run scrape.py with "$python -m scrape"
- check to see if the data is gathered in the "../module_2/test" or "collected" folder
- run clean.py with "$python -m clean"
- check to see if the data is cleaned properly in "../module_2/test" or "cleaned" folder
- run "$python app.py \--file ../cleaned/gradcafe_results.json --out ../cleaned/llm_cleaned_results.json"