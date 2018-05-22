# vote.py
from general import Slash

COMMAND = 'vote'

class Vote(Slash):

  def __init__(self):
    Slash.__init__(self, COMMAND)
    self.RESPONSE_MSG = "Thanks for voting! You voted for {} in {}"
    self.DUPL_RESPONSE_MSG = "You already voted!"