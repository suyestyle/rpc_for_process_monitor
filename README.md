## 使用指南

### 一、引言

因线上机器基本都是单机多实例，有时候会出现因为某个实例而影响了整个机器的性能。因缺少进程级别的监控，事后想分析是哪个实例跑满了系统资源往往比较困难。为了解决这一运维痛点，迫切希望实现进程级别的监控。

> 进程级别的资源监控，包括但是不限于CPU, 内存, 磁盘IO, 网络流量。

### 二、环境准备

#### 1、系统环境
```
$ uname -a
Linux 3.10.0-693.21.1.el7.x86_64 #1 SMP Wed Mar 7 19:03:37 UTC 2018 x86_64 x86_64 x86_64 GNU/Linux
$ cat /etc/redhat-release
CentOS Linux release 7.4.1708 (Core)
```
> 其他环境没有测试, 可能会出现异常，请根据实际情况解决。

#### 2、python3环境

进到虚拟环境安装必要的模块

```
virtualenv -p /usr/local/python3/bin/python3 py37env  
source py37env/bin/activate
pip install -r init/requirements.txt
```
> 用自带的虚拟环境，这三个操作就不用做了

#### 3、操作系统工具
```
ip,top,netstat,df,awk,grep,sed,free,lscpu,uptime,iftop,iotop,md5sum,tr,cd,ssh,rsync,python3,timeout
```

### 三、工作原理

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/monitor-info.png "monitor-info.png")

#### 1、server

- 线程1

这个线程会做三个事情：

（1）在server重启的时候会去读【tb_monitor_version】表，判断当前版本号跟MySQL记录的版本号是否一致，如果不一致就会去更新MySQL记录的版本号。然后将【tb_monitor_host_config】表所有istate=2的节点更新为istate=1。

（2）管理client上线下线，每30s去读一次【tb_monitor_host_config】表，将需要上线的节点或者需要下线的节点进行维护。istate=1表示需要上线，就会去部署监控脚本（升级就更新代码），并更新为istate=2，istate=0表示需要下线，会去下线该client节点并更新为istate=-1。

（3）管理client状态，每30s去读一次【tb_monitor_host_config，tb_monitor_alert_info，tb_monitor_host_info】表（三表关联），将最近两分钟没有上报的client且最近5min没有被告警的节点统计出来并告警。

- 线程2

这个线程做两个事：

（1）等待client上报监控数据，然后进行二次分析并写到MySQL中。

（2）返回当前版本号给client。

#### 2、client

client端会做三个事情

（1）六线程并行去采集【机器cpu】【机器内存】【机器磁盘】【机器网络】【进程网络】【进程io，进程cpu，进程内存】。采集完毕后，主线程会进行分析并上报给server端。

（2）在上报过程中如果遇到连续三次server都是异常状态就会将server异常记录（避免多个client同时告警）到【tb_monitor_alert_info】表发送告警。

（3）上报完成后会判断自己的版本号跟server端返回的版本号是否一致，如果不一致就会退出程序，等待crontab拉起，以此完成升级。

> server端完成代码更新，在重启server的时候会将新代码同步到各个client。

#### 3、MySQL

MySQL的作用是存版本信息，client ip配置，监控数据，以及告警状态等。

#### 4、grafana

grafana的作用是从MySQL读取监控数据并展示出来。

#### 5、alert

采用企业微信的机器人作为告警通道。

> 客户端数据采集/分析部分可以参考这个文章第三部分第二点   https://mp.weixin.qq.com/s/UCSZWYJ5D4_EoK6mud2pPQ

### 四、使用介绍
#### 1、部署server

软件版本可能存在兼容性问题，所以其他版本不确定是否能用，请各自测试调试。

##### （1）clone项目

```
mkdir -p /opt/soft/git
cd /opt/soft/git
git clone https://gitee.com/mo-shan/rpc_for_process_monitor.git
```

> 依赖Python3环境，建议3.7.4，要求python3在PATH里面，安装过程略。

##### （2）部署server

```
cp -r /opt/soft/git/rpc_for_process_monitor /opt/soft/rpc_for_monitor  #注意这里的目录是有区别的, 主要是希望开发环境跟实际部署的目录不一样, 避免失误
cd /opt/soft/rpc_for_monitor
```

```
$ tree -L 2
.
├── conf
│   └── config.ini                  #配置文件
├── img                             #忽略
│   ├── all-info.png
│   ├── cpu-info.png
│   ├── disk-info.png
│   ├── grafana-data-source-1.png
│   ├── grafana-data-source-2.png
│   ├── grafana-data-source-3.png
│   ├── grafana-data-source-4.png
│   ├── grafana-data-source-5.png
│   ├── grafana-data-source-6.png
│   ├── grafana-data-source-7.png
│   ├── mem-info.png
│   ├── net-info.png
│   └── process-info.png
├── init                            #初始化文件
│   ├── grafana.json                #grafana配置模板
│   ├── init.sql                    #MySQL建表语句
│   └── requirements.txt            #python3依赖的模块
├── lib                             #库文件
│   ├── Config.py                   #解析config.ini
│   ├── ConnectMySQL.py             #连接并操作MySQL
│   ├── globalVar.py                #全局变量
│   ├── Public.py                   #公共函数
│   └── __pycache__
├── LICENSE
├── logs                            #日志目录
│   └── info.log                    #日志文件
├── py37env                         #虚拟环境，要求在/opt/soft/rpc_for_monitor/py37env下才能使用（activate等文件的路径写死了）
│   ├── bin
│   ├── include
│   ├── lib
│   └── pip-selfcheck.json
├── README.md                       #帮助文档
├── rpc.py                          #主程序
├── start_server.sh                 #server端的启动脚本
└── state                           #忽略
    └── state.log

11 directories, 28 files
```

##### （3）配置server

```
vim conf/config.ini #根据实际情况进行编辑
```

```
[global]
version       = 1.1   #版本号, 通过这个变量控制server和client的代码，如果server和client版本号不一样client会进行重启，以此达到升级效果
interval_time = 30    #监控采集粒度单位是秒，即30秒一次，这个不是完全精确的30一次
retention_day = 30    #监控数据保留天数，即30天
log_file = /opt/soft/rpc_for_monitor/logs/info.log #日志文件
script_dir = /opt/soft/rpc_for_monitor             #脚本目录，不建议变更
mount_part    = /work  #数据盘挂载点, 也可以不配置，置为空，但是不能删除这个配置项
log_size      = 20     #日志文件大小（MB）限制，超过这个值就会删除历史日志

[RULE] 
cpu = 200    #采集的阈值，200表示某个进程使用cpu大于等于200%才会被采集
mem = 10     #采集的阈值，10表示某个进程使用内存大于等于10GB才会被采集
io  = 10240  #采集的阈值，10240表示某个进程使用io（读写有一个就算）大于等于10MB才会被采集
net = 10240  #采集的阈值，10240表示某个进程使用网络（进出有一个就算）大于等于10MB才会被采集

[CLIENT]
path = /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/root/bin:/root/bin  #预定义一下操作系统的path，因为client会维护一个cront任务，所以避免因为环境变量问题导致脚本执行报错，需要定义一下path
python3 = /usr/local/python3 #python3安装目录
py3env = /opt/soft/rpc_for_monitor/py37env #python3虚拟环境目录，工程自带了一个虚拟环境，可以直接用（前提是脚本目录没有变更）

[MSM]
wx_url  = xxxx   #企业微信报警url，告警功能需要用户自己修改一下并测试（如果是告警机器人url+key，可以直接配上就能用，本例就是通过企业微信机器人发送告警）

[Monitor]  #存放监控数据的MySQL的配置
mysql_host      = xxxx
mysql_port      = xxxx
mysql_user      = xxxx
mysql_pass      = xxxx
省略部分不建议变更的配置
```

> 所有目录不建议修改, 要不然需要变更的地方太多了

#### 2、部署MySQL

> 安装MySQL略，建议的版本：5.7

##### （1）新建必要的账户

> 用MySQL管理员用户登录并操作。

```
create user 'monitor_ro'@'192.%' identified by 'pass1';

grant select on dbzz_monitor.* to 'monitor_ro'@'192.%';

create user 'monitor_rw'@'192.%' identified by 'pass2';

grant select,insert,update,delete on dbzz_monitor.* to 'monitor_rw'@'192.%';
```

> monitor_ro用户给grafana使用, monitor_rw用户是给程序写入监控数据的（server端写数据，client上报给server）。所以注意的是，monitor_ro用户要给grafana机器授权，monitor_rw用户要给所有监控对象授权，这个目的是用来控制当server失联了，第一个发现的client就会向表里写一条告警记录并告警，避免其他client重复操作。

##### （2）初始化MySQL

> 用MySQL管理员用户登录并操作。

```
cd /opt/soft/rpc_for_monitor
mysql < init/init.sql 
```
> 所有表放在dbzz_monitor库下

```
(dba:3306)@[dbzz_monitor]>show tables;
+----------------------------+
| Tables_in_dbzz_monitor     |
+----------------------------+
| tb_monitor_alert_info      |   # 告警表, 触发告警就会在里面写入一条记录, 避免同一时间多次告警。
| tb_monitor_disk_info       |   # 磁盘信息表，多个盘会记录多条记录
| tb_monitor_host_config     |   # client配置表，需要采集监控的机器配置到这里面就行
| tb_monitor_host_info       |   # 系统层面的监控记录到这里面
| tb_monitor_port_net_info   |   # 端口级别的网络监控会记录到这里面
| tb_monitor_process_info    |   # 这里面是记录了进程信息，全局的
| tb_monitor_process_io_info |   # 这里是记录的进程的网络监控数据
+----------------------------+
6 rows in set (0.00 sec)

(dba:3306)@[dbzz_monitor]>
```
> 所有表都有详细的注释，请看表的建表注释。

#### 3、配置client

配置客户端很简单，只需要往MySQL表里面写入一条记录。

```
use dbzz_monitor;
insert into tb_monitor_host_config select 0,'192.168.168.11',1;  #多个机器就写多条记录
```

> 这里有个限制条件，这个client端已经有python3环境，否则可能会报错。

#### 4、部署grafana

安装略。

> grafana版本：8.3.1，建议小版本也要一致。 https://dl.grafana.com/enterprise/release/grafana-enterprise-8.3.1.linux-amd64.tar.gz

这部分涉及到grafana的配置，所有的配置都已经导成json文件，用户直接导入即可。

> 具体的操作如下。

##### （1）新建DataSource

新建一个数据源

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/grafana-data-source-1.png "grafana-data-source-1.png")
![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/grafana-data-source-2.png "grafana-data-source-2.png")

需要选择MySQL数据源

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/grafana-data-source-3.png "grafana-data-source-3.png")

数据源的名称要求写【dba_process_monitor】，如果跟grafana配置不一致可能会有影响。

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/grafana-data-source-4.png "grafana-data-source-4.png")

##### （2）导入json配置

```
$ ll init/grafana.json 
-rw-r--r-- 1 root root 47875 Jun 23 14:28 init/grafana.json
```

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/grafana-data-source-5.png "grafana-data-source-5.png")

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/grafana-data-source-6.png "grafana-data-source-6.png")

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/grafana-data-source-7.png "grafana-data-source-7.png")


> 本配置是在grafana 8.3.1 版本下生成的。需要注意一下版本，不同版本可能不兼容。

#### 5、启动server

将server端的启动脚本配置到crontab中，可以起到守护进程的作用。

```
echo "*/1 * * * * bash /opt/soft/rpc_for_monitor/start_server.sh" >> /var/spool/cron/root
```

> client端不用管，server启动以后会自动去管理client。

配置完成后，等待一分钟查看日志【/opt/soft/rpc_for_monitor/logs/info.log】，可以看到类似下面的日志。

```
[ 2022-06-30 15:13:01 ] [ INFO ] [ V1.1 Listening for '0.0.0.0:9300' ]
[ 2022-06-30 15:13:04 ] [ INFO ] [ 新加监控节点成功 ] [ 192.168.168.11 ]
[ 2022-06-30 15:13:11 ] [ INFO ] [ 监控数据上报成功 ] [ 192.168.168.11 ] 
```
> 端口默认是9300，可以通过修改【/opt/soft/rpc_for_monitor/start_server.sh】这个文件就行变更监听端口。

#### 6、效果图

##### （1）主页面

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/all-info.png "all-info.png")

> 总共有五个ROW，前面五个是机器级别的监控图，process是进程的监控图

##### （2）CPU页面

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/cpu-info.png) "cpu-info.png")

> 整个机器的CPU使用情况。

##### （3）内存页面

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/mem-info.png) "mem-info.png")

> 整个机器的内存使用情况。

##### （4）磁盘页面

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/disk-info.png) "disk-info.png")

> 整个机器的磁盘使用情况，如果没有定义具体的挂载点，会采集所有的挂载点。

##### （5）网络页面

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/net-info.png "net-info.png")

> 整个机器的网络使用情况。

##### （6）进程页面

![输入图片说明](https://github.com/suyestyle/rpc_for_process_monitor/blob/main/img/process-info.png "process-info.png")

> 会看到具体的进程对系统资源的使用情况

### 五、注意事项

- server，client端一定要有python3环境。

- 如果有多个server，在启动server的时候就要指定多个（用逗号隔开），要不然在部署client的时候只会配上单个server，配置多个的好处就是如果第一个宕机/异常，client会上报给其他的server。

- server在运行过程中可以添加client，只需要在【tb_monitor_host_config】表添加istate为1的记录即可。同理，如果下线的话就更新istate为0即可，运行中的istate为2，下线后的istate为-1。

- 该工具有告警功能（如果配置），server挂了（client连续三次都连不上server），会由第一个发现的client记录到MySQL里面，并发送告警，如果client挂了，server会发现并告警（超过两分钟未上报告警数据）。

- 如果需要升级代码，只需要测试好新代码，确认无误后，更新到server的部署脚本目录，然后kill掉server进程即可，等待crontab拉起就行了，client端的代码不用人为进行更新。需要注意，新代码一定要记得修改配置文件的版本号，要不然server端不会发现版本不一致，也就不会下发相关任务去更新client的代码。

- 如果需要修改部署目录请根据实际情况修改【conf/config.ini】【lib/Config.py】，注意这时候自带的虚拟环境将不能使用了。强烈不建议变更目录结构或者目录名。

- 因考虑到MySQL性能问题及grafana渲染性能问题，所以增加了采集阈值功能，所以部分面板的监控数据可能会没有（该时间段的进程没有满足采集阈值的数据）。

### 六、写在最后
本文所有内容仅供参考，因各自环境不同，在使用文中代码时可能碰上未知的问题。<font color='red'>如有线上环境操作需求，请在测试环境充分测试。</font>
