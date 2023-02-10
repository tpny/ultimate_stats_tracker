import mysql.connector

class MySQLConnector:
  def __init__(self, stats_list, user='root', host='localhost', password='', database='ultimate_stats'):
    # For public server
    self.user = user
    self.password = password
    self.host = host
    self.database = database
    self.cnx = mysql.connector.connect(user = self.user, password = self.password, host = self.host, database = self.database)

    self.stats_list = stats_list
    self.create_tables()

  def create_tables(self):
    cursor = self.cnx.cursor()
    query = "CREATE TABLE IF NOT EXISTS TEAMS ( id int NOT NULL AUTO_INCREMENT, team_name varchar(20) NOT NULL, PRIMARY KEY (id));"
    cursor.execute(query)
    self.cnx.commit()
    
    query = "CREATE TABLE IF NOT EXISTS PLAYERS ( id int NOT NULL AUTO_INCREMENT, player_name varchar(20) NOT NULL, team int, base_id int, hidden BOOLEAN NOT NULL DEFAULT FALSE, PRIMARY KEY (id), FOREIGN KEY (team) REFERENCES TEAMS(id), FOREIGN KEY (base_id) REFERENCES PLAYERS(id));"
    cursor.execute(query)
    self.cnx.commit()

    query = "CREATE TABLE IF NOT EXISTS GAMES ( id int NOT NULL AUTO_INCREMENT, home_team int NOT NULL, away_team int NOT NULL, notes varchar(50), game_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (id), FOREIGN KEY (home_team) REFERENCES TEAMS(id), FOREIGN KEY (away_team) REFERENCES TEAMS(id));"
    cursor.execute(query)
    self.cnx.commit()

    query = "CREATE TABLE IF NOT EXISTS PLAYS (team int NOT NULL, game int NOT NULL, play MEDIUMTEXT, processed BOOLEAN NOT NULL, PRIMARY KEY (team, game), FOREIGN KEY (team) REFERENCES TEAMS(id), FOREIGN KEY (game) REFERENCES GAMES(id));"
    cursor.execute(query)
    self.cnx.commit()

    stats_str = ",".join(map(lambda stats: " stats_{} int NOT NULL".format(stats), self.stats_list))
    query = "CREATE TABLE IF NOT EXISTS PLAYER_STATS (player int NOT NULL, game int NOT NULL, team int NOT NULL, {}, PRIMARY KEY (player, game), FOREIGN KEY (player) REFERENCES PLAYERS(id), FOREIGN KEY (team) REFERENCES TEAMS(id), FOREIGN KEY (game) REFERENCES GAMES(id));".format(stats_str)
    self.cnx.commit()

    cursor.close()

  def insert_or_update_play(self, team_id, game_id, plays_str, processed = False):
    cursor = self.cnx.cursor()
    query = "REPLACE INTO PLAYS (team, game, play, processed) VALUES(%s, %s, '%s', %s);"
    cursor.execute(query, (team_id, game_id, plays_str, processed))
    self.cnx.commit()
    cursor.close()

  def create_game(self, home_team_id, away_team_id, game_time = None):
    cursor = self.cnx.cursor()
    if(game_time):
      query = "REPLACE INTO GAMES (home_team, away_team, game_time) VALUES(%s, %s, '%s');"
      cursor.execute(query, (home_team_id, away_team_id, game_time))
    else:
      query = "REPLACE INTO GAMES (home_team, away_team) VALUES(%s, %s);"
      cursor.execute(query, (home_team_id, away_team_id))
    self.cnx.commit()
    cursor.close()

  def update_game(self, game_id, home_team_id, away_team_id, game_time = None):
    cursor = self.cnx.cursor()
    if(datetime):
      query = "REPLACE INTO GAMES (home_team, away_team, game_time) VALUES(%s, %s, %s);"
      cursor.execute(query, (home_team_id, away_team_id, game_time))
    else:
      query = "REPLACE INTO GAMES (home_team, away_team) VALUES(%s, %s);"
      cursor.execute(query, (home_team_id, away_team_id))
    self.cnx.commit()
    cursor.close()

  # def remove_game(self, game_id)
  #   cursor = self.cnx.cursor()
  #   query = "DELETE FROM GAMES WHERE id = %s;".format(game_id)
  #   cursor.execute(query)
  #   self.cnx.commit()
  #   cursor.close()

  def create_team(self, team_name):
    cursor = self.cnx.cursor()
    query = "INSERT INTO TEAMS (team_name) VALUES(%s);"
    cursor.execute(query, (team_name, ))
    self.cnx.commit()
    cursor.close()

  def update_team(self, team_id, team_name):
    cursor = self.cnx.cursor()
    query = "UPDATE TEAMS SET team_name = %s WHERE id = %s;"
    print((team_name, team_id))
    cursor.execute(query, (team_name, team_id))
    self.cnx.commit()
    cursor.close()

  # def remove_team(self, team_id)
  #   cursor = self.cnx.cursor()
  #   query = "DELETE FROM TEAMS WHERE id = %s;".format(team_id)
  #   cursor.execute(query)
  #   self.cnx.commit()
  #   cursor.close()

  def create_player(self, player_name, team_id, base_id = "NULL"):
    cursor = self.cnx.cursor()
    query = "INSERT INTO PLAYERS (player_name, team, base_id) VALUES(%s, %s, %s);"
    print(query)
    cursor.execute(query, (player_name, team_id, base_id))
    self.cnx.commit()
    cursor.close()

  def update_player(self, player_id, player_name = None, team_id = None):
    cursor = self.cnx.cursor()
    if(player_name):
      query = "UPDATE PLAYERS SET player_name = %s WHERE id = %s OR base_id = %s;"
      cursor.execute(query, (player_name, player_id, player_id))
    if(team_id):
      query = "UPDATE PLAYERS SET team = %s WHERE id = %s;"
      cursor.execute(query, (team_id, player_id))
    self.cnx.commit()
    cursor.close()

  def remove_player(self, player_id, is_base = False):
    cursor = self.cnx.cursor()
    if(is_base): # hide base player and all its stats
      query = "UPDATE PLAYERS SET hidden = TRUE WHERE base_id = %s or id = %s;"
      cursor.execute(query, (player_id, player_id))
    else: # remove a player from a team
      query = "UPDATE PLAYERS SET team = %s WHERE id = %s;"
      cursor.execute(query, ("NULL", player_id))

    self.cnx.commit()
    cursor.close()

  def get_players(self, team_id = None, get_hidden = False):
    cursor = self.cnx.cursor()
    if(team_id):
      query = "SELECT * FROM PLAYERS WHERE team = %s AND hidden = %s;"
      cursor.execute(query, (team_id, not get_hidden))
    else:
      query = "SELECT * FROM PLAYERS;"
      cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return data

  def get_teams(self):
    cursor = self.cnx.cursor()
    query = "SELECT * FROM TEAMS;"
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return data

  def get_plays(self, team_id = None, game_id = None, unprocessed = False):
    cursor = self.cnx.cursor()

    if(team_id or game_id or unprocessed):
      criti = []
      if(team_id):
        criti.append("team = %s".format(team_id))
      if(game_id):
        criti.append("game = %s".format(game_id))
      if(unprocessed):
        criti.append("processed = FALSE")
      query = "SELECT * FROM PLAYS WHERE %s;"
      cursor.execute(query, " AND ".join(criti))
    else:
      query = "SELECT * FROM PLAYS;"
      cursor.execute(query)
    data = None
    if(team_id and game_id):
      data = cursor.fetchone()
    else:
      data = cursor.fetchall()
    cursor.close()
    return data

  def get_games(self):
    cursor = self.cnx.cursor()
    query = "SELECT * FROM GAMES;"
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return data

  def get_player_stats(self, game_id = None, player_id = None, team_id = None):
    cursor = self.cnx.cursor()
    if(game_id or player_id or team_id):
      criti = []
      if(game_id):
        criti.append("game = %s".format(game_id))
      if(player_id):
        criti.append("player = %s".format(player_id))
      if(team_id):
        criti.append("team = %s".format(team_id))
      query = "SELECT * FROM PLAYER_STATS WHERE %s;"
      cursor.execute(query, " AND ".join(criti))
    else:
      query = "SELECT * FROM PLAYER_STATS;"
      cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return data

  def insert_or_update_player_stats(self, player_stats, players_to_id, team, game):
    cursor = self.cnx.cursor()
    stats_str = ",".join(map(lambda stats: " stats_%s".format(stats), self.stats_list))
    for player in player_stats:
      player_stats_str = ",".join(map(str, player_stats[player]))
      query = "REPLACE INTO PLAYER_STATS (player, game, team, %s) VALUES(%s, %s, %s, %s);"
      cursor.execute(query, (stats_str, players_to_id[player], game, team, player_stats_str))
    self.cnx.commit()
    cursor.close()


  def execute_sql(self, query):
    cursor = self.cnx.cursor()
    cursor.execute(query)
    self.cnx.commit()
    data = cursor.fetchall()
    cursor.close()
    return data