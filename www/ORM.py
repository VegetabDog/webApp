__author__ = 'Tony Mo'

import aiohttp, aiomysql
import logging; logging.basicConfig(level=logging.INFO)
# sql表示SQL语句
# 封装一个log函数包装写入日志的格式
def log(sql, arg=()):
    logging.info('SQL: %s'% sql)

# 创建全局连接池
async def create_pool(loop, **kw):
    logging.info('create database connection pool ...')
    # 创建全局变量__pool
    global __pool
    # 创建数据库连接池
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),
        autocommit=kw.get('autocommit', True),
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )

async def select(sql, agrs, size=None):
    log(sql, agrs)
    global __pool
    # await表示调用一个子协程，也就是一个协程调用另一个协程，并直接获得子协程的返回结果
    with (await __pool) as conn:
        cur = await conn.cursor(aiomysql.DictCursor)
    # async with __pool.get() as conn:
    #     async with conn.cursor(aiomysql.DictCursor) as cur:
    #     SQL语句的占位符是‘？’，MySql的占位符为‘%s’
    #     SQL语句要使用带参数的，避免使用自己拼接的字符串，这样可以防止SQL注入攻击
        await cur.execute(sql.replace('?', '%s'), agrs or ())
        if size:
            # fetchmany()返回size大小的数据记录
            rs = await cur.fetchmany(size)
        else:
            # fetchall()返回所有数据记录
            rs = await cur.fetchall()
        await cur.close()
        logging.info('row returned: %s' % len(rs))
        return rs
# 该函数用于执行INSERT、UPDATE、DELETE语句，原因是三种操作所需参数一致；
# 返回受影响数据的行数
async def execute(sql, agrs):
    log(sql)
    global __pool
    async with __pool.acquire() as conn:
        try:
            cur = await conn.cursor()
            await cur.execute(sql.replace('?', '%s'), agrs)
            affected = cur.rowcount
            await cur.close()
        except BaseException as e:
            raise
        return affected

def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ', '.join(L)
# 定义Field类
class Field(object):
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default
    def __str__(self):
        return '<%s, %s, %s>' % (self.__class__.__name__, self.column_type, self.name)
# 定义Field子类并设置默认值
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
# type是一个元类
class ModelMetaclass(type):
    # __new__是一个静态方法,而__init__是一个实例方法.
    # __new__方法会返回一个创建的实例,而__init__什么都不返回.
    # 只有在new返回一个cls的实例时后面的__init__才能被调用.
    # 当创建一个新实例时调用__new__,初始化一个实例时用__init__.

    # cls:当前准备创建的类对象class
    # name:类名
    # bases:类继承的父类集合
    # attrs:类方法集合
    def __new__(cls, name, bases, attrs):
        # 排除Model类
        if name=='Model':
            return type.__new__(cls, name, bases, attrs)
        # 获取表名
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        # 属性和列的映射
        mappings = dict()
        # 除主键外的属性
        fields = []
        # 主键
        primaryKey = None
        for k, v in attrs.items():
            # isinstance函数是判断v和Field两个类型是否一致，一致返回Ture，否则返回False
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                # 当前属性为主键，赋值给primaryKey
                if v.primary_key:
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                # 非主键属性加入fields列表
                else:
                    fields.append(k)
        if not primaryKey:
            raise RuntimeError('Primary key not found.')
        # 将Model中的k删除
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        # 保存属性和列的对应关系
        attrs['__mappings__'] = mappings
        # 保存表名
        attrs['__table__'] = tableName
        # 保存主键
        attrs['__primary_key__'] = primaryKey
        # 保存除主键外的属性
        attrs['__fields__'] = fields
        # 保存select、insert、update和delete对应MySql语句
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)
# 通过ModelMetaclass来创建
class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)
    # 返回属性为item的value值
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError:
            raise AttributeError(r"'Model' object hsa no attribute  '%s'" % item)
    # 设置属性为key的值
    def __setattr__(self, key, value):
        self[key] = value
    # 获取属性key的值
    def getValue(self, key):
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value)
        return value
    # 使用classmethod，可以让所有子类调用class方法
    @classmethod
    async def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. '
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        rs = await select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        ' find number by select and where. '
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    @classmethod
    async def find(cls, pk):
        ' find object by primary key. '
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = await execute(self.__insert__, args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValue, self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = await execute(self.__delete__, args)
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)

