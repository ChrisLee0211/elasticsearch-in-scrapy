__author__ = '10185'
from selenium import webdriver

# browser = webdriver.Chrome(executable_path="C:\python flies\myspider\chromedriver.exe")
#

#
# #selenium通过js代码实现鼠标下拉页面
# import time
# time.sleep(5)
# for i in range(3):
#     browser.execute_script("window.scrollTo(0,document.body.scrollHeight); var lenOfPage=document.body.scrollHeight; return lenOfPage")
#     time.sleep(2)

#设置chromedriver不加载图片
chrome_opt = webdriver.ChromeOptions()
prefs = {"profile.managed_default_content_settings.images":2}
chrome_opt.add_experimental_option('prefs', prefs)
browser = webdriver.Chrome(executable_path="C:\python flies\myspider\chromedriver.exe",chrome_options=chrome_opt)
browser.get("http://python.jobbole.com/86787/")

import time
time.sleep(6)
browser.close()
