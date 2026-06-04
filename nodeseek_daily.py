# -- coding: utf-8 --
"""
Copyright (c) 2024 [Hosea]
Licensed under the MIT License.
See LICENSE file in the project root for full license information.
"""
import os
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
import time
import traceback
import undetected_chromedriver as uc
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

# ================= 通知模块 =================
# 尝试导入青龙面板自带的通知模块
try:
    from notify import send
except ImportError:
    def send(title, content):
        print(f"\n[本地运行提示] 未找到青龙 notify.py 文件，跳过通知发送。")
        print(f"通知标题: {title}")
        print(f"通知内容:\n{content}")

# 收集推送到手机的通知内容
notify_content = []

def ql_log(msg):
    """同时打印日志并加入通知列表"""
    print(msg)
    notify_content.append(msg)
# ==========================================

ns_random = os.environ.get("NS_RANDOM","false")
cookie = os.environ.get("NS_COOKIE") or os.environ.get("COOKIE")
headless = os.environ.get("HEADLESS", "true").lower() == "true"
ns_comment_enable = os.environ.get("NS_COMMENT", "true").lower() == "true"

# ✨ 新增：尝试读取环境变量中的用户名
ns_user = os.environ.get("NS_USER", "")

randomInputStr = [
    "绑定",
    "帮顶",
    "好价祝早出",
    "帮顶了",
    "不错，顶一下",
    "价格挺合适的",
    "插眼看看",
    "前排支持一下"
]

def click_sign_icon(driver):
    try:
        print("开始查找签到图标...")
        sign_icon = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//span[@title='签到']"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", sign_icon)
        time.sleep(0.5)
        
        try:
            sign_icon.click()
            ql_log("✅ 签到图标点击成功")
        except Exception as click_error:
            driver.execute_script("arguments[0].click();", sign_icon)
            ql_log("✅ 签到图标点击成功 (JS强制点击)")
        
        time.sleep(5)
        
        try:
            if ns_random == "true":
                click_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '试试手气')]"))
                )
                click_button.click()
                ql_log("🎁 试试手气点击成功")
            else:
                click_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '鸡腿 x 5')]"))
                )
                click_button.click()
                ql_log("🍗 鸡腿x5 领取成功")
        except Exception as lucky_error:
            ql_log("⚠️ 试试手气/鸡腿领取失败或已签到过")
            
        return True
        
    except Exception as e:
        ql_log("❌ 签到过程中出错，可能是Cookie失效或已被拦截")
        return False

def setup_driver_and_cookies():
    try:
        if not cookie:
            ql_log("❌ 未找到 NS_COOKIE 环境变量配置")
            return None
            
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        if headless:
            options.add_argument('--headless')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = uc.Chrome(
            options=options,
            driver_executable_path='/usr/bin/chromedriver',
            browser_executable_path='/usr/bin/chromium-browser'
        )
        
        if headless:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.set_window_size(1920, 1080)
        
        driver.get('https://www.nodeseek.com')
        time.sleep(5)
        
        for cookie_item in cookie.split(';'):
            try:
                name, value = cookie_item.strip().split('=', 1)
                driver.add_cookie({
                    'name': name, 
                    'value': value, 
                    'domain': '.nodeseek.com',
                    'path': '/'
                })
            except Exception as e:
                continue
        
        driver.refresh()
        time.sleep(5) 
        return driver
        
    except Exception as e:
        ql_log(f"❌ 浏览器初始化失败: {str(e)}")
        return None

def nodeseek_comment(driver):
    try:
        target_url = 'https://www.nodeseek.com/categories/trade'
        driver.get(target_url)
        time.sleep(5)
        
        posts = WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.post-list-item'))
        )
        
        valid_posts = [post for post in posts if not post.find_elements(By.CSS_SELECTOR, '.pined')]
        selected_posts = random.sample(valid_posts, min(20, len(valid_posts)))
        
        selected_urls = []
        for post in selected_posts:
            try:
                post_link = post.find_element(By.CSS_SELECTOR, '.post-title a')
                selected_urls.append(post_link.get_attribute('href'))
            except:
                continue
        
        is_chicken_leg = False
        comments_count = 0
        
        for i, post_url in enumerate(selected_urls):
            try:
                driver.get(post_url)
                
                if is_chicken_leg is False:
                    is_chicken_leg = click_chicken_leg(driver)
                    if is_chicken_leg:
                        ql_log("🍗 成功给随机帖子加了一个鸡腿")
                
                if ns_comment_enable:
                    editor = WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, '.CodeMirror'))
                    )
                    editor.click()
                    time.sleep(0.5)
                    input_text = random.choice(randomInputStr)

                    actions = ActionChains(driver)
                    for char in input_text:
                        actions.send_keys(char)
                        actions.pause(random.uniform(0.1, 0.3))
                    actions.perform()
                    
                    time.sleep(2)
                    
                    submit_button = WebDriverWait(driver, 30).until(
                     EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'submit') and contains(@class, 'btn') and contains(text(), '发布评论')]"))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
                    time.sleep(0.5)
                    driver.execute_script("arguments[0].click();", submit_button)
                    
                    comments_count += 1
                else:
                    if is_chicken_leg is True:
                        ql_log("💡 评论已关闭且鸡腿已送出，提前结束逛帖任务")
                        break 
                
                time.sleep(random.uniform(2,5))
                
            except Exception as e:
                continue
                
        if ns_comment_enable:
            ql_log(f"💬 自动评论任务完成，共水了 {comments_count} 个帖子")
                
    except Exception as e:
        ql_log("❌ NodeSeek 逛帖/评论过程出现异常")

def click_chicken_leg(driver):
    try:
        chicken_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@class="nsk-post"]//div[@title="加鸡腿"][1]'))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", chicken_btn)
        time.sleep(0.5)
        chicken_btn.click()
        
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.msc-confirm'))
        )
        
        try:
            error_title = driver.find_element(By.XPATH, "//h3[contains(text(), '该评论创建于7天前')]")
            if error_title:
                ok_btn = driver.find_element(By.CSS_SELECTOR, '.msc-confirm .msc-ok')
                ok_btn.click()
                return False
        except:
            ok_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.msc-confirm .msc-ok'))
            )
            ok_btn.click()
            
        WebDriverWait(driver, 5).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.msc-overlay'))
        )
        time.sleep(2)
        return True
        
    except Exception as e:
        return False

if __name__ == "__main__":
    global_user = ns_user
    display_name = f"[{global_user}] " if global_user else ""
    ql_log(f"=== NodeSeek {display_name}自动化签到报告 ===")
    
    driver = setup_driver_and_cookies()
    if driver:
        # ✨ 自动抓取兜底：如果你没有设置环境变量，尝试从顶部导航栏把你的名字薅下来
        if not global_user:
            try:
                # 寻找页面上第一个空间链接（通常就是顶部登录后的用户头像按钮）
                user_el = driver.find_element(By.XPATH, "(//a[contains(@href, '/space/')])[1]")
                if user_el and user_el.text:
                    global_user = user_el.text.strip()
                    ql_log(f"💡 自动抓取到用户名: {global_user}")
            except:
                pass

        nodeseek_comment(driver)
        click_sign_icon(driver)
        ql_log("✅ 脚本所有任务执行完毕")
        
        try:
            driver.quit()
        except:
            pass
    
    # 汇总消息并通过青龙通知发送（标题带上用户名）
    title = f"NodeSeek[{global_user}] 每日签到" if global_user else "NodeSeek 每日签到"
    final_message = "\n".join(notify_content)
    send(title, final_message)
