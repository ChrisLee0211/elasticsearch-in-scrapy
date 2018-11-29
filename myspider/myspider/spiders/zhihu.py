# -*- coding: utf-8 -*-
import scrapy
import json
import re
import datetime
from urllib import parse
from scrapy.loader import ItemLoader
from myspider.items import ZhihuAnswerItem, ZhihuQuestionItem, ZhihuQueItemLoader


class ZhihuSpider(scrapy.Spider):
    name = 'zhihu'
    allowed_domains = ['www.zhihu.com']
    start_urls = ['https://www.zhihu.com/']

    headers = {
        "HOST": "www.zhihu.com",
        "Referer": "https://www.zhizhu.com",
        'User-Agent': "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:51.0) Gecko/20100101 Firefox/51.0"
    }

    custom_settings = {
        "COOKIES_ENABLED": True,
    }

    handle_httpstatus_list = [404]

    def __init__(self):
        self.fail_urls = []

    start_answer_url = "https://www.zhihu.com/api/v4/questions/{0}/answers?include=data%5B%2A%5D.is_normal%2Cadmin_closed_comment%2Creward_info%2Cis_collapsed%2Cannotation_action%2Cannotation_detail%2Ccollapse_reason%2Cis_sticky%2Ccollapsed_by%2Csuggest_edit%2Ccomment_count%2Ccan_comment%2Ccontent%2Ceditable_content%2Cvoteup_count%2Creshipment_settings%2Ccomment_permission%2Ccreated_time%2Cupdated_time%2Creview_info%2Crelevant_info%2Cquestion%2Cexcerpt%2Crelationship.is_authorized%2Cis_author%2Cvoting%2Cis_thanked%2Cis_nothelp%3Bdata%5B%2A%5D.mark_infos%5B%2A%5D.url%3Bdata%5B%2A%5D.author.follower_count%2Cbadge%5B%2A%5D.topics&limit={1}&offset={2}&sort_by=default"

    def parse(self, response):
        """
        利用深度爬取策略，先获取首页所有url，然后进一步爬取
        :param response:
        :return:
        """
        if response.status == 200:
            self.fail_urls.append(response.url)
            self.crawler.stats.inc_value("failed_url")
        all_urls = response.css("a::attr(href)").extract()
        all_urls = [parse.urljoin(response.url, url) for url in all_urls]
        for url in all_urls:
            match_obj = re.match("(.*zhihu.com/question/(\d+))(/|$).*", url)  # 匹配出只包含问题的url
            if match_obj:
                # 如果匹配到question的url，就回调到用于question解析的方法
                request_url = match_obj.group(1)
                question_id = match_obj.group(2)
                yield scrapy.Request(request_url, headers=self.headers, callback=self.parse_question)
            else:
                # 如果不是question页面，继续返回爬取
                yield scrapy.Request(url, headers=self.headers, callback=self.parse)

    def parse_question(self, response):
        """
        处理question解析
        :param response:
        :return:
        """
        match_obj = re.match('(.*zhihu.com/question/(\d+))(/|$).*', response.url)
        if match_obj:
            question_id = int(match_obj.group(2))
        item_loader = ZhihuQueItemLoader(item=ZhihuQuestionItem(), response=response)
        item_loader.add_css("title", ".QuestionHeader-title::text")
        item_loader.add_css("content", ".QuestionHeader-detail")
        item_loader.add_value("url", response.url)
        item_loader.add_value("zhihu_id", question_id)
        item_loader.add_css("answer_num", ".List-headerText span::text")
        item_loader.add_css("comments_num", ".QuestionHeader-Comment button::text")
        item_loader.add_css("watch_user_num", ".Button.NumberBoard-item .NumberBoard-itemValue::text")
        # item_loader.add_css("topics",".QuestionHeader-topics .Popover div::text")
        item_loader.add_xpath("topics", "//div[@class='QuestionPage']/meta[@itemprop='keywords']/@content")
        item_loader.add_xpath("click_num", "//div[@class='NumberBoard-item']/div/strong/text()")

        question_item = item_loader.load_item()
        yield scrapy.Request(url=self.start_answer_url.format(question_id, 20, 0), headers=self.headers,
                             callback=self.parse_answer)
        yield question_item

    def parse_answer(self, response):
        """
        通过api形式解析answer，先把得到的json数据读取
        :return:
        """
        ans_json = json.loads(response.text)
        is_end = ans_json["paging"]["is_end"]
        next_url = ans_json["paging"]["next"]
        totals = ans_json["paging"]["totals"]

        for answer in ans_json["data"]:
            answer_item = ZhihuAnswerItem()
            answer_item["zhihu_id"] = answer["id"]
            answer_item["url"] = answer["url"]
            answer_item["question_id"] = answer["question"]["id"]
            answer_item["author_id"] = answer["author"]["id"] if "id" in answer["author"] else None
            # 考虑到匿名回答是没有id，所以做判断
            answer_item["content"] = answer["content"]
            answer_item["praise_num"] = answer["voteup_count"]
            answer_item["comments_num"] = answer["comment_count"]
            answer_item["update_time"] = answer["updated_time"]
            answer_item["create_time"] = answer["created_time"]
            answer_item["crawl_time"] = datetime.datetime.now()

            yield answer_item
        if not is_end:
            yield scrapy.Request(url=next_url, headers=self.headers, callback=self.parse_answer)

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
            f = open('C:\python flies\myspider\cookies\zhihu' + cookie['name'] + '.zhihu', 'wb')
            pickle.dump(cookies, f)  # 将序列化的cookie写入到f中
            f.close()
            cookie_dict[cookie['name']] = cookie['value']
        browser.close()
        return [scrapy.Request(url=self.start_urls[0], cookies=cookie_dict, dont_filter=True, headers=self.headers)]
