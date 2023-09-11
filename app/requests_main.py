# coding: utf-8
import logging
import pandas as pd
from tqdm import tqdm

from import_secrets import *
from functions import gs_update_data
from functions import open_worksheet
from functions import gs_get_data
from functions import devtracker_sleep
from functions import column_index_to_alphabet
from functions import get_driver
from functions import bubbleio_login
from functions_slack import slack_notification
from requests_functions import get_rfp_request
from requests_functions import send_req_slack_msg


def requests_main_script(driver):
    # Creating a dataframe from Leads Sheet
    logging.info("[Script Log | Requests]: Opening New Requests Sheet")
    sh = open_worksheet(req_sheet_name)
    req_sh_data = gs_get_data(sh)
    req_sh_cols = req_sh_data[0]
    req_df = pd.DataFrame(req_sh_data[1:], columns=req_sh_cols)

    # Assign a range column to the DataFrame
    req_df['Range'] = [f"A{i + 2}:{column_index_to_alphabet(len(req_df.columns))}{i + 2}" for i in range(len(req_df))]

    # Filter out the rows for which the Slack Message has already been sent.
    logging.info("[Script Log | Requests]: Removing threads for which the message has already been sent.")
    non_etl_df = req_df.loc[req_df['etl_status'] != 'Y']
    logging.info(f"[Script Log | Requests]: Data to be Extracted, Rows, Columns: {non_etl_df.shape}")

    # Extracting Data for Non-ETL Requests
    non_etl_rows = non_etl_df.values.tolist()

    if non_etl_df.shape[0]:
        try:
            is_logged_in = bubbleio_login(driver)
            if is_logged_in:
                for non_etl_row_vals in tqdm(non_etl_rows, desc="[Script Log | Requests]: Extracting New Requests"):
                    # Get Email Request URL
                    email_req_url = non_etl_row_vals[0]
                    logging.info(f"Now Extracting: {email_req_url}")

                    # Get RFP_Request Data using Email Request URL
                    rfp_req_results = get_rfp_request(email_req_url, driver)
                    logging.info(rfp_req_results)

                    # RFP ID
                    non_etl_row_vals[1] = rfp_req_results[0]

                    # Client First Name
                    non_etl_row_vals[2] = rfp_req_results[1]

                    # Project Title
                    non_etl_row_vals[3] = rfp_req_results[2]

                    # Tags
                    non_etl_row_vals[4] = rfp_req_results[3]

                    # Pricing
                    non_etl_row_vals[5] = rfp_req_results[4]

                    # # Timestamp (Already Inserted)
                    # non_etl_row_vals[6] = rfp_req_results[5]

                    # Description
                    non_etl_row_vals[7] = rfp_req_results[6]

                    # Request URL
                    non_etl_row_vals[8] = rfp_req_results[7]

                    # Slack Thread
                    if non_etl_row_vals[10] == "Agency Request":
                        non_etl_row_vals[9] = send_req_slack_msg(request_channel_name, rfp_req_results)
                    elif non_etl_row_vals[10] == "Direct Request":
                        non_etl_row_vals[9] = send_req_slack_msg(request_channel_direct, rfp_req_results)
                    else:
                        logging.warning("Request Type is not included, Sending to Agency Request Channel.")
                        non_etl_row_vals[9] = send_req_slack_msg(request_channel_name, rfp_req_results)

                    # Verify if Slack Message is sent
                    if non_etl_row_vals[9]:
                        non_etl_row_vals[-2] = "Y"
                        # Update Google Sheets
                        row_index = non_etl_row_vals[-1]
                        gs_update_data(sh, row_index, [non_etl_row_vals[:-1]])
                        devtracker_sleep(1, 2)
        except Exception as e:
            logging.critical(f"[Script Log | Requests]: Something went wrong: {e}")
    else:
        logging.warning("[Script Log | Requests]: No New Requests Found")
    logging.info("[Script Log | Requests]: Iteration complete, Requests Script is Restarting...")
    devtracker_sleep(20, 20)


def exec_req_main_script():
    logging.info("[Script Log | Requests]: Starting RFP Request Tracker Tool")
    slack_notification(channel=alerts_channel_name,
                       msg_text=":incoming_envelope: RFP Requests Script Started! :rocket:")
    driver = get_driver()

    while True:
        try:
            requests_main_script(driver)
        except Exception as e:
            logging.info(f"[Script Log | Requests]: RFP Request Tracker is Down,  Error: {e}")
            slack_notification(channel=alerts_channel_name,
                               msg_text=":incoming_envelope: :x: RFP Request Tracker is Down :x:",
                               exception_trace=e)
            break

    # Quiting Driver & Restarting
    try:
        driver.quit()
        logging.info(f"[Script Log | Requests]: Closing Driver")
    except Exception as e:
        logging.info(f"[Script Log | Requests]: Driver is already closed {e}")

    devtracker_sleep(30, 60)
    slack_notification(channel=alerts_channel_name,
                       msg_text=":incoming_envelope: :recycle: Restarting RFP Requests Tracker :recycle:")
    exec_req_main_script()


if __name__ == '__main__':
    exec_req_main_script()
