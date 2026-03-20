import json
import urllib.request

url = 'https://raw.githubusercontent.com/modood/Administrative-divisions-of-China/master/dist/pca.json'
req = urllib.request.Request(url)
with urllib.request.urlopen(req) as response:
    data = json.loads(response.read().decode())
    
sichuan = data.get('四川省', {})
options = []
sichuan_node = {'value': '四川省', 'label': '四川省', 'children': []}
for city, areas in sichuan.items():
    city_node = {'value': city, 'label': city, 'children': []}
    for area in areas:
        city_node['children'].append({'value': area, 'label': area})
    sichuan_node['children'].append(city_node)

options.append(sichuan_node)

js_op = json.dumps(options, ensure_ascii=False, indent=4)
js_op = js_op.replace('\n', '\n      ')

with open('sichuan.txt', 'w', encoding='utf-8') as f:
    f.write(js_op)
