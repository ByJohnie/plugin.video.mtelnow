# -*- coding: utf-8 -*-
import sys
PY2 = sys.version_info[0] == 2
import xbmc, xbmcaddon
import uuid
if PY2:
    from urllib import urlencode
    import urllib2
    import urlparse
else:
    import urllib.request
    import urllib.parse
import datetime, time, pytz
import json
from lib.graphqlclient import GraphQLClient

def debug(obj):
    xbmc.log(json.dumps(obj, indent=2), xbmc.LOGDEBUG)

#Място за дефиниране на константи, които ще се използват няколкократно из отделните модули
username = xbmcaddon.Addon(id='plugin.video.mtelnow').getSetting('settings_username')
password = xbmcaddon.Addon(id='plugin.video.mtelnow').getSetting('settings_password')
user_id = xbmcaddon.Addon(id='plugin.video.mtelnow').getSetting('settings_user_id')
session_id = xbmcaddon.Addon(id='plugin.video.mtelnow').getSetting('settings_session_id')
max_bandwidth = xbmcaddon.Addon(id='plugin.video.mtelnow').getSetting('settings_max_bandwidth')
if xbmcaddon.Addon(id='plugin.video.mtelnow').getSetting('settings_adult') == "false":
    adult_setting = False
else:
    adult_setting = True
if PY2:
    args = urlparse.parse_qs(sys.argv[2][1:])
else:
    args = urllib.parse.parse_qs(sys.argv[2][1:])

# device_id, ще го мъкнем като параметър, че понякога се взима бавно
device_id = args.get('device_id',[''])[0]
if not device_id:
    mac = xbmc.getInfoLabel('Network.MacAddress')
    # Мак-а може да се върне като Busy, ако kodi прави нещо друго, затова пробваме докато успеем
    while mac == 'Busy':
        time.sleep(0.5)
        mac = xbmc.getInfoLabel('Network.MacAddress')
    device_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, mac))

# Класс за ползване на GraphQL
class my_gqlc(GraphQLClient):
    def __init__(self, headers):
        self.endpoint = 'https://web.a1xploretv.bg:8443/sdsmiddleware/Mtel/graphql/4.0'
        self.headers = headers
    def execute(self, query, variables=None):
        debug(self.headers)
        debug(query.partition('\n')[0])
        res = self._send(query, variables, self.headers)
        debug(res)
        return res

def to_datetime(instr):
    return datetime.datetime(*(time.strptime(instr, '%Y-%m-%dT%H:%M:%SZ')[0:6])).replace(tzinfo=pytz.timezone('UTC')).astimezone(pytz.timezone('Europe/Sofia'))

#изпращане на requst към endpoint
def request(action, params={}, method='POST'):
    endpoint = 'https://web.a1xploretv.bg:8843/ext_dev_facade/auth/'
    data = {}
    data.update(params)
    debug(action)
    debug(data)
    if PY2:
        tmp = ''
        if method == 'GET':
            tmp = None
        req = urllib2.Request(endpoint + action + '?%s' % urlencode(data), data=tmp)
    else:
        req = urllib.request.Request(endpoint + action + '?%s' % urllib.parse.urlencode(data), method=method)
    req.add_header('Content-Type', 'application/json')
    if PY2:
        f = urllib2.urlopen(req)
    else:
        f = urllib.request.urlopen(req)
    responce = f.read()
    json_responce = json.loads(responce)
    debug(json_responce)
    return json_responce
