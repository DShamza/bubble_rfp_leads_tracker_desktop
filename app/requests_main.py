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
from requests_functions import select_slack_channel


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
    non_etl_df = req_df.loc[(req_df['etl_status'] != 'Y') & (req_df['etl_status'] != 'RFP Link Error')]
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
                    logging.info(f"[Script Log | Requests]: Now Extracting: {email_req_url}")
                    if email_req_url:
                        # Get RFP_Request Data using Email Request URL
                        rfp_req_results = get_rfp_request(email_req_url, driver)
                        logging.info("[Script Log | Requests]: RFP Request Results: %s", rfp_req_results)

                        # Extracting relevant information from RFP results
                        (rfp_id, client_first_name, project_title, tags, pricing, req_timestamp, description,
                         request_url) = rfp_req_results

                        # Update non_etl_row_vals with RFP data
                        non_etl_row_vals[1] = rfp_id
                        non_etl_row_vals[2] = client_first_name
                        non_etl_row_vals[3] = project_title
                        non_etl_row_vals[4] = tags
                        non_etl_row_vals[5] = pricing
                        non_etl_row_vals[7] = description
                        non_etl_row_vals[8] = request_url

                        # Set Slack Message Status
                        slack_msg_status = "Y"
                    else:
                        logging.critical("[Script Log | Requests]: RFP Link Error")
                        slack_msg_status = "RFP Link Error"
                        rfp_req_results = ["", "", "", "", ":rotating_light: RFP LINK ERROR :rotating_light:", "",
                                           f"{member_ids} Records with empty request links were detected in "
                                           f"Request Google Sheet, Please check RFP System for Any Errors",
                                           ""]

                    # Slack Thread
                    non_etl_row_vals[9] = send_req_slack_msg(select_slack_channel(non_etl_row_vals[10]),
                                                             rfp_req_results)

                    # Verify if Slack Message is sent
                    if non_etl_row_vals[9]:
                        non_etl_row_vals[-2] = slack_msg_status
                        # Update Google Sheets
                        row_index = non_etl_row_vals[-1]
                        gs_update_data(sh, row_index, [non_etl_row_vals[:-1]])
                        devtracker_sleep(1, 2)

        except Exception as _:
            logging.critical(f"[Script Log | Requests]: Something went wrong:", exc_info=True)
            raise
    else:
        logging.warning("[Script Log | Requests]: No New Requests Found")
    logging.info("[Script Log | Requests]: Iteration complete, Requests Script is Restarting...")
    devtracker_sleep(10, 20)


def exec_req_main_script():
    logging.info("[Script Log | Requests]: Starting RFP Request Tracker Tool")
    slack_notification(channel=alerts_channel_name,
                       msg_text=":incoming_envelope: RFP Requests Script Started! :rocket:")
    driver = get_driver()

    while True:
        try:
            requests_main_script(driver)
        except Exception as e:
            logging.critical(f"[Script Log | Requests]: RFP Request Tracker is Down,  Error:", exc_info=True)
            slack_notification(channel=alerts_channel_name,
                               msg_text=":incoming_envelope: :x: RFP Request Tracker is Down :x:",
                               exception_trace=e)
            break

    # Quiting Driver & Restarting
    try:
        driver.quit()
        logging.info(f"[Script Log | Requests]: Closing Driver")
    except Exception as e:
        logging.warning(f"[Script Log | Requests]: Driver is already closed {e}")

    devtracker_sleep(30, 60)
    slack_notification(channel=alerts_channel_name,
                       msg_text=":incoming_envelope: :recycle: Restarting RFP Requests Tracker :recycle:")
    exec_req_main_script()


if __name__ == '__main__':
    exec_req_main_script()
