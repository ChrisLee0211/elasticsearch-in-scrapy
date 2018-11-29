# -*- coding: utf-8 -*-
__author__ = '10185'

import requests
import pymysql
from scrapy.selector import Selector

conn = pymysql.connect(host="localhost", port=3306, user="root", password="123456", db="jobbole", charset="utf8")
#请使用前在mysql中建立对应的表和字段，然后在此处配置好数据库用户密码端口等信息
cursor = conn.cursor()


def crawl_ip():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0"}
    for i in range(3483):
        re = requests.get("http://www.xicidaili.com/nn/{0}".format(i), headers=headers)

        selector = Selector(text=re.text)
        all_trs = selector.css("#ip_list tr")

        ip_list = []
        for tr in all_trs[1:]:
            speed_str = tr.css(".bar::attr(title)").extract()[0]
            all_text = tr.css("td::text").extract()
            if speed_str:
                speed = float(speed_str.split("秒")[0])
            ip = all_text[0]
            port = all_text[1]
            proxy_type = all_text[5]
            ip_list.append((ip, port, proxy_type, speed))

        for ip_info in ip_list:
            cursor.execute(
                """
                insert ip_pool(ip,port,speed,proxy_type)
                VALUE ('{0}','{1}','{2}','HTTP') ON DUPLICATE KEY UPDATE ip=VALUES(ip),port=VALUES(port)
                """.format(
                    ip_info[0], ip_info[1], ip_info[3]
                )
            )
            conn.commit()


crawl_ip()
