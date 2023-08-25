# -*- coding:utf-8 -*-
import sys
import os
from urllib.parse import urlencode
import requests
import json
import qrcode
import time
import locale
import shutil
from datetime import datetime
from xbmcswift2 import Plugin, xbmc, xbmcplugin, xbmcvfs, xbmcgui, xbmcaddon
from danmaku2ass import Danmaku2ASS

locale.setlocale(locale.LC_ALL, 'zh_CN.utf-8')

try:
    xbmc.translatePath = xbmcvfs.translatePath
except AttributeError:
    pass

plugin = Plugin()


def tag(info, color='red'):
    return '[COLOR ' + color + ']' + info + '[/COLOR]'


def parts_tag(p):
    return tag('【' + str(p) + 'P】', 'red')


def convert_number(num):
    if isinstance(num, str):
        return num
    if num < 9950:
        return str(num)
    if num < 99500000:
        result = round(num / 10000, 1)
        return str(result) + "万"
    else:
        result = round(num / 100000000, 1)
        return str(result) + "亿"


def timestamp_to_date(timestamp):
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime('%Y年%m月%d日 %H:%M:%S')


def notify(title, msg, t=1500):
    xbmcgui.Dialog().notification(title, msg, xbmcgui.NOTIFICATION_INFO, t, False)


def notify_error(res):
    message = '未知错误'
    if 'message' in res:
        message = res['message']
    notify('提示', str(res['code']) + ': ' + message)

def localize(id):
    return xbmcaddon.Addon().getLocalizedString(id)


def getSetting(name):
    return xbmcplugin.getSetting(int(sys.argv[1]), name)


def clear_text(text):
    return text.replace('<em class=\"keyword\">', '').replace('</em>', '')


def get_video_item(item):
    if 'attr' in item and item['attr'] != 0:
        return

    if 'videos' in item and isinstance(item['videos'], int):
        multi_key = 'videos'
    elif 'page' in item and isinstance(item['page'], int):
        multi_key = 'page'
    elif 'count' in item and isinstance(item['count'], int):
        multi_key = 'count'
    else:
        multi_key = ''

    if 'upper' in item:
        uname = item['upper']['name']
    elif 'owner' in item:
        uname = item['owner']['name']
    elif 'author' in item:
        uname = item['author']
    else:
        uname = ''

    if 'pic' in item:
        pic = item['pic']
    elif 'cover' in item:
        pic = item['cover']
    elif 'face' in item:
        pic = item['face']
    else:
        pic = ''

    if 'bvid' in item:
        bvid = item['bvid']
    elif 'history' in item and 'bvid' in item['history']:
        bvid = item['history']['bvid']

    if 'title' in item:
        title = item['title']


    if 'cid' in item:
        cid = item['cid']
    elif 'ugc' in item and 'first_cid' in item['ugc']:
        cid = item['ugc']['first_cid']
    else:
        cid = 0

    if 'duration' in item:
        if isinstance(item['duration'], int):
            duration = item['duration']
        else:
            duration = parse_duration(item['duration'])
    elif 'length' in item:
        if isinstance(item['length'], int):
            duration = item['length']
        else:
            duration = parse_duration(item['length'])
    elif 'duration_text' in  item:
        duration = parse_duration(item['duration_text'])
    else:
        duration = 0

    plot = parse_plot(item)
    if (not multi_key) or item[multi_key] == 1:
        video = {
            'label': uname + ' - ' + title,
            'path': plugin.url_for('video', id=item['bvid'], cid=cid, ispgc='false'),
            'is_playable': True,
            'icon': pic,
            'thumbnail': pic,
            'info': {
                'mediatype': 'video',
                'title': title,
                'duration': duration,
                'plot': plot
            },
            'info_type': 'video'
        }
    elif item[multi_key] > 1:
        label = parts_tag(item[multi_key]) + uname + ' - ' + title
        video = {
            'label': label,
            'path': plugin.url_for('videopages', id=bvid),
            'icon': pic,
            'thumbnail': pic,
            'info': {
                'plot': plot
            }
        }
    else:
        return
    return video


def parse_plot(item):
    plot = ''
    if 'upper' in item:
        plot += 'UP: ' + item['upper']['name'] + '\tID: ' + str(item['upper']['mid']) + '\n'
    elif 'owner' in item:
        plot += 'UP: ' + item['owner']['name'] + '\tID: ' + str(item['owner']['mid']) + '\n'
    elif 'author' in item:
        plot += 'UP: ' + item['author']
        if 'mid' in item:
            plot +='\tID: ' + str(item['mid'])
        plot += '\n'

    if 'bvid' in item:
        plot += item['bvid'] + '\n'

    if 'pubdate' in item:
        plot += timestamp_to_date(item['pubdate']) + '\n'

    if 'copyright' in item and str(item['copyright']) == '1':
        plot += '未经作者授权禁止转载\n'

    state = ''
    if 'stat' in item:
        stat = item['stat']
        if 'view' in stat:
            state += convert_number(stat['view']) + '播放 · '
        elif  'play' in stat:
            state += convert_number(stat['play']) + '播放 · '
        if 'like' in stat:
            state += convert_number(stat['like']) + '点赞 · '
        if 'coin' in stat:
            state += convert_number(stat['coin']) + '投币 · '
        if 'favorite' in stat:
            state += convert_number(stat['favorite']) + '收藏 · '
        if 'reply' in stat:
            state += convert_number(stat['reply']) + '评论 · '
        if 'danmaku' in stat:
            state += convert_number(stat['danmaku']) + '弹幕 · '
        if 'share' in stat:
            state += convert_number(stat['share']) + '分享 · '
    elif 'cnt_info' in item:
        stat = item['cnt_info']
        if 'play' in item:
            state += convert_number(stat['play']) + '播放 · '
        if 'collect' in stat:
            state += convert_number(stat['collect']) + '收藏 · '
        if 'danmaku' in stat:
            state += convert_number(stat['danmaku']) + '弹幕 · '
    else:
        if 'play' in item and isinstance(item['play'], int):
            state += convert_number(item['play']) + '播放 · '
        if 'comment' in item and isinstance(item['comment'], int):
            state += convert_number(item['comment']) + '评论 · '

    if state:
        plot += state[:-3] + '\n'
    plot += '\n'

    if 'achievement' in item and item['achievement']:
        plot += tag(item['achievement'], 'orange') + '\n\n'
    if 'rcmd_reason' in item and isinstance(item['rcmd_reason'], str) and item['rcmd_reason']:
        plot += '推荐理由：' + item['rcmd_reason'] + '\n\n'
    if 'desc' in item and item['desc']:
        plot += '简介: ' + item['desc']
    elif 'description' in item and item['description']:
        plot += '简介: ' + item['description']

    return plot


def choose_resolution(videos):
    videos = sorted(videos, key=lambda x: (x['id'], x['codecid']), reverse=True)
    current_id = int(getSetting('video_resolution'))
    current_codecid = int(getSetting('video_encoding'))

    filtered_videos = []
    max_id = 0
    for video in videos:
        if video['id'] > current_id:
            continue
        if video['id'] == current_id:
            filtered_videos.append(video)
        else:
            if (not filtered_videos) or video['id'] == max_id:
                filtered_videos.append(video)
                max_id = video['id']
            else:
                break
    if not filtered_videos:
        min_id = videos[-1]['id']
        for video in videos:
            if video['id'] == min_id:
                filtered_videos.append(video)


    final_videos = []
    max_codecid = 0
    for video in filtered_videos:
        if video['codecid'] > current_codecid:
            continue
        if video['codecid'] == current_codecid:
            final_videos.append(video)
        else:
            if (not final_videos) or video['codecid'] == max_codecid:
                final_videos.append(video)
                max_codecid = video['codecid']
            else:
                break
    if not final_videos:
        min_codecid = videos[-1]['codecid']
        for video in videos:
            if video['codecid'] == min_codecid:
                final_videos.append(video)

    return final_videos


def choose_live_resolution(streams):
    lives = []
    avc_lives = []
    hevc_lives = []
    for stream in streams:
        for format in stream['format']:
            for codec in format['codec']:
                live = {
                    'protocol_name': stream['protocol_name'],
                    'format_name': format['format_name'],
                    'codec_name': codec['codec_name'],
                    'current_qn': codec['current_qn'],
                    'url': codec['url_info'][0]['host'] + codec['base_url'] + codec['url_info'][0]['extra']
                }
                if codec['codec_name'] == 'avc':
                    avc_lives.append(live)
                elif codec['codec_name'] == 'hevc':
                    hevc_lives.append(live)
                lives.append(live)

    encoding = getSetting('live_video_encoding')
    if encoding == '12' and hevc_lives:
        hevc_lives = sorted(hevc_lives, key=lambda x: (x['current_qn']), reverse=True)
        return hevc_lives[0]['url']
    elif avc_lives:
        avc_lives = sorted(avc_lives, key=lambda x: (x['current_qn']), reverse=True)
        return avc_lives[0]['url']
    else:
        lives = sorted(lives, key=lambda x: (x['current_qn']), reverse=True)
        return lives[0]['url']


def parse_duration(duration_text):
    parts = duration_text.split(':')
    duration = 0
    for part in parts:
        duration = duration * 60 + int(part)
    return duration


@plugin.route('/remove_cache_files/')
def remove_cache_files():
    addon_id = 'plugin.video.bili'
    try:
        path = xbmc.translatePath('special://temp/%s' % addon_id).decode('utf-8')
    except AttributeError:
        path = xbmc.translatePath('special://temp/%s' % addon_id)

    if os.path.isdir(path):
        try:
            xbmcvfs.rmdir(path, force=True)
        except:
            pass
    if os.path.isdir(path):
        try:
            shutil.rmtree(path)
        except:
            pass

    if os.path.isdir(path):
        xbmcgui.Dialog().ok('提示', '清除失败')
        return False
    else:
        xbmcgui.Dialog().ok('提示', '清除成功')
        return True


@plugin.route('/check_login/')
def check_login():
    if not get_cookie():
        xbmcgui.Dialog().ok('提示', '账号未登录')
        return
    res = apiGet('/x/web-interface/nav/stat')
    if res['code'] == 0:
        xbmcgui.Dialog().ok('提示', '登录成功')
    elif res['code'] == -101:
        xbmcgui.Dialog().ok('提示', '账号未登录')
    else:
        xbmcgui.Dialog().ok('提示', res.get('message', '未知错误'))


@plugin.route('/logout/')
def logout():
    account = plugin.get_storage('account')
    account['cookie'] = ''
    plugin.clear_function_cache()
    xbmcgui.Dialog().ok('提示', '退出成功')


@plugin.route('/cookie_login/')
def cookie_login():
    keyboard = xbmc.Keyboard('', '请输入 Cookie')
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        cookie = keyboard.getText().strip()
        if not cookie:
            return
    else:
        return
    account = plugin.get_storage('account')
    account['cookie'] = cookie
    plugin.clear_function_cache()
    xbmcgui.Dialog().ok('提示', 'Cookie 设置成功')


@plugin.route('/qrcode_login/')
def qrcode_login():
    temp_path = get_temp_path()
    temp_path = os.path.join(temp_path, 'login.png')
    if not temp_path:
        notify('提示', '无法创建文件夹')
        return
    try:
        res = requests.get('https://passport.bilibili.com/x/passport-login/web/qrcode/generate').json()
    except:
        notify('提示', '二维码获取失败')
        return
    if res['code'] != 0:
        notify_error(res)

    login_path = res['data']['url']
    key = res['data']['qrcode_key']
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=20
    )
    qr.add_data(login_path)
    qr.make(fit=True)
    img = qr.make_image()
    img.save(temp_path)
    xbmc.executebuiltin('ShowPicture(%s)' % temp_path)
    polling_login_status(key)


def polling_login_status(key):
    session = requests.Session()
    for i in range(50):
        try:
            response = session.get('https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key=' + key)
            check_result = response.json()
        except:
            time.sleep(3)
            continue
        if check_result['code'] != 0:
            xbmc.executebuiltin('Action(Back)')
            return
        if check_result['data']['code'] == 0:
            account = plugin.get_storage('account')
            cookies = session.cookies
            cookies = ' '.join([cookie.name + '=' + cookie.value + ';' for cookie in cookies])
            xbmc.log('set-cookie: ' + cookies)
            account['cookie'] = cookies
            plugin.clear_function_cache()
            xbmcgui.Dialog().ok('提示', '登录成功')
            xbmc.executebuiltin('Action(Back)')
            return
        elif check_result['data']['code'] == 86038:
            notify('提示', '二维码已失效')
            xbmc.executebuiltin('Action(Back)')
            return
        time.sleep(3)
    xbmc.executebuiltin('Action(Back)')


def generate_mpd(dash):
    videos = choose_resolution(dash['video'])
    audios = dash['audio']

    list = [
        '<?xml version="1.0" encoding="UTF-8"?>\n',
        '<MPD xmlns="urn:mpeg:dash:schema:mpd:2011" profiles="urn:mpeg:dash:profile:isoff-on-demand:2011" type="static" mediaPresentationDuration="PT', str(dash['duration']), 'S" minBufferTime="PT', str(dash['minBufferTime']), 'S">\n',
        '\t<Period>\n'
    ]

    # video
    list.append('\t\t<AdaptationSet mimeType="video/mp4" startWithSAP="1" scanType="progressive" segmentAlignment="true">\n')
    for video in videos:
        list.extend([
            '\t\t\t<Representation bandwidth="', str(video['bandwidth']), '" codecs="', video['codecs'], '" frameRate="', video['frameRate'], '" height="', str(video['height']), '" width="', str(video['width']), '" id="', str(video['id']), '">\n',
            '\t\t\t\t<BaseURL>', video['baseUrl'].replace('&', '&amp;'), '</BaseURL>\n',
            '\t\t\t\t<SegmentBase indexRange="', video['SegmentBase']['indexRange'], '">\n',
            '\t\t\t\t\t<Initialization range="' + video['SegmentBase']['Initialization'] + '"></Initialization>\n',
            '\t\t\t\t</SegmentBase>\n',
            '\t\t\t</Representation>\n'
        ])
    list.append('\t\t</AdaptationSet>\n')

    # audio
    list.append('\t\t<AdaptationSet mimeType="audio/mp4" startWithSAP="1" segmentAlignment="true" lang="und">\n')
    for audio in audios:
        list.extend([
            '\t\t\t<Representation audioSamplingRate="44100" bandwidth="', str(audio['bandwidth']), '" codecs="', audio['codecs'], '" id="', str(audio['id']), '">\n',
            '\t\t\t\t<BaseURL>', audio['baseUrl'].replace('&', '&amp;'), '</BaseURL>\n',
            '\t\t\t\t<SegmentBase indexRange="', audio['SegmentBase']['indexRange'], '">\n',
            '\t\t\t\t\t<Initialization range="' + audio['SegmentBase']['Initialization'] + '"></Initialization>\n',
            '\t\t\t\t</SegmentBase>\n',
            '\t\t\t</Representation>\n'
        ])
    list.append('\t\t</AdaptationSet>\n')

    list.append('\t</Period>\n</MPD>\n')

    return ''.join(list)

def generate_ass(cid):
    basepath = xbmc.translatePath('special://temp/plugin.video.bili/')
    if not make_dirs(basepath):
        return
    xmlfile = os.path.join(basepath, str(cid) + '.xml')
    assfile = os.path.join(basepath, str(cid) + '.ass')
    if xbmcvfs.exists(assfile):
        return assfile
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'
    }

    try:
        res = requests.get('https://comment.bilibili.com/' + str(cid) + '.xml', headers=headers)
        res.encoding = 'utf-8'
        content = res.text
    except:
        return
    with xbmcvfs.File(xmlfile, 'w') as f:
        success = f.write(content)
    if not success:
        return
    font_size = float(getSetting('font_size'))
    text_opacity = float(getSetting('opacity'))
    duration = float(getSetting('danmaku_stay_time'))
    width = 1920
    height = 540
    reserve_blank = int((1.0 - float(getSetting('display_area'))) * height)
    Danmaku2ASS(xmlfile, 'autodetect' , assfile, width, height, reserve_blank=reserve_blank,font_size=font_size, text_opacity=text_opacity,duration_marquee=duration,duration_still=duration)
    if xbmcvfs.exists(assfile):
        return assfile


def make_dirs(path):
    if not path.endswith('/'):
        path = ''.join([path, '/'])
    path = xbmc.translatePath(path)
    if not xbmcvfs.exists(path):
        try:
            _ = xbmcvfs.mkdirs(path)
        except:
            pass
        if not xbmcvfs.exists(path):
            try:
                os.makedirs(path)
            except:
                pass
        return xbmcvfs.exists(path)

    return True


def get_temp_path():
    temppath = xbmc.translatePath('special://temp/plugin.video.bili/')
    if not make_dirs(temppath):
        return
    return temppath


def get_cookie():
    account = plugin.get_storage('account')
    if 'cookie' in account:
        return account['cookie']
    return ''


def get_cookie_value(key):
    cookie = get_cookie()
    if key in cookie:
        return cookie.split(key + '=')[1].split(';')[0]
    return ''

def get_uid():
    return get_cookie_value('DedeUserID') or '0'


def post(url, data):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    cookie = get_cookie()
    if cookie:
        headers['Cookie'] = cookie
    try:
        res = requests.post(url, data=data, headers=headers).json()
    except Exception as e:
        res = {'code': -1, 'message': '网络错误'}
    return res


def get(url):
    xbmc.log('url_get: ' + url)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36',
        'Referer': 'https://www.bilibili.com',
    }
    cookie = get_cookie()
    if cookie:
        headers['Cookie'] = cookie
    try:
        res = requests.get(url, headers=headers).json()
    except Exception as e:
        res = {'code': -1, 'message': '网络错误'}
    return res


@plugin.cached(TTL=1)
def cachedGet(url):
    return get(url)


def apiGet(url, data={}):
    url = 'https://api.bilibili.com' + url
    if data:
        url += '?' + urlencode(data)
    return get(url)


def cachedApiGet(url, data={}):
    url = 'https://api.bilibili.com' + url
    if data:
        url += '?' + urlencode(data)
    return cachedGet(url)

@plugin.route('/')
def index():
    items = []
    if getSetting('function.home') == 'true':
        items.append({
            'label': localize(30101),
            'path': plugin.url_for('home', page=1),
        })
    if getSetting('function.dynamic_list') == 'true':
        items.append({
            'label': localize(30102),
            'path': plugin.url_for('dynamic_list'),
        })
    if getSetting('function.ranking_list') == 'true':
        items.append({
            'label': localize(30103),
            'path': plugin.url_for('ranking_list'),
        })
    if getSetting('function.popular_weekly') == 'true':
        items.append({
            'label': localize(30114),
            'path': plugin.url_for('popular_weekly'),
        })
    if getSetting('function.popular_history') == 'true':
        items.append({
            'label': localize(30115),
            'path': plugin.url_for('popular_history'),
        })
    if getSetting('function.live_areas') == 'true':
        items.append({
            'label': localize(30104),
            'path': plugin.url_for('live_areas', level=1, id=0),
        })
    if getSetting('function.followingLive') == 'true':
        items.append({
            'label': localize(30105),
            'path': plugin.url_for('followingLive', page=1),
        })
    if getSetting('function.my') == 'true':
        items.append({
            'label': localize(30106),
            'path': plugin.url_for('my'),
        })
    if getSetting('function.web_dynamic') == 'true':
        items.append({
            'label': localize(30107),
            'path': plugin.url_for('web_dynamic', page=1, offset=0),
        })
    if getSetting('function.followings') == 'true':
        items.append({
            'label': localize(30108),
            'path': plugin.url_for('followings', id=get_uid(), page=1),
        })
    if getSetting('function.followers') == 'true':
        items.append({
            'label': localize(30109),
            'path': plugin.url_for('followers', id=get_uid(), page=1),
        })
    if getSetting('function.watchlater') == 'true':
        items.append({
            'label': localize(30110),
            'path': plugin.url_for('watchlater', page=1),
        })
    if getSetting('function.history') == 'true':
        items.append({
            'label': localize(30111),
            'path': plugin.url_for('history', time=0),
        })
    if getSetting('function.space_videos') == 'true':
        items.append({
            'label': localize(30112),
            'path': plugin.url_for('space_videos', id=get_uid(), page=1),
        })
    if getSetting('function.search_list') == 'true':
        items.append({
            'label': localize(30113),
            'path': plugin.url_for('search_list'),
        })
    if getSetting('function.open_settings') == 'true':
        items.append({
            'label': localize(30116),
            'path': plugin.url_for('open_settings'),
        })

    return items


@plugin.route('/open_settings/')
def open_settings():
    plugin.open_settings()


@plugin.route('/popular_history/')
def popular_history():
    videos = []
    res = cachedApiGet('/x/web-interface/popular/precious')
    if res['code'] != 0:
        return videos
    list = res['data']['list']
    for item in list:
        video = get_video_item(item)
        if video:
            videos.append(video)
    return videos


@plugin.route('/popular_weekly/')
def popular_weekly():
    categories = []
    res = cachedApiGet('/x/web-interface/popular/series/list')
    if res['code'] != 0:
        return categories
    list = res['data']['list']
    for item in list:
        categories.append({
            'label': item['name'] + ' ' + item['subject'],
            'path':plugin.url_for('weekly', number = item['number']),
        })
    return categories


@plugin.route('/weekly/<number>/')
def weekly(number):
    videos = []
    res = cachedApiGet('/x/web-interface/popular/series/one', {'number': number})
    if res['code'] != 0:
        return videos
    list = res['data']['list']
    for item in list:
        video = get_video_item(item)
        if video:
            videos.append(video)
    return videos

@plugin.route('/space_videos/<id>/<page>/')
def space_videos(id, page):
    videos = []
    if id == '0':
        notify('提示', '未设置 uid')
        return videos
    ps = 50
    data = {
        'mid': id,
        'ps': ps,
        'pn': page,
        'order': 'pubdate',
        'tid': 0,
        'keyword': '',
        'platform': 'web'
    }
    res = cachedApiGet('/x/space/wbi/arc/search', data)
    if res['code'] != 0:
        notify_error(res)
        return videos

    list = res['data']['list']['vlist']
    for item in list:
        video = get_video_item(item)
        if video:
            videos.append(video)
    if int(page) * ps < res['data']['page']['count']:
        videos.append({
            'label': tag('下一页', 'yellow'),
            'path': plugin.url_for('space_videos', id=id, page=int(page) + 1),
        })
    return videos


@plugin.route('/followings/<id>/<page>/')
def followings(id, page):
    users = []
    if id == '0':
        notify('提示', '未设置 uid')
        return users
    ps = 50
    data = {
        'vmid': id,
        'ps': ps,
        'pn': page,
        'order': 'desc',
        'order_type': 'attention'
    }
    res = cachedApiGet('/x/relation/followings', data)
    if res['code'] != 0:
        notify_error(res)
        return users
    list = res['data']['list']
    for item in list:
        # 0: 非会员 1: 月度大会员 2: 年度以上大会员
        if item['vip']['vipType'] == 0:
            uname = item['uname']
        else:
            uname = tag(item['uname'], 'pink')
        user = {
            'label': uname,
            'path': plugin.url_for('user', id=item['mid']),
            'icon': item['face'],
            'thumbnail': item['face'],
            'info': {
                'plot': 'UP:' + item['uname'] + '\tID: ' + str(item['mid']) + '\n'  + '签名: ' + item['sign']
            },
        }
        users.append(user)
    if int(page) * 50 < res['data']['total']:
        users.append({
            'label': tag('下一页', 'yellow'),
            'path': plugin.url_for('followings', id=id, page=int(page) + 1),
        })
    return users


@plugin.route('/followers/<id>/<page>/')
def followers(id, page):
    users = []
    if id == '0':
        notify('提示', '未设置 uid')
        return users
    ps = 50
    data = {
        'vmid': id,
        'ps': ps,
        'pn': page,
        'order': 'desc',
        'order_type': 'attention'
    }
    res = cachedApiGet('/x/relation/followers', data)
    if res['code'] != 0:
        notify_error(res)
        return users
    list = res['data']['list']
    for item in list:
        # 0: 非会员 1: 月度大会员 2: 年度以上大会员
        if item['vip']['vipType'] == 0:
            uname = item['uname']
        else:
            uname = tag(item['uname'], 'pink')
        user = {
            'label': uname,
            'path': plugin.url_for('user', id=item['mid']),
            'icon': item['face'],
            'thumbnail': item['face'],
            'info': {
                'plot': 'UP:' + item['uname'] + '\tID: ' + str(item['mid']) + '\n'  + '签名: ' + item['sign']
            },
        }
        users.append(user)
    if int(page) * 50 < res['data']['total']:
        users.append({
            'label': tag('下一页', 'yellow'),
            'path': plugin.url_for('followings', id=id, page=int(page) + 1),
        })
    return users


@plugin.route('/user/<id>/')
def user(id):
    return [
        {
            'label': '投稿的视频',
            'path': plugin.url_for('space_videos', id=id, page=1),
        },
        {
            'label': '合集和列表',
            'path': plugin.url_for('seasons_series', uid=id, page=1),
        },
        {
            'label': '关注列表',
            'path': plugin.url_for('followings', id=id, page=1),
        },
        {
            'label': '粉丝列表',
            'path': plugin.url_for('followers', id=get_uid(), page=1),
        },
        {
            'label': 'TA的订阅',
            'path': plugin.url_for('his_subscription', id=id),
        },
    ]



@plugin.route('/seasons_series/<uid>/<page>/')
def seasons_series(uid, page):
    collections = []
    ps = 20
    data = {
        'mid': uid,
        'page_num': page,
        'page_size': ps
    }
    res = cachedApiGet('/x/polymer/web-space/seasons_series_list', data)
    if res['code'] != 0:
        notify_error(res)
        return collections
    list = res['data']['items_lists']['seasons_list']
    for item in list:
        collections.append({
            'label': item['meta']['name'],
            'path': plugin.url_for('seasons_and_series_detail', uid=uid, id=item['meta']['season_id'], type='season', page=1),
            'icon': item['meta']['cover'],
            'thumbnail': item['meta']['cover']
        })
    list = res['data']['items_lists']['series_list']
    for item in list:
        collections.append({
            'label': item['meta']['name'],
            'path': plugin.url_for('seasons_and_series_detail', uid=uid, id=item['meta']['series_id'], type='series', page=1),
            'icon': item['meta']['cover'],
            'thumbnail': item['meta']['cover']
        })
    if res['data']['items_lists']['page']['page_num'] * res['data']['items_lists']['page']['page_size'] < res['data']['items_lists']['page']['total']:
        collections.append({
            'label': tag('下一页', 'yellow'),
            'path': plugin.url_for('seasons_series', uid=uid, page=int(page)+1)
        })
    return collections


@plugin.route('/seasons_and_series_detail/<uid>/<id>/<type>/<page>/')
def seasons_and_series_detail(id, uid, type, page):
    videos = []
    ps = 100
    if type == 'season':
        url = '/x/polymer/space/seasons_archives_list'
        data = {
            'mid': uid,
            'season_id': id,
            'sort_reverse': False,
            'page_size': ps,
            'page_num': page
        }
    else:
        url = '/x/series/archives'
        data = {
            'mid': uid,
            'series_id': id,
            'sort': 'desc',
            'ps': ps,
            'pn': page
        }
    res = cachedApiGet(url, data)
    if res['code'] != 0:
        return videos
    list = res['data']['archives']
    for item in list:
        video = {
            'label': item['title'],
            'path': plugin.url_for('video', id=item['bvid'], cid=0, ispgc='false'),
            'is_playable': True,
            'icon': item['pic'],
            'thumbnail': item['pic'],
            'info': {
                'mediatype': 'video',
                'title': item['title'],
                'duration': item['duration']
            },
            'info_type': 'video',
        }
        videos.append(video)
    if type == 'season':
        if res['data']['page']['page_num'] * res['data']['page']['page_size'] < res['data']['page']['total']:
            videos.append({
                'label': tag('下一页', 'yellow'),
                'path': plugin.url_for('seasons_and_series_detail', uid=uid, id=id, type=type, page=int(page)+1)
            })
    else:
        if res['data']['page']['num'] * res['data']['page']['size'] < res['data']['page']['total']:
            videos.append({
                'label': tag('下一页', 'yellow'),
                'path': plugin.url_for('seasons_and_series_detail', uid=uid, id=id, type=type, page=int(page)+1)
            })
    return videos


@plugin.route('/his_subscription/<id>/')
def his_subscription(id):
    return [
        {
            'label': '追番',
            'path': plugin.url_for('fav_series', uid=id, type=1)
        },
        {
            'label': '追剧',
            'path': plugin.url_for('fav_series', uid=id, type=2)
        },
    ]


@plugin.route('/search_list/')
def search_list():
    return [
        {
            'label': '综合搜索',
            'path': plugin.url_for('search', type='all', page=1)
        },
        {
            'label': '视频搜索',
            'path': plugin.url_for('search', type='video', page=1)
        },
        {
            'label': '番剧搜索',
            'path': plugin.url_for('search', type='media_bangumi', page=1)
        },
        {
            'label': '影视搜索',
            'path': plugin.url_for('search', type='media_ft', page=1)
        },
        {
            'label': '用户搜索',
            'path': plugin.url_for('search', type='bili_user', page=1)
        },
    ]


def get_search_list(list):
    videos = []
    for item in list:
        if item['type'] == 'video':
            plot = parse_plot(item)
            video = {
                'label': item['author'] + ' - ' + clear_text(item['title']),
                'path': plugin.url_for('video', id=item['bvid'], cid=0, ispgc='false'),
                'is_playable': True,
                'icon': item['pic'],
                'thumbnail': item['pic'],
                'info': {
                    'mediatype': 'video',
                    'title': clear_text(item['title']),
                    'duration': parse_duration(item['duration']),
                    'plot': plot
                },
                'info_type': 'video',
            }
        elif item['type'] == 'media_bangumi' or item['type'] == 'media_ft':
            if item['type'] == 'media_bangumi':
                cv_type = '声优'
            else:
                cv_type = '出演'
            plot = tag(clear_text(item['title']), 'pink') + ' ' + item['index_show'] + '\n\n'
            plot += '地区: ' + item['areas'] + '\n'
            plot += cv_type + ': ' + clear_text(item['cv']).replace('\n', '/') + '\n'
            plot += item['staff'] + '\n'
            plot += '\n'
            plot += item['desc']
            video = {
                'label': tag('【' + item['season_type_name'] + '】', 'pink') + clear_text(item['title']),
                'path': plugin.url_for('bangumi', type='season_id' ,id=item['season_id']),
                'icon': item['cover'],
                'thumbnail': item['cover'],
                'info': {
                    'plot': plot
                }
            }
        elif item['type'] == 'bili_user':
            plot = 'UP: ' + item['uname'] + '\tLV' + str(item['level']) + '\n'
            plot += 'ID: ' + str(item['mid']) + '\n'
            plot += '粉丝: ' + str(convert_number(item['fans'])) + '\n\n'
            plot += '签名: ' + item['usign'] + '\n'
            video = {
                'label': tag('【用户】') + item['uname'],
                'path': plugin.url_for('user', id=item['mid']),
                'icon': item['upic'],
                'thumbnail': item['upic'],
                'info': {
                    'plot': plot
                }
            }
        else:
            continue
        videos.append(video)
    return videos


@plugin.route('/search/<type>/<page>/')
def search(type, page):
    videos = []
    keyboard = xbmc.Keyboard('', '请输入搜索内容')
    keyboard.doModal()
    if (keyboard.isConfirmed()):
        keyword = keyboard.getText()
    else:
        return videos

    if not keyword.strip():
        return videos
    return search_by_keyword(type, keyword, page)


@plugin.route('/search_by_keyword/<type>/<keyword>/<page>/')
def search_by_keyword(type, keyword, page):
    videos = []
    data = {
        'page': page,
        'page_size': 50,
        'platform': 'pc',
        'keyword': keyword,
    }

    if type == 'all':
        url = '/x/web-interface/wbi/search/all/v2'
    else:
        url = '/x/web-interface/wbi/search/type'
        data['search_type'] = type
    res = cachedApiGet(url, data)
    if res['code'] != 0:
        return videos
    if 'result' not in res['data']:
        return videos
    list = res['data']['result']
    if type == 'all':
        for result in list:
            if result['result_type'] in ['video', 'media_bangumi', 'media_ft', 'bili_user']:
                videos.extend(get_search_list(result['data']))
    else:
        videos.extend(get_search_list(list))
    if res['data']['page'] < res['data']['numPages']:
        videos.append({
            'label': tag('下一页', 'yellow'),
            'path': plugin.url_for('search_by_keyword', type=type, keyword=keyword , page=int(page)+1)
        })
    return videos


@plugin.route('/live_areas/<level>/<id>/')
def live_areas(level, id):
    areas = {'2': {'id': '2', 'name': '网游', 'list': [{'id': '86', 'name': '英雄联盟'}, {'id': '92', 'name': 'DOTA2'}, {'id': '89', 'name': 'CS:GO'}, {'id': '240', 'name': 'APEX英雄'}, {'id': '666', 'name': '永劫无间'}, {'id': '88', 'name': '穿越火线'}, {'id': '87', 'name': '守望先锋'}, {'id': '80', 'name': '吃鸡行动'}, {'id': '252', 'name': '逃离塔科夫'}, {'id': '695', 'name': '传奇'}, {'id': '78', 'name': 'DNF'}, {'id': '575', 'name': '生死狙击2'}, {'id': '599', 'name': '洛奇英雄传'}, {'id': '102', 'name': '最终幻想14'}, {'id': '249', 'name': '星际战甲'}, {'id': '710', 'name': '梦三国'}, {'id': '690', 'name': '英魂之刃'}, {'id': '82', 'name': '剑网3'}, {'id': '691', 'name': '铁甲雄兵'}, {'id': '300', 'name': '封印者'}, {'id': '653', 'name': '新天龙八部'}, {'id': '667', 'name': '赛尔号'}, {'id': '668', 'name': '造梦西游'}, {'id': '669', 'name': '洛克王国'}, {'id': '670', 'name': '问道'}, {'id': '654', 'name': '诛仙世界'}, {'id': '652', 'name': '大话西游'}, {'id': '683', 'name': '奇迹MU'}, {'id': '684', 'name': '永恒之塔'}, {'id': '685', 'name': 'QQ三国'}, {'id': '677', 'name': '人间地狱'}, {'id': '329', 'name': 'VALORANT'}, {'id': '686', 'name': '彩虹岛'}, {'id': '663', 'name': '洛奇'}, {'id': '664', 'name': '跑跑卡丁车'}, {'id': '658', 'name': '星际公民'}, {'id': '659', 'name': 'Squad战术小队'}, {'id': '629', 'name': '反恐精英Online'}, {'id': '648', 'name': '风暴奇侠'}, {'id': '642', 'name': '装甲战争'}, {'id': '590', 'name': '失落的方舟'}, {'id': '639', 'name': '阿尔比恩'}, {'id': '600', 'name': '猎杀对决'}, {'id': '472', 'name': 'CFHD '}, {'id': '650', 'name': '骑士精神2'}, {'id': '680', 'name': '超击突破'}, {'id': '634', 'name': '武装突袭'}, {'id': '84', 'name': '300英雄'}, {'id': '91', 'name': '炉石传说'}, {'id': '499', 'name': '剑网3缘起'}, {'id': '649', 'name': '街头篮球'}, {'id': '601', 'name': '综合射击'}, {'id': '505', 'name': '剑灵'}, {'id': '651', 'name': '艾尔之光'}, {'id': '632', 'name': '黑色沙漠'}, {'id': '596', 'name': ' 天涯明月刀'}, {'id': '519', 'name': '超激斗梦境'}, {'id': '574', 'name': '冒险岛'}, {'id': '487', 'name': '逆战'}, {'id': '181', 'name': '魔兽争霸3'}, {'id': '610', 'name': 'QQ飞车'}, {'id': '83', 'name': '魔兽世界'}, {'id': '388', 'name': 'FIFA ONLINE 4'}, {'id': '581', 'name': 'NBA2KOL2'}, {'id': '318', 'name': '使命召唤:战区'}, {'id': '656', 'name': 'VRChat'}, {'id': '115', 'name': '坦克世界'}, {'id': '248', 'name': '战舰世界'}, {'id': '316', 'name': '战争雷霆'}, {'id': '383', 'name': '战意'}, {'id': '114', 'name': '风暴英雄'}, {'id': '93', 'name': '星际争霸2'}, {'id': '239', 'name': '刀塔自走 棋'}, {'id': '164', 'name': '堡垒之夜'}, {'id': '251', 'name': '枪神纪'}, {'id': '81', 'name': '三国杀'}, {'id': '112', 'name': '龙之谷'}, {'id': '173', 'name': '古剑奇谭OL'}, {'id': '176', 'name': '幻想全明星'}, {'id': '288', 'name': '怀旧网游'}, {'id': '298', 'name': '新游前瞻'}, {'id': '331', 'name': '星战前夜：晨曦'}, {'id': '350', 'name': '梦幻西游端游'}, {'id': '551', 'name': '流放之路'}, {'id': '633', 'name': 'FPS沙盒'}, {'id': '459', 'name': '永恒轮回'}, {'id': '607', 'name': '激战2'}, {'id': '107', 'name': '其他网游'}]}, '3': {'id': '3', 'name': '手游', 'list': [{'id': '35', 'name': '王者荣耀'}, {'id': '256', 'name': '和平精英'}, {'id': '395', 'name': 'LOL手游'}, {'id': '321', 'name': '原神'}, {'id': '163', 'name': '第五人格'}, {'id': '255', 'name': '明日方舟'}, {'id': '474', 'name': '哈利波特：魔法觉醒 '}, {'id': '550', 'name': '幻塔'}, {'id': '514', 'name': '金铲铲之战'}, {'id': '506', 'name': 'APEX手游'}, {'id': '598', 'name': '深空之眼'}, {'id': '675', 'name': '无期迷途'}, {'id': '687', 'name': '光遇'}, {'id': '717', 'name': '跃迁旅人'}, {'id': '725', 'name': '环形战争'}, {'id': '689', 'name': '香肠派对'}, {'id': '645', 'name': '猫之城'}, {'id': '644', 'name': '玛娜希斯回响'}, {'id': '386', 'name': '使命召唤手游'}, {'id': '615', 'name': '黑色沙漠手游'}, {'id': '40', 'name': '崩坏3'}, {'id': '407', 'name': '游戏王：决斗链接'}, {'id': '303', 'name': '游戏王'}, {'id': '724', 'name': 'JJ斗地主'}, {'id': '571', 'name': '蛋仔派对'}, {'id': '36', 'name': '阴阳师'}, {'id': '719', 'name': '欢乐斗地主'}, {'id': '718', 'name': '空之要塞：启航'}, {'id': '292', 'name': '火影忍者手游'}, {'id': '37', 'name': 'Fate/GO'}, {'id': '354', 'name': '综合棋牌'}, {'id': '154', 'name': 'QQ飞车手游'}, {'id': '140', 'name': '决战！平安京'}, {'id': '41', 'name': '狼人杀'}, {'id': '352', 'name': '三国杀移动版'}, {'id': '113', 'name': '碧蓝航线'}, {'id': '156', 'name': '影之诗'}, {'id': '189', 'name': '明日之后'}, {'id': '50', 'name': '部落冲突: 皇室战争'}, {'id': '661', 'name': '奥比岛手游'}, {'id': '704', 'name': '盾之勇者成名录：浪潮'}, {'id': '214', 'name': '雀姬'}, {'id': '330', 'name': ' 公主连结Re:Dive'}, {'id': '343', 'name': 'DNF手游'}, {'id': '641', 'name': 'FIFA足球世界'}, {'id': '258', 'name': 'BanG Dream'}, {'id': '469', 'name': '荒野乱斗'}, {'id': '333', 'name': 'CF手游'}, {'id': '293', 'name': '战双帕弥什'}, {'id': '389', 'name': '天涯明月刀手游'}, {'id': '42', 'name': '解密 游戏'}, {'id': '576', 'name': '恋爱养成游戏'}, {'id': '492', 'name': '暗黑破坏神：不朽'}, {'id': '502', 'name': '暗区突围'}, {'id': '265', 'name': '跑 跑卡丁车手游'}, {'id': '212', 'name': '非人学园'}, {'id': '286', 'name': '百闻牌'}, {'id': '269', 'name': '猫和老鼠手游'}, {'id': '442', 'name': '坎公 骑冠剑'}, {'id': '203', 'name': '忍者必须死3'}, {'id': '342', 'name': '梦幻西游手游'}, {'id': '504', 'name': '航海王热血航线'}, {'id': '39', 'name': ' 少女前线'}, {'id': '688', 'name': '300大作战'}, {'id': '525', 'name': '少女前线：云图计划'}, {'id': '478', 'name': '漫威超级战争'}, {'id': '464', 'name': '摩尔庄园手游'}, {'id': '493', 'name': '宝可梦大集结'}, {'id': '473', 'name': '小动物之星'}, {'id': '448', 'name': '天地劫：幽城再临'}, {'id': '511', 'name': '漫威对决'}, {'id': '538', 'name': ' 东方归言录'}, {'id': '178', 'name': '梦幻模拟战'}, {'id': '643', 'name': '时空猎人3'}, {'id': '613', 'name': '重返帝国'}, {'id': '679', 'name': '休闲小游戏'}, {'id': '98', 'name': '其他手游'}, {'id': '274', 'name': '新游评测'}]}, '6': {'id': '6', 'name': '单机游戏', 'list': [{'id': '236', 'name': '主机游戏'}, {'id': '579', 'name': '战神'}, {'id': '216', 'name': '我的世界'}, {'id': '726', 'name': '大多数'}, {'id': '283', 'name': '独立游戏'}, {'id': '237', 'name': '怀旧游戏'}, {'id': '460', 'name': '弹幕互动玩法'}, {'id': '722', 'name': '互动派对'}, {'id': '276', 'name': '恐怖游戏'}, {'id': '693', 'name': '红色警戒2'}, {'id': '570', 'name': '策略游戏'}, {'id': '723', 'name': '战锤40K:暗潮'}, {'id': '707', 'name': '禁闭求生'}, {'id': '694', 'name': '斯普拉遁3'}, {'id': '700', 'name': '卧龙：苍天陨落'}, {'id': '282', 'name': '使命召唤19'}, {'id': '665', 'name': '异度神剑'}, {'id': '555', 'name': '艾尔登法环'}, {'id': '636', 'name': '聚会游戏'}, {'id': '716', 'name': '哥谭骑士'}, {'id': '277', 'name': '命运2'}, {'id': '630', 'name': '沙石镇时光'}, {'id': '591', 'name': 'Dread Hunger'}, {'id': '721', 'name': '生化危机'}, {'id': '714', 'name': '失落 迷城：群星的诅咒'}, {'id': '597', 'name': '战地风云'}, {'id': '720', 'name': '宝可梦集换式卡牌游戏'}, {'id': '612', 'name': '幽灵线：东京'}, {'id': '357', 'name': '糖豆人'}, {'id': '586', 'name': '消逝的光芒2'}, {'id': '245', 'name': '只狼'}, {'id': '578', 'name': '怪物猎人'}, {'id': '218', 'name': ' 饥荒'}, {'id': '228', 'name': '精灵宝可梦'}, {'id': '708', 'name': 'FIFA23'}, {'id': '582', 'name': '暖雪'}, {'id': '594', 'name': '全面战争：战锤3'}, {'id': '580', 'name': '彩虹六号：异种'}, {'id': '302', 'name': 'FORZA 极限竞速'}, {'id': '362', 'name': 'NBA2K'}, {'id': '548', 'name': '帝国时代4'}, {'id': '559', 'name': '光环：无限'}, {'id': '537', 'name': '孤岛惊魂6'}, {'id': '309', 'name': '植物大战僵尸'}, {'id': '540', 'name': '仙剑奇侠传七'}, {'id': '223', 'name': '灵魂筹码'}, {'id': '433', 'name': '格斗游戏'}, {'id': '226', 'name': '荒野大镖客2'}, {'id': '426', 'name': '重生细胞'}, {'id': '227', 'name': '刺客信条'}, {'id': '387', 'name': '恐鬼症'}, {'id': '219', 'name': '以撒'}, {'id': '446', 'name': '双人成行'}, {'id': '295', 'name': '方 舟'}, {'id': '313', 'name': '仁王2'}, {'id': '244', 'name': '鬼泣5'}, {'id': '727', 'name': '黑白莫比乌斯 岁月的代价'}, {'id': '364', 'name': '枪火重生'}, {'id': '341', 'name': '盗贼之海'}, {'id': '507', 'name': '胡闹厨房'}, {'id': '500', 'name': '体育游戏'}, {'id': '439', 'name': '恐惧之间'}, {'id': '308', 'name': '塞尔达'}, {'id': '261', 'name': '马力欧制造2'}, {'id': '243', 'name': '全境封锁2'}, {'id': '326', 'name': '骑马与砍杀'}, {'id': '270', 'name': '人类一败涂地'}, {'id': '424', 'name': '鬼谷八荒'}, {'id': '273', 'name': '无主之地3'}, {'id': '220', 'name': '辐射76'}, {'id': '257', 'name': '全面战争'}, {'id': '463', 'name': '亿万僵尸'}, {'id': '535', 'name': '暗黑破坏神2'}, {'id': '583', 'name': '文字游戏'}, {'id': '592', 'name': '恋爱模 拟游戏'}, {'id': '593', 'name': '泰拉瑞亚'}, {'id': '441', 'name': '雨中冒险2'}, {'id': '678', 'name': '游戏速通'}, {'id': '681', 'name': '摔角城大乱斗'}, {'id': '692', 'name': '勇敢的哈克'}, {'id': '698', 'name': ' 审判系列'}, {'id': '728', 'name': '蜀山：初章'}, {'id': '235', 'name': '其他单机'}]}, '1': {'id': '1', 'name': '娱乐', 'list': [{'id': '21', 'name': '视频唱见'}, {'id': '530', 'name': '萌宅领域'}, {'id': '145', 'name': '视频聊天'}, {'id': '207', 'name': '舞见'}, {'id': '706', 'name': '情感'}, {'id': '123', 'name': '户外'}, {'id': '399', 'name': '日常'}]}, '5': {'id': '5', 'name': '电台', 'list': [{'id': '190', 'name': '唱见电台'}, {'id': '192', 'name': '聊天电台'}, {'id': '193', 'name': '配音'}]}, '9': {'id': '9', 'name': '虚拟主播', 'list': [{'id': '371', 'name': '虚拟主播'}, {'id': '697', 'name': '3D虚拟主播'}]}, '10': {'id': '10', 'name': '生活', 'list': [{'id': '646', 'name': '生活分享'}, {'id': '628', 'name': '运动'}, {'id': '624', 'name': '搞笑'}, {'id': '627', 'name': '手工绘画'}, {'id': '369', 'name': '萌宠'}, {'id': '367', 'name': '美食'}, {'id': '378', 'name': '时尚'}, {'id': '33', 'name': '影音馆'}]}, '11': {'id': '11', 'name': '知识', 'list': [{'id': '376', 'name': '社科法律心理'}, {'id': '702', 'name': '人文历史'}, {'id': '372', 'name': '校园学习'}, {'id': '377', 'name': '职场·技能'}, {'id': '375', 'name': ' 科技'}, {'id': '701', 'name': '科学科普'}]}, '13': {'id': '13', 'name': '赛事', 'list': [{'id': '561', 'name': '游戏赛事'}, {'id': '562', 'name': '体育赛事'}, {'id': '563', 'name': '赛事综合'}]}}
    if level == '1':
        return [{
            'label': areas[area_id]['name'],
            'path': plugin.url_for('live_areas', level=2, id=area_id),
        } for area_id in areas]

    childran_areas = areas[id]['list']
    items = [{
        'label': areas[id]['name'],
        'path': plugin.url_for('live_area', pid=id, id=0, page=1),
    }]
    items.extend([{
        'label': area['name'],
        'path': plugin.url_for('live_area', pid=id, id=area['id'], page=1),
    } for area in childran_areas])
    return items

@plugin.route('/live_area/<pid>/<id>/<page>/')
def live_area(pid, id, page):
    lives = []
    page_size = 30
    data = {
        'platform': 'web',
        'parent_area_id': pid,
        'area_id': id,
        'page': page,
        'page_size': page_size
    }
    res = cachedGet('https://api.live.bilibili.com/room/v3/area/getRoomList?' + urlencode(data))
    if res['code'] != 0:
        return lives
    list = res['data']['list']
    for item in list:
        live = {
            'label': item['uname'] + ' - ' + item['title'],
            'path': plugin.url_for('live', id=item['roomid']),
            'is_playable': True,
            'icon': item['cover'],
            'thumbnail': item['cover'],
            'info': {
                'mediatype': 'video',
                'title': item['title'],
            },
            'info_type': 'video'
        }
        lives.append(live)
    if page_size * int(page) < res['data']['count']:
        lives.append({
            'label': tag('下一页', 'yellow'),
            'path': plugin.url_for('live_area', pid=pid, id=id, page=int(page)+1)
        })
    return lives

@plugin.route('/my/')
def my():
    uid= get_uid()
    if uid == '0':
        notify('提示', '未设置 uid')
        return []
    items = [
        {
            'label': '我的收藏夹',
            'path': plugin.url_for('favlist_list', uid=uid),
        },
        {
            'label': '追番',
            'path': plugin.url_for('fav_series', uid=uid, type=1)
        },
        {
            'label': '追剧',
            'path': plugin.url_for('fav_series', uid=uid, type=2)
        },
    ]
    return items


@plugin.route('/web_dynamic/<page>/<offset>/')
def web_dynamic(page, offset):
    videos = []
    url = '/x/polymer/web-dynamic/v1/feed/all'
    data = {
        'timezone_offset': -480,
        'type': 'all',
        'page': page
    }
    if page != '1':
        data['offset'] = offset
    res = cachedApiGet(url, data)
    if res['code'] != 0:
        return videos
    list = res['data']['items']
    offset = res['data']['offset']
    for d in list:
        major = d['modules']['module_dynamic']['major']
        if not major:
            continue
        author = d['modules']['module_author']['name']
        mid = d['modules']['module_author']['mid']
        if 'archive' in major:
            item = major['archive']
            item['author'] = author
            item['mid'] = mid
            video = get_video_item(item)
        elif 'live_rcmd' in major:
            content = major['live_rcmd']['content']
            item = json.loads(content)
            if item['live_play_info']['live_status'] == 1:
                label = tag('【直播中】', 'red') + author + ' - ' + item['live_play_info']['title']
            else:
                label = tag('【未直播】', 'grey') + author + ' - ' + item['live_play_info']['title']
            video = {
                'label': label,
                'path': plugin.url_for('live', id=item["live_play_info"]["room_id"]),
                'is_playable': True,
                'icon': item["live_play_info"]["cover"],
                'thumbnail': item["live_play_info"]["cover"],
                'info': {
                    'mediatype': 'video',
                    'title': item['live_play_info']['title'],
                },
                'info_type': 'video',
            }
        else:
            continue
        videos.append(video)
    if res['data']['has_more']:
        videos.append({
            'label': tag('下一页', 'yellow'),
            'path': plugin.url_for('web_dynamic', page=int(page)+1, offset=offset)
        })
    return videos

@plugin.route('/fav_series/<uid>/<type>/')
def fav_series(uid, type):
    videos = []
    if uid == '0':
        return videos

    res = cachedApiGet('/x/space/bangumi/follow/list', {'vmid': uid, 'type': type})
    if res['code'] != 0:
        return videos

    list = res['data']['list']
    for item in list:
        label = item['title']
        if item['season_type_name']:
            label = tag('【' + item['season_type_name'] + '】', 'pink') + label
        video = {
            'label': label,
            'path': plugin.url_for('bangumi', type='season_id' ,id=item['season_id']),
            'icon': item['cover'],
            'thumbnail': item['cover']
        }
        videos.append(video)
    return videos


@plugin.route('/fav_series/<uid>/')
def favlist_list(uid):
    videos = []
    if uid == '0':
        return videos

    res = cachedApiGet('/x/v3/fav/folder/created/list-all', {'up_mid': uid})

    if res['code'] != 0:
        return videos

    list = res['data']['list']
    for item in list:
        video = {
            'label': item['title'],
            'path': plugin.url_for('favlist', id=item['id'], page=1)
        }
        videos.append(video)
    return videos


@plugin.route('/favlist/<id>/<page>/')
def favlist(id, page):
    videos = []
    data = {
        'media_id': id,
        'ps': 20,
        'pn': page,
        'keyword': '',
        'order': 'mtime',
        'tid': '0'
    }
    res = cachedApiGet('/x/v3/fav/resource/list', data)
    if res['code'] != 0:
        return videos
    list = res['data']['medias']
    for item in list:
        video = get_video_item(item)
        if video:
            videos.append(video)
    if res['data']['has_more']:
        videos.append({
            'label': tag('下一页', 'yellow'),
            'path': plugin.url_for('favlist', id=id, page=int(page)+1)
        })
    return videos



@plugin.route('/home/<page>/')
def home(page):
    videos = []
    page = int(page)
    url = '/x/web-interface/index/top/feed/rcmd'
    data = {
        'y_num': 3,
        'fresh_type': 4,
        'feed_version': 'V8',
        'fresh_idx_1h': page,
        'fetch_row': 3 * page + 1,
        'fresh_idx': page,
        'brush': page,
        'homepage_ver': 1,
        'ps': 12,
        'last_y_num': 4,
        'outside_trigger': ''
    }
    res = cachedApiGet(url, data)

    if res['code'] != 0:
        return videos

    list = res['data']['item']
    for item in list:
        if not item['bvid']:
            continue
        if 'live.bilibili.com' in item['uri']:
            if (item['room_info']['live_status'] == 1):
                label = tag('【直播中】', 'red') + item['owner']['name'] + ' - ' + item['title']
            else:
                label = tag('【未直播】', 'grey') + item['owner']['name'] + ' - ' + item['title']

            video = {
                'label': label,
                'path': plugin.url_for('live', id=item['url'].split('/')[-1]),
                'is_playable': True,
                'icon': item['pic'],
                'thumbnail': item['pic']
            }
        else:
            video = get_video_item(item)
            if not video:
                continue
        videos.append(video)
    videos.append({
        'label': tag('下一页', 'yellow'),
        'path': plugin.url_for('home', page=page+1)
    })
    return videos


@plugin.route('/dynamic_list/')
def dynamic_list():
    list = [['番剧', 13], ['- 连载动画', 33], ['- 完结动画', 32], ['- 资讯', 51], ['- 官方延伸', 152], ['电影', 23], ['国创', 167], ['- 国产动画', 153], ['- 国产原创相关', 168], ['- 布袋戏', 169], ['- 动态漫·广播剧', 195], ['- 资讯', 51], ['电视剧', 11], ['纪录片', 177], ['动画', 1], ['- MAD·AMV', 24], ['- MMD·3D', 25], ['- 短片·手书·配音', 47], ['- 手办·模玩', 210], ['- 特摄', 86], ['- 动漫杂谈', 253], ['- 综合', 27], ['游戏', 4], ['- 单机游戏', 17], ['- 电 子竞技', 171], ['- 手机游戏', 172], ['- 网络游戏', 65], ['- 桌游棋牌', 173], ['- GMV', 121], ['- 音游', 136], ['- Mugen', 19], ['鬼畜', 119], ['- 鬼畜 调教', 22], ['- 音MAD', 26], ['- 人力VOCALOID', 126], ['- 鬼畜剧场', 216], ['- 教程演示', 127], ['音乐', 3], ['- 原创音乐', 28], ['- 翻唱', 31], ['- 演奏', 59], ['- VOCALOID·UTAU', 30], ['- 音乐现场', 29], ['- MV', 193], ['- 乐评盘点', 243], ['- 音乐教学', 244], ['- 音乐综合', 130], ['舞蹈', 129], ['- 宅舞', 20], ['- 街舞', 198], ['- 明星舞蹈', 199], ['- 中国舞', 200], ['- 舞蹈综合', 154], ['- 舞蹈教程', 156], ['影视', 181], ['- 影视杂谈', 182], ['- 影视剪辑', 183], ['- 小剧场', 85], ['- 预告·资讯', 184], ['娱乐', 5], ['- 综艺', 71], ['- 娱乐杂谈', 241], ['- 粉丝创作', 242], ['- 明星综合', 137], ['知识', 36], ['- 科学科普', 201], ['- 社科·法律·心理', 124], ['- 人文历史', 228], ['- 财经商业', 207], ['- 校园学习', 208], ['- 职业职场', 209], ['- 设计·创意', 229], ['- 野生技能协会', 122], ['科技', 188], ['- 数码', 95], ['- 软件应用', 230], ['- 计算机技术', 231], ['- 科工机械', 232], ['资讯', 51], ['- 热点', 203], ['- 环球', 204], ['- 社会', 205], ['- 综合', 27], ['美食', 211], ['- 美食制作', 76], ['- 美食侦探', 212], ['- 美食测评', 213], ['- 田 园美食', 214], ['- 美食记录', 215], ['生活', 160], ['- 搞笑', 138], ['- 亲子', 254], ['- 出行', 250], ['- 三农', 251], ['- 家居房产', 239], ['- 手工', 161], ['- 绘画', 162], ['- 日常', 21], ['汽车', 223], ['- 赛车', 245], ['- 改装玩车', 246], ['- 新能源车', 246], ['- 房车', 248], ['- 摩托车', 240], ['- 购车攻略', 227], ['- 汽车生活', 176], ['时尚', 155], ['- 美妆护肤', 157], ['- 仿妆cos', 252], ['- 穿搭', 158], ['- 时尚潮流', 159], ['运动', 234], ['- 篮球', 235], ['- 足球', 249], ['- 健身', 164], ['- 竞技体育', 236], ['- 运动文化', 237], ['- 运动综合', 238], ['动物圈', 217], ['- 喵星人', 218], ['- 汪星人', 219], ['- 小宠异宠', 222], ['- 野生动物', 221], ['- 动物二创', 220], ['- 动物综合', 75], ['搞笑', 138], ['单机游戏', 17]]
    items = []
    for d in list:
        if d[0].startswith('- '):
            continue
        items.append({
            'label':d[0],
            'path': plugin.url_for('dynamic', id=d[1], page=1)
        })
    return items


@plugin.route('/dynamic/<id>/<page>/')
def dynamic(id, page):
    videos = []
    ps = 50
    res = cachedApiGet('/x/web-interface/dynamic/region', {'pn':page, 'ps':ps, 'rid':id})
    if res['code'] != 0:
        return videos
    list = res['data']['archives']
    for item in list:
        if 'redirect_url' in item and 'www.bilibili.com/bangumi/play' in item['redirect_url']:
            plot = parse_plot(item)
            bangumi_id = item['redirect_url'].split('/')[-1].split('?')[0]
            if bangumi_id.startswith('ep'):
                type = 'ep_id'
            else:
                type = 'season_id'
            bangumi_id = bangumi_id[2:]
            video = {
                'label': tag('【' + item['tname'] +  '】', 'pink') + item['title'],
                'path': plugin.url_for('bangumi', type=type, id=bangumi_id),
                'icon': item['pic'],
                'thumbnail': item['pic'],
                'info': {
                    'plot': plot
                },
                'info_type': 'video'
            }
        else:
            video = get_video_item(item)
            if not video:
                continue
        videos.append(video)
    if int(page) * ps < res['data']['page']['count']:
        videos.append({
            'label': tag('下一页', 'yellow'),
            'path': plugin.url_for('dynamic', id=id, page=int(page) + 1)
        })
    return videos



@plugin.route('/ranking_list/')
def ranking_list():
    rankings = [['全站', 0], ['国创相关', 168], ['动画', 1], ['音乐', 3], ['舞蹈', 129], ['游戏', 4], ['知识', 36], ['科技', 188], ['运动', 234], ['汽车', 223], ['生活', 160], ['美食', 211], ['动物圈', 217], ['鬼畜', 119], ['时尚', 155], ['娱乐', 5], ['影视', 181]]
    return [{
        'label': r[0],
        'path': plugin.url_for('ranking', id=r[1])
    } for r in rankings]


@plugin.route('/ranking/<id>/')
def ranking(id):
    res = cachedApiGet('/x/web-interface/ranking/v2', {'rid': id})
    videos = []
    if (res['code'] != 0):
        return videos
    list = res['data']['list']
    for item in list:
        video = get_video_item(item)
        if item:
            videos.append(video)
    return videos

@plugin.route('/watchlater/<page>/')
def watchlater(page):
    videos = []
    page = int(page)
    url = '/x/v2/history/toview'
    res = cachedApiGet(url)

    if res['code'] != 0:
        notify_error(res)
        return videos
    list = res['data']['list']
    for item in list:
        video = get_video_item(item)
        if video:
            videos.append(video)
    return videos


@plugin.route('/followingLive/<page>/')
def followingLive(page):
    page = int(page)
    items = []
    res = cachedGet('https://api.live.bilibili.com/xlive/web-ucenter/user/following?page=' + str(page) + '&page_size=10')
    if res['code'] != 0:
        notify_error(res)
        return items
    list = res['data']['list']
    for live in list:
        if live['live_status'] == 1:
            label = tag('【直播中】 ', 'red')
        else:
            label = tag('【未开播】 ', 'grey')
        label += live['uname'] + ' - ' +  live['title']
        item = {
            'label': label,
            'path': plugin.url_for('live', id=live['roomid']),
            'is_playable': True,
            'icon': live['face'],
            'thumbnail': live['face'],
            'info': {
                'mediatype': 'video',
                'title': live['title'],
            },
            'info_type': 'video'
        }
        items.append(item)
    if page < res['data']['totalPage']:
        items.append({
            'label': tag('下一页', 'yellow'),
            'path': plugin.url_for('followingLive', page=page + 1)
        })
    return items


@plugin.route('/history/<time>/')
def history(time):
    videos = []
    url = '/x/web-interface/history/cursor'
    data = {
        'view_at': time,
        'ps': 20,
    }
    res = apiGet(url, data)
    if res['code'] != 0:
        notify_error(res)
        return videos
    list = res['data']['list']
    for item in list:
        if item['videos'] == 1:
            video = {
                'label': item['author_name'] + ' - ' +  item['title'],
                'path': plugin.url_for('video', id=item['history']['bvid'], cid=0, ispgc='false'),
                'is_playable': True,
                'icon': item['cover'],
                'thumbnail': item['cover'],
                'info': {
                    'mediatype': 'video',
                    'title': item['title'],
                    'duration': item['duration']
                },
                'info_type': 'video'
            }
        elif item['videos'] > 1:
            label = parts_tag(item['videos']) + item['author_name'] + ' - ' +  item['title']
            if 'show_title' in item and item['show_title']:
                label += '\n' + tag(item['show_title'], 'grey')
            video = {
                'label': label,
                'path': plugin.url_for('videopages', id=item['history']['bvid'], cid=item['history']['cid']),
                'icon': item['cover'],
                'thumbnail': item['cover'],
                'info_type': 'video'
            }
        else:
            if item['history']['business'] == 'live':
                if item['live_status'] == 1:
                    label = tag('【直播中】 ', 'red')
                else:
                    label = tag('【未开播】 ', 'grey')
                label += item['author_name'] + ' - ' +  item['title']
                video = {
                    'label': label,
                    'path': plugin.url_for('live', id=item['kid']),
                    'is_playable': True,
                    'icon': item['cover'],
                    'thumbnail': item['cover'],
                    'info': {
                        'mediatype': 'video',
                        'title': item['title'],
                    },
                    'info_type': 'video'
                }
            elif item['history']['business'] == 'pgc':
                if item['badge']:
                    label = tag('【' + item['badge'] + '】', 'pink') + item['title']
                else:
                    label = item['title']
                if 'show_title' in item and item['show_title']:
                    label += '\n' + tag(item['show_title'], 'grey')
                video = {
                    'label': label,
                    'path': plugin.url_for('bangumi', type='ep_id', id=item['history']['epid']),
                    'icon': item['cover'],
                    'thumbnail': item['cover'],
                    'info_type': 'video'
                }
            else:
                continue
        videos.append(video)
    videos.append({
        'label': tag('下一页', 'yellow'),
        'path': plugin.url_for('history', time=res['data']['cursor']['view_at'])
    })
    return videos

@plugin.route('/live/<id>/')
def live(id):
    qn = getSetting('live_resolution')
    res = cachedGet('https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?room_id={}&protocol=0,1&format=0,1,2&codec=0,1&qn={}&platform=web&ptype=8&dolby=5&panorama=1'.format(id, qn))
    if res['code'] != 0:
        notify_error(res)
        return
    if not res['data']['playurl_info']:
        return
    streams = res['data']['playurl_info']['playurl']['stream']
    live_url = choose_live_resolution(streams) + '|Referer=https://www.bilibili.com'
    plugin.set_resolved_url(live_url)


def md2ss(id):
    res = cachedApiGet('/pgc/review/user', {'media_id': id})
    if res['code'] == 0:
        return res['result']['media']['season_id']
    return 0


@plugin.route('/bangumi/<type>/<id>/')
def bangumi(type, id):
    items = []
    if type == 'media_id':
        type = 'season_id'
        id = md2ss(id)
    res = cachedApiGet('/pgc/view/web/season', {type: id})
    if res['code'] != 0:
        return items
    episodes = res['result']['episodes']
    for episode in episodes:
        label = ''
        if episode['badge']:
            label = tag('【' + episode['badge'] + '】', 'pink') + episode['share_copy']
        else:
            label = episode['share_copy']
        item = {
            'label': label,
            'path': plugin.url_for('video', id=episode['bvid'], cid=episode['cid'], ispgc='true'),
            'is_playable': True,
            'icon': episode['cover'],
            'thumbnail': episode['cover'],
            'info': {
                'mediatype': 'video',
                'title': episode['share_copy'],
                'duration': episode['duration'] / 1000
            },
            'info_type': 'video',
        }
        items.append(item)
    return items


@plugin.route('/videopages/<id>/')
def videopages(id):
    videos = []
    res = cachedApiGet('/x/web-interface/view', {'bvid': id})
    data = res['data']
    if res['code'] != 0:
        return videos
    for item in data['pages']:
        if 'first_frame' in item and item['first_frame']:
            pic = item['first_frame']
        else:
            pic = data['pic']
        video = {
            'label': item['part'],
            'path': plugin.url_for('video', id=data['bvid'], cid=item['cid'], ispgc='false'),
            'is_playable': True,
            'icon': pic,
            'thumbnail': pic,
            'info': {
                'mediatype': 'video',
                'title': item['part'],
                'duration': item['duration']
            },
            'info_type': 'video',
        }
        videos.append(video)
    return videos


def report_history(bvid, cid):
    data = {
        'bvid': bvid,
        'cid': cid,
        'csrf': get_cookie_value('bili_jct')
    }
    res = post('https://api.bilibili.com/x/click-interface/web/heartbeat', data)
    return res


@plugin.route('/video/<id>/<cid>/<ispgc>/')
def video(id, cid, ispgc):
    ispgc = ispgc == 'true'
    video_url = ''
    enable_dash = getSetting('enable_dash') == 'true'
    if cid == '0':
        res = cachedApiGet('/x/web-interface/view', {'bvid': id})

        data = res['data']
        if res['code'] != 0:
            return

        cid = data['pages'][0]['cid']
        if 'redirect_url' in data and 'bangumi/play/ep' in data['redirect_url']:
            ispgc = True
        else:
            ispgc = False

    if ispgc:
        url = '/pgc/player/web/playurl'
    else:
        url = '/x/player/playurl'

    qn = getSetting('video_resolution')

    if enable_dash:
        params = {
            'bvid': id,
            'cid': cid,
            'qn': qn,
            'fnval': 4048,
            'fourk': 1
        }
    else:
        params = {
            'bvid': id,
            'cid': cid,
            'qn': qn,
            'fnval': 128,
            'fourk': 1
        }

    res = cachedApiGet(url, data=params)

    if res['code'] != 0:
        return
    if ispgc:
        data = res['result']
    else:
        data = res['data']

    if 'dash' in data:
        mpd = generate_mpd(data['dash'])
        success = None
        basepath = 'special://temp/plugin.video.bili/'
        if not make_dirs(basepath):
            return
        filepath = '{}{}.mpd'.format(basepath, cid)
        with xbmcvfs.File(filepath, 'w') as mpd_file:
            success = mpd_file.write(mpd)
        if not success:
            return
        ip_address = '127.0.0.1'
        port = getSetting('server_port')
        video_url = {
            'path': 'http://{}:{}/{}.mpd'.format(ip_address, port, cid),
            'properties': {
                'inputstream': 'inputstream.adaptive',
                'inputstream.adaptive.manifest_type': 'mpd',
                'inputstream.adaptive.manifest_headers': 'Referer=https://www.bilibili.com',
                'inputstream.adaptive.stream_headers': 'Referer=https://www.bilibili.com'
            }
        }
    elif 'durl' in data:
        video_url = data['durl'][0]['url']
        if video_url:
            video_url += '|Referer=https://www.bilibili.com'
    else:
        video_url = ''

    if video_url and getSetting('enable_danmaku') == 'true':
        ass = generate_ass(cid)
        if ass:
            player = xbmc.Player()
            if player.isPlaying():
                player.stop()
            if video_url and (getSetting('report_history') == 'true'):
                report_history(id, cid)
            plugin.set_resolved_url(video_url, ass)
            return
    if video_url and (getSetting('report_history') == 'true'):
        report_history(id, cid)
    plugin.set_resolved_url(video_url)


if __name__ == '__main__':
    plugin.run()
