"""Integration checks against a real running API; no mocked store."""
import json
import os
import unittest
from urllib.request import urlopen,Request
from urllib.error import HTTPError

BASE=os.getenv('SUPERR_TEST_URL','http://127.0.0.1:8000')
def fetch(path,method='GET',data=None):
    request=Request(BASE+path,method=method,data=data,headers={'Content-Type':'application/json'})
    try:
        with urlopen(request,timeout=20) as response:
            body=response.read();return response.status,body,response.headers
    except HTTPError as e:return e.code,e.read(),e.headers

class ApiTests(unittest.TestCase):
    def test_health_and_rankings(self):
        status,body,_=fetch('/api/health');self.assertEqual(status,200);self.assertEqual(json.loads(body)['status'],'ok')
        for category in ['batters','bowlers']:
            status,body,_=fetch(f'/api/{category}/rankings?page_size=10')
            data=json.loads(body);self.assertEqual(status,200);self.assertEqual(len(data['items']),10)
            self.assertEqual([p['rank'] for p in data['items']],list(range(1,11)))

    def test_filters_pagination_and_sort(self):
        status,body,_=fetch('/api/players?q=Rinku&category=bat')
        self.assertEqual(status,200);self.assertEqual(json.loads(body)['items'][0]['name'],'Rinku Singh')
        _,body,_=fetch('/api/bowlers/rankings?sort=high_balls&descending=false&page_size=100')
        rows=json.loads(body)['items'];values=[r['metrics']['high_balls'] for r in rows];self.assertEqual(values,sorted(values))
        self.assertEqual(fetch('/api/players?page=-1')[0],422)
        self.assertEqual(fetch('/api/players?season=2028')[0],422)

    def test_comparison_and_profiles(self):
        status,body,_=fetch('/api/players/compare?ids=4708,8&category=bat')
        self.assertEqual(status,200);self.assertEqual(len(json.loads(body)['players']),2)
        self.assertEqual(fetch('/api/players/compare?ids=bad')[0],422)
        self.assertEqual(fetch('/api/players/999999')[0],404)
        self.assertEqual(fetch('/api/batters/4708/reliability')[0],200)
        self.assertEqual(fetch('/api/players/4708/report?category=bat')[0],200)

    def test_analysis_and_export(self):
        for path in ['/api/overview','/api/methodology','/api/data-quality','/api/analytics/pressure?category=bowl&level=High','/api/analytics/phase-wise?player_id=4708','/api/analytics/consistency?player_id=4708','/api/auction/recommendations']:
            self.assertEqual(fetch(path)[0],200,path)
        status,body,headers=fetch('/api/export/rankings.csv?category=bat');self.assertEqual(status,200)
        self.assertIn(b'Rinku Singh',body);self.assertIn('text/csv',headers.get('Content-Type'))

    def test_mutations_are_protected(self):
        self.assertEqual(fetch('/api/analytics/recalculate','POST',b'{"bootstrap":300}')[0],403)
        self.assertEqual(fetch('/api/data/upload?filename=new.csv','POST',b'a,b\n1,2')[0],403)

if __name__=='__main__':unittest.main(verbosity=2)
