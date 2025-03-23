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

