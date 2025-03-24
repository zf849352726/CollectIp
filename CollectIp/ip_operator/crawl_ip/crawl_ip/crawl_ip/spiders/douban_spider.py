import os
import sys
import logging
import time
import random
import scrapy
import traceback
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from scrapy.crawler import CrawlerProcess
import urllib.parse

# 获取项目根目录
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# 引入自定义日志设置
try:
    from ip_operator.services.crawler import setup_logging
    # 设置日志级别为WARNING以减少输出
    logger = setup_logging("douban_spider", logging.WARNING)
except ImportError:
    # 如果无法导入，使用基本日志设置
    logger = logging.getLogger("douban_spider")
    logger.setLevel(logging.WARNING)  # 提高日志级别，减少输出
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')  # 简化日志格式
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# 导入Django设置和模型
try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CollectIp.settings')
    django.setup()
except Exception as e:
    logger.error(f"Django设置失败: {e}")

# 导入项目项
try:
    from crawl_ip.items import MovieItem
except ImportError:
    try:
        from ip_operator.crawl_ip.crawl_ip.crawl_ip.items import MovieItem
    except ImportError:
        logger.error("无法导入MovieItem")

# 设置Selenium的日志级别
selenium_logger = logging.getLogger('selenium')
selenium_logger.setLevel(logging.ERROR)  # 仅记录错误

# 设置urllib3的日志级别
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.ERROR)  # 仅记录错误

class DoubanSpider(scrapy.Spider):
    name = 'douban'
    allowed_domains = ['douban.com']
    
    def __init__(self, movie_names=None, *args, **kwargs):
        """初始化爬虫"""
        super(DoubanSpider, self).__init__(*args, **kwargs)
        
        # 从环境变量中获取电影名，优先级高于参数
        env_movie_name = os.environ.get('MOVIE_NAME')
        if env_movie_name:
            self.movie_names = [env_movie_name]
        elif movie_names:
            if isinstance(movie_names, str):
                self.movie_names = [movie_names]
            else:
                self.movie_names = movie_names
        else:
            self.movie_names = ['肖申克的救赎']  # 默认电影
            
        # 记录电影名
        logger.warning(f"豆瓣爬虫爬取电影: {self.movie_names}")
        
        # 设置ChromeDriver路径
        try:
            self.driver_path = ChromeDriverManager().install()
            # 只在DEBUG模式记录详细信息
            if logger.level <= logging.DEBUG:
                logger.debug(f"ChromeDriver安装路径: {self.driver_path}")
        except Exception as e:
            logger.error(f"ChromeDriver安装失败: {e}")
            self.driver_path = None
            
        # 初始化driver为None
        self.driver = None
        
        # 设置每个电影抓取的评论数量
        self.comments_per_movie = 50
        
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
        if self.driver_path:
            self.driver = webdriver.Chrome(service=Service(self.driver_path), options=self.options)
            return self.driver
        else:
            logger.error("无法获取有效的Chrome驱动")
            return None
    
    def generate_search_urls(self, movie_names=None):
        """生成电影搜索URL列表"""
        if movie_names is None:
            movie_names = self.movie_names
            
        # 如果有多个电影名，只使用第一个
        if isinstance(movie_names, list) and len(movie_names) > 1:
            # 只在DEBUG模式记录详细信息
            if logger.level <= logging.DEBUG:
                logger.debug(f"处理多个电影名，使用第一个: {movie_names[0]}")
            movie_names = movie_names[0]
        elif isinstance(movie_names, list):
            movie_names = movie_names[0]
            
        # 生成搜索URL
        search_url = f"https://search.douban.com/movie/subject_search?search_text={urllib.parse.quote(movie_names)}"
        logger.warning(f"搜索电影: {movie_names}")
        
        return [search_url]
    
    def parse(self, response):
        """根据请求元数据决定使用哪个解析器"""
        # 检查是否需要使用Selenium
        use_selenium = response.meta.get('use_selenium', False)
        movie_names = response.meta.get('movie_names', self.movie_names)
        
        if use_selenium:
            # 删除不必要的日志
            url = response.url
            yield from self.parse_with_selenium(url, movie_names)
        else:
            # 常规解析
            yield from self.parse_search_results(response)
        
    def parse_with_selenium(self, url, movie_names):
        """使用Selenium解析搜索结果页"""
        # 获取WebDriver
        driver = self.get_driver()
        if not driver:
            logger.error("无法获取WebDriver")
            return
            
        try:
            # 访问搜索页面
            logger.warning(f"访问搜索页面: {url}")
            driver.get(url)
            self.random_sleep()
            
            # 处理验证码或其他异常
            self.handle_verification(driver)
            
            # 尝试找到第一个电影结果
            try:
                # 等待搜索结果加载
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".item-root"))
                )
                
                # 查找第一个电影结果的链接
                movie_links = driver.find_elements(By.CSS_SELECTOR, ".item-root a")
                if movie_links:
                    # 找到第一个包含'subject'的链接，这通常是电影详情页
                    detail_link = None
                    for link in movie_links:
                        href = link.get_attribute('href')
                        if 'subject' in href:
                            detail_link = href
                            break
                            
                    if detail_link:
                        logger.warning(f'找到电影详情页: {detail_link}')
                        
                        # 解析详情页
                        yield from self.parse_detail_with_selenium(detail_link)
                        return
            except Exception as e:
                logger.error(f"查找电影链接出错: {e}")
                
            # 如果没有找到结果，尝试直接在豆瓣主站搜索
            try:
                direct_search_url = f"https://www.douban.com/search?q={urllib.parse.quote(movie_names)}"
                logger.warning(f"尝试直接搜索: {direct_search_url}")
                driver.get(direct_search_url)
                self.random_sleep()
                
                # 处理验证码
                self.handle_verification(driver)
                
                # 查找第一个电影结果
                movie_elements = driver.find_elements(By.CSS_SELECTOR, ".result h3 a")
                first_movie_link = None
                for element in movie_elements:
                    href = element.get_attribute('href')
                    if 'subject' in href and '/movie/' in href:
                        first_movie_link = href
                        break
                        
                if first_movie_link:
                    logger.warning(f'找到电影链接: {first_movie_link}')
                    yield from self.parse_detail_with_selenium(first_movie_link)
                    
            except Exception as e:
                logger.error(f"直接搜索出错: {e}")
                
        except Exception as e:
            logger.error(f"Selenium解析出错: {e}")
            
        finally:
            # 不用每次都关闭，让爬虫结束时统一关闭
            pass
    
    def parse_search_results(self, response):
        """解析搜索结果页面"""
        try:
            # 直接使用Selenium获取详情页
            return self.parse_with_selenium(response.url, response.meta.get('movie_names'))
                
        except Exception as e:
            logger.error(f'解析搜索结果失败: {str(e)}')
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def parse_detail(self, response):
        """解析电影详情页，直接使用Selenium"""
        return self.parse_detail_with_selenium(response.url)
    
    def parse_detail_with_selenium(self, url):
        """使用Selenium解析电影详情页"""
        logger.warning(f"解析电影详情页: {url}")
        
        # 获取WebDriver
        driver = self.get_driver()
        if not driver:
            logger.error("无法获取WebDriver")
            return
            
        try:
            # 访问详情页
            driver.get(url)
            self.random_sleep()
            
            # 处理验证码
            self.handle_verification(driver)
            
            # 等待页面加载
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "h1"))
            )
            
            # 创建电影项
            movie_item = MovieItem()
            
            # 提取电影标题
            try:
                title_elem = driver.find_element(By.CSS_SELECTOR, "h1 span:first-child")
                movie_item['title'] = title_elem.text.strip()
            except Exception:
                try:
                    # 备用选择器
                    title_elem = driver.find_element(By.TAG_NAME, "h1")
                    movie_item['title'] = title_elem.text.strip()
                except Exception:
                    movie_item['title'] = "未知标题"
                    logger.error(f"无法提取电影标题: {url}")
            
            # 提取导演信息
            try:
                director_elem = driver.find_element(By.CSS_SELECTOR, 'a[rel="v:directedBy"]')
                movie_item['director'] = director_elem.text.strip()
            except Exception:
                try:
                    # 备用方式：查找包含"导演"的文本
                    director_text = driver.find_element(By.XPATH, "//*[contains(text(), '导演')]/following-sibling::*")
                    movie_item['director'] = director_text.text.strip()
                except Exception:
                    movie_item['director'] = "未知导演"
            
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
            
            # 记录提取的关键信息
            logger.warning(f"电影数据: {movie_item['title']}, {movie_item['year']}, 评分:{movie_item['rating']}")
            
            # 创建MovieItem实例
            movie_item['actors'] = actors
            movie_item['year'] = year
            movie_item['rating'] = rating
            movie_item['rating_count'] = rating_count
            movie_item['genre'] = genre
            movie_item['region'] = region
            movie_item['duration'] = duration
            movie_item['comments'] = []
            
            # 获取评论
            try:
                # 构建评论页URL
                comments_url = url + 'comments'
                
                # 先返回电影信息
                yield movie_item
                
                # 再获取评论
                driver.get(comments_url)
                self.random_sleep()
                
                # 获取评论内容
                comment_elements = driver.find_elements(By.CSS_SELECTOR, '.comment-item .comment-content')
                comments = [elem.text for elem in comment_elements if elem.text]
                
                if comments:
                    logger.warning(f"获取到{len(comments)}条评论")
                    movie_item_with_comments = movie_item.copy()
                    movie_item_with_comments['comments'] = comments
                    yield movie_item_with_comments
                else:
                    logger.warning("未找到评论内容")
                    
            except Exception as e:
                logger.error(f"获取评论出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
            return None
            
        except Exception as e:
            logger.error(f"Selenium解析电影详情出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
            
        finally:
            if driver:
                driver.quit()
    
    def parse_comments(self, response):
        """解析电影评论页面"""
        movie_id = response.meta.get('movie_id')
        comments = []
        
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
                logger.warning(f"获取到{len(comments)}条评论")
            else:
                logger.warning("响应不是HTML，无法获取评论")
            
            # 返回带有评论的电影信息
            yield movie_item
            
        except Exception as e:
            logger.error(f"解析评论出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
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
        """爬虫关闭时的清理操作"""
        logger.warning(f'爬虫关闭: {reason}')
        
        # 关闭WebDriver
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
                logger.warning("WebDriver已关闭")
            except Exception as e:
                logger.error(f"关闭WebDriver出错: {e}")
                
        # 其他清理操作
        logger.warning("爬虫资源已清理完毕")

if __name__ == '__main__':
    movie_names = '肖申克的救赎'
    process = CrawlerProcess()
    process.crawl(DoubanSpider, movie_names=movie_names)
    process.start()

