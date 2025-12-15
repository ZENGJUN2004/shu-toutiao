import requests
from bs4 import BeautifulSoup
import json
import time
import random
import sys
import io
import datetime
import re

# 防止云端控制台报错
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# --- 配置 ---
# 只保留最近 2 天内的新闻
MAX_DAYS_AGO = 2 

def get_header():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.baidu.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

def parse_baidu_time(time_str):
    """
    把各种格式的时间（5分钟前、昨天、2025-12-15）统一转换成 datetime 对象
    以便进行比较和排序
    """
    now = datetime.datetime.now()
    time_str = time_str.strip()

    try:
        if "分钟前" in time_str:
            mins = int(re.search(r'(\d+)', time_str).group(1))
            return now - datetime.timedelta(minutes=mins)
        elif "小时前" in time_str:
            hours = int(re.search(r'(\d+)', time_str).group(1))
            return now - datetime.timedelta(hours=hours)
        elif "昨天" in time_str:
            return now - datetime.timedelta(days=1)
        elif "前天" in time_str:
            return now - datetime.timedelta(days=2)
        elif "天前" in time_str:
            days = int(re.search(r'(\d+)', time_str).group(1))
            return now - datetime.timedelta(days=days)
        elif "年" in time_str or "-" in time_str:
            # 处理 2025年12月15日 或 2025-12-15
            clean_str = time_str.replace("年", "-").replace("月", "-").replace("日", "")
            return datetime.datetime.strptime(clean_str, "%Y-%m-%d")
        else:
            # 无法识别的格式（比如“刚刚”），默认算作现在
            return now
    except:
        return now - datetime.timedelta(days=365) # 出错就当做旧新闻处理

def get_shu_official():
    """上大官网新闻 (官网通常按时间排，直接取前8条)"""
    url = "https://news.shu.edu.cn/index/zhxw.htm"
    print(f"扫描官网: {url}")
    news_list = []
    try:
        res = requests.get(url, headers=get_header(), timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a')
        
        for link in links:
            title = link.get_text(strip=True)
            href = link.get('href')
            
            if title and href and len(title) > 10 and '.htm' in href:
                if "版权" in title: continue
                
                if not href.startswith('http'):
                    href = f"https://news.shu.edu.cn/{href.replace('../', '')}"
                
                # 官网没写具体时间，默认算作最新，排在最前
                # 为了排序，给他一个稍微滞后一点点的“当前时间”
                fake_time = datetime.datetime.now()
                
                if not any(n['url'] == href for n in news_list):
                    news_list.append({
                        "title": title, "url": href, "source": "上大官网", 
                        "time_str": "校内最新", # 显示给用户看的
                        "timestamp": fake_time, # 排序用的
                        "tag": "official"
                    })
    except Exception as e:
        print(f"官网抓取错误: {e}")
    return news_list[:8]

def get_internet_buzz():
    """全网搜索 (强制按时间排序)"""
    # 关键参数 rtt=1 (Sort by Time)，默认是4 (Sort by Relevance)
    url = "https://www.baidu.com/s?tn=news&rtt=1&bsst=1&cl=2&wd=上海大学"
    print(f"全网检索 (已开启时间强排序): {url}")
    
    news_list = []
    try:
        res = requests.get(url, headers=get_header(), timeout=12)
        soup = BeautifulSoup(res.text, 'html.parser')
        results = soup.find_all('div', class_='result-op')
        
        for item in results:
            try:
                title_node = item.find('h3').find('a')
                title = title_node.get_text(strip=True)
                href = title_node['href']
                
                source_node = item.find('span', class_='c-color-gray')
                source = source_node.get_text(strip=True) if source_node else "互联网"
                
                time_node = item.find('span', class_='c-color-gray2')
                time_str = time_node.get_text(strip=True) if time_node else ""

                # --- 关键步骤：时间过滤 ---
                real_time = parse_baidu_time(time_str)
                days_diff = (datetime.datetime.now() - real_time).days
                
                # 如果新闻超过了 2 天，直接扔掉 (continue)
                if days_diff > MAX_DAYS_AGO:
                    continue

                news_list.append({
                    "title": title, "url": href, "source": source, 
                    "time_str": time_str, # 原样显示 "5分钟前"
                    "timestamp": real_time, # 排序用
                    "tag": "media"
                })
            except:
                continue
    except Exception as e:
        print(f"全网抓取错误: {e}")
        
    return news_list

def save_to_js(data):
    # --- 最终排序：按时间戳倒序 (最新的在最上面) ---
    data.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # 清理掉 timestamp 字段（不需要写入JS文件）
    for item in data:
        del item['timestamp']
        
    # 北京时间
    utc_now = datetime.datetime.utcnow()
    cst_now = utc_now + datetime.timedelta(hours=8)
    time_str = cst_now.strftime('%Y-%m-%d %H:%M')

    output = {
        "update_time": time_str,
        "news": data[:20] # 只保留最新的20条
    }
    
    with open("data.js", "w", encoding="utf-8") as f:
        f.write(f"window.SHU_DATA = {json.dumps(output, ensure_ascii=False, indent=2)};")
    print(f"✅ 更新完成。时间: {time_str}，共 {len(data)} 条新闻。")

if __name__ == "__main__":
    official = get_shu_official()
    internet = get_internet_buzz()
    
    # 静态链接 (放在最后)
    static_links = [
        {"title": "👉 点击查看 B站“上海大学”最新视频 (按发布时间)", "source": "Bilibili", "url": "https://search.bilibili.com/all?keyword=上海大学&order=pubdate", "time_str": "实时", "tag": "video", "timestamp": datetime.datetime.now()},
        {"title": "👉 点击查看 微博“上海大学”实时广场", "source": "微博", "url": "https://s.weibo.com/weibo?q=上海大学&xsort=hot", "time_str": "实时", "tag": "forum", "timestamp": datetime.datetime.now()},
    ]
    
    # 合并所有数据
    all_data = official + internet + static_links
    save_to_js(all_data)
