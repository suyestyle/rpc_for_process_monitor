#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author      : moshan
# Mail        : mo_shan@yeah.net
# Version     : 1.0
# Created Time: 2021-08-12 09:40:43
# Function    : 读取配置文件的配置
#########################################################################
import configparser

config_file = "/opt/soft/rpc_for_monitor/conf/config.ini"
cf = configparser.ConfigParser() #读取配置文件的mongodb部分的配置
cf.read(config_file, encoding="utf-8")

#global相关
version            = cf.get("global", "version").strip('"').strip("'") #去掉单引号跟双引号
log_file           = cf.get("global", "log_file").strip('"').strip("'") #去掉单引号跟双引号
script_dir         = cf.get("global", "script_dir").strip('"').strip("'")
t_interval         = cf.get("global", "interval_time").strip('"').strip("'")
d_retention        = cf.get("global", "retention_day").strip('"').strip("'")
mount_part         = cf.get("global", "mount_part").strip('"').strip("'")
log_size           = int(cf.get("global", "log_size").strip('"').strip("'")) #单位是MB, 日志文件超过这个大小就进行删除历史日志, 即会循环写

#RULE相关, 这部分是定义监控采集的阈值, 及仅采集目标机器占用系统资源超过定义的阈值, 有一个满足即可
r_cpu              = int(cf.get("RULE", "cpu").strip('"').strip("'"))
r_mem              = int(cf.get("RULE", "mem").strip('"').strip("'"))
r_io               = int(cf.get("RULE", "io").strip('"').strip("'"))
r_net              = int(cf.get("RULE", "net").strip('"').strip("'"))
r_avgqu            = int(cf.get("RULE", "avgqu").strip('"').strip("'"))
r_util             = int(cf.get("RULE", "util").strip('"').strip("'"))

#client相关
os_path            = cf.get("CLIENT", "path").strip('"').strip("'")
python3            = cf.get("CLIENT", "python3").strip('"').strip("'")
py3env             = cf.get("CLIENT", "py3env").strip('"').strip("'")

#发送告警相关
wx_url = cf.get("MSM", "wx_url").strip('"').strip("'")

#监控相关的
monitor_host       = cf.get("Monitor", "mysql_host").strip('"').strip("'")
monitor_user       = cf.get("Monitor", "mysql_user").strip('"').strip("'")
monitor_pass       = cf.get("Monitor", "mysql_pass").strip('"').strip("'")
monitor_port       = int(cf.get("Monitor", "mysql_port").strip('"').strip("'"))
monitor_db         = cf.get("Monitor", "mysql_db").strip('"').strip("'")

t_host_info        = cf.get("Monitor", "host_info").strip('"').strip("'")
t_disk_info        = cf.get("Monitor", "disk_info").strip('"').strip("'")
t_port_net_info    = cf.get("Monitor", "port_net_info").strip('"').strip("'")
t_process_info     = cf.get("Monitor", "process_info").strip('"').strip("'")
t_process_io_info  = cf.get("Monitor", "process_io_info").strip('"').strip("'")
t_host_config      = cf.get("Monitor", "host_config").strip('"').strip("'")
t_alert_info       = cf.get("Monitor", "alert_info").strip('"').strip("'")
t_version_info     = cf.get("Monitor", "version_info").strip('"').strip("'")
t_util_qu_info     = cf.get("Monitor", "util_qu_info").strip('"').strip("'")

monitor_table_list = [t_host_info,t_disk_info,t_port_net_info,t_process_io_info,t_alert_info] #这几个表的诗句会进行删除, 根据用户定义的保存周期
