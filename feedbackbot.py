from flask import Flask, request, make_response, Response
import json
from collections import defaultdict
from tokens import SLACK_BOT_TOKEN, SLACK_VERIFICATION_TOKEN
from slackclient import SlackClient


slack_client = SlackClient(SLACK_BOT_TOKEN)
app = Flask(__name__)

feedback_id = 0
vote_id = 0

#TODO: Add checks for all responses from slack api calls

store = defaultdict(lambda: defaultdict(int))

# TODO: convert to following structure for multi user answering support
# dict store
# top level: per question/command (callback_id)
#   users: list
#   counter: defaultdict(int)
#   ques_ts: public message_ts
#   admin_ts: admin message_ts


def verify_slack_token(request_token):
    if SLACK_VERIFICATION_TOKEN != request_token:
        print("Error: invalid verification token!")
        print("Received {} but was expecting {}".format(request_token, SLACK_VERIFICATION_TOKEN))
        return make_response("Request contains invalid Slack verification token", 403)

@app.route("/slack/message_actions", methods=["POST"])
def message_actions():

    form_json = json.loads(request.form["payload"])
    verify_slack_token(form_json["token"])

    if "Admin" in form_json["callback_id"]:
      response = slack_client.api_call(
        "chat.update",
        ts=form_json["message_ts"],
        channel=form_json["channel"]["id"],
        text="Results for " + form_json["original_message"]["text"],
        attachments=[{
          "text": results(form_json["callback_id"])
        }]
      )
    else:
      # TODO: delete entries after x amount of time
      counter = store[form_json['callback_id']]
      counter[form_json["actions"][0]["name"]] += 1
      answer = form_json["actions"][0]["name"]

      # response based on request
      if "vote" in form_json["callback_id"]:
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

def results(callback_id):
    # TODO: delete entries after x amount of time
    callback_id = callback_id.replace("Admin", "")
    counter = json.dumps(store[callback_id])
    del store[callback_id]
    return counter

@app.route("/slack/feedback", methods=["POST"])
def feedback():
    global feedback_id
    statement = request.form["text"]

    options = ["Strongly Agree", "Agree", "Neither Agree/Disagree", "Disagree", "Strongly Disagree"]
    actions = []
    for x, opt in enumerate(options):
      actions.append({"name": opt, "text": opt, "type": "button", "value": x})

    attachments_json = [
        {
            "fallback": "Upgrade your Slack client!",
            "callback_id": "feedback" + str(feedback_id),
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": actions
        }
    ]

    admin_json = [
        {
            "fallback": "Upgrade your Slack client!",
            "callback_id": "feedbackAdmin" + str(feedback_id),
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": [{"name": "Get Results", "text": "Get Results", "type": "button", "value": 0}]
        }
    ]

    im_id = slack_client.api_call(
      "im.open",
      user=request.form["user_id"]
    )["channel"]["id"]

    response = slack_client.api_call(
      "chat.postMessage",
      channel=im_id,
      text=statement,
      attachments=admin_json
    )

    response = slack_client.api_call(
      "chat.postMessage",
      channel="#" + request.form["channel_name"],
      text=statement,
      attachments=attachments_json
    )

    feedback_id += 1
    return make_response("", 200)

@app.route("/slack/vote", methods=["POST"])
def vote():
    global vote_id
    statement = request.form["text"]

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
            "callback_id": "vote" + str(vote_id),
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": actions
        }
      ]

      admin_json = [
        {
            "fallback": "Upgrade your Slack client!",
            "callback_id": "voteAdmin" + str(vote_id),
            "color": "#3AA3E3",
            "attachment_type": "default",
            "actions": [{"name": "Get Results", "text": "Get Results", "type": "button", "value": 0}]
        }
      ]

      im_id = slack_client.api_call(
        "im.open",
        user=request.form["user_id"]
      )["channel"]["id"]

      response = slack_client.api_call(
        "chat.postMessage",
        channel=im_id,
        text=statement,
        attachments=admin_json
      )

      response = slack_client.api_call(
        "chat.postMessage",
        channel="#" + request.form["channel_name"],
        text="Vote!",
        attachments=attachments_json
      )
      vote_id += 1
    return make_response("", 200)

# Start the Flask server
if __name__ == "__main__":
    app.run()