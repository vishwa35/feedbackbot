from flask import Flask, request, make_response, Response
import json
from collections import defaultdict
from tokens import SLACK_BOT_TOKEN, SLACK_VERIFICATION_TOKEN
from slackclient import SlackClient
from vote import Vote
from ask import Ask


slack_client = SlackClient(SLACK_BOT_TOKEN)
app = Flask(__name__)

feedback_id = 0
vote_id = 0

asker = Ask()
voter = Vote()
slasher = {asker.command : asker, voter.command: voter}


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
  callback_id = form_json['callback_id']
  verify_slack_token(form_json["token"])

  if "admin" in form_json["callback_id"]:
    adminButtonResponse(form_json)

  else:
    # TODO: delete entries after x amount of time
    # check if user already responded
    if form_json["user"]["id"] not in store[callback_id]["users"]:
      # add response and record user
      newResponse(form_json)
    else:
      text = getSlasher(callback_id).DUPL_RESPONSE_MSG
      response = slack_client.api_call(
        "chat.postEphemeral",
        channel=form_json["channel"]["id"],
        text=text,
        user=form_json["user"]["id"]
      )

  return make_response("", 200)

@app.route("/slack/feedback", methods=["POST"])
def feedback():
  global feedback_id

  attachments_json, admin_json = asker.construct(feedback_id)

  slash(asker.getCallback(feedback_id), request.form, attachments_json, admin_json)

  feedback_id += 1
  return make_response("", 200)

@app.route("/slack/vote", methods=["POST"])
def vote():
  global vote_id

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
    attachments_json, admin_json = voter.construct(vote_id, options)

    slash(voter.getCallback(vote_id), request.form, attachments_json, admin_json)

    vote_id += 1
  return make_response("", 200)

def slash(callback, info, attachments_json, admin_json):
  im_id = slack_client.api_call(
    "im.open",
    user=info["user_id"]
  )["channel"]["id"]

  ownerMsg = slack_client.api_call(
    "chat.postMessage",
    channel=im_id,
    text=request.form["text"],
    attachments=admin_json
  )["message"]

  channelMsg = slack_client.api_call(
    "chat.postMessage",
    channel="#" + info["channel_name"],
    text=request.form["text"],
    attachments=attachments_json
  )["message"]

  store[callback] = {"users": [], "counter": defaultdict(int), "ques_ts": channelMsg["ts"], "admin_ts": ownerMsg["ts"], "ques_channel": info["channel_id"], "ques": request.form["text"]}

def results(callback_id):
  channelMsg = slack_client.api_call(
        "chat.update",
        ts=store[callback_id]["ques_ts"],
        channel=store[callback_id]["ques_channel"],
        text=store[callback_id]["ques"],
        attachments=[{
          "text": "Voting has closed"
        }]
      )

  counter = store[callback_id]["counter"]
  del store[callback_id]
  return sum(counter.values()), counter

def temp_results(callback_id):
  counter = store[callback_id]["counter"]
  return sum(counter.values()), counter

def adminButtonResponse(form_json):
  callback_id = form_json["callback_id"].replace("-admin", "")
  value = int(form_json["actions"][0]["value"])
  if not value:
    text1 = "Results for {}".format(store[callback_id]["ques"])
    total, counter = results(callback_id)
    resString = ["{}: {}\n".format(k, counter[k]) for k in counter]
    text2 = [{ "text": "Total Responses: {}\n{}".format(total, ''.join(resString)) }] # destroys row in store
  else:
    text2 = getSlasher(callback_id).getAdminJSON(callback_id.split('-')[-1])
    total, counter = temp_results(callback_id)
    resString = ["{}: {}\n".format(k, counter[k]) for k in counter]
    text1 = "{}\n{} responses so far.\n{}".format(store[callback_id]["ques"], total, ''.join(resString))

  ownerMsg = slack_client.api_call(
    "chat.update",
    ts=form_json["message_ts"],
    channel=form_json["channel"]["id"],
    text=text1,
    attachments=text2
  )

  return ownerMsg

def newResponse(form_json):
  callback_id = form_json["callback_id"]
  answer = form_json["actions"][0]["name"]
  uid = form_json["user"]["id"]
  counter = store[callback_id]["counter"]

  counter[answer] += 1
  store[callback_id]["users"].append(uid)

  # response based on request
  text = getSlasher(callback_id).RESPONSE_MSG.format(answer, form_json["original_message"]["text"])

  response = slack_client.api_call(
    "chat.postEphemeral",
    channel=form_json["channel"]["id"],
    text=text,
    user=uid
  )

  return response

def getSlasher(callback_id):
  return slasher[callback_id.split('-')[0]]

# Start the Flask server
if __name__ == "__main__":
  app.run()