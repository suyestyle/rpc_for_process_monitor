#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author      : moshan
# Mail        : mo_shan@yeah.net
# Version     : 1.0
# Created Time: 2021-08-12 09:40:43
# Function    : mysql连接函数
#########################################################################
import pymysql
from lib.Public import f_write_log
from lib.Config import *

def f_connect_mysql(): #建立连接
    """
    建立连接
    """
    state = 0

    try :

        db = pymysql.connect(monitor_host, monitor_user, monitor_pass, monitor_db, monitor_port, read_timeout = 2, write_timeout = 5) #连接mysql

    except Exception as e :

        f_write_log(log_opt = "ERROR", log = "[ 建立连接失败 ] [ " + str(e) + " ]", log_file = log_file)

        db =  None

    return  db

def f_test_connection(db):
    """
    测试连接
    """
    try:

        db.ping()

    except:

        f_connect_mysql()

    return db

def f_close_connection(db):
    """
    关闭连接
    """
    try:

        db.close()

    except:

        db = None

    return db

def f_query_mysql(db, opt, sql): #opt区分操作类型, 查询还是写入, sql是一个json串
    """
    查询函数
    """

    db = f_test_connection(db)

    state = 0

    data = []

    try :

        cursor = db.cursor()

    except Exception as e :

        f_write_log(log_opt = "ERROR", log = "[ 连接失败 ] [ " + str(e) + " ]", log_file = log_file)

        return 2, data, db  #连接失败直接返回状态码 2

    if opt == "select" : #如果是select就执行查询操作

        try :

            cursor.execute(sql["sql"])

            data = cursor.fetchall()

            if len(data) == 0 : #结果为空, 状态码为 1

                state = 1

            elif len(data[0]) == 0 : #结果为空, 状态码为 1

                state = 1

            elif data[0][0] is None : #结果为空, 状态码为 1

                state = 1

            else : #有结果, 状态码为 0

                state = 0

        except Exception as e : #查询失败状态码 2

            f_write_log(log_opt = "ERROR", log = "[ 查询失败 ] [ " + str(e) + " ]", log_file = log_file)

            state = 2

    else : #写入操作

        try :

            for key,sql_tmp in sql.items() : #insert update可能是多条sql, 所以遍历json串即可

                cursor.execute(sql_tmp)

            db.commit() #都执行失败再提交, 避免数据不一致

            state = 0

        except Exception as e : #执行失败返回状态码 2

            f_write_log(log_opt = "ERROR", log = "[ 写入失败 ] [ " + str(e) + " ] [ " + "\n".join(sql.values()) + "  ] ", log_file = log_file)

            state = 2

            db.rollback() #都执行失败再提交, 避免数据不一致

    return state, data, db #返回状态码跟data, data是一个列表
