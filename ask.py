# ask.py
from general import Slash

DEFAULT_OPTIONS = ["Strongly Agree", "Agree", "Neither Agree/Disagree", "Disagree", "Strongly Disagree"]
COMMAND = 'feedback'

class Ask(Slash):

  def __init__(self):
    Slash.__init__(self, COMMAND)
    self.RESPONSE_MSG = "Thanks for the feedback! You {} that {}."


  def construct(self, feedback_id, options=DEFAULT_OPTIONS):
    return Slash.construct(self, feedback_id, options)