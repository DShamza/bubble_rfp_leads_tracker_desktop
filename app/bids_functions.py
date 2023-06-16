# coding: utf-8
import logging
from functions import extract_dates
from functions import devtracker_sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import InvalidSessionIdException
from selenium.webdriver.support import expected_conditions as EC

# Browser Settings
sel_timeout = 20


def get_io_bids(driver, page_limit=1):
    """Gets All Bids from Bubbleio bids page and store them in dataframe

    Args:
        driver (webdriver): selenium webdriver object

    Returns:
        data[]: returns list of all scrapped bids
        :param driver:
        :param page_limit:
    """
    logging.info(f"[Script Log | Bids]: Opening Bid Page")
    # Open App
    retry_count = 0
    pages_scrapped = 0
    bids_url = f"https://bubble.io/agency-requests/sent"
    driver.get(bids_url)
    # check for total Bids
    total_bids_path = "//div[@class='bubble-element Text cnaBaJp3']"
    total_bids = driver.find_element(By.XPATH, total_bids_path).text
    logging.info(f"[Script Log | Bids]: Total Request: {total_bids}")
    devtracker_sleep(10, 15)

    # Get Bids
    bid_boxes_all_path = "//div[contains(@class, 'cnaBaJv3')]"
    bid_box_ind_path = "(//div[contains(@class, 'cnaBaJv3')])[{}]"
    bid_list = []
    request_list = []
    while True:
        try:
            # Limit pages to be scrapped
            if pages_scrapped > page_limit - 1:
                break

            logging.info(f'[Script Log | Bids]: ==========Get Page {pages_scrapped + 1}/{page_limit}===========')
            WebDriverWait(driver, sel_timeout).until(EC.visibility_of_element_located((By.XPATH, bid_boxes_all_path)))
            bid_containers = driver.find_elements(By.XPATH, bid_boxes_all_path)

            logging.info(f"[Script Log | Bids]: Number of Bids on Current Page: {len(bid_containers)}")
            for bid_index in range(len(bid_containers)):
                current_bid_path = bid_box_ind_path.format(str(bid_index + 1))
                job_details = get_bid(current_bid_path, driver)
                bid_details = job_details[0]
                request_details = job_details[1]
                bid_list.append(bid_details)
                request_list.append(request_details)

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
            logging.info("[Script Log | Bids]: Website Didn't Load, retrying!")
            # Retry in case page freezes or takes time to load dynamic content
            if retry_count > 3:
                break
            retry_count = retry_count + 1
            devtracker_sleep(5, 10)
        except InvalidSessionIdException:
            logging.critical("[Script Log | Bids]: Browser Crashed, retrying!")
            devtracker_sleep(1, 2)
            raise Exception

    return bid_list


def get_bid(bid_elem, driver):
    """Get single bid from bid details page

    Args:
        bid_elem (element): Bid container
        driver (webdriver): selenium webdriver object

    Returns:
        bid[]: bid array
    """
    # Open Bid
    while True:
        try:
            driver.find_element(By.XPATH, bid_elem).click()
            break
        except InvalidSessionIdException:
            logging.critical("[Script Log | Bids]: Browser Crashed, retrying!")
            devtracker_sleep(1, 2)
            raise Exception
        except Exception as e:
            logging.critical("[Script Log | Bids]: Exception while trying to click, retrying!")
            logging.critical(f"[Script Log | Bids]: Error Message {e}")
            devtracker_sleep(1, 2)
            continue

    devtracker_sleep(1, 2)

    # Switch to new Tab as clicking on a bid will open it in a new tab
    driver.switch_to.window(driver.window_handles[-1])

    """
    Extract Bids Data
    """
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
    response_path = "//div[contains(@class, 'cnaBaWc8')]"
    response = driver.find_element(By.XPATH, response_path).text

    # Extract Current URL
    bid_url = driver.current_url

    """
    Extract Request Data 
    """
    # Check if the Request Page is opened & Get Data
    # Extract Name
    name_path = "//div[contains(@class, 'cnaBaVaB8')]"
    WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.XPATH, name_path)))
    name = str(driver.find_element(By.XPATH, name_path).text).strip()

    # Extract Tags
    tags = driver.find_element(By.XPATH, "//div[contains(@class, 'cnaBaVaR8')]").text

    # Extract Pricing
    pricing = driver.find_element(By.XPATH, "//div[contains(@class, 'cnaBaVaU8')]").text

    # Extract Request Date
    request_date = driver.find_element(By.XPATH, "//div[contains(@class, 'cnaBaVaF8')]").text
    request_date = extract_dates(request_date)

    # Extract Request Description
    description = driver.find_element(By.XPATH, "//div[contains(@class, 'cnaNaq2')]").text

    # Extract Request URL
    request_url = driver.current_url

    # close the new tab
    driver.close()

    # Switch Back
    driver.switch_to.window(driver.window_handles[0])
    return [name, response_date, response, bid_url], [name, tags, pricing, request_date, description, request_url]
