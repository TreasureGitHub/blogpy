#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aiohttp import web
import asyncio

async def index(request):
	print(request.cookies)
	return web.Response(body='<h1>hello,index</h1>'.encode('utf-8'))

async def hello(request):
	path = request.match_info['name']
	# print(dir(request))
	body = '<h1>Hellosdf,%s</h1>' %path
	print('--------------')
	res = web.Response(body=body.encode('utf-8'))
	print(request.cookies)
	return web.Response(body=body.encode('utf-8'))

async def init(loop):
	app1 = web.Application(loop = loop)
	app1.router.add_route('GET','/',index)
	app1.router.add_route('GET','/hello/{name}',hello)
	rs = await loop.create_server(app1.make_handler(),'127.0.0.1','8000')
	return rs

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
