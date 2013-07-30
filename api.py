import exc
import json
import requests

from ducksboard_publisher import PROJECT_ROOT
from os import path
from respire.client import Client

APIS = {"dashboard": path.join(PROJECT_ROOT,
                               "ducksboard_specs/dashboard_api.json"),
        "push": path.join(PROJECT_ROOT,
                          "ducksboard_specs/push_api.json")}


def get_api_cli(api_key, api_name):
    try:
        spec_path = APIS[api_name.lower()]
    except KeyError:
        raise exc.ApiDoesNotExist

    session = requests.Session()
    session.auth = (api_key, "unused")

    with open(spec_path, "r") as spec_file:
        read_json_data = json.loads(spec_file.read())
    return Client(read_json_data, session)
