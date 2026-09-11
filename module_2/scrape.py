from selenium import webdriver
import urllib3
import certifi
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path
import argparse
import subprocess
import sys
import time

"""
This program is designed to access (www.thegradcafe.com) and going to
(Admissions) tab to collect grad school entries made by the community:

1. I'm going to use Selenium's WebDriver to webscrape to get the HTML page by
page from the website. I am going to do it concurrently. 

2. I'm going to use BeautifulSoup alongside Regex to gather get the inputs from
those HTML files

3. Once the data is collected, I am going to aggregate the data into a json
object.
"""

#    # Argparse to create workers to do the scraping
#    cli= argparse.ArgumentParser()
#    cli.add_argument("--worker", action= "store_true")
#    cli.add_argument("--start-url")
#    cli.add_argument("--pages", type= int, default= 5)
#    cli.add_argument("--output-dir", type= Path)
#    args= cli.parse_args()
#
#    if args.pages < 1:
#        cli.error("--pages must be at least 1")
#
#    # Start 3 copies working on 3 different parts of the time, I picked the earliest date thegradcafe has to now.
#    if not args.worker:
#        start_urls = [
#            "https://www.thegradcafe.com/survey?added_start=2020-01-01&added_end=2025-12-31",
#            "https://www.thegradcafe.com/survey?added_start=2013-01-01&added_end=2019-12-31",
#            "https://www.thegradcafe.com/survey?added_start=2006-01-01&added_end=2012-12-31"        
#        ]

### Creating webscraper-- ALL PARAMS WRITTEN HERE
user_agent="scrape_respectfully"
url="https://www.thegradcafe.com"
num = 3000 # number of pages to scrape


# Configurations
options = webdriver.ChromeOptions()
options.add_argument(f"--user-agent={user_agent}")

### Check if robots.txt complies with being scraped with URLLIB
### Use urllib3 to manage URLs and check if they're legit
robots_url = urljoin(url, "/robots.txt")
http = urllib3.PoolManager(
    cert_reqs = "CERT_REQUIRED",
    ca_certs=certifi.where(),
)

# Wrap in try/except (to catch connection problem):
try:
    response = http.request(
        "GET",
        robots_url,
        headers = {"User-Agent": user_agent},
        timeout=urllib3.Timeout(connect=5, read=10),
    )
except urllib3.exceptions.HTTPError as error:
    raise SystemExit(f"Can't retrieve robots.txt: {error}")

# Catching HTTPS error response
if response.status != 200:
    raise SystemExit(f"HTTPS error: HTTP {response.status}")

# Compliance with website permission
robots_txt = response.data.decode("utf-8", errors="replace")

parser = RobotFileParser(robots_url)
parser.parse(robots_txt.splitlines())
allow = parser.can_fetch(user_agent, url)

if not allow:
    print("Not allowed to scrape website")
else:
    print("website allowed to scrape!")

# Creating a survey page URL for scraping
cdriver= webdriver.Chrome(options=options)
survey_url= urljoin(url, "/survey")

### Scraping algorithm
try:
    cdriver.get(survey_url)
    pages_copied = 0

    # Scrape pages until reaching that number
    while pages_copied < num:
            
        # Gathering, wait until "html body" is available
        pages_copied = pages_copied + 1

        WebDriverWait(cdriver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Select page source and write them into "module_2/collected/data.html"
        html = cdriver.page_source

        # Folder where the data will go
        folder = Path(__file__).resolve().parent / "collected"
        output_path = folder / f"data_{pages_copied}.html"
        output_path.write_text(html, encoding="utf-8")

        # To break the while loop once the number reaches 5
        if pages_copied == num:
            break

        # result successions
        result_locator = (By.CSS_SELECTOR,'a[href^="/result/"]',)
        prev_result_url = cdriver.find_element(*result_locator).get_attribute("href")

        # Go to the next page (problem: there are ads that block the button)
        # (Going to jump to the next url directly with WebDriver)
        next_link = WebDriverWait(cdriver, 10).until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Next"))
        )
        # See URL destination URL first
        next_url = next_link.get_attribute("href")

        if not next_url:
            raise RuntimeError("next_link has no destination URL")
        
        # Jumping to the next URL
        cdriver.get(next_url)

        # Wait until different page
        WebDriverWait(cdriver, 10).until(lambda driver: driver.find_element(
        *result_locator).get_attribute("href") != prev_result_url)


# Error
except Exception as error:
    print(f"webscraping error, scraping algorithm broke, HTTPS: {error}")
     
### Terminating scraper
finally:
    cdriver.quit()