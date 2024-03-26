import time, uuid

import asyncio

from ORM import Model, StringField, BooleanField, FloatField, TextField, create_pool

def next_id():
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)
# 用户表
class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)
# 博客表
class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(default=time.time)
# 评价表
class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    created_at = FloatField(default=time.time)

async def test_save(loop):
    # 测试时需要修改为自己使用的数据库账户与密码
    await create_pool(loop, user='root', password='123456', db='awesome')
    user = User(id=3, name='c', email='c@example', passwd='123', image='about:blank')
    await user.save()
async def test_findAll(loop):
    await create_pool(loop, user='root', password='123456', db='awesome')
    res = await User.findAll()
    print(res)

if __name__ == '__main__':
    # user = User()
    # print(user['email'])
    loop = asyncio.get_event_loop()

    loop.run_until_complete(test_findAll(loop))
    # loop.run_until_complete(test_save(loop))