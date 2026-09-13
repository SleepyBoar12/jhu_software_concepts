from selenium import webdriver
import urllib3
import certifi
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pathlib import Path

"""
This program is designed to access (www.thegradcafe.com) and going to
(Admissions) tab to collect grad school entries made by the community:

1. First of all, I am going to check if the website allows for scraping by checking
its /robots.txt file to look for its policy on "User-Agent". If scraping is allowed,
the program will print out that it is okay to do it, this will be done by Python's urllib

2. After permission, I'm going to use Selenium's WebDriver to webscrape to get
the HTML page by page from the website using the Chrome browser to enter and view
the webpages. Because I don't want the scraping to take a long time, I am going to download
raw HTML of the pages in its entirety into my folder.

3. Once data is gathered, "clean.py" will go through the HTML in "collected" folder
to produce the JSON file.
"""

### Creating webscraper-- ALL PARAMS WRITTEN HERE
user_agent = "scrape_respectfully"
url = "https://www.thegradcafe.com"
route = "/survey"
num = 5 # number of pages to scrape
# Write "test" or "collected" depending on where in the module_2 folder you
# want files to go
location = "test"

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

# Yes for user agent and for the purpose of "search"
parser = RobotFileParser(robots_url)
parser.parse(robots_txt.splitlines())
allow = parser.can_fetch(user_agent, url) 

if not allow:
    print("Not allowed to scrape website")
else:
    print("website allowed to scrape!")

# Creating a web browser and going into the "survey" section of the website
cdriver= webdriver.Chrome(options=options)
survey_url= urljoin(url, route)

### Scraping algorithm
def scrape_data(cdriver: webdriver, survey_url: str, num: int):
    pages_copied = 0
    try:
        cdriver.get(survey_url)

        # Scrape pages until reaching that number
        while pages_copied < num:
            WebDriverWait(cdriver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Select page source and write them into "module_2/collected/data.html"
            html = cdriver.page_source

            # Folder where the data will go using Path to navigate folder within "module_2"
            # I am using (__file__) -> parent -> folder because it breaks often (I don't know why)
            # if I wrote the location in the Path("...") directly
            folder = Path(__file__).resolve().parent/location
            if folder.exists() == False:
                print("output directory isn't linked or doesn't exist")
            output_path = folder / f"data_{pages_copied + 1}.html"
            output_path.write_text(html, encoding="utf-8")

            pages_copied = pages_copied + 1
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
                raise RuntimeError("next_link has no destination URL (check internet connection?)")
            
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
    return print(f"scraping terminated, pull {pages_copied} pages")

if __name__ == "__main__":
    scrape_data(cdriver, survey_url, num)
