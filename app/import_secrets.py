# coding: utf-8
import os
from dotenv import load_dotenv

# Initialize Env
# load_dotenv()
load_dotenv("../.env.prod")

# CREDs
email = os.environ.get("EMAIL")
password = os.environ.get("PASS")

# Slack
slack_messaging = os.environ.get("SLACK_MESSAGING")
slack_secret = os.environ.get("SLACK_APP_SECRET")
alerts_channel_name = os.environ.get("ALERTS_SLACK_CH_NAME")
request_channel_name = os.environ.get("AGENCY_REQS_SLACK_CH_NAME")
request_channel_direct = os.environ.get("DIRECT_REQS_SLACK_CH_NAME")
response_channel_name = os.environ.get("RESPONSE_SLACK_CH_NAME")

# GS
spreadsheet_id = os.environ.get("SPREADSHEET_ID")
service_acc_credentials = os.environ.get("SERVICE_ACCOUNT_CREDENTIALS")
req_sheet_name = os.environ.get("REQ_SHEET_NAME")
bid_sheet_name = os.environ.get("BID_SHEET_NAME")
lead_sheet_name = os.environ.get("LEADS_SHEET_NAME")
