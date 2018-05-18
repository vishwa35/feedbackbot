from flask import Flask, request, make_response, Response
import json
from collections import defaultdict
from tokens import SLACK_BOT_TOKEN, SLACK_VERIFICATION_TOKEN
from slackclient import SlackClient


slack_client = SlackClient(SLACK_BOT_TOKEN)
app = Flask(__name__)

# TODO: handle per request and return to user who requested
counter = defaultdict(int)

def verify_slack_token(request_token):
    if SLACK_VERIFICATION_TOKEN != request_token:
        print("Error: invalid verification token!")
        print("Received {} but was expecting {}".format(request_token, SLACK_VERIFICATION_TOKEN))
        return make_response("Request contains invalid Slack verification token", 403)

@app.route("/slack/message_actions", methods=["POST"])
def message_actions():

    form_json = json.loads(request.form["payload"])
    verify_slack_token(form_json["token"])
    print form_json

    # TODO: counter handling based on request, returning results
    counter[form_json["actions"][0]["name"]] += 1
    answer = form_json["actions"][0]["name"]

    # response based on request
    if form_json["callback_id"] == "vote":
      response = slack_client.api_call(
        "chat.update",
        ts=form_json["message_ts"],
        channel=form_json["channel"]["id"],
        text="Thanks for voting! You voted for {}".format(answer),
        attachments="[]"
      )
    else:
      response = slack_client.api_call(
        "chat.update",
        ts=form_json["message_ts"],
        channel=form_json["channel"]["id"],
        text="Thanks for the feedback! You {} that {}".format(answer.lower(), form_json["original_message"]["text"]),
        attachments="[]"
      )

    return make_response("", 200)


@app.route("/slack/feedback", methods=["POST"])
def feedback():
    statement = request.form["text"]

    options = ["Strongly Agree", "Agree", "Neither Agree/Disagree", "Disagree", "Strongly Disagree"]
    actions = []
    for x, opt in enumerate(options):
      actions.append({"name": opt, "text": opt, "type": "button", "value": x})

    attachments_json = [
        {
            "fallback": "Upgrade your Slack client!",
            "callback_id": "feedback",
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": actions
        }
    ]

    slack_client.api_call(
      "chat.postMessage",
      channel="#" + request.form["channel_name"],
      text=statement,
      attachments=attachments_json
    )
    return make_response("", 200)

@app.route("/slack/vote", methods=["POST"])
def vote():
    options = request.form["text"].split(",")
    if len(options) < 2:
      # Tell user they need to supply at least two comma separated options
      slack_client.api_call(
      "chat.postEphemeral",
      channel="#" + request.form["channel_name"],
      text="You must provide at least 2 options separated by a comma",
      user=request.form["user_id"]
    )
    else:
      actions = []
      for x, opt in enumerate(options):
        actions.append({"name": opt, "text": opt, "type": "button", "value": x})

      attachments_json = [
        {
          "fallback": "Upgrade your Slack client!",
            "callback_id": "vote",
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": actions
        }
      ]

    slack_client.api_call(
      "chat.postMessage",
      channel="#" + request.form["channel_name"],
      text="Vote!",
      attachments=attachments_json
    )
    return make_response("", 200)

# Start the Flask server
if __name__ == "__main__":
    app.run()