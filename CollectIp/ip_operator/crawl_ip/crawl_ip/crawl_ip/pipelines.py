# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter

# 在 Scrapy 项目的 pipelines.py 中添加：
from index.models import IpData  # 替换为你的 Django 应用和模型
from scrapy.exceptions import DropItem
from asgiref.sync import sync_to_async
from decimal import Decimal


class SaveIpPipeline:

    async def process_item(self, item, spider):
        # item有字段： server、ping......
        # 检查并替换值为‘？’的字段
        for field in item:
            if item[field] == '?':
                item[field] = ''

        # 检查并设置默认值
        if not item.get('speed') or item['speed'] == '':
            item['speed'] = '0.0'  # 设置默认值为 0.0

        # 确保将字段值转换为 Decimal
        item['speed'] = Decimal(item['speed'])   # 检查并设置默认值

        # 检查并设置默认值
        if not item.get('ping') or item['ping'] == '':
            item['ping'] = '0.0'  # 设置默认值为 0.0

        # 确保将字段值转换为 Decimal
        item['ping'] = Decimal(item['ping'])   # 检查并设置默认值

        await sync_to_async(self.save_or_update_ip)(item)
        return item

    def save_or_update_ip(self, item):
        # 检查数据库中是否已经存在相同的 server 条目
        try:
            ip = IpData.objects.get(server=item.get('server'))
            # 更新现有条目
            ip.ping = item.get('ping')
            ip.speed = item.get('speed')
            ip.uptime1 = item.get('uptime1')
            ip.uptime2 = item.get('uptime2')
            ip.type_data = item.get('type_data')
            ip.country = item.get('country')
            ip.ssl = item.get('ssl')
            ip.conn = item.get('conn')
            ip.post = item.get('post')
            ip.last_work_time = item.get('last_work_time')
            ip.save()
        except IpData.DoesNotExist:
            # 如果条目不存在，则创建新条目
            ip = IpData(
                server=item.get('server'),
                ping=item.get('ping'),
                speed=item.get('speed'),
                uptime1=item.get('uptime1'),
                uptime2=item.get('uptime2'),
                type_data=item.get('type_data'),
                country=item.get('country'),
                ssl=item.get('ssl'),
                conn=item.get('conn'),
                post=item.get('post'),
                last_work_time=item.get('last_work_time'),
            )
            ip.save()