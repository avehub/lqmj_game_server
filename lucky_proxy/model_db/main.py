from nsanic.orm.db_model import DBModel
from tortoise import fields


class GameUser(DBModel):
    """用户总表"""
    uid = fields.IntField(max_length=28, pk=True, default=500000, description='玩家ID')
    name = fields.CharField(max_length=32, null=True, default='', description='玩家昵称')
    phone = fields.CharField(max_length=11, null=True, default='', description='玩家手机号')
    avatar = fields.CharField(max_length=256, null=True, default='', description='头像地址')
    unionid = fields.CharField(max_length=128, null=True, default='', description='用户授权唯一标识')

    class Meta:
        table = "user"


class ProxyUser(DBModel):
    """代理商（服务商表）"""
    id = fields.IntField(max_length=20, pk=True, default=500000, description='代理用户id')
    create_by = fields.IntField(default=None, description='创建者')
    proxy_name = fields.CharField(max_length=32, null=True, default='', description='玩家昵称')
    phone = fields.CharField(max_length=20, null=True, default='', description='手机号')
    unionid = fields.CharField(max_length=128, null=True, default='', description='用户授权唯一标识')
    created = fields.BigIntField(null=True, default=0, description='更新时间')
    proxy_level = fields.IntField(null=True, default=1, description='代理等级等级')
    auth_status = fields.IntField(null=True, default=0, description='认证状态 1、已认证 0、未认证')
    level1_proxy_id = fields.IntField(max_length=20, default=0, description='一级代理id')
    promotion_code = fields.CharField(max_length=10, null=False, description='专属邀请码/推广码')
    join_day = fields.CharField(max_length=10, null=False, description='加入时间 yyyy-MM-dd')
    room_card_rate = fields.DecimalField(max_digits=4, decimal_places=2, null=False, description='房卡提成比例')
    assistance_program_rate = fields.DecimalField(max_digits=4, decimal_places=2, null=False,
                                                  description='助农提成比例')
    status = fields.IntField(null=True, default=0, description='状态：0 被封禁 1：正常')

    class Meta:
        table = "proxy_user"


"""
代理月收入
"""


class ProxyMonthIncome(DBModel):
    """代理用户钱包"""
    id = fields.IntField(max_length=20, pk=True, description='主键无意义')
    proxy_id = fields.IntField(max_length=28, description='代理（服务商id）')
    month_income = fields.DecimalField(max_digits=10, decimal_places=2, description='月收入')
    room_income = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00, description='房卡收益')
    assistance_program_income = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                                    description='助农收益')
    update_time = fields.BigIntField(description='更新时间')
    created = fields.BigIntField(description='创建时间')

    class Meta:
        table = "proxy_month_income"


class ProxyUserWallet(DBModel):
    """代理用户钱包"""
    id = fields.IntField(max_length=20, pk=True, description='代理（服务商id）')
    level1_proxy_id = fields.IntField(max_length=20,  description='一级代理id')
    total_income = fields.DecimalField(max_digits=10, decimal_places=2, description='总收入累计总收益')
    room_income = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00, description='房卡收益（')
    assistance_program_income = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                                    description='助农收益')

    total_amount = fields.DecimalField(max_digits=12, decimal_places=2, default=0.00, description='总推广额')
    room_amount = fields.DecimalField(max_digits=12, decimal_places=2, default=0.00, description='房卡推广总额')
    assistance_program_amount = fields.DecimalField(max_digits=12, decimal_places=2, default=0.00,
                                                    description='助农推广总额')

    level1_total_income = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                              description='一级代理（上级）获得的收益')
    level1_assistance_program_income = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                                           description='级代（上级）理获得的助农收益')
    level1_room_card_income = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                                  description='一级代理（上级）获得的房卡收益')

    update_time = fields.BigIntField(description='更新时间')
    created = fields.BigIntField(description='创建时间')

    class Meta:
        table = "proxy_user_wallet"


"""
代理订单分红明细表
"""


class ProxyOrderDividendRecords(DBModel):
    id = fields.BigIntField(max_length=28, pk=True, description='主键无意义')
    order_id = fields.BigIntField(max_length=28, description='订单id')
    proxy_id = fields.BigIntField(max_length=20, null=False, description='代理商id')
    level1_proxy_id = fields.BigIntField(max_length=20, null=False, description='一级代理id')
    player_id = fields.BigIntField(max_length=20, null=False, description='用户id')
    platform_id = fields.BigIntField(max_length=20, default=0, description='平台（厂商ID）（如有的话）')
    promotion_id = fields.BigIntField(max_length=20, default=0, description='推广码id')
    order_amount = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00, description='订单金额')
    price = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00, description='订单单价')
    dividend_rate = fields.DecimalField(max_digits=5, decimal_places=2, default=0.00, description='订单的分红比例')
    level2_dividend_rate = fields.DecimalField(max_digits=5, decimal_places=2, default=0.00, description='一级分红比例')
    proxy_income = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00, description='代理分红金额')
    level1_proxy_income = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                              description='一级代理分红金额')
    platform_income = fields.DecimalField(max_digits=10, decimal_places=2, default=0.00, description='平台收入')
    order_year = fields.CharField(max_length=4, description='余订单年')
    order_month = fields.CharField(max_length=8, description='余订单月 yyyyMM')
    order_day = fields.CharField(max_length=10, description='冗余订单日 yyyyMMdd')
    order_week_day = fields.CharField(max_length=10, description='所属周的开始日期 yyyyMMdd')
    goods_number = fields.IntField(max_length=10, default=0, description='商品数量')
    order_type = fields.IntField(max_length=10, default=0, description='商品类型')
    level = fields.IntField(default=1, description='订单等级（1、一级代理订单 2、二级代理订单）')
    status = fields.IntField(default=0, description='状态，0：未对账 1、已对账确认')
    update_time = fields.BigIntField(description='更新时间')
    order_time = fields.BigIntField(description='订单时间')
    created = fields.BigIntField(description='创建时间')

    class Meta:
        table = "proxy_order_dividend_records"


"""
推广码用户绑定关系表
"""


class ProxyPromotionRelation(DBModel):
    id = fields.BigIntField(max_length=20, pk=True, description='主键无意义')
    player_id = fields.BigIntField(max_length=28, description='订玩家id')
    proxy_id = fields.BigIntField(max_length=20, null=False, description='代理商id')
    level1_proxy_id = fields.BigIntField(max_length=20, null=False, description='一级代理id')
    promotion_type = fields.BigIntField(max_length=20, null=False, description='平台（厂商ID）（如有的话）')
    promotion_id = fields.BigIntField(max_length=20, null=False, description='订单金额')
    promotion_year = fields.CharField(max_length=4, description='余订单年 yyyy')
    promotion_month = fields.CharField(max_length=8, description='余订单月 yyyyMM')
    promotion_day = fields.CharField(max_length=10, description='冗余订单日 yyyyMMdd')
    level = fields.IntField(default=1, description='绑定等级（1、一级代理邀请 2、二级代理邀请）')
    created = fields.BigIntField(description='创建时间')

    class Meta:
        table = "proxy_promotion_relation"

        unique_together = ("player_id", "proxy_id")


class ProxyPromotionCode(DBModel):
    id = fields.BigIntField(max_length=20, pk=True, description='主键无意义')
    proxy_id = fields.BigIntField(max_length=20, description='代理id')
    url = fields.CharField(max_length=255, null=False, description='代理商id')
    promotion_code = fields.CharField(max_length=20, null=False, description='推广码')
    promotion_code_name = fields.CharField(max_length=20, null=False, description='推广码名字')
    is_deleted = fields.IntField(null=False, description='是否删除1、是 0、否')
    created = fields.BigIntField(description='创建时间')
    level = fields.IntField(default=1, description='订单等级（1、一级代理推广码 2、二级代理推广码）')

    class Meta:
        table = "proxy_promotion_code"
        unique_together = "promotion_code"

    def to_dict(self):
        return {
            'id': self.id,
            'proxy_id': self.proxy_id,
            'url': self.url,
            'promotion_code': self.promotion_code,
            'promotion_code_name': self.promotion_code_name,
            'created': self.created,
            # 其他属性
        }


"""
用户银行卡信息
"""


class ProxyUserBankCard(DBModel):
    id = fields.BigIntField(max_length=20, pk=True, description='主键无意义')
    proxy_id = fields.BigIntField(max_length=20, description='代理id')
    phone = fields.CharField(max_length=20, null=False, description='电话号码')
    name = fields.CharField(max_length=20, null=False, description='名字')
    bank_card_no = fields.CharField(max_length=32, null=False, description='银行卡号')
    card_name = fields.CharField(null=False, max_length=20, description='户名')
    sub_branch = fields.CharField(max_length=32, description='支行')
    created = fields.BigIntField(description='创建时间')

    class Meta:
        table = "proxy_user_bank_card"

    def to_dict(self):
        return {
            'id': self.id,
            'proxy_id': self.proxy_id,
            'phone': self.phone,
            'name': self.name,
            'bank_card_no': self.bank_card_no,
            'card_name': self.card_name,
            'sub_branch': self.sub_branch,
            'created': self.created,
            # 其他属性
        }


"""
代理每月结算记录
"""


class ProxyMonthSettlement(DBModel):
    id = fields.BigIntField(max_length=20, pk=True, description='主键无意义')
    proxy_id = fields.BigIntField(max_length=20, description='代理id')
    month = fields.CharField(max_length=10, null=False, description='月份 yyyyMMdd')
    year = fields.CharField(max_length=10, null=False, description='年份 yyyy')
    total_amount = fields.DecimalField(max_digits=12, decimal_places=2, null=False, description='推广额度')
    total_income = fields.DecimalField(max_digits=10, decimal_places=2, null=False, description='总收益')
    status = fields.CharField(max_length=2, default=0, null=False, description='状态')
    created = fields.BigIntField(description='创建时间')

    class Meta:
        table = "proxy_month_settlement"

    def to_dict(self):
        return {
            'id': self.id,
            'proxy_id': self.proxy_id,
            'month': self.month,
            'year': self.year,
            'amount': self.amount,
            'status': self.status,
            'created': self.created,
            # 其他属性
        }

