import csv
import functools
import io
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
from flask import Flask, abort, flash, g, redirect, render_template, request, session, url_for, Response
from werkzeug.security import check_password_hash, generate_password_hash

CATEGORIES = {'Electronics': (18.0, '◈'), 'Appliances': (12.0, '⌁'), 'Bicycles': (6.0, '◎'), 'Furniture': (3.0, '▱'), 'Textiles': (8.0, '✂'), 'Other': (4.0, '◇')}
AREAS = ['Petaling Jaya', 'Kuala Lumpur', 'Subang Jaya', 'Shah Alam', 'Other']
STATES = {'assigned': ['in_progress', 'cancelled'], 'in_progress': ['repaired', 'unrepairable', 'cancelled'], 'open': ['cancelled']}

def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

def local_today():
    return datetime.now(timezone(timedelta(hours=8))).date()

def db():
    if 'db' not in g:
        g.db = sqlite3.connect(g.app_db, timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db

def rows(sql, args=()):
    return db().execute(sql, args).fetchall()

def one(sql, args=()):
    return db().execute(sql, args).fetchone()

def execute(sql, args=()):
    return db().execute(sql, args)

def text(name, minimum=1, maximum=200):
    value = request.form.get(name, '').strip()
    if not minimum <= len(value) <= maximum:
        raise ValueError(f'{name.replace("_", " ").capitalize()} must contain {minimum}–{maximum} characters.')
    return value

def choice(name, allowed):
    value = text(name)
    if value not in allowed:
        raise ValueError(f'Choose a valid {name.replace("_", " ")}.')
    return value

def integer(name, low, high):
    try:
        value = int(request.form.get(name, ''))
    except ValueError:
        raise ValueError(f'{name.capitalize()} must be a whole number.')
    if not low <= value <= high:
        raise ValueError(f'{name.capitalize()} must be between {low} and {high}.')
    return value

def notify(user_id, body, link):
    execute('INSERT INTO notifications(user_id,body,link,created) VALUES(?,?,?,?)', (user_id, body, link, now()))

def audit(action, detail):
    execute('INSERT INTO audit(actor_id,action,detail,created) VALUES(?,?,?,?)', (g.user['id'] if g.user else None, action, detail, now()))

def login_required(fn):
    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for('login'))
        return fn(*args, **kwargs)
    return wrapped

def roles(*allowed):
    def deco(fn):
        @functools.wraps(fn)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user['role'] not in allowed:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return deco

def ticket_access(ticket_id):
    ticket = one('SELECT t.*,u.name owner,f.name fixer FROM tickets t JOIN users u ON u.id=t.owner_id LEFT JOIN users f ON f.id=t.fixer_id WHERE t.id=?', (ticket_id,))
    if not ticket:
        abort(404)
    if g.user['role'] != 'admin' and g.user['id'] not in (ticket['owner_id'], ticket['fixer_id']):
        if not (g.user['role'] == 'fixer' and ticket['status'] == 'open'):
            abort(403)
    return ticket

def matches(ticket):
    result = []
    for user in rows("SELECT u.*, (SELECT count(*) FROM tickets t WHERE t.fixer_id=u.id AND t.status IN ('assigned','in_progress')) workload FROM users u WHERE u.role='fixer' AND u.active=1 AND u.id!=?", (ticket['owner_id'],)):
        skill = ticket['category'] in user['skills'].split(',')
        local = ticket['area'] == user['area']
        score = (60 if skill else 0) + (25 if local else 0) + max(0, 15 - user['workload'] * 5)
        result.append({'user': user, 'score': score, 'skill': skill, 'local': local})
    return sorted(result, key=lambda m: (-m['score'], m['user']['workload'], m['user']['id']))[:3]

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    secret_path = Path(app.instance_path) / 'session.key'
    if not secret_path.exists():
        try:
            fd = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'w') as file:
                file.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    app.config.update(SECRET_KEY=os.environ.get('SECRET_KEY') or secret_path.read_text(), DATABASE=str(Path(app.instance_path) / 'looplocal.sqlite'), MAX_CONTENT_LENGTH=64*1024,
                      SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax', SESSION_COOKIE_SECURE=os.environ.get('COOKIE_SECURE') == '1', PERMANENT_SESSION_LIFETIME=timedelta(hours=12))
    if test_config:
        app.config.update(test_config)

    @app.before_request
    def before():
        g.app_db = app.config['DATABASE']
        g.user = None
        if session.get('uid'):
            g.user = one('SELECT * FROM users WHERE id=? AND active=1', (session['uid'],))
            if not g.user:
                session.clear()
        if 'csrf' not in session:
            session['csrf'] = secrets.token_hex(24)
        if request.method == 'POST':
            if not secrets.compare_digest(session['csrf'], request.form.get('csrf', '')):
                abort(400, 'Your form expired. Reload the page and try again.')
            db().execute('BEGIN IMMEDIATE')

    @app.after_request
    def after(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        response.headers['Cache-Control'] = 'no-store'
        if 'db' in g:
            if response.status_code < 400:
                g.db.commit()
            else:
                g.db.rollback()
        return response

    @app.teardown_appcontext
    def close(error=None):
        connection = g.pop('db', None)
        if connection:
            connection.close()

    @app.context_processor
    def context():
        unread = one('SELECT count(*) n FROM notifications WHERE user_id=? AND seen=0', (g.user['id'],))['n'] if g.user else 0
        return dict(categories=CATEGORIES, areas=AREAS, unread=unread, today=local_today().isoformat(), csrf=session.get('csrf'), current_year=datetime.now().year)

    @app.template_filter('date')
    def date_filter(value):
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone(timedelta(hours=8))).strftime('%d %b %Y, %H:%M')
        except ValueError:
            return value

    @app.errorhandler(ValueError)
    def invalid(error):
        db().rollback()
        return render_template('error.html', code=422, message=str(error)), 422

    for code in (400, 403, 404, 413, 429, 500):
        def handler(error, code=code):
            return render_template('error.html', code=code, message=error.description if code != 500 else 'Something went wrong. Please try again.'), code
        app.register_error_handler(code, handler)

    @app.get('/health')
    def health():
        one('SELECT id FROM users LIMIT 1')
        return {'status': 'ok', 'service': 'LoopLocal'}

    @app.get('/')
    def home():
        if g.user:
            return redirect(url_for('dashboard'))
        stats = impact_stats()
        return render_template('home.html', stats=stats)

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            name, email, password = text('name', 2, 80), text('email', 5, 120).lower(), text('password', 10, 128)
            if '@' not in email or '.' not in email.split('@')[-1] or ' ' in email:
                raise ValueError('Enter a valid email address.')
            role = choice('role', ['resident', 'fixer'])
            area = choice('area', AREAS)
            skills = ','.join(s for s in request.form.getlist('skills') if s in CATEGORIES)
            if role == 'fixer' and not skills:
                raise ValueError('Select at least one repair skill.')
            if one('SELECT id FROM users WHERE email=?', (email,)):
                raise ValueError('This email is already registered. Sign in instead.')
            uid = execute('INSERT INTO users(name,email,password,role,area,skills) VALUES(?,?,?,?,?,?)', (name,email,generate_password_hash(password),role,area,skills)).lastrowid
            session.clear(); session['uid'] = uid; session.permanent = True
            flash('Welcome to the loop! Your account is ready.', 'success')
            return redirect(url_for('dashboard'))
        return render_template('auth.html', mode='register')

    @app.route('/login', methods=['GET','POST'])
    def login():
        if request.method == 'POST':
            ip = request.remote_addr or 'unknown'
            cutoff = int(time.time()) - 900
            execute('DELETE FROM login_attempts WHERE happened<?', (cutoff,))
            if one('SELECT count(*) n FROM login_attempts WHERE ip=?', (ip,))['n'] >= 15:
                abort(429, 'Too many sign-in attempts. Try again in 15 minutes.')
            user = one('SELECT * FROM users WHERE email=?', (text('email', 3, 120).lower(),))
            password = text('password', 1, 128)
            if not user or not check_password_hash(user['password'], password) or not user['active']:
                execute('INSERT INTO login_attempts VALUES(?,?)', (ip, int(time.time())))
                flash('Email or password is incorrect, or the account is inactive.', 'error')
                return render_template('auth.html', mode='login')
            execute('DELETE FROM login_attempts WHERE ip=?', (ip,))
            session.clear(); session['uid'] = user['id']; session.permanent = True
            return redirect(url_for('dashboard'))
        return render_template('auth.html', mode='login')

    @app.post('/logout')
    def logout():
        session.clear()
        return redirect(url_for('home'))

    @app.get('/dashboard')
    @login_required
    def dashboard():
        uid = g.user['id']
        personal = rows('SELECT * FROM tickets WHERE owner_id=? OR fixer_id=? ORDER BY updated DESC LIMIT 5', (uid,uid))
        loans = rows("SELECT l.*,t.name FROM loans l JOIN tools t ON t.id=l.tool_id WHERE l.user_id=? AND l.status IN ('reserved','collected') ORDER BY l.end", (uid,))
        clinics = rows('SELECT c.*, (SELECT count(*) FROM signups s WHERE s.clinic_id=c.id) joined FROM clinics c WHERE cancelled=0 AND starts>? ORDER BY starts LIMIT 3', (now(),))
        return render_template('dashboard.html', stats=impact_stats(), tickets=personal, loans=loans, clinics=clinics)

    @app.get('/repairs')
    @login_required
    def repairs():
        scope = request.args.get('scope', 'mine')
        where, params = [], []
        if scope == 'community' and g.user['role'] in ('fixer', 'admin'):
            if g.user['role'] == 'fixer':
                where.append("(t.status='open' OR t.fixer_id=? OR t.owner_id=?)");params.extend([g.user['id'], g.user['id']])
        else:
            scope = 'mine'
            where.append('(t.owner_id=? OR t.fixer_id=?)');params.extend([g.user['id'],g.user['id']])
        q = request.args.get('q', '').strip()[:100]
        state = request.args.get('status', '')
        if q:
            where.append('(t.title LIKE ? OR t.category LIKE ?)'); params.extend([f'%{q}%', f'%{q}%'])
        if state in ('open','assigned','in_progress','repaired','unrepairable','cancelled'):
            where.append('t.status=?'); params.append(state)
        tickets = rows('SELECT t.*,u.name owner FROM tickets t JOIN users u ON u.id=t.owner_id '+('WHERE '+' AND '.join(where) if where else '')+' ORDER BY t.created DESC', params)
        return render_template('repairs.html', tickets=tickets, scope=scope, q=q, state=state)

    @app.route('/repairs/new', methods=['GET','POST'])
    @login_required
    def repair_new():
        if request.method == 'POST':
            title, category = text('title', 5, 100), choice('category', CATEGORIES)
            description, area = text('description', 20, 2000), choice('area', AREAS)
            safety = choice('safety', ['safe', 'unsure', 'hazard'])
            priority = choice('priority', ['normal','essential'])
            try:
                weight = float(request.form.get('weight',''))
            except ValueError:
                raise ValueError('Enter an estimated weight in kilograms.')
            if not 0 < weight <= 500:
                raise ValueError('Weight must be greater than 0 and at most 500 kg.')
            if safety == 'hazard':
                raise ValueError('For smoke, swollen batteries, exposed mains wiring or chemical leaks, stop use and contact a qualified professional. Hazardous items cannot enter volunteer repair.')
            tid = execute('INSERT INTO tickets(owner_id,title,category,description,area,safety,priority,weight,public_code,created,updated) VALUES(?,?,?,?,?,?,?,?,?,?,?)', (g.user['id'],title,category,description,area,safety,priority,weight,secrets.token_urlsafe(18),now(),now())).lastrowid
            execute('INSERT INTO history(ticket_id,user_id,status,note,created) VALUES(?,?,?,?,?)', (tid,g.user['id'],'open','Repair request created.',now()))
            audit('repair.created', str(tid))
            flash('Request created. Explore your suggested repair partners below.', 'success')
            return redirect(url_for('repair_detail', ticket_id=tid))
        return render_template('repair_new.html')

    @app.get('/repairs/<int:ticket_id>')
    @login_required
    def repair_detail(ticket_id):
        ticket = ticket_access(ticket_id)
        return render_template('repair_detail.html', ticket=ticket, matches=matches(ticket) if ticket['status']=='open' else [],
                               history=rows('SELECT h.*,u.name FROM history h JOIN users u ON u.id=h.user_id WHERE ticket_id=? ORDER BY h.id', (ticket_id,)),
                               messages=rows('SELECT m.*,u.name FROM messages m JOIN users u ON u.id=m.user_id WHERE ticket_id=? ORDER BY m.id', (ticket_id,)), transitions=STATES.get(ticket['status'],[]))

    @app.post('/repairs/<int:ticket_id>/claim')
    @roles('fixer')
    def claim(ticket_id):
        ticket = ticket_access(ticket_id)
        if ticket['status'] != 'open' or ticket['owner_id'] == g.user['id']:
            raise ValueError('This request is no longer available to claim.')
        if ticket['category'] not in g.user['skills'].split(','):
            raise ValueError('Add the matching repair skill to your profile before claiming this item.')
        if one("SELECT count(*) n FROM tickets WHERE fixer_id=? AND status IN ('assigned','in_progress')", (g.user['id'],))['n'] >= 3:
            raise ValueError('Finish an active repair first. Each volunteer can hold up to three active repairs.')
        execute("UPDATE tickets SET fixer_id=?,status='assigned',updated=? WHERE id=?", (g.user['id'],now(),ticket_id))
        execute('INSERT INTO history(ticket_id,user_id,status,note,created) VALUES(?,?,?,?,?)', (ticket_id,g.user['id'],'assigned','Volunteer accepted the repair.',now()))
        notify(ticket['owner_id'], f'{g.user["name"]} accepted your repair: {ticket["title"]}', f'/repairs/{ticket_id}')
        audit('repair.claimed', str(ticket_id))
        return redirect(url_for('repair_detail', ticket_id=ticket_id))

    @app.post('/repairs/<int:ticket_id>/status')
    @login_required
    def repair_status(ticket_id):
        ticket = ticket_access(ticket_id)
        target, note = text('status'), text('note', 5, 1000)
        if target not in STATES.get(ticket['status'], []):
            raise ValueError('That status transition is not allowed.')
        is_operator = g.user['role']=='admin' or g.user['id']==ticket['fixer_id']
        if not is_operator and not (target=='cancelled' and g.user['id']==ticket['owner_id']):
            abort(403)
        if target == 'repaired' and len(note) < 20:
            raise ValueError('Document the repair and safety checks in at least 20 characters.')
        execute('UPDATE tickets SET status=?,updated=? WHERE id=?', (target,now(),ticket_id))
        execute('INSERT INTO history(ticket_id,user_id,status,note,created) VALUES(?,?,?,?,?)', (ticket_id,g.user['id'],target,note,now()))
        for uid in {ticket['owner_id'], ticket['fixer_id']} - {None, g.user['id']}:
            notify(uid, f'{ticket["title"]}: {target.replace("_"," ")}', f'/repairs/{ticket_id}')
        audit('repair.'+target, str(ticket_id))
        flash('Repair record updated.', 'success')
        return redirect(url_for('repair_detail', ticket_id=ticket_id))

    @app.post('/repairs/<int:ticket_id>/messages')
    @login_required
    def message(ticket_id):
        ticket = ticket_access(ticket_id)
        if g.user['role']!='admin' and g.user['id'] not in (ticket['owner_id'],ticket['fixer_id']):
            abort(403)
        body = text('body', 1, 1500)
        execute('INSERT INTO messages(ticket_id,user_id,body,created) VALUES(?,?,?,?)', (ticket_id,g.user['id'],body,now()))
        for uid in {ticket['owner_id'],ticket['fixer_id']} - {None,g.user['id']}:
            notify(uid, f'New message about {ticket["title"]}', f'/repairs/{ticket_id}')
        return redirect(url_for('repair_detail', ticket_id=ticket_id))

    @app.get('/passport/<code>')
    def passport(code):
        ticket = one('SELECT id,title,category,status,weight,public_code,created FROM tickets WHERE public_code=? AND status=?', (code,'repaired'))
        if not ticket:
            abort(404)
        # Public passport deliberately excludes names, location, messages and free-text repair notes.
        history = rows('SELECT status,created FROM history WHERE ticket_id=? ORDER BY id', (ticket['id'],))
        return render_template('passport.html', ticket=ticket, history=history, co2=round(ticket['weight']*CATEGORIES[ticket['category']][0],1))

    @app.get('/tools')
    @login_required
    def tools():
        q = request.args.get('q','').strip()[:100]
        items = rows('SELECT * FROM tools WHERE active=1 AND (name LIKE ? OR category LIKE ?) ORDER BY name', (f'%{q}%',f'%{q}%'))
        loans = rows('SELECT l.*,t.name,u.name borrower FROM loans l JOIN tools t ON t.id=l.tool_id JOIN users u ON u.id=l.user_id '+('' if g.user['role']=='admin' else 'WHERE l.user_id=? ')+'ORDER BY l.created DESC', () if g.user['role']=='admin' else (g.user['id'],))
        return render_template('tools.html', tools=items, loans=loans, q=q)

    @app.post('/tools/<int:tool_id>/reserve')
    @login_required
    def reserve(tool_id):
        tool = one('SELECT * FROM tools WHERE id=? AND active=1', (tool_id,))
        if not tool:
            abort(404)
        try:
            start = datetime.strptime(text('start'), '%Y-%m-%d').date()
            end = datetime.strptime(text('end'), '%Y-%m-%d').date()
        except ValueError:
            raise ValueError('Choose valid collection and return dates.')
        today = local_today()
        if start < today or end < start or (end-start).days > 6 or start > today+timedelta(days=90):
            raise ValueError('Reserve within the next 90 days for up to 7 days. Return date cannot precede collection.')
        # Count every day independently: sequential reservations must not be mistaken for simultaneous use.
        for offset in range((end-start).days+1):
            day = (start+timedelta(days=offset)).isoformat()
            booked = one("SELECT count(*) n FROM loans WHERE tool_id=? AND status IN ('reserved','collected') AND ((start<=? AND end>=?) OR (status='collected' AND end<?))", (tool_id,day,day,today.isoformat()))['n']
            if booked >= tool['total']:
                raise ValueError(f'All copies are reserved or awaiting an overdue return on {day}. Choose different dates or contact the hub.')
        if one("SELECT id FROM loans WHERE tool_id=? AND user_id=? AND status IN ('reserved','collected') AND start<=? AND end>=?", (tool_id,g.user['id'],end.isoformat(),start.isoformat())):
            raise ValueError('You already have an overlapping reservation for this tool.')
        lid = execute('INSERT INTO loans(tool_id,user_id,start,end,created) VALUES(?,?,?,?,?)', (tool_id,g.user['id'],start.isoformat(),end.isoformat(),now())).lastrowid
        audit('loan.reserved', str(lid))
        flash('Tool reserved. An administrator will check it out at the community hub.', 'success')
        return redirect(url_for('tools'))

    @app.post('/loans/<int:loan_id>/status')
    @login_required
    def loan_status(loan_id):
        loan = one('SELECT * FROM loans WHERE id=?', (loan_id,))
        if not loan:
            abort(404)
        target = text('status')
        if target=='cancelled' and loan['status']=='reserved' and (loan['user_id']==g.user['id'] or g.user['role']=='admin'):
            pass
        elif g.user['role']=='admin' and (loan['status'],target) in [('reserved','collected'),('collected','returned')]:
            if target=='collected' and not loan['start'] <= local_today().isoformat() <= loan['end']:
                raise ValueError('Check-out is only available during the reserved dates.')
            if target=='collected':
                total=one('SELECT total FROM tools WHERE id=?',(loan['tool_id'],))['total']
                out=one("SELECT count(*) n FROM loans WHERE tool_id=? AND status='collected'",(loan['tool_id'],))['n']
                if out>=total:
                    raise ValueError('All copies are still checked out. Record a return before handing out this tool.')
        else:
            abort(403)
        execute('UPDATE loans SET status=? WHERE id=?', (target,loan_id))
        notify(loan['user_id'], f'Tool reservation #{loan_id}: {target}', '/tools')
        audit('loan.'+target, str(loan_id))
        return redirect(url_for('tools'))

    @app.route('/clinics', methods=['GET','POST'])
    @login_required
    def clinics():
        if request.method=='POST':
            if g.user['role']!='admin':
                abort(403)
            title, description, location = text('title',5,100),text('description',20,1500),text('location',5,150)
            capacity = integer('capacity',1,500)
            try:
                local = datetime.fromisoformat(text('starts'))
                starts = local.replace(tzinfo=timezone(timedelta(hours=8))).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            except ValueError:
                raise ValueError('Choose a valid date and time (Malaysia time).')
            if starts <= now():
                raise ValueError('Clinics must start in the future.')
            cid=execute('INSERT INTO clinics(title,description,location,starts,capacity,host_id) VALUES(?,?,?,?,?,?)', (title,description,location,starts,capacity,g.user['id'])).lastrowid
            audit('clinic.created',str(cid))
            flash('Repair clinic published.', 'success')
            return redirect(url_for('clinics'))
        events = rows('SELECT c.*,u.name host,(SELECT count(*) FROM signups s WHERE s.clinic_id=c.id) joined,EXISTS(SELECT 1 FROM signups s WHERE s.clinic_id=c.id AND s.user_id=?) attending FROM clinics c JOIN users u ON u.id=c.host_id ORDER BY c.starts DESC', (g.user['id'],))
        return render_template('clinics.html', clinics=events, utc_now=now())

    @app.post('/clinics/<int:clinic_id>/<action>')
    @login_required
    def clinic_action(clinic_id,action):
        clinic = one('SELECT * FROM clinics WHERE id=?', (clinic_id,))
        if not clinic:
            abort(404)
        if action=='cancel':
            if g.user['role']!='admin': abort(403)
            execute('UPDATE clinics SET cancelled=1 WHERE id=?',(clinic_id,))
            for user in rows('SELECT user_id FROM signups WHERE clinic_id=?',(clinic_id,)):
                notify(user['user_id'],f'Clinic cancelled: {clinic["title"]}','/clinics')
            audit('clinic.cancelled',str(clinic_id))
        elif action=='leave':
            execute('DELETE FROM signups WHERE clinic_id=? AND user_id=?',(clinic_id,g.user['id']))
        elif action=='join':
            if clinic['cancelled'] or clinic['starts'] <= now(): raise ValueError('This clinic is no longer accepting registrations.')
            if one('SELECT 1 FROM signups WHERE clinic_id=? AND user_id=?',(clinic_id,g.user['id'])):
                raise ValueError('You are already registered.')
            if one('SELECT count(*) n FROM signups WHERE clinic_id=?',(clinic_id,))['n'] >= clinic['capacity']:
                raise ValueError('This clinic is full. Please try another event.')
            execute('INSERT INTO signups VALUES(?,?)',(clinic_id,g.user['id']))
            notify(g.user['id'],f'You are registered: {clinic["title"]}','/clinics')
        else: abort(404)
        return redirect(url_for('clinics'))

    @app.get('/impact')
    @login_required
    def impact():
        return render_template('impact.html',stats=impact_stats(),breakdown=rows("SELECT category,count(*) count,round(sum(weight),1) weight FROM tickets WHERE status='repaired' GROUP BY category ORDER BY count DESC"))

    @app.get('/impact/export.csv')
    @roles('admin')
    def export():
        output = io.StringIO(); writer = csv.writer(output)
        writer.writerow(['Repair ID','Category','Status','Weight kg','Estimated avoided kg CO2e','Completed UTC'])
        for t in rows("SELECT * FROM tickets WHERE status='repaired' ORDER BY id"):
            writer.writerow([t['id'],t['category'],t['status'],t['weight'],round(t['weight']*CATEGORIES[t['category']][0],1),t['updated']])
        return Response(output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=looplocal-impact.csv'})

    @app.route('/profile', methods=['GET','POST'])
    @login_required
    def profile():
        if request.method=='POST':
            if request.form.get('action')=='password':
                if not check_password_hash(g.user['password'],text('current_password',1,128)):
                    raise ValueError('Current password is incorrect.')
                password=text('password',10,128)
                execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(password),g.user['id']))
                session['csrf']=secrets.token_hex(24)
                flash('Password updated.', 'success')
            else:
                name, area = text('name',2,80),choice('area',AREAS)
                skills=','.join(s for s in request.form.getlist('skills') if s in CATEGORIES)
                if g.user['role']=='fixer' and not skills: raise ValueError('Keep at least one repair skill.')
                execute('UPDATE users SET name=?,area=?,skills=? WHERE id=?',(name,area,skills,g.user['id']))
                flash('Profile saved.', 'success')
            return redirect(url_for('profile'))
        return render_template('profile.html')

    @app.route('/notifications',methods=['GET','POST'])
    @login_required
    def notifications():
        if request.method=='POST':
            execute('UPDATE notifications SET seen=1 WHERE user_id=?',(g.user['id'],))
            return redirect(url_for('notifications'))
        return render_template('notifications.html',notifications=rows('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 100',(g.user['id'],)))

    @app.route('/admin',methods=['GET','POST'])
    @roles('admin')
    def admin():
        if request.method=='POST':
            action=text('action')
            if action=='tool':
                execute('INSERT INTO tools(name,category,description,area,total) VALUES(?,?,?,?,?)',(text('name',3,100),choice('category',CATEGORIES),text('description',10,1000),choice('area',AREAS),integer('total',1,100)))
                audit('tool.created','New tool added')
            elif action=='toggle_tool':
                tid=integer('tool_id',1,2147483647)
                execute('UPDATE tools SET active=1-active WHERE id=?',(tid,));audit('tool.toggled',str(tid))
            elif action=='toggle_user':
                uid=integer('user_id',1,2147483647)
                user=one('SELECT * FROM users WHERE id=?',(uid,))
                if not user: abort(404)
                if user['role']=='admin': raise ValueError('Administrator accounts cannot be disabled here.')
                if user['active'] and (one("SELECT id FROM tickets WHERE (owner_id=? OR fixer_id=?) AND status IN ('open','assigned','in_progress')",(uid,uid)) or one("SELECT id FROM loans WHERE user_id=? AND status IN ('reserved','collected')",(uid,))):
                    raise ValueError('Resolve active repairs and tool loans before disabling this account.')
                execute('UPDATE users SET active=1-active WHERE id=?',(uid,));audit('user.toggled',str(uid))
            else: abort(400)
            flash('Administration change saved.', 'success')
            return redirect(url_for('admin'))
        return render_template('admin.html',users=rows('SELECT id,name,email,role,active FROM users ORDER BY id'),tools=rows('SELECT * FROM tools ORDER BY id'),audit=rows('SELECT a.*,u.name FROM audit a LEFT JOIN users u ON u.id=a.actor_id ORDER BY a.id DESC LIMIT 50'),stats=impact_stats())

    @app.cli.command('init-db')
    def init_command():
        init_db(app)
        click.echo('Database schema ready (existing data preserved).')

    @app.cli.command('create-admin')
    @click.option('--email', prompt=True)
    @click.option('--name', prompt=True)
    @click.password_option(confirmation_prompt=True)
    def admin_command(email,name,password):
        if len(password)<10: raise click.ClickException('Password must contain at least 10 characters.')
        g.app_db=app.config['DATABASE']
        if one('SELECT id FROM users WHERE email=?',(email,)): raise click.ClickException('Email already exists.')
        execute("INSERT INTO users(name,email,password,role) VALUES(?,?,?,'admin')",(name,email.lower(),generate_password_hash(password)));db().commit()
        click.echo('Administrator created.')

    @app.cli.command('seed-demo')
    def seed_command():
        from .seed import seed
        g.app_db=app.config['DATABASE']; seed(); db().commit()
        click.echo('Demo data ready. Local demo accounts: resident@looplocal.test, fixer@looplocal.test, admin@looplocal.test. Password: LoopLocal2026! Change passwords before any shared deployment.')

    return app

def init_db(app):
    with sqlite3.connect(app.config['DATABASE']) as connection:
        connection.executescript(Path(__file__).with_name('schema.sql').read_text())
        connection.execute('PRAGMA journal_mode=WAL')

def impact_stats():
    repaired=rows("SELECT category,weight FROM tickets WHERE status='repaired'")
    return dict(repaired=len(repaired),waste=round(sum(t['weight'] for t in repaired),1),co2=round(sum(t['weight']*CATEGORIES[t['category']][0] for t in repaired),1),
                volunteers=one("SELECT count(*) n FROM users WHERE role='fixer' AND active=1")['n'],open=one("SELECT count(*) n FROM tickets WHERE status IN ('open','assigned','in_progress')")['n'],
                tools=one('SELECT coalesce(sum(total),0) n FROM tools WHERE active=1')['n'],loans=one("SELECT count(*) n FROM loans WHERE status='returned'")['n'])
