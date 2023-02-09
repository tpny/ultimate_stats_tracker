from flask import Flask
from flask import render_template, request, redirect, url_for

import numpy as np

import mysql_connector

#const
ACTIONS = ["DROP", "THROW_AWAY", "DEFENSE", "GOAL"]
STATS = ["GOAL", "ASSIST", "BLOCK", "CATCH_BLOCK", "DROP", "THROW_AWAY", "POSSESSION", "CALLAHAN"]
APP = Flask(__name__)
db_connector = mysql_connector.MySQLConnector(STATS);


GOAL = 0
ASSIST = 1
BLOCK = 2
CATCH_BLOCK = 3
DROP = 4
THROW_AWAY = 5
POSSESSION = 6
CALLAHAN = 7
STATS_COUNT = 8

#static
teams_to_id = {}
players_to_id = {}
id_to_teams = {}
id_to_players = {}
team_id_to_players = {}


def compute_play_stats(play_seq, players_in_team):
  player_stats = {}
  one_prior = ""
  two_prior = ""
  three_prior = ""

  for play in play_seq:
    if(play in players_in_team): # is player
      player = play
      if(player not in player_stats):
        player_stats[player] = [0] * STATS_COUNT
      player_stats[player][POSSESSION] += 1
      if(one_prior == "DEFENSE" and two_prior == player):
          player_stats[player][CATCH_BLOCK] += 1
          player_stats[player][BLOCK] -= 1

    else: # is not player
      player = one_prior
      if(play == "DEFENSE"):
        player_stats[player][BLOCK] += 1
        player_stats[player][POSSESSION] -= 1
      elif(play == "DROP"):
        player_stats[player][DROP] += 1
        player_stats[player][POSSESSION] -= 1
      elif(play == "THROW_AYAW"):
        player_stats[player][THROW_AYAW] += 1
      elif(play == "GOAL"):
        player_stats[player][GOAL] += 1
        if(two_prior in players_in_team):
          player_stats[two_prior][ASSIST] += 1
        elif(two_prior == "DEFENSE"):
          player_stats[player][CALLAHAN] += 1

    three_prior = two_prior
    two_prior = one_prior
    one_prior = play

  invalid_moves = set()
  if(one_prior in players_in_team):
    invalid_moves.add(one_prior)
    if((two_prior not in players_in_team) and (two_prior != "DEFENSE" or three_prior != one_prior)):
      invalid_moves.add("GOAL")
    if(two_prior == "DEFENSE"):
      invalid_moves.add("DEFENSE")
    if(two_prior not in players_in_team):
      invalid_moves.add("DROP")
  else:
    invalid_moves.update(ACTIONS)

  return player_stats, invalid_moves

@APP.route('/record/<team_name>_<game_id>', methods = ["POST", "GET"])
def record(team_name, game_id):
  global teams_to_id
  global team_id_to_players

  team_id = teams_to_id[team_name]

  play = db_connector.get_plays(team_id = team_id, game_id = game_id)
  plays = []
  if(play): #not empty
      plays = play[2].split(",")
  if(request.method == "POST"):
    action_type = request.form.get("button")
    play = db_connector.get_plays(team_id = team_id, game_id = game_id)
    if(action_type == "UNDO"):
      del plays[-1]
    else:
      plays.append(action_type)
    plays_str = ",".join(plays)
    db_connector.insert_or_update_play(team_id = team_id, game_id = game_id, plays_str = plays_str, processed = False)

  team_players = team_id_to_players[teams_to_id[team_name]]
  player_stats, invalid_moves = compute_play_stats(plays, team_players)

  return render_template("record.html", players = sorted(team_players), plays = reversed(plays[-10:]), actions = ACTIONS, invalid_moves = invalid_moves, stats_header = STATS, player_stats = player_stats, hide_stats = "" if player_stats else "hidden", disable_undo = len(plays) == 0)


@APP.route('/')
@APP.route('/index')
def index():
  teams = db_connector.get_teams()
  team_dict = {}
  for team in teams:
    team_dict[team[0]] = team[1]

  games = db_connector.get_games()
  game_info = []
  for game in games:
    game_info.append((game[0], team_dict[game[1]], team_dict[game[2]]))
  return render_template("index.html", game_info = game_info)

@APP.route('/list_teams', methods = ["POST", "GET"])
def list_teams():
  global teams_to_id

  err = ""
  if(request.method == "POST"):
    action_type = request.form.get("button")
    if(action_type == "View Stats"):
      pass
    elif(action_type == "Edit Team"):
      return redirect(url_for("edit_team", team_name = request.form.get("team_name")))
    elif(action_type == "Create Team"):
      new_team = request.form.get("team_name")
      if(new_team in teams_to_id):
        err = "Team {} already exists".format(new_team)
      else:
        db_connector.create_team(new_team);
        refresh_teams()
        return redirect(url_for("edit_team", team_name = new_team))

  return render_template("list_teams.html", teams_to_id = teams_to_id, error = err)

@APP.route('/edit_team/<team_name>', methods = ["POST", "GET"])
def edit_team(team_name):
  global teams_to_id
  global id_to_teams
  global players_to_id

  team_id = teams_to_id[team_name]
  err = ""
  if(request.method == "POST"):
    action_type = request.form.get("button")
    if(action_type == "Add Player"):
      new_player = request.form.get("player_name")
      if(new_player in players_to_id):
        err = "Player {} already registered with {}".format(new_player, id_to_teams[players_to_id[new_player][1]])
      else:
        db_connector.create_player(player_name = new_player, team_id = team_id);
        refresh_players()
    elif(action_type == "Remove Player"):
      player_name = request.form.get("player_name")
      print(player_name, players_to_id[player_name][0])
      db_connector.remove_player(players_to_id[player_name][0])
      refresh_players()
    elif(action_type == "Rename Player"):
      player_name = request.form.get("player_name")
      new_player_name = request.form.get("new_name")
      if(new_player_name in players_to_id):
        err = "Player {} already registered with {}".format(new_player_name, id_to_teams[players_to_id[new_player_name][1]])
      else:
        db_connector.update_player(players_to_id[player_name][0], new_player_name, team_id)
        refresh_players()
    elif(action_type == "Transfer Player"):
      player_name = request.form.get("player_name")
      new_team_id = teams_to_id[request.form.get("new_team")]
      db_connector.update_player(players_to_id[player_name][0], player_name, new_team_id)
      refresh_players()
    elif(action_type == "View Stats"):
      return redirect(url_for("view_player_stat", player_name = request.form.get("player_name")))
    elif(action_type == "Rename Team"):
      new_team_name = request.form.get("new_name")
      if(new_team_name in teams_to_id):
        err = "Team {} already exists".format(new_team_name)
      else:
        db_connector.update_team(team_id = team_id, team_name = new_team_name)
        refresh_teams()
        return redirect(url_for("edit_team", team_name = new_team_name))

  players = []
  for player_name in players_to_id:
    if(players_to_id[player_name][1] == team_id):
      players.append((player_name, players_to_id[player_name][0]))

  return render_template("edit_team.html", curr_team_name = team_name, error = err, players = players, team_names = teams_to_id.keys())

@APP.route('/list_games', methods = ["POST", "GET"])
def list_games():
  err = ""
  if(request.method == "POST"):
    action_type = request.form.get("button")
    if(action_type == "Create Game"):
      home_team_id = teams_to_id[request.form.get("home_team")]
      away_team_id = teams_to_id[request.form.get("away_team")]
      game_time = request.form.get("game_time")
      note =request.form.get("note")
      if(home_team_id == away_team_id):
        err = "Home and aways team cannot be the same"
      else:
        # def create_game(self, home_team_id, away_team_id, game_time = None):
        db_connector.create_game(home_team_id = home_team_id, away_team_id = away_team_id, game_time = game_time)
    elif(action_type == "Start Record"):
      team_name = id_to_teams[int(request.form.get("team_id"))]
      game_id = int(request.form.get("game_id"))
      print(team_name, game_id)
      return redirect(url_for("record", team_name = team_name, game_id = game_id))
    
  return render_template("list_games.html", team_names = teams_to_id.keys(), games = db_connector.get_games(), id_to_teams = id_to_teams, error = err)


@APP.route('/view_team_stat/<team_name>', methods = ["POST", "GET"])
def view_team_stat(team_name):
  team_id = teams_to_id(team_name)
  return "TODO"

@APP.route('/view_player_stat/<player_name>', methods = ["POST", "GET"])
def view_player_stat(player_name):
  player_id = players_to_id[player_name]
  return "TODO"

def update_db_player_stats():
  unprocessed_plays = db_connector.get_plays(unprocessed = True)
  for unprocessed_play in unprocessed_plays:
    team_id = unprocessed_play[0]
    game_id = unprocessed_play[1]
    plays_str = unprocessed_play[2]
    players_to_id = {}
    for players_in_team in db_connector.get_players(team_id):
      players_to_id[players_in_team[1]] = players_in_team[0]
    player_stats, invalid_moves = compute_play_stats(plays_str.split(","), players_to_id)
    db_connector.insert_or_update_player_stats(player_stats, players_to_id, team_id, unprocessed_play[1])
    db_connector.insert_or_update_play(team_id, game_id, plays_str, processed = True)
    
def refresh_teams():
  global teams_to_id
  global id_to_teams
  teams_to_id = {}
  id_to_teams = {}

  for team_id, team_name in db_connector.get_teams():
    teams_to_id[team_name] = team_id
    id_to_teams[team_id] = team_name

def refresh_players():
  global players_to_id
  global id_to_players
  global team_id_to_players
  players_to_id = {}
  id_to_players = {}
  team_id_to_players = {}

  players_to_id = {}
  for player_id, player_name, team_id in db_connector.get_players():
    players_to_id[player_name] = (player_id, team_id)
    id_to_players[player_id] = player_name
    if(team_id not in team_id_to_players):
      team_id_to_players[team_id] = set()
    team_id_to_players[team_id].add(player_name)



if __name__ == "__main__":
  # players["team_1"] = ["A", "B", "C", "D", "E", "F"]
  # players["team_2"] = ["A", "B", "C", "D", "E", "F"]
  print("get_players")
  print(db_connector.get_players())
  print("get_teams")
  print(db_connector.get_teams())
  print("get_plays")
  print(db_connector.get_plays())
  print("get_games")
  print(db_connector.get_games())

  refresh_teams()
  refresh_players()
  update_db_player_stats()

  #db_connector.get_player_stats(game_id = None, player_id = None, team_id = None)


  APP.run('0.0.0.0', 5000, debug=False)

