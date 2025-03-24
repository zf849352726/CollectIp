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
    """豆瓣电影Item"""
    title = scrapy.Field()         # 电影名称
    director = scrapy.Field()      # 导演
    actors = scrapy.Field()        # 主演
    year = scrapy.Field()          # 上映年份
    rating = scrapy.Field()        # 评分
    rating_count = scrapy.Field()  # 评分人数
    genre = scrapy.Field()         # 类型
    region = scrapy.Field()        # 国家/地区
    duration = scrapy.Field()      # 片长
    comments = scrapy.Field()      # 评论内容

