CREATE TABLE `proxy_month_settlement` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `proxy_id` bigint DEFAULT NULL,
  `month` varchar(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'yyyy-MM-dd',
  `total_amount` decimal(10,2) DEFAULT NULL,
  `created` bigint DEFAULT NULL,
  `status` int DEFAULT NULL,
  `total_income` decimal(10,2) DEFAULT NULL COMMENT '总收益',
  `total_order` int DEFAULT '0' COMMENT '总订单数',
  `year` varchar(4) COLLATE utf8mb4_general_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_settle_month` (`proxy_id`,`month`,`year`)
) ENGINE=InnoDB AUTO_INCREMENT=54455 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代理每月结算记录';


CREATE TABLE `proxy_order_dividend_records` (
  `id` bigint NOT NULL,
  `order_no` varchar(32) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '订单单价',
  `order_id` bigint DEFAULT NULL COMMENT '订单id',
  `promotion_id` bigint DEFAULT NULL COMMENT '推广码id',
  `level1_proxy_id` bigint DEFAULT NULL COMMENT '一级代理id',
  `proxy_id` bigint DEFAULT NULL COMMENT '代理id',
  `player_id` bigint DEFAULT NULL COMMENT '用户id',
  `goods_number` int DEFAULT NULL COMMENT '商品数量',
  `order_type` int DEFAULT NULL COMMENT '订单类型  1:房卡 2:助农订单',
  `platform_id` bigint DEFAULT '0' COMMENT '平台id(暂无)',
  `price` decimal(10,2) DEFAULT NULL COMMENT '单价',
  `order_amount` decimal(10,2) DEFAULT NULL COMMENT '订单总金额',
  `level2_dividend_rate` decimal(5,2) DEFAULT '0.00' COMMENT '一级分红比例',
  `dividend_rate` decimal(5,2) DEFAULT NULL COMMENT '分红比例',
  `level1_proxy_income` decimal(10,2) DEFAULT '0.00' COMMENT '一级代理分红金额',
  `proxy_income` decimal(10,2) DEFAULT NULL COMMENT '代理收入',
  `platform_income` decimal(10,2) DEFAULT NULL COMMENT '平台收入',
  `order_year` varchar(4) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '订单年：yyyy',
  `order_month` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '订单月yyyyMM',
  `order_day` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '订单日 yyyyMMdd',
  `order_week_day` varchar(10) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '所属周开始日期',
  `status` tinyint DEFAULT '0' COMMENT '状态（暂无用）',
  `order_time` bigint DEFAULT NULL COMMENT '订单时间戳',
  `update_time` bigint DEFAULT NULL COMMENT '更新时间',
  `created` bigint DEFAULT NULL COMMENT '创建时间',
  `level` int DEFAULT NULL COMMENT '订单等级（1、一级代理订单 2、二级代理订单）',
  PRIMARY KEY (`id`),
  KEY `idx_player_id` (`player_id`),
  KEY `idx_div_proxid` (`proxy_id`,`order_month`,`order_day`),
  KEY `idx_div_level1_proxid` (`level1_proxy_id`,`order_month`,`order_day`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;


CREATE TABLE `proxy_promotion_relation` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `player_id` bigint DEFAULT NULL COMMENT '游戏玩家id',
  `proxy_id` bigint DEFAULT NULL COMMENT '代理（服务商id）',
  `promotion_type` int DEFAULT NULL COMMENT '推广类型(1:邀请码 2:推广链接)',
  `promotion_id` bigint DEFAULT NULL,
  `promotion_year` varchar(4) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '数据(年)',
  `promotion_month` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '数据(月)',
  `promotion_day` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '数据(日)',
  `created` bigint DEFAULT NULL COMMENT '创建时间',
  `level` int DEFAULT NULL COMMENT '绑定等级（1、一级代理邀请 2、二级代理邀请）',
  `level1_proxy_id` bigint DEFAULT NULL COMMENT '一级代理id',
  `total_amount` decimal(12,2) DEFAULT '0.00',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_ppr_puid` (`player_id`) USING BTREE,
  KEY `idx_ppr_proxy_id` (`proxy_id`),
  KEY `idx_ppr_level1_proxy_id` (`level1_proxy_id`)
) ENGINE=InnoDB AUTO_INCREMENT=56 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代理邀请关系绑定';

CREATE TABLE `proxy_settlement_log` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `platform_id` bigint DEFAULT '0' COMMENT '平台id',
  `month` varchar(12) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'yyyy-MM-dd',
  `total_amount` decimal(10,2) DEFAULT NULL,
  `created` bigint DEFAULT NULL,
  `settlement_status` int DEFAULT NULL,
  `total_income` decimal(10,2) DEFAULT NULL COMMENT '总收益',
  `total_order` int DEFAULT '0' COMMENT '总订单数',
  `year` varchar(4) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `start_time` bigint DEFAULT NULL,
  `end_time` bigint DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11055 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='每月结算job日志';


CREATE TABLE `proxy_user` (
  `id` bigint NOT NULL DEFAULT '0',
  `proxy_name` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '代理名字（不是昵称）（暂无用）',
  `unionid` varchar(128) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '微信开放平台唯一ID',
  `create_by` int DEFAULT NULL COMMENT '创建代理的管理员id',
  `created` int DEFAULT '0' COMMENT '创建时间',
  `status` int DEFAULT '1' COMMENT '状态1、正常 0、被封禁',
  `proxy_level` int DEFAULT '1' COMMENT '代理等级 ',
  `phone` varchar(20) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '手机号',
  `level1_proxy_id` bigint DEFAULT NULL COMMENT '一级代理id',
  `auth_status` int DEFAULT '0' COMMENT '认证状态 1、已认证 0、未认证',
  `promotion_code` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '推广码（10位唯一字符）',
  `assistance_program_rate` decimal(4,2) DEFAULT '0.00' COMMENT '助农提成比例',
  `room_card_rate` decimal(4,2) DEFAULT '0.00' COMMENT '房卡提成比例',
  `level2_total_player` int DEFAULT '0' COMMENT '下级邀请总玩家',
  `join_day` varchar(10) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT 'yyyy-MM-dd',
  `is_deleted` int DEFAULT '0' COMMENT '1、是 0否',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_pu_unionid` (`unionid`),
  KEY `idx_pu_phone` (`phone`),
  KEY `idx_pu_pr_code` (`promotion_code`,`is_deleted`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代理用户表';


CREATE TABLE `proxy_user_bank_card` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键',
  `proxy_id` bigint DEFAULT NULL COMMENT '代理id',
  `phone` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '联系电话',
  `name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '姓名',
  `bank_card_no` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '卡号',
  `card_name` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '户名',
  `sub_branch` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '支行',
  `created` bigint DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代理银行卡';


CREATE TABLE `proxy_user_wallet` (
  `id` int NOT NULL COMMENT '代理id',
  `total_player` int DEFAULT '0' COMMENT '邀请总玩家',
  `total_income` decimal(10,2) DEFAULT '0.00' COMMENT '总收入累计总收益',
  `room_income` decimal(10,2) DEFAULT '0.00' COMMENT '房卡收益',
  `assistance_program_income` decimal(10,2) DEFAULT '0.00' COMMENT '助农推广收益',
  `total_amount` decimal(12,2) DEFAULT '0.00' COMMENT '总推广额',
  `room_amount` decimal(12,2) DEFAULT '0.00' COMMENT '房卡推广总额',
  `assistance_program_amount` decimal(12,2) DEFAULT '0.00' COMMENT '助农推广总额',
  `level1_total_income` decimal(10,2) DEFAULT '0.00' COMMENT '一级代理（上级）获得的总收益',
  `level1_assistance_program_income` decimal(10,2) DEFAULT '0.00' COMMENT '一级代（上级）理获得的助农收益',
  `level1_room_income` decimal(10,2) DEFAULT '0.00' COMMENT '一级代理（上级）获得的房卡收益',
  `update_time` bigint DEFAULT NULL COMMENT '更新时间',
  `created` bigint DEFAULT NULL COMMENT '创建时间',
  `level1_proxy_id` int DEFAULT NULL COMMENT '一级代理id',
  `proxy_level` int DEFAULT '1' COMMENT '代理等级1or2',
  `level2_total_player` int DEFAULT '0',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_pw_level1` (`level1_proxy_id`,`proxy_level`) USING BTREE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='代理用户钱包';

