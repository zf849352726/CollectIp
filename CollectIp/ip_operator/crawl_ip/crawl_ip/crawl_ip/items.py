# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class IpItem(scrapy.Item):
    # define the fields for your item here like:
    # name = scrapy.Field()
    server = scrapy.Field()
    ping = scrapy.Field()
    speed = scrapy.Field()
    uptime1 = scrapy.Field()
    uptime2 = scrapy.Field()
    type_data = scrapy.Field()
    country = scrapy.Field()
    ssl = scrapy.Field()
    conn = scrapy.Field()
    post = scrapy.Field()
    last_work_time = scrapy.Field()


class MovieItem(scrapy.Item):
    """电影数据项"""
    id = scrapy.Field()  # 数据库ID
    title = scrapy.Field()  # 标题
    director = scrapy.Field()  # 导演
    actors = scrapy.Field()  # 演员
    year = scrapy.Field()  # 年份
    rating = scrapy.Field()  # 评分
    rating_count = scrapy.Field()  # 评分人数
    genre = scrapy.Field()  # 类型
    region = scrapy.Field()  # 地区
    duration = scrapy.Field()  # 片长
    poster_url = scrapy.Field()  # 海报URL
    summary = scrapy.Field()  # 剧情简介
    comments = scrapy.Field()  # 评论列表（纯文本）
    comment_details = scrapy.Field()  # 评论详细信息（包含用户、评分、时间等）

