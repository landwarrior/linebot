"""LINE bot on AWS Lambda."""
import datetime
import json
import logging
import os
import random
import traceback

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s [%(filename)s in %(lineno)d]')
stream_handler.setFormatter(formatter)
LOGGER.addHandler(stream_handler)

# 日本時間に調整
NOW = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)

# requests のユーザーエージェントを書き換えたい
HEADER = {
    'User-agent': '''\
Mozilla/5.0 (Windows NT 10.0; Win64; x64) \
AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36'''
}

HOTPEPPER = os.environ['hotpepper']

TOKEN = ''


class MethodGroup:
    """やりたい処理を定義."""

    @staticmethod
    def _send_data(message: str) -> None:
        """LINE へ送信.

        :param str message: メッセージ
        :param str token: 応答トークン
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
    def help(args: list) -> None:
        """メソッド一覧."""
        methods = [a for a in dir(MethodGroup) if '_' not in a]
        if len(args) > 0 and getattr(MethodGroup, args[0], None):
            message = getattr(MethodGroup, args[0]).__doc__.replace('    ', '')
        else:
            message = 'メソッド一覧 '
            message += ', '.join(methods)
        MethodGroup._send_data(message)

    @staticmethod
    def lunch(args: list) -> None:
        """ランチ営業しているところを検索します.

        引数なし、もしくは一つの場合はデフォルト座標の近くでキーワード検索します。
        引数を2つ以上指定した場合、それらでキーワード検索します。
        この時のキーワードには場所も含まれます。
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
            message = '検索結果がありません'
        message += '　　Powered by ホットペッパー Webサービス'
        MethodGroup._send_data(message)

    @staticmethod
    def qiita(args: list) -> None:
        """Qiita の新着を3つ教えてくれます."""
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
        """どこに飲みに行くのか決めてくれます.

        引数なし、もしくは一つの場合は溜池山王辺りを中心にしてキーワード検索します。
        引数を2つ以上指定した場合、それらでキーワード検索します。
        キーワードには場所も含まれます。
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
            message = '検索結果がありません'
        else:
            shop = random.choice(shops)
            message = f"{shop['name']}\n{shop['urls']['pc']}\n"
        message += '　　Powered by ホットペッパー Webサービス'
        MethodGroup._send_data(message)


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
        text = text.replace('　', ' ')
        args = text.split(' ')
        if (len(args) > 0 and getattr(MethodGroup, args[0], None)):
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
