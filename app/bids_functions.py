# coding: utf-8
import logging
from functions import limit_string
from functions import extract_dates
from functions import devtracker_sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import InvalidSessionIdException
from selenium.webdriver.support import expected_conditions as EC

# Browser Settings
sel_timeout = 30


def get_io_bids(driver, page_limit):
    """Gets All Bids from Bubbleio bids page and store them in dataframe

    Args:
        driver (webdriver): selenium webdriver object

    Returns:
        data[]: returns list of all scrapped bids
        :param driver:
        :param page_limit:
    """
    logging.info(f"[Bids]: Opening Bid Page")
    # Open App
    retry_count = 0
    pages_scrapped = 0
    bids_url = f"https://bubble.io/agency-requests/sent"
    driver.get(bids_url)
    # check for total Bids
    total_bids_path = "//div[@class='bubble-element Text cnaBaJp3']"
    total_bids = driver.find_element(By.XPATH, total_bids_path).text
    logging.info(f"[Bids]: Total Request: {total_bids}")
    devtracker_sleep(10, 15)

    # Get Bids
    job_boxes_all_path = "//div[contains(@class, 'cnaBaJv3')]"
    job_box_ind_path = "(//div[contains(@class, 'cnaBaJv3')])[{}]"
    job_list = []
    while True:
        try:
            # Limit pages to be scrapped
            if pages_scrapped > page_limit - 1:
                break

            logging.info(f'[Bids]: ==========Get Page {pages_scrapped + 1}/{page_limit}===========')
            WebDriverWait(driver, sel_timeout).until(EC.visibility_of_element_located((By.XPATH, job_boxes_all_path)))
            job_containers = driver.find_elements(By.XPATH, job_boxes_all_path)

            logging.info(f"[Bids]: Number of Bids on Current Page: {len(job_containers)}")
            for job_index in range(len(job_containers)):
                current_job_path = job_box_ind_path.format(str(job_index + 1))
                job_details = get_bid(current_job_path, driver)
                job_list.append(job_details)

            # Paginate by finding forward arrow icon
            forward_btn = driver.find_element(By.XPATH, "//button[text()='arrow_forward']")
            pages = driver.find_element(By.XPATH, "//div[contains(@class, 'cnaBaLaA3')]").text.split("  ")

            # If no limit applied go till the last page
            if not forward_btn or int(pages[0]) == int(pages[-1]):
                break
            driver.execute_script("arguments[0].click();", forward_btn)
            devtracker_sleep(4, 6)
            pages_scrapped += 1

        except TimeoutException:
            logging.info("[Bids]: Website Didn't Load, retrying!")
            # Retry in case page freezes or takes time to load dynamic content
            if retry_count > 3:
                break
            retry_count = retry_count + 1
            devtracker_sleep(5, 10)
        except InvalidSessionIdException:
            logging.critical("[Bids]: Browser Crashed, retrying!")
            devtracker_sleep(1, 2)
            raise Exception

    return job_list


def get_bid(job_elem, driver):
    """Get single bid from bid details page

    Args:
        job_elem (element): Bid container
        driver (webdriver): selenium webdriver object

    Returns:
        bid[]: bid array
    """
    # Open Job
    while True:
        try:
            driver.find_element(By.XPATH, job_elem).click()
            break
        except InvalidSessionIdException:
            logging.critical("[Bids]: Browser Crashed, retrying!")
            devtracker_sleep(1, 2)
            raise Exception
        except Exception as e:
            logging.critical("[Bids]: Exception while trying to click, retrying!")
            logging.critical(f"[Bids]: Error Message {e}")
            devtracker_sleep(1, 2)
            continue

    devtracker_sleep(1, 2)

    # Switch to new Tab as clicking on a bid will open it in a new tab
    driver.switch_to.window(driver.window_handles[-1])

    # Check if the Bid is opened & Get Data
    # Extract Name
    name_path = "//div[contains(@class, 'cnaBaVaB8')]"
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, name_path)))
    name = str(driver.find_element(By.XPATH, name_path).text).strip()

    # Extract Response Date
    response_date_path = "//div[contains(@class, 'cnaBaVy8')]"
    response_date = driver.find_element(By.XPATH, response_date_path).text
    response_date = extract_dates(response_date)

    # Extract Response
    response_char_limit = 50000
    response_path = "//div[contains(@class, 'cnaBaWc8')]"
    response = driver.find_element(By.XPATH, response_path).text
    response = limit_string(s=response, max_chars=response_char_limit)

    # Extract Rep
    rep_path = "(//div[contains(@class, 'cnaBaWc8')]//u)[last()]"
    rep_name = driver.find_element(By.XPATH, rep_path).text
    rep_name = rep_name.split("|")[0].strip()

    # Extract Rep calendly
    rep_calendly_path = "//a[contains(@href, 'calendly.com')]"
    rep_calendly_link = driver.find_element(By.XPATH, rep_calendly_path)
    rep_calendly_link = rep_calendly_link.get_attribute("href")

    # Extract Current URL
    bid_url = driver.current_url

    # Extract the Rfp_id
    rfp_id = str(bid_url.split("=")[-1])

    # close the new tab
    driver.close()

    # Switch Back
    driver.switch_to.window(driver.window_handles[0])
    return [rfp_id, name, response_date, response, bid_url, rep_name, rep_calendly_link]
