"""
用户信息获取、更新、认证相关接口
"""
from sanic import Request
from common.utils import tool_certification
from lucky_game.base_api import GameAuthApi
from lucky_game.const import ReasonCostGold, PlatForm
from lucky_game.handler.decorator import GameChecker, CurrentLimiting, LimitTestCall
from lucky_game.handler.douyin import DouYin
from lucky_game.model_rc.base_user import BaseUserRC
from common.proto.py_pb2.http_login import PbUser, PbS2CExternalReturn
from common.utils.utils import UtilsTool
from lucky_game.handler.wechat import WeChat


class BaseUserInfo(GameAuthApi):

    def format_response_info(self, user: dict):
        self.info_log("format_response_info:", user)
        proto_data = PbUser.pb_model(**user)
        return self.answer(data=proto_data)


class ModifyGeneralUserInfo(BaseUserInfo):
    """ 更新用户必要信息（头像、昵称、性别） """

    async def post(self, req: Request, **kwargs):
        new_info = {}
        name = req.json.get("name")
        if name:
            self.check_str(name, require=False, p_name="name")
            new_info["name"] = UtilsTool.filter_emoji(name[:20])

        sex = req.json.get("sex")
        if sex:
            self.check_int(sex, require=False, minval=0, maxval=2, p_name="sex")
            new_info["sex"] = sex

        avatar = req.json.get("avatar")
        if avatar:
            self.check_str(avatar, require=False, p_name="avatar")
            new_info["avatar"] = avatar

        # 通过uid查询数据库用户信息
        old_info = kwargs.get("u_info")
        p_info = await BaseUserRC.update_info(old_info, new_info)
        (not p_info) and self.answer(self.sta_code.PASS)

        self.info_log('ModifyGeneralUserInfo suc:', p_info)
        return self.format_response_info(p_info)


class Certification(BaseUserInfo):
    """ 实名认证 """
    decorators = [CurrentLimiting, GameChecker]

    async def post(self, req, **kwargs):
        id_card = self.check_str(req.json.get("id_card"), require=True, minlen=18, maxlen=18, p_name="id_card")
        real_name = self.check_str(req.json.get("real_name"), require=True, minlen=2, p_name="real_name")

        res = UtilsTool.check_id_card(id_card)
        not res and self.answer(self.sta_code.ERR_ARG, hint='请检查身份证合法性')
        res = UtilsTool.validate_name(real_name)
        not res and self.answer(self.sta_code.ERR_ARG, hint='姓名错误')
        u_info = kwargs.get("u_info") or {}
        if u_info.get("id_card"):
            self.answer(self.sta_code.HAD_CERTIFICATED)

        status, result = await tool_certification.do_shi_ming_check(real_name, id_card, u_info.get("uid"))
        self.info_log("实名结果：", result)
        if not status:
            data = PbS2CExternalReturn.pb_model(**result)
            self.answer(code=self.sta_code.EXTERNAL_ERR, data=data)

        pi = result.get('data').get('result').get('pi')
        sex = UtilsTool.determine_gender(id_card)
        new_info = {
            "sex": sex,
            "id_card": id_card,
            "real_name": real_name,
        }
        if pi:
            new_info["pi"] = pi
        p_info = await BaseUserRC.update_info(u_info, new_info)
        # (not p_info) and self.answer(self.sta_code.WITHOUT_MODIFY, hint='Failed to modify info.')
        self.info_log('Certification 实名认证 suc:', p_info)
        return self.format_response_info(p_info)


class TestAddGold(BaseUserInfo):
    """修改灵石（调试用）"""
    decorators = [LimitTestCall, GameChecker]

    async def post(self, req, **kwargs):
        make_zero = self.check_int(req.json.get("make_zero", 0), default=0, minval=0, maxval=1, p_name="make_zero")

        u_info = kwargs.get("u_info") or {}
        if make_zero:
            new_info = {
                "gold": 0
            }
            if u_info.get("gold") == 0:
                self.answer(self.sta_code.ALREADY_DO, hint="灵石已经归零了")
            p_info = await BaseUserRC.update_info(u_info, new_info)
        else:
            gold = self.check_int(req.json.get("gold"), require=True, p_name="gold")
            new_info = {
                "gold": gold,
            }
            p_info = await BaseUserRC.update_user_asset(u_info.get("uid"), new_info, ReasonCostGold.TEST_ADD)

        if not p_info:
            return self.answer(code=self.sta_code.FAIL)

        self.info_log('TestAddGold 修改灵石成功')
        return self.format_response_info(p_info)


class GetSessionKey(BaseUserInfo):
    """session_key更新，参照接口：LoginByWechatMiniProgram"""

    async def post(self, req: Request, **kwargs):
        # 获取客户端code
        code = req.json.get('code')
        (not code) and self.answer(self.sta_code.ERR_ARG, hint='Invalid code.')

        platform = req.args.get('c_platform') or ''
        if platform == PlatForm.WECHAT_MINI_GAME:
            # 请求微信session_key
            errcode, req_data = await WeChat.wechat_mini_game_login(code)
        elif platform == PlatForm.DOUYIN_MINI_GAME:
            # 请求抖音session_key
            errcode, req_data = await DouYin.douyin_mini_game_login(code)
        else:
            return self.answer(self.sta_code.ERR_ARG, hint='Invalid platform.')

        self.info_log(f'{platform} GetSessionKey res:', code, req_data)
        if errcode > 0:
            data = PbS2CExternalReturn.pb_model(**{"errcode": errcode, "errmsg": req_data})
            self.answer(self.sta_code.EXTERNAL_ERR, data, hint=req_data)

        session_key = req_data.get("session_key")
        u_info = kwargs.get('u_info')
        uid = u_info.get('uid')
        await BaseUserRC.cache_session_key(uid, session_key)
        self.answer(hint='SessionKey 更新成功')


class GetWeChatGzhOpenid(BaseUserInfo):
    """
    获取微信公众号的Openid
    注意和登陆小游戏的Openid是互相独立的
    """

    async def post(self, req: Request, **kwargs):
        u_info = kwargs.get('u_info')
        uid = u_info.get('uid')

        code = req.json.get('code')
        (not code) and self.answer(self.sta_code.ERR_ARG, hint='Invalid code.')

        gzh_openid = await WeChat.update_gzh_openid(uid, code)
        if gzh_openid:
            return self.answer(self.sta_code.PASS)

        return self.answer(self.sta_code.FAIL, hint='Invalid gzh_openid.')





