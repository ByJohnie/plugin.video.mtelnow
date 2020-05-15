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
import time

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
if PY2:
    args = urlparse.parse_qs(sys.argv[2][1:])
else:
    args = urllib.parse.parse_qs(sys.argv[2][1:])

# Променливи предавани, чрез параметри
profile_id = int(args.get('profile_id',[0])[0])
timeout = int(args.get('timeout',[0])[0])

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
reauth = False
if int(user_id) and session_id and int(time.time()) > timeout:
    responce = request('CheckToken', {'devId': device_id, 'token': session_id, 'apply': 'true'}, method='GET')
    if 'error_code' in responce and responce['error_code']:
        # Ако има проблем казваме да се аутентикира наново
        reauth = True
        if responce['error_code'] not in ('errClDevNotFound', 'errExpiredSecToken', 'errSecTokenCustom'):
            # Ако е непозната грешка да я покажем
            xbmcgui.Dialog().ok('Проблем', responce['message'])

if not user_id or not session_id or reauth:
    # Логин
    login_params = {'devId': device_id, 'user': username, 'pwd': password, 'rqT': 'true'} #, 'refr': 'true'}
    responce = request('Login', login_params)

    if 'error_code' in responce and responce['error_code'] == 'errClDevNotFound':
        # Ако устройството не е регистрирано, го регистрираме
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
        res = client.execute(open(resources_path + '/createDevice.graphql').read(), variables={
            'input':{
                'clientGeneratedDeviceId': device_id,
                'deviceType': 'LINUX',
                'name': 'Kodi on LINUX'
                }
            }
        )
        if 'data' in res and 'createDevice' in res['data']:
            if res['data']['createDevice']['reauthenticate']:
                # Ако ни е казано, се аутентикираме наново
                client.execute(open(resources_path + '/logout.graphql').read())
                login_params['devId'] = device_id
                responce = request('Login', login_params)
        else:
            message = ''
            if 'errors' in res:
                message = ''
                for error in res['errors']:
                    message += error['message'] + "\n"
            else:
                message = 'Unknown'
            xbmcgui.Dialog().ok('Проблем', message)
            xbmcplugin.endOfDirectory(addon_handle)
        # ще изградим клиента наново
        del client
    
    # Малко тъпо, ако не ни е казано да се логнем на ново тука може и да гръмне
    if 'error_code' in responce and responce['error_code']:
        xbmcgui.Dialog().ok('Проблем', responce['message'])
    else:
        # Ако сме се аутентикирали успешно си записваме в settings user_id и session_id
        if user_id != str(responce['user_id']):
            user_id = str(responce['user_id'])
            xbmcaddon.Addon(id='plugin.video.mtelnow').setSetting('settings_user_id', user_id)
        if session_id != responce['token']:
            session_id = responce['token']
            xbmcaddon.Addon(id='plugin.video.mtelnow').setSetting('settings_session_id', session_id)

# Изграждаме си нов клиент за GraphQL
headers = {'SDSEVO_USER_ID': user_id,
           'SDSEVO_DEVICE_ID': device_id,
           'SDSEVO_SESSION_ID': session_id,
}
client = my_gqlc(headers)

# ако ни е дошло време си подновяваме сесията
if int(time.time()) > timeout:
    res = client.execute(open(resources_path + '/keepAlive.graphql').read())
    if 'keepSessionAlive' in res['data'] and 'sessionTimeout' in res['data']['keepSessionAlive']:
        timeout = int(time.time()) + res['data']['keepSessionAlive']['sessionTimeout']

# Взимаме profile_id, ако го нямаме
if not profile_id:
    res = client.execute(open(resources_path + '/getSetupSteps.graphql').read())
    profile_id = int(res['data']['me']['household']['profiles']['items'][0]['id'])

#Меню с директории в приставката
def MainMenu():
    #addDir('НЕ ПРОПУСКАЙТЕ', 'https://'+dns+'/home',5, live)
    addDir('indexLiveTV', 'На живо', resources_path + "/icon_livetv.png")
    addDir('indexChannelList', 'ТВ Програма', resources_path + "/icon_tvschedule.png")
#    addDir('indexVOD', 'За теб', resources_path + "/icon_videostore.png")
    addDir('indexMyLibrary', 'Моята секция', resources_path + "/home_tile_myrecordings.png")

# Списък с канали за гледане в реално време
def indexLiveTV():
    variables={"channelListId":"59-6","channelAfterCursor":None,"currentTime":datetime.datetime.utcnow().isoformat()[0:23]+'Z',"logoWidth":76,"logoHeight":28,"thumbnailHeight":280,"backgroundHeight":780,"backgroundWidth":1920,"shortDescriptionMaxLength":0}
    res = client.execute(open(resources_path + '/liveTV.graphql').read(), variables=variables)

    for channel in res['data']['channelList']['channels']['edges']:
        currentEvent = channel['node']['currentEvent']['items'][0]
        adult = currentEvent['parentalRating']['adult']
        if not(adult) or (adult and adult_setting):
            dt_start = to_datetime(currentEvent['start'])
            dt_end = to_datetime(currentEvent['end'])
            addLink(mode='playChannel', 
                    name=dt_start.strftime('%H:%M') + ' ' + dt_end.strftime('%H:%M') + ' - ' + currentEvent['title'],
                    iconimage=channel['node']['logo']['url'],
                    params={'channel_id': channel['node']['id']},
                    banner=channel['node']['logo']['url'],
                    poster=currentEvent['thumbnail']['url'],
                    fanart=currentEvent['backgroundImage']['url'],
                    plot=channel['node']['title'] + ' - ' + dt_start.strftime('%Y-%m-%d %H:%M') + ' ' + dt_end.strftime('%H:%M') + "\n" +
                        currentEvent['title'] + "\n" + 
                        currentEvent['eventMetadata']['genre']['title'] + "\n\n" +
                        currentEvent['eventMetadata']['fullDescription']
            )

# Списък с канали за преглед назад във времето
def indexChannelList():
    variables={"channelListId":"59-6","firstChannels":1000,"after":None,"currentTime":datetime.datetime.utcnow().isoformat()[0:23]+'Z',"thumbnailHeight":280,"backgroundHeight":780,"backgroundWidth":1920,"shortDescriptionMaxLength":0}
    res = client.execute(open(resources_path + '/channelList.graphql').read(), variables=variables)

    for channel in res['data']['channelList']['channels']['edges']:
        currentEvent = channel['node']['currentEvent']['items'][0]
        adult = currentEvent['parentalRating']['adult']
        if not(adult) or (adult and adult_setting):
            dt_start = to_datetime(currentEvent['start'])
            dt_end = to_datetime(currentEvent['end'])
            addDir(mode='indexChannelGuide', 
                name=channel['node']['title'] + ' - ' + currentEvent['title'],
                iconimage=channel['node']['logo']['url'],
                params={'channel_id': channel['node']['id']},
                banner=channel['node']['logo']['url'],
                poster=currentEvent['thumbnail']['url'],
                fanart=currentEvent['backgroundImage']['url'],
                plot=channel['node']['title'] + ' - ' + dt_start.strftime('%Y-%m-%d %H:%M') + ' ' + dt_end.strftime('%H:%M') + "\n" +
                    currentEvent['title'] + "\n" + 
                    currentEvent['eventMetadata']['genre']['title'] + "\n\n" +
                    currentEvent['eventMetadata']['fullDescription']
            )

# Списък на програмата на даден канал
def indexChannelGuide(args):
    channel_id = args.get('channel_id')[0]
    days = int(args.get('days',[1])[0])
    start_date = datetime.datetime.utcnow() - datetime.timedelta(days=days, hours=0)
    variables = {
        "channelId": channel_id,
        "channelLogoFlavour": "NORMAL",
        "channelLogoHeight": 41,
        "channelLogoWidth": 112,
        "startDate": start_date.isoformat()+'Z',
        "thumbnailHeight": 280,
        "timeslotDurations": [86400],
        "shortDescriptionMaxLength": 0,
        "backgroundHeight":780,
        "backgroundWidth":1920
    }
    res = client.execute(open(resources_path + '/channelGuide.graphql').read(), variables=variables)
    channel = res['data']['channel']

    for event in reversed(res['data']['channel']['events'][0]['items']):
        adult = event['parentalRating']['adult']
        if not(adult) or (adult and adult_setting):
            dt_start = to_datetime(event['start'])
            dt_end = to_datetime(event['end'])
            addLink(mode='catchupEvent', 
                    name=dt_start.strftime('%H:%M') + ' ' + dt_end.strftime('%H:%M') + ' - ' + event['title'],
                    iconimage=event['thumbnail']['url'],
                    params={'event_id': event['id']},
                    banner=event['thumbnail']['url'],
                    poster=event['thumbnail']['url'],
                    fanart=event['backgroundImage']['url'],
                    plot=channel['title'] + ' - ' + dt_start.strftime('%Y-%m-%d %H:%M') + ' ' + dt_end.strftime('%H:%M') + "\n" +
                    event['title'] + "\n" + 
                    event['eventMetadata']['genre']['title'] + "\n\n" +
                    event['eventMetadata']['fullDescription'],
                    context_items={'Добави в моя списък': 'favoriteItem,' + str(profile_id) + ',' + str(event['id'])}
            )
    addDir('indexChannelGuide', ' << ' + start_date.strftime('%Y-%m-%d'), '', {'channel_id':channel_id, 'days': days + 1})

# Пускане на канал в реално време
def PlayChannel(args):
    channel_id = args.get('channel_id')[0]

    playback_session_id = xbmcaddon.Addon(id='plugin.video.mtelnow').getSetting('settings_playback_session_id')
    if playback_session_id:
        variables = {"input": {"sessionId": playback_session_id}}
        client.execute(open(resources_path + '/stopPlayback.graphql').read(), variables=variables)

    variables = {"input": {"channelId": channel_id, "replaceSessionId": None}}
    res = client.execute(open(resources_path + '/playChannel.graphql').read(), variables)
    xbmcaddon.Addon(id='plugin.video.mtelnow').setSetting('settings_playback_session_id', res['data']['playChannel']['playbackInfo']['sessionId'])
    playPath(res['data']['playChannel']['playbackInfo']['url'])

# Пускане на евент от миналото
def catchupEvent(args):
    event_id = args.get('event_id')[0]

    playback_session_id = xbmcaddon.Addon(id='plugin.video.mtelnow').getSetting('settings_playback_session_id')
    if playback_session_id:
        variables = {"input": {"sessionId": playback_session_id}}
        client.execute(open(resources_path + '/stopPlayback.graphql').read(), variables=variables)

    variables = {"input": {"eventId": event_id, "replaceSessionId": None}}
    res = client.execute(open(resources_path + '/catchupEvent.graphql').read(), variables)
    xbmcaddon.Addon(id='plugin.video.mtelnow').setSetting('settings_playback_session_id', res['data']['catchupEvent']['playbackInfo']['sessionId'])
    playPath(res['data']['catchupEvent']['playbackInfo']['url'])
     
# За теб секцията. Не е довършена, защото няма play
def indexVOD():
    variables = {
        "profileId": profile_id,
        "firstFolders": 5,
        "foldersAfterCursor": None,
    }
    res = client.execute(open(resources_path + '/home.graphql').read(), variables=variables)
    for folder in res['data']['homeRows']['folders']['edges']:
        addDir('indexVODFolder', folder['node']['title'], None, {'folder_id': folder['node']['id']})

def indexVODFolder(args):
    folder_id = args.get('folder_id')[0]
    variables = { "profileId": profile_id,
      "id": folder_id,
      "firstItems": 100,
      "itemsAfterCursor": None,
      "lastItems": 0,
      "itemsBeforeCursor": None,
      "thumbnailHeight": 280,
      "channelLogoWidth": 112,
      "channelLogoHeight": 41,
      "channelLogoFlavour": "INVERTED",
      "backgroundHeight": 780,
      "backgroundWidth": 1920}
    res = client.execute(open(resources_path + '/getFolderById.graphql').read(), variables=variables)
    for item in res['data']['contentFolder']['firstItems']['edges'] + res['data']['contentFolder']['lastItems']['edges']:
        fullDescription = ''
        fanart = item['node']['thumbnail']['url']
        if 'backgroundImage' in item['node']:
            fanart = item['node']['backgroundImage']['url']
        if 'fullDescription' in item['node']:
            fullDescription = "\n\n" + item['node']['fullDescription']
        addDir(mode='indexVOD', 
                name=item['node']['title'],
                iconimage=item['node']['thumbnail']['url'],
                params={},
                banner=item['node']['thumbnail']['url'],
                poster=item['node']['thumbnail']['url'],
                fanart=fanart,
                plot=item['node']['title'] #+ "\n" + 
                  #event['eventMetadata']['genre']['title'] + "\n\n" +
                  + fullDescription
        )

def playPath(path, title = "", plot=""):
    PROTOCOL = 'mpd'
    DRM = 'com.widevine.alpha'

    is_helper = inputstreamhelper.Helper(PROTOCOL, drm=DRM)
    if is_helper.check_inputstream():
        li = xbmcgui.ListItem(path=path)
        li.setProperty('inputstreamaddon', is_helper.inputstream_addon)
        li.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
        li.setProperty('inputstream.adaptive.license_type', DRM)
        if max_bandwidth:
          li.setProperty('inputstream.adaptive.max_bandwidth', max_bandwidth)
        if PY2:
          device_hash = base64.b64encode(device_id)
        else:
          device_hash = base64.b64encode(device_id.encode()).decode()
        dt_custom_data = 'https://wvps.a1xploretv.bg:8063/?deviceId=' + device_hash
        li.setProperty('inputstream.adaptive.license_key', dt_custom_data + '||R{SSM}|')
        #li.setMimeType('application/dash+xml')
        if title and plot:
            li.setInfo( type="Video", infoLabels={ "Title": title, "plot": plot})
        try:
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, li)
        except:
            xbmc.executebuiltin("Notification('Грешка','Видеото липсва на сървъра!')")
 
# Моята секция / Любими
def indexMyLibrary():
    variables = {"profileId": profile_id,
                 "firstFolders": 20,
                 "foldersAfterCursor": None,
                 "firstItems": 30,
                 "itemsAfterCursor": None,
                 "lastItems": 15,
                 "itemsBeforeCursor": None,
                 "onlyDisplayAdultContent": False,
                 "thumbnailHeight": 280,
                 "backgroundHeight": 780,
                 "backgroundWidth": 1920,
                 "channelLogoWidth": 112,
                 "channelLogoHeight": 41,
                 "channelLogoFlavour": "INVERTED",
    }
    res = client.execute(open(resources_path + '/myLibrary.graphql').read(), variables=variables)
    for folder in res['data']['myLibrary']['folders']['edges']:
        for item in folder['node']['firstItems']['edges']:
            event = item['node']
            adult = event['parentalRating']['adult']
            if not(adult) or (adult and adult_setting):
                channel = event['channel']
                dt_start = to_datetime(event['start'])
                dt_end = to_datetime(event['end'])
                addLink(mode='catchupEvent', 
                        name=channel['title'] + dt_start.strftime('%Y-%m-%d %H:%M') + ' ' + dt_end.strftime('%H:%M') + ' - ' + event['title'],
                        iconimage=event['thumbnail']['url'],
                        params={'event_id': event['id']},
                        banner=event['thumbnail']['url'],
                        poster=event['thumbnail']['url'],
                        #fanart=event['backgroundImage']['url'],
                        plot=channel['title'] + ' - ' + dt_start.strftime('%Y-%m-%d %H:%M') + ' ' + dt_end.strftime('%H:%M') + "\n" +
                        event['title'] + "\n" + 
                        event['eventMetadata']['genre']['title'] + "\n\n" +
                        event['eventMetadata']['fullDescription'],
                        context_items={'Премахване от моя списък': 'unfavoriteItem,' + str(profile_id) + ',' + str(event['id'])}
                )

#Модул за добавяне на отделно заглавие и неговите атрибути към съдържанието на показваната в Kodi директория
def addLink(mode, name, iconimage, params={}, fanart="", plot="", context_items = {}, banner="", poster="", isFolder=False, isPlayable=True):
    query = {'mode': mode, 'profile_id': profile_id, 'timeout': timeout, 'device_id': device_id}
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
    if isPlayable:
        li.setProperty("IsPlayable" , "true")
    if context_items:
        pre_items = []
        for item in context_items:
            pre_items.append((item, "XBMC.RunScript(" + this_plugin + ", " + context_items[item] + ")"))
        li.addContextMenuItems(pre_items)
    return xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=url, listitem=li, isFolder=isFolder)

#Модул за добавяне на отделна директория и нейните атрибути към съдържанието на показваната в Kodi директория
def addDir(mode, name, iconimage, params={}, fanart="", plot="", context_items = {}, banner="", poster=""):
    return addLink(mode, name, iconimage, params=params, fanart=fanart, plot=plot, context_items=context_items, banner=banner, poster=poster, isFolder=True, isPlayable=False)

mode = args.get('mode', None)

#Списък на отделните подпрограми/модули в тази приставка - трябва напълно да отговаря на кода отгоре
if mode == None:
        MainMenu()
elif mode[0] == 'indexLiveTV':
        indexLiveTV()
elif mode[0] == 'playChannel':
        PlayChannel(args)
elif mode[0] == 'indexChannelList':
        indexChannelList()
elif mode[0] == 'indexChannelGuide':
        indexChannelGuide(args)
elif mode[0] == 'catchupEvent':
        catchupEvent(args)
elif mode[0] == 'indexVOD':
        indexVOD()
elif mode[0] == 'indexVODFolder':
        indexVODFolder(args)
elif mode[0] == 'indexMyLibrary':
        indexMyLibrary()
        
xbmcplugin.endOfDirectory(addon_handle)
