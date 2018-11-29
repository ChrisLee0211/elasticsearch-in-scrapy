# -*- coding: utf-8 -*-
import re
import scrapy
import datetime
from scrapy.http import Request
from scrapy.loader import ItemLoader
from scrapy.xlib.pydispatch import dispatcher  # 信号分发器
from scrapy import signals  # 信号
from urllib import parse
from myspider.myspider.items import JobBoleArticleItem, ArticleItemLoader
from myspider.myspider.utils.common import get_md5
from selenium import webdriver


class JobboleSpider(scrapy.Spider):
    name = 'jobbole'
    allowed_domains = ['python.jobbole.com']
    start_urls = ['http://python.jobbole.com/all-posts/']


    def parse(self, response):
        """
        1、获取文章列表的所有文章url并交给scrapy解析
        2、获取当前页的下一页
        """
        # 获取当前页的每一篇文章url
        post_nodes = response.css("#archive .floated-thumb .post-thumb a")
        for post_node in post_nodes:
            # 用parse.urljoin做一个地址拼接，因为大部分网站的href地址很可能不是绝对路径，有可能是相对路径，因此把主页和每一页的路径拼接最保险
            image_url = post_node.css("img::attr(src)").extract_first("")
            post_url = post_node.css("::attr(href)").extract_first("")
            yield Request(url=parse.urljoin(response.url, post_url), meta={'front_image_url': image_url},
                          callback=self.parse_detail)
        # 获取下一页的url
        next_url = response.css(".next.page-numbers::attr(href)").extract_first("")
        if next_url:
            yield Request(url=parse.urljoin(response.url, next_url), callback=self.parse)

    def parse_detail(self, response):
        article_item = JobBoleArticleItem()


        # itemloader加载item
        front_image_url = response.meta.get("front_image_url", "")
        item_loader = ArticleItemLoader(item=JobBoleArticleItem(), response=response)
        item_loader.add_xpath('title', "//div[@class='entry-header']/h1/text()")
        item_loader.add_value("url", response.url)
        item_loader.add_value("url_object_id", get_md5(response.url))
        item_loader.add_css("create_date", "p.entry-meta-hide-on-mobile::text")
        item_loader.add_value("front_image_url", [front_image_url])
        item_loader.add_css("praise_nums", ".vote-post-up h10::text")
        item_loader.add_css("comment_nums", "a[href='#article-comment'] span::text")
        item_loader.add_css("fav_nums", ".bookmark-btn::text")
        item_loader.add_xpath("tag", "//p[@class='entry-meta-hide-on-mobile']/a/text()")
        item_loader.add_xpath("content", "//div[@class='entry']")

        article_item = item_loader.load_item()

        yield article_item
