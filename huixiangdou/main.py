#!/usr/bin/env python3

"""HuixiangDou binary."""
import argparse
import os
import time

import pytoml
import requests
from aiohttp import web
from loguru import logger
from termcolor import colored

from .services import ErrorCode, build_reply_text
from .services import SerialPipeline, ParallelPipeline
from .primitive import always_get_an_event_loop

def parse_args():
    """Parse args."""
    parser = argparse.ArgumentParser(description='SerialPipeline.')
    parser.add_argument('--work_dir',
                        type=str,
                        default='workdir',
                        help='Working directory.')
    parser.add_argument(
        '--config_path',
        default='config.ini',
        type=str,
        help='SerialPipeline configuration path. Default value is config.ini')
    args = parser.parse_args()
    return args

async def show(assistant, fe_config: dict):
    queries = ['百草园里有什么?', '请问明天天气如何？']
    print(colored('Running some examples..', 'yellow'))
    for query in queries:
        print(colored('[Example]' + query, 'yellow'))

    for query in queries:
        async for sess in assistant.generate(query=query, history=[], groupname=''):
            pass

        code, reply, refs = str(sess.code), sess.response, sess.references
        reply_text = build_reply_text(code=code,
                                      query=query,
                                      reply=reply,
                                      refs=refs)
        logger.info('\n' + reply_text)

        if fe_config['type'] == 'lark':
            # send message to lark group
            logger.error(
                '!!!`lark_send_only` feature will be removed on October 10, 2024. If this function still helpful for you, please let me know: https://github.com/InternLM/HuixiangDou/issues'
            )
            from .frontend import Lark
            lark = Lark(webhook=fe_config['webhook_url'])
            logger.info(f'send {reply} and {refs} to lark group.')
            lark.send_text(msg=reply_text)

    while True:
        user_input = input("🔆 Input your question here, type `bye` for exit:\n")
        if 'bye' in user_input:
            break

        async for sess in assistant.generate(query=user_input, history=[], groupname=''):
            pass
        code, reply, refs = str(sess.code), sess.response, sess.references

        reply_text = build_reply_text(code=code,
                                      query=user_input,
                                      reply=reply,
                                      refs=refs,
                                      max_len=300)
        print('\n' + reply_text)

async def lark_group_recv_and_send(assistant, fe_config: dict):
    from .frontend import (is_revert_command, revert_from_lark_group,
                           send_to_lark_group)
    msg_url = fe_config['webhook_url']
    lark_group_config = fe_config['lark_group']
    sent_msg_ids = []

    while True:
        # fetch a user message
        resp = requests.post(msg_url, timeout=10)
        resp.raise_for_status()
        json_obj = resp.json()
        if len(json_obj) < 1:
            # no user input, sleep
            time.sleep(2)
            continue

        logger.debug(json_obj)
        query = json_obj['content']

        if is_revert_command(query):
            for msg_id in sent_msg_ids:
                error = revert_from_lark_group(msg_id,
                                               lark_group_config['app_id'],
                                               lark_group_config['app_secret'])
                if error is not None:
                    logger.error(
                        f'revert msg_id {msg_id} fail, reason {error}')
                else:
                    logger.debug(f'revert msg_id {msg_id}')
                time.sleep(0.5)
            sent_msg_ids = []
            continue

        async for sess in assistant.generate(query=query, history=[], groupname=''):
            pass
        code, reply, refs = str(sess.code), sess.response, sess.references
        if code == ErrorCode.SUCCESS:
            json_obj['reply'] = build_reply_text(reply=reply,
                                                 references=refs)
            error, msg_id = send_to_lark_group(
                json_obj=json_obj,
                app_id=lark_group_config['app_id'],
                app_secret=lark_group_config['app_secret'])
            if error is not None:
                raise error
            sent_msg_ids.append(msg_id)
        else:
            logger.debug(f'{code} for the query {query}')


async def wechat_personal_run(assistant, fe_config: dict):
    """Call assistant inference."""

    async def api(request):
        input_json = await request.json()
        logger.debug(input_json)

        query = input_json['query']

        if type(query) is dict:
            query = query['content']

        async for sess in assistant.generate(query=query, history=[], groupname=''):
            pass
        code, reply, refs = str(sess.code), sess.response, sess.references
        reply_text = build_reply_text(reply=reply, references=refs)

        return web.json_response({'code': int(code), 'reply': reply_text})

    bind_port = fe_config['wechat_personal']['bind_port']
    app = web.Application()
    app.add_routes([web.post('/api', api)])
    web.run_app(app, host='0.0.0.0', port=bind_port)


async def run(args):
    """Automatically download config, start llm server and run examples."""

    # query by worker
    with open(args.config_path, encoding='utf8') as f:
        fe_config = pytoml.load(f)['frontend']
    logger.info('Config loaded.')
    assistant = SerialPipeline(work_dir=args.work_dir, config_path=args.config_path)

    fe_type = fe_config['type']
    if fe_type == 'none':
        await show(assistant, fe_config)
    elif fe_type == 'lark_group':
        await lark_group_recv_and_send(assistant, fe_config)
    elif fe_type == 'wechat_personal':
        await wechat_personal_run(assistant, fe_config)
    elif fe_type == 'wechat_wkteam':
        from .frontend import WkteamManager
        manager = WkteamManager(args.config_path)
        await manager.loop(assistant)
    else:
        logger.info(
            f'unsupported fe_config.type {fe_type}, please read `config.ini` description.'  # noqa E501
        )

if __name__ == '__main__':
    args = parse_args()
    loop = always_get_an_event_loop()
    loop.run_until_complete(run(args=args))
