# -*- coding: utf-8 -*-
#Библиотеки, които използват python и Kodi в тази приставка
import sys
import os
import urllib
import urllib2
import urlparse
import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import base64
import uuid
import json
import datetime
import md5

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs(sys.argv[2][1:])

#xbmcplugin.setContent(addon_handle, 'movies')

def build_url(query):
    return base_url + '?' + urllib.urlencode(query)

#Място за дефиниране на константи, които ще се използват няколкократно из отделните модули
#UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'
UA = 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'
username = xbmcaddon.Addon().getSetting('settings_username')
password = xbmcaddon.Addon().getSetting('settings_password')
deviceSerial = str(uuid.uuid5(uuid.NAMESPACE_DNS, xbmc.getInfoLabel('Network.MacAddress')))

if not username or not password or not xbmcaddon.Addon():
        xbmcaddon.Addon().openSettings()
#Инициализация

#Меню с директории в приставката
def CATEGORIES():
    #addDir('НЕ ПРОПУСКАЙТЕ', 'https://'+dns+'/home',5, live)
    addDir('index', 'Телевизия', "https://tagott.vip.hr/OTTResources/mtel/icon_livetv.png")
    addDir('index_program', 'Програма', "https://tagott.vip.hr/OTTResources/mtel/icon_tvschedule.png")
    #addDir('index_vod', 'Видеотека', "https://tagott.vip.hr/OTTResources/mtel/icon_videostore.png")
    addDir('index_zapisi', 'Записи', "https://tagott.vip.hr/OTTResources/mtel/home_tile_myrecordings.png")

def _byteify(data, ignore_dicts = False):
    # if this is a unicode string, return its string representation
    if isinstance(data, unicode):
        val = data.encode('utf-8')
        if val[0:6] == '/Date(' and val[-2:] == ')/':
            val = datetime.datetime.utcfromtimestamp(int(val[6:19]) / 1e3 + 60*60*2)
        return val
    # if this is a list of values, return list of byteified values
    if isinstance(data, list):
        return [ _byteify(item, ignore_dicts=True) for item in data ]
    # if this is a dictionary, return dictionary of byteified keys and values
    # but only if we haven't already byteified it
    if isinstance(data, dict) and not ignore_dicts:
        return {
            _byteify(key, ignore_dicts=True): _byteify(value, ignore_dicts=True)
            for key, value in data.iteritems()
        }
    # if it's anything else, return it in its original form
    return data

#изпращане на requst към endpoint
def request(action, params={}):
    global customer_reference_id
    endpoint = 'https://tagott.vip.hr/OTTService.svc/restservice/'
    data = {'deviceType': "118",
            'deviceSerial': deviceSerial,
            'operatorReferenceID': "A1_bulgaria",
            'username': username,
            'password':"{md5}" + md5.new(password).hexdigest()}
    data.update(params)
    req = urllib2.Request(endpoint + action, json.dumps(data))
    req.add_header('User-Agent', UA)
    req.add_header('Content-Type', 'application/json; charset=UTF-8')
    f = urllib2.urlopen(req)
    responce = f.read()
    json_responce = json.loads(responce, object_hook=_byteify)
    #xbmc.log(json.dumps(),xbmc.LOGNOTICE)
    return json_responce[action + 'Result']

# Аутентикация
login = request('CustomerLoginGlobal', {'DRMID': deviceSerial, 'operatorExternalID': "A1_bulgaria"})
server_time = login['ServerTime']
customer_reference_id = login['myCustomer']['AdditionalIdentifiers'][0]['CustomerReferenceId']
language_reference_id = login['myCustomer']['LanguageExternalID']

#Списък с каналите за изграждане на програма
def INDEXPROGRAM():
    channels = request('ChannelGetByDeviceInstanceExtended', {'customerReferenceID': customer_reference_id})
    for channel in channels:
        funart = channel['Icon']
        if 'CurrentProgrammeImagePath' in channel:
            funart = channel['CurrentProgrammeImagePath']
        addDir('program', channel['Name'] + ' - ' + channel['CurrentProgramme'], channel['Icon'], {'ChannelReferenceID': channel['ReferenceID']}, funart)

def PROGRAM(args):
    global server_time
    channel_ref_id = args.get('ChannelReferenceID')[0]
    days = int(args.get('days',[1])[0])
    date = server_time - datetime.timedelta(days=days, hours=1)
    epg = request('EPGGetByChannelReferenceIDForDate', 
                    {'customerReferenceID': customer_reference_id, 
                     'channelReferenceID': channel_ref_id, 
                     'date': date.strftime('%Y-%m-%dT%H:%M')})
    for rec in reversed(epg):
        time_end = rec['TimeEnd']
        time_start = rec['TimeStart']
        desc = 'Час: ' + time_start.strftime('%d.%m.%Y %H:%M') + ' - ' + time_end.strftime('%H:%M')
        title = time_start.strftime('%H:%M') + ' ' + time_end.strftime('%H:%M') + ' ' + rec['Title']
        addLink('playepg', title, rec['ImagePath'],
                {'EPGReferenceID': rec['ReferenceID'], 'ChannelReferenceID': rec['ChannelReferenceID']}, 
                desc, rec['ImagePath'])
    addDir('program', ' << ' + date.strftime('%Y-%m-%d'), '', {'ChannelReferenceID':channel_ref_id, 'days': days + 1})


#Разлистване видеата на първата подадена страница
def INDEXPAGES():
    channels = request('ChannelGetByDeviceInstanceExtended', {'customerReferenceID': customer_reference_id})
    for channel in channels:
        time_end = channel['CurrentProgrammeStopTime']
        time_start = channel['CurrentProgrammeStartTime']
        funart = channel['Icon']
        if 'CurrentProgrammeImagePath' in channel:
            funart = channel['CurrentProgrammeImagePath']
        addLink('play', 
                  channel['Name'] + ' - ' + time_start.strftime('%H:%M') + ' ' + time_end.strftime('%H:%M') + ' - ' + channel['CurrentProgramme'],
                  channel['Icon'],
                  {'path': channel['StreamingURL']},
                  channel['CurrentProgramme'],
                  funart)

#Зареждане на видео
def PLAY(args):
    path = args.get('path')[0]
    PLAYPATH(path)

def PLAYPATH(path, title = "", plot=""):
    payload = {'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.GetAddonDetails', 'params': {'addonid': 'inputstream.adaptive','properties': ['version']}}
    response = xbmc.executeJSONRPC(json.dumps(payload))
    data = json.loads(response)
    version = data['result']['addon']['version'].replace(".", "")
    if version < 2211:
        xbmcgui.Dialog().ok('Грешка','Inputsream.Adaptive е стара версия, моля обновете!')
    li = xbmcgui.ListItem(path=path)
    li.setProperty('inputstreamaddon', 'inputstream.adaptive')
    li.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    li.setProperty('inputstream.adaptive.license_type', 'com.widevine.alpha')
    dt_custom_data = base64.b64decode('aHR0cHM6Ly92aXBvdHR2bXhkcm13di52aXAuaHIvP2RldmljZUlkPWFHVnNiRzg9fHxSe1NTTX18')
    li.setProperty('inputstream.adaptive.license_key', dt_custom_data)
    li.setMimeType('application/dash+xml')
    if title and plot:
        li.setInfo( type="Video", infoLabels={ "Title": title, "plot": plot})
    try:
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)
    except:
        xbmc.executebuiltin("Notification('Грешка','Видеото липсва на сървъра!')")

def PLAYEPG(args):
    epg_ref_id = args.get('EPGReferenceID')[0]
    channel_ref_id = args.get('ChannelReferenceID')[0]
    
    epg_details = request('EPGGetDetails', 
                            {'customerReferenceID': customer_reference_id,
                             'channelReferenceID': channel_ref_id,
                             'epgReferenceID': epg_ref_id})
    path = epg_details['FileName']
    if path.find('/Live/') > 0:
        path = epg_details['FileNameStartOver']
    PLAYPATH(path, title=epg_details['Title'], plot=epg_details["DescriptionLong"])

def INDEXZAPISI():
    recs = request('NPVRGetByCustomerReferenceID', {'customerReferenceID': customer_reference_id})
    for rec in recs:
        time_end = rec['TimeEnd']
        time_start = rec['TimeStart']
        desc = 'Час: ' + time_start.strftime('%d.%m.%Y %H:%M') + ' - ' + time_end.strftime('%H:%M')
        title = time_start.strftime('%d.%m %H:%M') + ' ' + rec['ChannelName'] + ' ' + rec['Title']
        addLink('playepg', title, rec['ImagePath'],
                {'EPGReferenceID': rec['EPGReferenceID'], 'ChannelReferenceID': rec['ChannelReferenceID']}, 
                desc, rec['ImagePath'])
        
def INDEXVOD():
    items = request('VideostoreItemGetChildrenCatalogue', 
                     {'languageReferenceID': language_reference_id})
    for item in items:
        addDir('index_vod_cat', item['Name'], item['Icon'], {'ReferenceID': item['ReferenceID']})

def INDEXVODCAT(args):
    ref_id = args.get('ReferenceID')[0]
    items = request('VideostoreItemGetChildrenCatalogue', 
                     {'languageReferenceID': language_reference_id, 
                      'catalogueReferenceID': ref_id})
    for item in items:
        if item['Type'] == 'series':
            funart = item['PosterLandscape']
            if not funart:
                funart = item['PosterPortrait']
            addDir('index_vod_series', item['Name'], item['PosterPortrait'], {'ReferenceID': item['ReferenceID']}, funart, item['DescriptionShort'])

def INDEXVODSERIES(args):
    ref_id = args.get('ReferenceID')[0]
    s_ref_id = args.get('seasonReferenceID',[''])[0]
    items = request('SeriesGetContent', 
                     {'languageReferenceID': language_reference_id, 
                      'seriesReferenceID': ref_id,
                      'seasonReferenceID': s_ref_id})
    for item in items:
        print(item)
        funart = item['PosterLandscape']
        if not funart:
            funart = item['PosterPortrait']
        if item['Type'] == 'season':
            addDir('index_vod_series', item['Name'], funart, {'seasonReferenceID': item['ReferenceID'], 'ReferenceID': ref_id}, funart)
        else:
            plot = ''
            if 'DescriptionShort' in item:
                plot = item['DescriptionShort']
            addDir('index_vod_series', 'S' + str(item['SeasonNr']) + ' E' + str(item['EpisodeNr']) + ' ' + item['Name'], funart, {'seasonReferenceID': item['ReferenceID'], 'ReferenceID': ref_id}, funart, plot)

#Модул за добавяне на отделно заглавие и неговите атрибути към съдържанието на показваната в Kodi директория - НЯМА НУЖДА ДА ПРОМЕНЯТЕ НИЩО ТУК
def addLink(mode, name, iconimage, params={}, plot="", fanart=""):
    query = {'mode': mode}
    if params:
        query.update(params)
    url = build_url(query)
    li = xbmcgui.ListItem(name, iconImage=iconimage, thumbnailImage=iconimage)
    li.setArt({ 'thumb': iconimage,'poster': fanart, 'banner' : fanart, 'fanart': fanart })
    li.setInfo( type="Video", infoLabels={"Title": name, "plot": plot})
    li.setProperty("IsPlayable" , "true")
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=False)

#Модул за добавяне на отделна директория и нейните атрибути към съдържанието на показваната в Kodi директория - НЯМА НУЖДА ДА ПРОМЕНЯТЕ НИЩО ТУК
def addDir(mode, name, iconimage, params={}, funart="", plot=""):
    query = {'mode': mode}
    if params:
        query.update(params)
    url = build_url(query)
    if not funart:
        funart = iconimage
    li = xbmcgui.ListItem(name, iconImage=iconimage, thumbnailImage=iconimage)
    li.setArt({ 'thumb': iconimage,'poster': funart, 'banner': funart, 'fanart': funart })
    li.setInfo( type="Video", infoLabels={"Title": name, "plot": plot})
    return xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)


mode = args.get('mode', None)

#Списък на отделните подпрограми/модули в тази приставка - трябва напълно да отговаря на кода отгоре
if mode == None:
        CATEGORIES()
elif mode[0] == 'index':
        INDEXPAGES()
elif mode[0] == 'play':
        PLAY(args)
elif mode[0] == 'index_zapisi':
        INDEXZAPISI()
elif mode[0] == 'index_vod':
        INDEXVOD()
elif mode[0] == 'index_vod_cat':
        INDEXVODCAT(args)
elif mode[0] == 'index_vod_series':
        INDEXVODSERIES(args)
elif mode[0] == 'playepg':
        PLAYEPG(args)
elif mode[0] == 'program':
        PROGRAM(args)
elif mode[0] == 'index_program':
        INDEXPROGRAM()
        
xbmcplugin.endOfDirectory(addon_handle)
