# coding: utf-8
import logging

import pandas as pd

from bids_functions import get_io_bids
from functions import bubbleio_login
from functions import devtracker_sleep
from functions import diff_df_by_column
from functions import get_driver
from functions import gs_get_data
from functions import gs_insert_data
from functions import open_worksheet
from functions_slack import slack_notification
from import_secrets import *


def bids_main_script():
    logging.info("[Bids]: Starting Bubbleio Dev Monitor Tool")
    slack_notification(channel=alerts_channel_name, msg_text=":outbox_tray: RFP Bids Script Started!  :rocket:")
    # Setting the number of pages from which script can get bids
    page_limit = 1

    try:
        # Check Login & Get apps to track
        driver = get_driver()
        is_logged_in = bubbleio_login(driver)

        if is_logged_in:
            while True:
                try:
                    # Get Existing Data
                    sh = open_worksheet(bid_sheet_name)
                    logging.info(f"[Bids]: Getting Bids, Page Limit: {page_limit}")
                    bids_sh_data = gs_get_data(sh)
                    logging.info(f"[Bids]: Existing Records: {str(len(bids_sh_data))}")
                    bids_sheet_cols = ['rfp_id', 'name', 'response_date', 'response', 'bid_url', 'rep_name',
                                       'rep_calendly_link']
                    if len(bids_sh_data) > 0:
                        existing_bids_df = pd.DataFrame(bids_sh_data, columns=bids_sheet_cols)
                    else:
                        existing_bids_df = pd.DataFrame([], columns=bids_sheet_cols)

                    # Get New Data
                    bids = get_io_bids(driver, page_limit)
                    if len(bids) > 0:
                        ext_bids_df = pd.DataFrame(bids, columns=bids_sheet_cols)
                    else:
                        ext_bids_df = pd.DataFrame([], columns=bids_sheet_cols)

                    # Check if there are new records
                    diff_df = diff_df_by_column(df_new=ext_bids_df,
                                                df_old=existing_bids_df,
                                                column_name='rfp_id',
                                                duplicate_criteria=['rfp_id', 'name', 'response', 'bid_url', 'rep_name',
                                                                    'rep_calendly_link'])
                    new_rec_count = str(diff_df.shape[0])
                    logging.info(f"[Bids]: New Unique records found: {new_rec_count}")
                    diff_df_final = diff_df.fillna("")
                    gs_insert_data(sh, diff_df_final.values.tolist())
                    devtracker_sleep(10, 15)

                except Exception as e:
                    logging.info(f"[Bids]: RFP Bids Tracker is down: {e}")
                    slack_notification(channel=alerts_channel_name,
                                       msg_text=":outbox_tray: :x: RFP Bids Tracker is down. :x:", exception_trace=e)
                    break

        # Quiting Driver & Restarting
        try:
            driver.quit()
            logging.info(f"[Bids]: Closing Driver")
        except Exception as e:
            logging.warning(f"[Bids]: Driver is already closed {e}")
    except Exception as e:
        logging.critical(f"[Bids]: RFP Bids Tracker is down: {e}")
        slack_notification(channel=alerts_channel_name,
                           msg_text=":outbox_tray: :x: RFP Bids Tracker is down. :x:", exception_trace=e)

    # Restarting
    devtracker_sleep(30, 60)
    slack_notification(channel=alerts_channel_name,
                       msg_text=":outbox_tray: :recycle: Restarting RFP Bids Tracker. :recycle:")
    bids_main_script()


if __name__ == '__main__':
    bids_main_script()
