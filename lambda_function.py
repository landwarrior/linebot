"""LINE bot on AWS Lambda."""
import datetime
import json
import logging
import os
import random
import re
import traceback
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s [%(filename)s in %(lineno)d]')
stream_handler.setFormatter(formatter)
LOGGER.addHandler(stream_handler)

# 日本時間に調整
NOW = datetime.datetime.now(datetime.timezone.utc) + \
    datetime.timedelta(hours=9)

# requests のユーザーエージェントを書き換えたい
HEADER = {
    'User-agent': '''\
Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'''
}

HOTPEPPER = os.environ.get('hotpepper')

TOKEN = ''


def help() -> None:
    """メソッド一覧."""
    methods = [a for a in dir(MethodGroup) if '_' not in a]
    bubbles = []
    for _method in methods:
        description = re.sub(' {1,}', '', getattr(MethodGroup, _method).__doc__)
        args = re.split(r'\.\n', description)
        title = args[0]
        # 末尾の改行も含まれている
        description = '\n'.join((''.join(args[1:])).split('\n')[1:])
        bubbles.append({
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "color": "#ffffff",
                        "align": "start",
                        "size": "md",
                        "gravity": "center"
                    }
                ],
                "backgroundColor": "#27ACB2",
                "paddingAll": "15px",
                "action": {
                    "type": "postback",
                    "label": _method,
                    "data": _method,
                    "displayText": _method
                }
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                          {
                              "type": "text",
                              "text": description,
                              "color": "#8C8C8C",
                              "size": "sm",
                              "wrap": True
                          }
                        ],
                        "flex": 1
                    }
                ],
                "spacing": "md",
                "paddingAll": "12px",
            },
            "styles": {
                "footer": {
                    "separator": False
                }
            }
        })

    headers = {
        'Content-Type': 'application/json',
        "Authorization": f"Bearer {os.environ['access_token']}",
    }
    url = 'https://api.line.me/v2/bot/message/reply'
    payload = {
        'replyToken': TOKEN,
        'messages': [
            {
                "type": "flex",
                "altText": "コマンド一覧",
                "contents": {
                    "type": "carousel",
                    "contents": bubbles
                }
            }
        ]
    }

    res = requests.post(url, data=json.dumps(
        payload).encode('utf-8'), headers=headers)
    LOGGER.info(
        f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")


class MethodGroup:
    """やりたい処理を定義."""

    @staticmethod
    def _send_data(message: str) -> None:
        """LINE へ送信.

        :param str message: メッセージ
        """
        headers = {
            'Content-Type': 'application/json',
            "Authorization": f"Bearer {os.environ['access_token']}",
        }
        url = 'https://api.line.me/v2/bot/message/reply'
        payload = {
            'replyToken': TOKEN,
            'messages': [
                {
                    'type': 'text',
                    'text': message,
                }
            ]
        }
        res = requests.post(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        LOGGER.info(f"[RESPONSE] [STATUS]{res.status_code} [HEADER]{res.headers} [CONTENT]{res.content}")

    @staticmethod
    def lunch(args: list) -> None:
        """ランチ営業店舗検索.

        lunchコマンドの後にスペース区切りで二つ以上キーワードを入力すると場所での検索も可能です。
        一つの場合はデフォルト座標付近での検索となります。
        """
        _param = {
            'key': HOTPEPPER,
            'large_service_area': 'SS10',  # 関東
            'range': '3',
            'order': '2',
            'type': 'lite',
            'format': 'json',
            'count': '100',
            'lunch': '1',
        }
        if not args or len(args) == 1:
            _param['lat'] = os.environ['default_lat']
            _param['lng'] = os.environ['default_lng']
        if len(args) > 0:
            _param['keyword'] = ' '.join(list(args))
        hotpepper = requests.get(
            'http://webservice.recruit.co.jp/hotpepper/gourmet/v1/',
            params=_param,
            headers=HEADER)
        shops = hotpepper.json()['results']['shop']
        if len(shops) > 0:
            shop = random.choice(shops)
            message = f'{shop["name"]}\n{shop["urls"]["pc"]}\n'
        else:
            message = '検索結果がありません\n'
        message += '　　Powered by ホットペッパー Webサービス'
        MethodGroup._send_data(message)

    @staticmethod
    def qiita(args: list) -> None:
        """Qiita新着記事取得.

        qiitaコマンドでQiitaの新着記事を3件取得します。
        """
        res = requests.get('https://qiita.com/api/v2/items?page=1&per_page=3',
                           headers=HEADER)
        data = res.json()
        msg = []
        for d in data:
            msg.append(f"{d['title']}\n{d['url']}")
        message = '\n'.join(msg)
        MethodGroup._send_data(message)

    @staticmethod
    def nomitai(args: list) -> None:
        """居酒屋検索.

        nomitaiコマンドの後にスペース区切りで二つ以上キーワードを入力すると場所での検索も可能です。
        一つの場合はデフォルト座標付近での検索となります。
        """
        _param = {
            'key': HOTPEPPER,
            'large_service_area': 'SS10',  # 関東
            'range': '5',
            'order': '2',
            'type': 'lite',
            'format': 'json',
            'count': '100',
        }
        if not args or len(args) == 1:
            _param['lat'] = os.environ['default_lat']
            _param['lng'] = os.environ['default_lng']
            if not args:
                # デフォルトは居酒屋
                _param['genre'] = 'G001'
        if len(args) > 0:
            _param['keyword'] = ' '.join(list(args))
        if len(args) >= 2:
            # 範囲を絞る
            _param['range'] = 3

        hotpepper = requests.get(
            'http://webservice.recruit.co.jp/hotpepper/gourmet/v1/',
            params=_param,
            headers=HEADER)
        shops = hotpepper.json()['results']['shop']
        if len(shops) == 0:
            message = '検索結果がありません\n'
        else:
            shop = random.choice(shops)
            message = f"{shop['name']}\n{shop['urls']['pc']}\n"
        message += '　　Powered by ホットペッパー Webサービス'
        MethodGroup._send_data(message)

    @staticmethod
    def itsEvents(args: list) -> None:
        """関東ITソフトウェア健康保険組合のイベント情報を返します.

        滅多に更新されないので見る価値ないかも。
        """
        ret = requests.get('https://www.its-kenpo.or.jp/NEWS/event_rss.xml',
                           headers=HEADER)
        root = ET.fromstring(ret.content.decode('utf8'))
        msg = []
        for child in root[0]:
            if 'item' in child.tag.lower():
                msg.append(f'{child[0].text}\n{child[1].text}')
        message = '関東ITソフトウェア健康保険組合のイベント情報です\n'
        message += '\n'.join(msg)
        MethodGroup._send_data(message)

    @staticmethod
    def yahoo(args: list) -> None:
        """ヤフーニュースを取得します.

        主要なヤフーニュースにのみ対応しています。
        """
        ret = requests.get('https://news.yahoo.co.jp', headers=HEADER)
        # utf8 以外だったら以下みたいにデコードする
        # html = ret.content.decode('sjis')
        yahoo = BeautifulSoup(ret.text, 'html.parser')
        topics = yahoo.select('ul.topicsList_main')[0].select('li>a')
        message = '主要なニュースをお伝えします\n'
        msg = []
        for topic in topics:
            msg.append(f"{topic.text}\n{topic.get('href')}")
        message += '\n'.join(msg)
        MethodGroup._send_data(message)

    @staticmethod
    def itmediaYesterday(args: list) -> None:
        """ITmediaの昨日のニュースをお伝えします.

        無ければ無いって言います。
        """
        yesterday = NOW - datetime.timedelta(days=1)
        s_yd = f'{yesterday.year}年{yesterday.month}月{yesterday.day}日'
        url = f"https://www.itmedia.co.jp/news/subtop/archive/{yesterday.strftime('%Y%m')[2:]}.html"
        ret = requests.get(url, headers=HEADER)
        site = BeautifulSoup(ret.content.decode('sjis'), 'html.parser')
        root = site.select('div.colBoxBacknumber')[
            0].select('div.colBoxInner>div')
        message = '【 ITmediaの昨日のニュース一覧 】\n'
        msg = []
        for i, item in enumerate(root):
            if 'colBoxSubhead' in item.get('class', []) and item.text == s_yd:
                for a in root[i + 1].select('ul>li'):
                    msg.append(
                        f"{a.select('a')[0].text}\nhttps:{a.select('a')[0].get('href')}")
                break
        if len(msg) > 0:
            message += '\n'.join(msg)
        else:
            message = 'ITmediaの昨日のニュースはありませんでした。'
        MethodGroup._send_data(message)

    @staticmethod
    async def zdJapan(args: list) -> None:
        """ZDNet Japanの昨日のニュースを取得.

        無ければ無いって言います。
        """
        yesterday = NOW - datetime.timedelta(days=1)
        s_yd = yesterday.strftime('%Y-%m-%d')
        base = 'https://japan.zdnet.com'
        url = base + '/archives/'
        ret = requests.get(url, headers=HEADER)
        site = BeautifulSoup(ret.content.decode('utf8'), 'html.parser')
        root = site.select('div.pg-mod')
        message = '【 ZDNet Japanの昨日のニュース一覧 】\n'
        msg = []
        for div in root:
            span = div.select('h2.ttl-line-center>span')
            if span and span[0].text == '最新記事一覧':
                for li in div.select('ul>li'):
                    if s_yd in li.select('p.txt-update')[0].text:
                        anchor = li.select('a')[0]
                        msg.append(
                            f"{anchor.text}\n{base + anchor.get('href')}")
                break
        if len(msg) > 0:
            message += '\n'.join(msg)
        else:
            message = 'ZDNet Japanの昨日のニュースはありませんでした。'
        MethodGroup._send_data(message)

    @staticmethod
    def weeklyReport(args: list) -> None:
        """JPCERT から Weekly Report を取得.

        水曜日とかじゃないと何も返ってきません。
        """
        url = 'https://www.jpcert.or.jp'
        today = NOW.strftime('%Y-%m-%d')
        ret = requests.get(url, headers=HEADER)
        jpcert = BeautifulSoup(ret.content.decode('utf-8'), 'html.parser')
        whatsdate = jpcert.select('a.fl')[0].text.replace('号', '')
        if today == whatsdate:
            message = f"【 JPCERT の Weekly Report {jpcert.select('a.fl')[0].text} 】\n"
            message += url + jpcert.select('a.fl')[0].get('href') + '\n'
            wkrp = jpcert.select('div.contents')[0].select('li')
            for i, item in enumerate(wkrp, start=1):
                message += f"{i}. {item.text}\n"
            MethodGroup._send_data(message)

    @staticmethod
    def noticeAlert(*args) -> None:
        """当日発表の注意喚起もしくは脆弱性関連情報を取得.

        何もなきゃ何も言いません。
        """
        url = 'https://www.jpcert.or.jp'
        today = NOW.strftime('%Y-%m-%d')
        yesterday = NOW - datetime.timedelta(days=1)
        # 12:00 に実行するので、前日の 11:59 以降をデータ取得対象にする
        yesterday = datetime.datetime(
            yesterday.year,
            yesterday.month,
            yesterday.day,
            11, 59, 59
        )
        ret = requests.get(url, headers=HEADER)
        jpcert = BeautifulSoup(ret.content.decode('utf-8'), 'html.parser')
        items = jpcert.select('div.container')
        notice = '【 JPCERT の直近の注意喚起 】\n'
        warning = '【 JPCERT の直近の脆弱性関連情報 】\n'
        notice_list = []
        warning_list = []
        for data in items:
            if data.select('h3') and data.select('h3')[0].text == '注意喚起':
                for li in data.select('ul.list>li'):
                    published = li.select('a')[0].select(
                        'span.left_area')[0].text
                    title = li.select('a')[0].select('span.right_area')[0].text
                    if today in published:
                        link = url + li.select('a')[0].get('href')
                        notice_list.append(f"{today} {title} {link}")
                    if yesterday.strftime('%Y-%m-%d') in published:
                        link = url + li.select('a')[0].get('href')
                        notice_list.append(
                            f"{yesterday.strftime('%Y-%m-%d')} {title} {link}")
            if data.select('h3') and data.select('h3')[0].text == '脆弱性関連情報':
                for li in data.select('ul.list>li'):
                    published = li.select('a')[0].select(
                        'span.left_area')[0].text.strip()
                    dt_published = datetime.datetime.strptime(
                        published, '%Y-%m-%d %H:%M')
                    title = li.select('a')[0].select('span.right_area')[0].text
                    if yesterday <= dt_published:
                        link = li.select('a')[0].get('href')
                        warning_list.append(f"{title} {link}")
        if len(notice_list) > 0:
            notice += '\n'.join(notice_list)
            MethodGroup._send_data(notice)
        if len(warning_list) > 0:
            warning += '\n'.join(warning_list)
            MethodGroup._send_data(warning)


def lambda_handler(event, context):
    """eventの中身はログ見てね."""
    global TOKEN
    try:
        LOGGER.info('--LAMBDA START--')
        LOGGER.info(f"event: {json.dumps(event)}")
        LOGGER.info(f"context: {context}")
        LOGGER.info(f"body: {event.get('body')}")
        LOGGER.debug(f"Japan Time is : {NOW}")
        body = json.loads(event.get('body', {}))
        # LINE webhook
        for event in body.get('events', []):
            TOKEN = event.get('replyToken', '')
            text = event.get('message', {}).get('text')
            # postback の場合はメソッドのデフォルトで動作するように設定
            if event.get('postback', {}).get('data'):
                text = event['postback']['data']
        text = text.replace('　', ' ')
        args = text.split(' ')
        if args[0] == 'コマンド':
            help()
        elif (len(args) > 0 and getattr(MethodGroup, args[0], None)):
            LOGGER.info(f"method: {args[0]}, param: {args[1:]}")
            getattr(MethodGroup, args[0])(args[1:])

    except Exception:
        LOGGER.error(traceback.format_exc())

    payload = {
        'replyToken': TOKEN,
        'messages': [
            {
                'type': 'text',
                'text': 'これはテストです'
            },
        ],
    }

    ret = {
        'statusCode': '200',
        'body': json.dumps(payload, ensure_ascii=False),
        'headers': {
            'Content-Type': 'application/json',
            "Authorization": f"Bearer {os.environ['access_token']}",
        },
    }
    LOGGER.info(f'[RETURN] {ret}')
    LOGGER.info('--LAMBDA END--')
    return ret
