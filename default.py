# -*- coding: utf-8 -*-
#Библиотеки, които използват python и Kodi в тази приставка
import sys
__all__ = ['PY2']
PY2 = sys.version_info[0] == 2

#import os

if PY2:
    import urlparse
    import urllib
else:
    import urllib.parse
import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import base64
import inputstreamhelper
from common import *
import datetime

import web_pdb

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
if PY2:
    args = urlparse.parse_qs(sys.argv[2][1:])
else:
    args = urllib.parse.parse_qs(sys.argv[2][1:])
this_plugin = xbmcaddon.Addon().getAddonInfo('path') + '/actions.py'
resources_path = xbmcaddon.Addon().getAddonInfo('path') + '/resources'

#xbmcplugin.setContent(addon_handle, 'movies')

def build_url(query):
    if PY2:
        return base_url + '?' + urllib.urlencode(query)
    return base_url + '?' + urllib.parse.urlencode(query)

if not username or not password or not xbmcaddon.Addon():
    xbmcaddon.Addon().openSettings()

#Инициализация
__all__ = ['PY2']

# Аутентикация
if int(user_id) and session_id:
    responce = request('CheckToken', {'devId': device_id, 'token': session_id, 'apply': 'true'}, method='GET')
    if 'error_code' in responce and responce['error_code']:
        session_id = ''
        if responce['error_code'] != 'errClDevNotFound':
            xbmcgui.Dialog().ok('Проблем', responce['message'])

if not user_id or not session_id:
    login_params = {'devId': device_id, 'user': username, 'pwd': password, 'rqT': 'true', 'refr': 'true'}
    responce = request('Login', login_params)

    if 'error_code' in responce and responce['error_code'] == 'errClDevNotFound':
        login_params = {'devId': '', 'user': username, 'pwd': password, 'rqT': 'true'}
        responce = request('Login', login_params)
        if 'error_code' in responce and responce['error_code']:
            xbmcgui.Dialog().ok('Проблем', responce['message'])
        # register
        headers = {'SDSEVO_USER_ID': responce['user_id'],
                   'SDSEVO_DEVICE_ID': device_id,
                   'SDSEVO_SESSION_ID': responce['token'],
        }
        client = my_gqlc(headers)
        query = '''
mutation createDevice($input: CreateDeviceInput!) {
    createDevice(input: $input) {
        success
        reauthenticate
        __typename
      }
}
'''
        res = client.execute(query, variables={
            'input':{
                'clientGeneratedDeviceId': device_id,
                'deviceType': 'LINUX',
                'name': 'Kodi on LINUX'
                }
            }
        )
        if 'errors' in res:
            message = ''
            for error in res['errors']:
                message += error['message']
            xbmcgui.Dialog().ok('Проблем', message)
            xbmcplugin.endOfDirectory(addon_handle)
        if 'data' in res and 'createDevice' in res['data']:
            if res['data']['createDevice']['reauthenticate']:
                client.execute('''mutation logout {
  logout
}
''')
                login_params['devId'] = device_id
                responce = request('Login', login_params)
        else:
            xbmcgui.Dialog().ok('Проблем', 'Unknown')
            xbmcplugin.endOfDirectory(addon_handle)
        del client
        
    if 'error_code' in responce and responce['error_code']:
        xbmcgui.Dialog().ok('Проблем', responce['message'])
    else:
        if user_id != str(responce['user_id']):
            user_id = str(responce['user_id'])
            xbmcaddon.Addon(id='plugin.video.mtelnow').setSetting('settings_user_id', user_id)
        if session_id != responce['token']:
            session_id = responce['token']
            xbmcaddon.Addon(id='plugin.video.mtelnow').setSetting('settings_session_id', session_id)

headers = {'SDSEVO_USER_ID': user_id,
           'SDSEVO_DEVICE_ID': device_id,
           'SDSEVO_SESSION_ID': session_id,
}
client = my_gqlc(headers)
client.execute('''mutation keepAlive {
  keepSessionAlive {
    sessionTimeout
    __typename
  }
}
''')

#Меню с директории в приставката
def MainMenu():
    #addDir('НЕ ПРОПУСКАЙТЕ', 'https://'+dns+'/home',5, live)
    addDir('index_channels', 'На живо', resources_path + "/icon_livetv.png")
    addDir('index_channels_program', 'ТВ Програма', resources_path + "/icon_tvschedule.png")
    addDir('index_vod', 'Видеотека', resources_path + "/icon_videostore.png")
    addDir('index_npvr', 'Записи', resources_path + "/home_tile_myrecordings.png")

#Разлистване видеата на първата подадена страница
def indexChannels():
    variables={"channelListId":"59-6","channelAfterCursor":None,"currentTime":datetime.datetime.utcnow().isoformat()[0:23]+'Z',"logoWidth":76,"logoHeight":28,"thumbnailHeight":280,"backgroundHeight":780,"backgroundWidth":1920,"shortDescriptionMaxLength":0}
    query = '''
query liveTV($channelAfterCursor: String, $currentTime: Date!, $logoWidth: Int!, $logoHeight: Int!, $thumbnailHeight: Int!, $backgroundHeight: Int!, $backgroundWidth: Int!, $channelListId: ID!, $shortDescriptionMaxLength: Int!) {
  channelList(id: $channelListId) {
    ...cacheInfoFragment
    name
    channels(after: $channelAfterCursor) {
      ...cacheInfoFragment
      totalCount
      pageInfo {
        hasNextPage
        endCursor
        __typename
      }
      edges {
        ...cacheInfoFragment
        cursor
        node {
          ...cacheInfoFragment
          title
          userInfo {
            ...cacheInfoFragment
            subscribed
            __typename
          }
          logo(width: $logoWidth, height: $logoHeight) {
            ...cacheInfoFragment
            url
            __typename
          }
          currentEvent: eventsAt(time: $currentTime, previous: 0, following: 0) {
            ...cacheInfoFragment
            itemCount
            items {
              ...nowPlayingEventFragment
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}

fragment cacheInfoFragment on Cacheable {
  __typename
  id
  expiry
}

fragment nowPlayingEventFragment on Event {
  ...cacheInfoFragment
  ...eventInfoBasicFragment
  eventEntitlements: entitlements {
    ...eventEntitlementsFragment
    __typename
  }
  eventMetadata: metadata {
    ...metadataExtendedFragment
    __typename
  }
  __typename
}

fragment eventInfoBasicFragment on Event {
  title
  start
  end
  blackout
  startOverTVBeforeTime
  startOverTVAfterTime
  thumbnail(height: $thumbnailHeight) {
    ...imageFragment
    __typename
  }
  parentalRating {
    ...parentalRatingFragment
    __typename
  }
  backgroundImage(width: $backgroundWidth, height: $backgroundHeight) {
    ...imageFragment
    __typename
  }
  __typename
}

fragment imageFragment on Image {
  ...cacheInfoFragment
  url
  width
  height
  __typename
}

fragment parentalRatingFragment on ParentalRating {
  ...cacheInfoFragment
  title
  description
  rank
  adult
  __typename
}

fragment eventEntitlementsFragment on EventEntitlements {
  pauseLiveTV
  restartTV
  catchupTV
  catchupTVAvailableUntil
  networkRecording
  networkRecordingPlannableUntil
  __typename
}

fragment metadataExtendedFragment on Metadata {
  ...cacheInfoFragment
  title
  originalTitle
  shortDescription(maxLength: $shortDescriptionMaxLength)
  country
  year
  fullDescription
  genre {
    ...cacheInfoFragment
    title
    __typename
  }
  seriesInfo {
    ...cacheInfoFragment
    title
    __typename
  }
  episodeInfo {
    ...cacheInfoFragment
    number
    title
    season
    __typename
  }
  actors
  directors
  ratings {
    ...cacheInfoFragment
    value
    name
    __typename
  }
  __typename
}

'''
    res = client.execute(query, variables=variables)

    #channels = request('ChannelGetByDeviceInstanceExtended', {'customerReferenceID': customer_reference_id})
    for channel in res['data']['channelList']['channels']['edges']:
        currentEvent = channel['node']['currentEvent']['items'][0]
        addLink(mode='playChannel', 
                name=currentEvent['start'][11:16] + ' ' + currentEvent['end'][11:16] + ' - ' + currentEvent['title'],
                iconimage=channel['node']['logo']['url'],
                params={'cid': channel['node']['id']},
                banner=channel['node']['logo']['url'],
                poster=currentEvent['thumbnail']['url'],
                fanart=currentEvent['backgroundImage']['url'],
                plot=channel['node']['title'] + ' - ' + currentEvent['start'][11:16] + ' ' + currentEvent['end'][11:16] + "\n" +
                currentEvent['title'] + "\n" + 
                currentEvent['eventMetadata']['genre']['title'] + "\n\n" +
                currentEvent['eventMetadata']['fullDescription']
        )
#def addLink(mode, name, iconimage, params={}, fanart="", plot="", context_items = {}):

#Списък с каналите за изграждане на програма
def indexChannelsProgram():
    channels = request('ChannelGetByDeviceInstanceExtended', {'customerReferenceID': customer_reference_id})
    for channel in channels:
        funart = channel['Icon']
        if 'CurrentProgrammeImagePath' in channel:
            funart = channel['CurrentProgrammeImagePath']
        addDir('index_program', channel['Name'] + ' - ' + channel['CurrentProgramme'], channel['Icon'], {'ChannelReferenceID': channel['ReferenceID']}, funart)

def indexProgram(args):
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
        addLink('play_epg', title, rec['ImagePath'],
                {'EPGReferenceID': rec['ReferenceID'], 'ChannelReferenceID': rec['ChannelReferenceID']}, 
                rec['ImagePath'], desc, 
                context_items = {'Запиши': "insert_npvr," + customer_reference_id + "," + rec['ReferenceID']})
    addDir('index_program', ' << ' + date.strftime('%Y-%m-%d'), '', {'ChannelReferenceID':channel_ref_id, 'days': days + 1})

def PlayChannel(args):
    channel_id = args.get('cid')[0]

    playback_session_id = xbmcaddon.Addon(id='plugin.video.mtelnow').getSetting('settings_playback_session_id')
    if playback_session_id:
        variables = {"input": {"sessionId": playback_session_id}}
        query = '''
mutation stopPlayback($input: StopPlaybackInput!) {
  stopPlayback(input: $input) {
    success
    __typename
  }
}

'''
        client.execute(query, variables=variables)

    variables = {"input": {"channelId": channel_id, "replaceSessionId": None}}
    query = '''
mutation playChannel($input: PlayChannelInput!) {
  playChannel(input: $input) {
    playbackInfo {
      sessionId
      url
      channel {
        id
        kind
        __typename
      }
      heartbeat {
        ... on HttpHeartbeat {
          url
          interval
          includeAuthHeaders
          __typename
        }
        __typename
      }
      __typename
    }
    __typename
  }
}
'''
    res = client.execute(query, variables)
    xbmcaddon.Addon(id='plugin.video.mtelnow').setSetting('settings_playback_session_id', res['data']['playChannel']['playbackInfo']['sessionId'])
    playPath(res['data']['playChannel']['playbackInfo']['url'])

#Зареждане на видео
def Play(args):
    path = args.get('path')[0]
    playPath(path)

def playPath(path, title = "", plot=""):
    #payload = {'jsonrpc': '2.0', 'id': 1, 'method': 'Addons.GetAddonDetails', 'params': {'addonid': 'inputstream.adaptive','properties': ['version']}}
    #response = xbmc.executeJSONRPC(json.dumps(payload))
    #data = json.loads(response)
    #version = data['result']['addon']['version'].replace(".", "")
    #if version < 2211:
    #    xbmcgui.Dialog().ok('Грешка','Inputsream.Adaptive е стара версия, моля обновете!')
    PROTOCOL = 'mpd'
    DRM = 'com.widevine.alpha'

    is_helper = inputstreamhelper.Helper(PROTOCOL, drm=DRM)
    if is_helper.check_inputstream():
        li = xbmcgui.ListItem(path=path)
        li.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        li.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
        li.setProperty('inputstream.adaptive.license_type', DRM)
        dt_custom_data = base64.b64decode('aHR0cHM6Ly93dnBzLmExeHBsb3JldHYuYmc6ODA2My8/ZGV2aWNlSWQ9WXpVNU1ERmpNRGN0WXpNNU15MDBZamd3TFdJek16UXRZbVV6TVdGbE9USXpZelUw')
        li.setProperty('inputstream.adaptive.license_key', dt_custom_data + '||R{SSM}|')
        #li.setMimeType('application/dash+xml')
        if title and plot:
            li.setInfo( type="Video", infoLabels={ "Title": title, "plot": plot})
        try:
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)
        except:
            xbmc.executebuiltin("Notification('Грешка','Видеото липсва на сървъра!')")
 
def playEPG(args):
    epg_ref_id = args.get('EPGReferenceID')[0]
    channel_ref_id = args.get('ChannelReferenceID')[0]
    
    epg_details = request('EPGGetDetails', 
                            {'customerReferenceID': customer_reference_id,
                             'channelReferenceID': channel_ref_id,
                             'epgReferenceID': epg_ref_id})
    path = epg_details['FileName']
    if path.find('/Live/') > 0:
        path = epg_details['FileNameStartOver']
    playPath(path, title=epg_details['Title'], plot=epg_details["DescriptionLong"])

def playVOD(args):
    asset_ref_id = args.get('ReferenceID')[0]

    asset_details = request('AssetGetAssetDetails',
                            {'customerReferenceID': customer_reference_id,
                             'languageReferenceID': language_reference_id,
                             'deviceReferenceID': "118",
                             'assetReferenceID': asset_ref_id})
    path = asset_details['FileName']
    playPath(path)

def indexNPVR():
    recs = request('NPVRGetByCustomerReferenceID', {'customerReferenceID': customer_reference_id})
    for rec in recs:
        time_end = rec['TimeEnd']
        time_start = rec['TimeStart']
        desc = 'Час: ' + time_start.strftime('%d.%m.%Y %H:%M') + ' - ' + time_end.strftime('%H:%M')
        title = time_start.strftime('%d.%m %H:%M') + ' ' + rec['ChannelName'] + ' ' + rec['Title']
        addLink('play_epg', title, rec['ImagePath'],
                {'EPGReferenceID': rec['EPGReferenceID'], 'ChannelReferenceID': rec['ChannelReferenceID']}, 
                rec['ImagePath'], desc, 
                context_items = {'Изтрий': "delete_npvr," + customer_reference_id + "," + rec['EPGReferenceID']})
        
def indexVOD():
    try:
        items = request('VideostoreItemGetChildrenCatalogue', 
                     {'languageReferenceID': language_reference_id})
        for item in items:
            addDir('index_vod_cat', item['Name'], item['Icon'], {'ReferenceID': item['ReferenceID']})
    except TypeError:
        xbmcgui.Dialog().ok('Не сте абониран','Не сте абониран за избрания пакет. Моля, свържете се с наш сътрудник на *88.')

def indexVODCat(args):
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

def indexVODSeries(args):
    ref_id = args.get('ReferenceID')[0]
    s_ref_id = args.get('seasonReferenceID',[''])[0]
    items = request('SeriesGetContent', 
                     {'languageReferenceID': language_reference_id, 
                      'seriesReferenceID': ref_id,
                      'seasonReferenceID': s_ref_id})
    for item in items:
        funart = item['PosterLandscape']
        if not funart:
            funart = item['PosterPortrait']
        if item['Type'] == 'season':
            addDir('index_vod_series', item['Name'], funart, {'seasonReferenceID': item['ReferenceID'], 'ReferenceID': ref_id}, funart)
        else:
            plot = ''
            if 'DescriptionShort' in item:
                plot = item['DescriptionShort']
            addLink('play_vod',
                     'S' + str(item['SeasonNr']) + ' E' + str(item['EpisodeNr']) + ' ' + item['Name'], 
                     funart, 
                     {'ReferenceID': item['ReferenceID']}, 
                     funart, plot)

#Модул за добавяне на отделно заглавие и неговите атрибути към съдържанието на показваната в Kodi директория - НЯМА НУЖДА ДА ПРОМЕНЯТЕ НИЩО ТУК
def addLink(mode, name, iconimage, params={}, fanart="", plot="", context_items = {}, banner="", poster=""):
    query = {'mode': mode}
    if params:
        query.update(params)
    url = build_url(query)
    if not banner:
        banner = fanart
    if not poster:
        poster = fanart
    li = xbmcgui.ListItem(name, iconImage=iconimage, thumbnailImage=iconimage)
    li.setArt({ 'thumb': iconimage,'poster': poster, 'banner' : banner, 'fanart': fanart })
    li.setInfo( type="Video", infoLabels={"Title": name, "plot": plot})
    li.setProperty("IsPlayable" , "true")
    if context_items:
        pre_items = []
        for item in context_items:
            pre_items.append((item, "XBMC.RunScript(" + this_plugin + ", " + context_items[item] + ")"))
        li.addContextMenuItems(pre_items)
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
        MainMenu()
elif mode[0] == 'index_channels':
        indexChannels()
elif mode[0] == 'playChannel':
        PlayChannel(args)
elif mode[0] == 'play':
        Play(args)
elif mode[0] == 'index_npvr':
        indexNPVR()
elif mode[0] == 'index_vod':
        indexVOD()
elif mode[0] == 'index_vod_cat':
        indexVODCat(args)
elif mode[0] == 'index_vod_series':
        indexVODSeries(args)
elif mode[0] == 'play_vod':
        playVOD(args)
elif mode[0] == 'play_epg':
        playEPG(args)
elif mode[0] == 'index_channels_program':
        indexChannelsProgram()
elif mode[0] == 'index_program':
        indexProgram(args)
        
xbmcplugin.endOfDirectory(addon_handle)
