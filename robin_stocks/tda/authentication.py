import pickle
from datetime import datetime, timedelta
from pathlib import Path

from robin_stocks.tda.globals import DATA_DIR_NAME, PICKLE_NAME
from robin_stocks.tda.helper import (request_data, set_login_state,
                                     update_session)
from robin_stocks.tda.urls import URLS


def login_first_time(client_id, authorization_token, refresh_token):
    # Create necessary folders and paths for pickle file as defined in globals.
    data_dir = Path.home().joinpath(DATA_DIR_NAME)
    if not data_dir.exists():
        data_dir.mkdir(parents=True)
    pickle_path = data_dir.joinpath(PICKLE_NAME)
    if not pickle_path.exists():
        Path.touch(pickle_path)
    # Write information to the file.
    with pickle_path.open("wb") as pickle_file:
        pickle.dump(
            {
                'authorization_token': authorization_token,
                'refresh_token': refresh_token,
                'client_id': client_id,
                'authorization_timestamp': datetime.now(),
                'refresh_timestamp': datetime.now()
            }, pickle_file)


def login():
    """ Set the authorization token so the API can be used.
    """
    # Check that file exists before trying to read from it.
    data_dir = Path.home().joinpath(DATA_DIR_NAME)
    pickle_path = data_dir.joinpath(PICKLE_NAME)
    if not pickle_path.exists():
        raise FileExistsError(
            "Please Call login_first_time() to create pickle file.")
    # Read the information from the pickle file.
    with pickle_path.open("rb") as pickle_file:
        pickle_data = pickle.load(pickle_file)
        access_token = pickle_data['authorization_token']
        refresh_token = pickle_data['refresh_token']
        client_id = pickle_data['client_id']
        authorization_timestamp = pickle_data['authorization_timestamp']
        refresh_timestamp = pickle_data['refresh_timestamp']
    # Authorization tokens expire after 30 mins. Refresh tokens expire after 90 days,
    # but you need to request a fresh authorization and refresh token before it expires.
    authorization_delta = timedelta(minutes=1800)
    refresh_delta = timedelta(days=60)
    url = URLS.oauth()
    # If it has been longer than 60 days. Get a new refresh and authorization token.
    # Else if it has been longer than 30 minutes, get only a new authorization token.
    if (datetime.now() - refresh_timestamp > refresh_delta):
        payload = {
            "grant_type": "refresh_token",
            "access_type": "offline",
            "refresh_token": refresh_token,
            "client_id": client_id
        }
        data, _ = request_data(url, payload, True)
        if "access_token" not in data and "refresh_token" not in data:
            raise ValueError(
                "Refresh token is no longer valid. Call login_first_time() to get a new refresh token.")
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
        with pickle_path.open("wb") as pickle_file:
            pickle.dump(
                {
                    'authorization_token': access_token,
                    'refresh_token': refresh_token,
                    'client_id': client_id,
                    'authorization_timestamp': datetime.now(),
                    'refresh_timestamp': datetime.now()
                }, pickle_file)
    elif (datetime.now() - authorization_timestamp > authorization_delta):
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id
        }
        data, _ = request_data(url, payload, True)
        if "access_token" not in data:
            raise ValueError(
                "Refresh token is no longer valid. Call login_first_time() to get a new refresh token.")
        access_token = data["access_token"]
        # Write new data to file. Do not replace the refresh timestamp.
        with pickle_path.open("wb") as pickle_file:
            pickle.dump(
                {
                    'authorization_token': access_token,
                    'refresh_token': refresh_token,
                    'client_id': client_id,
                    'authorization_timestamp': datetime.now(),
                    'refresh_timestamp': refresh_timestamp
                }, pickle_file)
    # Store authorization token in session information to be used with API calls.
    auth_token = "Bearer {0}".format(access_token)
    update_session("Authorization", auth_token)
    update_session("apikey", client_id)
    set_login_state(True)
