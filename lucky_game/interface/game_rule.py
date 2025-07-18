"""
游戏规则接口
"""
from sanic import Request
from lucky_game.base_api import GameAuthApi
from nsanic.libs.tool import json_encode, json_parse
from lucky_game.model_rc.conf_game_room_rules import ConfGameRoomRulesRC


class GameRuleAll(GameAuthApi):
    """获取所有游戏规则"""
    async def get(self, req: Request, **kwargs):
        pid = req.args.get("pid", 0)
        rule_type = self.check_int(req.args.get("rule_type"), require=False, p_name="规则类型")
        status = self.check_int(req.args.get("status"), require=False, default=0, p_name="状态")
        data, e = await ConfGameRoomRulesRC.get_all(pid, rule_type=rule_type, status=status)
        return self.answer(data=data)
