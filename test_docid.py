import requests, re
ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
html = requests.get('https://www.facebook.com/', headers={'user-agent': ua}).text

js_urls_raw = re.findall(r'"(https:\\/\\/static\.xx\.fbcdn\.net\\/rsrc\.php\\/[^"]{10,}\.js)"', html)
if not js_urls_raw:
    js_urls_raw = re.findall(r'"(https://static\.xx\.fbcdn\.net/rsrc\.php/[^"]{10,}\.js)"', html)
js_urls = [url.replace('\\/', '/') for url in js_urls_raw]

print('Found', len(js_urls), 'JS urls')
found = False
for i, url in enumerate(js_urls):
    try:
        text = requests.get(url, headers={'user-agent': ua}).text
        m = re.search(r'CometUFIFeedbackReactMutation[^\d]{0,30}(\d{15,20})', text)
        if not m:
            m = re.search(r'(\d{15,20})[^\d]{0,30}CometUFIFeedbackReactMutation', text)
        if m:
            print('Found doc_id:', m.group(1), 'in file #', i, url)
            found = True
            break
    except Exception as e:
        pass

if not found:
    print('Not found')
