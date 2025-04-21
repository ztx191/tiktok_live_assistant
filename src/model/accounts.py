from datetime import datetime

from pydantic import BaseModel, Field

"""
用户登陆账户
"""


class Account(BaseModel):
    id: str = Field(alias="_id")
    userId: str | None = None  # 手机号
    wxUid: str | None = None  # 微信UnionID
    wxOid: str | None = None  # 微信OpenID
    registerTime: int = round(datetime.utcnow().timestamp())  # 注册时间
    lastLoginTime: int = round(datetime.utcnow().timestamp())  # 登录时间


def from_record(record: dict) -> Account:
    return Account(_id=str(record["_id"]),
                   userId=record["userId"],
                   wxUid=record["wxUid"],
                   wxOid=record["wxOid"],
                   registerTime=record["registerTime"],
                   lastLoginTime=record["lastLoginTime"]
                   )


def from_records(records: list[dict]) -> list[Account]:
    return [from_record(record) for record in records]


def to_record(account: Account) -> dict:
    return account.dict(by_alias=True)


def to_records(accounts: list[Account]) -> list[dict]:
    return [to_record(account) for account in accounts]
