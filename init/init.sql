create database dbzz_monitor;

use dbzz_monitor;

CREATE TABLE `tb_monitor_alert_info` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT COMMENT '主键',
  `rshost` varchar(30) DEFAULT '' COMMENT '告警机器',
  `istate` tinyint(4) NOT NULL DEFAULT '0' COMMENT '告警状态, 0表示已经恢复, 1表示正在告警',
  `a_time` datetime NOT NULL DEFAULT '2021-12-08 00:00:00' COMMENT '发送告警的时间',
  `remarks` varchar(50) NOT NULL DEFAULT '' COMMENT '告警内容',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_alert_task` (`rshost`),
  KEY `idx_a_time` (`a_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `tb_monitor_disk_info` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `rshost` varchar(20) NOT NULL DEFAULT '' COMMENT '主机地址',
  `part` varchar(50) NOT NULL DEFAULT '' COMMENT '分区信息',
  `disk_info` json DEFAULT NULL COMMENT 'disk信息 json串, 单位是GB',
  `a_time` datetime NOT NULL DEFAULT '2022-01-01 00:00:00',
  PRIMARY KEY (`id`),
  KEY `idx_rshost` (`rshost`),
  KEY `idx_a_time` (`a_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `tb_monitor_host_config` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `rshost` varchar(20) NOT NULL DEFAULT '' COMMENT '主机地址',
  `istate` tinyint(4) NOT NULL DEFAULT '0' COMMENT '状态, 0表示删除监控, 1表示正在监控, 2表示暂停监控',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_rshost` (`rshost`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `tb_monitor_host_info` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `rshost` varchar(20) NOT NULL DEFAULT '' COMMENT '主机地址',
  `cpu_info` json DEFAULT NULL COMMENT 'cpu信息 json串',
  `mem_info` json DEFAULT NULL COMMENT 'mem信息 json串, 单位是GB',
  `io_info` json DEFAULT NULL COMMENT '磁盘io使用情况, 单位是KB',
  `net` json DEFAULT NULL COMMENT '网络使用情况, 单位是KB(speed单位是MB/S)',
  `a_time` datetime NOT NULL DEFAULT '2022-01-01 00:00:00',
  PRIMARY KEY (`id`),
  KEY `idx_a_time` (`a_time`),
  KEY `idx_rshost` (`rshost`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `tb_monitor_port_net_info` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `rsinfo` varchar(50) NOT NULL DEFAULT '' COMMENT '主机地址',
  `remote` varchar(50) NOT NULL DEFAULT '' COMMENT '传输到的目标端',
  `in_info` bigint(20) NOT NULL DEFAULT '0' COMMENT '入口流量, 单位是KB',
  `out_info` bigint(20) NOT NULL DEFAULT '0' COMMENT '出口流量, 单位是KB',
  `a_time` datetime NOT NULL DEFAULT '2022-01-01 00:00:00',
  PRIMARY KEY (`id`),
  KEY `idx_rsinfo_port` (`rsinfo`),
  KEY `idx_remote_port` (`remote`),
  KEY `idx_a_time` (`a_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `tb_monitor_process_info` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `md5_str` char(32) NOT NULL DEFAULT '' COMMENT '进程信息的md5值, 方便建立索引',
  `remarks` text COMMENT '进程详细信息',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_md5` (`md5_str`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `tb_monitor_process_io_info` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `rshost` varchar(20) NOT NULL DEFAULT '' COMMENT '主机地址',
  `rsport` int(11) NOT NULL DEFAULT '0' COMMENT '端口号',
  `cpu` float NOT NULL DEFAULT '0' COMMENT 'cpu使用率',
  `mem` float NOT NULL DEFAULT '0' COMMENT '内存使用情况单位是GB',
  `io_r` float NOT NULL DEFAULT '0' COMMENT '读io, 单位是KB',
  `io_w` float NOT NULL DEFAULT '0' COMMENT '读io, 单位是KB',
  `a_time` datetime NOT NULL DEFAULT '2022-01-01 00:00:00' COMMENT '采集时间',
  `md5_str` char(32) NOT NULL DEFAULT '' COMMENT '进程信息的md5值, 对应t_monitor_process_info表的md5_str字段',
  `remarks` text COMMENT '备注信息',
  PRIMARY KEY (`id`),
  KEY `idx_host_port` (`rshost`,`rsport`),
  KEY `idx_port` (`rsport`),
  KEY `idx_a_time` (`a_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `tb_monitor_version` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `version` varchar(5) DEFAULT '' COMMENT '版本号',
  `a_time` datetime NOT NULL DEFAULT '2022-01-01 00:00:00',
  PRIMARY KEY (`id`),
  KEY `idx_a_time` (`a_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `tb_monitor_disk_util_qu_info` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `rshost` varchar(20) NOT NULL DEFAULT '' COMMENT '主机地址',
  `dev` varchar(50) NOT NULL DEFAULT '' COMMENT '硬盘信息',
  `avgqu` int(11) NOT NULL DEFAULT '0' COMMENT '队列信息, 没有单位',
  `util` int(11) NOT NULL DEFAULT '0' COMMENT '磁盘压力, 单位%',
  `a_time` datetime NOT NULL DEFAULT '2022-01-01 00:00:00',
  PRIMARY KEY (`id`),
  KEY `idx_rshost` (`rshost`),
  KEY `idx_a_time` (`a_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
