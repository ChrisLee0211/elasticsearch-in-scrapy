__author__ = '10185'
import pymysql
import requests

conn = pymysql.connect(host="localhost", port=3306, user="root", password="123456", db="jobbole", charset="utf8")
cursor = conn.cursor()

class GetIp(object):
    def delete_ip(self, ip):
        sql = """
        DELETE FROM ip_pool WHERE ip='{0}'
        """.format(ip)
        cursor.execute(sql)
        conn.commit()
        return True

    def judge_ip(self, ip, port):
        # 利用对百度发起请求验证ip是否可用，返回200即可用
        judge_url = "http://www.baidu.com"
        proxy_url = "http://{0}:{1}".format(ip, port)
        try:
            proxy_dict = {
                "http": proxy_url,
            }
            response = requests.get(judge_url, proxies=proxy_dict)
        except Exception as e:
            print("invalid ip")
            self.delete_ip(ip)
            return False
        else:
            code = response.status_code
            if code >= 200 and code < 300:
                print("it work")
                return True
            else:
                print("invalid ip")
                self.delete_ip(ip)
                return False

    def get_ip(self):
        sql = """
        SELECT ip, port FROM ip_pool ORDER BY RAND() LIMIT 1
        """
        result = cursor.execute(sql)
        for ip_info in cursor.fetchall():
            ip = ip_info[0]
            port = ip_info[1]
            judge = self.judge_ip(ip, port)
            if judge:
                return "http://{0}:{1}".format(ip, port)
            else:
                return self.get_ip()

if __name__ == "__main__":
    get_ip = GetIp()
    get_ip.get_ip()