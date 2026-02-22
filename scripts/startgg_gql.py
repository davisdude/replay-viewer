import os
import time

from gql import Client, gql
from gql.graphql_request import GraphQLRequest
from gql.transport.requests import RequestsHTTPTransport

STARTGG_API_KEY = os.environ.get("STARTGG_API_KEY")

SET_VOD_MUTATION = gql("""
mutation ($setId: ID!, $vodUrl: String) {
  updateVodUrl(setId: $setId, vodUrl: $vodUrl) {
    id
  }
}
""")

def get_set_vod_request(set_id: str, video_url: str):
    params = {"setId": set_id, "vodUrl": video_url}
    return GraphQLRequest(request=SET_VOD_MUTATION, variable_values=params)

def batch_set_vods(client: Client, requests: list[GraphQLRequest]):
    client.execute_batch(requests)

def get_client(api_key=None):
    api_key = api_key or STARTGG_API_KEY
    transport = RequestsHTTPTransport(
        url="https://api.start.gg/gql/alpha",
        headers={
            "Authorization": f"Bearer {api_key}",
        },
    )
    return Client(transport=transport)
