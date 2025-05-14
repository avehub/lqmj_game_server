"""
聊天相关
"""
from nsanic.libs import tool_dt
from nsanic.orm.rc_model import RCModel
from promising_game.model_db.main import RecordsChatHistory
from nsanic.libs.tool import json_encode, json_parse


class ChatRecordRC(RCModel):
    db_model = RecordsChatHistory
    tb_name = db_model.sheet_name()

    MAX_CHAT_RECORDS_BEFORE_PERSIST = 100  # 设定的阈值，比如100条消息后持久化
    CHAT_HISTORY_LIMIT = 50  # 聊天历史记录限制

    CACHE_LIMIT = MAX_CHAT_RECORDS_BEFORE_PERSIST + CHAT_HISTORY_LIMIT  # 缓存限制条目

    @classmethod
    def get_channel_key(cls, chat_channel: int) -> str:
        """获取指定频道的缓存键"""
        return f"{cls.tb_name}:{chat_channel}"

    @classmethod
    async def save_chat_message(cls, chat_message: dict):
        """
        缓存聊天记录
        :param chat_message: 聊天消息字典
        """
        chat_channel = chat_message.get("chat_channel")
        key_name = cls.get_channel_key(chat_channel)

        await cls.conf.rds.qrpush(key_name, [chat_message])

        # 判断是否达到持久化阈值
        if await cls.conf.rds.qlen(key_name) >= cls.CACHE_LIMIT:
            return await cls.persist_chat_messages(key_name)
        return True

    @classmethod
    async def persist_chat_messages(cls, key_name: str):
        """
        持久化储存聊天记录
        """

        # 1.取出缓存中最旧的100条
        messages_to_save = await cls.conf.rds.conn.lrange(key_name, 0, cls.MAX_CHAT_RECORDS_BEFORE_PERSIST - 1)
        if not messages_to_save:
            return False

        # 使用批量插入的方法将聊天记录保存到数据库
        # todo 这里批量插入会有问题，当缓存中没有数据时，从数据查询出来写入缓存，当缓存到达阈值时，这部分旧数据又会重写进数据库
        # todo 后续改成发一条插入一条？
        messages_parsed = [json_parse(msg) for msg in messages_to_save]
        await cls.bulk_insert_chat_records(messages_parsed)

        # 保留列表中指定范围内的元素值。
        await cls.conf.rds.conn.ltrim(key_name, cls.MAX_CHAT_RECORDS_BEFORE_PERSIST, -1)
        return True

    @classmethod
    async def bulk_insert_chat_records(cls, chat_messages: list):
        """
        批量插入聊天记录到数据库
        :param chat_messages: 聊天消息列表，每个元素是一个字典
        """
        if not chat_messages:
            return

        # 创建聊天记录实例列表
        chat_record_tasks = []
        for msg in chat_messages:
            new_chat_record = {
                "chat_channel": msg.get('chat_channel'),
                "from_uid": msg.get('from_uid'),
                "to_uid": msg.get('to_uid'),
                "content": msg.get('content'),
                "created": msg.get('created') or tool_dt.cur_time()
            }
            chat_record_tasks.append(cls.db_model(**new_chat_record))

        # 批量插入数据库
        await cls.db_model.bulk_create(chat_record_tasks, batch_size=cls.MAX_CHAT_RECORDS_BEFORE_PERSIST)

    @classmethod
    async def query_chat_records(cls, chat_channel: int, limit: int = CHAT_HISTORY_LIMIT):
        """
        查询指定聊天频道的最近聊天记录
        :param chat_channel: 聊天频道ID
        :param limit: 返回的最大记录数，默认为50
        :return: 聊天记录列表
        """

        async def from_db():
            # 如果缓存中没有足够数据，则从数据库中查询
            query_records = await cls.db_model.get_by_dict({"chat_channel": chat_channel}, limit=limit)
            if query_records:
                # 将查询结果加入缓存，这里按时间降序，最新的向左边插入
                await cls.conf.rds.drop_item(key_name)  # 确保写入前清空
                await cls.conf.rds.qlpush(key_name, query_records)
                return query_records
            return []

        key_name = cls.get_channel_key(chat_channel)

        # 取最新的limit条目
        cache_records = await cls.conf.rds.conn.lrange(key_name, -limit, -1)
        if cache_records:
            records = [json_parse(msg) for msg in cache_records]
            return records

        return await from_db()
