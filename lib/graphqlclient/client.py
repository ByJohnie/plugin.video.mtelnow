from lib.six.moves import urllib
import json

class GraphQLClient:
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def execute(self, query, variables=None, headers={}):
        return self._send(query, variables, headers)

    def _send(self, query, variables, headers):
        data = {'query': query,
                'variables': variables}
        headers['Accept'] = 'application/json'
        headers['Content-Type'] = 'application/json'

        req = urllib.request.Request(self.endpoint, json.dumps(data).encode('utf-8'), headers=headers)

        try:
            response = urllib.request.urlopen(req)
            return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print((e.read()))
            print('')
            raise e
