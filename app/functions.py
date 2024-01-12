# coding: utf-8
import sys
import pytz
import json
import random
import gspread
import logging
import datefinder
from time import sleep
from datetime import datetime
from gspread.exceptions import APIError

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC

# WebDriver-Manager
from webdriver_manager.chrome import ChromeDriverManager

from functions_slack import slack_notification
from import_secrets import *

# Timezone
tz_NY = pytz.timezone("UTC")

# Browser Settings
sel_timeout = 20


def config_logs():
    """
    Configure Logs for the Project.
    :return:
    """
    # Configuring logs
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(levelname)s - [%(asctime)s]: {(%(filename)s):(Line:%(lineno)d)} - %(message)s")
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)


# Initialize Logs
config_logs()


def get_driver():
    """
    Create & Open Webdriver!

    Returns:
    """
    # Chrome Options
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--window-size=1366,2500")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-application-cache")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.set_capability("detach", True)

    # # Browser Cache
    # chrome_prof_path = os.path.abspath("account_data/Selenium")
    # chrome_options.add_argument("user-data-dir=" + chrome_prof_path)

    # Experimental Features
    prefs = {"profile.managed_default_content_settings.images": 2}
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

    # Install Webdriver
    chromedriver_path = Service(ChromeDriverManager().install())

    # Open and Return Driver
    driver = webdriver.Chrome(service=chromedriver_path, options=chrome_options)
    return driver


def devtracker_sleep(int_min, int_max):
    """
    This function is for introducing random pauses in program
    :param int_min: Minimum Sleep in Seconds (num)
    :param int_max: Maximum Sleep in Seconds (num)
    :return: Sleep Interval (num)
    """
    system_random = random.SystemRandom()
    sleep_interval = system_random.randint(int_min, int_max)
    logging.debug(f"[Functions] Sleep Interval: {sleep_interval}")
    sleep(sleep_interval)


def extract_dates(data_str):
    """
    Utility function to extract right date and add current UTC timestamp to the string

    Args:
        data_str:

    Returns:

    """
    # a generator will be returned by the datefinder module.
    # I'm typecasting it to a list. Please read the note of caution provided at the bottom.
    matches = list(datefinder.find_dates(data_str))
    # Get the timezone object for UTC

    # Get the current time in UTC
    datetime_ny = datetime.now(tz_NY)

    # Format the time as a string and print it
    if len(matches) > 0:
        # date returned will be a datetime.datetime object. here we are only using the first match.
        date = matches[0]
        return f'{date.day}/{date.month}/{date.year}, {datetime_ny.strftime("%H:%M:%S")}'
    else:
        return datetime.now(tz_NY).strftime("%d/%m/%Y, %H:%M:%S")


def bubbleio_login(driver):
    # Access requests via the `requests` attribute
    """
    This Function signs in to Bubbleio and Returns the driver.
    :return: driver
    """
    login_button_path = "//button[text()='Log in']"
    login_button_path2 = "(//button[text()='Log in'])[2]"
    email_path = "//*[text()='Password']/preceding-sibling::input[@type='email']"
    password_path = "//div[text()='Password']/following-sibling::input[@type='password']"
    app_indicator_path = "//div[text()='Apps']"
    retry_count = 0
    # Install Chrome Driver & Open Browser
    source_url = "https://bubble.io/"

    # Login
    try:
        driver.get(source_url)
        sleep(5)
        driver.find_element(By.XPATH, app_indicator_path)
        logging.info("[Functions]: Already Logged in..Continue")
        devtracker_sleep(5, 10)
    except Exception as e:
        logging.critical(f"[Functions]: Error Message {e}, Not Logged In")
        while True:
            try:
                logging.info("[Functions]: Opening Bubble URL")
                driver.get(source_url)
                sleep(5)
                WebDriverWait(driver, sel_timeout).until(
                    EC.visibility_of_element_located((By.XPATH, login_button_path))
                )
                logging.info("[Functions]: Landing page login button detected")
                driver.find_element(By.XPATH, login_button_path).click()
                logging.info("[Functions]: Clicked landing page login button")
                # Login
                try:
                    devtracker_sleep(10, 20)
                    # Check of 2nd Login Button
                    WebDriverWait(driver, sel_timeout).until(
                        EC.visibility_of_element_located((By.XPATH, login_button_path2))
                    )
                    logging.info("[Functions]: login page login button detected")
                    # Enter Email & Password
                    sleep(1)
                    logging.info("[Functions]: Entering Credentials")
                    driver.find_element(By.XPATH, email_path).clear()
                    driver.find_element(By.XPATH, email_path).send_keys(email)
                    sleep(1)
                    driver.find_element(By.XPATH, password_path).clear()
                    driver.find_element(By.XPATH, password_path).send_keys(password)
                    sleep(1)
                    # Click Login Button on Login Page
                    driver.find_element(By.XPATH, login_button_path2).click()
                    logging.info("[Functions]: Click login page login button.")
                    # Validate Login
                    WebDriverWait(driver, sel_timeout).until(
                        EC.visibility_of_element_located((By.XPATH, app_indicator_path))
                    )
                    logging.info("[Functions]: login successful")
                    devtracker_sleep(2, 10)
                except TimeoutException:
                    logging.critical("[Functions]: Login Timeout")
                    driver.refresh()
                    continue
            except TimeoutException:
                logging.critical("[Functions]: Website Didn't Load, retrying!")
                retry_count = retry_count + 1
                if retry_count > 3:
                    break
                # logging.info(driver.page_source)
                devtracker_sleep(5, 10)
            break
    return True


def open_worksheet(sheet_name):
    """
    Opens a spreadsheet and returns the provided worksheet by name.
    If the sheet doesn't exist in the spreadsheet, it is inserted
    into it before return.
    :param sheet_name:
    :return:
    """
    # open spreadsheet
    service_acc_creds = json.loads(service_acc_credentials)
    service_acc_creds["private_key"] = service_acc_creds["private_key"].replace("\\n", "\n")
    while True:
        try:
            gc = gspread.service_account_from_dict(service_acc_creds)
            spreadsheet = gc.open_by_key(spreadsheet_id)

            try:
                sh = spreadsheet.worksheet(sheet_name)
                logging.info(f"[Functions]: Spreadsheet available: {sheet_name}, Opening Spreadsheet!")
            except Exception as e:
                logging.critical(
                    f"[Functions]: Error Message: {e}" f"\nWorkSheet Not available, adding worksheet {sheet_name}"
                )
                sh = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols="12", index=0)

            if not sh:
                raise Exception
            else:
                return sh
        except Exception as e:
            devtracker_sleep(5, 10)
            logging.critical(f"[Functions]: Error connecting with spreadsheet {e}")
            continue


def gs_get_data(sh):
    """
    Get Data from a Google WorkSheet.
    :return:
    """
    retries = 0
    max_retries = 5

    while retries < max_retries:
        try:
            logging.info("[Functions]: [GS GET Data] Getting Sheet Data...")
            sheet_data = sh.get_all_values()
            if not sheet_data:
                logging.error("[Functions]: [GS GET Data] Sheet Data Not Found, Raising Error!")
                raise Exception
            else:
                logging.info("[Functions]: [GS GET Data] Sheet Data Found, Continuing!")
                return sheet_data

        except APIError as gs_api_error:
            logging.critical("[Functions]: [GS GET Data] Something Went Wrong with the Google Sheets API")
            gs_status_code = gs_api_error.response.status_code
            if gs_status_code == 429 or gs_status_code == 503:
                retries += 1
                logging.error(f"[Functions]: [GS GET Data] Retry #{retries} Rate Limit Exceeded")
                logging.error(f"[Functions]: [GS GET Data] Status Code: {gs_status_code}")
                devtracker_sleep(60, 80)
            else:
                logging.critical("[Functions]: [GS GET Data] Something went wrong with the Google Sheets")
                raise

        except Exception as e:
            logging.critical(f"[Functions]: [GS GET Data] Error Message: {e}", exc_info=True)

    return []


def gs_insert_data(sh, bubble_data):
    """
    Insert Data into Google Sheets.
    :return:
    """
    error_count = 0
    while True:
        try:
            # sh.append_rows(bubble_data, value_input_option="USER_ENTERED", table_range="A1")
            sh.append_rows(bubble_data, value_input_option="RAW", table_range="A1")
        except APIError as gs_api_error:
            logging.critical("[Functions]: [GS Insert Data] Unable to insert data in Google Sheets")
            gs_status_code = gs_api_error.response.status_code
            if gs_status_code == 429 or gs_status_code == 503:
                logging.critical(f"Status Code: {gs_status_code}")
                error_count += 1
                devtracker_sleep(60, 80)
            else:
                logging.critical(f"API Error not handled, Status Code: {gs_status_code}")
                raise
        except Exception as e:
            logging.critical(f"[Functions]: [GS Insert Data] Error Message: {e}")
            if error_count % 10 == 0:
                slack_notification(
                    channel=alerts_channel_name,
                    msg_text=":rotating_light: Error while inserting data rows to google sheets :rotating_light:",
                    exception_trace=e,
                )
                if error_count % 50 == 0:
                    slack_notification(
                        channel=alerts_channel_name,
                        msg_text=":rotating_light: Bids and Requests Tracker is down! :rotating_light:",
                        exception_trace=e,
                    )
            devtracker_sleep(1, 5)
            error_count += 1
            continue
        break


def gs_update_data(sh, sh_range, data):
    """
    Update Data into Google Sheets for a given cell/range.
    :return:
    """
    error_count = 0
    while True:
        try:
            sh.update(sh_range, data, value_input_option="RAW")
        except Exception as e:
            logging.critical(f"[Functions]: [GS Update Data]: {e}")
            if error_count % 10 == 0:
                slack_notification(
                    channel=alerts_channel_name,
                    msg_text=":rotating_light: Error Updating Response Message Status & "
                             "Response Thread_ID to Google Sheets:rotating_light:",
                    exception_trace=e,
                )
                if error_count % 50 == 0:
                    slack_notification(
                        channel=alerts_channel_name,
                        msg_text=":rotating_light: RFP Response Slack " "Notifier is down! :rotating_light:",
                        exception_trace=e,
                    )
            devtracker_sleep(1, 5)
            error_count += 1
            continue
        break


def diff_df_by_column(df_new, df_old, column_name, duplicate_criteria):
    """
    Returns a new DataFrame containing the rows that are present in df_new but not in df_old,
    based on the specified column name.

    :param df_new: Dataframe
        The new DataFrame to compare against the old DataFrame.
    :param df_old: Dataframe
        The old DataFrame to compare against.
    :param column_name: str
        The name of the column used as the basis for comparison.
    :param duplicate_criteria: list of str
        A list of column names to consider when removing duplicates from both DataFrames.
    :return: DataFrame
        A new DataFrame containing rows from df_new that are not present in df_old.
    """
    df_new = df_new.drop_duplicates(subset=duplicate_criteria)
    df_old = df_old.drop_duplicates(subset=duplicate_criteria)
    diff_rows = df_new[~df_new[column_name].isin(df_old[column_name])]

    return diff_rows


def column_index_to_alphabet(column_index):
    """
    Convert a 0-based column index to its corresponding alphabetical letter.
    Example: 0 -> 'A', 1 -> 'B', 25 -> 'Z', 26 -> 'AA', ...
    """
    alphabet = ""
    while column_index > 0:
        column_index -= 1
        remainder = column_index % 26
        alphabet = chr(65 + remainder) + alphabet
        column_index //= 26
    return alphabet


def add_spreadsheet_range_column(df, columns, columns_to_find):
    """
    This function adds the address of the last column for each row into a new columns "Spreadsheet Range"
    Args:
        df:
        columns:
        columns_to_find:
    Returns:

    """
    for column_to_find in columns_to_find:
        col_index = columns.index(column_to_find) + 1
        spreadsheet_ranges = []
        row_count = df.shape[0]
        last_col_letter = column_index_to_alphabet(col_index)
        start_index = 1
        for i in range(row_count):
            spreadsheet_ranges.append(f"{last_col_letter}{start_index + 1}")
            start_index += 1
        df[f"{column_to_find}_range"] = spreadsheet_ranges

    return df


def limit_string(s, max_chars):
    """
    Truncates the input string to a maximum number of characters.

    Args:
        s (str): The input string to be limited.
        max_chars (int): The maximum number of characters allowed in the output string.

    Returns:
        str: The truncated string with at most `max_chars` characters.
    """
    return s[:max_chars]
