import fire
import requests
from datetime import datetime
from secret import GITHUB_AUTH_TOKEN

GITHUB_GRAPHQL_URL = 'https://api.github.com/graphql'
DATE_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def get_user_name(token=GITHUB_AUTH_TOKEN):
    """Return current login user's name with given token

    Parameters
    ----------
    token : str
        String representing Github Developer Access Token

    Returns
    -------
    user_name : str
    """
    payload = "{\"query\":\"query {\\n  viewer {\\n    login\\n  }\\n}\"}"
    res = query_graphql(payload, token)
    return res['data']['viewer']['login']


def query_graphql(payload, token=GITHUB_AUTH_TOKEN, url=GITHUB_GRAPHQL_URL):
    """Helper to query Github GraphQL API

    Parameters
    ----------
    payload : str
        Valid GraphQL query string.
        e.g., "{\"query\":\"query {\\n  viewer {\\n    login\\n  }\\n}\"}"

    Returns
    -------
    res : dict

    """
    headers = {
        'content-type': "application/json",
        'authorization': "Bearer {}".format(token)
    }

    res = requests.request("POST", url, data=payload, headers=headers).json()
    assert res.get('data', False), 'No data available from Github: {}'.format(res)
    return res


def get_gists(cursor=None, size=100):
    """Return all gists (public & secret) and end_cursor for pagination

    Parameters
    ----------
    cursor : str
        String indicating endCursor in previous API request.
        e.g. "Y3Vyc29yOnYyOpK5MjAxOC0wMS0yM1QxMTo1NDo0MSswOTowMM4FGyp6"

    size : int
        Specify how many gists to fetch in a HTTP request to Github.
        Default set to Node limit specified by Github GraphQL resource limit.

    Returns
    -------
    gists : list of dict
        List of gists with each gist is a dict of form:
            {
                "id": "id",
                "description": "some description",
                "name": "just a name",
                "pushedAt": "2018-01-15T08:32:57Z"
            }

    total : int
        Indicate how many gists available

    end_cursor : str
        A string representing the endCursor in gists.pageInfo

    has_next_page : bool
        Indicating whether there are gists remains

    Notes
    -----
    Github GraphQL resource limit
        https://developer.github.com/v4/guides/resource-limitations/

    """
    first_payload = "{\"query\":\"query {viewer {gists(first:%d, privacy:ALL, orderBy: {field: UPDATED_AT, direction: DESC}) {totalCount edges { node { id description name pushedAt } cursor } pageInfo { endCursor hasNextPage } } } }\"}"
    payload_template = "{\"query\":\"query {viewer {gists(first:%d, privacy:ALL, orderBy: {field: UPDATED_AT, direction: DESC}, after:\\\"%s\\\") {totalCount edges { node { id description name pushedAt } cursor } pageInfo { endCursor hasNextPage } } } }\"}"

    if not cursor:
        payload = first_payload % size
    else:
        payload = payload_template % (size, cursor)

    res = query_graphql(payload)


    # parse nested response for easier usage
    gists = res['data']['viewer']['gists']
    total = gists['totalCount']
    page_info = gists['pageInfo']
    end_cursor, has_next_page = page_info['endCursor'], page_info['hasNextPage']
    gists = [e['node'] for e in gists['edges']]

    return gists, total, end_cursor, has_next_page


def get_number_of_gists():
    """Get total number of gists available in the user account

    Returns
    -------
    num_gists : int
    """
    payload = "{\"query\":\"query { viewer { gists(privacy:ALL) {totalCount}}}\"}"
    res = query_graphql(payload)
    return res['data']['viewer']['gists']['totalCount']


def get_all_gists(size=None, after_date=None, filter_on='pushedAt'):
    """Get number of `size` gists at once without pagination.

    A wrapper over `get_gists` func. Handle the pagination automatically.
    If size is not set by user, query Github for total number of gists.
    If a valid `after_date` is given, gists with field `filter_on` earlier than
    `after_date` will be dropped.

    Parameters
    ----------
    size : int, optional
        Number of gists to fetch. Set to total number of gists if not set by user

    after_date : datetime.datetime
        UTC date to filter gists

    filter_on : str
        Date field corresponding to Github API for Gist

    Returns
    -------
    gists : list of dict
        List of gists with each gist is a dict of form:
            {
                "id": "id",
                "description": "some description",
                "name": "just a name",
                "pushedAt": "2018-01-15T08:32:57Z"
            }

    See Also
    --------
    get_gists : Return all gists (public & secret) and end_cursor for pagination


    """
    if not size:
        size = get_number_of_gists()

    end_cursor = None
    gists = []

    while True:
        cur_gists, total, end_cursor, has_next_page = get_gists(end_cursor)
        for gist in cur_gists:
            pushed_date = datetime.strptime(gist[filter_on], DATE_FORMAT)
            if after_date and pushed_date <= after_date:
                return gists

            if len(gists) >= size:
                return gists
            gists.append(gist)

        if not has_next_page:
            break

    return gists


if __name__ == '__main__':
    fire.Fire()
