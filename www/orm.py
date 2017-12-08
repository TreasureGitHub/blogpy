#!/usr/bin/env python3
# -*- coding:utf-8 --

import aiomysql
import asyncio,logging

def log(sql,args=None):
    logging.info('SQL:%s' %sql)

async def create_pool(loop,**kw):
    logging.info('create database connection pool...')
    global __pool
    __pool = await aiomysql.create_pool(
        host = kw.get('host','127.0.0.1'),
        user = kw['user'], 
        password = kw['password'], 
        db = kw['db'],
        port = kw.get('port',3306),
        charset = kw.get('charset','utf8'),
        autocommit = kw.get('autocommit',True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop = loop
        )

async def select(sql,args,size = None):
    log(sql,args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?','%s'),args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs

async def execute(sql,args,autocommit=True):
    log(sql,args)
    global __pool
    async with __pool.get() as conn:
        try:
            cur = await conn.cursor()
            await cur.execute(sql.replace('?','%s'),args)
            affected = cur.rowcount
            await cur.close()
        except BaseException as e:
            raise
        return affected

class Field(object):

    def __init__(self,name,column_type,primary_key=False,default=None):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' %(self.__class__.__name__,self.column_type,self.name)

    __repr__ = __str__

class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

class ModelMetaClass(type):

    def __new__(cls,name,bases,attrs):
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        tableName = attrs.get('__table__',name)
        fields = []
        mappings = dict()
        primary_key = None
        for k,v in attrs.items():
            if isinstance(v,Field):
                logging.info('  found mapping: %s ==> %s' %(k,v))
                mappings[k] = v
                if v.primary_key:
                    logging.info('Found primary_key:%s' %k)
                    if primary_key:
                        raise BaseException('Duplicate primary key for field: %s' %k)
                    primary_key = k
                else:
                    fields.append(k)
        if not primary_key:
            raise StandardError('not found primary_key')
        for k in fields:
            attrs.pop(k)
        attrs.pop(primary_key)
        attrs['__table__'] = tableName
        attrs['__mappings__'] = mappings
        attrs['__fields__'] = fields
        attrs['__primary_key__'] = primary_key
        attrs['__select__'] = 'select %s,`%s` from `%s`' %(','.join(map(lambda f:'`%s`' %f ,fields)),primary_key,tableName)
        attrs['__insert__'] = 'insert into `%s`(%s,`%s`) values(%s)' %(tableName,','.join(map(lambda f:'`%s`' %f ,fields)),primary_key,'%s,?' %(','.join(['?'] * len(fields))))
        attrs['__update__'] = 'update `%s` set %s where `%s` = ?' %(tableName,','.join(map(lambda f:'`%s` = ?' %(f) ,fields)),primary_key)
        attrs['__delete__'] = 'delete from `%s` where `%s` = ?' %(tableName,primary_key)
        return super(ModelMetaClass,cls).__new__(cls,name,bases,attrs)


class Model(dict,metaclass=ModelMetaClass):

    def __init__(self,**kw):
        super().__init__(**kw)

    def __getattr__(self,key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s' " %key)

    def __setattr__(self,key,value):
        self[key] = value

    def getValue(self,key):
        return self.__getattr__(key)

    def getValueOrDefault(self,key):
        rs = self.get(key,None)
        if rs is None:
            field = self.__mappings__[key]
            if field.default is not None:
                rs = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' %(key,str(rs)))
        return rs

    @classmethod
    async def findAll(cls,where = None,args = None,**kw):
        sql = [cls.__select__]
        if where:
            sql.extend(['where',where])
        if args is None:
            args = []
        orderBy = kw.get('OrderBy',None)
        if orderBy:
            sql.extend(['order by',orderBy])
        limit = kw.get('limit',None)
        if limit:
            sql.append('limit')
            if isinstance(limit,int):
                sql.append(str(limit))
            elif isinstance(limit,tuple) and len(limit) == 2:
                sql.append('?,?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql),args)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls,selectField,where=None,args=None):
        sql = ['select %s __num__ from  `%s`' %(selectField,cls.__table__) ]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql),args,1)
        if len(rs) == 0:
            return None
        return rs[0]['__num__']

    @classmethod
    async def find(cls,pk):
        rs = await select('%s where `%s` = ?' %(cls.__select__,cls.__primary_key__),[pk],1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    async def save(self):
        sql = self.__insert__
        args = list(map(self.getValueOrDefault,self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(sql,args)
        rows = 1
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValue,self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__,args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__,args)
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)
