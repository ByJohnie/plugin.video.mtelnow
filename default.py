# -*- coding: utf-8 -*-
#Библиотеки, които използват python и Kodi в тази приставка
import sys
__all__ = ['PY2']
PY2 = sys.version_info[0] == 2

import os

if PY2:
    import urlparse
    import urllib
else:
    import urllib.parse
import xbmc, xbmcplugin, xbmcgui, xbmcaddon
import base64
import inputstreamhelper
from common import *

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
if PY2:
    args = urlparse.parse_qs(sys.argv[2][1:])
else:
    args = urllib.parse.parse_qs(sys.argv[2][1:])
this_plugin = xbmcaddon.Addon().getAddonInfo('path') + '/actions.py'

#xbmcplugin.setContent(addon_handle, 'movies')

def build_url(query):
    if PY2:
        return base_url + '?' + urllib.urlencode(query)
    return base_url + '?' + urllib.parse.urlencode(query)

if not username or not password or not xbmcaddon.Addon():
    xbmcaddon.Addon().openSettings()
#Инициализация

#Меню с директории в приставката
def MainMenu():
    #addDir('НЕ ПРОПУСКАЙТЕ', 'https://'+dns+'/home',5, live)
    addDir('index_channels', 'Телевизия', "https://tagott.vip.hr/OTTResources/mtel/icon_livetv.png")
    addDir('index_channels_program', 'Програма', "https://tagott.vip.hr/OTTResources/mtel/icon_tvschedule.png")
    addDir('index_vod', 'Видеотека', "https://tagott.vip.hr/OTTResources/mtel/icon_videostore.png")
    addDir('index_npvr', 'Записи', "https://tagott.vip.hr/OTTResources/mtel/home_tile_myrecordings.png")

# Аутентикация
login = request('CustomerLoginGlobal', {'DRMID': deviceSerial, 'operatorExternalID': "A1_bulgaria"})
server_time = login['ServerTime']
__all__ = ['PY2', 'server_time']
customer_reference_id = login['myCustomer']['AdditionalIdentifiers'][0]['CustomerReferenceId']
language_reference_id = login['myCustomer']['LanguageExternalID']

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


#Разлистване видеата на първата подадена страница
def indexChannels():
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
        dt_custom_data = base64.b64decode('aHR0cHM6Ly92aXBvdHR2bXhkcm13di52aXAuaHIvP2RldmljZUlkPWFHVnNiRzg9fHxSe1NTTX18')
        li.setProperty('inputstream.adaptive.license_key', dt_custom_data)
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
def addLink(mode, name, iconimage, params={}, fanart="", plot="", context_items = {}):
    query = {'mode': mode}
    if params:
        query.update(params)
    url = build_url(query)
    li = xbmcgui.ListItem(name, iconImage=iconimage, thumbnailImage=iconimage)
    li.setArt({ 'thumb': iconimage,'poster': fanart, 'banner' : fanart, 'fanart': fanart })
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
