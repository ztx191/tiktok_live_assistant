from typing import ClassVar

import httpx
import redis
from pymongo import MongoClient
import pymysql
from semantic_kernel.kernel_pydantic import KernelBaseSettings

from src.model.common import Result


class LocalRagSettings(KernelBaseSettings):
    env_prefix: ClassVar[str] = "LOCAL_RAG_"
    endpoint: str | None = None


class SmsSettings(KernelBaseSettings):
    env_prefix: ClassVar[str] = "SMS_"

    url: str | None = None
    api_key: str | None = None


class MongoDBSettings(KernelBaseSettings):
    env_prefix: ClassVar[str] = "MONGODB_"

    uri: str | None = None
    database: str | None = None
    max_keepalive_connections: int = 5
    max_connections: int = 100


class RedisSettings(KernelBaseSettings):
    env_prefix: ClassVar[str] = "REDIS_"

    uri: str | None = None
    database: str | None = None
    max_keepalive_connections: int = 5
    max_connections: int = 100

class DifySettings(KernelBaseSettings):
    env_prefix: ClassVar[str] = "DIFY_"

    url: str | None = None
    token: str | None = None

class MysqlSettings(KernelBaseSettings):
    env_prefix: ClassVar[str] = "MYSQL_"

    host: str | None = None
    port: int | None = None
    user: str | None = None
    password: str | None = None


class Clients:
    """
    定义各种数据库数据源客户端
    """
    # mongodb client
    _mongo_client = None
    # redis client
    _redis_client = None
    # sms
    _sms_settings = None

    _mysql_client = None

    @staticmethod
    def sms_send(userId, tpl_id, tpl_value) -> Result:
        if not Clients._sms_settings:
            Clients._sms_settings = SmsSettings.create()
        try:
            data = {'apikey': Clients._sms_settings.api_key, "mobile": userId, 'tpl_id': tpl_id, "tpl_value": tpl_value}
            response = httpx.post(Clients._sms_settings.url, data=data)
            result = response.json()
            return Result(code=result['code'], message=result['msg'])
        except Exception as e:
            return Result(code=-1, message=str(e))

    @staticmethod
    def get_mongo():
        if not Clients._mongo_client:
            mongodb_settings = MongoDBSettings.create()
            Clients._mongo_client = MongoClient(mongodb_settings.uri)[mongodb_settings.database]
        return Clients._mongo_client

    @staticmethod
    def get_by_redis(key):
        if not Clients._redis_client:
            redis_settings = RedisSettings.create()
            Clients._redis_client = redis.from_url(url=redis_settings.uri, db=redis_settings.database)
        value = Clients._redis_client.get(name=key)
        if value:
            return value.decode()
        else:
            return None

    @staticmethod
    def set_to_redis(key, value, ex):
        if not Clients._redis_client:
            redis_settings = RedisSettings.create()
            Clients._redis_client = redis.from_url(url=redis_settings.uri, db=redis_settings.database)
        Clients._redis_client.set(name=key, value=value, ex=ex)

    @staticmethod
    def del_from_redis(key):
        if not Clients._redis_client:
            redis_settings = RedisSettings.create()
            Clients._redis_client = redis.from_url(url=redis_settings.uri, db=redis_settings.database)
        Clients._redis_client.delete(key)

    @staticmethod
    def get_mysql():
        if not Clients._mysql_client:
            mysql_settings = MysqlSettings.create()
            Clients._mysql_client = pymysql.connect(host=mysql_settings.host, port=mysql_settings.port,
                                                    user=mysql_settings.user, password=mysql_settings.password
                                                    )
        return Clients._mysql_client

if __name__ == '__main__':
    # setting = MysqlSettings.create()
    # print(setting.host)
    Clients.get_mysql()
