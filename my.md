[TOC]

### 一、巡检报告

#### 1、一键巡检

    obdiag check run \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}

一键集群全量巡检结束后会生成一份报告，存放路径是`${log_dir}/obdiag_check_report_{observer|obproxy}_{yyyy-mm-dd-HH-MM-SS}.table`。如下是一份测试环境的报告，需要注意的是，报告内容很多，所以只保留了有问题的部分，其余部分已经删减。

（1）fail-tasks-report

    observer commit id: 4.2.5.3_103000022025033117-35332d18a11e56f660c3be9383a5682322cd7949(Mar 31 2025 18:00:08)
    +-------------------------------------------------------------------------------------------------------+
    |                                           fail-tasks-report                                           |
    +-----------------------------------+-------------------------------------------------------------------+
    |                task               | task_report                                                       |
    +-----------------------------------+-------------------------------------------------------------------+
    |       network.log_easy_slow       | [fail] Failed to parse EASY SLOW count on remote_10_191_78_171: 0 |
    |                                   | 0                                                                 |
    | network.network_write_cond_wakeup | [fail] Failed to parse wakeup count on remote_10_191_78_171: 0    |
    |                                   | 0                                                                 |
    +-----------------------------------+-------------------------------------------------------------------+

第一个是查找该节点中是否有`EASY SLOW`。第二个是查找该节点中是否有`write cond wakeup`，这两个都属于逻辑问题，需要改一下代码，官方应该在下个版本修复。

经过跟官方沟通，说`fail-tasks-report`都属于逻辑错误，这里这两个可以通过修改`python`脚本规避。

    ~/.obdiag/check/tasks/observer/network/network_write_cond_wakeup.py
    ~/.obdiag/check/tasks/observer/network/log_easy_slow.py

    将这两个文件里面删除{|| echo '0'}部分即可

（2）critical-tasks-report

    +----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    |                                                                                                   critical-tasks-report                                                                                                    |
    +----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    |            task            | task_report                                                                                                                                                                                   |
    +----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
    |    disk.mount_disk_full    | [critical] node: remote_10_191_78_171 mount point: /tmp disk usage: 95%, over 90%                                                                                                             |
    |      disk.xfs_repair       | [critical] [remote_10_191_78_171] xfs need repair. Please check disk. xfs_repair_log: dmesg: read kernel buffer failed: Operation not permitted                                               |
    | cluster.data_path_settings | [critical] [remote_10_191_78_171] ip:10.191.78.171 ,data_dir and log_dir_disk are on the same disk.                                                                                           |
    |   cluster.task_opt_stat    | [critical] [cluster:(Please set ob_cluster_name or obproxy_cluster_name)] The collection of statistical information related to tenants has issues.. Please check the tenant_ids: 1,1001,1002  |
    | network.TCP-retransmission | [critical] [remote_10_191_78_171] tsar is not installed. we can not check tcp retransmission.                                                                                                 |
    |    network.network_drop    | [critical] [remote_10_191_78_171] network: bond0  RX error is not 0, please check by ip -s link show bond0                                                                                    |
    |   network.network_speed    | [critical] [remote_10_191_78_171] network_speed is null , can not get real speed                                                                                                              |
    |    system.mount_options    | [critical] node: remote_10_191_78_171 /mnt/nfs_share mount option lookupcache=positive is not exist                                                                                           |
    |                            | [critical] node: remote_10_191_78_171 /mnt/nfs_share mount option nfsvers=4.1 is not exist                                                                                                    |
    +----------------------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+



    [critical] node: remote_10_191_78_171 mount point: /tmp disk usage: 95%, over 90%

这个是`/tmp`分区快满了，需要及时清理空间。

    [remote_10_191_78_171] xfs need repair. Please check disk. xfs_repair_log: dmesg: read kernel buffer failed: Operation not permitted 

这个是因为`obdiag`读取到`xfs`文件系统有问题，然后想进一步查看`dmesg`的日志文件，但是提示了一个权限不足。解决方式有如下两个：

第一个方法是修改`obdiag`采集脚本的命令。

    vim .obdiag/check/tasks/observer/disk/xfs_repair.yaml   # 执行dmesg命令的时候带上sudo

第二个方法是修改操作系统内核参数，给普通用户也拥有执行`dmesg`命令的权限。

    sudo sysctl kernel.dmesg_restrict         #查看是否是0，如果是1则需要改成0

    sudo sysctl -w kernel.dmesg_restrict=0    #临时修改

    echo "kernel.dmesg_restrict = 0" | sudo tee -a /etc/sysctl.conf    #永久修改



    [critical] [remote_10_191_78_171] ip:10.191.78.171 ,data_dir and log_dir_disk are on the same disk.

这个是数据目录和日志目录放在一个分区，建议分开。

    [critical] [cluster:(Please set ob_cluster_name or obproxy_cluster_name)] The collection of statistical information related to tenants has issues.. Please check the tenant_ids: 1,1001,1002

这个是因为统计信息失效了，重新采集一下就好了。

    [remote_10_191_78_171] tsar is not installed. we can not check tcp retransmission.

这个是因为目标机器没有tsar工具，导致无法检查`TCP`重传情况，安装上就好了。

    [remote_10_191_78_171] network: bond0  RX error is not 0, please check by ip -s link show bond0

这个表示网络接口接受错误计数器不为零，需要关注一下网络问题。

    [critical] [remote_10_191_78_171] network_speed is null , can not get real speed 

这个是因为`obdiag`执行`ethtool`工具的时候没获取网卡带宽大小，也是需要修改`yaml`文件加上`sudo`才行。

    vim .obdiag/check/tasks/observer/network/network_speed.yaml 将所有ethtool命令前面加上sudo



    [critical] node: remote_10_191_78_171 /mnt/nfs_share mount option lookupcache=positive is not exist

这个表示`nfs`挂载的时候没有带上`lookupcache=positive`参数。

    [critical] node: remote_10_191_78_171 /mnt/nfs_share mount option nfsvers=4.1 is not exist 

这个是因为`nfs`版本不是`obdiag`推荐的版本。

#### 2、一键诊断分析

    obdiag analyze log --since 10h \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}

如果执行的时候目标机器文件个数太多超过默认值`50`会导致执行失败，报错如下：

    +---------------+--------------------------------------------------------------------+------------+--------------------+-------------+-----------+
    | Node          | Status                                                             | FileName   | First Found Time   | ErrorCode   | Message   |
    +===============+====================================================================+============+====================+=============+===========+
    | 10.191.78.171 | Error:Too many files 53 > 50, Please adjust the analyze time range |            |                    |             |           |
    +---------------+--------------------------------------------------------------------+------------+--------------------+-------------+-----------+

这种情况可以带上`--inner_config obdiag.basic.file_number_limit=300`参数来避免报错。

    Analyze OceanBase Online Log Summary:
    +---------------+-----------+----------------------------------------------------------------------------------------------------------+----------------------------+-------------+-----------+---------+
    | Node          | Status    | FileName                                                                                                 | First Found Time           |   ErrorCode | Message   |   Count |
    +===============+===========+==========================================================================================================+============================+=============+===========+=========+
    | 10.191.78.171 | Completed | /home/dumbo/mylog/obdiag_analyze_pack_20250828201411/remote_10_191_78_171/observer.log.20250828112203347 | 2025-08-28 11:06:45.096678 |       -4012 | Timeout   |       1 |
    +---------------+-----------+----------------------------------------------------------------------------------------------------------+----------------------------+-------------+-----------+---------+

    Details:

    Node: 10.191.78.171
    Status: Completed
    FileName: /home/dumbo/mylog/obdiag_analyze_pack_20250828201411/remote_10_191_78_171/observer.log.20250828112203347
    First Found Time: 2025-08-28 11:06:45.096678
    ErrorCode: -4012
    Message: Timeout
    Count: 1
    Last Found Time: 2025-08-28 11:06:45.096678
    Cause: Internal Error
    Solution: Contact OceanBase Support
    Trace_IDS: {'B420ABF4EAB-00063D6431C850E4-0-0'}

可以发现分析了最近十小时的日志得知，该集群发生了一次`-4012`的错误，该错误被记录在了`observer.log.20250828112203347`日志，更加详细的错误信息可以通过`Trace_IDS`在该日志查阅，如下面的命令。

    grep "B420ABF4EAB-00063D6431C850E4-0-0" /home/dumbo/mylog/obdiag_analyze_pack_20250828201411/remote_10_191_78_171/observer.log.20250828112203347

#### 3、一键根因分析

（1）断连接

    obdiag rca run --scene=disconnection --env since=1d \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}



    +---------------------------------------------------------------------------------------------------------+
    |                                                  record                                                 |
    +------+--------------------------------------------------------------------------------------------------+
    | step | info                                                                                             |
    +------+--------------------------------------------------------------------------------------------------+
    |  1   | node:10.192.68.89 obproxy_diagnosis_log:[2025-08-28 11:29:43.472774] [5849][Y0-00007FE1CF23A9C0] |
    |      | [CONNECTION](trace_type="CLIENT_VC_TRACE", connection_diagnosis={cs_id:16265217, ss_id:0,        |
    |      | proxy_session_id:774694285139443722, server_session_id:0, client_addr:"7.37.2.154:46690",        |
    |      | server_addr:"*Not IP address [0]*:0", proxy_server_addr:"*Not IP address [0]*:0",                |
    |      | cluster_name:"test", tenant_name:"sys", user_name:"root", error_code:-10010, error_msg:"An       |
    |      | unexpected connection event received from client while obproxy reading request",                 |
    |      | request_cmd:"OB_MYSQL_COM_QUERY", sql_cmd:"OB_MYSQL_COM_QUERY",                                  |
    |      | req_total_time(us):0}{vc_event:"VC_EVENT_EOS", user_sql:"select version();"})                    |
    |  2   | cs_id:16265217, server_session_id:0                                                              |
    |  3   | observer_trace_id is Y0-0000000000000000-0-0, Not reaching the working thread                    |
    |  4   | trace_type:CLIENT_VC_TRACE                                                                       |
    |  5   | error_code:-10010                                                                                |
    +------+--------------------------------------------------------------------------------------------------+
    The suggest: Need client cooperation for diagnosis

通过上面的报告记录可知：该集群在`2025-08-28 11:29:43`左右记录了一条断连接的记录。错误代码是`-10010`，客户端地址是`7.37.2.154:46690`，执行的sql是`select version();`

（2）卡合并

    obdiag rca run --scene=major_hold --env since=1d \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}



    +-------------------------------------------------------------------------------+
    |                                     record                                    |
    +------+------------------------------------------------------------------------+
    | step | info                                                                   |
    +------+------------------------------------------------------------------------+
    |  1   | observer version: 4.2.5.3                                              |
    |  2   | check major task is error or not                                       |
    |  3   | CDB_OB_MAJOR_COMPACTION is not exist IS_ERROR='YES'                    |
    |  4   | check on CDB_OB_MAJOR_COMPACTION IS_ERROR is 'YES'.  sql:select * from |
    |      | oceanbase.CDB_OB_MAJOR_COMPACTION where IS_ERROR="YES";                |
    |  5   | __all_virtual_compaction_diagnose_info is not exist status="FAILED";   |
    |  6   | No merge tasks that have not ended beyond the expected time            |
    +------+------------------------------------------------------------------------+
    The suggest: major merge abnormal situation not need execute

通过上面的分析报告得知，该集群存在一些合并任务失败的情况，

（3）锁冲突

    obdiag rca run --scene=lock_conflict --env since=24d \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}



    obdiag version: 3.6.0
    observer Version: 4.2.5.3
    +----------------------------------+
    |              record              |
    +------+---------------------------+
    | step | info                      |
    +------+---------------------------+
    |  1   | observer version: 4.2.5.3 |
    +------+---------------------------+
    The suggest
    +--------------------------------------+
    |                record                |
    +------+-------------------------------+
    | step | info                          |
    +------+-------------------------------+
    |  1   | on GV$OB_LOCKS result is null |
    +------+-------------------------------+
    The suggest: No block lock found. Not Need Execute

葱报告结果看没有检查到有锁冲突。

（4）DDL报错磁盘满

    obdiag rca run --scene=ddl_disk_full --env tenant_name=sys --env table_name=sbtest1 --env action_type=add_index --env index_name=idx_name --env database_name=sbtest \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}

这里需要注意，租户和表和库名要对上，要不然可能会报下面的错误，找不到表。

    [ERROR] rca run Exception: rca_scene.init err: can not find table id by table name: sbtest1. Please check the table name.



    +---------------------------------------------+
    |                    record                   |
    +------+--------------------------------------+
    | step | info                                 |
    +------+--------------------------------------+
    |  1   | observer version: 4.2.5.3            |
    |  2   | table_id is 500012                   |
    |  3   | tenant_id is 1                       |
    |  4   | estimated_size is ()                 |
    |  5   | index_name is idx_name               |
    |  6   | action_type is add_index             |
    |  7   | index_table_id is 500013             |
    |  8   | main_table_sum_of_data_length is 20  |
    |  9   | index_table_sum_of_data_length is 20 |
    +------+--------------------------------------+

因为是测试环境，所以一切正常。

（5）clog磁盘满

    obdiag rca run --scene=clog_disk_full \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}



    +--------------------------------------------------+
    |                      record                      |
    +------+-------------------------------------------+
    | step | info                                      |
    +------+-------------------------------------------+
    |  1   | observer version: 4.2.5.3                 |
    |  2   | Not find tenant_ids about clog_disk_full. |
    +------+-------------------------------------------+

测试环境一切正常。

（5）错误日志

    obdiag rca run --scene=log_error \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}

错误日志的报告是按租户维度，所以租户越多报告的内容越多。

    +----------------------------------------------------------------------------------------------------+
    |                                               record                                               |
    +------+---------------------------------------------------------------------------------------------+
    | step | info                                                                                        |
    +------+---------------------------------------------------------------------------------------------+
    |  1   | tenant_id: 1.                                                                               |
    |  2   | start step1                                                                                 |
    |  3   | all ls_id:[1]                                                                               |
    |  4   | on ls_id: 1                                                                                 |
    |  5   | Normal. The ls_id's leader number = 1                                                       |
    |  6   | start step2                                                                                 |
    |  7   | on ls_id: 1                                                                                 |
    |  8   | Normal. Unable to find a replica where both election_role and palf_role are leaders, but    |
    |      | log_handler_role is follower                                                                |
    |  9   | start step3                                                                                 |
    |  10  | tenant_id: 1, ls_id: 1                                                                      |
    |  11  | Normal.Unable to find a replica where the selection_role is a leader, but the palf_role and |
    |      | palf_state are not leaders or active, respectively                                          |
    +------+---------------------------------------------------------------------------------------------+
    The suggest: Normal. Not find the reason of the log handler failure in taking over.

    +----------------------------------------------------------------------------------------------------+
    |                                               record                                               |
    +------+---------------------------------------------------------------------------------------------+
    | step | info                                                                                        |
    +------+---------------------------------------------------------------------------------------------+
    |  1   | tenant_id: 1001.                                                                            |
    |  2   | start step1                                                                                 |
    |  3   | all ls_id:[1]                                                                               |
    |  4   | on ls_id: 1                                                                                 |
    |  5   | Normal. The ls_id's leader number = 1                                                       |
    |  6   | start step2                                                                                 |
    |  7   | on ls_id: 1                                                                                 |
    |  8   | Normal. Unable to find a replica where both election_role and palf_role are leaders, but    |
    |      | log_handler_role is follower                                                                |
    |  9   | start step3                                                                                 |
    |  10  | tenant_id: 1001, ls_id: 1                                                                   |
    |  11  | Normal.Unable to find a replica where the selection_role is a leader, but the palf_role and |
    |      | palf_state are not leaders or active, respectively                                          |
    +------+---------------------------------------------------------------------------------------------+
    The suggest: Normal. Not find the reason of the log handler failure in taking over.

    +----------------------------------------------------------------------------------------------------+
    |                                               record                                               |
    +------+---------------------------------------------------------------------------------------------+
    | step | info                                                                                        |
    +------+---------------------------------------------------------------------------------------------+
    |  1   | tenant_id: 1002.                                                                            |
    |  2   | start step1                                                                                 |
    |  3   | all ls_id:[1, 1001]                                                                         |
    |  4   | on ls_id: 1                                                                                 |
    |  5   | Normal. The ls_id's leader number = 1                                                       |
    |  6   | on ls_id: 1001                                                                              |
    |  7   | Normal. The ls_id's leader number = 1                                                       |
    |  8   | start step2                                                                                 |
    |  9   | on ls_id: 1                                                                                 |
    |  10  | Normal. Unable to find a replica where both election_role and palf_role are leaders, but    |
    |      | log_handler_role is follower                                                                |
    |  11  | on ls_id: 1001                                                                              |
    |  12  | Normal. Unable to find a replica where both election_role and palf_role are leaders, but    |
    |      | log_handler_role is follower                                                                |
    |  13  | start step3                                                                                 |
    |  14  | tenant_id: 1002, ls_id: 1                                                                   |
    |  15  | Normal.Unable to find a replica where the selection_role is a leader, but the palf_role and |
    |      | palf_state are not leaders or active, respectively                                          |
    |  16  | tenant_id: 1002, ls_id: 1001                                                                |
    |  17  | Normal.Unable to find a replica where the selection_role is a leader, but the palf_role and |
    |      | palf_state are not leaders or active, respectively                                          |
    +------+---------------------------------------------------------------------------------------------+
    The suggest: Normal. Not find the reason of the log handler failure in taking over.

该集群有三个租户，状态正常。

（6）DDL失败

    obdiag rca run --scene=ddl_failure --env tenant_id=1 --env table_id=500012 --env tablet_id=200002 \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}

需要注意，这里需要获取`table_id`和`tablet_id`两个关键值，但是文档没提示从哪里获取这两个值，可以通过下面查询获取：

    mysql> select tenant_id,table_id,tablet_id from oceanbase.__all_virtual_table where table_name = 'sbtest1' and database_id='500011';
    +-----------+----------+-----------+
    | tenant_id | table_id | tablet_id |
    +-----------+----------+-----------+
    |         1 |   500012 |    200002 |
    +-----------+----------+-----------+
    1 row in set (0.02 sec)

    mysql>



    +----------------------------------------------------------------------------------+
    |                                      record                                      |
    +------+---------------------------------------------------------------------------+
    | step | info                                                                      |
    +------+---------------------------------------------------------------------------+
    |  1   | input parameters: tenant_id: 1, table_id: 500012, tablet_id: 200002       |
    |  2   | diagnose use parameters: tenant_id: 1, table_id: 500012, tablet_id 200002 |
    +------+---------------------------------------------------------------------------+
    The suggest
    +-------------------------------------------------------------------------------------------------------------+
    |                                                    record                                                   |
    +------+------------------------------------------------------------------------------------------------------+
    | step | info                                                                                                 |
    +------+------------------------------------------------------------------------------------------------------+
    |  1   | ddl error message is empty, query sql: select * from oceanbase.__all_virtual_ddl_error_message where |
    |      | tenant_id=1 and object_id=500012 and target_object_id=-1 order by gmt_create desc limit 1            |
    +------+------------------------------------------------------------------------------------------------------+
    The suggest: no ddl error message, no need to diagnose

该集群这个巡检项，状态正常。需要注意，如果这个租户id和表id没有找到记录的话，会报一个表没找到，这个提示有点误导人，比如下面的提示信息：

    [ERROR] rca run Exception: rca_scene.init err: , query sql: select * from oceanbase.__all_virtual_table_history where tenant_id=1002 and table_id=500012 and is_deleted = 0 limit 1

（7）添加索引失败

    obdiag rca run --scene=index_ddl_error --env tenant_name=sys --env table_name=sbtest1 --env database_name=sbtest --env index_name=idx_name \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}



    +-------------------------------------------------------------------------------------------------------+
    |                                                 record                                                |
    +------+------------------------------------------------------------------------------------------------+
    | step | info                                                                                           |
    +------+------------------------------------------------------------------------------------------------+
    |  1   | tenant_id is 1                                                                                 |
    |  2   | database_id is 500011                                                                          |
    |  3   | table_id is 500012                                                                             |
    |  4   | index_table_id is 500013                                                                       |
    |  5   | index_name is idx_name                                                                         |
    |  6   | trace_id is YB420ABF4EAB-00063D6442912910-0-0                                                  |
    |  7   | task_id is 1529883                                                                             |
    |  8   | gather rootservice.log  by YB420ABF4EAB-00063D6442912910-0-0                                   |
    |  9   | Log saving                                                                                     |
    |      | location：mylog/obdiag_index_ddl_error_20250829145840/YB420ABF4EAB-00063D6442912910-0-0_on_rs/ |
    +------+------------------------------------------------------------------------------------------------+
    The suggest: The index creation failed during the other phase. Please upload mylog/obdiag_index_ddl_error_20250829145840 to the OceanBase community

这个报告提示有错误，但是根据提示的内容进到`mylog/obdiag_index_ddl_error_20250829145840/YB420ABF4EAB-00063D6442912910-0-0_on_rs/`目录去看详情又是成功的，所以忽略即可。

（8）事务断联场景

    obdiag rca run --scene=transaction_disconnection --env since=4h \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}



    +----------------------------------------------------------+
    |                          record                          |
    +------+---------------------------------------------------+
    | step | info                                              |
    +------+---------------------------------------------------+
    |  1   | observer version: 4.2.5.3                         |
    |  2   | syslog_level data is WDIAG                        |
    |  3   | no log about 'session is kill' to get session_id. |
    +------+---------------------------------------------------+
    The suggest: no log about 'session is kill' to get session_id. please check the log file on mylog/obdiag_transaction_disconnection_20250829150943/session_killed_log

该集群这个巡检项，状态正常。

（9）悬挂事务

    obdiag rca run --scene=suspend_transaction --env since=4h \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}



    +--------------------------------------+
    |                record                |
    +------+-------------------------------+
    | step | info                          |
    +------+-------------------------------+
    |  1   | observer version: 4.2.5.3     |
    |  2   | Not find suspend_transaction. |
    +------+-------------------------------+
    The suggest

该集群这个巡检项，状态正常。

（10）unit\_gc异常

    obdiag rca run --scene=unit_gc \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}



    +------------------------------------------------------------------------------------------+
    |                                          record                                          |
    +------+-----------------------------------------------------------------------------------+
    | step | info                                                                              |
    +------+-----------------------------------------------------------------------------------+
    |  1   | observer version: 4.2.5.3                                                         |
    |  2   | find tenant_ids about unit_gc. sql: select * from oceanbase.gv$ob_units;          |
    |  3   | save gv_ob_units_data to mylog/obdiag_unit_gc_20250829154903/gv_ob_units_data.txt |
    |  4   | start analyze gv_ob_units_data                                                    |
    |  5   | find tenant_ids about unit_gc. task_list: []                                      |
    |  6   | start gather log about unit_gc                                                    |
    |  7   | Not find tenant_ids about unit_gc.                                                |
    +------+-----------------------------------------------------------------------------------+
    The suggest: Please send mylog/obdiag_unit_gc_20250829154903 to the Oceanbase community.

该集群这个巡检项，状态正常。

（11）回放卡

    obdiag rca run --scene=replay_hold \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}



    +------------------------------------------------------------------------------------------------------------+
    |                                                   record                                                   |
    +------+-----------------------------------------------------------------------------------------------------+
    | step | info                                                                                                |
    +------+-----------------------------------------------------------------------------------------------------+
    |  1   | observer version: 4.2.5.3                                                                           |
    |  2   | start check the replay_hold scene                                                                   |
    |  3   | start check the replay_hold scene                                                                   |
    |  4   | check the replay_hold. by sql: select a.svr_ip, a.svr_port, a.tenant_id, a.ls_id, b.end_scn,        |
    |      | a.unsubmitted_log_scn, a.pending_cnt from oceanbase.__all_virtual_replay_stat a join                |
    |      | oceanbase.__all_virtual_log_stat b on a.svr_ip=b.svr_ip and a.svr_port=b.svr_port and               |
    |      | a.tenant_id=b.tenant_id and a.ls_id = b.ls_id and a.role='FOLLOWER'                                 |
    |  5   | sql: select a.svr_ip, a.svr_port, a.tenant_id, a.ls_id, b.end_scn, a.unsubmitted_log_scn,           |
    |      | a.pending_cnt from oceanbase.__all_virtual_replay_stat a join oceanbase.__all_virtual_log_stat b on |
    |      | a.svr_ip=b.svr_ip and a.svr_port=b.svr_port and a.tenant_id=b.tenant_id and a.ls_id = b.ls_id and   |
    |      | a.role='FOLLOWER' execute result is empty.                                                          |
    |  6   | no unsubmitted_scn < end_scn found.                                                                 |
    +------+-----------------------------------------------------------------------------------------------------+
    The suggest: no unsubmitted_scn < end_scn found.
    Please send mylog/obdiag_replay_hold_20250829155003 to the Oceanbase community.

该集群这个巡检项，状态正常。

（12）集群内存

    obdiag rca run --scene=memory_full \
        --inner_config obdiag.basic.file_number_limit=300 \
        --config ocp.login.url=${ocp_url} \
        --config ocp.login.user=${ocp_user} \
        --config ocp.login.password=${ocp_pass} \
        --store_dir=${log_dir} \
        --config db_host=${ob_host}\
        --config db_port=${ob_port} \
        --config tenant_sys.user=${tenant} \
        --config tenant_sys.password=${ob_pass} \
        --config obcluster.servers.global.home_path=${ob_home_dir} \
        --config obcluster.ob_cluster_name=${cluster_name} \
        --config obcluster.servers.nodes[0].net_interface=eth0 \
        --config obcluster.servers.nodes[0].ip=${node1} \
        --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
        --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
        --config obcluster.servers.global.ssh_port=${ssh_port} \
        --config obcluster.servers.global.ssh_username=${ssh_user} \
        --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
        --config obproxy.servers.nodes[0].ip=${node0} \
        --config obproxy.servers.global.home_path=${obp_home_dir} \
        --config obproxy.servers.global.ssh_port=${ssh_port} \
        --config obproxy.servers.global.ssh_username=${ssh_user} \
        --config obproxy.servers.global.ssh_key_file=${ssh_rsa}



    +--------------------------------------------------------------------------+
    |                                  record                                  |
    +------+-------------------------------------------------------------------+
    | step | info                                                              |
    +------+-------------------------------------------------------------------+
    |  1   | observer version: 4.2.5.3                                         |
    |  2   | start check the memory_full scene                                 |
    |  3   | ob_connector is exist, use sql to save __all_virtual_memory_info. |
    |  4   | Not find log.                                                     |
    +------+-------------------------------------------------------------------+
    The suggest: Please send mylog/obdiag_memory_full_20250829162648 to the Oceanbase community.

该集群这个巡检项，状态正常。

（13）删除observer节点异常

需要注意，需要带上`svr_ip svr_port`这两个参数，要不然会报错，这点官方文档没有写。

```
obdiag rca run --scene=delete_server_error --env svr_ip=10.191.78.171 --env svr_port=2883 \
    --inner_config obdiag.basic.file_number_limit=300 \
    --config ocp.login.url=${ocp_url} \
    --config ocp.login.user=${ocp_user} \
    --config ocp.login.password=${ocp_pass} \
    --store_dir=${log_dir} \
    --config db_host=${ob_host}\
    --config db_port=${ob_port} \
    --config tenant_sys.user=${tenant} \
    --config tenant_sys.password=${ob_pass} \
    --config obcluster.servers.global.home_path=${ob_home_dir} \
    --config obcluster.ob_cluster_name=${cluster_name} \
    --config obcluster.servers.nodes[0].net_interface=eth0 \
    --config obcluster.servers.nodes[0].ip=${node1} \
    --config obcluster.servers.nodes[0].data_dir=${ob_data_dir} \
    --config obcluster.servers.nodes[0].redo_dir=${ob_redo_dir} \
    --config obcluster.servers.global.ssh_port=${ssh_port} \
    --config obcluster.servers.global.ssh_username=${ssh_user} \
    --config obcluster.servers.global.ssh_key_file=${ssh_rsa} \
    --config obproxy.servers.nodes[0].ip=${node0} \
    --config obproxy.servers.global.home_path=${obp_home_dir} \
    --config obproxy.servers.global.ssh_port=${ssh_port} \
    --config obproxy.servers.global.ssh_username=${ssh_user} \
    --config obproxy.servers.global.ssh_key_file=${ssh_rsa}


```

```
+-------------------------------------------------------------------------------------------------------------+
|                                                    record                                                   |
+------+------------------------------------------------------------------------------------------------------+
| step | info                                                                                                 |
+------+------------------------------------------------------------------------------------------------------+
|  1   | observer version: 4.2.5.3                                                                            |
|  2   | start check enable_rebalance by: show parameters like 'enable_rebalance';                            |
|  3   | start check tenant by: select tenant_id from oceanbase.__all_resource_pool where resource_pool_id in |
|      | (select resource_pool_id from oceanbase.__all_unit where svr_ip = '10.191.78.171' and svr_port =     |
|      | '2883');                                                                                             |
|  4   | sql: select tenant_id from oceanbase.__all_resource_pool where resource_pool_id in (select           |
|      | resource_pool_id from oceanbase.__all_unit where svr_ip = '10.191.78.171' and svr_port = '2883');    |
|      | execute result is empty.                                                                             |
|  5   | sql: select ZONE from oceanbase.DBA_OB_SERVERS where svr_ip='10.191.78.171' and svr_port=2883;       |
|      | execute result is empty.                                                                             |
|  6   | node 10.191.78.171 is not in the cluster                                                             |
+------+------------------------------------------------------------------------------------------------------+

```

该集群这个巡检项，状态正常。
