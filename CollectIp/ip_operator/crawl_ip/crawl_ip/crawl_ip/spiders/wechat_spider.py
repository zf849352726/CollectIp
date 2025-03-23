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
import json
from datetime import datetime

class WechatArticleSpider(scrapy.Spider):
    name = 'wechat_articles'
    allowed_domains = ['mp.weixin.qq.com']
    start_urls = ['https://mp.weixin.qq.com/']
    
    def __init__(self):
        """初始化配置"""
        self.options = Options()
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        # self.options.add_argument('--headless')  # 无头模式，建议调试时注释掉
        
        # 添加实验性选项
        self.options.add_experimental_option('excludeSwitches', ['enable-automation'])
        self.options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver_path = ChromeDriverManager().install()
        except ValueError:
            self.driver_path = r'D:\chorme_download\chromedriver-win32\chromedriver.exe'
            
        self.service = Service(self.driver_path)
        
    def start_requests(self):
        """开始请求"""
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse, dont_filter=True)
    
    def get_driver(self):
        """获取Chrome驱动实例"""
        driver = webdriver.Chrome(service=self.service, options=self.options)
        # 执行CDP命令来禁用webdriver检测
        driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': '''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            '''
        })
        return driver
    
    def parse(self, response):
        """解析页面"""
        driver = self.get_driver()
        try:
            # 访问登录页面
            driver.get(response.url)
            # self.logger.info("等待扫码登录...")
            
            # 通过API获取access_token
            appid = "你的APPID" 
            secret = "你的SECRET"
            url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={appid}&secret={secret}"
            
            response = requests.get(url)
            access_token = response.json().get("access_token")
            
            if not access_token:
                self.logger.error("获取access_token失败")
                return
                
            # 使用token设置cookie实现自动登录
            cookie = {
                "access_token": access_token
            }
            for k, v in cookie.items():
                driver.add_cookie({"name": k, "value": v})
                
            # 刷新页面使cookie生效
            driver.refresh()
            
            # 等待登录成功
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.weui-desktop-account__nickname'))
            )
            self.logger.info("登录成功！")
            
            # 等待页面加载
            time.sleep(3)
            
            # 进入图文消息管理页面
            driver.get('https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_list')
            time.sleep(2)
            
            # 开始获取文章列表
            page = 0
            articles = []
            
            while True:
                # 等待文章列表加载
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.weui-desktop-mass-media__list'))
                )
                
                # 获取当前页的所有文章
                article_elements = driver.find_elements(By.CSS_SELECTOR, '.weui-desktop-mass-media__list .weui-desktop-mass-media__item')
                
                if not article_elements:
                    break
                    
                for article in article_elements:
                    try:
                        # 获取文章信息
                        title = article.find_element(By.CSS_SELECTOR, '.weui-desktop-mass-media__title').text
                        date = article.find_element(By.CSS_SELECTOR, '.weui-desktop-mass-media__time').text
                        link = article.find_element(By.CSS_SELECTOR, '.weui-desktop-mass-media__title').get_attribute('href')
                        status = article.find_element(By.CSS_SELECTOR, '.weui-desktop-mass-media__status').text
                        
                        article_data = {
                            'title': title,
                            'publish_date': date,
                            'url': link,
                            'status': status,
                            'crawl_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        
                        articles.append(article_data)
                        yield article_data
                        
                    except Exception as e:
                        self.logger.error(f"提取文章信息错误: {str(e)}")
                
                # 随机延时
                time.sleep(random.uniform(2, 4))
                
                # 尝试点击下一页
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, '.weui-desktop-pagination__next:not(.weui-desktop-pagination__next--disabled)')
                    next_button.click()
                    page += 1
                    self.logger.info(f"正在获取第 {page + 1} 页")
                except:
                    self.logger.info("已到达最后一页")
                    break
            
            # 保存所有文章信息到JSON文件
            self.save_articles(articles)
            
        except Exception as e:
            self.logger.error(f"爬取错误: {str(e)}")
            
        finally:
            driver.quit()
    
    def save_articles(self, articles):
        """保存文章信息到JSON文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'wechat_articles_{timestamp}.json'
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(articles, f, ensure_ascii=False, indent=2)
            self.logger.info(f"文章信息已保存到: {filename}")
        except Exception as e:
            self.logger.error(f"保存文件失败: {str(e)}")
    
    def random_sleep(self, min_seconds=2, max_seconds=5):
        """随机延时"""
        time.sleep(random.uniform(min_seconds, max_seconds)) 