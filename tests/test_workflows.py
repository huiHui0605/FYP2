from datetime import datetime, timedelta, timezone
import re
import sqlite3
import pytest
from looplocal import create_app, init_db


def read(app,sql,args=()):
    with sqlite3.connect(app.config['DATABASE']) as c:
        c.row_factory=sqlite3.Row
        return c.execute(sql,args).fetchall()


def write(app,sql,args=()):
    with sqlite3.connect(app.config['DATABASE']) as c:
        return c.execute(sql,args).lastrowid


def day(offset=0):
    return (datetime.now(timezone(timedelta(hours=8)))+timedelta(days=offset)).date().isoformat()


def new_repair(post,**values):
    return post('/repairs/new',{'title':'A broken study lamp','category':'Electronics','description':'The switch does not respond. No visible damage or smoke.','area':'Petaling Jaya','safety':'safe','priority':'normal','weight':'1.5',**values})


def test_public_and_authentication(client,post,app):
    assert client.get('/').status_code==200
    assert client.get('/dashboard').status_code==302
    r=post('/login',{'email':'resident@looplocal.test','password':'wrong'})
    assert b'Email or password is incorrect' in r.data
    assert post('/login',{'email':'resident@looplocal.test','password':'LoopLocal2026!'}).status_code==302
    assert b'Hello, Amira' in client.get('/dashboard').data
    assert post('/logout').status_code==302
    assert client.get('/profile').status_code==302


def test_registration_cannot_grant_admin(client,post,app):
    data={'name':'New Neighbour','email':'new@example.com','password':'UniquePassword123','area':'Petaling Jaya','role':'admin'}
    assert post('/register',data).status_code==422
    data['role']='fixer'
    assert post('/register',data).status_code==422
    data['skills']='Electronics'
    assert post('/register',data).status_code==302
    assert read(app,'SELECT role FROM users WHERE email=?',('new@example.com',))[0]['role']=='fixer'
    post('/logout')
    assert post('/register',data).status_code==422


def test_csrf_and_security_headers(auth,client):
    auth(1)
    assert client.post('/logout',data={}).status_code==400
    r=client.get('/dashboard')
    assert r.headers['X-Frame-Options']=='DENY'
    assert "script-src 'self'" in r.headers['Content-Security-Policy']
    assert r.headers['Cache-Control']=='no-store'


@pytest.mark.parametrize('uid',[1,2,3])
def test_role_pages(auth,client,uid):
    auth(uid)
    for path in ['/dashboard','/repairs','/tools','/clinics','/impact','/profile','/notifications']:
        assert client.get(path).status_code==200,path
    assert client.get('/admin').status_code==(200 if uid==3 else 403)
    assert client.get('/impact/export.csv').status_code==(200 if uid==3 else 403)


def test_repair_end_to_end_and_private_passport(app,auth,post,client):
    auth(1)
    r=new_repair(post)
    assert r.status_code==302
    path=r.headers['Location'];tid=int(path.rsplit('/',1)[-1])
    assert b'Matching skill' in client.get(path).data
    auth(5)
    assert client.get(path).status_code==403
    assert post(path+'/messages',{'body':'Intruder'}).status_code==403
    auth(2)
    # Unassigned volunteers see the description but cannot read/post a private discussion.
    assert post(path+'/messages',{'body':'Not assigned yet'}).status_code==403
    assert post(path+'/claim').status_code==302
    assert post(path+'/claim').status_code==422
    assert post(path+'/messages',{'body':'Private note: call nobody@example.com'}).status_code==302
    assert post(path+'/status',{'status':'repaired','note':'Skipping the work is not allowed.'}).status_code==422
    assert post(path+'/status',{'status':'in_progress','note':'Checking the switch carefully.'}).status_code==302
    assert post(path+'/status',{'status':'repaired','note':'done'}).status_code==422
    assert post(path+'/status',{'status':'repaired','note':'Replaced the switch and checked safe low-voltage operation.'}).status_code==302
    record=read(app,'SELECT * FROM tickets WHERE id=?',(tid,))[0]
    passport='/passport/'+record['public_code']
    post('/logout')
    public=client.get(passport)
    assert public.status_code==200
    for private in [b'Amira Hassan',b'Daniel Tan',b'Private note',b'nobody@example.com',b'Petaling Jaya',b'Replaced the switch']:
        assert private not in public.data
    assert b'A broken study lamp' in public.data
    assert len(read(app,'SELECT * FROM history WHERE ticket_id=?',(tid,)))==4
    assert read(app,'SELECT * FROM notifications WHERE user_id=1 AND body LIKE ?',('%accepted your repair%',))


def test_owner_cannot_fake_completion(app,auth,post):
    auth(1)
    assert post('/repairs/5/status',{'status':'repaired','note':'I want to inflate the environmental statistics.'}).status_code==403
    assert read(app,'SELECT status FROM tickets WHERE id=5')[0]['status']=='in_progress'
    assert post('/repairs/5/status',{'status':'cancelled','note':'No longer needed, thanks.'}).status_code==302


def test_hazard_and_invalid_weights(app,auth,post):
    auth(1)
    before=len(read(app,'SELECT * FROM tickets'))
    for values in [{'safety':'hazard'},{'weight':'nan'},{'weight':'inf'},{'weight':'-1'},{'category':'Unlisted'},{'weight':'500.1'}]:
        assert new_repair(post,**values).status_code==422
    assert len(read(app,'SELECT * FROM tickets'))==before


def test_fixer_skills_and_limit(auth,post,app):
    auth(4)
    assert post('/repairs/1/claim').status_code==422
    auth(2)
    assert post('/repairs/1/claim').status_code==302
    auth(1)
    r=new_repair(post); path=r.headers['Location']
    auth(2);assert post(path+'/claim').status_code==302
    auth(1);r=new_repair(post)
    auth(2);assert post(r.headers['Location']+'/claim').status_code==422


def test_reservation_capacity_overlap_and_return(app,auth,post,client):
    auth(1)
    data={'start':day(),'end':day(2)}
    assert post('/tools/2/reserve',data).status_code==302
    assert post('/tools/2/reserve',data).status_code==422
    auth(5)
    assert post('/tools/2/reserve',data).status_code==422
    assert post('/tools/2/reserve',{'start':day(2),'end':day(3)}).status_code==422
    assert post('/tools/2/reserve',{'start':day(3),'end':day(4)}).status_code==302
    loan=read(app,'SELECT id FROM loans WHERE tool_id=2 AND user_id=1')[0]['id']
    assert post(f'/loans/{loan}/status',{'status':'returned'}).status_code==403
    assert post(f'/loans/{loan}/status',{'status':'cancelled'}).status_code==403
    auth(3)
    assert post(f'/loans/{loan}/status',{'status':'collected'}).status_code==302
    assert post(f'/loans/{loan}/status',{'status':'returned'}).status_code==302
    assert post(f'/loans/{loan}/status',{'status':'returned'}).status_code==403
    assert len(read(app,"SELECT * FROM loans WHERE status='returned'"))==1


def test_multiple_copies_count_each_day(app,auth,post):
    # Tool 1 has two copies. Sequential reservations do not consume two copies on one day.
    auth(1);assert post('/tools/1/reserve',{'start':day(1),'end':day(2)}).status_code==302
    auth(5);assert post('/tools/1/reserve',{'start':day(3),'end':day(4)}).status_code==302
    auth(2);assert post('/tools/1/reserve',{'start':day(1),'end':day(4)}).status_code==302
    auth(4);assert post('/tools/1/reserve',{'start':day(2),'end':day(3)}).status_code==422


@pytest.mark.parametrize('start,end',[(day(-1),day()),(day(),day(8)),(day(91),day(92)),(day(2),day(1)),('bad',day())])
def test_reservation_dates(auth,post,start,end):
    auth(1)
    assert post('/tools/1/reserve',{'start':start,'end':end}).status_code==422


def test_clinic_capacity_duplicates_cancellation(app,auth,post,client):
    write(app,'UPDATE clinics SET capacity=2 WHERE id=1')
    auth(5);assert post('/clinics/1/join').status_code==302
    assert post('/clinics/1/join').status_code==422
    auth(2);assert post('/clinics/1/join').status_code==422
    assert post('/clinics/1/cancel').status_code==403
    auth(5);assert post('/clinics/1/leave').status_code==302
    auth(2);assert post('/clinics/1/join').status_code==302
    auth(3);assert post('/clinics/1/cancel').status_code==302
    auth(5);assert post('/clinics/1/join').status_code==422
    assert read(app,"SELECT * FROM notifications WHERE user_id=2 AND body LIKE 'Clinic cancelled%'")


def test_clinic_creation_and_timezone(app,auth,post):
    auth(1)
    assert post('/clinics',{}).status_code==403
    auth(3)
    future=day(2)+'T10:30'
    r=post('/clinics',{'title':'Learn a repair skill','description':'Bring an item and learn how to care for it safely.','location':'Community hub 14','starts':future,'capacity':3})
    assert r.status_code==302
    record=read(app,'SELECT starts FROM clinics ORDER BY id DESC')[0]
    assert record['starts']==day(2)+'T02:30:00Z'


def test_impact_export_correct_and_anonymous(app,auth,client):
    auth(3)
    r=client.get('/impact/export.csv')
    assert r.status_code==200
    text=r.data.decode()
    assert len(text.strip().splitlines())==4
    assert 'Amira' not in text and '@' not in text
    assert 'repaired' in text
    assert b'17.3' in client.get('/impact').data # 12 + 0.8 + 4.5 kg


def test_profile_password_and_xss(app,auth,post,client):
    auth(1)
    assert post('/profile',{'action':'profile','name':'<script>alert(1)</script>','area':'Petaling Jaya'}).status_code==302
    assert b'<script>alert(1)</script>' not in client.get('/profile').data
    assert b'&lt;script&gt;' in client.get('/profile').data
    assert post('/profile',{'action':'password','current_password':'wrong','password':'NewPassword123!'}).status_code==422
    assert post('/profile',{'action':'password','current_password':'LoopLocal2026!','password':'NewPassword123!'}).status_code==302
    post('/logout')
    assert post('/login',{'email':'resident@looplocal.test','password':'NewPassword123!'}).status_code==302


def test_admin_retire_and_disable(app,auth,post):
    auth(3)
    assert post('/admin',{'action':'toggle_user','user_id':1}).status_code==422
    assert post('/admin',{'action':'toggle_user','user_id':3}).status_code==422
    assert post('/admin',{'action':'toggle_user','user_id':4}).status_code==302
    auth(4)
    assert post('/repairs/2/claim').status_code==400 # stale CSRF rejected after inactive session is cleared
    assert read(app,'SELECT fixer_id FROM tickets WHERE id=2')[0]['fixer_id'] is None
    auth(3)
    assert post('/admin',{'action':'toggle_tool','tool_id':1}).status_code==302
    auth(1)
    assert post('/tools/1/reserve',{'start':day(),'end':day()}).status_code==404


def test_rate_limit(client,post):
    for i in range(15):
        assert post('/login',{'email':'missing@example.com','password':'wrong'}).status_code==200
    assert post('/login',{'email':'missing@example.com','password':'wrong'}).status_code==429


def test_init_and_seed_are_repeatable(app):
    before=len(read(app,'SELECT * FROM tickets'))
    assert app.test_cli_runner().invoke(args=['init-db']).exit_code==0
    assert app.test_cli_runner().invoke(args=['seed-demo']).exit_code==0
    assert len(read(app,'SELECT * FROM tickets'))==before


def test_anonymous_passport_only_after_repair(app,client):
    pending=read(app,'SELECT public_code FROM tickets WHERE id=1')[0]['public_code']
    assert client.get('/passport/'+pending).status_code==404
    assert client.get('/passport/nonexistent').status_code==404


def test_health_and_missing_routes(client):
    assert client.get('/health').json['status']=='ok'
    assert client.get('/does-not-exist').status_code==404


def test_overdue_tools_are_not_repromised(app,auth,post):
    write(app,"INSERT INTO loans(tool_id,user_id,start,end,status,created) VALUES(2,5,?,?,'collected','2026-01-01T00:00:00Z')",(day(-4),day(-1)))
    auth(1)
    assert post('/tools/2/reserve',{'start':day(2),'end':day(3)}).status_code==422


def test_concurrent_last_copy_and_last_place(app):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    barrier=Barrier(2)
    def reserve(uid):
        with app.test_client() as client:
            with client.session_transaction() as s:
                s['uid']=uid;s['csrf']='race-token'
            barrier.wait(timeout=10)
            return client.post('/tools/2/reserve',data={'csrf':'race-token','start':day(),'end':day(1)}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(reserve,[1,5]))
    assert sorted(outcomes)==[302,422]
    assert len(read(app,"SELECT * FROM loans WHERE tool_id=2 AND status='reserved'"))==1
    write(app,'UPDATE clinics SET capacity=2 WHERE id=1')
    barrier=Barrier(2)
    def join(uid):
        with app.test_client() as client:
            with client.session_transaction() as s:
                s['uid']=uid;s['csrf']='race-token'
            barrier.wait(timeout=10)
            return client.post('/clinics/1/join',data={'csrf':'race-token'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(join,[2,5]))
    assert sorted(outcomes)==[302,422]
    assert len(read(app,'SELECT * FROM signups WHERE clinic_id=1'))==2


def test_concurrent_claim_is_exclusive(app):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    write(app,"UPDATE users SET skills='Electronics' WHERE id=6")
    barrier=Barrier(2)
    def claim(uid):
        with app.test_client() as client:
            with client.session_transaction() as s:
                s['uid']=uid;s['csrf']='claim-token'
            barrier.wait(timeout=10)
            return client.post('/repairs/1/claim',data={'csrf':'claim-token'}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(claim,[2,6]))
    assert sorted(outcomes)==[302,403] # once assigned, other volunteers lose access
    assert len(read(app,"SELECT * FROM history WHERE ticket_id=1 AND status='assigned'"))==1


def test_checkout_requires_a_physical_copy(app,auth,post):
    write(app,"INSERT INTO loans(tool_id,user_id,start,end,status,created) VALUES(2,5,?,?,'collected','2026-01-01T00:00:00Z')",(day(-4),day(-1)))
    # This booking existed before the earlier borrower became overdue.
    lid=write(app,"INSERT INTO loans(tool_id,user_id,start,end,status,created) VALUES(2,1,?,?,'reserved','2026-01-01T00:00:00Z')",(day(),day(2)))
    auth(3)
    assert post(f'/loans/{lid}/status',{'status':'collected'}).status_code==422
    assert read(app,'SELECT status FROM loans WHERE id=?',(lid,))[0]['status']=='reserved'
