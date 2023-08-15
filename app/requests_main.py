# coding: utf-8
import logging

import pandas as pd

from functions import bubbleio_login
from functions import devtracker_sleep
from functions import diff_df_by_column
from functions import get_driver
from functions import gs_get_data
from functions import gs_insert_data
from functions import open_worksheet
from functions_slack import slack_notification
from import_secrets import *
from requests_functions import get_io_jobs
from requests_functions import show_request_data_to_slack


def requests_main_script():
    logging.info("[Script Log | Requests]: Starting Bubbleio Dev Monitor Tool")
    slack_notification(channel=main_channel_name,
                       msg_text=":incoming_envelope: RFP Requests Script Started! :rocket:")
    try:
        # Check Login & Get apps to track
        driver = get_driver()
        is_logged_in = bubbleio_login(driver)
        if is_logged_in:
            while True:
                try:
                    sh = open_worksheet("New_Requests")
                    req_sh_data = gs_get_data(sh)
                    req_sh_cols = req_sh_data[0]
                    logging.info(f"[Script Log | Requests]: Old records: {str(len(req_sh_data))}")
                    # Check if sheet has data or not to initialize dataframe properly
                    if len(req_sh_data) > 0:
                        # Has Existing Data
                        existing_req_df = pd.DataFrame(req_sh_data[1:], columns=req_sh_cols)
                    else:
                        # No Existing Data, Start a New Dataframe
                        existing_req_df = pd.DataFrame([], columns=req_sh_cols)

                    # Get job-requests from first two Pages of Inbox
                    job_requests = get_io_jobs(driver)

                    # Select first 7 columns because 8th Col is for threads which will be added later on
                    req_sh_cols = req_sh_cols[:7]

                    if len(job_requests) > 0:
                        ext_req_df = pd.DataFrame(job_requests, columns=req_sh_cols)
                    else:
                        ext_req_df = pd.DataFrame([], columns=req_sh_cols)

                    # Assign Str Datatype for avoiding numeric duplicates.
                    ext_req_df['name'] = ext_req_df['name'].astype(str)
                    existing_req_df['name'] = existing_req_df['name'].astype(str)

                    # Check if there are any new values in the dataset
                    duplicate_criteria = ['rfp_id', 'name', 'tags', 'pricing', 'description', 'request_url']
                    diff_df = diff_df_by_column(ext_req_df, existing_req_df, 'rfp_id', duplicate_criteria)
                    new_rec_count = str(diff_df.shape[0])
                    logging.info(f"[Script Log | Requests]: New Unique records found: {new_rec_count}")

                    # send the new requests to the requests Slack channel
                    diff_df = show_request_data_to_slack(diff_df)

                    # Format Dataset
                    diff_df_final = diff_df.fillna("")
                    gs_insert_data(sh, diff_df_final.values.tolist())
                    logging.info(f"[Script Log | Requests]: [GS SAVE DATA] Data Saved!")
                    devtracker_sleep(10, 15)
                except Exception as e:
                    logging.info(f"[Script Log | Requests]: RFP Request Tracker is Down,  Error: {e}")
                    slack_notification(channel=main_channel_name,
                                       msg_text=":incoming_envelope: :x: RFP Request Tracker is Down :x:",
                                       exception_trace=e)
                    break
        # Quiting Driver & Restarting
        try:
            driver.quit()
            logging.info(f"[Script Log | Requests]: Closing Driver")
        except Exception as e:
            logging.info(f"[Script Log | Requests]: Driver is already closed {e}")
    except Exception as e:
        logging.info(f"[Script Log | Requests]: RFP Request Tracker is Down,  Error: {e}")
        slack_notification(channel=main_channel_name,
                           msg_text=":incoming_envelope: :x: RFP Request Tracker is Down :x:",
                           exception_trace=e)

    devtracker_sleep(30, 60)
    slack_notification(channel=main_channel_name,
                       msg_text=":incoming_envelope: :recycle: Restarting RFP Requests Tracker :recycle:")
    requests_main_script()


if __name__ == '__main__':
    requests_main_script()
