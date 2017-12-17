#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aiohttp import web
import asyncio
import os
import logging
from jinja2 import Environment,FileSystemLoader


async def index(request):
	print(request.cookies)
	return web.Response(body='<h1>hello,index</h1>'.encode('utf-8'))

async def hello(request):
	path = request.match_info['name']
	# print(dir(request))
	body = '<h1>Hellosdf,%s</h1>' %path
	res = web.Response(body=body.encode('utf-8'))
	return web.Response(body=body.encode('utf-8'))

def init_jinja2(app,**kw):
	options = dict(
		autoescape = kw.get('autoescape', True),
        block_start_string = kw.get('block_start_string', '{%'),
		block_end_string = kw.get('block_end_string', '%}'),
		variable_start_string = kw.get('variable_start_string','{{'),
        variable_end_string = kw.get('variable_end_string', '}}'),
        auto_reload = kw.get('auto_reload', True)
	)
	path = kw.get('path', None)
	if path is None:
		path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
	logging.info('set jinja2 templates path:%s' % (path))
	env = Environment(loader=FileSystemLoader(path),**options)
	filters = kw.get('filters',None)
	if filters is not None:
		for name,f in filters.items():
			env.fitlers[name] = f
	app['__templating__'] = env

async def init(loop):
	app1 = web.Application(loop = loop)
	init_jinja2(app1)
	app1.router.add_route('GET','/',index)
	app1.router.add_route('GET','/hello/{name}',hello)
	rs = await loop.create_server(app1.make_handler(),'127.0.0.1','8000')
	return rs


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
