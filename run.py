from ultimate_stats_tracker import APP, db_connector, frontend, api, logger
import logging

if __name__ == "__main__":

  logger.setLevel(logging.DEBUG)

  logger.debug("get_players: " + str(db_connector.get_players()))
  logger.debug("get_teams: " + str(db_connector.get_teams()))
  logger.debug("get_plays: " + str(db_connector.get_plays()))
  logger.debug("get_games: " + str(db_connector.get_games()))

  api.refresh_globals()
  api.update_db_player_stats()

  APP.run('0.0.0.0', 5000, debug=False)