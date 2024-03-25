__author__ = 'Tony Mo'

import aiohttp, aiomysql, logging
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
            cur =  await conn.cursor()
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
