from flask import Flask
from flask import render_template, request, redirect, url_for
import mysql

from ultimate_stats_tracker import APP, db_connector, Stats, Actions, logger

#static
id_to_teams = {}
teams_to_id = {}
id_to_players = {}
team_id_to_player_ids = {}
team_id_to_player_base_ids = {}
base_players_to_id = {}
hidden_players_ids = set()

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

@APP.route('/')
@APP.route('/index')
def index():
  db_connector.create_tables()
  refresh_globals()

  teams = db_connector.get_teams()
  team_dict = {}
  for team in teams:
    team_dict[team[0]] = team[1]

  games = db_connector.get_games()
  game_info = []
  for game in games:
    game_info.append((game[0], team_dict[game[1]], team_dict[game[2]]))
  return render_template("index.html", game_info = game_info)

@APP.route('/record/<team_id>_<game_id>', methods = ["POST", "GET"])
def record(team_id, game_id):
  global id_to_teams
  global id_to_players
  global team_id_to_player_ids
  global base_players_to_id

  team_id = str(team_id)
  game_id = str(game_id)

  play = db_connector.get_plays(team_id = team_id, game_id = game_id)
  plays = []
  if(play): #not empty
      plays = play[2].split(",")
  if(request.method == "POST"):
    action_type = request.form.get("button")
    if(action_type == "UNDO"):
      del plays[-1]
    else:
      plays.append(action_type)

    plays_str = ",".join(plays)
    db_connector.insert_or_update_play(team_id = team_id, game_id = game_id, plays_str = plays_str, processed = False)

  player_stats, invalid_moves = compute_play_stats(plays, team_id_to_player_ids[team_id])

  player_stats_in_names = {}
  deleted_player_stats = [0] * Stats.COUNT
  has_deleted = False
  for player_id in player_stats:
    if(player_id in hidden_players_ids):
      has_deleted = True
      for i in range(Stats.COUNT):
        deleted_player_stats[i] += player_stats[player_id][i]
    else:
      player_stats_in_names[id_to_players[player_id]] = player_stats[player_id]

  invalid_moves_in_name = set()
  for invalid_move in invalid_moves:
    if(invalid_move in id_to_players):
      invalid_moves_in_name.add(id_to_players[invalid_move])
    else:
      invalid_moves_in_name.add(invalid_move)

  plays_in_name = []
  for play in reversed(plays[-10:]):
    if(play in id_to_players):
      plays_in_name.append(id_to_players[play])
    else:
      plays_in_name.append(play)

  active_players_in_team = []
  for player_id in team_id_to_player_ids[team_id]:
    if(player_id not in hidden_players_ids):
      active_players_in_team.append((player_id, id_to_players[player_id]))

  return render_template("record.html", team_name = id_to_teams[team_id], players_in_team = sorted(active_players_in_team, key = lambda x : x[1]), plays = plays_in_name \
    , actions = list(Actions.__members__.keys())[:-1], invalid_moves = invalid_moves_in_name, stats_header = list(Stats.__members__.keys())[:-1], player_stats = player_stats_in_names, deleted_player_stats = deleted_player_stats \
    , has_deleted = has_deleted, hide_stats = "" if (player_stats_in_names or has_deleted) else "hidden", disable_undo = len(plays_in_name) == 0)


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
        refresh_globals()
        return redirect(url_for("edit_team", team_name = new_team))

  return render_template("list_teams.html", teams_to_id = teams_to_id, error = err)


@APP.route('/edit_team/<team_name>', methods = ["POST", "GET"])
def edit_team(team_name):
  global id_to_teams
  global teams_to_id
  global id_to_players
  global team_id_to_player_ids
  global base_players_to_id
  global hidden_players_ids

  team_id = teams_to_id[team_name]
  err = ""
  if(request.method == "POST"):
    action_type = request.form.get("button")
    if(action_type == "Create New Player"):
      new_player = request.form.get("player_name")
      if(new_player in base_players_to_id):
        err = "Player {} is already registered. ID: {}".format(new_player, base_players_to_id[new_player])
      else:
        db_connector.create_player(player_name = new_player, team_id = team_id);
        refresh_globals()
    elif(action_type == "Add Existing Player"):
      new_player = request.form.get("player_name")
      if(team_id in team_id_to_player_base_ids and base_players_to_id[new_player] in team_id_to_player_base_ids[team_id]):
        db_connector.create_player(player_name = new_player, team_id = team_id, base_id = base_players_to_id[new_player], unhidden = True);
      else:
        db_connector.create_player(player_name = new_player, team_id = team_id, base_id = base_players_to_id[new_player]);
      refresh_globals()
    elif(action_type == "Remove Player From Team"):
      player_id = request.form.get("player_id")
      db_connector.remove_player(player_id)
      refresh_globals()
    elif(action_type == "Transfer Player"):
      player_id = request.form.get("player_id")
      new_player = id_to_players[player_id]
      new_team_id = teams_to_id[request.form.get("new_team")]
      db_connector.remove_player(player_id)
      if(new_team_id in team_id_to_player_base_ids and base_players_to_id[new_player] in team_id_to_player_base_ids[new_team_id]):
        db_connector.create_player(player_name = new_player, team_id = new_team_id, base_id = base_players_to_id[new_player], unhidden = True);
      else:
        db_connector.create_player(player_name = new_player, team_id = new_team_id, base_id = base_players_to_id[new_player]);
      refresh_globals()
    elif(action_type == "View Stats"):
      pass
      # return redirect(url_for("view_player_stat", player_name = request.form.get("player_name")))
    elif(action_type == "Rename Team"):
      new_team_name = request.form.get("new_name")
      if(new_team_name in teams_to_id):
        err = "Team {} is already registered. ID: {}".format(new_team_name, teams_to_id[new_team_name])
      else:
        db_connector.update_team(team_id = team_id, team_name = new_team_name)
        refresh_globals()
        return redirect(url_for("edit_team", team_name = new_team_name))

  team_players_info = []
  team_players_name = set()
  if(team_id in team_id_to_player_ids):
    for player_id in team_id_to_player_ids[team_id]:
      if(player_id not in hidden_players_ids):
        team_players_name.add(id_to_players[player_id])

        transferable_teams = []
        for transferable_team_id, transferable_team_name in id_to_teams.items():
          if(transferable_team_name != team_name and (transferable_team_id not in team_id_to_player_base_ids or player_id not in team_id_to_player_base_ids[transferable_team_id])):
            transferable_teams.append(transferable_team_name)

        team_players_info.append((player_id, id_to_players[player_id], transferable_teams))

  base_players = []
  for base_player_name in sorted(base_players_to_id.keys()):
    if(base_player_name not in team_players_name):
      base_players.append(base_player_name)



  return render_template("edit_team.html", base_players = base_players, curr_team_name = team_name, error = err, team_players_info = sorted(team_players_info, key=lambda x: x[1]))

@APP.route('/list_games', methods = ["POST", "GET"])
def list_games():
  err = ""
  if(request.method == "POST"):
    action_type = request.form.get("button")
    if(action_type == "Create Game"):
      home_team_id = teams_to_id[request.form.get("home_team")]
      away_team_id = teams_to_id[request.form.get("away_team")]
      game_time = request.form.get("game_time")
      note = request.form.get("note")
      if(home_team_id == away_team_id):
        err = "Home and away team cannot be the same"
      else:
        db_connector.create_game(home_team_id = home_team_id, away_team_id = away_team_id, game_time = game_time, note = note)
    elif(action_type == "Start Record"):
      return redirect(url_for("record", team_id = request.form.get("team_id"), game_id = request.form.get("game_id")))
    
  return render_template("list_games.html", team_names = teams_to_id.keys(), games = db_connector.get_games(), id_to_teams = id_to_teams, error = err)


@APP.route('/list_players', methods = ["POST", "GET"])
def list_players():
  global id_to_teams
  global teams_to_id
  global id_to_players
  global team_id_to_player_ids
  global base_players_to_id
  
  err = ""
  if(request.method == "POST"):
    action_type = request.form.get("button")
    if(action_type == "Create New Player"):
      new_player = request.form.get("player_name")
      if(new_player in base_players_to_id):
        err = "Player {} is already registered. ID: {}".format(new_player, base_players_to_id[new_player])
      else:
        db_connector.create_player(player_name = new_player);
        refresh_globals()
    elif(action_type == "Remove Player"):
      player_id = request.form.get("player_id")
      db_connector.remove_player(player_id, is_base = True)
      refresh_globals()
    elif(action_type == "Rename Player"):
      player_name = request.form.get("player_name")
      player_id = request.form.get("player_id")
      new_name = request.form.get("new_name")
      if(new_name in base_players_to_id):
        err = "Player {} is already registered. ID: {}".format(new_name, base_players_to_id[new_name])
      else:
        db_connector.update_player(base_players_to_id[player_name], new_name)
        refresh_globals()
    elif(action_type == "View Stats"):
      pass

  return render_template("list_players.html", base_players_to_id = base_players_to_id, error = err)

@APP.route('/execute_sql', methods = ["POST", "GET"])
def execute_sql():
  update_db_player_stats()
  err = ""
  result = None

  if(request.method == "POST"):
    query = request.form.get("query")
    try:
      result = db_connector.execute_sql(query)
    except mysql.connector.Error as error:
      err = str(error)

  header = []
  table = []
  if(result):
    header = result[0].keys()

    for line in result:
      table.append([])
      for item in header:
        table[-1].append(line[item])

  return render_template("execute_sql.html", header = header, table = table, error = err)

@APP.route('/view_team_stat/<team_name>', methods = ["POST", "GET"])
def view_team_stat(team_name):
  return "TODO"

@APP.route('/view_player_stat/<player_name>', methods = ["POST", "GET"])
def view_player_stat(player_name):
  return "TODO"

@APP.route('/view_game_stat/<game_id>', methods = ["POST", "GET"])
def view_game_stat(game_id):
  return "TODO"
