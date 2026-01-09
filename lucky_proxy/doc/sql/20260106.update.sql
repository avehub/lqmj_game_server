ALTER TABLE proxy_user ADD COLUMN vip_level INT default 0 COMMENT 'VIP等级1（月卡会员）、2（季卡会员）、3（年卡会员）、999（永久会员）';

ALTER TABLE proxy_user ADD COLUMN vip_expire_time BIGINT COMMENT 'vip过期时间（时间秒）';