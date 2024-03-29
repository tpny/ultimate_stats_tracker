from flask import Flask
from flask import render_template, request, redirect, url_for
import mysql

from ultimate_stats_tracker import APP, api, db_connector, Stats, Actions, logger

@APP.route('/')
@APP.route('/index')
def index():
  db_connector.create_tables()
  api.refresh_globals()

  teams = db_connector.get_teams()
  team_dict = {}
  for team in teams:
    team_dict[team[0]] = team[1]

  return render_template("index.html")

@APP.route('/record/<team_name>_<game_id>', methods = ["POST", "GET"])
def record(team_name, game_id):

  team_id = str(api.teams_to_id[team_name])
  game_id = str(game_id)

  play = db_connector.get_plays(team_id = team_id, game_id = game_id)
  play_str = ""
  plays = []
  player_stats = {}
  invalid_moves = set()
  if(play): #not empty
    play_str = play[2]
    plays = play[2].split(",")
    player_stats, invalid_moves = api.compute_play_stats(plays, api.team_id_to_player_ids[team_id])
  else:
    invalid_moves.add("GOAL")
    invalid_moves.add("DEFENSE")
    invalid_moves.add("DROP")
    invalid_moves.add("THROW_AWAY")

  active_players_in_team = []
  if(team_id in api.team_id_to_player_ids):
    for player_id in api.team_id_to_player_ids[team_id]:
      if(player_id not in api.hidden_players_ids):
        active_players_in_team.append((player_id, api.id_to_players[player_id], api.id_to_player_gender[player_id]))

  player_stats_in_names = {}
  deleted_player_stats = [0] * Stats.COUNT
  has_deleted = False
  for player_id in player_stats:
    if(player_id in api.hidden_players_ids):
      has_deleted = True
      for i in range(Stats.COUNT):
        deleted_player_stats[i] += player_stats[player_id][i]
    else:
      player_stats_in_names[api.id_to_players[player_id]] = player_stats[player_id]

  invalid_moves_in_name = set()
  for invalid_move in invalid_moves:
    if(invalid_move in api.id_to_players):
      invalid_moves_in_name.add(api.id_to_players[invalid_move])
    else:
      invalid_moves_in_name.add(invalid_move)

  return render_template("record.html", team_name = team_name, players_in_team = sorted(active_players_in_team, key = lambda x : x[1]), \
    actions = list(Actions.__members__.keys())[:-1], invalid_moves = invalid_moves_in_name, stats_header = list(Stats.__members__.keys())[:-1], player_stats = player_stats_in_names, \
    deleted_player_stats = deleted_player_stats, has_deleted = has_deleted, hide_stats = "" if (player_stats_in_names or has_deleted) else "hidden", \
    disable_undo = len(play_str) == 0, game_id = game_id, team_id = team_id, id_to_players = api.id_to_players, play_str = play_str)


@APP.route('/list_teams', methods = ["POST", "GET"])
def list_teams():
  err = ""
  if(request.method == "POST"):
    action_type = request.form.get("button")
    if(action_type == "View Stats"):
      pass
    elif(action_type == "Edit Team"):
      return redirect(url_for("edit_team", team_name = request.form.get("team_name")))
    elif(action_type == "Create Team"):
      new_team = request.form.get("team_name")
      if(new_team in api.teams_to_id):
        err = "Team {} already exists".format(new_team)
      else:
        db_connector.create_team(new_team);
        api.refresh_globals()
        return redirect(url_for("edit_team", team_name = new_team))

  return render_template("list_teams.html", teams_to_id = api.teams_to_id, error = err)


@APP.route('/edit_team/<team_name>', methods = ["POST", "GET"])
def edit_team(team_name):
  logger.debug("edit_team(team_name)")

  team_id = api.teams_to_id[team_name]
  err = ""
  if(request.method == "POST"):
    action_type = request.form.get("button")
    logger.debug("Get button press " + action_type)
    if(action_type == "Create New Player"):
      new_player = request.form.get("player_name")
      player_gender = request.form.get("player_gender")
      logger.debug("Create New Player {} {}".format(new_player, player_gender))
      if(new_player in api.base_players_to_id):
        err = "Player {} is already registered. ID: {}".format(new_player, api.base_players_to_id[new_player])
      else:
        db_connector.create_player(player_name = new_player, team_id = team_id, player_gender = player_gender);
        api.refresh_globals()
    elif(action_type == "Add Existing Player"):
      new_player = request.form.get("player_name")
      if(new_player):
        base_id = api.base_players_to_id[new_player]
        logger.debug("Add Existing Player: {}".format(new_player))
        if(team_id in api.team_id_to_player_base_ids and api.base_players_to_id[new_player] in api.team_id_to_player_base_ids[team_id]):
          db_connector.create_player(player_name = new_player, team_id = team_id, base_id = base_id, unhidden = True);
        else:
          db_connector.create_player(player_name = new_player, team_id = team_id, player_gender = api.id_to_player_gender[base_id], base_id = base_id);
        api.refresh_globals()
    elif(action_type == "Remove Player From Team"):
      player_id = request.form.get("player_id")
      db_connector.remove_player(player_id)
      api.refresh_globals()
    elif(action_type == "Transfer Player"):
      player_id = request.form.get("player_id")
      new_player = api.id_to_players[player_id]
      new_team_id = api.teams_to_id[request.form.get("new_team")]
      db_connector.remove_player(player_id)
      if(new_team_id in api.team_id_to_player_base_ids and api.base_players_to_id[new_player] in api.team_id_to_player_base_ids[new_team_id]):
        db_connector.create_player(player_name = new_player, team_id = new_team_id, base_id = api.base_players_to_id[new_player], unhidden = True);
      else:
        db_connector.create_player(player_name = new_player, team_id = new_team_id, base_id = api.base_players_to_id[new_player]);
      api.refresh_globals()
    elif(action_type == "View Stats"):
      pass
    elif(action_type == "Rename Team"):
      new_team_name = request.form.get("new_name")
      if(new_team_name in api.teams_to_id):
        err = "Team {} is already registered. ID: {}".format(new_team_name, api.teams_to_id[new_team_name])
      else:
        db_connector.update_team(team_id = team_id, team_name = new_team_name)
        api.refresh_globals()
        return redirect(url_for("edit_team", team_name = new_team_name))

  team_players_info = []
  team_players_name = set()
  if(team_id in api.team_id_to_player_ids):
    for player_id in api.team_id_to_player_ids[team_id]:
      if(player_id not in api.hidden_players_ids):
        team_players_name.add(api.id_to_players[player_id])

        transferable_teams = []
        for transferable_team_id, transferable_team_name in api.id_to_teams.items():
          if(transferable_team_name != team_name and (transferable_team_id not in api.team_id_to_player_base_ids or player_id not in api.team_id_to_player_base_ids[transferable_team_id])):
            transferable_teams.append(transferable_team_name)

        team_players_info.append((player_id, api.id_to_players[player_id], transferable_teams))

  base_players = []
  for base_player_name in sorted(api.base_players_to_id.keys()):
    if(base_player_name not in team_players_name):
      base_players.append(base_player_name)



  return render_template("edit_team.html", base_players = base_players, curr_team_name = team_name, error = err, team_players_info = sorted(team_players_info, key=lambda x: x[1]))

@APP.route('/list_games', methods = ["POST", "GET"])
def list_games():
  err = ""
  if(request.method == "POST"):
    action_type = request.form.get("button")
    if(action_type == "Create Game"):
      home_team_id = api.teams_to_id[request.form.get("home_team")]
      away_team_id = api.teams_to_id[request.form.get("away_team")]
      game_time = request.form.get("game_time")
      note = request.form.get("note")
      if(home_team_id == away_team_id):
        err = "Home and away team cannot be the same"
      else:
        db_connector.create_game(home_team_id = home_team_id, away_team_id = away_team_id, game_time = game_time)
    elif(action_type == "Start Record"):
      return redirect(url_for("record", team_name = request.form.get("team_name"), game_id = request.form.get("game_id")))
    
  return render_template("list_games.html", team_names = api.teams_to_id.keys(), games = db_connector.get_games(), id_to_teams = api.id_to_teams, error = err)


@APP.route('/list_players', methods = ["POST", "GET"])
def list_players():
  
  err = ""
  if(request.method == "POST"):
    action_type = request.form.get("button")
    if(action_type == "Create New Player"):
      new_player = request.form.get("player_name")
      player_gender = request.form.get("player_gender")
      if(new_player in api.base_players_to_id):
        err = "Player {} is already registered. ID: {}".format(new_player, api.base_players_to_id[new_player])
      else:
        db_connector.create_player(player_name = new_player, player_gender = player_gender);
        api.refresh_globals()
    elif(action_type == "Remove Player"):
      player_id = request.form.get("player_id")
      db_connector.remove_player(player_id, is_base = True)
      api.refresh_globals()
    elif(action_type == "Rename Player"):
      player_name = request.form.get("player_name")
      player_id = request.form.get("player_id")
      new_name = request.form.get("new_name")
      if(new_name in api.base_players_to_id):
        err = "Player {} is already registered. ID: {}".format(new_name, api.base_players_to_id[new_name])
      else:
        db_connector.update_player(api.base_players_to_id[player_name], new_name)
        api.refresh_globals()
    elif(action_type == "View Stats"):
      pass

  return render_template("list_players.html", base_players_to_id = api.base_players_to_id, error = err)

@APP.route('/execute_sql', methods = ["POST", "GET"])
def execute_sql():

  api.update_db_player_stats()

  result = None
  err = ""
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

@APP.route('/view_team_stats/<team_id>', methods = ["POST", "GET"])
def view_team_stats(team_id):
  return str(db_connector.get_player_stats(game_id = None, player_id = None, team_id = team_id))

@APP.route('/view_player_stats/<player_name>', methods = ["POST", "GET"])
def view_player_stats(player_name):
  return str(db_connector.get_player_stats(game_id = None, player_id = api.base_players_to_id[player_name], team_id = None))

@APP.route('/view_game_stats/<game_id>', methods = ["POST", "GET"])
def view_game_stats(game_id):
  return str(db_connector.get_player_stats(game_id = game_id, player_id = None, team_id = None))
