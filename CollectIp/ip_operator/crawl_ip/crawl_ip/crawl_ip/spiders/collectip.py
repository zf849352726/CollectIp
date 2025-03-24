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
    logger = setup_logging("collectip_spider")
except ImportError:
    # 如果无法导入，使用基本日志设置
    logger = logging.getLogger("collectip_spider")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("使用基本日志设置，无法导入自定义日志函数")

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

        # 移除detach选项，确保浏览器随脚本关闭
        # options.add_experimental_option('detach', True)
        
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

            # 找到下拉框元素
            select_elem_free = driver.find_element(By.ID, 'select9')

            # 创建 Select 对象
            select = Select(select_elem_free)

            # 通过文本内容选择选项
            select.select_by_visible_text('free proxy servers')

            # 替换手动输入验证码的部分
            code = self.get_captcha_text(driver)
            # 找到验证码文本框
            code_input = driver.find_element(By.XPATH, '//*[@id="code"]')
            code_input.send_keys(code)

            # 提交筛选
            submit_tag = driver.find_element(By.XPATH, '// *[@id="filter"]')
            submit_tag.click()
            # 检查验证码是否有效
            first_tr = driver.find_element(By.XPATH, '//*[@id="proxytable"]/tbody/tr[2]')
            first_server = first_tr.find_elements(By.XPATH, './/td')[1].text
            
            # 如果server中包含*号,说明验证码无效,需要重新获取
            retry_count = 0
            max_retries = 20  # 设置最大重试次数
            while '*' in first_server and retry_count < max_retries:
                retry_count += 1
                logger.info(f"验证码识别失败,第{retry_count}次重试...")
                # 重新获取验证码
                code = self.get_captcha_text(driver)
                # 清空验证码输入框
                code_input = driver.find_element(By.XPATH, '//*[@id="code"]')
                code_input.clear()
                # 输入新验证码
                code_input.send_keys(code)
                # 重新提交
                submit_tag = driver.find_element(By.XPATH, '// *[@id="filter"]')
                submit_tag.click()
                # 重新检查第一行数据
                first_tr = driver.find_element(By.XPATH, '//*[@id="proxytable"]/tbody/tr[2]')
                first_server = first_tr.find_elements(By.XPATH, './/td')[1].text
                # 每10次重试暂停1秒,避免请求过于频繁
                if retry_count % 10 == 0:
                    time.sleep(1)
            
            # 如果达到最大重试次数仍然失败，记录错误并返回
            if retry_count >= max_retries and '*' in first_server:
                logger.error(f"验证码识别失败达到最大重试次数({max_retries})，放弃本次爬取")
                return
                
            logger.info(f"验证码识别成功,共重试{retry_count}次")

            pages = driver.find_element(By.XPATH, '(//*[@id="container"]/table/tbody/tr[4]/td/div/div/a)[last()]').text

            for p in range(1, int(pages)):
                trs = driver.find_elements(By.XPATH, '//*[@id="proxytable"]/tbody/tr')
                for i, tr in enumerate(trs[1:]):
                    td_list = tr.find_elements(By.XPATH, './/td')  # td合集
                    item = IpItem()

                    server = td_list[1].text
                    ping = td_list[2].text
                    speed = td_list[3].text
                    uptime1 = td_list[4].text
                    uptime2 = td_list[5].text
                    type_data = td_list[6].text
                    country = td_list[7].text
                    ssl = td_list[8].find_elements(By.TAG_NAME, 'div')[0].find_elements(By.TAG_NAME, 'img')[0].get_attribute('title')
                    conn = td_list[9].find_elements(By.TAG_NAME, 'div')[0].find_elements(By.TAG_NAME, 'img')[0].get_attribute('title')
                    post = td_list[10].find_elements(By.TAG_NAME, 'div')[0].find_elements(By.TAG_NAME, 'img')[0].get_attribute('title')
                    last_work_time = td_list[11].find_elements(By.TAG_NAME, 'div')[0].get_attribute('title')

                    item['server'] = server
                    # 查数据库 如果ip不存在执行以下代码
                    item['ping'] = ping
                    item['speed'] = speed
                    item['uptime1'] = uptime1
                    item['uptime2'] = uptime2
                    item['type_data'] = type_data
                    item['country'] = country
                    item['ssl'] = ssl
                    item['conn'] = conn
                    item['post'] = post
                    item['last_work_time'] = last_work_time
                    yield item

                # 如果有多页，点击下一页
                if p < int(pages) - 1:  # 确保不是最后一页
                    page_number = driver.find_element(By.XPATH, f'//*[@id="container"]/table/tbody/tr[4]/td/div/div/a[{p}]')
                    page_number.click()
                    time.sleep(1)
                    
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
        # 等待验证码图片元素出现
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="tbl_filter"]/tbody/tr[2]/td/table/tbody/tr[1]/td[3]/div/img'))
        )
        # 找到验证码图片元素
        img_element = driver.find_element(By.XPATH, '//*[@id="tbl_filter"]/tbody/tr[2]/td/table/tbody/tr[1]/td[3]/div/img')  # 请根据实际验证码图片的xpath修改
        
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
        return result

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
                print(f"\n开始第{i + 1}次测试:")
                code = self.get_captcha_text(driver)
                print(f"识别结果: {code}")

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
                    print("验证码识别成功！")
                    successful_test = True
                    break
                except:
                    print("验证码可能识别错误，将重试")
                    # 刷新页面重试
                    driver.refresh()
                    time.sleep(2)
                    
            if not successful_test:
                print("所有测试都失败，验证码识别功能可能有问题")

        except Exception as e:
            print(f"测试过程中出错: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # 确保无论如何都关闭浏览器
            if driver:
                print("关闭Chrome浏览器")
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
                        for proc in psutil.process_iter(['pid', 'name']):
                            try:
                                # 如果是测试期间创建的Chrome进程，尝试终止它
                                if 'chrome' in proc.name().lower():
                                    print(f"尝试终止可能的Chrome残留进程: {proc.pid}")
                                    if platform.system() == 'Windows':
                                        os.kill(proc.pid, signal.SIGTERM)
                                    else:
                                        os.kill(proc.pid, signal.SIGKILL)
                            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                                pass
                    except ImportError:
                        print("psutil不可用，无法进行额外的进程清理")
                        
                except Exception as e:
                    print(f"关闭浏览器时出错: {e}")

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

if __name__ == "__main__":
    # 创建爬虫实例并测试验证码识别
    spider = CollectipSpider()
    spider.test_captcha_recognition()