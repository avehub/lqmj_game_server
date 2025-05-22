CREATE TABLE `users` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `uid` int NOT NULL AUTO_INCREMENT COMMENT '玩家ID',
  `gold` decimal(65,2) NOT NULL DEFAULT '0' COMMENT '金币',
  `diamond` int NOT NULL DEFAULT '0' COMMENT '钻石',
  `room_card` int NOT NULL DEFAULT '0' COMMENT '房卡',
  `yellow_diamond` int NOT NULL DEFAULT '0' COMMENT '黄钻',
  `vip` int NOT NULL DEFAULT '0' COMMENT 'VIP等级',
  `guild_id` int NOT NULL DEFAULT '0' COMMENT '牌友会ID',
  `game_num` int NOT NULL DEFAULT '0' COMMENT '游戏对局数',
  `game_percentage` int NOT NULL DEFAULT '0' COMMENT '游戏胜率',
  `platform` smallint NOT NULL DEFAULT '0' COMMENT '登录平台: 1微信小游戏 2APP 3H5',
  `dev_ident` varchar(18) DEFAULT NULL COMMENT '登录设备标识',
  `ip` varchar(128) DEFAULT '' COMMENT '登陆IP',
  `region` varchar(20) DEFAULT '' COMMENT '登录地区/行政区域',
  `updated` bigint DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`uid`),
  KEY `idx_guild_id` (`guild_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户信息表（热）';

CREATE TABLE `users_info` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `uid` int NOT NULL AUTO_INCREMENT COMMENT '玩家ID',
  `name` varchar(20) DEFAULT '' COMMENT '玩家昵称',
  `sex` smallint NOT NULL DEFAULT '0' COMMENT '性别',
  `phone` varchar(18) DEFAULT NULL COMMENT '手机号码',
  `email` varchar(256) DEFAULT NULL COMMENT '邮箱',
  `address` varchar(256) DEFAULT '' COMMENT '所在地址',
  `id_card` varchar(20) DEFAULT '' COMMENT '身份证',
  `real_name` varchar(32) DEFAULT '' COMMENT '玩家真实姓名',
  `pi` varchar(64) DEFAULT '' COMMENT '已通过实名认证用户的唯一标识',
  `avatar` varchar(256) DEFAULT '' COMMENT '头像地址',
  `album` varchar(255) DEFAULT '' COMMENT '相册',
  `platform` smallint NOT NULL DEFAULT '0' COMMENT '注册平台: 1微信小游戏 2APP 3H5',
  `apple_id` smallint NOT NULL DEFAULT '0' COMMENT 'Apple User ID',
  `dev_ident` varchar(18) DEFAULT NULL COMMENT '设备标识',
  `safe_key` varchar(18) DEFAULT '' COMMENT '安全密钥',
  `valid_key` varchar(16) DEFAULT '' COMMENT '验证密钥',
  `tst_mark` tinyint(1) DEFAULT '0' COMMENT '测试号标记',
  `ip` varchar(128) DEFAULT '' COMMENT '注册IP',
  `region` varchar(20) DEFAULT '' COMMENT '注册地区/行政区域',
  `country` varchar(16) DEFAULT 'CN' COMMENT '国家域名',
  `openid` varchar(128) DEFAULT NULL COMMENT '授权用户唯一标识',
  `unionid` varchar(128) DEFAULT NULL COMMENT 'unionid',
  `ban_time` bigint DEFAULT '0' COMMENT '封禁时间：0未封禁 -1永久封禁 大于0为封禁时间',
  `updated` bigint DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`uid`),
  UNIQUE KEY `uid_user_platfor_b2b99c` (`platform`,`openid`),
  UNIQUE KEY `uid_user_platfor_919560` (`platform`,`unionid`),
  KEY `idx_user_created` (`created`),
  KEY `idx_user_phone` (`phone`),
  KEY `idx_user_email` (`email`),
  KEY `idx_user_pi (`pi`),
  KEY `idx_user_platfo` (`platform`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户信息表（冷）';


CREATE TABLE `log_user_behavior` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `uid` int NOT NULL COMMENT '馆主ID(玩家ID)',
  `behavior_type` varchar(128) NOT NULL COMMENT '行为类型（接口方法）',
  `behavior_info` varchar(128) NOT NULL COMMENT '行为内容（接口参数）',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='用户行为日志表';  


CREATE TABLE `teahouses` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `tid` int(6) UNSIGNED ZEROFILL NOT NULL AUTO_INCREMENT COMMENT '茶馆ID',
  `uid` int NOT NULL COMMENT '馆主ID(玩家ID)',
  `num` int NOT NULL DEFAULT '0' COMMENT '茶馆人数',
  `name` varchar(20) NOT NULL DEFAULT '' COMMENT '茶馆名称',
  `template_id` int NOT NULL DEFAULT '1' COMMENT '常玩玩法ID（玩法模板ID）',
  `room_card` int NOT NULL DEFAULT '0' COMMENT '茶馆基金（房卡）',
  `other` json DEFAULT NULL COMMENT '其他设置：JSON存储',
  `status` tinyint(2) UNSIGNED NOT NULL DEFAULT '0' COMMENT '状态：0正常',
  `updated` bigint DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`tid`),
  KEY `idx_user_id` (`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='茶馆信息表';  

CREATE TABLE `teahouse_users` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `tid` int(6) UNSIGNED ZEROFILL NOT NULL AUTO_INCREMENT COMMENT '茶馆ID',
  `uid` int NOT NULL COMMENT '馆主ID(玩家ID)',
  `role` tinyint(2) UNSIGNED NOT NULL COMMENT '角色:0普通成员 1管理员 9馆主',
  `status` tinyint(2) UNSIGNED NOT NULL DEFAULT '0' COMMENT '成员状态：0正常 1小黑屋',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_teahouse_user` (`tid`,`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='茶馆和用户关系表';  

CREATE TABLE `game_rooms` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '房间ID',
  `tid` int(6) UNSIGNED ZEROFILL NOT NULL AUTO_INCREMENT COMMENT '茶馆ID,无茶馆为0',
  `uid` int NOT NULL COMMENT '房主ID(玩家ID)',
  `template_id` int NOT NULL COMMENT '玩法模板ID',
  `room_rule_id` int NOT NULL COMMENT '房间玩法规则ID',
  `max_players` tinyint(2) UNSIGNED NOT NULL DEFAULT '0' COMMENT '最大人数',
  `current_players` tinyint(2) UNSIGNED NOT NULL DEFAULT '0' COMMENT '当前人数',
  `other` json DEFAULT NULL COMMENT '其他配置：JSON存储',
  `status` tinyint(1) UNSIGNED NOT NULL DEFAULT '0' COMMENT '房间状态：0有空 1已满',
  PRIMARY KEY (`id`),
  KEY `idx_teahouse_room_status` (`status`),
  KEY `idx_teahouse_id` (`tid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='游戏房间关系表';  

CREATE TABLE `teahouse_groups` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '分组ID',
  `tid` int(6) UNSIGNED ZEROFILL NOT NULL AUTO_INCREMENT COMMENT '茶馆ID',
  `uid` int NOT NULL COMMENT '玩家ID',
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_teahouse_user` (`tid`,`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='茶馆隔离组表';  

CREATE TABLE `extra_teahouse_behavior` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '行为ID',
  `tid` int(6) UNSIGNED ZEROFILL NOT NULL AUTO_INCREMENT COMMENT '茶馆ID',
  `type` tinyint(2) UNSIGNED NOT NULL COMMENT '类型：1加入茶馆申请 2小黑屋 3隔离',
  `uid` int NOT NULL COMMENT '类型==1：申请玩家ID 类型==2：被拉入黑名单玩家ID',
  `status` tinyint(2) UNSIGNED NOT NULL COMMENT '状态，类型==1：0未审批 1拒绝 99通过，类型==2、3:99成功',
  `check_uid` int NOT NULL COMMENT '审批/操作玩家ID',
  `updated` bigint DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='茶馆操作行为记录表';  

CREATE TABLE `extra_teahouse_event` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '事件ID',
  `tid` int(6) UNSIGNED ZEROFILL NOT NULL AUTO_INCREMENT COMMENT '茶馆ID',
  `type` tinyint(2) UNSIGNED NOT NULL COMMENT '类型：1基金充值 2基金消耗 3入馆审批记录',
  `uid` int NOT NULL COMMENT '玩家ID（发起方）',
  `explain` varchar(255) DEFAULT '' COMMENT '说明:记录XX管理员（ID：xx）通过XX玩家（ID：xx）加入茶馆; XX玩家（ID：xx）消耗XX基金创建了xx玩法（房间号：xx）; XX玩家（ID：xx）为茶馆充值基金xx',
  PRIMARY KEY (`id`),
  KEY `idx_teahouse_event_type` (`type`),
  KEY `idx_teahouse_id` (`tid`),
  KEY `idx_user_id` (`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='茶馆日常事件相关记录表';  

CREATE TABLE `records_games` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '战绩ID',
  `tid` int(6) UNSIGNED ZEROFILL NOT NULL DEFAULT '0' AUTO_INCREMENT COMMENT '茶馆ID，玩家无茶馆值为0',
  `room_id` int NOT NULL COMMENT '房间ID',
  `uid` int NOT NULL COMMENT '玩家ID',
  `template_id` int NOT NULL DEFAULT '0' COMMENT '玩法模板ID',
  `round_total` int NOT NULL COMMENT '总局数',
  `round_num` int NOT NULL COMMENT '当前局数',
  `result` json DEFAULT NULL COMMENT '游戏结果：JSON存储',
  PRIMARY KEY (`id`),
  KEY `idx_teahouse_event_type` (`type`),
  KEY `idx_teahouse_id` (`tid`),
  KEY `idx_user_id` (`uid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='游戏战绩记录表';  

CREATE TABLE `game_types` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '类型ID',
  `name` varchar(20) NOT NULL COMMENT '类型名称',
  `icon` varchar(255) NOT NULL COMMENT '类型图标',
  `updated` bigint DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='游戏类型表';  

CREATE TABLE `gamepaly_templates` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '模板ID',
  `game_type_id` int NOT NULL COMMENT '类型ID',
  `name` varchar(20) DEFAULT '' COMMENT '玩法名称',
  `description` json DEFAULT NULL COMMENT '玩法描述：JSON存储',
  `min_players` tinyint(2) UNSIGNED NOT NULL COMMENT '最少人数',
  `max_players` tinyint(2) UNSIGNED NOT NULL COMMENT '最多人数',
  `updated` bigint DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_game_type_id` (`game_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='游戏玩法模板表';  

CREATE TABLE `gamepaly_rules` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '规则ID',
  `pid` int NOT NULL COMMENT '父级规则ID',
  `template_id` int NOT NULL COMMENT '玩法模板ID',
  `label` varchar(8) NOT NULL COMMENT '规则唯一标识',
  `name` varchar(20) NOT NULL COMMENT '规则名称',
  `option_type` ENUM(bool, enum, multi_enum) NOT NULL COMMENT '选项类型',
  `option_info` json DEFAULT NULL COMMENT '选项内容：JSON存储',
  `updated` bigint DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_gamepaly_template_id` (`template_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='游戏玩法规则表';  


CREATE TABLE `game_room_rules` (
  `created` bigint DEFAULT '0' COMMENT '创建时间',
  `id` int NOT NULL AUTO_INCREMENT COMMENT '规则ID',
  `template_id` int NOT NULL COMMENT '玩法模板ID',
  `paly_rule_id` int NOT NULL  COMMENT '玩法规则ID',
  `option_value` json DEFAULT NULL COMMENT '选项值：JSON存储',
  `name` varchar(20) NOT NULL COMMENT '规则名称',
  `option_type` ENUM(bool, enum, multi_enum) NOT NULL COMMENT '选项类型',
  `option_value` json DEFAULT NULL COMMENT '选项值：JSON存储（用户选择的值，类型与gamepaly_rules表data_type匹配））',
  `updated` bigint DEFAULT '0' COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_gamepaly_template_id` (`template_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='游戏房间玩法规则实例表';  