import json, os, sys, urllib.request
API=os.environ['PAPERCLIP_API_URL']; KEY=os.environ['PAPERCLIP_API_KEY']; RUN=os.environ['PAPERCLIP_RUN_ID']
def req(method, path, body=None):
    r=urllib.request.Request(API+path, method=method, data=None if body is None else json.dumps(body).encode(),
        headers={'Authorization':'Bearer '+KEY,'Content-Type':'application/json','X-Paperclip-Run-Id':RUN})
    with urllib.request.urlopen(r) as f: return json.load(f)
uuid, path = sys.argv[1], sys.argv[2]
body=open(path).read().rstrip('\n')
c=req('POST','/api/issues/%s/comments'%uuid,{'body':body}); print('comment', c['id'])
r=req('PATCH','/api/issues/'+uuid,{'status':'done','executionPolicy':{'monitor':None}})
print('patched', r['identifier'], r['status'], (r.get('executionPolicy') or {}).get('monitor'))
