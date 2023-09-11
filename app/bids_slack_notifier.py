# coding: utf-8
import logging
import pandas as pd
from tqdm import tqdm
from datetime import datetime

from import_secrets import *
from functions import gs_update_data
from functions import open_worksheet
from functions import gs_get_data
from functions import devtracker_sleep
from functions import add_spreadsheet_range_column
from functions_slack import get_elapsed_ts
from functions_slack import slack_notification
from functions_slack import channel_name_to_id
from functions_slack import respond_to_slack_message
from functions_slack import react_to_slack_message
from functions_slack import edit_slack_message


def resp_slack_notifier():
    # Creating a dataframe from Leads Sheet
    logging.info("[Requests Notifier]: Opening Leads Sheet")
    sh = open_worksheet(lead_sheet_name)
    leads_sh_data = gs_get_data(sh)
    leads_sh_cols = leads_sh_data[0]
    leads_df = pd.DataFrame(leads_sh_data[1:], columns=leads_sh_cols)

    # Adding Cell addresses for "response_msg_status" and "response_thread_id"
    leads_df = add_spreadsheet_range_column(leads_df, leads_sh_cols, ["response_msg_status", "response_thread_id"])

    # Filter Out the rows that do not have Slack threads
    logging.info("[Requests Notifier]: Removing Leads without Slack Threads")
    slack_threads_df = leads_df.loc[leads_df['requests_thread_id'] != '']

    # Filter out only the rows that have matches
    logging.info("[Requests Notifier]: Removing Leads without matches")
    matched_df = slack_threads_df.loc[slack_threads_df['response'] != '#N/A']

    # Filter out the rows for which the Slack Message has already been sent.
    logging.info("[Requests Notifier]: Removing threads for which the message has already been sent.")
    unsent_df = matched_df.loc[matched_df['response_msg_status'] != 'Y']

    # Sending Messages to the unsent rows
    logging.info(f"[Requests Notifier]: Rows, Columns: {unsent_df.shape}")
    unsent_rows = unsent_df.values.tolist()

    if unsent_df.shape[0]:
        for unsent_row_vals in tqdm(unsent_rows):
            url = f"https://bubble.io/agency-requests/sent?rfp={unsent_row_vals[0]}"
            budget = unsent_row_vals[4]
            created_date = unsent_row_vals[5]
            req_thread_ts = unsent_row_vals[7]
            req_type = unsent_row_vals[8]
            response_date = unsent_row_vals[9]
            response_body = unsent_row_vals[10]
            rep_name = unsent_row_vals[11]
            flag_cell_address = unsent_row_vals[-2]
            response_th_cell_address = unsent_row_vals[-1]

            # Calculate Response Time
            created_date_time = datetime.strptime(created_date, "%d/%m/%Y, %H:%M:%S")
            response_date_time = datetime.strptime(response_date, "%d/%m/%Y, %H:%M:%S")
            total_response_time = response_date_time - created_date_time

            if req_type == "Agency Request":
                request_channel_id = channel_name_to_id(request_channel_name)
                req_channel_name = request_channel_name
            else:
                request_channel_id = channel_name_to_id(request_channel_direct)
                req_channel_name = request_channel_direct


            req_thread_ts = get_elapsed_ts(request_channel_id, req_thread_ts)
            if req_thread_ts:
                # Edit Message in "rfp-leads"
                updated_slack_message = (f"`Budget:` {budget} | `Rep:` {rep_name} | "
                                         f"`Response Time:` {total_response_time}")
                edit_slack_message(channel=request_channel_id,
                                   thread_ts=req_thread_ts,
                                   updated_text=updated_slack_message)

                # Send Message to "rfp-leads"
                thread_msg_text = f"""*Response Body* : {response_body}\n*Url*: {url}"""
                thread_emojis = ["alphabet-white-s", "alphabet-white-e", "alphabet-white-n", "alphabet-white-t",
                                 "alphabet-white-exclamation"]
                respond_to_slack_message(channel=req_channel_name,
                                         thread_ts=req_thread_ts,
                                         text=thread_msg_text)

                # React to the Message in "rfp-leads"
                react_to_slack_message(channel_id=request_channel_id,
                                       thread_ts=req_thread_ts,
                                       reactions=thread_emojis)
            else:
                gs_update_data(sh, flag_cell_address, "Expired Thread")
                continue

            # Send Message to "rfp-response-time"
            # Craft Message and Message Thread
            # main_body_msg = f"""*Budget* : {budget}\n*Time to response*: {total_response_time} hours"""
            main_body_msg = f"`Budget:` {budget} | `Rep:` {rep_name} | `Response Time:` {total_response_time}"
            thread_msg_text = f"""*Response Body* : {response_body}\n*Url*: {url}"""

            # Send the Message Main Body
            msg_response = slack_notification(channel=response_channel_name, msg_text=main_body_msg)
            gs_update_data(sh, response_th_cell_address, msg_response)

            # Send the Response.
            respond_to_slack_message(channel=response_channel_name, text=thread_msg_text, thread_ts=msg_response)

            # Add a "Y" to flag that a message has been sent for this lead
            gs_update_data(sh, flag_cell_address, "Y")
            devtracker_sleep(2, 5)
    else:
        logging.info("[Requests Notifier]: No Messages to Send")
    logging.info("[Requests Notifier]: Iteration complete, Restarting...")
    devtracker_sleep(5, 10)


def exec_resp_slack_notifier():
    logging.info("[Requests Notifier]: Starting Response Slack Notifier")
    slack_notification(channel=alerts_channel_name,
                       msg_text=":grey_exclamation: RFP Response Slack Notifier Started! :rocket:")
    while True:
        try:
            resp_slack_notifier()
        except Exception as e:
            logging.info(f"[Requests Notifier]: RFP Response Slack Notifier is Down,  Error: {e}")
            slack_notification(channel=alerts_channel_name,
                               msg_text=":grey_exclamation: :x: RFP Response Slack Notifier is Down :x:",
                               exception_trace=e)
            break

    devtracker_sleep(30, 60)
    slack_notification(channel=alerts_channel_name,
                       msg_text=":grey_exclamation: :recycle: Restarting RFP Response Slack Notifier :recycle:")
    exec_resp_slack_notifier()


if __name__ == '__main__':
    exec_resp_slack_notifier()
