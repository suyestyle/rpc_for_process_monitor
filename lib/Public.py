#!/usr/bin/env python
# -*- coding: utf-8 -*-
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author      : moshan
# Mail        : mo_shan@yeah.net
# Version     : 1.0
# Created Time: 2021-08-12 09:40:43
# Function    : 公共函数
#########################################################################

import sys, subprocess, os, json, requests
import datetime as dt
from lib.Config import *

from lib.globalVar import gloVar

def f_return_value(in_info):

    """
    单位转换
    """
    if "GB" in in_info :

        in_info = float(in_info.split("GB")[0]) * 1024 * 1024

    elif "G/s" in in_info :

        in_info = float(in_info.split("G/s")[0]) * 1024 * 1024

    elif "MB" in in_info :

        in_info = float(in_info.split("MB")[0]) * 1024

    elif "M/s" in in_info :

        in_info = float(in_info.split("M/s")[0]) * 1024

    elif "KB" in in_info :

        in_info = float(in_info.split("KB")[0])

    elif "K/s" in in_info :

        in_info = float(in_info.split("K/s")[0])

    else :

        in_info = 0

    return in_info

def f_exe_os_comm(comm_str):
    """
    执行系统命令, 返回状态及输出
    """

    if "rsync" in comm_str :

        (status,output) = subprocess.getstatusoutput("set -o pipefail && timeout 600s " + comm_str)

    else :

        (status,output) = subprocess.getstatusoutput("set -o pipefail && timeout 5s " + comm_str)

    return status,output

def f_monitor_for_util_qu():
    """
    磁盘相关的采集
    """

    util_qu = {}

    _, util_qu_tmp = f_exe_os_comm("""iostat -xk 1 2|awk 'NF==14 && $1 != "Device:" {print "/dev/"$1,int($9),int($14)}'|tail -2""")

    for tmp in util_qu_tmp.split("\n") :
        tmp = tmp.split(" ")
        if len(tmp) != 3 : continue

        if int(tmp[1]) < r_avgqu and int(tmp[2]) < r_util : continue

        util_qu[tmp[0]] = {"avgqu-sz": tmp[1], "util" : tmp[2]}

    gloVar.res_util_qu = util_qu

def f_monitor_for_disk():
    """
    磁盘相关的采集
    """

    disk = {}

    part = mount_part

    if len(part) > 0 : #判断是否有挂载点, 如果用户没有配置挂载点就采集所有磁盘(大于50GB的挂载点)

        part = part + "$"

    _, has_disk = f_exe_os_comm("df|grep ' " + part + "'")

    if len(has_disk) == 0 : part = "" #没有这个分区就全分区采集

    _, disk_tmp = f_exe_os_comm("df|grep ' " + part + "'|awk '$2 > 1024 * 1024 * 50 && /^\//{print $1,int($2/1024/1024),int($3/1024/1024),int($4/1024/1024)}'")

    for tmp in disk_tmp.split("\n") :
        tmp = tmp.split(" ")

        if len(tmp) != 4 : continue

        disk[tmp[0]] = {"total" : tmp[1], "used" : tmp[2], "free" : tmp[3]}

    gloVar.res_disk = disk

def f_monitor_for_mem():
    """
    内存相关的采集
    """
    _, mem = f_exe_os_comm("free |grep '^Mem:'|awk '{print int($2/1024/1024),int($3/1024/1024),int(($2-$3)/1024/1024)}'")

    mem = mem.split(" ")

    gloVar.res_mem = {"total" : mem[0], "used" : mem[1], "free" : mem[2]}

def f_monitor_for_cpu():
    """
    CPU相关的采集
    """

    _, gloVar.res_cpu["total"] = f_exe_os_comm("lscpu|grep 'NUMA node0 CPU(s)'|awk '{print $NF}'|awk -F'-' '{print $2+1}'")
    _, gloVar.res_cpu["load"] = f_exe_os_comm("uptime|awk -F'average: ' '{print $2}'|awk -F, '{print int($1)}'")
    _, gloVar.res_cpu["id"] = f_exe_os_comm("top -b -n 1|grep '%Cpu(s):' |awk '{print int($8)}'")
    _, gloVar.res_cpu["wa"] = f_exe_os_comm("top -b -n 1|grep '%Cpu(s):' |awk '{print int($10)}'")

def f_monitor_for_net(ip):
    """
    整机网络监控, 返回值均为KB
    """

    _, net_name = f_exe_os_comm("/sbin/ip a|grep 'inet " + ip + "/'|grep -P '(eth|bond)[0-9]$'|awk '{print $NF}'")

    if len(net_name) == 0 : #如果没有找到网卡名称就使用eth0

        net_name = "eth0"

    status , gloVar.res_net["speed"] = f_exe_os_comm("ethtool " + net_name + "|grep 'Speed:'|awk '{print int($2)}'")

    if status != 0 : #如果获取不到网卡的传输速度就设为0

        gloVar.res_net["speed"] = "0"

    # 下面这个逻辑是直接抓取机器的网络总传输情况
    _, net_info = f_exe_os_comm("""iftop -t -n -B -P -s 1 2>/dev/null|grep Total |awk '
            NR < 3 {
                a = $4;
                if ($4 ~ /MB/) {
                    a = ($4 ~ /MB/) ? 1024 * int($4) "KB" : $4;
                } else if ($4 ~ /GB/) {
                    a = ($4 ~ /GB/) ? 1024 * 1024 * int($4) "KB" : $4;
                }
                a = (a ~ /KB/) ? int(a) : 0
                print $2, a;
            }
            NR == 3 {

                b = $6;
                if ($6 ~ /MB/) {
                    b = ($6 ~ /MB/) ? 1024 * int($6) "KB" : $6;
                } else if ($6 ~ /GB/) {
                    b = ($6 ~ /GB/) ? 1024 * 1024 * int($6) "KB" : $6;
                }
                b = (b ~ /KB/) ? int(b) : 0
                print $1, b;
            }
    '""")

    for tmp in net_info.split("\n") :

        tmp2 = tmp.split(" ")

        if len(tmp) != 2 : continue

        gloVar.res_net[tmp2[0]] = tmp2[1]

    now_time = f_get_time()

    gloVar.res_net["time"] = now_time["log"]

def f_monitor_for_iotop():
    """
    进程io监控采集
    """

    top_dic     = {} #保存top的结果, 记录pid的cpu 内存使用情况
    ps_dic      = {} #保存ps的结果, 记录pid对应的进程信息, 因为top没有进程详情, top_dic ps_dic通过pid关联
    now_time = f_get_time()

    #获取机器总内存, 用于计算进程具体使用了多少内存
    _, mem_total = f_exe_os_comm("free |grep '^Mem:'|awk '{print int($2/1024/1024)}'")

    #抓取机器磁盘使用情况, 基于进程级别, 结果保存到全局变量 res_iotop
    _ , iotop_info = f_exe_os_comm("""iotop -d 1 -k -o -t -P -qq -b -n 1|awk -F' % ' 'NR>2{
                OFS="@@@";
                split($1,a," ");
                if(a[5] >= """ + str(r_io) + """ || a[7] >= """ + str(r_io) + """) {
                    print a[1],a[2],a[5]a[6],a[7]a[8],$NF;
                }
            }
        NR<3{
                print $0;
            }'|awk '{
                if(NR==1){
                    print $1,$2,$6,$13;
                } else if(NR==2) {
                    print $1,$2,$5,$11;
                } else {
                    print $0;
                }
            }'""")

    #抓取top详情, 目的是记录进程使用cpu 内存情况
    _, top_info = f_exe_os_comm("""top -b -n 1|grep -P "^[ 0-9]* "|awk 'NF==12{

            if($9 >= """ + str(r_cpu) + """ || $10 >= """ + str(r_mem) + """){
                for (i=1;i<=NF;i++) {
                    printf $i"@@@";
                }
                print "";
            }
        }'""")

    #抓取ps详情, 记录进程信息(因为top没有进程详细信息), 通过pid进行关联
    _, ps_info  = f_exe_os_comm("""ps -ef|awk '{printf $2"@@@" ;for(i=8;i<=NF;i++) {printf $i" "}print ""}'""")

    for tmp in ps_info.split("\n") : #遍历ps结果, 保存到字典

        tmp1 = tmp.split("@@@")

        if len(tmp1) != 2 : continue

        ps_dic[tmp1[0]] = {"info": tmp1[1]}

    for tmp in top_info.split("\n") : #遍历top结果, 保存到字典

        tmp1 = tmp.split("@@@")

        if len(tmp1) < 10 : continue

        top_dic[tmp1[0]] = {"cpu" : tmp1[8] ,"mem" : tmp1[9]}

    for tmp in iotop_info.split("\n") : #遍历iotop结果, 保存到字典

        iops = tmp.split("@@@")

        if (len(iops)==1) :

            iops = tmp.split(" ")

            gloVar.res_iotop["time"] = now_time["date"] + " " + iops[0]

            gloVar.res_iotop[iops[1]] = {
                    "read"  : iops[2],
                    "write" : iops[3]
            }

            continue

        if (len(iops) != 5) :

            continue

        port = iops[1]  #这个其实是pid

        remarks = iops[4].split(" ")

        remarks = [x for x in remarks if len(x) > 0]

        remarks = " ".join(remarks) #进程详情, 会单独写到一张表专门记录进程详情的, 按进程信息(md5)作为唯一键, 避免冗余

        gloVar.res_iotop[port] = {
                "io_r"    : iops[2],
                "io_w"    : iops[3],
                "remarks" : remarks
            }

        if(str(iops[1]) in top_dic.keys()) : #如果在top记录里面能找到这个pid的详情, 就记录一下cpu 内存使用情况

            gloVar.res_iotop[port]["cpu"] = top_dic[str(iops[1])]["cpu"] + "%"

            gloVar.res_iotop[port]["mem"] = int((float(top_dic[str(iops[1])]["mem"]) * float(mem_total))/100)

            gloVar.res_iotop[port]["mem"] = str(gloVar.res_iotop[port]["mem"]) + "GB"

        else : #如果在top记录里面不能找到这个pid的详情, 就置为0

            gloVar.res_iotop[port]["cpu"] = "0%"

            gloVar.res_iotop[port]["mem"] = "0GB"

    for k in top_dic.keys() : #遍历top_dic字典

        if k not in ps_dic.keys() :

            continue

        if float(top_dic[k]["cpu"]) < r_cpu and float(top_dic[k]["mem"]) < r_mem : #将没有产生io的进程也记录一下(cpu mem超过采集阈值的进程)

            continue

        if k not in gloVar.res_iotop.keys():  #需要注意, 这里的进程信息是在iotop没有记录下而又符合采集对象的

            gloVar.res_iotop[k] = {
                "cpu"     : top_dic[k]["cpu"] + "%",
                "mem"     : str(int((float(top_dic[k]["mem"]) * float(mem_total))/100)) + "GB",
                "io_r"    : "0",
                "io_w"    : "0",
                "remarks" : ps_dic[k]["info"]
            }

def f_monitor_for_iftop():
    """
    进程网络监控采集
    """

    #抓取iftop详情, 进程级别(这个不严谨, 确切的说是ip:port --> ip:port), 需要注意只会记录那些符合条件的
    _ , gloVar.res_iftop["iftop"] = f_exe_os_comm("""iftop -t -n -B -P -s 2 -L 200 2>/dev/null|grep -P '(<=|=>)'|sed 'N;s/\\n/,/g'|awk 'NF==13{
                    if($4 ~ /(K|M|G)B/ || $10 ~ /(K|M|G)B/) {
                        if(($4 ~ /KB/ && int($4) >= """ + str(r_net) + """) ||
                           ($10 ~ /KB/ && int($10) >= """ + str(r_net) + """) ||
                           ($4 ~ /MB/ && int($4) >= """ + str(r_net/1024) + """) ||
                           ($10 ~ /MB/ && int($10) >= """ + str(r_net/1024) + """) ||
                           ($4 ~ /GB/ || $10 ~ /GB/)) {
                           print $2,$4,$8,$10
                        }
                    }
                }'""")

    now_time = f_get_time()

    gloVar.res_iftop["time"] = now_time["log"]

def f_get_time() :
    """
    时间函数, 会返回两个时间格式
      1、2021-06-01 10:10:10 用来做日志的时间格式
      2、20210601101010      下线的时候用这个时间格式作为目录的一部分
    """
    now_time = {}

    tmp_time = str(dt.datetime.now())

    tmp_time = tmp_time[0:19]

    now_time["log"] = tmp_time        #2022-02-24 11:34:16

    now_time["date"] = tmp_time[0:10] #2022-02-24

    now_time["offline"] = tmp_time[0:4] + tmp_time[5:7] + tmp_time[8:10] + tmp_time[11:13] + tmp_time[14:16] + tmp_time[17:19] #20220224113416

    now_time["orderid"] = tmp_time[0:4] + tmp_time[5:7] + tmp_time[8:10] + tmp_time[11:13] + tmp_time[14:16] + tmp_time[17:19] + tmp_time[20:] #20220224113611597348

    return now_time

def f_write_log(log_opt, log, log_file):
    """
    写日志的函数, 将字符串写到日志文件, 这是api的日志, opt为空, 就是不在日志前面带上时间
    """

    now_time = f_get_time()

    log_dir = os.path.dirname(log_file)

    if(os.path.exists(log_dir) == False):

        os.makedirs(log_dir)

    if os.path.exists(log_file) == False:

        os.system(r"touch {}".format(log_file))

    else:

        file_size = os.path.getsize(log_file) / 1024 / 1024

        if file_size > log_size :

            now_time = f_get_time()

            tar_file = log_file+ "." + now_time["date"]

            comm_str = "sed -i '1,1000d' " + log_file

            status,out = f_exe_os_comm(comm_str = comm_str)

    with open(log_file, 'a') as f:

        if log_opt == "" :

            state = f.write(log + "\n")

        else :

            state = f.write("[ " + now_time["log"] + " ] [ " + log_opt + " ] " + log + "\n")

        f.close()

    return 0

def f_manager_state_for_node(remove_members, script_dir, log_file, rpc_server, rpc_port):
    """
    同步脚本的函数, remove_members是一个列表
    """
    d = {}

    res = {}

    mark = 0

    opt = ""

    cron = "/var/spool/cron/root"

    base_comm = 'cd '+ script_dir + ' && flock --wait 5 -x state/rpc_client_flock.lock -c "' + py3env + '/bin/python rpc.py --role client --client '

    add_cront_comm = "grep rpc_for_monitor " + cron + " || echo '*/1 * * * * bash " + script_dir + "/start_client.sh' >> " + cron

    del_cront_comm = "grep '" + script_dir + "' " + cron + " && sed -i 's#.*bash " + script_dir + "/start_client.sh.*##g' " + cron

    path_py3 = ''' 'grep "''' + python3 + '''/bin" /etc/profile || echo "export PATH=''' + python3 + '''/bin:\${PATH}" >> /etc/profile' '''

    for member in remove_members: #这是同步脚本, 保证每次执行脚本都是最新的

        d[member[0]] = 1

        if member[1] == 1 : #新加的监控节点, server端重启也会置为新加节点

            with open(script_dir + "/state/state.log", 'w') as f : #初始化client这个文件

                f.write('start')
                f.close()

            with open(script_dir + "/start_client.sh", 'w') as f : #初始化client启动脚本

                f.write('export PATH="' + python3 + "/bin:" + os_path + '"\n')

                f.write(base_comm + member[0] + ' --port ' + str(rpc_port) + ' --server ' + rpc_server + '"\n')

                f.close()

            comm_str = """ssh """ + member[0] + """ 'mkdir -p """ + script_dir + """'"""

            status,out = f_exe_os_comm(comm_str = comm_str) #client创建目录

            comm_str = """rsync -avpr --exclude "logs" """ + script_dir + """/ """ + member[0] + """:""" + script_dir
            status,out = f_exe_os_comm(comm_str = comm_str) #同步脚本

            if status != 0 :

                f_write_log(log_opt = "提示", log = "[ " + member[0] + "同步脚本目录失败 ] [ " + out + " ] [ " + comm_str + " ]", log_file = log_file)

                continue

            opt = "新加监控节点"

            if len(python3) != 0 :

                comm_str = """rsync -avpr """ + python3 + """/ """ + member[0] + """:""" + python3
                status,out = f_exe_os_comm(comm_str = comm_str) #同步python3环境

            else : status = 0

            if status != 0 :

                f_write_log(log_opt = "提示", log = "[ " + member[0] + "同步python3环境失败 ] [ " + out + " ] [ " + comm_str + " ]", log_file = log_file)

                continue

            if len(python3) != 0 :

                comm_str = """ssh """ + member[0] + path_py3

                status,out = f_exe_os_comm(comm_str = comm_str) #同步python3环境

            else : status = 0

            if status != 0 :

                f_write_log(log_opt = "提示", log = "[ " + member[0] + "设置python3环境失败 ] [ " + out + " ] [ " + comm_str + " ]", log_file = log_file)

                continue

            comm_str = """ssh """ + member[0] + """ " """ + add_cront_comm + """ " """
            status,out = f_exe_os_comm(comm_str = comm_str) #配置crontab

            if status != 0 :

                f_write_log(log_opt = "提示", log = "[ " + member[0] + "添加crontab失败 ] [ " + out + " ] [ " + comm_str + " ]", log_file = log_file)

                continue

            d[member[0]] = status

        elif member[1] == 0 :

            opt = "监控节点下线"

            with open(script_dir + "/state/state.log", 'w') as f : #初始化client这个文件

                f.write('stop')
                f.close()

            state_file = script_dir + "/state/state.log "

            comm_str = """rsync -avpr --exclude "logs" """ + state_file + " " + member[0] + """:""" + script_dir + """/state/"""
            status,out = f_exe_os_comm(comm_str = comm_str) #同步这个文件到client

            if status != 0 :

                f_write_log(log_opt = "提示", log = "[ " + member[0] + "设置关闭项失败 ] [ " + out + " ] [ " + comm_str + " ]", log_file = log_file)

            start_file = script_dir + "/start_client.sh"

            with open(start_file , 'w') as f : #初始化启动脚本, 设置为exit, 避免crontab没下掉而又被拉起

                f.write('exit')
                f.close()

            comm_str = """ssh """ + member[0] + """ " """ + del_cront_comm + """ " """
            status,out = f_exe_os_comm(comm_str = comm_str) #删除crontab

            if status != 0 :

                f_write_log(log_opt = "提示", log = "[ " + member[0] + "删除cront任务失败 ] [ " + out + " ] [ " + comm_str + " ]", log_file = log_file)

            comm_str = """rsync -avpr --exclude "logs" """ + start_file + " " + member[0] + """:""" + script_dir + """/ |tr "\n" " " """
            status,out = f_exe_os_comm(comm_str = comm_str)

            if status != 0 :

                f_write_log(log_opt = "提示", log = "[ " + member[0] + "停掉任务失败 ] [ " + out + "] [ " + comm_str + " ]", log_file = log_file)

            d[member[0]] = status

        else :

            continue

        if status == 0 :

            f_write_log(log_opt = "INFO", log = "[ " + opt + "成功 ] [ " + member[0] + " ] ", log_file = log_file)

        else :

            f_write_log(log_opt = "ERROR", log = "[ " + opt + "失败 ] [ " + member[0] + " ] ", log_file = log_file)

    for k in d.keys(): #如果有节点同步失败, d字典就不为空, 所以遍历这个字典

        if d[k] != 0:

            mark = -1  #mark=-1表示有节点同步脚本失败

            res[k] = "管理client任务失败."  #同步失败不处理

    return mark, res

def f_send_alert_to_bot(info) :

    now_time = f_get_time()

    info = now_time["log"] + "\n" + info.replace(";","\n")

    header = {'content-type': "application/json"}

    dic = {
             "msgtype": "text",
             "text": {
                 "content": info
             }
        }

    try :

        res = json.loads(requests.post(wx_url, json = dic, headers = header, timeout = 10, verify=False).text)

        if "resp" not in res.keys() or "errcode" not in res["resp"].keys() : status = 2
            #返回结果失败

        if res["resp"]["errcode"] == 0: status = 0

        else : status = 1 #发送失败

    except Exception as e :

        status = 3

    return status
