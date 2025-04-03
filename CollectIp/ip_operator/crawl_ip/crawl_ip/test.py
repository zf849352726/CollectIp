"""
#!/usr/bin/env python
# -*- coding:utf-8 -*-
@Project : crawl_ip
@File : test.py
@Author : 帅张张
@Time : 2025/3/22 17:10

"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import json
import re
import os
import random
import string
from urllib.parse import urlparse, parse_qs
from webdriver_manager.chrome import ChromeDriverManager


def generate_wechat_cookie():
    """生成微信请求所需的随机cookie值"""
    # 基础时间戳：最近30天内的随机时间
    now = int(time.time())
    random_days = random.randint(1, 30)
    random_timestamp = now - (random_days * 24 * 60 * 60)
    
    # 生成随机bid值（11位字母数字组合）
    bid = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(11))
    
    # 生成随机城市代码（中国常见城市）
    city_codes = ['110100', '310100', '440100', '510100', '330100', '320100', '420100', '430100', '610100', '500100']
    location_code = random.choice(city_codes)
    
    # 生成随机推送消息数量
    push_count = random.randint(0, 5)
    
    # 生成随机UTM参数
    utm_sources = ['weixin', 'wechat', 'mp', 'official', 'account']
    utm_source = random.choice(utm_sources)
    utm_medium = random.choice(['organic', 'social', 'direct'])
    utm_campaign = random.choice(['spring', 'summer', 'autumn', 'winter', 'new_year'])
    
    # 生成随机Google Analytics ID
    ga_id = f"GA1.1.{random.randint(1000000000, 9999999999)}.{random.randint(1000000000, 9999999999)}"
    
    # 微信cookie相关的随机值
    wxuin = ''.join(random.choice('0123456789') for _ in range(14))
    pgv_pvid = ''.join(random.choice('0123456789') for _ in range(10))
    uuid = ''.join(random.choice('0123456789abcdef') for _ in range(32))
    bizuin = '3964761215'  # 固定值，公众号ID
    
    # 生成随机sig值（模拟签名）
    sig_chars = string.ascii_lowercase + string.digits
    sig = ''.join(random.choice(sig_chars) for _ in range(64))
    
    # 生成随机slave_sid值
    slave_sid_chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
    slave_sid = ''.join(random.choice(slave_sid_chars) for _ in range(128))
    
    # 构建完整cookie字符串，结构与真实微信cookie一致
    cookie_parts = [
        f"appmsglist_action_{bizuin}=card",
        f"wxuin={wxuin}",
        f"cert={bid}",
        f"mm_lang=zh_CN",
        f"pgv_info=ssid=s{random.randint(1000000000, 9999999999)}",
        f"pgv_pvid={pgv_pvid}",
        f"ts_uid={random.randint(1000000000, 9999999999)}",
        f"rewardsn=",
        f"wxtokenkey={random.randint(100, 999)}",
        f"_qpsvr_localtk={random.random()}",
        f"RK={''.join(random.choice(string.ascii_letters) for _ in range(10))}",
        f"ptcz={''.join(random.choice('0123456789abcdef') for _ in range(64))}",
        f"media_ticket={''.join(random.choice('0123456789abcdef') for _ in range(32))}",
        f"media_ticket_id={bizuin}",
        f"ptui_loginuin={random.randint(100000000, 999999999)}",
        f"personAgree_{bizuin}=true",
        f"qq_domain_video_guid_verify={''.join(random.choice('0123456789abcdef') for _ in range(16))}",
        f"_qimei_uuid42={''.join(random.choice('0123456789abcdef') for _ in range(32))}",
        f"vversion_name=8.2.95",
        f"video_omgid={''.join(random.choice('0123456789abcdef') for _ in range(16))}",
        f"_qimei_fingerprint={''.join(random.choice('0123456789abcdef') for _ in range(32))}",
        f"_qimei_h38={''.join(random.choice('0123456789abcdef') for _ in range(32))}",
        f"_qimei_q32={''.join(random.choice('0123456789abcdef') for _ in range(32))}",
        f"_qimei_q36={''.join(random.choice('0123456789abcdef') for _ in range(32))}",
        f"__root_domain_v=.weixin.qq.com",
        f"_qddaz=QD.{random.randint(100000000000, 999999999999)}",
        f"sig={sig}",
        f"mmad_session={''.join(random.choice('0123456789abcdef') for _ in range(64))}",
        f"ua_id={''.join(random.choice(string.ascii_letters + string.digits + '=') for _ in range(24))}",
        f"pac_uid=0_{''.join(random.choice(string.ascii_letters) for _ in range(10))}",
        f"_clck={bizuin}|1|fup|0",
        f"noticeLoginFlag=1",
        f"remember_acct={random.randint(1000000000, 9999999999)}%40qq.com",
        f"uuid={uuid}",
        f"rand_info=CAESIP8MlEpSLiqgBVmefntp/yH6Zk+0XYa53JqnjZvbwRpe",
        f"slave_bizuin={bizuin}",
        f"data_bizuin={bizuin}",
        f"bizuin={bizuin}",
        f"data_ticket={''.join(random.choice(string.ascii_letters + string.digits + '/+') for _ in range(64))}",
        f"slave_sid={slave_sid}",
        f"slave_user=gh_{''.join(random.choice('0123456789abcdef') for _ in range(10))}",
        f"xid={''.join(random.choice('0123456789abcdef') for _ in range(32))}",
        f"_clck={bizuin}|1|fuq|0",
        f"_clsk={random.randint(1000000000000, 9999999999999)}|{int(time.time()*1000)}|1|1|mp.weixin.qq.com/weheat-agent/payload/record"
    ]
    
    # 随机决定是否包含一些可选cookie项
    if random.random() < 0.7:  # 70%的概率包含这些cookie
        cookie_parts.extend([
            f"push_count={push_count}",
            f"push_time={random_timestamp}",
            f"utm_source={utm_source}",
            f"utm_medium={utm_medium}",
            f"utm_campaign={utm_campaign}",
            f"_ga={ga_id}",
            f"_ga_XXXXXXXX={ga_id}",
            f"location_code={location_code}"
        ])
    
    # 将所有部分组合成最终cookie字符串
    return "; ".join(cookie_parts)

def generate_wechat_headers(path=None, token=None):
    """
    生成微信请求所需的完整请求头
    
    Args:
        path: 请求路径，例如 "/cgi-bin/home?t=home/index&lang=zh_CN&token=483311627"
        token: 微信token，用于构建referer
        
    Returns:
        包含所有必要字段的请求头字典
    """
    # 基础请求头
    headers = {
        "authority": "mp.weixin.qq.com",
        "method": "GET",
        "scheme": "https",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "zh-CN,zh;q=0.9",
        "cache-control": "max-age=0",
        "sec-ch-ua": '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
    }
    
    # 如果提供了path，则添加到请求头中
    if path:
        headers["path"] = path
        
        # 如果提供了token，则构建referer
        if token:
            # 从path中提取基本路径
            base_path = path.split('?')[0]
            headers["referer"] = f"https://mp.weixin.qq.com{base_path}?token={token}"
    
    # 生成随机cookie
    headers["cookie"] = generate_wechat_cookie()
    
    return headers

class WeChatPublicTest:
    """微信公众号登录测试类"""
    
    def __init__(self):
        # 初始化Chrome选项
        chrome_options = Options()
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option('detach', True)
        
        # 设置用户代理
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        chrome_options.add_argument(f'user-agent={user_agent}')

        # 自动下载和配置 ChromeDriver
        try:
            driver_path = ChromeDriverManager().install()
        except ValueError as e:
            driver_path = r'D:\chorme_download\chromedriver-win32\chromedriver.exe'

        # 创建 Service 对象，传入 ChromeDriver 的路径
        service = Service(driver_path)

        # 创建 Chrome 对象时，传入 service 和 options 对象
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        self.token = None
        
    def login(self):
        """使用Selenium模拟登录流程"""
        print("开始模拟登录...")
        try:
            # 访问登录页面
            self.driver.get("https://mp.weixin.qq.com/")
            
            # 等待二维码出现
            qr_code = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "login__type__container__scan__qrcode"))
            )
            print("请扫描二维码登录...")
            
            # 等待登录成功
            while True:
                try:
                    # 检查是否登录成功
                    self.driver.find_element(By.CLASS_NAME, "weui-desktop_name")
                    print("登录成功！")
                    
                    # 获取token
                    current_url = self.driver.current_url
                    self.token = self._extract_token_from_url(current_url)
                    if self.token:
                        print(f"获取到token: {self.token}")
                        return True
                    break
                except NoSuchElementException:
                    time.sleep(1)
                    continue
                    
        except Exception as e:
            print(f"登录过程中出现异常: {e}")
            return False
    
    def _extract_token_from_url(self, url):
        """从URL中提取token参数"""
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        return query_params.get('token', [None])[0]
    
    def get_home_page(self):
        """获取首页内容"""
        try:
            # 访问首页
            url = f"https://mp.weixin.qq.com/cgi-bin/home?t=home/index&lang=zh_CN&token={self.token}"
            self.driver.get(url)
            
            # 等待页面加载完成
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "weui-desktop-account__name"))
            )
            
            # 检查是否有登录超时
            if "请重新登录" in self.driver.page_source:
                print("登录已超时，需要重新登录")
                return False
                
            print("成功获取首页")
            return True
            
        except Exception as e:
            print(f"获取首页时出现异常: {e}")
            return False
    
    def get_published_articles(self, count=10):
        """获取已发布的文章列表"""
        try:
            # 访问已发布文章页面
            url = f"https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count={count}&type=9&lang=zh_CN&token={self.token}"
            self.driver.get(url)
            
            # 等待文章列表加载
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "weui-desktop-mass-media__title"))
            )
            
            # 获取文章列表
            articles = []
            article_elements = self.driver.find_elements(By.CLASS_NAME, "weui-desktop-mass-media__title")
            
            for element in article_elements:
                try:
                    title = element.text
                    link = element.find_element(By.TAG_NAME, "a").get_attribute("href")
                    update_time = element.find_element(By.XPATH, "./following-sibling::div[contains(@class, 'weui-desktop-mass-media__info')]").text
                    
                    articles.append({
                        "title": title,
                        "link": link,
                        "update_time": update_time
                    })
                except Exception as e:
                    print(f"提取文章信息时出错: {e}")
                    continue
            
            print(f"成功获取到 {len(articles)} 条已发布文章")
            return {"app_msg_list": articles}
            
        except Exception as e:
            print(f"获取已发布文章列表时出现异常: {e}")
            return None
    
    def get_material_list(self, count=10):
        """获取素材列表"""
        try:
            # 访问素材列表页面
            url = f"https://mp.weixin.qq.com/cgi-bin/appmsg?action=list_ex&begin=0&count={count}&type=9&lang=zh_CN&token={self.token}"
            self.driver.get(url)
            
            # 等待素材列表加载
            self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "weui-desktop-mass-media__title"))
            )
            
            # 获取素材列表
            materials = []
            material_elements = self.driver.find_elements(By.CLASS_NAME, "weui-desktop-mass-media__title")
            
            for element in material_elements:
                try:
                    title = element.text
                    link = element.find_element(By.TAG_NAME, "a").get_attribute("href")
                    update_time = element.find_element(By.XPATH, "./following-sibling::div[contains(@class, 'weui-desktop-mass-media__info')]").text
                    
                    materials.append({
                        "title": title,
                        "link": link,
                        "update_time": update_time
                    })
                except Exception as e:
                    print(f"提取素材信息时出错: {e}")
                    continue
            
            print(f"成功获取到 {len(materials)} 条素材")
            return {"app_msg_list": materials}
            
        except Exception as e:
            print(f"获取素材列表时出现异常: {e}")
            return None
    
    def close(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()

def main():
    """主函数"""
    print("=" * 50)
    print("微信公众号登录测试开始")
    print("=" * 50)
    
    wechat_test = WeChatPublicTest()
    
    try:
        # 执行登录测试
        login_success = wechat_test.login()
        
        if login_success:
            # 获取首页
            home_success = wechat_test.get_home_page()
            
            if home_success:
                # 获取已发布文章列表
                print("\n尝试获取已发布文章列表...")
                published_articles = wechat_test.get_published_articles(count=5)
                
                if published_articles and 'app_msg_list' in published_articles:
                    articles = published_articles['app_msg_list']
                    print(f"\n成功获取到 {len(articles)} 条已发布文章:")
                    for i, article in enumerate(articles):
                        title = article.get('title', '无标题')
                        link = article.get('link', '无链接')
                        update_time = article.get('update_time', '未知时间')
                        print(f"{i+1}. {title}")
                        print(f"   链接: {link}")
                        print(f"   更新时间: {update_time}")
                        print("-" * 50)
                
                # 获取素材列表
                print("\n尝试获取素材列表...")
                material_data = wechat_test.get_material_list(count=5)
                if material_data:
                    print("素材列表获取成功")
                    materials = material_data.get('app_msg_list', [])
                    print(f"获取到 {len(materials)} 条素材:")
                    for i, material in enumerate(materials):
                        title = material.get('title', '无标题')
                        link = material.get('link', '无链接')
                        update_time = material.get('update_time', '未知时间')
                        print(f"{i+1}. {title}")
                        print(f"   链接: {link}")
                        print(f"   更新时间: {update_time}")
                        print("-" * 50)
    
    except Exception as e:
        print(f"测试过程中出现异常: {e}")
    
    finally:
        # 关闭浏览器
        wechat_test.close()
        print("\n" + "=" * 50)
        print("微信公众号登录测试结束")
        print("=" * 50)

if __name__ == "__main__":
    main()
