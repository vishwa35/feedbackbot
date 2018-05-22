# general.py

RESPONSE_MSG = "Thanks!"
DUPL_RESPONSE_MSG = "You already responded!"

class Slash():

  def __init__(self, cmd):
    self.command = cmd
    self.RESPONSE_MSG = "Thanks!{}{}"
    self.DUPL_RESPONSE_MSG = "You already responded!"

  def construct(self, id, options):
    actions = []
    for x, opt in enumerate(options):
      actions.append({"name": opt, "text": opt, "type": "button", "value": x})

    return self.constructJSONattachments(id, actions)

  def constructJSONattachments(self, id, actions):
    admin_json = self.getAdminJSON(id)
    channel_json = self.getChannelJSON(id, actions)
    return channel_json, admin_json

  def getAdminJSON(self, id):
    return [
      {
        "fallback": "Upgrade your Slack client!",
        "callback_id": self.getAdminCallback(id),
        "color": "#3AA3E3",
        "attachment_type": "default",
        "actions": [{"name": "Get Results", "text": "Get Results + Close Poll", "type": "button", "value": 0},
        {"name": "Number of Responses", "text": "Number of Responses", "type": "button", "value": 1}]
      }
    ]

  def getChannelJSON(self, id, actions):
    return [
      {
        "fallback": "Upgrade your Slack client!",
        "callback_id": self.getCallback(id),
        "color": "#3AA3E3",
        "attachment_type": "default",
        "actions": actions
      }
    ]

  def getCallback(self, id):
    return self.command + '-' + str(id)

  def getAdminCallback(self, id):
    return self.command + '-admin-' + str(id)
