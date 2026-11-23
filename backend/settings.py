"""Fixed rules of the game, taken from the Excel model it was played with."""

STARTING_CAPITAL = 600
# Price of one insider tip in turn 1, 2, 3, ...; the last value repeats for later turns.
INSIDER_COSTS = (5, 10, 30)
RESULTS_SECONDS = 15        # how long the results of a turn stay on screen
MIN_TEAMS = 2               # teams needed before the start countdown can begin
MAX_TEAMS = 20
COUNTDOWN_SECONDS = 10      # lobby countdown once every joined team is ready
STALE_LOBBY_SECONDS = 60    # a team that stops polling in the lobby is dropped
CLEANUP_EVERY_SECONDS = 60
