-- 赛事模块发版执行SQL
ALTER TABLE `user` 
ADD COLUMN `future_value` int(0) UNSIGNED NULL DEFAULT 0 COMMENT '福袋' AFTER `yellow_diamond`,
ADD COLUMN `status`  tinyint NOT NULL DEFAULT '0' COMMENT '福袋' AFTER `用户状态：0正常 1注销`;

CREATE TABLE `tournament_rewards` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '奖励ID',
  `round_type` tinyint NOT NULL COMMENT '场次类型:1-线上周赛,2-线下总决赛',
  `rank_start` int NOT NULL COMMENT '奖励范围排名起始值，默认1',
  `rank_end` int NOT NULL COMMENT '奖励范围排名结束，默认10',
  `reward_content` json DEFAULT NULL COMMENT '奖励内容',
  `reward_description` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '奖励描述',
  `created` bigint DEFAULT '0',
  `updated` bigint DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_round_type` (`round_type`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='奖励配置表';

CREATE TABLE `tournament_cycle` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '周期ID',
  `template_id` bigint NOT NULL COMMENT '关联模板ID',
  `reward_id` bigint unsigned NOT NULL COMMENT '关联奖励ID',
  `cycle_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '周期名称:2026年1月月赛',
  `reward_name` varchar(64) COLLATE utf8mb4_general_ci NOT NULL COMMENT '邮件奖励名称',
  `cycle_year` int NOT NULL COMMENT '年份:2026',
  `cycle_month` tinyint NOT NULL COMMENT '月份:1-12',
  `cycle_start_date` date NOT NULL COMMENT '周期开始日期',
  `cycle_end_date` date NOT NULL COMMENT '周期结束日期',
  `status` tinyint NOT NULL DEFAULT '0' COMMENT '状态:0-未开始,1-进行中,2-已结束,3-已归档',
  `cycle_type` tinyint DEFAULT '0' COMMENT '赛季类型：0周赛 1热身赛',
  `content` varchar(255) COLLATE utf8mb4_general_ci DEFAULT NULL COMMENT '其他赛事内容：json存储',
  `created` bigint DEFAULT '0',
  `updated` bigint DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`),
  KEY `idx_date_range` (`cycle_start_date`,`cycle_end_date`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='赛事周期表';

CREATE TABLE `tournament_cycle_leaderboard` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '排行榜ID',
  `cycle_id` bigint NOT NULL COMMENT '关联周期ID',
  `uid` bigint NOT NULL COMMENT '用户ID',
  `total_points` int NOT NULL DEFAULT '0' COMMENT '总积分',
  `participated_rounds` int DEFAULT '0' COMMENT '参与场次数',
  `created` bigint DEFAULT '0',
  `updated` bigint DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_cycle_user` (`cycle_id`,`uid`),
  KEY `idx_cycle_rank` (`cycle_id`,`total_points` DESC),
  KEY `idx_user_cycle` (`uid`,`cycle_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='周期排行榜表';

CREATE TABLE `tournament_registration` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '报名ID',
  `cycle_id` bigint NOT NULL COMMENT '关联周期ID',
  `uid` bigint NOT NULL COMMENT '用户ID',
  `register_type` tinyint NOT NULL COMMENT '报名类型:1-主动报名,2-邀请报名',
  `register_time` datetime NOT NULL COMMENT '报名时间',
  `register_status` tinyint NOT NULL DEFAULT '1' COMMENT '报名状态:1-已报名,2-已取消,3-已确认参赛',
  `pid` bigint DEFAULT NULL COMMENT '邀请用户ID',
  `created` bigint DEFAULT '0',
  `updated` bigint DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_round_user` (`cycle_id`,`uid`),
  KEY `idx_user_status` (`uid`,`register_status`),
  KEY `idx_round_status` (`cycle_id`,`register_status`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户报名表';

CREATE TABLE `tournament_rules` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '规则ID',
  `template_id` bigint NOT NULL COMMENT '关联模板ID',
  `rule_type` tinyint unsigned NOT NULL COMMENT '规则类型: 1-线上,0-线下',
  `rule_content` json NOT NULL COMMENT '规则内容JSON',
  `created` bigint DEFAULT '0',
  `updated` bigint DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_round_type` (`template_id`,`rule_type`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='赛事规则表';

CREATE TABLE `tournament_template` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '模板ID',
  `template_name` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL COMMENT '模板名称:月赛/季赛等',
  `template_type` tinyint NOT NULL COMMENT '赛事类型:1-月赛,2-季赛,预留扩展',
  `cycle_type` tinyint NOT NULL COMMENT '周期类型:1-自然月,2-自然季',
  `rounds_per_cycle` tinyint NOT NULL COMMENT '每周期场次:月赛为4',
  `online_rounds` tinyint NOT NULL COMMENT '线上场次数:月赛为3',
  `final_round_offline` tinyint NOT NULL DEFAULT '1' COMMENT '总决赛是否线下:1-是,0-否',
  `qualifier_count` int NOT NULL COMMENT '晋级总决赛人数:10',
  `status` tinyint NOT NULL DEFAULT '1' COMMENT '模板状态:1-启用,0-停用',
  `created` bigint DEFAULT '0',
  `updated` bigint DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `idx_type_status` (`template_type`,`status`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='赛事模板配置表';

CREATE TABLE `tournament_user_points` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '积分ID',
  `cycle_id` bigint NOT NULL COMMENT '关联赛事周期ID',
  `uid` bigint NOT NULL COMMENT '用户ID',
  `ticket` int NOT NULL DEFAULT '0' COMMENT '门票',
  `score` int NOT NULL DEFAULT '0' COMMENT '得分',
  `created` bigint DEFAULT '0',
  `updated` bigint DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_round_user` (`cycle_id`,`uid`),
  KEY `idx_user_round` (`uid`,`cycle_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='用户赛事积分表';

CREATE TABLE `conf_competition` (
  `id` int NOT NULL AUTO_INCREMENT,
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `name` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '赛事名称',
  `cs_type` int NOT NULL DEFAULT '0' COMMENT '子服务类型',
  `competition_type` smallint NOT NULL DEFAULT '0' COMMENT '赛事类型',
  `rule_detail` json DEFAULT NULL COMMENT '规则详情',
  `max_player` int DEFAULT NULL COMMENT '最大玩家数',
  `price` int DEFAULT '0' COMMENT '门票价格',
  `price_type` smallint NOT NULL DEFAULT '3' COMMENT '支付类型',
  `status` smallint NOT NULL DEFAULT '2' COMMENT '赛事状态',
  `start_time` bigint DEFAULT '0' COMMENT '开始时间',
  `end_time` bigint DEFAULT '0' COMMENT '结束时间',
  `total_round` smallint DEFAULT '1' COMMENT '总局数',
  `play_type` smallint NOT NULL DEFAULT '3' COMMENT '玩法类型',
  `max_match_player` smallint DEFAULT '0' COMMENT '最大开局人数',
  `daily_start_time` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '每日开始时间',
  `daily_end_time` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL COMMENT '每日结束时间',
  `total_match_round` smallint DEFAULT '1' COMMENT '比赛总轮次',
  `cycle_id` smallint DEFAULT '1' COMMENT '周期ID',
  PRIMARY KEY (`id`) USING BTREE,
  KEY `idx_conf_compet_created_0c41f1` (`created`) USING BTREE,
  KEY `idx_conf_compet_cs_type_8a84ef` (`cs_type`) USING BTREE
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='赛事配置表 ';

CREATE TABLE `logout_user` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `uid` int NOT NULL AUTO_INCREMENT COMMENT '玩家ID',
  `name` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '玩家昵称',
  `avatar` varchar(256) DEFAULT '' COMMENT '头像地址',
  `sex` smallint NOT NULL DEFAULT '0' COMMENT '性别',
  `phone` varchar(18) DEFAULT NULL COMMENT '手机号码',
  `email` varchar(256) DEFAULT NULL COMMENT '邮箱',
  `address` varchar(256) DEFAULT '' COMMENT '所在地址',
  `id_card` varchar(20) DEFAULT '' COMMENT '身份证',
  `real_name` varchar(32) DEFAULT '' COMMENT '玩家真实姓名',
  `pi` varchar(64) NOT NULL DEFAULT '' COMMENT '已通过实名认证用户的唯一标识',
  `discount` float(3,2) unsigned DEFAULT '1.00' COMMENT '消费折扣',
  `gold` decimal(65,2) DEFAULT '0.00' COMMENT '金币',
  `diamond` int DEFAULT '0' COMMENT '钻石',
  `room_card` int DEFAULT '0' COMMENT '房卡',
  `yellow_diamond` int DEFAULT '0' COMMENT '黄钻',
  `vip` smallint DEFAULT '0' COMMENT 'VIP等级',
  `platform` smallint NOT NULL COMMENT '平台：1网页 2微信公众号 3原生app 4微信小游戏 5支付宝小游戏 6抖音小游戏',
  `dev_ident` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '设备标识',
  `ip` varchar(128) DEFAULT '' COMMENT '登陆IP',
  `region` varchar(20) DEFAULT '' COMMENT '地区/行政区域',
  `country` varchar(16) DEFAULT 'CN' COMMENT '国家域名',
  `openid` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '小游戏授权用户唯一标识',
  `unionid` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci DEFAULT '' COMMENT '平台用户授权唯一标识',
  `wechat` smallint unsigned DEFAULT '0' COMMENT '微信平台绑定状态：1已绑定',
  `apple_id` varchar(128) DEFAULT '' COMMENT '苹果平台用户授权唯一标识',
  `future_value` int unsigned DEFAULT '0' COMMENT '福袋',
  `updated` bigint DEFAULT '0' COMMENT '更新时间',
  `status` smallint DEFAULT NULL COMMENT '用户状态：0正常 1注销中 2已注销',
  UNIQUE KEY `uid` (`uid`),
  UNIQUE KEY `uid_user_platfor_b2b99c` (`platform`,`openid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='注销用户表';

-- 奖励内容
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 51, 4, 1, '赛事奖励-晋级资格', '{\"rewards\": [{\"img\": \"tournament/qualified.png\", \"type\": \"qualified\", \"title\": \"晋级资格x1\", \"amount\": 1}], \"good_suk\": \"IRLJQAMF\"}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 52, 4, 2, '赛事奖励-10000福袋', '{\"rewards\": [{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x10000\", \"amount\": 10000}], \"good_suk\": \"OIWARYRC\"}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 53, 4, 3, '赛事奖励-5000福袋', '{\"rewards\": [{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x5000\", \"amount\": 5000}], \"good_suk\": \"YZRWWAOO\"}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 54, 4, 4, '赛事奖励-钻石礼包', '{\"rewards\": [{\"img\": \"store/sc3.png\", \"type\": \"diamond\", \"title\": \"钻石x200\", \"amount\": 200}], \"good_suk\": \"VWRVIABV\"}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 57, 5, 1, '线下决赛-冠军', '{\"rewards\": [{\"img\": \"\", \"type\": \"money\", \"title\": \"现金x20000\", \"amount\": 20000}, {\"img\": \"\", \"type\": \"kind\", \"title\": \"水晶奖杯x1\", \"amount\": 1}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 58, 5, 2, '线下决赛-亚军', '{\"rewards\": [{\"img\": \"\", \"type\": \"money\", \"title\": \"现金x5000\", \"amount\": 5000}, {\"img\": \"\", \"type\": \"kind\", \"title\": \"银质奖杯x1\", \"amount\": 1}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 59, 5, 3, '线下决赛-季军', '{\"rewards\": [{\"img\": \"\", \"type\": \"money\", \"title\": \"现金x2000\", \"amount\": 2000}, {\"img\": \"\", \"type\": \"kind\", \"title\": \"铜质奖杯x1\", \"amount\": 1}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 60, 5, 4, '线下决赛-4~8名', '{\"rewards\": [{\"img\": \"\", \"type\": \"money\", \"title\": \"现金x1000\", \"amount\": 1000}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 61, 5, 5, '线下决赛-9~18名', '{\"rewards\": [{\"img\": \"\", \"type\": \"money\", \"title\": \"现金x500\", \"amount\": 500}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 62, 6, 1, '赛事奖励-15福袋', '{\"rewards\": [{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x15\", \"amount\": 15}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 63, 6, 2, '赛事奖励-10福袋', '{\"rewards\": [{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x10\", \"amount\": 10}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 64, 6, 3, '赛事奖励-8福袋', '{\"rewards\": [{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x8\", \"amount\": 8}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 65, 6, 4, '赛事奖励-3福袋', '{\"rewards\": [{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x3\", \"amount\": 3}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 66, 6, 1, '赛事奖励-5000福袋', '{\"rewards\": [{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x5000\", \"amount\": 5000}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 67, 6, 2, '赛事奖励-3000福袋', '{\"rewards\": [{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x3000\", \"amount\": 3000}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 68, 6, 3, '赛事奖励-500福袋', '{\"rewards\": [{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x500\", \"amount\": 500}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 69, 6, 4, '赛事奖励-100福袋', '{\"rewards\": [{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x100\", \"amount\": 100}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 70, 6, 5, '赛事奖励-30福袋', '{\"rewards\": [{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x30\", \"amount\": 30}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 71, 6, 1, '热身赛-第1名', '{\"rewards\": [{\"img\": \"tournament/score.png\", \"type\": \"score\", \"title\": \"赛事积分x50\", \"amount\": 50}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 72, 6, 2, '热身赛-第2~3名', '{\"rewards\": [{\"img\": \"tournament/score.png\", \"type\": \"score\", \"title\": \"赛事积分x30\", \"amount\": 30}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 73, 6, 3, '热身赛-第4~10名', '{\"rewards\": [{\"img\": \"tournament/score.png\", \"type\": \"score\", \"title\": \"赛事积分x15\", \"amount\": 15}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 74, 6, 4, '热身赛-第11~30名', '{\"rewards\": [{\"img\": \"tournament/score.png\", \"type\": \"score\", \"title\": \"赛事积分x8\", \"amount\": 8}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 75, 6, 5, '热身赛-第31~100名', '{\"rewards\": [{\"img\": \"tournament/score.png\", \"type\": \"score\", \"title\": \"赛事积分x3\", \"amount\": 3}]}', 0);
INSERT INTO `lucky_game`.`awards` (`created`, `award_id`, `type`, `level`, `name`, `content`, `updated`) VALUES (0, 76, 6, 5, '赛事奖励-20福袋', '{\"rewards\": [{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x20\", \"amount\": 20}]}', 0);


-- 商品表
UPDATE `lucky_game`.`goods` SET `created` = 0, `sid` = 6, `kind` = 0, `type` = 4, `currency` = 5, `sku` = 'NHEYRPIO', `total` = -1, `purchase_limit` = '', `name` = '1000张房卡', `img` = 'store/scfk.png', `desc` = '', `original` = 1000.00, `price` = 1000.00, `content` = '{\"img\": \"store/scfk.png\", \"type\": \"room_card\", \"title\": \"房卡x1000\", \"amount\": 1000}', `status` = 0, `up_time` = NULL, `down_time` = NULL, `bag_type` = 0, `rank` = 2, `updated` = 0 WHERE `good_id` = 54;
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 55, 0, 1, 14, 0, 'IRLJQAMF', -1, '', '晋级资格', 'tournament/qualified.png', NULL, 1.00, 0.00, '{\"img\": \"tournament/qualified.png\", \"type\": \"qualified\", \"title\": \"晋级资格x1\", \"amount\": 1, \"describe\": \"城市挑战赛决赛资格，请使用赶紧填个人信息，别让福利飞啦！\"}', 1, NULL, NULL, 1, 0, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 56, 0, 1, 13, 0, 'OIWARYRC', -1, '', '10000福袋', 'tournament/future.png', NULL, 10000.00, 0.00, '{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x10000\", \"amount\": 10000, \"describe\": \"福袋\"}', 1, NULL, NULL, 0, 2, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 57, 0, 1, 13, 0, 'YZRWWAOO', -1, '', '5000福袋', 'tournament/future.png', NULL, 5000.00, 0.00, '{\"img\": \"tournament/future.png\", \"type\": \"future_value\", \"title\": \"福袋x5000\", \"amount\": 5000, \"describe\": \"福袋\"}', 1, NULL, NULL, 0, 2, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 58, 0, 0, 13, 0, 'VWRVIABV', -1, '', '200钻石', 'store/sc3.png', NULL, 500.00, 0.00, '{\"img\": \"store/sc3.png\", \"type\": \"diamond\", \"title\": \"钻石x200\", \"amount\": 200}', 1, NULL, NULL, 0, 2, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 59, 7, 1, 15, 5, 'WCRVIABC', 10000, '', '普安红茶', 'tournament/tea.png', 'com.leqi.network.hjmj.tea.39.9', 0.10, 0.10, '{\"img\": \"tournament/tea.png\", \"type\": \"good\", \"title\": \"茶叶x1\", \"amount\": 1, \"ticket\": 50, \"describe\": \"助农公益产品，请使用赶紧填个人信息！\", \"ticket_img\": \"tournament/ticket.png\"}', 1, NULL, NULL, 1, 2, 1769772501);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 77, 10, 2, 17, 6, 'AHEYRPIC', -1, '', '10元话费', 'store/mr_10.png', '', 100.00, 100.00, '{\"img\": \"store/mr_10.png\", \"cost\": 10, \"type\": \"future_value\", \"title\": \"10元话费\", \"amount\": 100, \"describe\": \"面值 10 元，可抵扣手机话费充值金额\"}', 1, NULL, NULL, 1, 9, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 78, 10, 2, 17, 6, 'BHEYRPIC', -1, '', '30元话费', 'store/mr_30.png', '', 300.00, 300.00, '{\"img\": \"store/mr_30.png\", \"cost\": 30, \"type\": \"future_value\", \"title\": \"30元话费\", \"amount\": 300, \"describe\": \"面值 30 元，可抵扣手机话费充值金额\"}', 1, NULL, NULL, 1, 8, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 79, 10, 2, 17, 6, 'CHEYRPIC', -1, '', '50元话费', 'store/mr_50.png', '', 500.00, 500.00, '{\"img\": \"store/mr_50.png\", \"cost\": 50, \"type\": \"future_value\", \"title\": \"50元话费\", \"amount\": 500, \"describe\": \"面值 50 元，可抵扣手机话费充值金额\"}', 1, NULL, NULL, 1, 7, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 80, 10, 1, 18, 6, 'AAEYRPIC', -1, '', '峰林布依景区门票', 'store/cy_flby.png', '', 700.00, 700.00, '{\"img\": \"store/cy_flby.png\", \"type\": \"future_value\", \"title\": \"峰林布依景区门票\", \"amount\": 700, \"describe\": \"热门景区入园凭证，畅游布依特色风光\"}', 1, NULL, NULL, 1, 9, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 81, 10, 1, 18, 6, 'ABEYRPIC', -1, '', '马岭河峡谷景区门票', 'store/cy_mlh.png', '', 700.00, 700.00, '{\"img\": \"store/cy_mlh.png\", \"type\": \"future_value\", \"title\": \"马岭河峡谷景区门票\", \"amount\": 700, \"describe\": \"热门景区入园凭证，畅游布依特色风光\"}', 1, NULL, NULL, 1, 8, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 95, 10, 1, 18, 6, 'ACEYRPIC', -1, '', '万峰林景区门票', 'store/cy_wfl.png', '', 900.00, 900.00, '{\"img\": \"store/cy_wfl.png\", \"type\": \"future_value\", \"title\": \"万峰林景区门票\", \"amount\": 1, \"describe\": \"热门景区入园凭证，尽赏峰林壮阔景观\"}', 1, NULL, NULL, 1, 7, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 96, 10, 1, 18, 6, 'ADEYRPIC', -1, '', '云屯沐云温泉票', 'store/cy_ytwq.png', '', 1980.00, 1980.00, '{\"img\": \"store/cy_ytwq.png\", \"type\": \"future_value\", \"title\": \"云屯沐云温泉票\", \"amount\": 1, \"describe\": \"轻奢温泉体验票，享受舒适泡汤时光\"}', 1, NULL, NULL, 1, 6, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 97, 10, 1, 18, 6, 'AEEYRPIC', -1, '', '云屯沐云高级房一晚', 'store/cy_ytjd.png', '', 9800.00, 9800.00, '{\"img\": \"store/cy_ytjd.png\", \"type\": \"future_value\", \"title\": \"云屯沐云高级房一晚\", \"amount\": 1, \"describe\": \"高端住宿体验，入住舒适高级客房一晚\"}', 1, NULL, NULL, 1, 5, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 98, 10, 1, 19, 6, 'AAAYRPIC', -1, '', '品牌快充充电宝', 'store/dq_1.png', '', 1000.00, 1000.00, '{\"img\": \"store/dq_1.png\", \"type\": \"future_value\", \"title\": \"品牌快充充电宝\", \"amount\": 1, \"describe\": \"知名品牌出品，支持快速充电的便携移动电源\"}', 1, NULL, NULL, 1, 9, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 99, 10, 1, 19, 6, 'ABBYRPIC', -1, '', '品牌TES蓝牙耳机', 'store/dq_4.png', '', 1800.00, 1800.00, '{\"img\": \"store/dq_4.png\", \"type\": \"future_value\", \"title\": \"品牌TWS蓝牙耳机\", \"amount\": 1, \"describe\": \"知名品牌无线耳机，支持蓝牙连接，音质清晰\"}', 1, NULL, NULL, 1, 8, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 100, 10, 1, 19, 6, 'ACCYRPIC', -1, '', '品牌电动牙刷', 'store/dq_2.png', '', 2500.00, 2500.00, '{\"img\": \"store/dq_2.png\", \"type\": \"future_value\", \"title\": \"品牌电动牙刷（基础款）\", \"amount\": 1, \"describe\": \"知名品牌基础款电动牙刷，清洁牙齿更省力\"}', 1, NULL, NULL, 1, 7, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 101, 10, 1, 19, 6, 'ADDYRPIC', -1, '', '品牌智能音箱', 'store/dq_5.png', '', 3000.00, 3000.00, '{\"img\": \"store/dq_5.png\", \"type\": \"future_value\", \"title\": \"品牌智能音箱\", \"amount\": 1, \"describe\": \"知名品牌智能设备，支持语音交互、音乐播放等功能\"}', 1, NULL, NULL, 1, 6, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 102, 10, 1, 19, 6, 'AEFYRPIC', -1, '', '品牌迷你筋膜枪', 'store/dq_3.png', '', 4000.00, 4000.00, '{\"img\": \"store/dq_3.png\", \"type\": \"future_value\", \"title\": \"品牌迷你筋膜枪\", \"amount\": 1, \"describe\": \"知名品牌便携筋膜枪，缓解肌肉酸痛，放松身体\"}', 1, NULL, NULL, 1, 5, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 103, 10, 1, 20, 6, 'AAAYRPIA', -1, '', '特色零食组合包', 'store/qw_4.png', '', 600.00, 600.00, '{\"img\": \"store/qw_4.png\", \"type\": \"future_value\", \"title\": \"兴义特色零食组合包\", \"amount\": 1, \"describe\": \"地域风味尝鲜礼包，汇集兴义本地特色零食\"}', 1, NULL, NULL, 1, 9, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 104, 10, 1, 20, 6, 'ABBYRPIB', -1, '', '万峰林大米（5KG精品装）', 'store/qw_2.png', '', 800.00, 800.00, '{\"img\": \"store/qw_2.png\", \"type\": \"future_value\", \"title\": \"万峰林大米（5KG精品装）\", \"amount\": 1, \"describe\": \"5 公斤精品装优质大米，健康主食甄选\"}', 1, NULL, NULL, 1, 8, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 105, 10, 1, 20, 6, 'ACCYRPID', -1, '', '精品茶叶礼盒', 'store/qw_1.png', '', 2200.00, 2200.00, '{\"img\": \"store/qw_1.png\", \"type\": \"future_value\", \"title\": \"精品茶叶 / 咖啡礼盒\", \"amount\": 1, \"describe\": \"高品质茶叶与咖啡组合礼盒，健康饮品之选\"}', 1, NULL, NULL, 1, 7, 0);
INSERT INTO `lucky_game`.`goods` (`created`, `good_id`, `sid`, `kind`, `type`, `currency`, `sku`, `total`, `purchase_limit`, `name`, `img`, `desc`, `original`, `price`, `content`, `status`, `up_time`, `down_time`, `bag_type`, `rank`, `updated`) VALUES (0, 106, 10, 1, 20, 6, 'AEFYRPIF', -1, '', '高端食材滋补礼盒', 'store/qw_5.png', '', 4500.00, 4500.00, '{\"img\": \"store/qw_5.png\", \"type\": \"future_value\", \"title\": \"高端食材滋补礼盒\", \"amount\": 1, \"describe\": \"甄选高端滋补食材，营养丰富的送礼佳品\"}', 1, NULL, NULL, 1, 5, 0);


-- 赛事相关
INSERT INTO `lucky_game`.`tournament_cycle` (`id`, `template_id`, `reward_id`, `cycle_name`, `reward_name`, `cycle_year`, `cycle_month`, `cycle_start_date`, `cycle_end_date`, `status`, `cycle_type`, `content`, `created`, `updated`) VALUES (9, 1, 4, '热身赛I', '金州杯大奖赛热身赛I', 2026, 2, '2026-02-02', '2026-02-08', 0, 1, '{\"label\": \"第一周\"}', 0, 0);
INSERT INTO `lucky_game`.`tournament_cycle` (`id`, `template_id`, `reward_id`, `cycle_name`, `reward_name`, `cycle_year`, `cycle_month`, `cycle_start_date`, `cycle_end_date`, `status`, `cycle_type`, `content`, `created`, `updated`) VALUES (10, 1, 4, '热身赛II', '金州杯大奖赛热身赛II', 2026, 2, '2026-02-09', '2026-02-15', 0, 1, '{\"label\": \"第二周\"}', 0, 0);
INSERT INTO `lucky_game`.`tournament_cycle` (`id`, `template_id`, `reward_id`, `cycle_name`, `reward_name`, `cycle_year`, `cycle_month`, `cycle_start_date`, `cycle_end_date`, `status`, `cycle_type`, `content`, `created`, `updated`) VALUES (11, 1, 4, '热身赛III', '金州杯大奖赛热身赛III', 2026, 2, '2026-02-16', '2026-02-22', 0, 1, '{\"label\": \"第三周\"}', 0, 0);
INSERT INTO `lucky_game`.`tournament_cycle` (`id`, `template_id`, `reward_id`, `cycle_name`, `reward_name`, `cycle_year`, `cycle_month`, `cycle_start_date`, `cycle_end_date`, `status`, `cycle_type`, `content`, `created`, `updated`) VALUES (12, 1, 4, '热身赛IV', '金州杯大奖赛热身赛IV', 2026, 2, '2026-02-23', '2026-03-01', 0, 1, '{\"label\": \"第四周\"}', 0, 0);
INSERT INTO `lucky_game`.`tournament_cycle` (`id`, `template_id`, `reward_id`, `cycle_name`, `reward_name`, `cycle_year`, `cycle_month`, `cycle_start_date`, `cycle_end_date`, `status`, `cycle_type`, `content`, `created`, `updated`) VALUES (13, 1, 1, '周选赛I', '金州杯大奖赛周选赛I', 2026, 2, '2026-03-02', '2026-03-08', 0, 0, '{\"label\": \"第一周\"}', 0, 0);
INSERT INTO `lucky_game`.`tournament_cycle` (`id`, `template_id`, `reward_id`, `cycle_name`, `reward_name`, `cycle_year`, `cycle_month`, `cycle_start_date`, `cycle_end_date`, `status`, `cycle_type`, `content`, `created`, `updated`) VALUES (14, 1, 1, '周选赛II', '金州杯大奖赛周选赛II', 2026, 2, '2026-03-09', '2026-03-15', 0, 0, '{\"label\": \"第二周\"}', 0, 0);
INSERT INTO `lucky_game`.`tournament_cycle` (`id`, `template_id`, `reward_id`, `cycle_name`, `reward_name`, `cycle_year`, `cycle_month`, `cycle_start_date`, `cycle_end_date`, `status`, `cycle_type`, `content`, `created`, `updated`) VALUES (15, 1, 1, '周选赛III', '金州杯大奖赛周选赛III', 2026, 2, '2026-03-16', '2026-03-22', 0, 0, '{\"label\": \"第三周\"}', 0, 0);
INSERT INTO `lucky_game`.`tournament_cycle` (`id`, `template_id`, `reward_id`, `cycle_name`, `reward_name`, `cycle_year`, `cycle_month`, `cycle_start_date`, `cycle_end_date`, `status`, `cycle_type`, `content`, `created`, `updated`) VALUES (16, 1, 1, '周选赛IV', '金州杯大奖赛周选赛IV', 2026, 2, '2026-03-23', '2026-03-29', 0, 0, '{\"label\": \"第四周\"}', 0, 0);
INSERT INTO `lucky_game`.`tournament_cycle` (`id`, `template_id`, `reward_id`, `cycle_name`, `reward_name`, `cycle_year`, `cycle_month`, `cycle_start_date`, `cycle_end_date`, `status`, `cycle_type`, `content`, `created`, `updated`) VALUES (17, 1, 2, '线下总决赛', '金州杯大奖赛总决赛', 2026, 2, '2026-04-04', '2026-04-04', 0, 0, '{\"label\": \"第一周\"}', 0, 0);

INSERT INTO `lucky_game`.`tournament_rewards` (`id`, `round_type`, `rank_start`, `rank_end`, `reward_content`, `reward_description`, `created`, `updated`) VALUES (1, 1, 1, 20, '[{\"award_ids\": [51, 52], \"ranking_end\": 1, \"final_ticket\": 1, \"ranking_start\": 1}, {\"award_ids\": [51, 53], \"ranking_end\": 3, \"final_ticket\": 1, \"ranking_start\": 2}, {\"award_ids\": [51, 70], \"ranking_end\": 20, \"final_ticket\": 1, \"ranking_start\": 4}]', '积分赛事线上比赛前20名奖励', 0, 0);
INSERT INTO `lucky_game`.`tournament_rewards` (`id`, `round_type`, `rank_start`, `rank_end`, `reward_content`, `reward_description`, `created`, `updated`) VALUES (2, 2, 1, 18, '[{\"award_ids\": [57], \"ranking_end\": 1, \"ranking_start\": 1}, {\"award_ids\": [58], \"ranking_end\": 2, \"ranking_start\": 2}, {\"award_ids\": [59], \"ranking_end\": 3, \"ranking_start\": 3}, {\"award_ids\": [60], \"ranking_end\": 8, \"ranking_start\": 4}, {\"award_ids\": [61], \"ranking_end\": 18, \"ranking_start\": 9}]', '积分赛事线下比赛前18名奖励', 0, 0);
INSERT INTO `lucky_game`.`tournament_rewards` (`id`, `round_type`, `rank_start`, `rank_end`, `reward_content`, `reward_description`, `created`, `updated`) VALUES (3, 0, 1, 12, '[{\"award_ids\": [62], \"ranking_end\": 1, \"ranking_start\": 1}, {\"award_ids\": [63], \"ranking_end\": 2, \"ranking_start\": 2}, {\"award_ids\": [64], \"ranking_end\": 3, \"ranking_start\": 3}, {\"award_ids\": [65], \"ranking_end\": 12, \"ranking_start\": 4}]', '线上热身赛每轮前12名奖励', 0, 0);
INSERT INTO `lucky_game`.`tournament_rewards` (`id`, `round_type`, `rank_start`, `rank_end`, `reward_content`, `reward_description`, `created`, `updated`) VALUES (4, 3, 1, 100, '[{\"award_ids\": [66], \"ranking_end\": 1, \"ranking_start\": 1}, {\"award_ids\": [67], \"ranking_end\": 3, \"ranking_start\": 2}, {\"award_ids\": [68], \"ranking_end\": 10, \"ranking_start\": 4}, {\"award_ids\": [69], \"ranking_end\": 30, \"ranking_start\": 11}, {\"award_ids\": [70], \"ranking_end\": 100, \"ranking_start\": 31}]', '线上热身赛结算前100名奖励', 0, 0);
INSERT INTO `lucky_game`.`tournament_rewards` (`id`, `round_type`, `rank_start`, `rank_end`, `reward_content`, `reward_description`, `created`, `updated`) VALUES (5, 4, 1, 3, '[{\"award_ids\": [70], \"ranking_end\": 1, \"ranking_start\": 1}, {\"award_ids\": [76], \"ranking_end\": 2, \"ranking_start\": 2}, {\"award_ids\": [63], \"ranking_end\": 3, \"ranking_start\": 3}]', '积分赛事线上每轮前3名奖励', 0, 0);

INSERT INTO `lucky_game`.`tournament_rules` (`id`, `template_id`, `rule_type`, `rule_content`, `created`, `updated`) VALUES (1, 1, 1, '{\"range_time\": \"10:00-23:00\", \"unit_point\": 50, \"cycle_month\": 2, \"ticket_price\": 1, \"competition_id\": 2}', 0, 0);

INSERT INTO `lucky_game`.`tournament_template` (`id`, `template_name`, `template_type`, `cycle_type`, `rounds_per_cycle`, `online_rounds`, `final_round_offline`, `qualifier_count`, `status`, `created`, `updated`) VALUES (1, '月赛', 1, 1, 4, 3, 1, 10, 1, 0, 0);

-- 游戏配置
INSERT INTO `lucky_game`.`conf_competition` (`id`, `created`, `name`, `cs_type`, `competition_type`, `rule_detail`, `max_player`, `price`, `price_type`, `status`, `start_time`, `end_time`, `total_round`, `play_type`, `max_match_player`, `daily_start_time`, `daily_end_time`, `total_match_round`, `cycle_id`) VALUES (1, 0, '麻将积分比赛', 27, 1, '{\"bao_ji\": 1, \"ben_ji\": 1, \"yin_ji\": 0, \"zhan_ji\": 0, \"bao_gang\": 1, \"bao_ting\": 0, \"shang_ga\": 0, \"wu_gu_ji\": 1, \"yuan_bao\": 1, \"shu_zi_ji\": 0, \"yi_wan_ji\": 0, \"ze_ren_ji\": 0, \"di_long_qi\": 1, \"fan_ji_pai\": 1, \"limit_lose\": 0, \"lian_zhuang\": 0, \"man_tang_ji\": 1, \"decision_sec\": 1, \"gu_mai_score\": 0, \"left_3_bi_hu\": 0, \"shang_xia_ji\": 1, \"suo_de_jia_1\": 1, \"xi_pai_score\": 0, \"chong_feng_ji\": 0, \"hu_pai_ti_shi\": 1, \"jian_gang_san\": 1, \"liang_men_pai\": 0, \"zi_mo_jia_bei\": 0, \"bi_men_yi_shou\": 0, \"exchange_first\": 0, \"exchange_three\": 0, \"wu_gu_ji_score\": 0, \"bao_ting_bi_men\": 0, \"xiao_pai_bi_men\": 0, \"tui_zhang_can_hu\": 0, \"four_card_no_near\": 0, \"four_card_tian_hu\": 0, \"eight_card_tian_hu\": 0, \"four_card_bao_ting\": 0, \"exchange_cards_type\": 0, \"qing_yi_se_extra_add\": 0, \"after_peng_can_bao_ting\": 0, \"huang_zhuang_bu_huang_ji\": 0}', 4, 1, 3, 1, 1768406400, 1769011199, 4, 3, 8, '08:00:00', '23:00:00', 4, 7);
INSERT INTO `lucky_game`.`conf_competition` (`id`, `created`, `name`, `cs_type`, `competition_type`, `rule_detail`, `max_player`, `price`, `price_type`, `status`, `start_time`, `end_time`, `total_round`, `play_type`, `max_match_player`, `daily_start_time`, `daily_end_time`, `total_match_round`, `cycle_id`) VALUES (2, 0, '麻将积分比赛', 28, 1, '{\"bao_ji\": 1, \"ben_ji\": 0, \"yin_ji\": 0, \"zhan_ji\": 1, \"bao_gang\": 1, \"bao_ting\": 1, \"shang_ga\": 0, \"wu_gu_ji\": 0, \"yuan_bao\": 0, \"shu_zi_ji\": 0, \"yi_wan_ji\": 0, \"ze_ren_ji\": 1, \"di_long_qi\": 1, \"fan_ji_pai\": 1, \"limit_lose\": 0, \"lian_zhuang\": 0, \"man_tang_ji\": 0, \"decision_sec\": 1, \"gu_mai_score\": 3, \"left_3_bi_hu\": 1, \"shang_xia_ji\": 0, \"suo_de_jia_1\": 1, \"xi_pai_score\": 0, \"chong_feng_ji\": 1, \"hu_pai_ti_shi\": 1, \"jian_gang_san\": 1, \"liang_men_pai\": 1, \"zi_mo_jia_bei\": 1, \"bi_men_yi_shou\": 1, \"exchange_first\": 0, \"exchange_three\": 1, \"wu_gu_ji_score\": 0, \"bao_ting_bi_men\": 1, \"xiao_pai_bi_men\": 1, \"tui_zhang_can_hu\": 1, \"four_card_no_near\": 0, \"four_card_tian_hu\": 1, \"eight_card_tian_hu\": 8, \"four_card_bao_ting\": 4, \"exchange_cards_type\": 0, \"qing_yi_se_extra_add\": 0, \"after_peng_can_bao_ting\": 0, \"huang_zhuang_bu_huang_ji\": 0}', 3, 1, 3, 1, 1769702400, 1769875199, 4, 2, 12, '08:00:00', '23:00:00', 4, 6);
