
ALTER TABLE proxy_user ADD COLUMN upgrade_time BIGINT COMMENT '升级一级代理时间';

ALTER TABLE proxy_user ADD COLUMN opt_user_id BIGINT COMMENT '操作用户id';

ALTER TABLE proxy_promotion_relation ADD COLUMN upgrade_flag tinyint  default 0 COMMENT '升级成一级代理标志1、已升级 0、未生级';

ALTER TABLE proxy_user_wallet ADD COLUMN upgrade_flag tinyint  default 0 COMMENT '升级成一级代理标志1、已升级 0、未生级';