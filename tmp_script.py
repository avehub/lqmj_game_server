"""
脚本执行文件
具体脚本请在：promising_game/script下实现
"""

import asyncio

from promising_admin.script.create_admin import create_super_admin
from promising_game.script.ban_player import ban_player
from promising_game.script.set_new_season import set_new_season
from promising_game.script.db_manager import del_conf_leisure, delete_user
from promising_game.script.forbid_match import let_service_forbid_match

if __name__ == '__main__':
    asyncio.run(del_conf_leisure([6, 7]))  # 刷新游戏与匹配服务的内存休闲场配置
    # asyncio.run(delete_user(100027))  # 删除玩家
    # asyncio.run(let_service_forbid_match(5, "2024-12-04 10:08:00"))  # 匹配守卫
    # asyncio.run(ban_player(150001, 0))  # 封禁玩家
    # asyncio.run(set_new_season())  # 设置新赛季
    # asyncio.run(create_super_admin())  # 创建超级管理员
