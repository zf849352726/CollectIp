import os
import sys
import logging
import time
import random
import scrapy
import traceback
import json
import pickle
from selenium import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from scrapy.crawler import CrawlerProcess
import urllib.parse
import pymysql
import django
import urllib.request
from ddddocr import DdddOcr
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver import Chrome
import base64
import uuid
import tempfile

# 获取项目根目录
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..', '..'))
# print(f"PROJECT_DIR路径：{PROJECT_DIR}")
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# 确保策略模块可以被导入
CRAWL_IP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
# print(f"CRAWL_IP_DIR :策略模块{CRAWL_IP_DIR }")
if CRAWL_IP_DIR not in sys.path:
    sys.path.insert(0, CRAWL_IP_DIR)

# 导入自定义日志设置 - 确保在使用logger之前设置
try:
    from ip_operator.services.crawler import setup_logging
    # 使用INFO级别以显示调试信息
    logger = setup_logging("douban_spider", logging.INFO)
except ImportError:
    # 如果无法导入，使用基本日志设置
    logger = logging.getLogger("douban_spider")
    logger.setLevel(logging.INFO)  # 降低日志级别以显示更多信息
    
    # 确保移除所有已有的handler避免重复
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
    # 添加控制台处理器
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')  # 简化日志格式
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("使用基本日志设置，无法导入自定义日志函数")

# 设置Selenium的日志级别
selenium_logger = logging.getLogger('selenium')
selenium_logger.setLevel(logging.ERROR)  # 仅记录错误
selenium_logger.propagate = False  # 防止日志传播到父级记录器

# 设置urllib3的日志级别
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.ERROR)  # 仅记录错误
urllib3_logger.propagate = False  # 防止日志传播到父级记录器

# 设置Scrapy的日志级别
scrapy_logger = logging.getLogger('scrapy')
scrapy_logger.setLevel(logging.INFO)  # 确保INFO级别日志能显示
scrapy_logger.propagate = False  # 防止日志传播到父级记录器

# 尝试多种导入方式以增强兼容性
try:
    # 首先尝试相对导入
    from ..strategies.comment_strategies import CommentStrategyFactory, get_random_strategy
except (ImportError, ValueError):
    try:
        # 尝试绝对导入
        from crawl_ip.strategies.comment_strategies import CommentStrategyFactory, get_random_strategy
    except ImportError:
        try:
            # 尝试直接导入
            sys.path.append(os.path.join(CRAWL_IP_DIR, 'strategies'))
            from comment_strategies import CommentStrategyFactory, get_random_strategy
        except ImportError:
            # 如果所有导入方式都失败，创建临时替代类
            print("警告: 无法导入策略模块，将使用临时替代实现")
            
            class CommentStrategy:
                def __init__(self, name="sequential", **kwargs):
                    self.name = name
                    self.params = kwargs
                
                def get_name(self):
                    return self.name
                
                def get_pages_to_crawl(self, total_comments=50):
                    # 默认顺序策略，返回前5页
                    return list(range(1, 6))
            
            class CommentStrategyFactory:
                @staticmethod
                def get_strategy(strategy_type, **kwargs):
                    return CommentStrategy(strategy_type, **kwargs)
            
            def get_random_strategy():
                return CommentStrategy("sequential")

# 导入Django设置和模型
try:
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

def decode_movie_name(encoded_name):
    """从base64解码电影名"""
    if not encoded_name:
        return ""
    try:
        # 从base64解码
        decoded = base64.b64decode(encoded_name).decode('utf-8')
        return decoded
    except Exception as e:
        logger.error(f"解码电影名失败: {str(e)}")
        return ""

class DoubanSpider(scrapy.Spider):
    name = 'douban_spider'
    allowed_domains = ['douban.com']
    
    # 自定义Scrapy设置
    custom_settings = {
        'LOG_LEVEL': 'DEBUG',  # 修改为DEBUG以显示更多日志
        'LOG_FORMAT': '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 1,
        'PROXY_DEBUG': True,  # 明确启用代理调试
        'UA_DEBUG': True,     # 明确启用UA调试
        'LOG_STDOUT': True,   # 确保日志输出到控制台
        'DOWNLOADER_MIDDLEWARES': {
            'ip_operator.crawl_ip.crawl_ip.crawl_ip.middlewares.RandomUserAgentMiddleware': 543,
            'ip_operator.crawl_ip.crawl_ip.crawl_ip.middlewares.DoubanDownloaderMiddleware': 600,
            'ip_operator.crawl_ip.crawl_ip.crawl_ip.middlewares.ProxyMiddleware': 750,
        }
    }


    def __init__(self, movie_names=None, comment_strategy=None, douban_username=None, douban_password=None, **kwargs):
        """初始化爬虫"""
        super(DoubanSpider, self).__init__(name='douban_spider', **kwargs)
        
        print("【调试】豆瓣爬虫初始化，将使用代理中间件和UA中间件")
        
        # 从环境变量中获取电影名
        movie_name = None  # 初始化为None，之后尝试各种方式获取
        import os
        # 先尝试从编码的环境变量获取（最可靠的方式）
        encoded_movie_name = os.environ.get('MOVIE_NAME_ENCODED')
        if encoded_movie_name:
            movie_name = decode_movie_name(encoded_movie_name)
            logger.warning(f"从编码的环境变量获取电影名: {movie_name}")
        
        # 如果失败，尝试直接获取
        if not movie_name:
            movie_name = os.environ.get('MOVIE_NAME')
            if movie_name:
                logger.warning(f"从原始环境变量获取电影名: {movie_name}")
        
        # 如果还是失败，尝试从MOVIE_NAME_ORIGINAL获取
        if not movie_name:
            movie_name = os.environ.get('MOVIE_NAME_ORIGINAL')
            if movie_name:
                logger.warning(f"从MOVIE_NAME_ORIGINAL环境变量获取电影名: {movie_name}")
        
        # 最后尝试ASCII版本
        if not movie_name:
            movie_name = os.environ.get('MOVIE_NAME_ASCII')
            if movie_name:
                logger.warning(f"从ASCII环境变量获取电影名: {movie_name}")
        
        # 设置电影名称列表
        if movie_name:
            self.movie_names = [movie_name]
        elif movie_names:
            if isinstance(movie_names, str):
                self.movie_names = [movie_names]
            else:
                self.movie_names = movie_names
        else:
            self.movie_names = ['肖申克的救赎']  # 默认电影
        
        # 记录电影名
        logger.warning(f"豆瓣爬虫爬取电影: {self.movie_names}")
        
        # 从环境变量中获取爬取配置
        crawl_config = {}
        try:
            env_config = os.environ.get('CRAWL_CONFIG')
            if env_config:
                import json
                crawl_config = json.loads(env_config)
                logger.warning(f"从环境变量获取爬取配置: {crawl_config}")
                
                # 从配置中获取策略
                if 'strategy' in crawl_config:
                    comment_strategy = crawl_config.get('strategy')
                    
                # 从配置中更新参数
                for param in ['max_pages', 'sample_size', 'max_interval', 'block_size', 'use_random_strategy']:
                    if param in crawl_config:
                        kwargs[param] = crawl_config[param]
        except Exception as e:
            logger.error(f"解析爬取配置时出错: {e}")
        
        # 初始化评论采集策略
        strategy_type = comment_strategy or 'sequential'
        strategy_params = {k: int(v) for k, v in kwargs.items() if k in [
            'max_pages', 'sample_size', 'max_interval', 'block_size'
        ] and v}
        
        # 检查是否使用随机策略
        use_random_strategy = kwargs.get('use_random_strategy', False) or crawl_config.get('use_random_strategy', False)
        if strategy_type == 'random' or use_random_strategy:
            self.comment_strategy = get_random_strategy()
            logger.warning("使用随机策略，系统将随机选择一种评论采集方式")
        else:
            self.comment_strategy = CommentStrategyFactory.get_strategy(
                strategy_type, **strategy_params
            )
        
        logger.warning(f"使用评论采集策略: {self.comment_strategy.get_name()}, 参数: {strategy_params}")
        
        # 设置ChromeDriver路径
        # 使用相对路径指向chrome-linux64目录
        # import os
        # from django.conf import settings
        # chrome_path = os.path.join(settings.BASE_DIR, 'ip_operator', 'chrome-linux64')
        self.driver_path = r'/usr/local/CollectIp/CollectIp/ip_operator/chromedriver-linux64/'
        logger.info(f"路径为：{self.driver_path}")
        if self.driver_path:
            logger.info(f"使用本地Chrome路径: {self.driver_path}")
        else:
            logger.warning("本地Chrome路径不存在，将使用默认设置")
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
        # 登录信息
        self.douban_username = douban_username or os.environ.get('DOUBAN_USERNAME')
        self.douban_password = douban_password or os.environ.get('DOUBAN_PASSWORD')
        self.is_logged_in = False
        self.cookies_file = os.path.join(PROJECT_DIR, 'logs', 'douban_cookies.pkl')
        
        # 移除重复定义的Chrome配置，因为get_driver中已有更完整的配置
        # Chrome配置将在get_driver中一次性设置
        
        # 初始化MySQL连接
        self.db_conn = None
        self.db_cursor = None
        try:
            from django.conf import settings as django_settings
            db_settings = django_settings.DATABASES['default']
            self.db_conn = pymysql.connect(
                host=db_settings['HOST'],
                user=db_settings['USER'],
                password=db_settings['PASSWORD'],
                database=db_settings['NAME'],
                charset='utf8mb4'
            )
            self.db_cursor = self.db_conn.cursor()
            logger.warning("MySQL数据库连接成功")
        except Exception as e:
            logger.error(f"MySQL连接失败: {e}")
            
    def check_movie_exists(self, title):
        """检查电影是否已存在于数据库中"""
        if not self.db_cursor:
            logger.warning("数据库连接不存在，无法检查电影")
            return False, None
            
        try:
            self.db_cursor.execute("SELECT id, title FROM index_movie WHERE title = %s LIMIT 1", (title,))
            result = self.db_cursor.fetchone()
            
            if result:
                movie_id, title = result
                logger.warning(f"电影《{title}》已存在于数据库，ID: {movie_id}")
                return True, movie_id
            else:
                logger.warning(f"电影《{title}》不存在于数据库")
                return False, None
        except Exception as e:
            logger.error(f"查询数据库失败: {e}")
            return False, None
            
    def get_driver(self):
        """获取Chrome浏览器实例"""
        logger.warning("开始初始化Chrome浏览器")
        
        if self.driver is None and self.driver_path:
            try:
                logger.warning(f"ChromeDriver路径: {self.driver_path}")
                logger.warning("正在创建浏览器实例...")
                
                # 使用标准Chrome WebDriver
                from selenium.webdriver.chrome.service import Service
                from selenium import webdriver
                
                service = Service(executable_path=self.driver_path)
                
                # 设置 Chrome 选项
                options = webdriver.ChromeOptions()
                
                # 解决DevToolsActivePort文件不存在的问题
                options.add_argument('--no-sandbox')  # 禁用沙箱
                options.add_argument('--disable-dev-shm-usage')  # 禁用/dev/shm使用
                options.add_argument('--disable-gpu')  # 禁用GPU加速
                
                # 添加无头模式（在服务器环境中运行）
                options.add_argument('--headless=new')  # 新版无头模式
                
                # 设置user-agent
                options.add_argument(f'user-agent={self.headers["User-Agent"]}')
                
                # 禁用自动化控制检测
                options.add_argument('--disable-blink-features=AutomationControlled')
                
                # 设置窗口大小
                options.add_argument('--window-size=1920,1080')
                
                # 解决在Docker容器中的问题
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-software-rasterizer')
                
                # 禁用各种可能导致崩溃的功能
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-infobars')
                options.add_argument('--mute-audio')
                options.add_argument('--no-first-run')
                options.add_argument('--no-service-autorun')
                options.add_argument('--password-store=basic')
                
                # 添加排除自动化控制的实验选项
                options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
                options.add_experimental_option('useAutomationExtension', False)
                
                # 解决远程调试端口问题
                options.add_argument('--remote-debugging-port=9222')
                
                logger.warning("Chrome浏览器配置已设置，准备启动")
                
                # 创建Chrome实例
                self.driver = webdriver.Chrome(service=service, options=options)
                
                # 执行JS脚本绕过反自动化检测
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                logger.warning("创建新的Chrome实例成功")
                logger.warning(f"浏览器地址: {self.driver.current_url}")
                
                # 加载已保存的Cookie
                if self.load_cookies():
                    logger.warning("已加载保存的Cookie")
                    self.is_logged_in = True
                
                return self.driver
            except Exception as e:
                logger.error(f"创建WebDriver失败: {e}")
                logger.error(traceback.format_exc())
                return None
        elif self.driver is not None:
            logger.warning("使用现有的WebDriver实例")
            return self.driver
        else:
            logger.error("未找到ChromeDriver路径")
            return None
    
    def load_cookies(self):
        """加载保存的Cookie"""
        try:
            if os.path.exists(self.cookies_file):
                # 首先访问豆瓣域名，才能设置Cookie
                self.driver.get("https://www.douban.com")
                self.random_sleep(1, 2)
                
                with open(self.cookies_file, 'rb') as f:
                    cookies = pickle.load(f)
                    
                for cookie in cookies:
                    if 'expiry' in cookie:
                        del cookie['expiry']  # 这个字段可能导致问题
                    self.driver.add_cookie(cookie)
                
                # 再次访问豆瓣以检查Cookie是否生效
                self.driver.get("https://www.douban.com")
                self.random_sleep(1, 2)
                
                # 检查是否成功登录
                try:
                    # 如果能找到个人头像或用户名元素，说明已登录
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".top-nav-info .bn-more, .top-nav-info .nav-user-account"))
                    )
                    logger.warning("Cookie加载成功，已处于登录状态")
                    return True
                except:
                    logger.warning("Cookie已过期或无效，需要重新登录")
                    return False
            else:
                logger.warning("未找到Cookie文件，需要登录")
                return False
        except Exception as e:
            logger.error(f"加载Cookie时出错: {e}")
            return False
    
    def save_cookies(self):
        """保存Cookie到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.cookies_file), exist_ok=True)
            
            # 获取并保存Cookie
            cookies = self.driver.get_cookies()
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(cookies, f)
            
            logger.warning(f"已保存Cookie到 {self.cookies_file}")
        except Exception as e:
            logger.error(f"保存Cookie失败: {e}")
    
    def login_douban(self):
        """登录豆瓣"""
        if self.is_logged_in:
            logger.warning("已经登录，无需重复登录")
            return True
            
        if not self.douban_username or not self.douban_password:
            logger.error("未提供豆瓣账号密码，无法登录")
            return False
            
        try:

            try:
                logger.warning("开始登录豆瓣...")
                self.driver.get("https://www.douban.com/")

                iframe = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.TAG_NAME, "iframe"))
                )
                if iframe:
                    logger.warning("检测到豆瓣登录页面iframe")
                    # 切换到豆瓣验证码iframe
                    self.driver.switch_to.frame(iframe)
                    logger.info("已切换到豆瓣登录页iframe")
            except:
                logger.warning("未检测到豆瓣登录页iframe")

            # 等待登录页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".account-tab-account"))
            )
            time.sleep(2)
            # 点击切换到密码登录
            account_tab = self.driver.find_element(By.CSS_SELECTOR, ".account-tab-account")
            account_tab.click()
            self.random_sleep(1, 2)
            
            # 输入账号密码
            username_input = self.driver.find_element(By.ID, "username")
            password_input = self.driver.find_element(By.ID, "password")
            
            username_input.clear()
            username_input.send_keys(self.douban_username)
            self.random_sleep(0.5, 1)
            
            password_input.clear()
            password_input.send_keys(self.douban_password)
            self.random_sleep(0.5, 1)
            
            # 点击登录按钮
            login_button = self.driver.find_element(By.CSS_SELECTOR, ".account-form-field-submit .btn-account")
            login_button.click()
            
            # 检查是否出现了验证码
            if self.check_captcha():
                logger.warning("需要处理验证码")
                if not self.handle_tc_captcha(max_retries=3):
                    logger.error("验证码处理失败，登录失败")
                    return False
                
                # 验证码处理成功后，等待重定向完成
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".top-nav-info"))
                    )
                except:
                    logger.error("等待登录完成超时")
                    return False
                
            # 验证是否登录成功
            if "https://www.douban.com" in self.driver.current_url:
                logger.warning("登录成功")
                self.is_logged_in = True
                
                # 保存Cookie
                self.save_cookies()
                return True
            else:
                logger.error("登录失败：未跳转到豆瓣首页")
                return False
                
        except Exception as e:
            logger.error(f"登录过程出错: {e}")
            tb = traceback.format_exc()
            logger.error(tb)
            return False
    
    def check_captcha(self):
        """检查是否出现验证码（包括图形验证码和滑块验证码）"""
        try:
            # 检查是否存在豆瓣验证码iframe
            try:
                iframe = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.ID, "tcaptcha_iframe_dy"))
                )
                if iframe:
                    logger.warning("检测到豆瓣验证码iframe")
                    # 切换到豆瓣验证码iframe
                    self.driver.switch_to.frame(iframe)
                    logger.info("已切换到豆瓣验证码iframe")
            except:
                logger.warning("未检测到豆瓣验证码iframe")

            # 首先检查是否存在图形验证码
            try:
                captcha_element = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.ID, "captcha_image"))
                )
                if captcha_element:
                    logger.warning("检测到图形验证码")
                    return "text_captcha"
            except:
                pass

            # 检查是否存在滑块验证码
            try:
                slide_element = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.ID, "slideBg"))
                )
                if slide_element:
                    logger.warning("检测到滑块验证码")
                    return "slide_captcha"
            except:
                pass

            # 检查其他可能的验证码元素
            try:
                other_verify = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.ID, "verify"))
                )
                if other_verify:
                    logger.warning("检测到其他类型验证码")
                    return "other_captcha"
            except:
                pass

            return False
        except Exception as e:
            logger.error(f"检查验证码时出错: {str(e)}")
            return False

    def _ease_out_quad(self, x):
        """缓动函数 - 模拟人类滑动的加速度变化"""
        return x * (2 - x)

    def ensure_login(self):
        """确保登录状态"""
        if self.is_logged_in:
            return True
            
        # 尝试加载Cookie
        if self.load_cookies():
            self.is_logged_in = True
            return True
            
        # 如果Cookie无效，尝试登录
        return self.login_douban()
        
    def start_requests(self):
        """定义起始URL并传递电影名称"""
        logger.warning(f"使用Selenium启动爬虫，电影名: {self.movie_names}")
        
        # 获取WebDriver并确保登录
        driver = self.get_driver()
        if not driver:
            logger.error("无法获取WebDriver")
            return
        
        # 打印浏览器版本和状态确认
        logger.warning(f"Chrome浏览器已启动，地址: {driver.current_url}")
            
        # 生成搜索URL
        search_url = f"https://search.douban.com/movie/subject_search?search_text={urllib.parse.quote(self.movie_names[0])}"
        logger.warning(f"开始搜索电影: {self.movie_names[0]}")
        
        # 使用Selenium直接访问和处理
        yield from self.parse_with_selenium(search_url, self.movie_names)
            
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

        # # 确保已登录
        # if not self.ensure_login():
        #     logger.error("登录失败，无法继续爬取")
        #     return
            
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
            
        # # 确保已登录
        # if not self.ensure_login():
        #     logger.error("登录失败，无法继续爬取")
        #     return
            
        try:
            # 访问详情页
            driver.get(url)
            self.random_sleep()
            
            # 处理验证码
            # self.handle_verification(driver)
            
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
                    
            # 检查电影是否已存在于数据库中
            exists, movie_id = self.check_movie_exists(movie_item['title'])
            
            # 如果电影已存在，只提取评分、评分人数和评论
            if exists:
                logger.warning(f"电影《{movie_item['title']}》已存在，只更新评分、评分人数和评论")
                movie_item['id'] = movie_id
                
                # 获取评分
                try:
                    rating = driver.find_element(By.CSS_SELECTOR, '.rating_num').text
                    movie_item['rating'] = rating
                except:
                    rating = '0'
                    movie_item['rating'] = rating
                
                # 获取评分人数
                try:
                    rating_count = driver.find_element(By.CSS_SELECTOR, '.rating_people span').text
                    movie_item['rating_count'] = rating_count
                except:
                    rating_count = '0'
                    movie_item['rating_count'] = rating_count
                    
                # 记录提取的关键信息
                logger.warning(f"更新电影数据: {movie_item['title']}, 评分:{movie_item['rating']}, 评分人数:{movie_item['rating_count']}")
                
                # 初始化评论列表
                movie_item['comments'] = []
                
                # 获取评论并返回
                yield from self.crawl_comments(driver, url, movie_item)
                
                return
            
            # 如果电影不存在，正常爬取所有信息
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
                    
            # 获取海报URL
            try:
                poster_element = driver.find_element(By.CSS_SELECTOR, '#mainpic img')
                poster_url = poster_element.get_attribute('src')
                logger.warning(f"获取到海报URL: {poster_url}")
                movie_item['poster_url'] = poster_url
            except Exception as e:
                logger.error(f"获取海报URL出错: {str(e)}")
                movie_item['poster_url'] = None
                
            # 获取剧情简介
            try:
                # 先检查是否有短简介
                try:
                    summary_element = driver.find_element(By.CSS_SELECTOR, 'span[property="v:summary"]')
                    summary = summary_element.text.strip()
                except:
                    # 如果没有短简介，尝试获取详细简介
                    summary_element = driver.find_element(By.CSS_SELECTOR, '.related-info .indent span.short')
                    if not summary_element or not summary_element.text.strip():
                        summary_element = driver.find_element(By.CSS_SELECTOR, '.related-info .indent span.all')
                    summary = summary_element.text.strip()
                    
                # 如果简介太短或为空，尝试其他选择器
                if len(summary) < 10:
                    summary_element = driver.find_element(By.XPATH, '//span[contains(text(), "简介")]/../../following-sibling::div[contains(@class, "indent")]')
                    summary = summary_element.text.strip()
                
                movie_item['summary'] = summary
                logger.warning(f"获取到剧情简介: {summary[:50]}...")
            except Exception as e:
                logger.error(f"获取剧情简介出错: {str(e)}")
                movie_item['summary'] = "暂无简介"
            
            # 设置所有字段
            movie_item['actors'] = actors
            movie_item['year'] = year
            movie_item['rating'] = rating
            movie_item['rating_count'] = rating_count
            movie_item['genre'] = genre
            movie_item['region'] = region
            movie_item['duration'] = duration
            movie_item['comments'] = []
            
            # 记录提取的关键信息
            logger.warning(f"电影数据: {movie_item['title']}, {movie_item['year']}, 评分:{movie_item['rating']}")
            
            # 获取评论
            yield from self.crawl_comments(driver, url, movie_item)
            
            return None
            
        except Exception as e:
            logger.error(f"Selenium解析电影详情出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def crawl_comments(self, driver, url, movie_item):
        """获取电影评论"""
        try:
            # # 确保已登录
            # if not self.ensure_login():
            #     logger.error("登录失败，无法继续爬取评论")
            #     yield movie_item  # 返回无评论的电影数据
            #     return
                
            # 先返回电影基本信息
            yield movie_item
            
            # 构建评论页URL
            comments_url = url + 'comments'
            logger.warning(f"开始获取电影评论: {comments_url}")
            
            # 使用策略确定要爬取的页码
            pages_to_crawl = self.comment_strategy.get_pages_to_crawl(self.comments_per_movie)
            logger.info(f"采集策略 {self.comment_strategy.get_name()} 决定采集页码: {pages_to_crawl}")
            
            # 处理第一页评论，第一页已加载
            if 1 in pages_to_crawl:
                self.process_current_page_comments(driver, movie_item['comments'])
                pages_to_crawl.remove(1)  # 已处理第1页，从列表中移除
            
            # 处理剩余页码
            for page_num in pages_to_crawl:
                try:
                    # 确保我们有正确的电影ID
                    movie_url_parts = url.rstrip('/').split('/')
                    subject_index = movie_url_parts.index('subject') if 'subject' in movie_url_parts else -1
                    
                    if subject_index != -1 and subject_index + 1 < len(movie_url_parts):
                        movie_id = movie_url_parts[subject_index + 1]
                    else:
                        # 尝试从页面元素获取ID
                        page_source = driver.page_source
                        import re
                        id_match = re.search(r'(subject|sid)\/(\d+)', page_source)
                        if id_match:
                            movie_id = id_match.group(2)
                        else:
                            logger.error("无法获取电影ID，跳过评论获取")
                            break
                    
                    logger.warning(f"获取到电影ID: {movie_id}")
                    
                    # 构建评论页URL
                    page_url = f"https://movie.douban.com/subject/{movie_id}/comments?start={(page_num-1)*20}&limit=20&status=P&sort=new_score"
                    logger.warning(f"访问第{page_num}页评论: {page_url}")
                    time.sleep(1)
                    driver.get(page_url)
                    # # 处理验证码
                    # self.handle_verification(driver)
                    # 等待评论加载
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".comment-item"))
                    )
                    self.random_sleep(2, 5)  # 增加随机等待时间
                    
                    # 处理当前页评论
                    self.process_current_page_comments(driver, movie_item['comments'])
                    
                except Exception as e:
                    logger.error(f"访问第{page_num}页评论时出错: {str(e)}")
                    import traceback as tb
                    tb.print_exc()
                    
            # 将评论添加到电影数据中
            # 过滤掉可能的空评论，确保统计准确
            valid_comments = [comment for comment in movie_item['comments'] if comment]
            logger.warning(f"共获取到{len(valid_comments)}条有效评论，总评论数：{len(movie_item['comments'])}")
            
            # 创建一个新的item，包含评论数据
            comment_item = movie_item.copy()
            
            # 提取评论内容列表 (为了兼容原有管道)
            comment_texts = [comment for comment in movie_item['comments'] if comment]
            comment_item['comments'] = comment_texts
            
            # 添加评论详细信息列表 (为了提供给新的评论管道)
            comment_item['comment_details'] = movie_item['comments']
            
            # 返回包含评论的电影信息
            yield comment_item
            
        except Exception as e:
            logger.error(f"获取评论出错: {str(e)}")
            import traceback as tb
            tb.print_exc()
            
    def parse_comments(self, response):
        """解析电影评论页面"""
        movie_id = response.meta.get('movie_id')
        comments = []
        
        try:
            # 获取电影信息
            movie_item = response.meta.get('movie_item').copy()
            
            # 如果是HTML响应，使用CSS选择器
            if isinstance(response, scrapy.http.HtmlResponse):
                # 获取评论内容 - 尝试多种可能的选择器
                comments = []
                try:
                    # 尝试原始选择器
                    comments = response.css('.comment-item .comment-content::text').getall()

                    # 如果原始选择器没有结果，尝试其他选择器
                    if not comments:
                        logger.warning("原始评论选择器无结果，尝试替代选择器")
                        
                        # 尝试多种可能的选择器
                        alternative_selectors = [
                            '.comment-item .short::text',
                            '.comment-item .comment-text::text',
                            '.comment-item p::text',
                            '.comment-item .abstract::text'
                        ]
                        
                        for selector in alternative_selectors:
                            comments = response.css(selector).getall()
                            if comments:
                                logger.info(f"成功使用替代选择器: {selector}")
                                break
                except Exception as e:
                    logger.error(f"获取评论内容时出错: {str(e)}")

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
            captcha_type = self.check_captcha()
            if captcha_type:
                logger.warning(f"检测到{captcha_type}验证码，尝试处理...")
                self.handle_captcha(max_retries=3)
                return True
        except Exception as e:
            logger.error(f"验证处理失败: {str(e)}")
            
        # 没有验证码或处理完成，继续正常流程
        return False
            
    def closed(self, reason):
        """爬虫关闭时的清理工作"""
        logger.warning(f"爬虫结束，原因: {reason}")
        
        # 关闭浏览器
        if self.driver:
            try:
                logger.warning("关闭浏览器实例")
                self.driver.quit()
                
                # 给Chrome一些时间完全退出
                import time
                time.sleep(2)
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {e}")
            finally:
                self.driver = None
                
        # 写入爬取结果统计
        logger.warning(f"电影详情页爬取统计: {self.stats}")
        logger.warning(f"总评论条数: {self.comment_count}")
        
        all_comments = []
        for movie_id, comments in self.collected_comments.items():
            all_comments.extend(comments)
            
        logger.warning(f"成功采集评论数: {len(all_comments)}")
        logger.warning("爬虫清理工作完成")

    def process_current_page_comments(self, driver, all_comments):
        """处理当前页面的评论"""
        # 获取评论元素
        comment_items = driver.find_elements(By.CSS_SELECTOR, '.comment-item')
        logger.info(f"当前页面找到 {len(comment_items)} 条评论")
        
        # 解析评论数据
        for item in comment_items:
            try:
                # 评论内容 - 尝试多种可能的选择器
                try:
                    comment_content_element = None
                    selectors = [
                        '.comment-content',   # 原始选择器
                        '.short',             # 可能的替代选择器
                        '.comment-text',      # 可能的替代选择器
                        '.comment p',         # 可能的替代选择器
                        'p',                  # 最简单的选择器
                        '.comment-item > p',  # 直接子元素
                        '.abstract'           # 另一个可能的类名
                    ]
                    
                    for selector in selectors:
                        try:
                            elements = item.find_elements(By.CSS_SELECTOR, selector)
                            if elements and len(elements) > 0:
                                comment_content_element = elements[0]
                                logger.debug(f"成功使用选择器 '{selector}' 找到评论内容元素")
                                break
                        except Exception as e:
                            logger.debug(f"选择器 '{selector}' 失败: {str(e)}")
                            continue
                    
                    if comment_content_element:
                        comment_content = comment_content_element.text.strip()
                    else:
                        # 如果所有选择器都失败，尝试获取整个评论项的文本
                        logger.warning("所有评论内容选择器都失败，尝试获取整个评论项的文本")
                        comment_content = item.text.strip()
                        
                        # 从完整文本中提取评论内容 (去除用户名、时间等)
                        # 这是一个粗略的解决方案，可能需要基于实际HTML结构调整
                        lines = comment_content.split('\n')
                        if len(lines) > 2:  # 假设前两行是用户信息和时间
                            comment_content = '\n'.join(lines[2:])
                
                except Exception as e:
                    logger.error(f"获取评论内容时出错: {str(e)}")
                    comment_content = "无法获取评论内容"
                
                # 如果评论内容为空，跳过
                if not comment_content:
                    continue
                
                # 用户信息
                try:
                    user_element = item.find_element(By.CSS_SELECTOR, '.comment-info a')
                    user_nickname = user_element.text.strip()
                except:
                    try:
                        # 尝试其他可能的选择器
                        user_elements = item.find_elements(By.CSS_SELECTOR, 'a')
                        user_nickname = user_elements[0].text.strip() if user_elements else '匿名用户'
                    except:
                        user_nickname = '匿名用户'
                
                # 评分
                try:
                    rating_element = item.find_element(By.CSS_SELECTOR, '.rating')
                    rating_class = rating_element.get_attribute('class')
                    if 'allstar' in rating_class:
                        # 提取评分值 (如 allstar50 表示5星)
                        rating_value = rating_class.split('allstar')[-1].split(' ')[0]
                        # 转换为1-5的评分 (50->5, 40->4, 等)
                        rating = str(int(rating_value) // 10) 
                    else:
                        rating = '0'
                except:
                    try:
                        # 尝试其他可能的选择器
                        rating_elements = item.find_elements(By.CSS_SELECTOR, '[class*="star"]')
                        if rating_elements:
                            rating_class = rating_elements[0].get_attribute('class')
                            if 'star' in rating_class:
                                # 尝试从类名中提取数字
                                import re
                                match = re.search(r'(\d+)', rating_class)
                                if match:
                                    rating = str(int(match.group(1)) // 10)
                                else:
                                    rating = '0'
                            else:
                                rating = '0'
                        else:
                            rating = '0'
                    except:
                        rating = '0'
                    
                # 评论时间
                try:
                    time_element = item.find_element(By.CSS_SELECTOR, '.comment-time')
                    comment_time = time_element.text.strip()
                except:
                    try:
                        # 尝试其他可能的选择器
                        time_elements = item.find_elements(By.CSS_SELECTOR, 'time, .time, span[class*="time"]')
                        comment_time = time_elements[0].text.strip() if time_elements else ''
                    except:
                        comment_time = ''
                
                # 有用数量
                try:
                    votes_element = item.find_element(By.CSS_SELECTOR, '.votes')
                    votes = votes_element.text.strip()
                except:
                    try:
                        # 尝试其他可能的选择器
                        votes_elements = item.find_elements(By.CSS_SELECTOR, '[class*="vote"], .up, .like')
                        votes = votes_elements[0].text.strip() if votes_elements else '0'
                    except:
                        votes = '0'
                
                # 创建评论对象
                comment = {
                    'content': comment_content,
                    'user': user_nickname,
                    'rating': rating,
                    'time': comment_time,
                    'votes': votes
                }
                
                # 添加到评论列表
                all_comments.append(comment)
                logger.debug(f"提取评论: {user_nickname} - {comment_content[:20]}...")
                
            except Exception as e:
                logger.error(f"解析评论出错: {str(e)}")
                import traceback as tb
                tb.print_exc()
        
        logger.info(f"当前页解析完成，累计获取 {len(all_comments)} 条评论")

    def handle_tc_captcha(self, max_retries=3):
        """处理腾讯验证码"""
        retry_count = 0
        success = False
        
        # 确保先切回主文档
        try:
            self.driver.switch_to.default_content()
            logger.info("已切回主文档")
        except:
            logger.warning("切回主文档失败或已经在主文档")
        
        while retry_count < max_retries and not success:
            try:
                logger.warning(f"尝试处理腾讯验证码 (尝试 {retry_count+1}/{max_retries})...")
                
                # 切换到腾讯验证码iframe
                iframe = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.ID, "tcaptcha_iframe_dy"))
                )
                self.driver.switch_to.frame(iframe)
                logger.warning("已切换到验证码iframe")

                # 处理方式1: 从CSS样式中获取图片URL
                try:
                    # 等待加载验证码元素
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.ID, "slideBg"))
                    )
                    
                    # 获取背景图URL
                    bg_element = self.driver.find_element(By.ID, "slideBg")
                    bg_style = bg_element.get_attribute("style")
                    background_url = None
                    
                    if "background-image" in bg_style:
                        style_parts = bg_style.split(";")
                        for part in style_parts:
                            if "background-image" in part:
                                url_part = part.split("url(")[1].split(")")[0]
                                # 移除引号
                                background_url = url_part.strip('"').strip("'")
                                logger.info(f"获取到背景图URL: {background_url}")
                                break
                    
                    # 获取滑块图URL
                    slider_element = self.driver.find_element(By.XPATH, '//*[@id="tcOperation"]/div[7]')
                    logger.info(f"slider_element:{slider_element}")
                    slider_style = slider_element.get_attribute("style")
                    slide_url = None
                    
                    if "background-image" in slider_style:
                        style_parts = slider_style.split(";")
                        for part in style_parts:
                            if "background-image" in part:
                                url_part = part.split("url(")[1].split(")")[0]
                                # 移除引号
                                slide_url = url_part.strip('"').strip("'")
                                logger.info(f"获取到滑块图URL: {slide_url}")
                                break
                    
                    if background_url and slide_url:
                        # 下载图片
                        import requests
                        bg_response = requests.get(background_url, timeout=10)
                        slide_response = requests.get(slide_url, timeout=10)
                        
                        if bg_response.status_code == 200 and slide_response.status_code == 200:
                            # 保存图片
                            debug_dir = os.path.join(PROJECT_DIR, 'logs', 'captcha_debug')
                            os.makedirs(debug_dir, exist_ok=True)
                            
                            bg_path = os.path.join(debug_dir, 'tc_background.png')
                            slide_path = os.path.join(debug_dir, 'tc_slide.png')

                            with open(bg_path, 'wb') as f:
                                f.write(bg_response.content)

                            with open(slide_path, 'wb') as f:
                                f.write(slide_response.content)
                            
                            logger.info(f"背景图和滑块图已保存至: {debug_dir}")
                            
                            self.scale_img(bg_path, slide_path)

                            cropped = self.handle_slider_img(slide_path)

                            slide_path_cropped = os.path.join(debug_dir, 'tc_slide_cropped.png')

                            import cv2
                            cv2.imwrite(slide_path_cropped, cropped)
                            # 使用ddddocr识别滑动距离
                            detector = DdddOcr(det=False, ocr=False, show_ad=False)
                            try:
                                with open(slide_path_cropped, 'rb') as f:
                                    slide_bytes = f.read()
                                with open(bg_path, 'rb') as f:
                                    bg_bytes = f.read()
                                # 尝试使用simple_target参数
                                res = detector.slide_match(slide_bytes, bg_bytes, simple_target=True)
                                logger.info(f"滑块匹配结果(simple_target=True): {res}")
                            except Exception as e:
                                logger.error(f"使用simple_target模式匹配失败: {str(e)}")

                            if res and 'target' in res:
                                # 获取滑动距离
                                distance = res['target'][0]
                                logger.warning(f"滑动验证码识别结果: 需要滑动 {distance} 像素")
                                
                                # 获取滑动按钮元素
                                slider_button = self.driver.find_element(By.XPATH, '//*[@id="tcOperation"]/div[6]/img')
                                logger.info(f"滑动按钮元素:{slider_button}")
                                # 执行滑动操作
                                self._perform_slide(slider_button, distance)
                                
                                # 等待验证结果
                                self.random_sleep(2, 3)
                                
                                # 切回主文档
                                self.driver.switch_to.default_content()
                                
                                # 检查验证码是否还存在
                                try:
                                    iframe_exists = self.driver.find_element(By.ID, "tcaptcha_iframe_dy")
                                    if iframe_exists:
                                        logger.warning("验证码iframe仍然存在，可能验证失败")
                                        retry_count += 1
                                    else:
                                        logger.warning("验证码iframe已消失，可能验证成功")
                                        success = True
                                except:
                                    logger.warning("验证码iframe已消失，可能验证成功")
                                    success = True
                            else:
                                logger.error("滑块匹配失败，无有效结果")
                                retry_count += 1
                                self.driver.switch_to.default_content()
                        else:
                            logger.error(f"下载验证码图片失败: BG状态码 {bg_response.status_code}, SLIDE状态码 {slide_response.status_code}")
                            retry_count += 1
                            self.driver.switch_to.default_content()
                    else:
                        logger.warning("URL获取方式失败，尝试使用Canvas方式")
                        # 继续执行后续的Canvas方式
                        raise Exception("找不到背景图或滑块图URL")
                except Exception as url_method_error:
                    logger.error(f"URL方法处理验证码失败: {str(url_method_error)}")
            except Exception as e:
                logger.error(f"处理腾讯验证码失败：{e}")
                return False
        return success

    def handle_slider_img(self, slide_path):
        # 处理滑块：截图
        if not os.path.exists(slide_path):
            logger.error(f"文件不存在: {slide_path}")
            return

        # 加载图片获取尺寸
        import cv2
        img = cv2.imread(slide_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            print(f"无法加载图片: {slide_path}")
            return

        if img is None:
            logger.error(f"无法加载图片: {slide_path}")
            return None
        # 直接截取区域，不做任何处理
        x = 80
        y = 258
        width = 40
        height = 40

        cropped = img[y:y + height, x:x + width].copy()

        return cropped

    def scale_img(self, bg_img_path, slide_img_path):
        import cv2
        # 加载图片
        bg_img = cv2.imread(bg_img_path, cv2.IMREAD_UNCHANGED)
        slide_img = cv2.imread(slide_img_path, cv2.IMREAD_UNCHANGED)

        # 获取图片尺寸
        bg_height, bg_width = bg_img.shape[:2]
        slide_height, slide_width = slide_img.shape[:2]

        # 计算缩放比例
        scale_x_bg = 340 / bg_width
        scale_y_bg = 242.857 / bg_height
        scale_x_slide = 345.06 / slide_width
        scale_y_slide = 313.69 / slide_height

        # 缩放图片
        bg_img = cv2.resize(bg_img, (int(bg_width * scale_x_bg), int(bg_height * scale_y_bg)))
        slide_img = cv2.resize(slide_img, (int(slide_width * scale_x_slide), int(slide_height * scale_y_slide)))

        # 保存缩放后的图片  
        cv2.imwrite(bg_img_path, bg_img)
        cv2.imwrite(slide_img_path, slide_img)

    def _perform_slide(self, slider_button, distance):
        """执行滑动操作"""
        distance += 25.2976 / 2
        # 算透明框
        distance = distance - (60.7 // 2)
        action = ActionChains(self.driver)
        
        # 点击并按住滑块
        action.click_and_hold(slider_button)
        action.pause(0.2)  # 短暂停顿
        
        # 模拟人类滑动行为
        steps = 30
        for i in range(steps):
            ratio = i / steps
            offset = distance * self._ease_out_quad(ratio)
            action.move_by_offset(offset - (distance * self._ease_out_quad((i-1)/steps) if i > 0 else 0), 0)
            action.pause(0.01)
        
        # 添加随机性
        action.move_by_offset(random.randint(-3, 3), random.randint(-2, 2))
        action.pause(0.05)
        
        # 释放滑块
        action.release()
        action.perform()

# 在文件末尾添加测试函数
def test_comment_strategies():
    """测试不同的评论采集策略"""
    import time
    import pandas as pd
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    
    print("开始测试评论采集策略...")
    
    # 测试电影列表
    test_movies = ['出走的决心']
    
    # 策略列表及其参数
    strategies = [
        {'name': 'sequential', 'params': {'max_pages': 5}},
        {'name': 'random_pages', 'params': {'sample_size': 5}},
        {'name': 'random_interval', 'params': {'max_interval': 3, 'max_pages': 5}},
        {'name': 'random_block', 'params': {'block_size': 3}}
    ]
    
    # 结果存储
    results = []
    
    for movie in test_movies:
        print(f"\n开始测试电影: {movie}")
        
        for strategy in strategies:
            strategy_name = strategy['name']
            params = strategy['params']
            
            print(f"测试策略: {strategy_name}, 参数: {params}")
            
            # 记录开始时间
            start_time = time.time()
            
            try:
                # 配置爬虫设置
                settings = get_project_settings()
                settings.set('LOG_LEVEL', 'INFO')
                settings.set('ITEM_PIPELINES', {
                    'crawl_ip.pipelines.MoviePipeline': 300,
                    'crawl_ip.pipelines.CommentPipeline': 400,
                })
                
                # 启动爬虫进程
                process = CrawlerProcess(settings=settings)
                process.crawl(
                    DoubanSpider, 
                    movie_names=movie,
                    comment_strategy=strategy_name,
                    **params
                )
                
                # 运行爬虫
                process.start()
                
                # 记录结束时间
                end_time = time.time()
                duration = end_time - start_time
                
                # 尝试获取MongoDB中的结果
                try:
                    # 动态导入MongoDB客户端
                    sys.path.insert(0, PROJECT_DIR)  # 确保可以导入Django应用
                    
                    try:
                        from index.mongodb_utils import MongoDBClient
                        mongo_client = MongoDBClient.get_instance()
                        
                        # 查询电影ID
                        try:
                            import pymysql
                            import django
                            django.setup()
                            from django.conf import settings as django_settings
                            
                            # 获取MySQL连接
                            db_settings = django_settings.DATABASES['default']
                            conn = pymysql.connect(
                                host=db_settings['HOST'],
                                user=db_settings['USER'],
                                password=db_settings['PASSWORD'],
                                database=db_settings['NAME'],
                                charset='utf8mb4'
                            )
                            
                            cursor = conn.cursor()
                            cursor.execute("SELECT id FROM index_movie WHERE title = %s LIMIT 1", (movie,))
                            result = cursor.fetchone()
                            movie_id = result[0] if result else None
                            cursor.close()
                            conn.close()
                            
                            # 获取评论数量
                            comment_count = 0
                            if movie_id:
                                query = {"movie_id": str(movie_id), "comment_strategy": strategy_name}
                                comment_count = mongo_client.comments_collection.count_documents(query)
                            
                            print(f"测试完成: 策略={strategy_name}, 电影={movie}, 评论数={comment_count}, 用时={duration:.2f}秒")
                            
                            # 保存结果
                            results.append({
                                'movie': movie,
                                'strategy': strategy_name,
                                'params': str(params),
                                'comment_count': comment_count,
                                'duration': duration,
                                'success': True
                            })
                            
                        except Exception as e:
                            print(f"查询数据库失败: {str(e)}")
                            results.append({
                                'movie': movie,
                                'strategy': strategy_name,
                                'params': str(params),
                                'comment_count': '未知',
                                'duration': duration,
                                'success': True,
                                'error': f"查询数据库失败: {str(e)}"
                            })
                    except Exception as e:
                        print(f"MongoDB连接失败: {str(e)}")
                        results.append({
                            'movie': movie,
                            'strategy': strategy_name,
                            'params': str(params),
                            'comment_count': '未知',
                            'duration': duration,
                            'success': True,
                            'error': f"MongoDB连接失败: {str(e)}"
                        })
                except Exception as e:
                    print(f"结果评估失败: {str(e)}")
                    results.append({
                        'movie': movie,
                        'strategy': strategy_name,
                        'params': str(params),
                        'comment_count': '未知',
                        'duration': duration,
                        'success': True,
                        'error': f"结果评估失败: {str(e)}"
                    })
                
            except Exception as e:
                # 记录失败
                print(f"测试失败: 策略={strategy_name}, 电影={movie}, 错误={str(e)}")
                traceback.print_exc()
                results.append({
                    'movie': movie,
                    'strategy': strategy_name,
                    'params': str(params),
                    'comment_count': 0,
                    'duration': time.time() - start_time,
                    'success': False,
                    'error': str(e)
                })
    
    try:
        # 将结果保存为CSV文件
        df = pd.DataFrame(results)
        results_file = os.path.join(os.getcwd(), 'strategy_test_results.csv')
        df.to_csv(results_file, index=False, encoding='utf-8-sig')
        print(f"\n测试结果已保存到: {results_file}")
        
        # 简单分析结果
        if len(results) > 0:
            print("\n各策略评论数量统计:")
            success_df = df[df['success'] == True]
            if len(success_df) > 0:
                try:
                    print(success_df.groupby('strategy')['comment_count'].mean())
                    
                    print("\n各策略成功率:")
                    print(df.groupby('strategy')['success'].mean())
                    
                    print("\n各策略平均用时(秒):")
                    print(df.groupby('strategy')['duration'].mean())
                except Exception as e:
                    print(f"结果分析失败: {str(e)}")
            else:
                print("没有成功的测试结果可供分析")
        else:
            print("没有测试结果可供分析")
    except Exception as e:
        print(f"保存或分析结果失败: {str(e)}")
        traceback.print_exc()

# 在需要执行测试时调用
if __name__ == "__main__":
    print("即将测试豆瓣爬虫...")
    from scrapy.crawler import CrawlerProcess
    from scrapy.utils.project import get_project_settings
    
    settings = get_project_settings()
    settings.update({
        'LOG_LEVEL': 'DEBUG',
        'LOG_FORMAT': '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        'PROXY_DEBUG': True,
        'UA_DEBUG': True,
        'LOG_STDOUT': True,
    })
    process = CrawlerProcess(settings)
    process.crawl(DoubanSpider, movie_names="星际穿越")
    print("启动爬虫...")
    process.start()
    print("爬虫运行结束")

