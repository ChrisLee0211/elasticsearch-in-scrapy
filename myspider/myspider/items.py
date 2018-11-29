# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/items.html
import datetime
import scrapy
import re

from scrapy.loader import ItemLoader
from scrapy.loader.processors import MapCompose, Join, TakeFirst
from w3lib.html import remove_tags

from elasticsearch_dsl.connections import connections

from myspider.myspider.utils.common import extract_num
from myspider.myspider.settings import SQL_DTAETIME_FORMAT, SQL_DATE_FORMAT
from myspider.myspider.models.es_type import JobboleEsType, ZhihuQuestionEsType, ZhihuAnwserEsType

es = connections.create_connection(JobboleEsType._doc_type.using) #初始化一个es的连接


class MyspiderItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    pass


class ArticleItemLoader(ItemLoader):
    default_output_processor = TakeFirst()


class ZhihuQueItemLoader(ItemLoader):
    default_output_processor = TakeFirst()


def date_convert(value):
    """
    时间格式转换
    :param value: 抓取的日期数据
    :return:
    """
    try:
        create_date = datetime.datetime.strptime(value, "%Y/%m/%d").date()
    except Exception as e:
        create_date = datetime.datetime.now().date()
        create_date = str(create_date)
    return create_date


def get_nums(value):
    """
    提取整数
    :param value: 抓取的数字+汉子
    :return:
    """
    match_re = re.match(".*?(\d+).*", value)
    if match_re:
        nums = int(match_re.group(1))
    else:
        nums = 0
    return nums


def return_value(value):
    return value


def suggest_word(index, info_tuple):
    """
    配置分词，为elasticsearch形成搜索建议数组
    :param index: 索引名称
    :param info_tuple: 自定义分词
    :return:
    """
    used_word = set()
    suggest = []
    for key, weight in info_tuple:
        if key:
            # 如果存在词组，那么就调用analyzer去拆分,得到词组result，但同时也要进行去重，防止多个字段有重复词组导致混乱
            result = es.indices.analyze(index=index, analyzer="ik_max_word", params={'filter': ['lowercase']}, body=key)
            words = set([r['token'] for r in result['tokens'] if len(r['token']) > 1])
            new_words = words - used_word
            used_word.update(words)
        else:
            new_words = set()
        if new_words:
            suggest.append({'input': list(new_words), 'weight': weight})
        return suggest


class JobBoleArticleItem(scrapy.Item):
    # 文章标题
    title = scrapy.Field()
    create_date = scrapy.Field(
        input_processor=MapCompose(date_convert),
    )  # 发布日期
    url = scrapy.Field()  # 地址
    url_object_id = scrapy.Field()
    front_image_url = scrapy.Field(
        output_processor=MapCompose(return_value)
    )  # 封面图地址
    front_image_path = scrapy.Field()  # 存放路径
    praise_nums = scrapy.Field(
        input_processor=MapCompose(get_nums)
    )  # 点赞数
    comment_nums = scrapy.Field(
        input_processor=MapCompose(get_nums)
    )  # 评论数
    fav_nums = scrapy.Field(
        input_processor=MapCompose(get_nums)
    )  # 收藏数
    content = scrapy.Field()
    tag = scrapy.Field(
        output_processor=Join(",")
    )

    def get_insert_sql(self):
        insert_sql = """
            insert into article(title, url, url_object_id, create_date, fav_nums)
            VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE fav_nums=VALUES(fav_nums)
        """
        params = (self["title"], self["url"], self["url_object_id"], self["create_date"], self["fav_nums"])

        return insert_sql, params

    def get_es(self):
        article = JobboleEsType()
        article.title = self["title"]
        article.create_date = self["create_date"]
        article.url = self["url"]
        article.meta.id = self["url_object_id"]
        article.front_image_url = self["front_image_url"]
        if "front_image_path" in self:
            article.front_image_path = self["front_image_path"]
        article.praise_nums = self["praise_nums"]
        article.comment_nums = self["comment_nums"]
        article.fav_nums = self["fav_nums"]
        if self["content"]:
            self["content"].strip().replace("\r", "").replace("\n", "").replace(" ", "")
        article.content = remove_tags(self["content"])
        article.tag = self["tag"]
        article.suggest = suggest_word(index=JobboleEsType._doc_type.index,
                                       info_tuple=((article.title, 10), (article.tag, 7)))
        article.save()
        return


class ZhihuQuestionItem(scrapy.Item):
    # 知乎问题item
    zhihu_id = scrapy.Field()
    topics = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    answer_num = scrapy.Field(
        input_processor=MapCompose(get_nums)
    )
    comments_num = scrapy.Field(
        input_processor=MapCompose(get_nums)
    )
    watch_user_num = scrapy.Field(
        input_processor=MapCompose(get_nums)
    )
    click_num = scrapy.Field(
        input_processor=MapCompose(get_nums)
    )
    crawl_time = scrapy.Field()

    def get_insert_sql(self):
        insert_sql = """
            insert into zhihu_question(
            zhihu_id, topics, url, title, content, answer_num, comments_num, watch_user_num, click_num, crawl_time
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE title=VALUES(title),
            content=VALUES(content), answer_num=VALUES(answer_num), comments_num=VALUES(comments_num),
            watch_user_num=VALUES(watch_user_num), click_num=VALUES(click_num)
        """
        zhihu_id = self["zhihu_id"][0]
        topics = "".join(self["topics"])
        url = "".join(self["url"])
        title = "".join(self["title"])
        content = "".join(self["content"])
        answer_num = extract_num("".join(self["answer_num"]))
        comments_num = extract_num("".join(self["comments_num"]))
        watch_user_num = extract_num("".join(self["watch_user_num"]))
        click_num = extract_num("".join(self["click_num"]))
        crawl_time = datetime.datetime.now().strftime(SQL_DTAETIME_FORMAT)  # 将datetime类型转换为str

        params = (
            zhihu_id, topics, url, title, content, answer_num, comments_num, watch_user_num, click_num, crawl_time)

        return insert_sql, params

    def get_es(self):
        ZhihuQue = ZhihuQuestionEsType()
        ZhihuQue.zhihu_id = self["zhihu_id"]
        ZhihuQue.topics = self["topics"]
        ZhihuQue.url = self["url"]
        ZhihuQue.title = self["title"]
        ZhihuQue.answer_num = self["answer_num"]
        ZhihuQue.comments_num = self["comments_num"]
        ZhihuQue.watch_user_num = self["watch_user_num"]
        ZhihuQue.content = remove_tags(self["content"])
        ZhihuQue.click_num = self["click_num"]
        ZhihuQue.crawl_time = datetime.datetime.now().strftime(SQL_DATE_FORMAT)
        ZhihuQue.suggest = suggest_word(index=ZhihuQuestionEsType._doc_type.index,
                                       info_tuple=((ZhihuQue.title, 10), (ZhihuQue.content, 7), (ZhihuQue.topics, 5)))

        ZhihuQue.save()
        return


class ZhihuAnswerItem(scrapy.Item):
    # 知乎问题回答
    zhihu_id = scrapy.Field()
    url = scrapy.Field()
    question_id = scrapy.Field()
    author_id = scrapy.Field()
    content = scrapy.Field()
    praise_num = scrapy.Field()
    comments_num = scrapy.Field()
    create_time = scrapy.Field()
    update_time = scrapy.Field()
    crawl_time = scrapy.Field()

    def get_insert_sql(self):
        """
        备注：插入mysql语句加上on duplicate key xxx条件，因为每次爬取同一个问题的答案是有可能更新的，但id一定冲突，那就只更新变动的内容
        """
        insert_sql = """
            insert into zhihu_answer(
            zhihu_id, url, question_id, author_id, content, praise_num, comments_num, create_time, update_time, crawl_time
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE content=VALUES(content), praise_num=VALUES(praise_num),
            comments_num=VALUES(comments_num), update_time=VALUES(update_time)
        """

        create_time = datetime.datetime.fromtimestamp(self["create_time"]).strftime(SQL_DTAETIME_FORMAT)
        update_time = datetime.datetime.fromtimestamp(self["update_time"]).strftime(SQL_DTAETIME_FORMAT)

        params = (
            self["zhihu_id"], self["url"], self["question_id"], self["author_id"], self["content"], self["praise_num"],
            self["comments_num"], create_time, update_time, self["crawl_time"].strftime(SQL_DTAETIME_FORMAT)
        )

        return insert_sql, params

    def get_es(self):
        """
        """
        ZhihuAns = ZhihuAnwserEsType()
        ZhihuAns.zhihu_id = self["zhihu_id"]
        ZhihuAns.url = self["url"]
        ZhihuAns.question_id = self["question_id"]
        ZhihuAns.author_id = self["author_id"]
        ZhihuAns.praise_num = self["praise_num"]
        ZhihuAns.comments_num = self["comments_num"]
        ZhihuAns.content = remove_tags(self["content"])
        ZhihuAns.create_time = datetime.datetime.fromtimestamp(self["create_time"]).strftime(SQL_DTAETIME_FORMAT)
        ZhihuAns.update_time = update_time = datetime.datetime.fromtimestamp(self["update_time"]).strftime(
            SQL_DTAETIME_FORMAT)
        ZhihuAns.crawl_time = datetime.datetime.now().strftime(SQL_DATE_FORMAT)

        ZhihuAns.save()
        return

