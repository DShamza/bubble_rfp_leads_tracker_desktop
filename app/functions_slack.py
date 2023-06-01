# coding: utf-8
import logging
import traceback
from time import sleep
from import_secrets import *
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

client = WebClient(token=slack_secret)


def get_elapsed_ts(channel_id, message_ts):
    """
    The Slack messages timestamps are converted to elapsed time after 24 hours,
    this function extracts the timestamp for the messages upto 7 Days.
    Args:
        channel_id:
        message_ts:

    Returns:

    """
    try:
        response = client.conversations_history(channel=channel_id, latest=message_ts, limit=1, inclusive=True)
        message = response['messages'][0]
        original_timestamp = message['ts']
        print(f"Original Timestamp: {original_timestamp}")
        return original_timestamp
    except SlackApiError as _e:
        print(f"Error retrieving message details: {_e.response['error']}")
    except IndexError:
        return ""


def channel_name_to_id(channel_name):
    """
    Function to convert channel name to ID
    Args:
        channel_name:

    Returns:

    """
    try:
        response = client.conversations_list(types="private_channel")
        channels = response['channels']
        # Iterate through the channels to find the matching channel name
        for channel in channels:
            if channel['name'] == channel_name:
                channel_id = channel['id']
                return channel_id
        else:
            print(f"No channel found with the name: {channel_name}")
    except Exception as _e:
        print(f"Error retrieving channel list: {str(_e)}")


def respond_to_slack_message(channel, thread_ts, text, msg_blocks=None):
    """
    Sends a response message to a Slack thread.

    Args:
        channel (str): Channel Name where the thread is located.
        thread_ts (str): Timestamp of the thread to respond to.
        text (str): Text of the response message.
        msg_blocks: Creatively rich or interactive message.

    Returns:
        None: Prints a success message if the message is sent successfully.
              Prints an error message if there is an issue sending the message.
    """
    try:
        response = client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=text,
            blocks=msg_blocks
        )
        if response["ok"]:
            print(f"Message sent successfully.")
        else:
            print(f"Failed to send message. Error: {response['error']}")

    except SlackApiError as _e:
        print(f"Failed to send message. Error: {_e.response['error']}")


def react_to_slack_message(channel_id, thread_ts, reactions):
    """
    Reacts to a Slack message with one or more specified emoji reactions.

    Args:
        channel_id (str): Channel ID where the message is located.
        thread_ts (str): Timestamp of the message to react to.
        reactions (list): Emoji reactions to add to the message.

    Returns:
        None: Prints a success message if the reaction is added successfully.
              Prints an error message if there is an issue adding the reaction.
    """

    try:
        for reaction in reactions:
            response = client.reactions_add(
                channel=channel_id,
                timestamp=thread_ts,
                name=reaction
            )
            if response["ok"]:
                print(f"Reaction '{reaction}' added successfully.")
            else:
                print(f"Failed to add reaction. Error: {response['error']}")
            sleep(0.1)

    except SlackApiError as _e:
        print(f"Failed to add reaction. Error: {_e.response['error']}")


def slack_notification(channel, msg_text, exception_trace=None):
    """
    function that posts a message to a given Slack channel. If the message
    contains a notification with a traceback, the function also attaches
    the traceback to the message thread.
    Args:
        channel (str): Channel Name where the thread is located.
        msg_text (str): Text of the response message.
        exception_trace (Exception): Traceback of the error if any.

    Returns:

    """
    try:
        response = client.chat_postMessage(channel=channel, text=msg_text, parse="full")
        msg_ts = response["ts"]
        if exception_trace:
            # Set the exception traceback as a code block
            traceback_string = traceback.format_exc()
            traceback_block = {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"Error Traceback: ```\n{traceback_string}\n```"
                }
            }
            traceback_blocks = [traceback_block]
            respond_to_slack_message(channel=channel, thread_ts=msg_ts, text=msg_text, msg_blocks=traceback_blocks)
        assert response["message"]["text"] == msg_text
        return msg_ts
    except SlackApiError as _e:
        # You will get a SlackApiError if "ok" is False
        assert _e.response["ok"] is False
        assert _e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        logging.critical(f"Got an error: {_e.response['error']}")
