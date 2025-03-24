import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from scrapy.crawler import CrawlerProcess
import time
import random
import urllib.parse
from ..items import MovieItem
import logging

logger = logging.getLogger(__name__)

class DoubanSpider(scrapy.Spider):
    name = 'douban'
    allowed_domains = ['douban.com']
    
    def __init__(self, movie_names=None, *args, **kwargs):
        """初始化配置"""
        super(DoubanSpider, self).__init__(*args, **kwargs)
        
        # 保存电影名称参数
        self.movie_names = movie_names
        logger.info(f"初始化豆瓣爬虫，电影名称: {movie_names}")
        
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
        self.options.add_argument('--headless')  # 使用无头模式
        
        try:
            self.driver_path = ChromeDriverManager().install()
            logger.info(f"ChromeDriver安装成功: {self.driver_path}")
        except ValueError as e:
            self.driver_path = r'D:\chorme_download\chromedriver-win32\chromedriver.exe'
            logger.warning(f"ChromeDriver安装失败，使用备用路径: {self.driver_path}，错误: {str(e)}")
            
        self.service = Service(self.driver_path)
        
    def start_requests(self):
        """定义起始URL并传递电影名称"""
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
                dont_filter=True,
                meta={'movie_names': self.movie_names}  # 传递电影名称参数
            )
            
    def get_driver(self):
        """获取Chrome驱动实例"""
        driver = webdriver.Chrome(service=self.service, options=self.options)
        return driver
    
    def generate_search_urls(self, movie_names=None):
        """生成搜索链接"""
        # 基础搜索URL
        base_url = "https://movie.douban.com/subject_search"
        
        # 如果没有传入电影名称，使用默认值
        if not movie_names:
            movie_names = '肖申克的救赎'  # 默认电影名称
            logger.warning(f"未提供电影名称，使用默认名称: {movie_names}")
            
        # 确保电影名称是字符串
        if isinstance(movie_names, (list, tuple)):
            movie_names = movie_names[0]
            logger.info(f"接收到多个电影名称，使用第一个: {movie_names}")
            
        # 记录日志
        logger.info(f"生成电影搜索链接: {movie_names}")
        
        # 搜索参数
        search_params = {
            'search_text': movie_names,  # 搜索关键词
            'cat': '1002',  # 电影分类
        }
            
        # 生成搜索URL
        params = urllib.parse.urlencode(search_params)
        search_url = f"{base_url}?{params}"
            
        return search_url
    
    def parse(self, response):
        """
        解析页面
        这里是示例解析方法，需要根据具体需求修改
        """
        # 从请求元数据中获取电影名称，如果没有则使用默认值
        movie_names = response.meta.get('movie_names', None)
        
        # 获取搜索链接
        search_url = self.generate_search_urls(movie_names)
        
        # 检查是否使用Selenium
        use_selenium = response.meta.get('use_selenium', False)
        if use_selenium:
            self.logger.info(f"基于标记使用Selenium获取: {search_url}")
            return self.parse_with_selenium(search_url, movie_names)
            
        # 使用普通请求
        yield scrapy.Request(
            url=search_url,
            headers=self.headers,
            callback=self.parse_search_results,
            dont_filter=True,
            meta={'movie_names': movie_names}
        )
        
    def parse_with_selenium(self, url, movie_names):
        """使用Selenium解析页面"""
        driver = None
        try:
            driver = self.get_driver()
            
            # 访问搜索页面
            self.logger.info(f"Selenium访问搜索页面: {url}")
            driver.get(url)
            
            # 等待页面加载
            self.random_sleep(2, 3)
            
            # 处理可能出现的验证码
            self.handle_verification(driver)
            
            # 等待搜索结果加载
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.item-root'))
                )
                
                # 获取第一个搜索结果的详情页链接
                detail_link = driver.find_element(By.CSS_SELECTOR, '.item-root a').get_attribute('href')
                
                if detail_link:
                    # 记录日志
                    self.logger.info(f'找到电影详情页链接: {detail_link}')
                    
                    # 获取详情页的内容
                    return self.parse_detail_with_selenium(detail_link)
                else:
                    self.logger.warning(f'未找到电影 {movie_names} 的详情页链接')
                    
            except Exception as e:
                self.logger.error(f'等待/查找搜索结果失败: {str(e)}')
                
                # 尝试直接使用搜索词进行查询
                if movie_names:
                    try:
                        # 构建详情页搜索链接
                        direct_search_url = f"https://www.douban.com/search?q={movie_names}"
                        self.logger.info(f"尝试直接搜索: {direct_search_url}")
                        
                        # 访问搜索页
                        driver.get(direct_search_url)
                        self.random_sleep(2, 3)
                        
                        # 查找电影搜索结果
                        movie_links = driver.find_elements(By.XPATH, '//div[contains(@class, "result")]//a[contains(@href, "movie.douban.com/subject/")]')
                        
                        if movie_links:
                            first_movie_link = movie_links[0].get_attribute('href')
                            self.logger.info(f'直接搜索找到电影链接: {first_movie_link}')
                            return self.parse_detail_with_selenium(first_movie_link)
                    except Exception as direct_search_err:
                        self.logger.error(f'直接搜索失败: {str(direct_search_err)}')
                
        except Exception as e:
            self.logger.error(f'使用Selenium获取详情页链接失败: {str(e)}')
            import traceback
            self.logger.error(traceback.format_exc())
            
        finally:
            if driver:
                driver.quit()
                
        return None
        
    def parse_search_results(self, response):
        """解析搜索结果页面"""
        try:
            # 直接使用Selenium获取详情页
            return self.parse_with_selenium(response.url, response.meta.get('movie_names'))
                
        except Exception as e:
            self.logger.error(f'解析搜索结果失败: {str(e)}')
            import traceback
            self.logger.error(traceback.format_exc())
            return None
    
    def parse_detail(self, response):
        """解析电影详情页，直接使用Selenium"""
        return self.parse_detail_with_selenium(response.url)
    
    def parse_detail_with_selenium(self, url):
        """使用Selenium解析电影详情页"""
        self.logger.info(f"使用Selenium解析URL: {url}")
        driver = None
        try:
            driver = self.get_driver()
            driver.get(url)
            self.random_sleep(2, 4)
            
            # 处理可能的验证码
            self.handle_verification(driver)
            
            # 尝试获取页面元素
            try:
                title = driver.find_element(By.CSS_SELECTOR, 'h1 span[property="v:itemreviewed"]').text
            except:
                try:
                    title = driver.find_element(By.CSS_SELECTOR, 'h1.title span').text
                except:
                    title = '未知'
            
            # 获取导演
            try:
                director = driver.find_element(By.CSS_SELECTOR, 'a[rel="v:directedBy"]').text
            except:
                try:
                    director = driver.find_element(By.XPATH, '//span[contains(text(), "导演")]/following-sibling::span//a').text
                except:
                    director = '未知'
            
            # 获取主演
            try:
                actors_elements = driver.find_elements(By.CSS_SELECTOR, 'a[rel="v:starring"]')
                actors = ','.join([a.text for a in actors_elements]) if actors_elements else '未知'
            except:
                try:
                    actors_elements = driver.find_elements(By.XPATH, '//span[contains(text(), "主演")]/following-sibling::span//a')
                    actors = ','.join([a.text for a in actors_elements]) if actors_elements else '未知'
                except:
                    actors = '未知'
            
            # 获取年份
            try:
                year_element = driver.find_element(By.CSS_SELECTOR, 'span.year')
                year = year_element.text.strip('()')
            except:
                year = '未知'
            
            # 获取评分
            try:
                rating = driver.find_element(By.CSS_SELECTOR, '.rating_num').text
            except:
                rating = '0'
            
            # 获取评分人数
            try:
                rating_count = driver.find_element(By.CSS_SELECTOR, '.rating_people span').text
            except:
                rating_count = '0'
            
            # 获取类型
            try:
                genre_elements = driver.find_elements(By.CSS_SELECTOR, 'span[property="v:genre"]')
                genre = ','.join([g.text for g in genre_elements]) if genre_elements else '未知'
            except:
                try:
                    genre_elements = driver.find_elements(By.XPATH, '//span[contains(text(), "类型")]/following-sibling::*//text()')
                    genre = ','.join([g for g in genre_elements]) if genre_elements else '未知'
                except:
                    genre = '未知'
            
            # 获取制片国家/地区
            try:
                region_text = driver.find_element(By.XPATH, '//span[contains(text(), "制片国家/地区:")]/following-sibling::text()[1]')
                region = region_text.text.strip()
            except:
                region = '未知'
            
            # 获取片长
            try:
                duration = driver.find_element(By.CSS_SELECTOR, 'span[property="v:runtime"]').text
            except:
                try:
                    duration_element = driver.find_element(By.XPATH, '//span[contains(text(), "片长:")]/following-sibling::text()[1]')
                    duration = duration_element.text.strip()
                except:
                    duration = '未知'
            
            # 创建MovieItem实例
            movie_item = MovieItem()
            movie_item['title'] = title
            movie_item['director'] = director
            movie_item['actors'] = actors
            movie_item['year'] = year
            movie_item['rating'] = rating
            movie_item['rating_count'] = rating_count
            movie_item['genre'] = genre
            movie_item['region'] = region
            movie_item['duration'] = duration
            movie_item['comments'] = []
            
            self.logger.info(f"Selenium获取到电影数据: {title}, {year}, {rating}分")
            
            # 获取评论
            try:
                # 构建评论页URL
                comments_url = url + 'comments'
                
                # 先返回电影信息
                yield movie_item
                
                # 再获取评论
                driver.get(comments_url)
                self.random_sleep(2, 3)
                
                # 获取评论内容
                comment_elements = driver.find_elements(By.CSS_SELECTOR, '.comment-item .comment-content')
                comments = [elem.text for elem in comment_elements if elem.text]
                
                if comments:
                    self.logger.info(f"获取到{len(comments)}条评论")
                    movie_item_with_comments = movie_item.copy()
                    movie_item_with_comments['comments'] = comments
                    yield movie_item_with_comments
                else:
                    self.logger.warning("未找到评论内容")
                    
            except Exception as e:
                self.logger.error(f"获取评论出错: {str(e)}")
                import traceback
                self.logger.error(traceback.format_exc())
                
            return None
            
        except Exception as e:
            self.logger.error(f"Selenium解析电影详情出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return None
            
        finally:
            if driver:
                driver.quit()
    
    def parse_comments(self, response):
        """解析评论页面"""
        try:
            # 获取电影信息
            movie_item = response.meta.get('movie_item').copy()
            
            # 如果是HTML响应，使用CSS选择器
            if isinstance(response, scrapy.http.HtmlResponse):
                # 获取评论内容  
                comments = response.css('.comment-item .comment-content::text').getall()
                
                # 添加到电影评论列表
                if 'comments' not in movie_item:
                    movie_item['comments'] = []
                
                movie_item['comments'].extend(comments)
                self.logger.info(f"获取到{len(comments)}条评论")
            else:
                self.logger.warning("响应不是HTML，无法获取评论")
            
            # 返回带有评论的电影信息
            yield movie_item
            
        except Exception as e:
            self.logger.error(f"解析评论出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
    
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

if __name__ == '__main__':
    movie_names = '肖申克的救赎'
    process = CrawlerProcess()
    process.crawl(DoubanSpider, movie_names=movie_names)
    process.start()

