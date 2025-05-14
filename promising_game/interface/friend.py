"""
友谊相关接口
"""
from sanic import Request
from datetime import datetime, timedelta
from promising_game.base_api import GameAuthApi
from common.proto.py_pb2.http_friend import PbFriendship
from promising_game.const import FriendshipSta, FriendOpType
from promising_game.model_rc.base_friend import UserFriendshipRC
from promising_game.model_rc.base_user import BaseUserRC


class GetUserFriendList(GameAuthApi):
    """
    通用获取好友列表
    is_new：新的朋友 1 / 好友 0
    """
    decorators = []

    async def get(self, req: Request, **kwargs):
        is_new = self.check_int(req.args.get("is_new") or 0, default=0, p_name="is_new")

        # u_info = kwargs.get("u_info")
        u_info = await BaseUserRC.cache_by_uid(155555)
        # u_info = await BaseUserRC.cache_by_uid(150001)
        uid = u_info.get("uid")

        # 1.获取用户好友列表
        friend_records = await UserFriendshipRC.cache_user_friendship(uid)
        (not friend_records) and self.answer(self.sta_code.NO_PLAYER_INFO, hint="没有任何好友记录")

        # 2.不同的列表分类处理
        friend_list = []
        for f in friend_records:
            friend_status = f.get("status")
            updated_time = f.get("updated") or 0

            if is_new:
                three_months_ago = int((datetime.now() - timedelta(days=90)).timestamp())  # 单位是秒

                # 只关注自己作为 to_uid 被申请的记录，也包含已拒绝的
                if friend_status in (FriendshipSta.PENDING.val, FriendshipSta.REJECTED.val) and \
                        (f.get("to_uid") == uid) and updated_time >= three_months_ago:
                    friend_list.append(f)

                    # 如果已经达到最大条目数，则停止添加更多条目
                    if len(friend_list) >= UserFriendshipRC.MAX_FRIEND_REQUESTS:
                        break
            else:
                # 查询好友时，因为 cache_user_friendship 已经返回双向关系，所以只需检查状态
                if friend_status == FriendshipSta.ACCEPTED.val:
                    friend_list.append(f)

        self.info_log(uid, f"GetUserFriendList 获取{is_new}列表 成功", friend_list)
        # (not friend_list) and self.answer(self.sta_code.NO_PLAYER_INFO, hint="没有任何相关好友记录")
        proto_data = PbFriendship.pb_model(friend_list)
        return self.answer(data=proto_data)


class FriendshipOperate(GameAuthApi):
    """
    通用好友操作
    """
    decorators = []

    async def post(self, req: Request, **kwargs):
        opt_type = self.check_int(req.json.get("opt_type") or 0, require=True, p_name="opt_type")
        ot_enum = FriendOpType.find_member_by_val(opt_type)
        (not isinstance(ot_enum, FriendOpType)) and self.answer(code=self.sta_code.ERR_ARG, hint="不支持的操作类型")

        # 获取目标用户UID
        target_uid = req.json.get("target_uid")
        (not target_uid) and self.answer(code=self.sta_code.ERR_ARG, hint="缺少目标用户ID")

        # 获取发起操作的用户信息
        # u_info = kwargs.get("u_info")
        # u_info = await BaseUserRC.cache_by_uid(155555)
        u_info = await BaseUserRC.cache_by_uid(150001)
        operate_uid = u_info.get("uid")

        map_func = {
            FriendOpType.REQUEST.val: self.friend_request,
            FriendOpType.ACCEPT.val: self.friend_accept,
            FriendOpType.REJECT.val: self.friend_reject,
            FriendOpType.BLOCK.val: self.friend_block,
            FriendOpType.UNBLOCK.val: self.friend_unblock,
            FriendOpType.REMOVE.val: self.friend_remove
        }
        opt_func = map_func.get(opt_type)
        if opt_func and callable(opt_func):
            opt_res = await opt_func(operate_uid, target_uid)
            self.info_log(operate_uid, f"FriendshipOperate {ot_enum.phrase}操作结果 {opt_res}")

            if opt_res:
                proto_data = PbFriendship.pb_model([opt_res])
                return self.answer(hint="OK", data=proto_data)

            return self.answer(code=self.sta_code.FAIL, hint="好友操作失败")
        return self.answer(code=self.sta_code.FAIL, hint="非有效操作")

    async def friend_request(self, operate_uid, target_uid):
        """
        发起好友申请
        操作玩家发起，目标玩家收到
        """
        add_res, add_hint = await UserFriendshipRC.add_friend_request(target_uid, operate_uid)
        self.info_log(f"{operate_uid} 发起好友申请结果：{add_res}，描述：{add_hint}")
        (not add_res) and self.answer(code=self.sta_code.FAIL, hint=add_hint)

        return add_res

    async def friend_accept(self, operate_uid, target_uid):
        """
        接受好友申请
        目标玩家接受
        """
        accept_res, accept_hint = await UserFriendshipRC.response_friend_request(operate_uid, target_uid,
                                                                                 FriendshipSta.ACCEPTED)
        self.info_log(f"{operate_uid} 接受好友申请结果：{accept_res}，描述：{accept_hint}")
        (not accept_res) and self.answer(code=self.sta_code.FAIL, hint=accept_hint)

        return accept_res

    async def friend_reject(self, operate_uid, target_uid):
        """
        拒绝好友申请
        目标玩家拒绝
        """
        reject_res, reject_hint = await UserFriendshipRC.response_friend_request(operate_uid, target_uid,
                                                                                 FriendshipSta.REJECTED)
        self.info_log(f"{operate_uid} 拒绝好友申请结果：{reject_res}，描述：{reject_hint}")
        (not reject_res) and self.answer(code=self.sta_code.FAIL, hint=reject_hint)

        return reject_res

    async def friend_block(self, operate_uid, target_uid):
        """
        屏蔽好友
        双方都可操作
        """
        block_res, block_hint = await UserFriendshipRC.block_or_unblock_friend(operate_uid, target_uid, is_block=True)
        self.info_log(f"{operate_uid} 屏蔽好友结果：{block_res}，描述：{block_hint}")
        (not block_res) and self.answer(code=self.sta_code.FAIL, hint=block_hint)

        return block_res

    async def friend_unblock(self, operate_uid, target_uid):
        """
        取消屏蔽好友
        双方都可操作
        """
        unblock_res, unblock_hint = await UserFriendshipRC.block_or_unblock_friend(operate_uid, target_uid,
                                                                                   is_block=False)
        self.info_log(f"{operate_uid} 取消屏蔽好友结果：{unblock_res}，描述：{unblock_hint}")
        (not unblock_res) and self.answer(code=self.sta_code.FAIL, hint=unblock_hint)

        return unblock_res

    async def friend_remove(self, operate_uid, target_uid):
        """
        解除好友关系
        双方都可操作
        """
        remove_res, remove_hint = await UserFriendshipRC.unfriend_request(operate_uid, target_uid)
        self.info_log(f"{operate_uid} 解除好友关系结果：{remove_res}，描述：{remove_hint}")
        (not remove_res) and self.answer(code=self.sta_code.FAIL, hint=remove_hint)

        return remove_res
