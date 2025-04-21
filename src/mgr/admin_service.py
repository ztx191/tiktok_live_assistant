import json
import logging
import uuid
from datetime import timedelta, datetime

import jwt

from src.connector.client import Clients
from src.model.accounts import Account

logger = logging.getLogger(__name__)


class AdminService:
    redis_token_prefix = "admin-login-token::"
    redis_token_timeout_minutes = 720  # 12小时

    token_secret_key = "QYTzjqEceU2WH5rEzKeFd2NBJBkzqGmzxTPK3Ssr3IQl9g7ZN7vV9qqfoGizZb8q"  # 密钥
    token_secret_algorithm = "HS256"  # 算法

    def login(self, account: str, password: str) -> Account | None:
        """
        通过账号密码登录
        """
        try:
            record = Clients.get_mongo().admin_accounts.find_one({"account": account})
            if record:
                if password == record['password']:
                    return self._build_token(record)
        except Exception as e:
            logger.error("db error: %s", e)

        return None

    def logout(self, token: str) -> bool:
        """
        退出
        """
        try:
            Clients.del_from_redis(self.redis_token_prefix + token.split('.')[2])
            return True
        except Exception as e:
            logger.error("db error: %s", e)

        return False

    def _build_token(self, record: dict):
        session_id = uuid.uuid4().hex
        expire_time = datetime.now() + timedelta(minutes=self.redis_token_timeout_minutes)  # expire 令牌到期时间
        token_session = {"_id": session_id,
                         "account": record['account'],
                         "name": record['name'],
                         "loginTimestamp": round(datetime.now().timestamp()),
                         "expireTimestamp": round(expire_time.timestamp())}

        token = jwt.encode(payload=token_session,
                           key=self.token_secret_key,
                           algorithm=self.token_secret_algorithm)

        Clients.set_to_redis(self.redis_token_prefix + token.split('.')[2],
                             json.dumps(token_session),
                             timedelta(minutes=self.redis_token_timeout_minutes))
        return token
