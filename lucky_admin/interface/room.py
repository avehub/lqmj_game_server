from sanic import Request
from lucky_admin.base_api import AdminAuthApi
from lucky_game.model_rc.base_records_game import BaseRecordsGameRC
from lucky_game.model_rc.extra_user_resource_changes import ExtraUserResourceChangesRC
from lucky_game.model_rc.game_rooms import GameRoomsRC
from lucky_game.model_rc.base_clubs import BaseClubRC


class GameRoom(AdminAuthApi):
    async def get(self, req: Request):
        """ 开启的房间 """
        room_id = self.check_int(req.args.get('room_id'), require=False, p_name='房间ID')
        uid = self.check_int(req.args.get('uid'), require=False, p_name='建房者ID')
        page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
        page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
        data, msg = await GameRoomsRC.get_game_rooms_by_filter(creator=uid, room_id=room_id, page=page, page_size=page_size)
        return self.answer(data=data, hint=msg)

class GameRecord(AdminAuthApi):
    async def get(self, req: Request):
        """房间战绩"""
        try:
            room_id = self.check_int(req.args.get('room_id'), require=False, p_name='房间ID')
            uid = self.check_int(req.args.get('uid'), require=False, p_name='建房者ID')
            page = self.check_int(req.args.get('page'), require=False, default=1, p_name='页码')
            page_size = self.check_int(req.args.get('page_size'), require=False, default=10, p_name='每页数量')
            start_time = self.check_int(req.args.get('start_time'), require=False, p_name='开始时间')
            end_time = self.check_int(req.args.get('end_time'), require=False, p_name='结束时间')
            data, msg = await BaseRecordsGameRC.get_record_list(uid=uid, room_id=room_id, page=page, page_size=page_size,
                                                            start_time=start_time, end_time=end_time)
        except Exception as e:
            self.log_info(f"获取房间战绩失败: {str(e)}")
            return self.answer(self.sta_code.FAILURE, hint="获取房间战绩失败")
        return self.answer(data=data, hint=msg)

