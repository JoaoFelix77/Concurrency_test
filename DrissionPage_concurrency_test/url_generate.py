import random

# 常用域名和路径模板
domains = [
    ("https://blog.csdn.net", "/user_{uid}/article/details/{id}"),
    ("https://www.jianshu.com/p", "/{id}"),
    ("https://www.lawtime.cn/wenda/q_{id}.html", ""),
    ("https://www.120ask.com/question/{id}.htm", ""),
    ("https://www.55188.com/keywords-{kw}.html", ""),
    ("https://diy.zol.com.cn/{cat}/{id}.html", ""),
    ("https://bbs.zol.com.cn/quanzi/{id}.html", ""),
    ("https://www.xjishu.com/fmr_{id}.html", ""),
    ("https://devpress.csdn.net/v1/article/detail/{id}", ""),
    ("https://www.ouryao.com/forum.php?mod=viewthread&tid={id}&page=1", ""),
]

# 生成关键词池，用于 55188.com 的 URL
keywords = [
    "智能家居", "机器学习", "深度学习", "互联网+", "新能源汽车", "量子计算",
    "区块链", "大数据", "云计算", "5G", "工业4.0", "智慧教育", "医疗健康",
    "金融科技", "网络安全", "物联网", "智能制造", "AR", "VR", "自然语言处理"
]

def gen_csdn(uid, aid):
    return f"https://blog.csdn.net/user_{uid}/article/details/{aid}"

def gen_jianshu(aid):
    return f"https://www.jianshu.com/p/{aid}"

def gen_lawtime(aid):
    return f"https://www.lawtime.cn/wenda/q_{aid}.html"

def gen_120ask(aid):
    return f"https://www.120ask.com/question/{aid}.htm"

def gen_55188(kw):
    return f"https://www.55188.com/keywords-{kw}.html"

def gen_zol_diy(cat, aid):
    return f"https://diy.zol.com.cn/{cat}/{aid}.html"

def gen_zol_bbs(aid):
    return f"https://bbs.zol.com.cn/quanzi/{aid}.html"

def gen_xjishu(aid):
    return f"https://www.xjishu.com/fmr_{aid}.html"

def gen_devpress(aid):
    return f"https://devpress.csdn.net/v1/article/detail/{aid}"

def gen_ouryao(aid):
    return f"https://www.ouryao.com/forum.php?mod=viewthread&tid={aid}&page=1"

generators = [
    gen_csdn, gen_jianshu, gen_lawtime, gen_120ask,
    gen_55188, gen_zol_diy, gen_zol_bbs,
    gen_xjishu, gen_devpress, gen_ouryao
]

# 随机生成 2000 条
urls = set()
while len(urls) < 8000:
    gen = random.choice(generators)
    if gen is gen_csdn:
        uid = random.randint(1000000, 9999999)
        aid = random.randint(10000000, 99999999)
        urls.add(gen_csdn(uid, aid))
    elif gen is gen_jianshu:
        aid = ''.join(random.choices('0123456789abcdef', k=16))
        urls.add(gen_jianshu(aid))
    elif gen is gen_lawtime:
        aid = random.randint(10000000, 99999999)
        urls.add(gen_lawtime(aid))
    elif gen is gen_120ask:
        aid = random.randint(10000000, 99999999)
        urls.add(gen_120ask(aid))
    elif gen is gen_55188:
        kw = random.choice(keywords)
        urls.add(gen_55188(kw))
    elif gen is gen_zol_diy:
        cat = random.randint(100, 999)
        aid = random.randint(100000, 999999)
        urls.add(gen_zol_diy(cat, aid))
    elif gen is gen_zol_bbs:
        aid = random.randint(100000, 999999)
        urls.add(gen_zol_bbs(aid))
    elif gen is gen_xjishu:
        aid = random.randint(10000000, 99999999)
        urls.add(gen_xjishu(aid))
    elif gen is gen_devpress:
        aid = random.randint(10000000, 99999999)
        urls.add(gen_devpress(aid))
    elif gen is gen_ouryao:
        aid = random.randint(10000000, 99999999)
        urls.add(gen_ouryao(aid))

# 写入文件
with open('url_list_extra_8000.txt', 'w', encoding='utf-8') as f:
    for u in urls:
        f.write(u + '\n')

print("已生成 8000 条测试 URL，保存在 url_list_extra_2000.txt")
