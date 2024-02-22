# coding: utf-8
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import InvalidSessionIdException
from selenium.webdriver.support import expected_conditions as EC

from import_secrets import *
from functions import limit_string
from functions import extract_dates
from functions import devtracker_sleep
from functions_slack import slack_notification
from functions_slack import respond_to_slack_message

# Browser Settings
sel_timeout = 60


def open_req_url(rfp_req_url, driver):
    """
    Opens the provided request URL in the given Selenium WebDriver.

    Retries if a timeout occurs or if there are issues accessing the URL.

    Args:
        rfp_req_url (str): The URL of the request to be opened.
        driver: The Selenium WebDriver instance.

    Returns:
        None

    Raises:
        InvalidSessionIdException: If an invalid session ID is encountered.
        WebDriverException: If a WebDriver-related exception occurs.
    """
    retry_count = 0
    req_name_path = "//*[contains(@class, 'cnaBaVaB8')]"
    while True:
        try:
            driver.get(rfp_req_url)
            WebDriverWait(driver, sel_timeout).until(EC.visibility_of_element_located((By.XPATH, req_name_path)))
        except TimeoutException:
            logging.critical("Timeout opening the Request URL", exc_info=True)
            if driver.find_element(By.XPATH, "//*[text()='Job request inbox']"):
                if retry_count >= 10:
                    logging.warning("Invalid Request")
                    return ["", "", "", "Invalid Request Link", "", "Invalid Request Link", rfp_req_url]
                else:
                    retry_count += 1
                    logging.error(f"Retry # {retry_count} Something Went Wrong, Retrying...")
            else:
                logging.error("Something Went Wrong, Retrying")
                continue
        except Exception as e:
            if isinstance(e, InvalidSessionIdException):
                raise InvalidSessionIdException
            if isinstance(e, WebDriverException):
                raise WebDriverException
            else:
                logging.critical("[Script Log | Requests]: Exception while trying to click, retrying!")
                logging.critical(f"[Script Log | Requests]: Error Message {e}")
                devtracker_sleep(1, 2)
                continue
        break
    devtracker_sleep(1, 2)


def get_rfp_request(rfp_req_url, driver):
    """
    Extracts relevant information from the provided RFP request URL using the given Selenium WebDriver.

    Args:
        rfp_req_url (str): The URL of the RFP request to be processed.
        driver: The Selenium WebDriver instance.

    Returns:
        list: A list containing the extracted information in the following order:
              [rfp_id, client_first_name, proj_title, tags, pricing, req_created_date, description, request_url]
    """
    # Open Req_URL
    open_req_url(rfp_req_url, driver)

    # Extract Project Title
    proj_title_path = "//*[contains(@class, 'cnaBaVaB8')]"
    proj_title = str(driver.find_element(By.XPATH, proj_title_path).text).strip()

    # Extract Client First Name
    f_name_path = "//*[text()='First name']/following-sibling::div[1]"
    client_first_name = str(driver.find_element(By.XPATH, f_name_path).text).strip()

    # Extract Tags
    tags = driver.find_element(By.XPATH, "//div[contains(@class, 'cnaBaVaR8')]").text

    # Extract Pricing
    pricing = driver.find_element(By.XPATH, "//*[contains(@class, 'cnaBaVaU8')]").text

    # Extract Request Date
    req_created_date = driver.find_element(By.XPATH, "//div[contains(@class, 'cnaBaVaF8')]").text
    req_created_date = extract_dates(req_created_date)

    # Extract Request Description
    description_char_limit = 50000
    description = driver.find_element(By.XPATH, "//div[contains(@class, 'cnaNaq2')]").text
    # Updating Job Description for Google Sheets' 50000 Char Limit per Cell
    gs_description = limit_string(input_string=description, max_chars=description_char_limit)

    # Extract Request URL
    request_url = driver.current_url

    # Extract the Rfp_id
    rfp_id = str(request_url.split("=")[-1])

    return [rfp_id, client_first_name, proj_title, tags, pricing, req_created_date, gs_description, request_url]


def send_req_slack_msg(channel_name, data_list):
    """
    send the budget of a new request and its detail in the slack.
    :return:
    """
    client_fn = data_list[1]
    tags = data_list[3]
    budget = data_list[4]
    description = data_list[6]
    url = data_list[7]

    # Craft the thread msg
    thread_msg_text = (f"*Tags:* {tags}\n\n*Client First Name:* {client_fn}\n\n"
                       f"*Descriptions*: {description}\n\n*URl:* {url}")

    # Send the main msg and thread msg
    msg_response = slack_notification(channel=channel_name, msg_text=budget)
    respond_to_slack_message(channel=channel_name, text=thread_msg_text, thread_ts=msg_response)
    devtracker_sleep(2, 4)

    # return the time-stamp to be saved in the GoogleSheet
    return str(msg_response)


def select_slack_channel(request_type):
    """
    Selects the Slack channel based on the request type.

    Args:
        request_type (str): Type of the request.

    Returns:
        str: Selected Slack channel.
    """
    if request_type == "Agency Request":
        return request_channel_name
    elif request_type == "Direct Request":
        return request_channel_direct
    else:
        logging.warning("Request Type is not included, Sending to Agency Request Channel.")
        return request_channel_name
