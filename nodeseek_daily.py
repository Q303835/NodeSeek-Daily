# -*- coding: utf-8 -*-
"""
任务名称
name: NodeSeek签到与评论
定时规则
cron: 25 6 * * *
"""
import os
import re
import random
import time
import traceback
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# 环境变量获取
ns_random = os.environ.get("NS_RANDOM", "false").lower() == "true"
cookie_env = os.environ.get("NS_COOKIE") or os.environ.get("COOKIE")
headless = os.environ.get("HEADLESS", "true").lower() == "true"

randomInputStr = [
    "路过帮顶",
    "帮顶了",
    "不错，顶一下",
    "挺合适的",
    "插眼看看",
    "支持一下"
]

# 全局变量记录执行状态
TASK_STATUS = {
    "sign": "未执行",
    "comment_count": 0,
    "chicken_leg": "未执行"
}

# 全局变量存储用户名
NS_USER = "未知用户"

# ==================== 青龙通知模块引入 ====================
def send_notification(title, content):
    """
    调用青龙面板自带的通知系统
    """
    global NS_USER
    full_title = f"NodeSeek - [{NS_USER}] - {title}"
    print(f"📣 尝试发送通知: [{full_title}] {content}")
    try:
        from notify import send
        send(full_title, content)
        print("✅ 青龙通知发送成功！")
    except ImportError:
        print("⚠️ 未找到青龙 notify.py 模块，如果你在本地运行此脚本，该提示可忽略。")
    except Exception as e:
        print(f"❌ 发送通知时发生异常: {str(e)}")
# ========================================================

def setup_driver_and_cookies():
    """
    初始化无头浏览器并注入 Cookie
    """
    try:
        if not cookie_env:
            msg = "❌ 未找到 NS_COOKIE 环境变量配置"
            print(msg)
            send_notification("配置错误", msg)
            return None
            
        print("🌐 开始初始化浏览器...")
        options = uc.ChromeOptions()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        if headless:
            print("👁️ 启用无头模式...")
            options.add_argument('--headless')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        print("🚀 正在启动 Chrome...")
        driver = uc.Chrome(
            options=options,
            driver_executable_path='/usr/bin/chromedriver',
            browser_executable_path='/usr/bin/chromium-browser'
        )
        
        if headless:
            driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            driver.set_window_size(1920, 1080)
        
        print("✅ Chrome 启动成功！")
        print("🔑 正在注入 Cookie...")
        
        driver.get('https://www.nodeseek.com/robots.txt')
        time.sleep(3)
        
        single_cookie = cookie_env.split('\n')[0].strip()
        
        for cookie_item in single_cookie.split(';'):
            if '=' in cookie_item:
                try:
                    name, value = cookie_item.strip().split('=', 1)
                    driver.add_cookie({
                        'name': name, 
                        'value': value, 
                        'domain': '.nodeseek.com',
                        'path': '/'
                    })
                except Exception as e:
                    print(f"⚠️ 设置单条 cookie 出错: {str(e)}")
                    continue
        
        print("🔄 刷新页面使登录态生效并获取用户信息...")
        driver.get('https://www.nodeseek.com/')
        time.sleep(4) 
        
        if '登录' in driver.page_source and '注册' in driver.page_source:
             print("⚠️ 警告：似乎未成功登录，Cookie 可能已过期。")
        else:
             global NS_USER
             try:
                 # 等待包含用户名的外层区域渲染出来
                 WebDriverWait(driver, 10).until(
                     EC.presence_of_element_located((By.CSS_SELECTOR, "a.Username, a[href^='/space/'][title], img[alt][class*='avatar']"))
                 )
                 
                 # 终极方案：直接用 JS 在页面内寻找目标属性，防止 Selenium 的文本可见性拦截
                 js_extract_user = """
                 var el1 = document.querySelector('a.Username');
                 if (el1 && el1.innerText.trim()) return el1.innerText.trim();
                 
                 var el2 = document.querySelector('a[href^="/space/"][title]');
                 if (el2 && el2.getAttribute('title').trim()) return el2.getAttribute('title').trim();
                 
                 var el3 = document.querySelector('img[alt][class*="avatar"]');
                 if (el3 && el3.getAttribute('alt').trim()) return el3.getAttribute('alt').trim();
                 
                 return null;
                 """
                 
                 extracted_name = driver.execute_script(js_extract_user)
                 
                 if extracted_name:
                     NS_USER = extracted_name
                     print(f"👤 成功锁定当前登录用户: {NS_USER}")
                 else:
                     raise Exception("JS 未能在节点中提取到有效文本")
                     
             except Exception as e:
                 # 备用方案：兜底正则
                 match = re.search(r'"username":"([^"]+)"', driver.page_source)
                 if match:
                     NS_USER = match.group(1)
                     print(f"👤 成功锁定当前登录用户(备用正则): {NS_USER}")
                 else:
                     print(f"⚠️ 获取用户名时发生异常 (不影响核心任务): {str(e)}")
             
        return driver
        
    except Exception as e:
        print(f"💥 设置浏览器和 Cookie 时出错: {str(e)}")
        traceback.print_exc()
        send_notification("环境异常", f"环境初始化出错: {str(e)}")
        return None

def click_sign_icon(driver):
    global TASK_STATUS
    try:
        print("🔍 开始检查签到状态...")
        driver.get('https://www.nodeseek.com/board')
        time.sleep(5)
        
        page_source = driver.page_source
        
        if any(kw in page_source for kw in ['今日签到获得', '当前排名第', '已经签过到', '你今天已经签过到了']):
            print("🎉 提示：今天已签到，请勿重复签到！")
            TASK_STATUS["sign"] = "今日已签"
            return True
            
        target_text = '试试手气' if ns_random else '鸡腿 x 5'
        print(f"🎯 准备直接点击选项: [{target_text}]")
        
        try:
            click_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(text(), '{target_text}')]"))
            )
            
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", click_button)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", click_button)
            print(f"🏆 成功点击 [{target_text}]！")
            TASK_STATUS["sign"] = "签到成功"
        except Exception as lucky_error:
            print(f"⚠️ 点击奖励按钮失败: {str(lucky_error)}")
            TASK_STATUS["sign"] = "获取奖励失败"
            
        return True
        
    except Exception as e:
        print(f"💥 签到过程中出错: {str(e)}")
        try:
            driver.save_screenshot('ns_sign_exception.png')
        except:
            pass
        TASK_STATUS["sign"] = "签到异常"
        return False

def click_chicken_leg(driver):
    try:
        print("🍗 尝试点击加鸡腿按钮...")
        chicken_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, '//div[@class="nsk-post"]//div[@title="加鸡腿"][1]'))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", chicken_btn)
        time.sleep(1)
        driver.execute_script("arguments[0].click();", chicken_btn)
        print("🖱️ 加鸡腿按钮点击成功")
        
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.msc-confirm'))
        )
        
        try:
            error_title = driver.find_element(By.XPATH, "//h3[contains(text(), '该评论创建于7天前')]")
            if error_title:
                print("⚠️ 该帖子超过7天，无法加鸡腿")
                ok_btn = driver.find_element(By.CSS_SELECTOR, '.msc-confirm .msc-ok')
                driver.execute_script("arguments[0].click();", ok_btn)
                return False
        except:
            ok_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.msc-confirm .msc-ok'))
            )
            driver.execute_script("arguments[0].click();", ok_btn)
            print("✅ 确认加鸡腿成功")
            
        WebDriverWait(driver, 5).until_not(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.msc-overlay'))
        )
        time.sleep(1.5) 
        
        return True
        
    except Exception as e:
        print(f"⚠️ 加鸡腿操作失败或未找到按钮: {str(e)}")
        return False

def nodeseek_comment(driver):
    global TASK_STATUS
    try:
        print("📂 正在访问交易区获取帖子...")
        target_url = 'https://www.nodeseek.com/categories/trade'
        driver.get(target_url)
        time.sleep(4)
        
        posts = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.post-list-item'))
        )
        print(f"📊 成功获取到 {len(posts)} 个帖子")
        
        valid_posts = [post for post in posts if not post.find_elements(By.CSS_SELECTOR, '.pined')]
        if not valid_posts:
            print("⚠️ 未找到有效的非置顶帖子。")
            return
            
        selected_posts = random.sample(valid_posts, min(20, len(valid_posts)))
        selected_urls = []
        for post in selected_posts:
            try:
                post_link = post.find_element(By.CSS_SELECTOR, '.post-title a')
                selected_urls.append(post_link.get_attribute('href'))
            except:
                continue
        
        is_chicken_leg = False
        success_count = 0
        
        for i, post_url in enumerate(selected_urls):
            try:
                print(f"💬 正在处理第 {i+1} 个帖子: {post_url}")
                driver.get(post_url)
                time.sleep(3)
                
                if not is_chicken_leg:
                    is_chicken_leg = click_chicken_leg(driver)
                    if is_chicken_leg:
                        TASK_STATUS["chicken_leg"] = "成功加权"
                
                editor = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.CodeMirror'))
                )
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", editor)
                time.sleep(1)
                
                try:
                    editor.click()
                except:
                    driver.execute_script("arguments[0].click();", editor)
                    
                time.sleep(0.5)
                input_text = random.choice(randomInputStr)

                actions = ActionChains(driver)
                for char in input_text:
                    actions.send_keys(char)
                    actions.pause(random.uniform(0.1, 0.3))
                actions.perform()
                
                time.sleep(2)
                
                submit_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'submit') and contains(@class, 'btn') and contains(text(), '发布评论')]"))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
                time.sleep(1)
                
                try:
                    submit_button.click()
                except:
                    driver.execute_script("arguments[0].click();", submit_button)
                
                print(f"✅ 已在当前帖子完成回复: [{input_text}]")
                success_count += 1
                
                time.sleep(random.uniform(4, 8))
                
                if success_count >= 3:
                    print("🛑 已达到单次安全回复数量上限，停止水贴。")
                    break
                
            except Exception as e:
                print(f"⚠️ 处理帖子 {post_url} 时出错: {str(e)}")
                continue
                
        TASK_STATUS["comment_count"] = success_count
        print("🏁 NodeSeek 互动评论任务阶段结束")
                
    except Exception as e:
        msg = f"💥 NodeSeek 评论区整体异常: {str(e)}"
        print(msg)
        try:
            driver.save_screenshot('ns_comment_exception.png')
        except:
            pass
        traceback.print_exc()

if __name__ == "__main__":
    print("---------- NodeSeek 模拟点击签到与互动任务开始 ----------")
    driver = setup_driver_and_cookies()
    if driver:
        # 1. 执行互动水贴与加鸡腿
        nodeseek_comment(driver)
        
        # 2. 执行核心签到任务
        click_sign_icon(driver)
        
        # 3. 汇总信息并推送青龙通知
        summary_msg = (
            f"🏅 签到状态: {TASK_STATUS['sign']}\n"
            f"💬 成功水贴: {TASK_STATUS['comment_count']} 条\n"
            f"🍗 鸡腿状态: {TASK_STATUS['chicken_leg']}"
        )
        
        if "成功" in TASK_STATUS['sign'] or "今日已签" in TASK_STATUS['sign']:
            send_notification("任务完成", summary_msg)
        else:
            send_notification("任务出现异常", summary_msg)
            
        print("👋 正在关闭浏览器，释放系统内存...")
        driver.quit()
    else:
        print("❌ 浏览器运行环境初始化失败。")
        
    print("---------- NodeSeek 模拟点击签到与互动任务结束 ----------")
