# coding: utf-8
import logging
import pandas as pd
from tqdm import tqdm
from datetime import datetime

from import_secrets import *
from functions import config_logs
from functions import open_worksheet
from functions import gs_get_data
from functions import devtracker_sleep
from functions import add_spreadsheet_range_column
from functions_slack import get_elapsed_ts
from functions_slack import slack_notification
from functions_slack import channel_name_to_id
from functions_slack import respond_to_slack_message
from functions_slack import react_to_slack_message

config_logs()


def resp_slack_notifier():
    # Creating a dataframe from Leads Sheet
    logging.info("Opening Leads Sheet")
    sh = open_worksheet("Leads")
    leads_sh_data = gs_get_data(sh)
    req_sh_cols = leads_sh_data[0]
    leads_df = pd.DataFrame(leads_sh_data[1:], columns=req_sh_cols)
    leads_df = add_spreadsheet_range_column(leads_df)
    request_channel_id = channel_name_to_id(request_channel_name)

    # Filter Out the rows that do not have Slack threads
    logging.info("Removing Leads without Slack Threads")
    slack_threads_df = leads_df.loc[leads_df['thread_id'] != '']
    # Filter out only the rows that have matches
    logging.info("Removing Leads without matches")
    matched_df = slack_threads_df.loc[slack_threads_df['response'] != '#N/A']
    # Filter out the rows for which the Slack Message has already been sent.
    logging.info("Removing threads for which the message has already been sent.")
    unsent_df = matched_df.loc[matched_df['resp_msg_status'] != 'Y']

    # Sending Messages to the unsent rows
    logging.info("Rows, Columns:")
    logging.info(unsent_df.shape)
    unsent_rows = unsent_df.values.tolist()

    if unsent_df.shape[0]:
        for unsent_row_vals in tqdm(unsent_rows):
            budget = unsent_row_vals[2]
            created_date = unsent_row_vals[3]
            thread_timestamp = unsent_row_vals[5]
            response_date = unsent_row_vals[6]
            response_body = unsent_row_vals[7]
            url = unsent_row_vals[8]
            flag_cell_address = unsent_row_vals[-1]

            thread_timestamp = get_elapsed_ts(request_channel_id, thread_timestamp)
            if thread_timestamp:
                # Send Message to "rfp-leads"
                thread_msg_text = f"""*Response Body* : {response_body}\n*Url*: {url}"""
                thread_emojis = ["alphabet-white-s", "alphabet-white-e", "alphabet-white-n", "alphabet-white-t",
                                 "alphabet-white-exclamation"]
                respond_to_slack_message(channel=request_channel_name, thread_ts=thread_timestamp, text=thread_msg_text)
                react_to_slack_message(channel_id=request_channel_id, thread_ts=thread_timestamp,
                                       reactions=thread_emojis)
            else:
                sh.update(flag_cell_address, "Expired Thread", value_input_option='USER_ENTERED')
                continue

            # Send Message to "rfp-response-time"
            created_date_time = datetime.strptime(created_date, "%d/%m/%Y, %H:%M:%S")
            response_date_time = datetime.strptime(response_date, "%d/%m/%Y, %H:%M:%S")
            total_response_time = response_date_time - created_date_time

            # Craft Message and Message Thread
            main_body_msg = f"""*Budget* : {budget}\n*Time to response*: {total_response_time} hours"""
            thread_msg_text = f"""*Response Body* : {response_body}\n*Url*: {url}"""

            # Send the Message Main Body
            msg_response = slack_notification(channel=response_channel_name, msg_text=main_body_msg)

            # Send the Response.
            respond_to_slack_message(channel=response_channel_name, text=thread_msg_text, thread_ts=msg_response)

            # Add a "Y" to flag that a message has been sent for this lead
            sh.update(flag_cell_address, "Y", value_input_option='USER_ENTERED')
            devtracker_sleep(2, 5)
    else:
        logging.info("No Messages to Send")
    logging.info("Iteration complete, Restarting...")
    devtracker_sleep(5, 10)


def exec_resp_slack_notifier():
    logging.info("[Script Log | Requests]: Starting Response Slack Notifier")
    slack_notification(channel=main_channel_name,
                       msg_text=":grey_exclamation: RFP Response Slack Notifier Started! :rocket:")
    while True:
        try:
            resp_slack_notifier()
        except Exception as e:
            logging.info(f"[Script Log | Requests]: RFP Response Slack Notifier is Down,  Error: {e}")
            slack_notification(channel=main_channel_name,
                               msg_text=":grey_exclamation: :x: RFP Response Slack Notifier is Down :x:",
                               exception_trace=e)
            break

    devtracker_sleep(30, 60)
    slack_notification(channel=main_channel_name,
                       msg_text=":grey_exclamation: :recycle: Restarting RFP Response Slack Notifier :recycle:")
    exec_resp_slack_notifier()


if __name__ == '__main__':
    exec_resp_slack_notifier()
