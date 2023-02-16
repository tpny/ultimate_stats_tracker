from flask import render_template, request, redirect, url_for, jsonify
import mysql

from ultimate_stats_tracker import APP, db_connector, Stats, Actions, logger
from ultimate_stats_tracker import id_to_teams, teams_to_id, id_to_players, team_id_to_player_ids, team_id_to_player_base_ids, base_players_to_id, hidden_players_ids

def update_db_player_stats():
  unprocessed_plays = db_connector.get_plays(unprocessed = True)
  for unprocessed_play in unprocessed_plays:
    team_id = str(unprocessed_play[0])
    game_id = str(unprocessed_play[1])
    plays_str = unprocessed_play[2]
    player_stats, invalid_moves = compute_play_stats(plays_str.split(","), team_id_to_player_ids[team_id])
    db_connector.insert_or_update_player_stats(player_stats, team_id, unprocessed_play[1])
    db_connector.insert_or_update_play(team_id, game_id, processed = True)
    
def refresh_globals():
  global id_to_teams
  global teams_to_id
  id_to_teams = {}
  teams_to_id = {}

  for team_id, team_name, hidden in db_connector.get_teams():
    team_id = str(team_id)

    id_to_teams[team_id] = team_name
    teams_to_id[team_name] = team_id

  global id_to_players
  global team_id_to_player_ids
  global team_id_to_player_base_ids
  global base_players_to_id
  global hidden_players_ids
  id_to_players = {}
  team_id_to_player_ids = {}
  team_id_to_player_base_ids = {}
  base_players_to_id = {}
  hidden_players_ids = set()

  for player_id, player_name, team_id, player_base_id, hidden in db_connector.get_players():
    player_id = str(player_id)

    if(hidden):
      hidden_players_ids.add(player_id)

    if(not player_base_id and not hidden):
      base_players_to_id[player_name] = player_id

    id_to_players[player_id] = player_name

    if(team_id): # this player is associated with a team
      team_id = str(team_id)

      if(team_id not in team_id_to_player_ids):
        team_id_to_player_ids[team_id] = set()
      if(team_id not in team_id_to_player_base_ids):
        team_id_to_player_base_ids[team_id] = set()

      team_id_to_player_ids[team_id].add(player_id)
      team_id_to_player_base_ids[team_id].add(str(player_base_id))

def compute_play_stats(play_seq, players_in_team):
  player_stats = {}
  one_prior = ""
  two_prior = ""
  three_prior = ""

  for play in play_seq:
    if(play in players_in_team): # is player
      player = play
      if(player not in player_stats):
        player_stats[player] = [0] * Stats.COUNT
      player_stats[player][Stats.POSSESSION] += 1
      if(one_prior == Actions.DEFENSE.name and two_prior == player):
          player_stats[player][Stats.CATCH_BLOCK] += 1
          player_stats[player][Stats.BLOCK] -= 1

    else: # is not player
      player = one_prior
      if(play == Actions.DEFENSE.name):
        player_stats[player][Stats.BLOCK] += 1
        player_stats[player][Stats.POSSESSION] -= 1
      elif(play == Actions.DROP.name):
        player_stats[player][Stats.DROP] += 1
        player_stats[player][Stats.POSSESSION] -= 1
      elif(play == Actions.THROW_AWAY.name):
        player_stats[player][Stats.THROW_AWAY] += 1
      elif(play == Actions.GOAL.name):
        player_stats[player][Stats.GOAL] += 1
        if(two_prior in players_in_team):
          player_stats[two_prior][Stats.ASSIST] += 1
        elif(two_prior == Actions.DEFENSE.name):
          player_stats[player][Stats.CALLAHAN] += 1

    three_prior = two_prior
    two_prior = one_prior
    one_prior = play

  invalid_moves = set()
  if(one_prior in players_in_team):
    invalid_moves.add(one_prior)
    if((two_prior not in players_in_team) and (two_prior != Actions.DEFENSE.name or three_prior != one_prior)):
      invalid_moves.add(Actions.GOAL.name)
    if(two_prior == Actions.DEFENSE.name):
      invalid_moves.add(Actions.DEFENSE.name)
    if(two_prior not in players_in_team):
      invalid_moves.add(Actions.DROP.name)
  else:
    invalid_moves.update(list(Actions.__members__.keys())[:-1])

  return player_stats, invalid_moves

@APP.route("/api/record", methods=["POST"])
def api_record():
  global team_id_to_player_ids
  game_id = request.form.get("game_id", "", type=str)
  team_id = request.form.get("team_id", "", type=str)
  play_str = request.form.get("play_str", "", type=str)
  db_connector.insert_or_update_play(team_id = team_id, game_id = game_id, plays_str = play_str, processed = False)
  player_stats, invalid_moves = compute_play_stats(play_seq = play_str.split(","), players_in_team = team_id_to_player_ids[team_id])
  return jsonify(player_stats = player_stats, invalid_moves = list(invalid_moves))

@APP.route("/api/exec_sql", methods=["POST"])
def api_exec_sql():
  err = ""
  result = []
  try:
    result = db_connector.execute_sql(request.form.get("query"))
  except mysql.connector.Error as error:
    err = str(error)

  return jsonify(result = result, error = err)

@APP.route("/api/reset_database", methods=["POST"])
def api_reset_database():
  db_connector.drop_tables()
  db_connector.create_tables()
  refresh_globals()
  return jsonify(success = "TRUE")

@APP.route("/api/reset_connection", methods=["POST"])
def api_reset_connection():
  db_connector.reset_connection()
  refresh_globals()
  return jsonify(success = "TRUE")
