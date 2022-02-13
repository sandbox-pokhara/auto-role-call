'''Main module'''
import os
import time

import requests
from dotenv import load_dotenv
from league_connection import LeagueConnection
from league_connection.exceptions import LeagueConnectionError

from logger import logger


def get_gameflow_phase(connection):
    res = connection.get('/lol-gameflow/v1/session')
    if res.ok:
        res = res.json()
        return res['phase']
    return None


def wait_for_champ_select(connection):
    logger.info('Waiting for champ select...')
    while True:
        phase = get_gameflow_phase(connection)
        if phase == 'ChampSelect':
            return
        if phase == 'Lobby':
            time.sleep(5)
            continue
        if phase == 'Matchmaking':
            time.sleep(2)
            continue
        if phase == 'ReadyCheck':
            time.sleep(0.5)
            continue
        if phase == 'InProgress':
            time.sleep(30)
            continue
        time.sleep(5)


def wait_for_champ_select_end(connection):
    logger.info('Waiting for champ select end...')
    while True:
        phase = get_gameflow_phase(connection)
        if phase != 'ChampSelect':
            return
        time.sleep(5)


def send_message(connection, repeat=3):
    while True:
        res = connection.get('/lol-chat/v1/conversations')
        if not res.ok:
            logger.error('Bad status code when parsing /lol-chat/v1/conversations')
            return None
        champ_select_con = [c for c in res.json() if c['type'] == 'championSelect']
        if champ_select_con == []:
            logger.info('Champ select converstation not loaded yet. Trying again...')
            time.sleep(0.1)
            continue
        logger.info('Found champ select conversation.')
        con_id = champ_select_con[0]['id']
        data = {'body': os.environ['MESSAGE']}
        success = False
        for _ in range(repeat):
            res = connection.post(f'/lol-chat/v1/conversations/{con_id}/messages', json=data)
            if res.ok:
                success = True
            if not res.ok:
                logger.error('Error sending message.')
            time.sleep(0.5)
        return con_id if success else None


def main():
    '''Main function'''
    load_dotenv('default.env')
    if 'LEAGUE_CLIENT' not in os.environ:
        logger.error('LEAGUE_CLIENT path is not set.')
        return
    if 'MESSAGE' not in os.environ:
        logger.error('MESSAGE path is not set.')
        return
    if 'REPEAT' not in os.environ:
        logger.error('REPEAT value is not set.')
        return
    try:
        repeat = int(os.environ['REPEAT'])
    except ValueError:
        logger.error('Invalid REPEAT value. It must be an integer.')
        return
    league_client_path = os.environ['LEAGUE_CLIENT']
    dir_name = os.path.dirname(league_client_path)
    lockfile = os.path.join(dir_name, 'lockfile')
    while True:
        try:
            logger.info('Getting league connection...')
            connection = LeagueConnection(lockfile, timeout=24 * 3600)  # 1 day timeout
            logger.info('Successfully connected to league client.')
            wait_for_champ_select(connection)
            if send_message(connection, repeat=repeat) is not None:
                logger.info('Sucessfully sent message.')
                wait_for_champ_select_end(connection)
        except (LeagueConnectionError, requests.RequestException) as exp:
            logger.error(exp.__class__.__name__)
            time.sleep(10)


if __name__ == '__main__':
    main()
