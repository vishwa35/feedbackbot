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

store = {}

# converted to following structure for multi user answering support
# dict store
# top level: per question/command (callback_id)
#   users: list
#   counter: defaultdict(int)
#   ques_ts: public message_ts
#   admin_ts: admin message_ts
# EXAMPLE:
# store = {"feedback1": {"users": [], "counter": defaultdict(int), "ques_ts": "1503435956.000247", "admin_ts": "1503484268.000285"}}

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
      # TODO: update the question using ques_ts
      # response = slack_client.api_call(
      #   "chat.update",
      #   ts=form_json["message_ts"],
      #   channel=form_json["channel"]["id"],
      #   text="Results for " + form_json["original_message"]["text"],
      #   attachments=[{
      #     "text": results(form_json["callback_id"])
      #   }]
      # )

    else:
      # TODO: delete entries after x amount of time
      counter = store[form_json['callback_id']]["counter"]
      if form_json["user"]["id"] not in store[form_json['callback_id']]["users"]:
        counter[form_json["actions"][0]["name"]] += 1
        answer = form_json["actions"][0]["name"]
        store[form_json['callback_id']]["users"].append(form_json["user"]["id"])

        # response based on request
        if "vote" in form_json["callback_id"]:
          text = "Thanks for voting! You voted for {}.".format(answer)
        else:
          text = "Thanks for the feedback! You {} that {}.".format(answer.lower(), form_json["original_message"]["text"])

        response = slack_client.api_call(
          "chat.postEphemeral",
          channel=form_json["channel"]["id"],
          text=text,
          user=form_json["user"]["id"]
        )
      else:
        if "vote" in form_json["callback_id"]:
          text = "You already voted!"
        else:
          text = "You already answered."
        response = slack_client.api_call(
          "chat.postEphemeral",
          channel=form_json["channel"]["id"],
          text=text,
          user=form_json["user"]["id"]
        )

    return make_response("", 200)

def results(callback_id):
    callback_id = callback_id.replace("Admin", "")
    counter = json.dumps(store[callback_id]["counter"])
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

    response1 = slack_client.api_call(
      "chat.postMessage",
      channel=im_id,
      text=statement,
      attachments=admin_json
    )["message"]

    response2 = slack_client.api_call(
      "chat.postMessage",
      channel="#" + request.form["channel_name"],
      text=statement,
      attachments=attachments_json
    )["message"]

    store["feedback" + str(feedback_id)] = {"users": [], "counter": defaultdict(int), "ques_ts": response1["ts"], "admin_ts": response2["ts"]}

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

      response1 = slack_client.api_call(
        "chat.postMessage",
        channel=im_id,
        text=statement,
        attachments=admin_json
      )["message"]

      response2 = slack_client.api_call(
        "chat.postMessage",
        channel="#" + request.form["channel_name"],
        text="Vote!",
        attachments=attachments_json
      )["message"]

      store["vote" + str(vote_id)] = {"users": [], "counter": defaultdict(int), "ques_ts": response1["ts"], "admin_ts": response2["ts"]}

      vote_id += 1
    return make_response("", 200)

# Start the Flask server
if __name__ == "__main__":
    app.run()