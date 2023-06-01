# coding: utf-8
import logging
import pandas as pd

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import WebDriverException
from selenium.common.exceptions import InvalidSessionIdException
from selenium.webdriver.support import expected_conditions as EC

from import_secrets import *
from functions import extract_dates
from functions import devtracker_sleep
from functions_slack import slack_notification
from functions_slack import respond_to_slack_message

# Browser Settings
sel_timeout = 20


def get_io_jobs(driver, page_limit=2):
    """Scrapes job requests from Bubbleio job requests page

    Args:
        driver (webdriver): selenium webdriver object

    Returns:
        data[][]: an array of all scrapped job requests
        :param driver:
        :param page_limit:
    """
    logging.info(f"[Script Log | Requests]: Opening Job Request Page")
    retry_count = 0
    pages_scrapped = 0
    requests_url = f"https://bubble.io/agency-requests/inbox"
    driver.get(requests_url)
    devtracker_sleep(10, 15)
    total_request = driver.find_element(By.XPATH, "//div[@class='bubble-element Text cnaBaAaD3']").text

    job_all_boxes_path = "//div[contains(@class, 'cnaBaCh3')]"
    job_boxes_ind_path = "(//div[contains(@class, 'cnaBaCh3')])[{}]"

    logging.info(f"[Script Log | Requests]: {total_request}")

    job_list = []
    while True:
        try:
            if pages_scrapped > page_limit - 1:
                break
            logging.info(f'[Script Log | Requests]: ==========Get Page {pages_scrapped + 1}/{page_limit}===========')
            WebDriverWait(driver, sel_timeout).until(EC.visibility_of_element_located((By.XPATH, job_all_boxes_path)))
            job_containers_count = len(driver.find_elements(By.XPATH, job_all_boxes_path))
            for job_index in range(job_containers_count):
                current_job_path = job_boxes_ind_path.format(str(job_index + 1))
                job_details = get_job(current_job_path, driver)
                job_list.append(job_details)

            forward_btn = driver.find_element(By.XPATH, "//button[text()='arrow_forward']")
            pages = driver.find_element(By.XPATH, "//div[contains(@class, 'cnaBaDaU3')]")
            if pages:
                pages = pages.text.split("  ")
                if not forward_btn or int(pages[0]) == int(pages[-1]):
                    break

            if not forward_btn or int(pages[0]) == int(pages[-1]):
                break

            driver.execute_script("arguments[0].click();", forward_btn)
            devtracker_sleep(4, 6)
            pages_scrapped = pages_scrapped + 1
        except TimeoutException:
            logging.critical("[Script Log | Requests]: Website Didn't Load, retrying!", exc_info=True)
            if retry_count > 3:
                break
            retry_count = retry_count + 1
            # logging.info(driver.page_source)
            devtracker_sleep(5, 10)

    return job_list


def get_job(job_elem, driver):
    # logging.info(job_elem.click())
    while True:
        try:
            element = driver.find_element(By.XPATH, job_elem)
            element.click()
            break
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

    devtracker_sleep(1, 2)

    # Switch to new Tan as click will open function in new tab
    driver.switch_to.window(driver.window_handles[-1])

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
    return [name, tags, pricing, request_date, description, request_url]


def show_request_data_to_slack(slack_data_df):
    """
        iterate each new request.
        send the Slack notification against each request.
        and return the time stamp of each request msg to save it in the Google sheet.
        :return:
    """

    slack_data = slack_data_df.values.tolist()
    if int(slack_data_df.shape[0]) == 0:
        return slack_data_df
    else:
        for i in slack_data:
            time_stamp = request_message_for_slack(request_channel_name, i)
            i.append(time_stamp)

        thread_df = pd.DataFrame(slack_data,
                                 columns=['name', 'tags', 'pricing', 'created_date', 'description', 'request_url',
                                          'thread_id'])
        return thread_df


def request_message_for_slack(channel_name, data_list):
    """
            send the budget of a new request and its detail in the slack.
            :return:
    """
    budget = data_list[2]
    tag = data_list[1]
    description = data_list[4]
    url = data_list[5]

    # Craft the thread msg
    thread_msg_text = f"""*Tag* : {tag}\n*Descriptions*: {description}\n*URl*: {url}"""

    # Send the main msg and thread msg
    msg_response = slack_notification(channel=channel_name, msg_text=budget)
    respond_to_slack_message(channel=channel_name, text=thread_msg_text, thread_ts=msg_response)
    devtracker_sleep(2, 4)

    # return the time-stamp to be saved in the GoogleSheet
    return str(msg_response)
