import requests
from bs4 import BeautifulSoup
import json
import time
import random
import re
import os

# 目标：上海大学新闻网
def get_header():
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15'
    ]
    return {'User-Agent': random.choice(user_agents)}

def get_shu_official():
    url = "https://news.shu.edu.cn/index/zhxw.htm"
    print(f"正在访问官网: {url}")
    news_list = []
    try:
        res = requests.get(url, headers=get_header(), timeout=15)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        
        for link in soup.find_all('a'):
            title = link.get_text(strip=True)
            href = link.get('href')
            if title and href and len(title) > 10 and '.htm' in href:
                if not href.startswith('http'):
                    href = f"https://news.shu.edu.cn/{href.replace('../', '').lstrip('/')}"
                
                if not any(n['url'] == href for n in news_list):
                    news_list.append({"title": title, "url": href, "source": "上大官网", "time": "校内", "tag": "official"})
    except Exception as e:
        print(f"官网抓取报错: {e}")
    return news_list[:8]

def get_internet_buzz():
    url = "https://www.baidu.com/s?tn=news&rtt=1&bsst=1&cl=2&wd=上海大学"
    print(f"正在全网巡查: {url}")
    news_list = []
    try:
        res = requests.get(url, headers=get_header(), timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        results = soup.find_all('div', class_='result-op')
        for item in results:
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

            news_list.append({"title": title, "url": href, "source": source, "time": pub_time, "tag": "media"})
    except Exception as e:
        print(f"全网搜索报错: {e}")

    platforms = [
        {"title": "👉 点击查看“上海大学”B站最新视频", "source": "Bilibili", "url": "https://search.bilibili.com/all?keyword=上海大学&order=pubdate", "time": "实时", "tag": "video"},
        {"title": "👉 点击查看“上海大学”知乎实时讨论", "source": "知乎", "url": "https://www.zhihu.com/search?type=content&q=上海大学", "time": "实时", "tag": "forum"},
        {"title": "👉 点击查看“上海大学”微博热搜", "source": "微博", "url": "https://s.weibo.com/weibo?q=上海大学&xsort=hot", "time": "实时", "tag": "forum"},
    ]
    return news_list[:12] + platforms

def save_to_js(data):
    path = "data.js"
    # 这里加一个随机数，防止文件大小完全一样导致Git不提交
    update_info = f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
    output = {
        "update_time": update_info,
        "news": data
    }
    content = f"window.SHU_DATA = {json.dumps(output, ensure_ascii=False, indent=2)};"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"数据已更新: {update_info}")

if __name__ == "__main__":
    print("--- GitHub Action 开始执行 ---")
    official = get_shu_official()
    internet = get_internet_buzz()
    save_to_js(official + internet)
    print("--- 执行完毕 ---")