import mysql.connector
from ultimate_stats_tracker import logger

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

  def reset_connection(self):
    self.cnx.close()
    self.cnx = mysql.connector.connect(user = self.user, password = self.password, host = self.host, database = self.database)

  def create_tables(self):
    cursor = self.cnx.cursor()
    query = "CREATE TABLE IF NOT EXISTS TEAMS ( id int NOT NULL AUTO_INCREMENT, team_name TEXT NOT NULL, hidden BOOLEAN NOT NULL DEFAULT FALSE, PRIMARY KEY (id));"
    cursor.execute(query)
    logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()
    
    query = "CREATE TABLE IF NOT EXISTS PLAYERS ( id int NOT NULL AUTO_INCREMENT, player_name TEXT NOT NULL, team int, base_id int, hidden BOOLEAN NOT NULL DEFAULT FALSE, PRIMARY KEY (id), FOREIGN KEY (team) REFERENCES TEAMS(id), FOREIGN KEY (base_id) REFERENCES PLAYERS(id));"
    cursor.execute(query)
    logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()

    query = "CREATE TABLE IF NOT EXISTS GAMES ( id int NOT NULL AUTO_INCREMENT, home_team int NOT NULL, away_team int NOT NULL, note TEXT, game_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, hidden BOOLEAN NOT NULL DEFAULT FALSE, PRIMARY KEY (id), FOREIGN KEY (home_team) REFERENCES TEAMS(id), FOREIGN KEY (away_team) REFERENCES TEAMS(id));"
    cursor.execute(query)
    logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()

    query = "CREATE TABLE IF NOT EXISTS PLAYS (team int NOT NULL, game int NOT NULL, play MEDIUMTEXT, processed BOOLEAN NOT NULL DEFAULT FALSE, hidden BOOLEAN NOT NULL DEFAULT FALSE, PRIMARY KEY (team, game), FOREIGN KEY (team) REFERENCES TEAMS(id), FOREIGN KEY (game) REFERENCES GAMES(id));"
    cursor.execute(query)
    logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()

    stats_str = ",".join(map(lambda stats: " stats_{} int NOT NULL".format(stats), self.stats_list))
    query = "CREATE TABLE IF NOT EXISTS PLAYER_STATS (player int NOT NULL, game int NOT NULL, team int NOT NULL, {}, PRIMARY KEY (player, game, team), FOREIGN KEY (player) REFERENCES PLAYERS(id), FOREIGN KEY (team) REFERENCES TEAMS(id), FOREIGN KEY (game) REFERENCES GAMES(id));".format(stats_str)
    cursor.execute(query)
    logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()
    cursor.close()

    # drop table PLAYER_STATS;
    # drop table PLAYERS;
    # drop table PLAYS;
    # drop table GAMES;
    # drop table TEAMS;
    # show tables;

  def insert_or_update_play(self, team_id, game_id, plays_str = None, processed = False):
    cursor = self.cnx.cursor()
    if(processed and not plays_str):
      query = "UPDATE PLAYS SET processed = TRUE WHERE team = %s and game = %s;"
      cursor.execute(query, (team_id, game_id))
      logger.debug("EXEC: " + cursor.statement)
    else:
      query = "REPLACE INTO PLAYS (team, game, play, processed) VALUES(%s, %s, %s, %s);"
      cursor.execute(query, (team_id, game_id, plays_str, processed))
      logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()
    cursor.close()

  def create_game(self, home_team_id, away_team_id, game_time = None, note = ""):
    cursor = self.cnx.cursor()
    if(game_time):
      query = "INSERT INTO GAMES (home_team, away_team, game_time, note) VALUES(%s, %s, %s, %s);"
      cursor.execute(query, (home_team_id, away_team_id, game_time, note))
      logger.debug("EXEC: " + cursor.statement)
    else:
      query = "INSERT INTO GAMES (home_team, away_team, note) VALUES(%s, %s, %s);"
      cursor.execute(query, (home_team_id, away_team_id, note))
      logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()
    cursor.close()

  def update_game(self, game_id, game_time, note):
    cursor = self.cnx.cursor()
    query = "UPDATE GAMES SET game_time = %s WHERE id = %s;"
    cursor.execute(query, (game_time, game_id))
    logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()
    cursor.close()

  def remove_game(self, game_id):
    cursor = self.cnx.cursor()
    query = "UPDATE PLAYS SET hidden = TRUE WHERE game = %s;"
    cursor.execute(query, (game_id, ))
    logger.debug("EXEC: " + cursor.statement)
    query = "UPDATE GAMES SET hidden = TRUE WHERE id = %s;"
    cursor.execute(query, (game_id, ))
    logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()
    cursor.close()

  def create_team(self, team_name):
    cursor = self.cnx.cursor()
    query = "INSERT INTO TEAMS (team_name) VALUES(%s);"
    cursor.execute(query, (team_name, ))
    logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()
    cursor.close()

  def update_team(self, team_id, team_name):
    cursor = self.cnx.cursor()
    query = "UPDATE TEAMS SET team_name = %s WHERE id = %s;"
    cursor.execute(query, (team_name, team_id))
    logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()
    cursor.close()

  def remove_team(self, team_id):
    cursor = self.cnx.cursor()
    query = "UPDATE TEAMS SET hidden = TRUE WHERE id = %s;"
    cursor.execute(query, (team_id, ))
    logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()
    cursor.close()

  def create_player(self, player_name, team_id = None, base_id = None, unhidden = False):
    cursor = self.cnx.cursor()
    if(not base_id): # create base player
      query = "INSERT INTO PLAYERS (player_name) VALUES(%s);"
      cursor.execute(query, (player_name, ))
      logger.debug("EXEC: " + cursor.statement)
      if(team_id):
        query = "INSERT INTO PLAYERS (player_name ,team, base_id) VALUES(%s, %s, LAST_INSERT_ID());"
        cursor.execute(query, (player_name, team_id))
        logger.debug("EXEC: " + cursor.statement)
      self.cnx.commit()
    elif(unhidden):
      query = "UPDATE PLAYERS SET hidden = FALSE WHERE base_id = %s and team = %s;"
      cursor.execute(query, (base_id, team_id))
      logger.debug("EXEC: " + cursor.statement)
      self.cnx.commit()
    else:
      query = "INSERT INTO PLAYERS (player_name,team, base_id) VALUES(%s, %s, %s);"
      cursor.execute(query, (player_name, team_id, base_id))
      logger.debug("EXEC: " + cursor.statement)
      self.cnx.commit()
    cursor.close()

  def update_player(self, player_id, player_name = None, team_id = None):
    cursor = self.cnx.cursor()
    if(player_name):
      query = "UPDATE PLAYERS SET player_name = %s WHERE id = %s OR base_id = %s;"
      cursor.execute(query, (player_name, player_id, player_id))
      logger.debug("EXEC: " + cursor.statement)
    if(team_id):
      query = "UPDATE PLAYERS SET team = %s WHERE id = %s;"
      cursor.execute(query, (team_id, player_id))
      logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()
    cursor.close()

  def remove_player(self, player_id, is_base = False):
    cursor = self.cnx.cursor()
    if(is_base): # hide base player and all its stats
      query = "UPDATE PLAYERS SET hidden = TRUE WHERE base_id = %s or id = %s;"
      cursor.execute(query, (player_id, player_id))
      logger.debug("EXEC: " + cursor.statement)
      self.cnx.commit()
    else: # remove a player from a team
      query = "UPDATE PLAYERS SET hidden = TRUE WHERE id = %s;"
      cursor.execute(query, (player_id, ))
      logger.debug("EXEC: " + cursor.statement)
      self.cnx.commit()
    cursor.close()
    self.update_player(player_id, player_name = "DELETED PLAYER")


  def get_players(self, team_id = None):
    cursor = self.cnx.cursor()
    if(team_id):
      query = "SELECT * FROM PLAYERS WHERE team = %s;"
      cursor.execute(query, (team_id, ))
      logger.debug("EXEC: " + cursor.statement)
    else:
      query = "SELECT * FROM PLAYERS;"
      cursor.execute(query)
      logger.debug("EXEC: " + cursor.statement)
    data = cursor.fetchall()
    cursor.close()
    return data

  def get_teams(self):
    cursor = self.cnx.cursor()
    query = "SELECT * FROM TEAMS;"
    cursor.execute(query)
    logger.debug("EXEC: " + cursor.statement)
    data = cursor.fetchall()
    cursor.close()
    return data

  def get_plays(self, team_id = None, game_id = None, unprocessed = False):
    cursor = self.cnx.cursor()

    if(team_id or game_id or unprocessed):
      query_str = []
      query_data = []
      if(team_id):
        query_str.append("team = %s")
        query_data.append(team_id)
      if(game_id):
        query_str.append("game = %s")
        query_data.append(game_id)
      if(unprocessed):
        query_str.append("processed = %s")
        query_data.append("FALSE")
      query = "SELECT * FROM PLAYS WHERE {};".format(" AND ".join(query_str))
      cursor.execute(query, query_data)
      logger.debug("EXEC: " + cursor.statement)
    else:
      query = "SELECT * FROM PLAYS;"
      cursor.execute(query)
      logger.debug("EXEC: " + cursor.statement)
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
    logger.debug("EXEC: " + cursor.statement)
    data = cursor.fetchall()
    cursor.close()
    return data

  def get_player_stats(self, game_id = None, player_id = None, team_id = None):
    cursor = self.cnx.cursor()
    if(game_id or player_id or team_id):
      query_str = []
      query_data = []
      if(game_id):
        query_str.append("game = %s")
        query_data.append(game_id)
      if(player_id):
        query_str.append("player = %s")
        query_data.append(player_id)
      if(team_id):
        query_str.append("team = %s")
        query_data.append(team_id)
      query = "SELECT * FROM PLAYER_STATS WHERE {};".format(" AND ".join(query_str))
      cursor.execute(query, query_data)
      logger.debug("EXEC: " + cursor.statement)
    else:
      query = "SELECT * FROM PLAYER_STATS;"
      cursor.execute(query)
      logger.debug("EXEC: " + cursor.statement)
    data = cursor.fetchall()
    cursor.close()
    return data

  def insert_or_update_player_stats(self, player_stats, team_id, game_id):
    cursor = self.cnx.cursor()
    stats_str = ", ".join(map(lambda stats: "stats_{}".format(stats), self.stats_list))
    value_str = ", ".join(map(lambda stats: "%s".format(stats), self.stats_list))

    for player_id in player_stats:
      query = "REPLACE INTO PLAYER_STATS (player, game, team, {}) VALUES(%s, %s, %s, {});".format(stats_str, value_str)
      cursor.execute(query, (player_id, game_id, team_id, *player_stats[player_id]))
      logger.debug("EXEC: " + cursor.statement)
    self.cnx.commit()
    cursor.close()


  def execute_sql(self, query):
    cursor = self.cnx.cursor(dictionary = True)
    querys = query.split(";")
    for query in querys:
      if(query):
        cursor.execute(query + ";")
        logger.debug("EXEC: " + cursor.statement)
        data = cursor.fetchall()
    self.cnx.commit()
    cursor.close()
    return data
