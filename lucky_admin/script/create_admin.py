import argparse
from nsanic.libs import tool_dt
from nsanic.libs.mk_random import RngMaker
from common.utils.utils import UtilsTool
from nsanic import verify
from common.public.conf import CONF_DB, SERVER_SECRET_KEY
from tortoise import Tortoise
from lucky_admin.const import AdminStatus, AdminPermission
from lucky_admin.model_db.main import Admins


def init_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--u', type=str, default='', help="用户名")
    parser.add_argument('--p', type=str, default='', help="密码")
    parser.add_argument('--permission', type=int, default=4, help="权限")
    args = parser.parse_args()
    if not args.u or len(args.u) < 6 or len(args.u) > 20:
        raise RuntimeError("用户名必须大于6位小于20位")
    flag, msg = verify.password(args.p, len_min=6, len_max=20, qc=3)
    if not flag:
        raise RuntimeError("密码长度必须为6-20，且大小写、数字、特殊字符任意3重组合")
    return args


async def create_super_admin():
    """ 创建超级管理员 """
    arg = init_args()
    cur_time = tool_dt.cur_time()
    rng = RngMaker
    permission = AdminPermission.find_member_by_val(arg.permission)
    if not permission:
        raise ValueError('权限不对！请更正！')
    init_data = {
        'created': cur_time,
        'updated': cur_time,
        'username': arg.u,
        'password': UtilsTool.get_hash_secrets(SERVER_SECRET_KEY, arg.p, secrets_type='sha256'),
        'safe_key': rng.mk_str(18),
        'valid_key': rng.mk_str(16),
        'status': AdminStatus.ENABLE,
        'permission': permission,
    }

    async def init_db():
        await Tortoise.init(
            config={
                'apps': {
                    "lucky_game": {'models': ["lucky_game.model_db.main", "lucky_game.model_db.extra"]}},
                'connections': CONF_DB,
                'use_tz': False,
                'timezone': "UTC"
            }
        )

    await init_db()

    u_info = await Admins.get_by_dict({'username': arg.u}, limit=1)
    if u_info:
        raise RuntimeError(f"{arg.u}用户已存在，请重新输入！")

    try:
        res = await Admins.add_one(init_data)
        print('创建成功！', res)
    except Exception as e:
        print("创建失败！", e)


async def main():
    await create_super_admin()


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())
