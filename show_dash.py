import json, sys

data = sys.stdin.read()
d = json.loads(data)
print('Stats:', d['stats'])
for o in d['payment_overview']:
    print(f'{o["unit_id"]} {o["name"]}: paid={o["total_paid"]} expected={o["total_expected"]} balance={o["balance"]}')
