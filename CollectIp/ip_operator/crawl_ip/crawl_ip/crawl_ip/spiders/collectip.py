import scrapy
import time
import json
import os
import logging
from selenium.webdriver import Chrome
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
from ..items import IpItem
from ddddocr import DdddOcr
import base64
import sys
from datetime import datetime

# 获取项目根目录
PROJECT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# 引入自定义日志设置
try:
    from ip_operator.services.crawler import setup_logging
    # 使用INFO级别以显示调试信息
    logger = setup_logging("collectip_spider", logging.INFO)
except ImportError:
    # 如果无法导入，使用基本日志设置
    logger = logging.getLogger("collectip_spider")
    logger.setLevel(logging.INFO)  # 确保日志级别为INFO以显示调试信息
    
    # 检查是否已经有处理器，如果有则移除
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            
    # 创建日志目录
    log_dir = os.path.join(PROJECT_DIR, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    # 创建文件处理器
    log_file = os.path.join(log_dir, 'collectip_spider.log')
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
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
scrapy_logger.setLevel(logging.INFO)  # 设置为INFO以显示更多信息
scrapy_logger.propagate = False  # 防止日志传播到父级记录器

# 导入Django设置和模型
try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CollectIp.settings')
    django.setup()
except Exception as e:
    logger.error(f"Django设置失败: {e}")

# 导入自定义项目
try:
    from crawl_ip.items import IpItem
except ImportError:
    logger.error("无法导入Items，尝试绝对导入")
    from ip_operator.crawl_ip.crawl_ip.crawl_ip.items import IpItem

class CollectipSpider(scrapy.Spider):
    name = "collectip"
    allowed_domains = ["freeproxylist.org"]
    start_urls = ["https://freeproxylist.org/en/free-proxy-list.htm"]
    
    # 自定义设置，确保与douban_spider一致
    custom_settings = {
        'LOG_LEVEL': 'INFO',
        'PROXY_DEBUG': True,  # 明确启用代理调试
        'UA_DEBUG': True,     # 明确启用UA调试
    }
    
    def __init__(self, *args, **kwargs):
        super(CollectipSpider, self).__init__(*args, **kwargs)
        logger.info("【调试】CollectIP爬虫初始化，将使用代理中间件和UA中间件")
        
        # 在爬虫初始化时获取验证码最大重试次数（避免异步上下文问题）
        self.captcha_max_retries = 5  # 默认值
        try:
            # 导入Django设置
            from django.db import models
            from django.conf import settings
            import django
            import os
            import logging
            logger = logging.getLogger(__name__)
            
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CollectIp.settings')
            django.setup()
            
            # 获取ProxySettings模型
            try:
                from index.models import ProxySettings
                settings_obj = ProxySettings.objects.first()
                if settings_obj and hasattr(settings_obj, 'captcha_retries'):
                    self.captcha_max_retries = settings_obj.captcha_retries
                    logger.info(f"从数据库获取验证码最大重试次数: {self.captcha_max_retries}")
                    logger.info(f"从数据库获取验证码最大重试次数: {self.captcha_max_retries}")
                else:
                    logger.info("未找到验证码重试设置，使用默认值: 5")
                    logger.warning("未找到验证码重试设置，使用默认值: 5")
            except Exception as e:
                logger.info(f"获取数据库设置时出错: {e}")
                logger.error(f"获取数据库设置时出错: {e}")
        except Exception as e:
            logger.info(f"导入Django设置时出错: {e}")
            
        logger.info(f"验证码识别将使用最大重试次数: {self.captcha_max_retries}")

    def parse(self, response):
        options = Options()
        # 设置请求头
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': 'https://freeproxylist.org',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        }
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument(f'user-agent={headers["User-Agent"]}')
        options.add_argument(f'referer={headers["Referer"]}')
        options.add_argument(f'accept-language={headers["Accept-Language"]}')

        # 增加无头模式的稳定性设置
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')  # 设置窗口大小
        
        # 添加不显示infobars和自动化控制提示
        options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)

        url = 'https://freeproxylist.org/en/free-proxy-list.htm'
        driver = None
        
        try:
            # 自动下载和配置 ChromeDriver
            try:
            driver_path = ChromeDriverManager().install()
        except ValueError as e:
                logger.warning(f"ChromeDriver自动安装失败: {e}，使用备用路径")
            driver_path = r'D:\chorme_download\chromedriver-win32\chromedriver.exe'
                
        # 创建 Service 对象，传入 ChromeDriver 的路径
        service = Service(driver_path)

        # 创建 Chrome 对象时，传入 service 和 options 对象
        driver = Chrome(service=service, options=options)
        driver.get(url)

            # 设置页面加载超时
            driver.set_page_load_timeout(30)
            
            # 使用显式等待来确保页面加载完成
            wait = WebDriverWait(driver, 20)  # 增加等待时间
            
            # 等待下拉框加载完成
            logger.info("等待下拉框加载完成...")
            select_elem_free = wait.until(
                EC.presence_of_element_located((By.ID, 'select9'))
            )

        # 创建 Select 对象
        select = Select(select_elem_free)

        # 通过文本内容选择选项
        select.select_by_visible_text('free proxy servers')
            logger.info("已选择 'free proxy servers' 选项")

            # 给页面一些时间响应选择操作
            time.sleep(2)

            # 获取并处理验证码
            logger.info("开始验证码处理...")
            retry_count = 0
            success = False
            
            while retry_count < self.captcha_max_retries and not success:
                retry_count += 1
                try:
                    # 等待验证码图片加载
                    code_img_xpath = '//*[@id="tbl_filter"]/tbody/tr[2]/td/table/tbody/tr[1]/td[3]/div/img'
                    wait.until(EC.visibility_of_element_located((By.XPATH, code_img_xpath)))
                    
                    # 获取验证码文本
        code = self.get_captcha_text(driver)
                    logger.info(f"识别的验证码: {code}")
                    
                    # 等待验证码输入框
                    code_input = wait.until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="code"]'))
                    )
                    code_input.clear()
        code_input.send_keys(code)

                    # 查找并点击提交按钮
                    submit_tag = wait.until(
                        EC.element_to_be_clickable((By.XPATH, '//*[@id="filter"]'))
                    )
        submit_tag.click()
                    
                    # 等待页面加载结果
                    time.sleep(3)
                    
                    # 等待数据表格加载
                    wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="proxytable"]')))
                    
        # 检查验证码是否有效
                    try:
                        # 使用新的等待实例和查询来获取第一行数据
                        first_tr = wait.until(
                            EC.presence_of_element_located((By.XPATH, '//*[@id="proxytable"]/tbody/tr[2]'))
                        )
        first_server = first_tr.find_elements(By.XPATH, './/td')[1].text
                        
                        if '*' not in first_server:
                            logger.info("验证码验证成功")
                            success = True
                        else:
                            logger.warning(f"验证码未通过，第 {retry_count} 次尝试")
                            # 重新加载页面以重置状态
                            if retry_count < self.captcha_max_retries:
                                driver.refresh()
                                time.sleep(2)
                    except (StaleElementReferenceException, TimeoutException) as e:
                        logger.warning(f"检查验证码结果时出错: {e}，重试...")
                        driver.refresh()
                        time.sleep(2)
                
                except Exception as e:
                    logger.error(f"尝试验证码识别过程中出错: {e}")
                    if retry_count < self.captcha_max_retries:
                        logger.info("刷新页面重试...")
                        driver.refresh()
                        time.sleep(2)
            
            if not success:
                logger.error("验证码处理失败，已达到最大重试次数")
                return
                
            # 获取总页数
            logger.info("获取分页信息...")
            try:
                # 使用更可靠的等待和查询
                pages_element = wait.until(
                    EC.presence_of_element_located((By.XPATH, '(//*[@id="container"]/table/tbody/tr[4]/td/div/div/a)[last()]'))
                )
                pages = int(pages_element.text)
                logger.info(f"总页数: {pages}")
            except Exception as e:
                logger.error(f"获取页数失败: {e}")
                pages = 1  # 默认至少有一页
                
            # 处理每一页数据
            for p in range(1, min(pages + 1, 5)):  # 限制最多爬取5页，避免耗时过长
                logger.info(f"处理第 {p} 页...")
                
                try:
                    # 每次刷新表格数据前等待
                    wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="proxytable"]/tbody/tr')))
                    
                    # 获取表格行
            trs = driver.find_elements(By.XPATH, '//*[@id="proxytable"]/tbody/tr')
                    
                    if len(trs) <= 1:
                        logger.warning(f"第 {p} 页没有找到数据行")
                        continue
                        
                    logger.info(f"找到 {len(trs) - 1} 行数据")
                    
                    # 处理每一行数据
            for i, tr in enumerate(trs[1:]):
                        try:
                td_list = tr.find_elements(By.XPATH, './/td')  # td合集
                            
                            if len(td_list) < 12:  # 确保有足够的列
                                logger.warning(f"行 {i+1} 列数不足，跳过")
                                continue
                                
                item = IpItem()

                            # 使用更安全的方式提取数据
                            server = td_list[1].text if len(td_list) > 1 else ""
                            ping = td_list[2].text if len(td_list) > 2 else ""
                            speed = td_list[3].text if len(td_list) > 3 else ""
                            uptime1 = td_list[4].text if len(td_list) > 4 else ""
                            uptime2 = td_list[5].text if len(td_list) > 5 else ""
                            type_data = td_list[6].text if len(td_list) > 6 else ""
                            country = td_list[7].text if len(td_list) > 7 else ""
                            
                            # 使用 try-except 处理可能的错误
                            try:
                                ssl_elem = td_list[8].find_elements(By.TAG_NAME, 'div')[0].find_elements(By.TAG_NAME, 'img')[0]
                                ssl = ssl_elem.get_attribute('title')
                            except:
                                ssl = "N/A"
                                
                            try:
                                conn_elem = td_list[9].find_elements(By.TAG_NAME, 'div')[0].find_elements(By.TAG_NAME, 'img')[0]
                                conn = conn_elem.get_attribute('title')
                            except:
                                conn = "N/A"
                                
                            try:
                                post_elem = td_list[10].find_elements(By.TAG_NAME, 'div')[0].find_elements(By.TAG_NAME, 'img')[0]
                                post = post_elem.get_attribute('title')
                            except:
                                post = "N/A"
                                
                            try:
                last_work_time = td_list[11].find_elements(By.TAG_NAME, 'div')[0].get_attribute('title')
                            except:
                                last_work_time = "N/A"

                item['server'] = server
                            
                            # 清洗ping数据，将非数字值转换为None
                            if ping == '?' or not ping or not ping.replace('.', '').isdigit():
                                item['ping'] = None
                            else:
                                try:
                                    item['ping'] = float(ping)
                                except ValueError:
                                    item['ping'] = None
                            
                            # 清洗speed数据，将非数字值转换为None
                            if speed == '?' or not speed or not speed.replace('.', '').isdigit():
                                item['speed'] = None
                            else:
                                try:
                                    item['speed'] = float(speed)
                                except ValueError:
                                    item['speed'] = None
                                    
                            # 其他字段正常赋值
                item['uptime1'] = uptime1
                item['uptime2'] = uptime2
                item['type_data'] = type_data
                item['country'] = country
                item['ssl'] = ssl
                item['conn'] = conn
                item['post'] = post
                item['last_work_time'] = last_work_time
                            
                            # 产生项目
                yield item

                        except StaleElementReferenceException:
                            logger.warning(f"在处理第 {p} 页的第 {i+1} 行时遇到过时元素引用异常，重新获取")
                            # 不重试，直接继续下一行
                            continue
                        except Exception as e:
                            logger.error(f"处理第 {p} 页的第 {i+1} 行时出错: {e}")
                            continue
                
                    # 如果有多页，点击下一页
                    if p < min(pages, 4):  # 如果不是最后一页（或第4页）
                        try:
                            # 使用更可靠的 XPath 定位下一页按钮
                            next_page_xpath = f'//*[@id="container"]/table/tbody/tr[4]/td/div/div/a[{p+1}]'
                            next_page = wait.until(
                                EC.element_to_be_clickable((By.XPATH, next_page_xpath))
                            )
                            next_page.click()
                            
                            # 等待页面加载
                            time.sleep(3)
                            
                            # 确认新页面已加载
                            wait.until(EC.staleness_of(trs[0]))
                            wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="proxytable"]/tbody/tr')))
                        except Exception as e:
                            logger.error(f"点击下一页时出错: {e}")
                            break
                
                except StaleElementReferenceException:
                    logger.warning(f"处理第 {p} 页时遇到过时元素引用异常，尝试重新获取元素")
                    # 等待页面刷新
                    time.sleep(2)
                    continue
                except Exception as e:
                    logger.error(f"处理第 {p} 页时出错: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"爬取过程中出错: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
        finally:
            # 确保无论如何都关闭浏览器
            if driver:
                logger.info("关闭Chrome浏览器")
                try:
        driver.quit()
                except Exception as e:
                    logger.error(f"关闭浏览器时出错: {e}")

    def get_captcha_text(self, driver):
        """获取验证码文本"""
        try:
            # 使用显式等待确保验证码图片已加载
            wait = WebDriverWait(driver, 10)
            img_element = wait.until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="tbl_filter"]/tbody/tr[2]/td/table/tbody/tr[1]/td[3]/div/img'))
            )
            
            # 等待一小段时间确保图片完全加载
            time.sleep(1)
        
        # 获取验证码图片的base64数据
        img_base64 = driver.execute_script("""
            var ele = arguments[0];
            var cnv = document.createElement('canvas');
            cnv.width = ele.width;
            cnv.height = ele.height;
            cnv.getContext('2d').drawImage(ele, 0, 0);
            return cnv.toDataURL('image/jpeg').substring(22);
        """, img_element)
        
        # 将base64转换为bytes
        img_bytes = base64.b64decode(img_base64)
        
        # 使用ddddocr识别验证码
        ocr = DdddOcr(show_ad=False)
        result = ocr.classification(img_bytes)
            
            # 记录结果
            logger.info(f"验证码识别结果: {result}")
            
        return result
        except Exception as e:
            logger.error(f"获取验证码文本时出错: {e}")
            return ""

    def test_captcha_recognition(self):
        """
        测试验证码识别功能
        """
        options = Options()
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
            'Referer': 'https://freeproxylist.org',
            'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        }
        options.add_argument('--disable-gpu')
        options.add_argument(f'user-agent={headers["User-Agent"]}')
        options.add_argument(f'referer={headers["Referer"]}')
        options.add_argument(f'accept-language={headers["Accept-Language"]}')
        
        # 确保不分离浏览器进程
        options.add_experimental_option('detach', False)

        # 增加退出时清理所有相关进程的选项
        options.add_argument("--remote-debugging-port=0")
        options.add_argument("--no-sandbox")
        
        # 添加不显示infobars和自动化控制提示
        options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)

        # 明确初始化driver为None
        driver = None
        self.test_driver = None  # 在Spider实例上存储driver引用，便于清理
        
        try:
        try:
            driver_path = ChromeDriverManager().install()
        except ValueError:
            driver_path = r'D:\chorme_download\chromedriver-win32\chromedriver.exe'

        service = Service(driver_path)
        driver = Chrome(service=service, options=options)
            self.test_driver = driver  # 保存引用到Spider实例

            # 访问目标网页
            driver.get("https://freeproxylist.org/en/free-proxy-list.htm")
            time.sleep(2)  # 等待页面加载

            # 测试验证码识别
            successful_test = False
            for i in range(3):  # 测试3次
                logger.info(f"\n开始第{i + 1}次测试:")
                code = self.get_captcha_text(driver)
                logger.info(f"识别结果: {code}")

                # 尝试输入验证码
                code_input = driver.find_element(By.XPATH, '//*[@id="code"]')
                code_input.clear()  # 清除之前的输入
                code_input.send_keys(code)

                # 点击提交按钮
                submit_tag = driver.find_element(By.XPATH, '// *[@id="filter"]')
                submit_tag.click()

                time.sleep(2)  # 等待结果

                # 检查是否成功（这里需要根据实际页面响应来判断）
                try:
                    # 尝试获取数据表格，如果能获取到说明验证码正确
                    driver.find_element(By.XPATH, '//*[@id="proxytable"]')
                    logger.info("验证码识别成功！")
                    successful_test = True
                    break
                except:
                    logger.info("验证码可能识别错误，将重试")
                    # 刷新页面重试
                    driver.refresh()
                    time.sleep(2)
                    
            if not successful_test:
                logger.info("所有测试都失败，验证码识别功能可能有问题")

        except Exception as e:
            logger.info(f"测试过程中出错: {e}")
            import traceback
            traceback.logger.info_exc()

        finally:
            # 确保无论如何都关闭浏览器
            if driver:
                logger.info("关闭Chrome浏览器")
                try:
                    driver.quit()
                    self.test_driver = None  # 清除引用
                    
                    # 添加额外的进程清理
                    import os
                    import signal
                    import platform
                    
                    try:
                        # 尝试使用psutil进行更彻底的清理
                        import psutil
                        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                            try:
                                # 如果是测试期间创建的Chrome进程，尝试终止它
                                if 'chrome' in proc.name().lower():
                                    logger.info(f"尝试终止可能的Chrome残留进程: {proc.pid}")
                                    if platform.system() == 'Windows':
                                        os.kill(proc.pid, signal.SIGTERM)
                                    else:
                                        # Linux系统下的处理
                                        logger.info(f"在Linux系统下终止Chrome进程: {proc.pid}")
                                        # 首先尝试正常终止
                                        os.kill(proc.pid, signal.SIGTERM)
                                        # 给进程一些时间来正常关闭
                                        time.sleep(0.5)
                                        # 检查进程是否还存在
                                        if psutil.pid_exists(proc.pid):
                                            logger.info(f"进程 {proc.pid} 没有响应SIGTERM，尝试SIGKILL")
                                            os.kill(proc.pid, signal.SIGKILL)
                                        
                                        # 对于Linux系统，还可以使用命令行工具进行额外清理
                                        try:
                                            import subprocess
                                            # 查找并杀死所有chromedriver进程
                                            subprocess.run("pkill -f chromedriver", shell=True)
                                            # 查找并杀死所有zombie状态的chrome相关进程
                                            subprocess.run("ps -ef | grep chrome | grep defunct | awk '{logger.info $2}' | xargs -r kill -9", shell=True)
                                        except Exception as e:
                                            logger.info(f"执行Linux命令行清理时出错: {e}")
                            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as e:
                                logger.info(f"处理进程时出错: {e}")
                    except ImportError:
                        logger.info("psutil不可用，无法进行额外的进程清理")
                        # 在Linux系统下尝试使用命令行工具进行清理
                        if platform.system() != 'Windows':
                            try:
                                import subprocess
                                logger.info("尝试使用Linux命令行工具清理Chrome进程")
                                subprocess.run("pkill -f chrome", shell=True)
                                subprocess.run("pkill -f chromedriver", shell=True)
                            except Exception as e:
                                logger.info(f"使用命令行工具清理时出错: {e}")
                        
                except Exception as e:
                    logger.info(f"关闭浏览器时出错: {e}")

    def closed(self, reason):
        """Spider关闭时的清理操作，确保所有WebDriver实例都被关闭"""
        logger.warning(f"爬虫正在关闭: {reason}")
        
        # 尝试清理可能存在的WebDriver实例
        driver_attrs = [attr for attr in dir(self) if attr.endswith('driver') and getattr(self, attr) is not None]
        for attr in driver_attrs:
            try:
                driver = getattr(self, attr)
                if hasattr(driver, 'quit'):
                    logger.info(f"关闭WebDriver实例: {attr}")
            driver.quit()
            except Exception as e:
                logger.error(f"关闭WebDriver实例 {attr} 时出错: {e}")
        
        # 额外的清理操作
        try:
            # 使用psutil查找和终止可能的残留Chrome进程
            import psutil
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if 'chrome' in proc.name().lower() and 'webdriver' in ' '.join(proc.cmdline()).lower():
                        logger.warning(f"尝试终止残留的Chrome WebDriver进程: {proc.pid}")
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except ImportError:
            logger.warning("psutil不可用，无法清理残留的Chrome进程")
            
        logger.warning("爬虫关闭完成")

    def parse_result(self, response):
        """解析最终结果页面并保存IP数据"""
        logger.info("开始解析结果页面...")
        logger.info(f"使用验证码最大重试次数: {self.captcha_max_retries}")
        
        # 获取验证通过后的结果数据
        # ... existing code ...

if __name__ == "__main__":
    # 创建爬虫实例并测试验证码识别
    spider = CollectipSpider()
    spider.test_captcha_recognition()