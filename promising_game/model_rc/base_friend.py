"""
好友系统
"""
import asyncio
from nsanic.libs import tool_dt
from nsanic.libs.tool import json_parse, json_encode
from promising_game.const import FriendshipSta
from promising_game.model_rc.base_rc import BaseRC
from promising_game.model_db.main import UserFriendship


class UserFriendshipRC(BaseRC):
    db_model = UserFriendship
    tb_name = db_model.sheet_name()

    expired_mode = 1
    expired_sec = 2 * 86400

    MAX_FRIEND_REQUESTS = 50  # 申请列表最大条目数
    MAX_FRIENDS_ACCEPTED = 500  # 已接受状态下的最大好友数量


    @classmethod
    async def cache_user_friendship(cls, cur_uid):
        """
        获取用户好友列表（双向）
        :param cur_uid: 发起查询操作的玩家，注意双向关系，则不管此cur_uid在表里作为from_uid或to_uid，都只能存在一条且都查询
        """

        async def from_db():
            # 查询当前用户作为from_uid的好友记录
            from_info = await cls.db_model.get_by_dict({"from_uid": cur_uid})

            # 查询当前用户作为to_uid的好友记录
            to_info = await cls.db_model.get_by_dict({"to_uid": cur_uid})

            combined_records = {}
            for f in from_info + to_info:
                """
                other_uid 是指与当前用户（cur_uid）相关的另一个用户ID。
                如果当前记录中的from_uid等于cur_uid，则other_uid为该记录的to_uid；
                反之，如果当前记录中的to_uid等于cur_uid，则other_uid为该记录的from_uid。
                """
                other_uid = f.get("to_uid") if f.get("from_uid") == cur_uid else f.get("from_uid")
                if other_uid not in combined_records:
                    combined_records[other_uid] = f

            # 确保每个other_uid只保留一条记录，避免重复
            if combined_records:
                cache_db_info_dict = {str(k): json_encode(v) for k, v in combined_records.items()}
                await cls.conf.rds.set_hash_bulk(key_name, cache_db_info_dict)
                return list(combined_records.values())
            return []

        key_name = f'{cls.tb_name}:{cur_uid}'
        info_list = await cls.conf.rds.get_hash_val(key_name)
        if info_list:
            info_list = [json_parse(one, cls.logerr) for one in info_list]
            return info_list
        return await from_db()

    @classmethod
    async def cache_user_friendship_by_id(cls, cur_uid, friend_uid):
        """
        获取当前用户和指定用户的友情（双向）
        :param cur_uid: 发起操作的玩家ID
        :param friend_uid: 指定的好友ID
        """

        # 防止缓存击穿，使用双重检查锁（DCL）
        async def from_cache():
            info = await cls.conf.rds.get_hash(key_name, friend_uid)
            if info:
                return json_parse(info, cls.logerr)

        async def cache_all_from_db():
            # 调用cache_user_friendship方法获取所有好友记录
            all_friends = await cls.cache_user_friendship(cur_uid)

            # 在所有好友记录中查找特定的好友关系
            for record in all_friends:
                if (record.get("from_uid") == cur_uid and record.get("to_uid") == friend_uid) or \
                        (record.get("from_uid") == friend_uid and record.get("to_uid") == cur_uid):
                    return record
            return {}

        key_name = f'{cls.tb_name}:{cur_uid}'
        return await from_cache() or await cls.conf.rds.locked(f"{key_name}:{friend_uid}", fun=cache_all_from_db)

    @classmethod
    async def get_both_ways_records(cls, cur_uid, friend_uid):
        """
        获取双向的好友记录
        :param cur_uid: 当前用户ID
        :param friend_uid: 好友用户ID
        :return: (forward_record, reverse_record)
        """
        forward_record = await cls.cache_user_friendship_by_id(cur_uid, friend_uid)
        reverse_record = await cls.cache_user_friendship_by_id(friend_uid, cur_uid)
        return forward_record, reverse_record

    @classmethod
    async def check_both_ways_friendship(cls, cur_uid, friend_uid):
        """
        检查双向好友关系
        :return: 如果任意一方已经是对方的好友，则返回True；否则返回False
        """
        # 使用 get_both_ways_records 获取双向的好友记录
        forward_record, reverse_record = await cls.get_both_ways_records(cur_uid, friend_uid)

        # 检查两个方向的好友状态是否为已接受（ACCEPTED）
        if (forward_record and forward_record.get("status") == FriendshipSta.ACCEPTED.val) or \
                (reverse_record and reverse_record.get("status") == FriendshipSta.ACCEPTED.val):
            return True

        return False

    @classmethod
    async def __clear_both_ways_cache(cls, cur_uid, friend_uid):
        """清除涉及用户的缓存（避免更新其中之一缓存，忽略了另一个缓存）"""
        await asyncio.gather(
            cls.conf.rds.drop_hash(f'{cls.tb_name}:{cur_uid}', friend_uid),
            cls.conf.rds.drop_hash(f'{cls.tb_name}:{friend_uid}', cur_uid)
        )

    @classmethod
    async def __update_cache(cls, cur_uid, friend_uid, new_info):
        await cls.conf.rds.set_hash(f'{cls.tb_name}:{cur_uid}', friend_uid, new_info)

    @classmethod
    async def __update_friendship(cls, cur_uid, friend_uid, friend_record, friend_status, prev_status=None):
        """
        更新友情状态
        :param friend_record: 友情记录
        :param friend_status: 新状态
        """
        if not friend_record:
            return False, '无好友记录'

        _id = friend_record.get("id")
        update_dict = {
            "status": friend_status.val,
            "prev_status": prev_status,
            "updated": tool_dt.cur_time()
        }

        update_res = await cls.db_model.update_by_pk(_id, update_dict)
        if update_res:
            updated_record = {**friend_record, **update_dict}
            await cls.__update_cache(cur_uid, friend_uid, updated_record)
            await cls.__clear_both_ways_cache(cur_uid, friend_uid)
            return updated_record, 'OK'
        return False, 'FAIL'

    @classmethod
    async def __create_friendship(cls, cur_uid, friend_uid, status, prev_status=None):
        """
        创建新的好友状态记录
        :param cur_uid: 当前用户ID
        :param friend_uid: 好友用户ID
        :param status: 新的状态
        :param prev_status: 屏蔽之前的旧状态（用于取消屏蔽后恢复）
        :return: (new_record, message)
        """
        new_record = {
            "from_uid": cur_uid,
            "to_uid": friend_uid,
            "status": status,
            "prev_status": prev_status,  # 初始屏蔽无前一状态
            "updated": tool_dt.cur_time()
        }
        insert_obj = await cls.db_model.add_one(new_record)
        if insert_obj:
            new_record["id"] = insert_obj.id
            await cls.__update_cache(cur_uid, friend_uid, new_record)
            return new_record, 'OK'
        return False, '操作失败'

    @classmethod
    async def add_friend_request(cls, cur_uid, friend_uid):
        """
        发起好友请求
        :param cur_uid: 发起操作的玩家ID
        :param friend_uid: 指定的好友ID
        """
        # 1.获取两个方向的好友记录
        forward_record, reverse_record = await cls.get_both_ways_records(cur_uid, friend_uid)

        # 2.双向检查是否已经是好友
        if await cls.check_both_ways_friendship(cur_uid, friend_uid):
            return False, '已经是好友关系'

        # 3.检查是否被对方屏蔽
        if reverse_record and reverse_record.get("status") == FriendshipSta.BLOCKED.val:
            return False, '对方已屏蔽您，无法发送好友请求'

        # 4.如果存在任意方向的关系，检查并更新状态
        if forward_record or reverse_record:
            target_record = forward_record if forward_record else reverse_record
            if target_record.get("status") not in (FriendshipSta.REJECTED.val, FriendshipSta.UNFRIENDED.val):
                return False, '当前已申请或不是可申请状态'

            return await cls.__update_friendship(cur_uid, friend_uid, target_record, FriendshipSta.PENDING)

        # 4.没有记录则创建新的友谊
        return await cls.__create_friendship(cur_uid, friend_uid, FriendshipSta.PENDING)

    @classmethod
    async def response_friend_request(cls, cur_uid, friend_uid, attitude: FriendshipSta=FriendshipSta.REJECTED):
        """
        响应好友请求
        :param cur_uid: 发起操作的玩家ID
        :param friend_uid: 指定的好友ID
        :param attitude: 被申请玩家的响应态度（答应/拒绝）
        """
        if attitude not in (FriendshipSta.ACCEPTED.val, FriendshipSta.REJECTED.val):
            return False, '只能接受或者拒绝对方的好友申请'

        # 若当前无记录，或待处理之外的状态，则无法表态
        friend_record = await cls.cache_user_friendship_by_id(cur_uid, friend_uid)
        if not friend_record or friend_record.get("status") != FriendshipSta.PENDING.val:
            return False, '不可操作的好友状态'

        return await cls.__update_friendship(cur_uid, friend_uid, friend_record, attitude)

    @classmethod
    async def block_or_unblock_friend(cls, cur_uid, friend_uid, is_block=False):
        """
        屏蔽或解除屏蔽指定用户（不限于好友）
        :param cur_uid: 发起操作的玩家ID
        :param friend_uid: 指定的用户ID
        :param is_block: 是否屏蔽
        """
        forward_record, reverse_record = await cls.get_both_ways_records(cur_uid, friend_uid)
        target_record = forward_record if forward_record else reverse_record

        if is_block:
            new_status = FriendshipSta.BLOCKED.val
            prev_status = target_record.get("status") if target_record else None

            if target_record:
                # 如果已有记录，则更新状态为屏蔽，并保存之前的友情状态
                return await cls.__update_friendship(cur_uid, friend_uid, target_record, FriendshipSta.BLOCKED, prev_status=prev_status)
            else:
                # 如果没有现有记录，则创建新的屏蔽记录
                return await cls.__create_friendship(cur_uid, friend_uid, FriendshipSta.BLOCKED)
        else:
            # 如果要解除屏蔽，检查当前状态是否为屏蔽状态
            if target_record and target_record.get("status") == FriendshipSta.BLOCKED.val:
                # 解除屏蔽时，恢复到之前的友情状态
                prev_status = target_record.get("prev_status")
                new_status = prev_status if prev_status else FriendshipSta.ACCEPTED.val

                # 更新状态并清除 prev_status 字段
                return await cls.__update_friendship(cur_uid, friend_uid, target_record, new_status)

            return False, '无法解除屏蔽，因为当前状态不是屏蔽状态'

    @classmethod
    async def unfriend_request(cls, cur_uid, friend_uid):
        """
        解除好友请求

        双方成为好友关系之后，任何一方都可主动解除好友关系
        :param cur_uid: 发起操作的玩家ID
        :param friend_uid: 指定的好友ID
        """
        friend_record = await cls.cache_user_friendship_by_id(cur_uid, friend_uid)
        if not friend_record:
            return False, '不是好友不可解除'

        # 若当前已是好友才可以解除好友
        if friend_record.get("status") == FriendshipSta.ACCEPTED.val:
            return await cls.__update_friendship(cur_uid, friend_uid, friend_record, FriendshipSta.UNFRIENDED)
        return False, '当前不是好友关系'