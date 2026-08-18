import json, re, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone

FEEDS={
'Ars Technica':'https://feeds.arstechnica.com/arstechnica/index',
'The Register':'https://www.theregister.com/headlines.atom',
'WIRED':'https://www.wired.com/feed/rss',
'BleepingComputer':'https://www.bleepingcomputer.com/feed/',
'TechCrunch':'https://techcrunch.com/feed/',
'IEEE Spectrum':'https://spectrum.ieee.org/feeds/feed.rss',
'Hacker News':'https://hnrss.org/frontpage'}
CATS={'AI':['artificial intelligence','machine learning',' llm',' ai ','openai','anthropic','gemini','qwen','llama'],'CYBERSECURITY':['security','cyber','vulnerability','exploit','malware','ransomware','breach','cve','phishing','zero-day'],'LINUX':['linux','ubuntu','debian','fedora','kernel'],'WINDOWS':['windows','microsoft','active directory','powershell'],'HARDWARE':['cpu','gpu','processor','chip','semiconductor','nvidia','amd','intel','hardware'],'ROBOTICS':['robot','robotics','drone','autonomous','humanoid'],'SPACE':['space','nasa','spacex','rocket','satellite','orbit','moon','mars']}

def clean(x): return re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',x or '')).strip()
def text(node, names):
 for n in names:
  x=node.find(n)
  if x is not None and x.text:return clean(x.text)
 return ''
def category(title,summary):
 s=' '+(title+' '+summary).lower()+' '; scores={k:sum(w in s for w in v) for k,v in CATS.items()}; best=max(scores,key=scores.get); return best if scores[best] else 'GENERAL'

def feed(url,source):
 req=urllib.request.Request(url,headers={'User-Agent':'Dylan-Tech-Intelligence/1.0'})
 root=ET.fromstring(urllib.request.urlopen(req,timeout=20).read()); items=root.findall('.//item') or root.findall('.//{http://www.w3.org/2005/Atom}entry'); out=[]
 for n in items[:25]:
  title=text(n,['title','{http://www.w3.org/2005/Atom}title']); summary=text(n,['description','summary','{http://www.w3.org/2005/Atom}summary']); link=text(n,['link','{http://www.w3.org/2005/Atom}link'])
  if not link:
   x=n.find('{http://www.w3.org/2005/Atom}link'); link=x.attrib.get('href','') if x is not None else ''
  if title and link: out.append({'title':title,'summary':summary[:280],'url':link,'source':source,'category':category(title,summary),'age':'RECENT'})
 return out

articles=[]
for source,url in FEEDS.items():
 try: articles += feed(url,source)
 except Exception as e: print('WARN',source,e)
seen=set(); unique=[]
for a in articles:
 k=(a['title'].lower(),a['url'])
 if k not in seen: seen.add(k); unique.append(a)
with open('data/tech-news.json','w',encoding='utf-8') as f: json.dump({'generated_at':datetime.now(timezone.utc).isoformat(),'articles':unique[:100]},f,ensure_ascii=False,indent=2)
print('Wrote',min(len(unique),100),'articles')
