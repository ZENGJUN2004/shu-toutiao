import requests
from bs4 import BeautifulSoup
import json
import time
import random
import sys
import io

# ==========================================
# 核心修复：防止云端控制台因为中文/Emoji报错
# ==========================================
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def get_header():
    # 模拟真实浏览器，防止被拦截
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Referer': 'https://www.baidu.com/'
    }

def get_shu_official():
    """抓取官网新闻"""
    url = "https://news.shu.edu.cn/index/zhxw.htm"
    print(f"Fetching Official: {url}") # 纯英文打印，防止报错
    news_list = []
    try:
        res = requests.get(url, headers=get_header(), timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 尝试适配多种列表结构
        links = soup.find_all('a')
        
        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href')
            
            # 筛选逻辑
            if title and href and len(title) > 8 and '.htm' in href:
                if "版权" in title or "联系" in title: continue
                
                if not href.startswith('http'):
                    # 修复相对路径
                    clean_href = href.replace('../', '').lstrip('/')
                    href = f"https://news.shu.edu.cn/{clean_href}"
                
                # 简单去重
                if not any(n['url'] == href for n in news_list):
                    news_list.append({
                        "title": title, "url": href, 
                        "source": "上大官网", "time": "校内", "tag": "official"
                    })
                    
        print(f"  - Official news count: {len(news_list)}")
    except Exception as e:
        print(f"  - Official Error: {e}")
    
    return news_list[:8]

def get_internet_buzz():
    """抓取全网资讯 (百度新闻)"""
    url = "https://www.baidu.com/s?tn=news&rtt=1&bsst=1&cl=2&wd=上海大学"
    print(f"Fetching Internet: {url}")
    news_list = []
    try:
        res = requests.get(url, headers=get_header(), timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        results = soup.find_all('div', class_='result-op')
        if not results: results = soup.find_all('div', class_='result')
        
        for item in results:
            try:
                title_tag = item.find('h3')
                if not title_tag: continue
                link_tag = title_tag.find('a')
                if not link_tag: continue
                
                title = link_tag.get_text(strip=True)
                href = link_tag['href']
                
                source_tag = item.find('span', class_='c-color-gray')
                source = source_tag.get_text(strip=True) if source_tag else "互联网"
                
                time_tag = item.find('span', class_='c-color-gray2')
                pub_time = time_tag.get_text(strip=True) if time_tag else "近期"

                news_list.append({
                    "title": title, "url": href, 
                    "source": source, "time": pub_time, "tag": "media"
                })
            except:
                continue
                
        print(f"  - Internet news count: {len(news_list)}")
    except Exception as e:
        print(f"  - Internet Error: {e}")

    # 静态链接 (即使爬虫挂了，这些也会显示)
    print("Adding static links...")
    platforms = [
        {"title": "👉 点击查看“上海大学”B站最新视频", "source": "Bilibili", "url": "https://search.bilibili.com/all?keyword=上海大学&order=pubdate", "time": "实时", "tag": "video"},
        {"title": "👉 点击查看“上海大学”知乎实时讨论", "source": "知乎", "url": "https://www.zhihu.com/search?type=content&q=上海大学", "time": "实时", "tag": "forum"},
        {"title": "👉 点击查看“上海大学”微博热搜", "source": "微博", "url": "https://s.weibo.com/weibo?q=上海大学&xsort=hot", "time": "实时", "tag": "forum"},
    ]
    
    return news_list[:15] + platforms

def save_to_js(data):
    try:
        path = "data.js"
        # 写入 UTC 时间，前端会显示
        update_info = time.strftime('%Y-%m-%d %H:%M', time.localtime())
        
        output = {
            "update_time": update_info,
            "news": data
        }
        
        # 强制 UTF-8 写入
        content = f"window.SHU_DATA = {json.dumps(output, ensure_ascii=False, indent=2)};"
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"Success! Saved {len(data)} items.")
        
    except Exception as e:
        print(f"Save Error: {e}")
        sys.exit(1) # 如果保存失败，才报错红色 X

if __name__ == "__main__":
    try:
        print(">>> Job Started")
        official = get_shu_official()
        internet = get_internet_buzz()
        
        # 合并数据
        all_data = official + internet
        
        # 就算没抓到新闻，至少把静态链接存进去，保证页面不白板
        if not all_data:
            print("Warning: No news fetched, using backup data.")
        
        save_to_js(all_data)
        print(">>> Job Finished")
        
    except Exception as e:
        print(f"Critical Error: {e}")
        sys.exit(1)
