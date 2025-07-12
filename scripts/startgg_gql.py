import os
import time
from zoneinfo import ZoneInfo

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

STARTGG_API_KEY = os.environ.get("STARTGG_API_KEY")

GET_TOURNAMENT_NAME_AND_TIMEZONE_QUERY = gql("""
query getTournamentName($slug: String) {
  tournament(slug: $slug) {
    name
    timezone
  }
}
""")

GET_EVENT_ID_QUERY = gql("""
query getEventId($slug: String) {
  event(slug: $slug) {
    id
  }
}
""")

GET_EVENT_SETS_QUERY = gql("""
query EventSets($eventId: ID!, $page: Int!, $perPage: Int!) {
  event(id: $eventId) {
    sets(page: $page, perPage: $perPage, sortType: STANDARD) {
      nodes {
        id
      }
    }
  }
}
""")

# Need `slots` in case the set doesn't have game-specific data
# Avoiding "completedAt" since that can reflect changes after the fact
GET_SET_DATA_QUERY = gql("""
query SetEntrants($setId: ID!) {
  set(id: $setId) {
    id
    startAt
    startedAt
    createdAt
    fullRoundText
    vodUrl
    slots {
      id
      entrant {
        id
        name
        participants {
          id
          gamerTag
          connectedAccounts
        }
      }
    }
    games {
      selections {
        character {
          id
          name
        }
        entrant {
          id
          name
          participants {
            id
            gamerTag
            connectedAccounts
          }
        }
      }
    }
  }
}
""")

SET_VOD_MUTATION = gql("""
mutation ($setId: ID!, $vodUrl: String) {
  updateVodUrl(setId: $setId, vodUrl: $vodUrl) {
    id
  }
}
""")


def sleep(f):
    def _sleep(*args, **kwargs):
        result = f(*args, **kwargs)
        time.sleep(60/80) # Sleep to avoid exceeding 80 req / minute
        return result
    return _sleep

@sleep
def get_tournament_name_and_timezone(client, slug):
    params = {"slug": slug}
    result = client.execute(GET_TOURNAMENT_NAME_AND_TIMEZONE_QUERY, variable_values=params)
    return result["tournament"]["name"], ZoneInfo(result["tournament"]["timezone"])

@sleep
def get_event_id(client, slug):
    params = {"slug": slug}
    result = client.execute(GET_EVENT_ID_QUERY, variable_values=params)
    return result["event"]["id"]

@sleep
def get_event_set_ids(client, event_id):
    params = {
        "eventId": event_id,
        "page": 1,
        "perPage": 500,
    }
    result = client.execute(GET_EVENT_SETS_QUERY, variable_values=params)
    return [set_["id"] for set_ in  result["event"]["sets"]["nodes"]]

@sleep
def get_set_data(client, set_id):
    params = {"setId": set_id}
    result = client.execute(GET_SET_DATA_QUERY, variable_values=params)
    return result["set"]

@sleep
def set_vod(client, set_id, vod_url):
    params = {"setId": set_id, "vodUrl": vod_url}
    client.execute(SET_VOD_MUTATION, variable_values=params)

def get_client(api_key=None):
    api_key = api_key or STARTGG_API_KEY
    transport = RequestsHTTPTransport(
        url="https://api.start.gg/gql/alpha",
        headers={
            "Authorization": f"Bearer {api_key}",
        },
    )
    return Client(transport=transport)
