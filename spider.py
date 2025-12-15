import requests
from bs4 import BeautifulSoup
import json
import time
import random
import sys
import io
import datetime
import re

# 1. 基础配置
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
MAX_DAYS_AGO = 2  # 只保留最近 48 小时内的报道

def get_header():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://www.baidu.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }

# 2. 时间清洗 (只留新鲜的)
def parse_baidu_time(time_str):
    now = datetime.datetime.now()
    time_str = str(time_str).strip()
    try:
        if "分钟前" in time_str:
            mins = int(re.search(r'(\d+)', time_str).group(1))
            return now - datetime.timedelta(minutes=mins)
        elif "小时前" in time_str:
            hours = int(re.search(r'(\d+)', time_str).group(1))
            return now - datetime.timedelta(hours=hours)
        elif "昨天" in time_str:
            return now - datetime.timedelta(days=1)
        elif "天前" in time_str:
            days = int(re.search(r'(\d+)', time_str).group(1))
            return now - datetime.timedelta(days=days)
        elif "年" in time_str or "-" in time_str:
            clean_str = time_str.replace("年", "-").replace("月", "-").replace("日", "")
            return datetime.datetime.strptime(clean_str, "%Y-%m-%d")
        else:
            return now
    except:
        return now - datetime.timedelta(days=365)

# ==========================================
# 3. 四大核心战区 (覆盖权威、地方、专业媒体)
# ==========================================
SEARCH_ZONES = [
    # --- 战区 A: 权威央媒 (最高关注度) ---
    {
        "name": "央媒报道",
        # 逻辑：搜索“上海大学”同时必须包含这些媒体名之一
        "query": '上海大学 ("人民日报" | "光明日报" | "新华网" | "中国日报")',
        "tag": "media"
    },
    # --- 战区 B: 主流沪媒 (本地影响力) ---
    {
        "name": "沪媒聚焦",
        # 逻辑：文汇报、解放日报、澎湃新闻
        "query": '上海大学 ("文汇报" | "解放日报" | "澎湃")',
        "tag": "media"
    },
    # --- 战区 C: 专业/学术报刊 (体现科研实力) ---
    {
        "name": "学术专业",
        # 逻辑：社科报、科技报
        "query": '上海大学 ("中国社会科学报" | "中国科学报" | "科技日报")',
        "tag": "media"
    },
    # --- 战区 D: 官网直通 (校内动态) ---
    {
        "name": "官网", 
        "query": "OFFICIAL_SITE", # 特殊标记，走专门函数
        "tag": "official"
    }
]

def fetch_baidu_news(zone):
    """通用百度新闻抓取器"""
    print(f"正在扫描：[{zone['name']}] ...")
    news_pool = []
    
    # rtt=1 强制按时间排序
    url = f"https://www.baidu.com/s?tn=news&rtt=1&bsst=1&cl=2&wd={zone['query']}"
    
    try:
        res = requests.get(url, headers=get_header(), timeout=12)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        items = soup.find_all('div', class_='result-op')
        if not items: items = soup.find_all('div', class_='result')
        
        for item in items:
            try:
                title_node = item.find('h3').find('a')
                title = title_node.get_text(strip=True)
                link = title_node['href']
                
                # 来源清洗
                source_node = item.find('span', class_='c-color-gray')
                source = source_node.get_text(strip=True) if source_node else "媒体报道"
                
                time_node = item.find('span', class_='c-color-gray2')
                time_str = time_node.get_text(strip=True) if time_node else ""
                
                # 时间过滤
                real_time = parse_baidu_time(time_str)
                if (datetime.datetime.now() - real_time).days > MAX_DAYS_AGO:
                    continue
                
                news_pool.append({
                    "title": title, "url": link, "source": source,
                    "time": time_str, "timestamp": real_time, 
                    "tag": zone['tag']
                })
            except: continue
        time.sleep(1.5)
    except Exception as e:
        print(f"  搜索错误: {e}")
        
    return news_pool

def get_shu_official():
    """专门抓取官网"""
    print("正在扫描：[上大官网] ...")
    url = "https://news.shu.edu.cn/index/zhxw.htm"
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
                
                # 官网默认为最新
                fake_time = datetime.datetime.now()
                if not any(n['url'] == href for n in news_list):
                    news_list.append({
                        "title": title, "url": href, "source": "上大官网",
                        "time": "校内", "timestamp": fake_time, "tag": "official"
                    })
    except Exception as e:
        print(f"官网错误: {e}")
    return news_list[:6]

def fetch_all():
    all_news = []
    
    for zone in SEARCH_ZONES:
        if zone['query'] == "OFFICIAL_SITE":
            all_news.extend(get_shu_official())
        else:
            all_news.extend(fetch_baidu_news(zone))
    
    # 固定静态入口
    now = datetime.datetime.now()
    static_links = [
        {"title": "👉【B站】上海大学官方视频动态 (按发布排序)", "source": "Bilibili", "url": "https://search.bilibili.com/all?keyword=上海大学&order=pubdate", "time": "实时", "tag": "video", "timestamp": now},
        {"title": "👉【微博】上海大学实时热搜广场", "source": "微博", "url": "https://s.weibo.com/weibo?q=上海大学&xsort=hot", "time": "实时", "tag": "forum", "timestamp": now},
    ]
    
    final_list = static_links + all_news
    
    # 去重
    seen = set()
    unique_list = []
    for item in final_list:
        if item['title'] not in seen:
            unique_list.append(item)
            seen.add(item['title'])
            
    # 按时间倒序
    unique_list.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # 清理字段
    for item in unique_list:
        del item['timestamp']
        
    return unique_list[:40]

def save(data):
    try:
        # 北京时间
        utc_now = datetime.datetime.utcnow()
        cst_now = utc_now + datetime.timedelta(hours=8)
        time_str = cst_now.strftime('%Y-%m-%d %H:%M')
        
        # 变量名 SHU_DATA (上大头条专用)
        output = { "update_time": time_str, "news": data }
        
        with open("data.js", "w", encoding="utf-8") as f:
            f.write(f"window.SHU_DATA = {json.dumps(output, ensure_ascii=False, indent=2)};")
        print(f"✅ 更新完成。时间: {time_str}，共 {len(data)} 条新闻。")
    except Exception as e:
        sys.exit(1)

if __name__ == "__main__":
    data = fetch_all()
    save(data)

