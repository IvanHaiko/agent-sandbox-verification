import json,runpy
f=runpy.run_path('src/candidate.py')['clamp']
cases=[{'args': [1, 2, 5], 'expected': 2}, {'args': [3, 2, 5], 'expected': 3}, {'args': [6, 2, 5], 'expected': 5}, {'args': [2, 2, 5], 'expected': 2}, {'args': [5, 2, 5], 'expected': 5}, {'args': [-4, -4, -4], 'expected': -4}, {'args': [-9, -7, -2], 'expected': -7}, {'args': [-3, -7, -2], 'expected': -3}, {'args': [0, -7, -2], 'expected': -2}, {'args': [3, 5, 2], 'expected': 'ValueError'}]
failures=[]
for i,c in enumerate(cases):
    try: got=f(*c['args'])
    except ValueError: got='ValueError'
    if got!=c['expected']: failures.append({'case':i,'args':c['args'],'expected':c['expected'],'actual':got})
print(json.dumps({'passed':not failures,'cases':len(cases),'failures':failures}))
raise SystemExit(bool(failures))
