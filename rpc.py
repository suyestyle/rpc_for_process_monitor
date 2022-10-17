#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author      : moshan
# Mail        : mo_shan@yeah.net
# Version     : 1.0
# Created Time: 2021-02-21 10:40:02
# Function    : 主程序
#########################################################################
import sys, time, threading, json, random
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.client import ServerProxy
from optparse import OptionParser

from lib.Config import *
from lib.ConnectMySQL import *
from lib.Public import *
from lib.globalVar import gloVar

# 调用函数
def f_init_client(DB):

    remove_members = []

    sql = "select rshost,istate from " + t_host_config + " where istate in (0,1)"

    status, data, DB = f_query_mysql(DB, "select", {"sql" : sql})

    update_sql = {}

    if data is None or len(data) == 0:

        pass

    else :

        for node in data :

            remove_members.append(node)

            update_sql[node[0]] = "update " + t_host_config + " set istate = (if(istate = 1, 2 , if(istate = 2, 2 , -1))) where rshost = '" + node[0] + "'"

        if len(update_sql) > 0 :

            status, data, DB = f_query_mysql(DB, "insert", update_sql)

            if (status != 0) :

                f_write_log(log_opt = "ERROR", log = "[ 节点状态更新失败 ] [ " + "\n".join(update_sql.values()) + " ] ", log_file = log_file)

    mark, res = f_manager_state_for_node(remove_members, script_dir, log_file, options.server_host, options.rpc_port)

    if mark != 0 :

        f_send_alert_to_bot("进程监控, 节点管理异常 : " + ",".join(res.keys()))

    #检查监控状态, 如果有超过两分钟没有上报状态的节点就告警
    sql = """select rshost from """ + t_host_config + """ where istate = 2 and rshost not in (select rshost from """ + t_host_info + """
        where a_time > date_add(now(), INTERVAL - 2 MINUTE) group by rshost)
        and rshost not in (select rshost from """ + t_alert_info + """ where istate = 1 and a_time > date_add(now(), INTERVAL - 5 MINUTE));"""

    status, data, DB = f_query_mysql(DB, "select", {"sql" : sql})

    error_members = []

    replace_sql = {}

    if data is None or len(data) == 0:

        pass

    else :

        for node in data :

            replace_sql[node[0]] = "replace into " + t_alert_info + "(rshost,istate,a_time,remarks) select '" + node[0] + "', 1,now(),'超过2min未上报';"

            error_members.append(node[0])

        status, data, DB = f_query_mysql(DB, "insert", replace_sql)

        if (status != 0) :

            f_write_log(log_opt = "ERROR", log = "[ 告警状态更新失败 ] [ " + "\n".join(replace_sql.values()) + " ] ", log_file = log_file)

        f_write_log(log_opt = "ERROR", log = "[ 超过2min未上报的节点有 : " + ",".join(error_members) + " ]", log_file = log_file)

        f_send_alert_to_bot("进程监控, 超过2min未上报的节点有 : " + ",".join(error_members))

    #检查监控数据, 保留retention_day天数
    delete_sql = {}

    for t in monitor_table_list :

        delete_sql[t] = "delete from " + t + " where a_time < date_add(now(), INTERVAL - " + d_retention + " DAY);"

    status, data, DB = f_query_mysql(DB, "insert", delete_sql)

    if (status != 0) :

        f_write_log(log_opt = "ERROR", log = "[ 历史监控数据清理失败 ] [ " + "\n".join(delete_sql.values()) + " ] ", log_file = log_file)

    return DB

def f_manager_client():

    DB = f_connect_mysql()

    sql = "select version from " + t_version_info + " order by id desc limit 1;"

    status, data, DB = f_query_mysql(DB, "select", {"sql" : sql}) #如果表里存储的版本号跟配置文件的不一样就会更新client代码

    update_mark = ""

    if data is None or len(data) == 0:

        update_mark = "true"

    else :

        for v in data :

            if v[0] != version : update_mark = "true"

    if update_mark == "true" : #如果需要升级就将所有监控client状态改为1, 且记录最新的版本号

        f_write_log(log_opt = "INFO", log = "[ 即将进行版本升级 ]", log_file = log_file)

        sql = {}

        sql["update"] = "update " + t_host_config + " set istate = 1 where istate = 2;"

        sql["insert"] = "insert into " + t_version_info + " (version,a_time) select '" + version + "', now();"

        status, data, DB = f_query_mysql(DB, "insert", sql)

        if (status != 0) : f_write_log(log_opt = "ERROR", log = "[ 版本号更新失败 ] [ " + "\n".join(sql.values()) + " ] ", log_file = log_file)

    while True :

        try :

            DB = f_init_client(DB)

            f_write_log(log_opt = "INFO", log = "[ client节点状态巡检完成 ]", log_file = log_file)

        except  Exception as e :

            f_write_log(log_opt = "ERROR", log = "[ client节点状态巡检遇到错误 ] [ " + str(e) + " ] ", log_file = log_file)

        time.sleep(30)

def f_rpc_func(data):

    """
    监控数据处理逻辑
    """
    global DB

    status = 0

    insert_sql = {}

    io_time = ""

    if "HOST" in data.keys():

        cpu_json = json.dumps(data["cpu"])

        mem_json = json.dumps(data["mem"])

        disk_json = json.dumps(data["disk"])

        io_time = data["io"]["time"]

        data["io"].pop("time")

        io_json = json.dumps(data["io"])

        net_time = data["net"]["time"]

        data["net"].pop("time")

        net_json = json.dumps(data["net"])

        insert_sql["host"] = """insert into """ + t_host_info + """(id,rshost,cpu_info,mem_info,io_info,net,a_time)
            value(0,'""" + data["HOST"] + """','""" + cpu_json + """','""" + mem_json + """','""" + io_json + """',
            '""" + net_json + """','""" + net_time + """');"""

        for tmp in data["disk"].keys():

            disk_json = json.dumps(data["disk"][tmp])

            insert_sql[tmp] = """insert into """ + t_disk_info + """(id,rshost,part,disk_info,a_time)
                value(0,'""" + data["HOST"] + """','""" + tmp + """','""" + disk_json + """','""" + net_time + """');"""

    if "util_qu" not in data.keys():

        data["util_qu"] = {}

    for qu_info in data["util_qu"].keys():
        insert_sql["util_qu" + data["HOST"] + qu_info] = """insert into """ + t_util_qu_info + """(id,rshost,dev,avgqu,util,a_time)
            value(0,'""" + data["HOST"] + """','""" + qu_info + """','""" + data["util_qu"][qu_info]["avgqu-sz"] + """',
            '""" + data["util_qu"][qu_info]["util"] + """','""" + net_time + """');"""

    for iftop in data["iftop"].keys():

        if iftop == "time" : continue

        for remote_info in data["iftop"][iftop] :

            remote = remote_info["remote"]

            in_info = remote_info["in"]

            out_info = remote_info["out"]

            remote_info.pop("remote")

            info_json = json.dumps(remote_info)

            in_info = f_return_value(in_info)

            out_info = f_return_value(out_info)

            if in_info < r_net and out_info < r_net : #只记录大于10MB的流量

                continue

            insert_sql[iftop+remote] = """insert into """ + t_port_net_info + """(id, rsinfo,remote, in_info, out_info, a_time)
                value(0,'""" + iftop + """','""" + remote + """','""" + str(in_info) + """','""" + str(out_info) + """','""" + data["iftop"]["time"] + """');"""

    tmp_index = 0

    for port_info in data["port"].keys():

        remarks = data["port"][port_info]["remarks"].strip()

        cpu_info = data["port"][port_info]["cpu"]

        mem_info = data["port"][port_info]["mem"]

        io_r = data["port"][port_info]["io_r"]

        io_w = data["port"][port_info]["io_w"]

        io_r = f_return_value(io_r)

        io_w = f_return_value(io_w)


        mem_info = mem_info.split("GB")[0]

        cpu_info = cpu_info.split("%")[0]

        if (io_r < r_io and io_w < r_io) and float(mem_info) < r_mem and float(cpu_info) < r_cpu : #只记录大于10MB的, 或者内存大于10GB, CPU大于200%
            continue

        data["port"][port_info].pop("remarks")

        io_json = json.dumps(data["port"][port_info])

        insert_sql[port_info] = """insert into """ + t_process_io_info + """(id,rshost,rsport,cpu,mem,io_r,io_w,a_time,md5_str,remarks)
            value(0,'""" + data["HOST"] + """','""" + port_info + """','""" + cpu_info + """','""" + mem_info + """'
                ,'""" + str(io_r) + """','""" + str(io_w) + """','""" + io_time + """',MD5('""" + remarks + """'),'');"""
        insert_sql[tmp_index] = """replace into """ + t_process_info + """(id,md5_str,remarks)
            value(0,MD5('""" + remarks + """'),'""" + remarks + """');"""

        tmp_index += 1

    data_json = json.dumps(data, indent=4,ensure_ascii=False, sort_keys=False,separators=(',', ':'))
    #print(data_json)

    status, _, DB = f_query_mysql(DB, "insert", insert_sql)

    if (status != 0) :

        f_write_log(log_opt = "ERROR", log = "[ 监控数据写入失败 ] [ " + data["HOST"] + " ] [ " + "\n".join(insert_sql.values()) + " ] ", log_file = log_file)

    else :

        f_write_log(log_opt = "INFO", log = "[ 监控数据上报成功 ] [ " + data["HOST"] + " ] ", log_file = log_file)

    data_json = json.dumps(insert_sql, indent=4,ensure_ascii=False, sort_keys=False,separators=(',', ':'))

    #print(data_json)

    insert_sql = {}

    return status, version

def f_rpc_server(port) :

    server = SimpleXMLRPCServer(('0.0.0.0', int(port)))      # 初始化

    server.register_function(f_rpc_func, "f_rpc_func")       # 注册get_string函数

    f_write_log(log_opt = "INFO", log = "[ V" + version + " Listening for '0.0.0.0:" + str(port) + "' ]", log_file = log_file)

    server.serve_forever() # 保持等待调用状态

def f_rpc_client(server_list, client, port) :

    if not os.path.exists(script_dir + "/state/state.log"):

        os.system(r"touch {}".format(script_dir + "/state/state.log"))

    server_mark = 0 #server状态标志, 如果连续三次异常就退出程序

    while True :

        start_time = int(str(time.time()).split(".")[0]) #记录开始时间

        gloVar.res_disk  = {} #避免历史数据干扰, 每次清空
        gloVar.res_mem   = {}
        gloVar.res_cpu   = {}
        gloVar.res_net   = {}
        gloVar.res_iftop = {}
        gloVar.res_iotop = {}
        gloVar.res_util_qu  = {} #避免历史数据干扰, 每次清空

        with open(script_dir + "/state/state.log", 'r') as f :

            mark = f.readline()

            if "stop" in mark :

                sys.exit()

        res = {}

        # 并发采集数据
        thread_list = []

        t1= threading.Thread(target=f_monitor_for_disk)
        thread_list.append(t1)

        t2= threading.Thread(target=f_monitor_for_mem)
        thread_list.append(t2)

        t3= threading.Thread(target=f_monitor_for_cpu)
        thread_list.append(t3)

        t4= threading.Thread(target=f_monitor_for_net, args=(client,))
        thread_list.append(t4)

        t5= threading.Thread(target=f_monitor_for_iftop)
        thread_list.append(t5)

        t6= threading.Thread(target=f_monitor_for_iotop)
        thread_list.append(t6)

        t7= threading.Thread(target=f_monitor_for_util_qu)
        thread_list.append(t7)

        for t in thread_list:

            t.setDaemon(True)  # 设置为守护线程，主线程结束一并回收

            t.start()

        for t in thread_list:

            t.join() # 子线程全部加入，主线程等所有子线程运行完毕

        res = {
            "HOST"     : client,
            "disk"     : gloVar.res_disk,
            "util_qu"  : gloVar.res_util_qu,
            "mem"      : gloVar.res_mem,
            "cpu"      : gloVar.res_cpu,
            "net"      : gloVar.res_net,
            "iftop"    : {},
            "io"       : {},
            "port"     : gloVar.res_iotop
        }

        iftop = gloVar.res_iftop
        res["iftop"]["time"] = iftop["time"]

        for tmp in iftop["iftop"].split("\n") : #处理iftop结果

            r = []

            for i in tmp.split(" "):

                if len(i) > 0 : r.append(i)

            if len(r) == 0 : continue

            if r[0] not in res["iftop"].keys(): res["iftop"][r[0]] = []

            res["iftop"][r[0]].append({"remote":r[2],"out":r[1],"in":r[3]})

        #d = json.dumps(res["iftop"], indent=4,ensure_ascii=False, sort_keys=False,separators=(',', ':'))

        res["io"] = {
            "Total"  : res["port"]["Total"],
            "Actual" : res["port"]["Actual"],
            "time"   : res["port"]["time"]
        }

        res["port"].pop("Total")
        res["port"].pop("Actual")
        res["port"].pop("time")

        #data = json.dumps(res, indent=4,ensure_ascii=False, sort_keys=False,separators=(',', ':'))
        #print(data)

        mark = 1

        for ser in server_list.split(",") : #多个sesrver的话会选择一个正常的进行上报

            try :
                server = ServerProxy("http://" + ser + ":" + str(port)) # 初始化服务器

                status, ver = server.f_rpc_func(res) #返回一个状态码, 版本号, 版本号是用来判断server端的版本跟当前版本是否一致, 不一致就自动升级

                if (ver != version and status == 0) :

                    f_write_log(log_opt = "INFO", log = "[ 需要升级 : " + version + " -> " + ver + " ]", log_file = log_file)

                    sys.exit(-1)

                if (status != 0) :

                    f_write_log(log_opt = "ERROR", log = "[ 监控入库失败 ]", log_file = log_file)

                mark = 0

            except Exception as e: #server都异常就报警, 并记录一下避免所有的client都同时告警

                if server_mark < 3 : continue #server连续三次都异常就退出程序

                sql = "select rshost from " + t_alert_info + " where istate = 1 and a_time > date_add(now(), INTERVAL - 5 MINUTE) and rshost  = '" + ser + "'"

                DB = f_connect_mysql()

                status, data, DB = f_query_mysql(DB, "select", {"sql" : sql})

                if data is None or len(data) == 0:

                    f_send_alert_to_bot(client + " 报告, 进程监控, server 端连接异常 : " + ser + ":" + str(port))

                    replace_sql = "replace into " + t_alert_info + "(rshost,istate,a_time,remarks) select '" + ser + "', 1,now(),'" + client + "报告, server 端连接异常';"

                    status, data, DB = f_query_mysql(DB, "insert", {"sql" : replace_sql})

                    if (status != 0) :

                        f_write_log(log_opt = "ERROR", log = "[ 告警状态更新失败 ] [ " + "\n".join(replace_sql.values()) + " ] ", log_file = log_file)

                f_close_connection(DB)

        if mark == 0 :

            server_mark = 0

        else :

            server_mark += 1

        if server_mark > 3 : #server连续三次都异常就退出程序

            sys.exit(-1)

        end_time = int(str(time.time()).split(".")[0]) #记录结束时间

        time.sleep(int(t_interval) - 5 + random.randint(1,5) - (end_time - start_time))  #根据采集周期进行sleep, 这里用了一个随机数是避免所有client同时上报

def _args_parse():

    opt = OptionParser(usage = "it's usage tip.", version = "%prog " + version, description = "")

    opt.add_option('-C', '--client', dest="client_host", type="string", help = u'rpc client的地址(本机地址)')

    opt.add_option('-S', '--server', dest="server_host", type="string", help = u'rpc server的地址,多个server逗号隔开')

    opt.add_option('-R', '--role',   dest="rpc_role",    type="string", help = u'rpc 角色(client|server)')

    opt.add_option('-P', '--port',   dest="rpc_port",    type="int",    help = u'rpc监听端口')

    options,args = opt.parse_args()

    mark = 0

    if options.rpc_role is None :

        mark = 1

    elif options.rpc_port is None :

        mark = 1

    elif options.rpc_role == "client" and (options.client_host is None or options.server_host is None):

        mark = 1

    if (mark == 1) :

        print (opt.print_help())

        sys.exit(-1)

    return options,args

if __name__ == '__main__':

    options,args = _args_parse()

    if options.rpc_role == "server" : #每次启动都会判断是否更新client的代码

        DB = f_connect_mysql()

        t_init = threading.Thread(target = f_manager_client)
        t_init.setDaemon(True)     # 设置为守护线程，主线程结束一并回收
        t_init.start()

        f_rpc_server(options.rpc_port)

    elif options.rpc_role == "client" :

        f_rpc_client(options.server_host, options.client_host, options.rpc_port)

    else:

        opt = OptionParser(usage = "it's usage tip.", version = "%prog " + version, description = "")

        print (opt.print_help())

        sys.exit(-1)
