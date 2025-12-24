from common.public.conf import CONF_DB, SERVER_SECRET_KEY
from tortoise import Tortoise


async def init_db():
    await Tortoise.init(
        config={
            'apps': {
                "lucky_game": {'models':
                    [

                    ]
                }
            },
            'connections': CONF_DB,
            'use_tz': False,
            'timezone': "UTC"
        }
    )
