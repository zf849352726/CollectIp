import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import random


class DoubanSpider(scrapy.Spider):
    name = 'douban'
    allowed_domains = ['douban.com']
    
    def __init__(self):
        """初始化配置"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
            'Connection': 'keep-alive',
        }
        
        # 初始化Chrome配置
        self.options = Options()
        self.options.add_argument('--disable-gpu')
        self.options.add_argument(f'user-agent={self.headers["User-Agent"]}')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        # self.options.add_argument('--headless')  # 无头模式，取消注释即可启用
        
        try:
            self.driver_path = ChromeDriverManager().install()
        except ValueError:
            self.driver_path = r'D:\chorme_download\chromedriver-win32\chromedriver.exe'  # 请根据实际路径修改
            
        self.service = Service(self.driver_path)
        
    def start_requests(self):
        """定义起始URL"""
        urls = [
            'https://movie.douban.com/',  # 电影
            # 'https://book.douban.com/',   # 图书
            # 可以添加更多起始URL
        ]
        
        for url in urls:
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                callback=self.parse,
                dont_filter=True
            )
            
    def get_driver(self):
        """获取Chrome驱动实例"""
        driver = webdriver.Chrome(service=self.service, options=self.options)
        return driver
    
    def generate_search_urls(self):
        """生成搜索链接"""
        # 基础搜索URL
        base_url = "https://movie.douban.com/subject_search"
        
        # 搜索参数
        search_params = {
            'search_text': '',  # 搜索关键词
            # 'cat': '1002',  # 电影分类
        }
        
        # 生成电影名称的搜索链接
        search_urls = []
        movie_names = ['肖申克的救赎', '阿甘正传', '泰坦尼克号']  # 示例电影名称列表
        
        for movie in movie_names:
            search_params['search_text'] = movie
            params = urllib.parse.urlencode(search_params)
            search_url = f"{base_url}?{params}"
            search_urls.append(search_url)
            
        return search_urls
    
    def parse(self, response):
        """
        解析页面
        这里是示例解析方法，需要根据具体需求修改
        """
        # 获取搜索链接
        search_urls = self.generate_search_urls()
        
        # 遍历搜索链接获取电影详情页
        for search_url in search_urls:
            driver = self.get_driver()
            try:
                driver.get(search_url)
                # 等待页面加载
                time.sleep(random.uniform(1, 3))
                
                # 等待搜索结果加载
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.item-root'))
                )
                
                # 获取第一个搜索结果的详情页链接
                detail_link = driver.find_element(By.CSS_SELECTOR, '.item-root a').get_attribute('href')
                
                if detail_link:
                    yield scrapy.Request(
                        url=detail_link,
                        headers=self.headers,
                        callback=self.parse_detail,
                        dont_filter=True
                    )
                    
            except Exception as e:
                self.logger.error(f'获取详情页链接失败: {str(e)}')
                
            finally:
                driver.quit()
    
    def parse_detail(self, response):
        """解析电影详情页"""
        # 获取电影标题
        title = response.css('.title-text::text').get()
        # 获取电影评分
        score = response.css('.rating_num::text').get()
        
        # 获取评论页面的URL
        comments_url = response.url + 'comments'
        
        # 生成评论页的分页URL
        comment_urls = []
        for page in range(1, 11):  # 获取前10页评论
            page_url = f"{comments_url}?start={(page-1)*20}&limit=20&status=P&sort=new_score"
            comment_urls.append(page_url)
            
        # 请求每个评论页面
        for url in comment_urls:
            yield scrapy.Request(
                url=url,
                headers=self.headers,
                callback=self.parse_comments,
                dont_filter=True,
                meta={'title': title}  # 传递电影标题信息
            )
    
    def parse_comments(self, response):
        """解析评论页面"""
        # 获取电影标题
        title = response.meta.get('title')
        
        # 获取评论内容  
        comments = response.css('.comment-item .comment-content::text').getall()

           
    def random_sleep(self, min_seconds=1, max_seconds=3):
        """随机延时，防止反爬"""
        time.sleep(random.uniform(min_seconds, max_seconds))
        
    def handle_verification(self, driver):
        """处理可能出现的验证码"""
        try:
            # 检查是否存在验证码
            verify_element = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located((By.ID, 'verify'))
            )
            if verify_element:
                # 这里添加验证码处理逻辑
                pass
                
        except:
            # 没有验证码，继续正常流程
            pass
            
    def closed(self, reason):
        """爬虫关闭时的清理工作"""
        self.logger.info(f'爬虫关闭，原因: {reason}') 