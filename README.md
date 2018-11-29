# elasticsearch-in-scrapy
爬取知乎全网和伯乐在线，配置到elasticsearch做搜索引擎数据支撑

## 项目说明
本项目是在之前的爬虫项目[zhihu_spider](https://github.com/ChrisLee0211/zhihu_spider)和[jobbole_spider](https://github.com/ChrisLee0211/jobbole_spider)的基础上进行重写的
重写的内容有：
- 新增代理IP池，防止IP屏蔽
- 新增user-agent随机切换
- 新增导入elasticsearch逻辑
- 进一步的数据清洗

### 开发环境以及第三方库：
> python 3.6\
scrapy 1.5\
selenium\
chromedriver\
request\
elasticsearch-dsl 5.5.1

传送门：[elasticsearch的py驱动](https://github.com/ChrisLee0211/elasticsearch-dsl-py)
>关于elasticsearch的用法请自行google或百度，它强大的地方在于集群处理以及作为搜索引擎，用作传统数据库的话未必比MongoDB或mysql好

### 注意事项
1. 要使用代理ip池，请先配置好myspider/myspider/tools/下的ip_pool.py文件,配置好后请直接运行该文件，进行IP爬取收集入库。
```python
conn = pymysql.connect(host="localhost", port=3306, user="root", password="123456", db="jobbole", charset="utf8")
#请使用前在mysql中建立对应的表和字段，然后在此处配置好数据库用户密码端口等信息
cursor = conn.cursor()
```

2. 第一步完成以后请在myspider/myspider/tools/random_ip.py下再做同样配置然后保存文件。

3. 同样地，在运行该爬虫进行爬取入elasticsearch之前，请配置/myspider/myspider/models/es_type.py配置好之后请单独运行该文件，让它在es中创建索引。
```python
from elasticsearch_dsl.connections import connections
connections.create_connection(hosts=["localhost"])
#如果是保存到本地的话则无需更改
```

4. 以上步骤确认完成之后，最后需要在elasticsearch-in-scrapy/myspider/myspider/spiders/zhihu.py中，为selenium配置好账号密码：
```python
def start_requests(self):
        from selenium import webdriver
        browser = webdriver.Chrome(executable_path="C:\python flies\myspider\chromedriver.exe")

        browser.get("https://www.zhihu.com/signup?next=%2F")

        browser.find_element_by_xpath("//div[@class='SignContainer-switch']/span").click()
        browser.find_element_by_css_selector(".Login-content input[name='username']").send_keys("xxx")  # 知乎账号
        browser.find_element_by_css_selector(".SignFlow-password input[name='password']").send_keys("xxx")  # 知乎密码
        browser.find_element_by_css_selector(".Login-content button[type='submit']").click()

        import time
        time.sleep(8)  # 等待跳转到首页再取cookies
        import pickle
        cookies = browser.get_cookies()
        cookie_dict = {}
        for cookie in cookies:
            f = open('C:\python flies\myspider\cookies\zhihu' + cookie['name'] + '.zhihu', 'wb')#请将'C:\python flies'修改成自己文件路径
            pickle.dump(cookies, f)  # 将序列化的cookie写入到f中
            f.close()
            cookie_dict[cookie['name']] = cookie['value']
        browser.close()
        return [scrapy.Request(url=self.start_urls[0], cookies=cookie_dict, dont_filter=True, headers=self.headers)]
```

### 建议：
- 不要用pip安装elasticsearch的python版本，因为最新版在doc_type继承上有bug，建议直接先```pip install elasticsearch-dsl==5.5.1```它会自动安装对应的elasticsearch版本
- 请一定要熟悉elasticsearch的用法才使用，不然还是自己配置成入库mysql吧，不需要变动代码，只需要在settings中注释掉```'myspider.pipelines.EsPipeline```就好了，然后恢复mysql的Pipeline
