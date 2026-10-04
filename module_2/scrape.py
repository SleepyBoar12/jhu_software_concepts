"""Collect recent GradCafe admissions pages with Selenium."""

from pathlib import Path
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import certifi
import urllib3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


### Keep the scraper configuration in one place.
user_agent = "scrape_respectfully"
url = "https://www.thegradcafe.com"
route = "/survey"
num = 5
location = "test"


def scraping_is_allowed(base_url=url, page_route=route):
    """Check robots.txt before requesting GradCafe admissions pages."""

    robots_url = urljoin(base_url, "/robots.txt")
    survey_url = urljoin(base_url, page_route)
    http = urllib3.PoolManager(
        cert_reqs="CERT_REQUIRED",
        ca_certs=certifi.where(),
    )

    try:
        response = http.request(
            "GET",
            robots_url,
            headers={"User-Agent": user_agent},
            timeout=urllib3.Timeout(connect=5, read=10),
        )
    except urllib3.exceptions.HTTPError as error:
        raise RuntimeError(f"Could not retrieve robots.txt: {error}") from error

    if response.status != 200:
        raise RuntimeError(
            f"GradCafe robots.txt returned HTTP {response.status}"
        )

    parser = RobotFileParser(robots_url)
    parser.parse(response.data.decode("utf-8", errors="replace").splitlines())
    return parser.can_fetch(user_agent, survey_url)


def create_driver(headless=True):
    """Create the Chrome driver used for one scraping operation."""

    options = webdriver.ChromeOptions()
    options.add_argument(f"--user-agent={user_agent}")

    # A server-triggered scrape should not open a visible browser window.
    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--window-size=1440,1200")
    return webdriver.Chrome(options=options)


def scrape_data(driver, survey_url, page_count, output_directory):
    """Save GradCafe survey pages as UTF-8 HTML and close the driver on exit.

    :param driver: Selenium driver used to navigate the survey.
    :param survey_url: URL of the first survey page.
    :param page_count: Number of pages to save.
    :param output_directory: Directory for numbered ``data_*.html`` files.
    :returns: List of saved :class:`pathlib.Path` objects.
    :raises RuntimeError: Navigation or page extraction fails.
    """

    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    saved_pages = []

    try:
        driver.get(survey_url)

        while len(saved_pages) < page_count:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            output_path = output_directory / f"data_{len(saved_pages) + 1}.html"
            output_path.write_text(driver.page_source, encoding="utf-8")
            saved_pages.append(output_path)

            if len(saved_pages) == page_count:
                break

            # Remember the first result so Selenium can verify that the next
            # page finished loading before it saves another HTML file.
            result_locator = (By.CSS_SELECTOR, 'a[href^="/result/"]')
            previous_result_url = driver.find_element(
                *result_locator
            ).get_attribute("href")

            next_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Next"))
            )
            next_url = next_link.get_attribute("href")

            if not next_url:
                raise RuntimeError("The next-page link has no destination URL")

            driver.get(next_url)
            WebDriverWait(driver, 10).until(
                lambda current_driver: current_driver.find_element(
                    *result_locator
                ).get_attribute("href")
                != previous_result_url
            )
    except Exception as error:
        raise RuntimeError(
            f"GradCafe scraping stopped after {len(saved_pages)} pages: {error}"
        ) from error
    finally:
        driver.quit()

    return saved_pages


def scrape_latest_pages(output_directory, page_count=num):
    """Check permission and scrape the newest GradCafe result pages."""

    if not scraping_is_allowed():
        raise PermissionError(
            "GradCafe robots.txt does not allow this scraper to access /survey"
        )

    survey_url = urljoin(url, route)
    driver = create_driver(headless=True)
    return scrape_data(driver, survey_url, page_count, output_directory)


if __name__ == "__main__":
    output_directory = Path(__file__).resolve().parent / location
    saved_pages = scrape_latest_pages(output_directory, num)
    print(f"Scraping completed: saved {len(saved_pages)} pages")
