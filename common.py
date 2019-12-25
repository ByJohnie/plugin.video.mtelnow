# -*- coding: utf-8 -*-
import sys
PY2 = sys.version_info[0] == 2
import xbmc, xbmcaddon
import uuid
if PY2:
    import urllib2
else:
    import urllib.request
import datetime
import json
#import md5


#Място за дефиниране на константи, които ще се използват няколкократно из отделните модули
#UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
UA = 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
username = xbmcaddon.Addon(id='plugin.video.mtelnow').getSetting('settings_username')
password = xbmcaddon.Addon(id='plugin.video.mtelnow').getSetting('settings_password')
deviceSerial = str(uuid.uuid5(uuid.NAMESPACE_DNS, xbmc.getInfoLabel('Network.MacAddress')))

def _byteify(data, ignore_dicts = False):
    # if this is a unicode string, return its string representation
    if (PY2 and isinstance(data, unicode)) or isinstance(data, str):
        if PY2:
            val = data.encode('utf-8')
        else:
            val = data
        if val[0:6] == '/Date(' and val[-2:] == ')/':
            val = datetime.datetime.utcfromtimestamp(int(val[6:19]) / 1e3 + 60*60*2)
        return val
    # if this is a list of values, return list of byteified values
    if isinstance(data, list):
        return [ _byteify(item, ignore_dicts=True) for item in data ]
    # if this is a dictionary, return dictionary of byteified keys and values
    # but only if we haven't already byteified it
    if isinstance(data, dict) and not ignore_dicts:
        if PY2:
            return {
                _byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
                for key, value in data.iteritems()
            }
        else:
            return {
                _byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
                for key, value in data.items()
            }
    # if it's anything else, return it in its original form
    return data

#изпращане на requst към endpoint
def request(action, params={}):
    endpoint = 'https://tagott.vip.hr/OTTService.svc/restservice/'
    data = {'deviceType': "118",
            'deviceSerial': deviceSerial,
            'operatorReferenceID': "A1_bulgaria",
            'username': username,
            'password': password}#"{md5}" + md5.new(password).hexdigest()}
    data.update(params)
    if PY2:
        req = urllib2.Request(endpoint + action, json.dumps(data))
    else:
        req = urllib.request.Request(endpoint + action, json.dumps(data).encode("utf-8"))
    req.add_header('User-Agent', UA)
    req.add_header('Content-Type', 'application/json; charset=UTF-8')
    if PY2:
        f = urllib2.urlopen(req)
    else:
        f = urllib.request.urlopen(req)
    responce = f.read()
    json_responce = json.loads(responce, object_hook=_byteify)
    return json_responce[action + 'Result']
