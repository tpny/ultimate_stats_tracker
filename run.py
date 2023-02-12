from ultimate_stats_tracker import APP, db_connector, frontend, logger
import logging

if __name__ == "__main__":

  logger.setLevel(logging.INFO)

  logger.debug("get_players: " + str(db_connector.get_players()))
  logger.debug("get_teams: " + str(db_connector.get_teams()))
  logger.debug("get_plays: " + str(db_connector.get_plays()))
  logger.debug("get_games: " + str(db_connector.get_games()))

  frontend.refresh_globals()
  frontend.update_db_player_stats()

  APP.run('0.0.0.0', 5000, debug=False)