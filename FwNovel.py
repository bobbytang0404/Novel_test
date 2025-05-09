import requests
from requests.adapters import HTTPAdapter

import parsel
from parsel import Selector
import os
from urllib3 import Retry

# 配置重试策略
retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry_strategy)
session = requests.Session()
session.mount("https://", adapter)
session.mount("http://", adapter)

headers = {
    # 用户信息，常用于检测是否有登录账号
    'Cookie': '替换',
    # User-Agent 用户代理，浏览器/设备的基本身份信息
    'User-Agent': '替换'
}
url = 'https://www.sosad.fun/threads/替换/profile'
try:
    response = session.get(url=url, headers=headers)
    html = response.text
    selector = parsel.Selector(html)

    # 小说名
    name = selector.css('.font-1::text').get().strip()
    os.makedirs(name, exist_ok=True)

    # 获取作者名称
    author_first = selector.css('div.h5 a::text').get()
    # 如果 author_first 是 "Original Novel"，则从 .majia 元素获取文本
    if author_first == "Original Novel":
        author_first = selector.css('.majia::text').get()
    # 如果 author_first 存在，则去除多余的空白并赋值给 author
    if author_first:
        author = author_first.strip()
    else:
        # 如果 author_first 不存在或为空，则默认值为 "匿名咸鱼"
        author = '匿名咸鱼'

    #tag
    tag = selector.css('a[title]::attr(title)').getall()

    # 简介
    intro_son = selector.css('.no-selection *::text').getall()
    introduction = '\n'.join([i.strip() for i in intro_son if i.strip()])

    # 提取章节名和链接
    chapter_links = selector.css('.btn-group-sm>.btn, .btn-sm')
    title_list = [
        " ".join(a.css('::text').getall()).strip()  # 合并所有文本内容
        for a in chapter_links
    ]
    title_href = [a.css('::attr(href)').get() for a in chapter_links]

    '''
    过滤掉含图片的章节链接(没有就注释掉，有就单独复制章节链接到bad_link里)
    bad_link = 'https://www.sosad.fun/posts/15639543'
    filtered = [(t, h) for t, h in zip(title_list, title_href) if h != bad_link]
    title_list, title_href = zip(*filtered)
    '''

    # 初始化整本书内容
    full_book = f"{name}\n\n作者：{author}\n\ntag:{tag}\n\n简介：\n{introduction}\n\n"

    for title, href in zip(title_list, title_href):
        print(f'正在抓取章节：{title}')
        try:
            chapter_html = session.get(href, headers=headers).text
            chapter_sel = parsel.Selector(chapter_html)

            # 小标题
            sub_title = chapter_sel.css('strong.h5::text').get()
            sub_title = sub_title.strip() if sub_title else ''

            # 作者有话说
            author_notes = chapter_sel.css('.warning-tag::text').getall()
            ban_keywords = ['Check In', '（本帖非边限对外公开，请不要引入“边限”讨论。）']
            author_note_first = ''.join(i.strip() for i in author_notes if i.strip() and not any(b in i for b in ban_keywords))

            # 提取正文内容
            # 找第一个 span[id]
            first_span = chapter_sel.css('.main-text span[id]').get()
            if first_span:
                # 用新的 Selector 单独解析这段 HTML
                first_span_sel = Selector(text=first_span)
                content_paragraphs = first_span_sel.css('p::text').getall()
                content = '\n'.join(i.strip() for i in content_paragraphs if i.strip())
            else:
                content = ''

            # 提取章节末尾作话内容
            author_note_paragraphs = chapter_sel.css('.main-text .text-left.grayout p::text').getall()
            author_note_finish = '\n'.join(i.strip() for i in author_note_paragraphs if i.strip())

            # 合并两部分
            full_content_text = content
            if author_note_finish:
                full_content_text += '\n\n作话：\n' + author_note_finish

            # 拼接章节内容
            full_book += f"\n\n【{title}】\n\n"
            if sub_title:
                full_book += f"概要：{sub_title}\n\n"
            if author_note_first:
                full_book += f"作者有话说：{author_note_first}\n\n"
            full_book += f"{full_content_text}\n"
        except requests.exceptions.RequestException as e:
            print(f"抓取章节 {title} 时出错: {e}")

    # 保存为 txt 文件
    with open(f"{name}/{name}by{author}.txt", 'w', encoding='utf-8') as f:
        f.write(full_book)

    print('小说保存成功 ✅')
    print(name +'by'+ author)
except requests.exceptions.RequestException as e:
    print(f"请求小说页面时出错: {e}")