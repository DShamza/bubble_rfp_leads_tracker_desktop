# coding: utf-8
import os
from dotenv import load_dotenv

# Initialize Env
load_dotenv()
# load_dotenv("../.env.prod")

email = os.environ.get("EMAIL")
password = os.environ.get("PASS")
slack_secret = os.environ.get("SLACK_APP_SECRET")
main_channel_name = os.environ.get("MAIN_SLACK_CHANNEL_NAME")
request_channel_name = os.environ.get("REQUESTS_SLACK_CHANNEL_NAME")
response_channel_name = os.environ.get("RESPONSE_SLACK_CHANNEL_NAME")
