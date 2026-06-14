import json
import os
import uuid
from datetime import datetime, timedelta
from functools import wraps
from io import BytesIO

from dotenv import load_dotenv
from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, g, flash, send_file)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import Config
from init_db import get_db, setup_db

# 加载 .env 文件中的环境变量（必须在读取 Config 之前）
load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# 启动时自动初始化数据库（建表 + 种子数据）
setup_db()


# ── helpers ──────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash('无权访问')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def get_current_user():
    if 'user_id' in session:
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
        db.close()
        return dict(user) if user else None
    return None

LEVEL_THRESHOLDS = [0, 200, 600, 1200, 2000, 3000, 4500, 6500, 9000, 12000]
LEVEL_TITLES = ['萌新实习生', '初入职场', '渐入佳境', '独当一面', '团队骨干',
                '技术能手', '业务专家', '全栈达人', '准正式员工', '转正预备']

def calc_level(xp):
    for i in range(len(LEVEL_THRESHOLDS) - 1, -1, -1):
        if xp >= LEVEL_THRESHOLDS[i]:
            return i + 1
    return 1

def xp_for_next_level(current_level):
    if current_level >= 10:
        return LEVEL_THRESHOLDS[9]
    return LEVEL_THRESHOLDS[current_level]

DIMENSION_NAMES = ['技术能力', '沟通协作', '业务理解', '主动成长', '问题解决', '工程素养']


@app.context_processor
def inject_globals():
    user = get_current_user()
    role_colors = {
        'intern': {'primary': '#F5A623', 'primary_dark': '#E09000', 'primary_light': '#FFD180', 'bg': '#FFF8E1'},
        'mentor': {'primary': '#4CAF50', 'primary_dark': '#388E3C', 'primary_light': '#A5D6A7', 'bg': '#E8F5E9'},
        'leader': {'primary': '#9C27B0', 'primary_dark': '#7B1FA2', 'primary_light': '#CE93D8', 'bg': '#F3E5F5'},
        'admin': {'primary': '#607D8B', 'primary_dark': '#455A64', 'primary_light': '#B0BEC5', 'bg': '#ECEFF1'}
    }
    theme = role_colors.get(user['role'], role_colors['intern']) if user else role_colors['intern']
    return dict(current_user=user, now=datetime.now(), theme=theme)


# ── Auth ─────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        role_param = request.args.get('role', '')
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
        db.close()
        if user and check_password_hash(user['password_hash'], password):
            # 检查用户角色是否与登录页面的角色匹配
            if role_param and user['role'] != role_param:
                flash('该账号不是此身份，请使用对应的登录入口')
                return redirect(url_for('login', role=role_param))
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['name'] = user['name']
            return redirect(url_for('dashboard'))
        flash('邮箱或密码错误')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        role = request.form.get('role', 'intern')
        department = request.form.get('department', '').strip()
        position = request.form.get('position', '').strip()

        if not email or not password or not name:
            flash('请填写所有必填项')
            return render_template('register.html')

        db = get_db()
        exists = db.execute('SELECT id FROM users WHERE email=?', (email,)).fetchone()
        if exists:
            flash('该邮箱已注册')
            db.close()
            return render_template('register.html')

        pwd_hash = generate_password_hash(password)
        cur = db.execute(
            'INSERT INTO users (email, password_hash, name, role, department, position) VALUES (?,?,?,?,?,?)',
            (email, pwd_hash, name, role, department, position)
        )
        user_id = cur.lastrowid

        if role == 'intern':
            db.execute(
                'INSERT INTO intern_profiles (user_id, start_date, level, xp, status) VALUES (?,?,1,0,?)',
                (user_id, datetime.now().date().isoformat(), 'active')
            )
            profile_id = db.execute('SELECT id FROM intern_profiles WHERE user_id=?', (user_id,)).fetchone()[0]
            for dim_id in range(1, 7):
                db.execute(
                    'INSERT INTO skill_scores (intern_id, dimension_id, score) VALUES (?,?,50)',
                    (profile_id, dim_id)
                )

        db.commit()
        db.close()

        session['user_id'] = user_id
        session['role'] = role
        session['name'] = name
        return redirect(url_for('dashboard'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    role = session.get('role', '')
    session.clear()
    return redirect(url_for('login', role=role))


# ── Dashboard Router ─────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    role = session.get('role')
    if role == 'intern':
        return redirect(url_for('intern_dashboard'))
    elif role == 'mentor':
        return redirect(url_for('mentor_dashboard'))
    elif role == 'hr':
        return redirect(url_for('hr_dashboard'))
    elif role == 'leader':
        return redirect(url_for('leader_dashboard'))
    elif role == 'admin':
        return redirect(url_for('admin_users'))
    return redirect(url_for('login'))


# ── Intern Pages ─────────────────────────────────────────

@app.route('/intern/dashboard')
@login_required
@role_required('intern')
def intern_dashboard():
    db = get_db()
    uid = session['user_id']
    profile = db.execute(
        'SELECT ip.*, u.position FROM intern_profiles ip JOIN users u ON ip.user_id=u.id WHERE ip.user_id=?',
        (uid,)
    ).fetchone()
    if not profile:
        db.close()
        return redirect(url_for('login'))

    pid = profile['id']
    scores = db.execute(
        'SELECT d.name, s.score FROM skill_scores s JOIN skill_dimensions d ON s.dimension_id=d.id WHERE s.intern_id=?',
        (pid,)
    ).fetchall()

    unlocked = db.execute(
        'SELECT t.id, t.name, t.description, t.level_required, t.xp_reward, t.prerequisites, t.sort_order '
        'FROM skill_unlocks u JOIN skill_tree_templates t ON u.template_id=t.id '
        'WHERE u.intern_id=? ORDER BY t.sort_order', (pid,)
    ).fetchall()

    all_templates = db.execute(
        'SELECT * FROM skill_tree_templates WHERE position=? ORDER BY sort_order',
        (profile['position'] if profile['position'] else 'frontend',)
    ).fetchall()

    unlocked_ids = {r['id'] for r in unlocked}

    logs = db.execute(
        'SELECT * FROM growth_logs WHERE intern_id=? ORDER BY created_at DESC LIMIT 10', (pid,)
    ).fetchall()

    tasks = db.execute(
        'SELECT a.*, t.title, t.xp_reward FROM task_assignments a '
        'JOIN growth_tasks t ON a.task_id=t.id WHERE a.intern_id=? ORDER BY a.due_date DESC LIMIT 5',
        (pid,)
    ).fetchall()

    db.close()

    scores_dict = {r['name']: r['score'] for r in scores}
    radar_data = [scores_dict.get(name, 50) for name in DIMENSION_NAMES]

    return render_template('intern/dashboard.html',
        profile=dict(profile),
        scores=scores_dict,
        radar_data=radar_data,
        radar_labels=DIMENSION_NAMES,
        all_templates=[dict(t) for t in all_templates],
        unlocked_ids=unlocked_ids,
        logs=[dict(l) for l in logs],
        tasks=[dict(t) for t in tasks],
        level_title=LEVEL_TITLES[profile['level'] - 1],
        next_xp=xp_for_next_level(profile['level']),
    )

@app.route('/intern/growth-map')
@login_required
@role_required('intern')
def intern_growth_map():
    db = get_db()
    uid = session['user_id']
    profile = db.execute(
        'SELECT ip.*, u.position FROM intern_profiles ip JOIN users u ON ip.user_id=u.id WHERE ip.user_id=?',
        (uid,)
    ).fetchone()
    pid = profile['id']

    all_templates = db.execute(
        'SELECT * FROM skill_tree_templates WHERE position=? ORDER BY sort_order',
        (profile['position'] or 'frontend',)
    ).fetchall()
    unlocked = db.execute('SELECT template_id FROM skill_unlocks WHERE intern_id=?', (pid,)).fetchall()
    unlocked_ids = {r['template_id'] for r in unlocked}

    scores = db.execute(
        'SELECT d.name, s.score FROM skill_scores s JOIN skill_dimensions d ON s.dimension_id=d.id WHERE s.intern_id=?',
        (pid,)
    ).fetchall()
    scores_dict = {r['name']: r['score'] for r in scores}

    task_stats = db.execute(
        "SELECT status, COUNT(*) as cnt FROM task_assignments WHERE intern_id=? GROUP BY status", (pid,)
    ).fetchall()
    stats = {r['status']: r['cnt'] for r in task_stats}

    fb = db.execute(
        'SELECT AVG(rating) as avg_rating FROM feedbacks WHERE intern_id=?', (pid,)
    ).fetchone()
    avg_rating = fb['avg_rating'] or 3.0

    total_tasks = sum(stats.values())
    completed_tasks = stats.get('completed', 0)
    completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 0

    unlocked_count = len(unlocked_ids)
    total_skills = db.execute(
        'SELECT COUNT(*) as cnt FROM skill_tree_templates WHERE position=?',
        (profile['position'] or 'frontend',)
    ).fetchone()['cnt']

    avg_score = sum(scores_dict.values()) / len(scores_dict) if scores_dict else 50
    probability = int(min(100, (
        avg_score * 0.2 +
        completion_rate * 100 * 0.2 +
        (avg_rating / 5) * 100 * 0.2 +
        (profile['xp'] / 12000) * 100 * 0.15 +
        (unlocked_count / total_skills * 100 if total_skills > 0 else 50) * 0.15 +
        min(profile['level'] / 10, 1) * 100 * 0.1
    )))

    risk_level = 'low' if probability > 70 else 'medium' if probability > 40 else 'high'

    strengths = sorted(scores_dict.items(), key=lambda x: x[1], reverse=True)[:2]
    weaknesses = sorted(scores_dict.items(), key=lambda x: x[1])[:2]

    db.close()
    return render_template('intern/growth_map.html',
        profile=dict(profile),
        all_templates=[dict(t) for t in all_templates],
        unlocked_ids=unlocked_ids,
        scores=scores_dict,
        level_title=LEVEL_TITLES[profile['level'] - 1],
        next_xp=xp_for_next_level(profile['level']),
        probability=probability,
        risk_level=risk_level,
        strengths=strengths,
        weaknesses=weaknesses,
        completion_rate=completion_rate,
        avg_rating=avg_rating,
    )

@app.route('/intern/tasks')
@login_required
@role_required('intern')
def intern_tasks():
    db = get_db()
    uid = session['user_id']
    profile = db.execute('SELECT id FROM intern_profiles WHERE user_id=?', (uid,)).fetchone()
    pid = profile['id']

    filter_status = request.args.get('status', 'all')
    query = ('SELECT a.*, t.title, t.description, t.category, t.difficulty, t.xp_reward '
             'FROM task_assignments a JOIN growth_tasks t ON a.task_id=t.id WHERE a.intern_id=?')
    params = [pid]
    if filter_status != 'all':
        query += ' AND a.status=?'
        params.append(filter_status)
    query += ' ORDER BY a.due_date DESC'

    tasks = db.execute(query, params).fetchall()
    db.close()
    return render_template('intern/tasks.html', tasks=[dict(t) for t in tasks], current_filter=filter_status)

@app.route('/intern/tasks/<int:assignment_id>/start', methods=['POST'])
@login_required
@role_required('intern')
def start_task(assignment_id):
    db = get_db()
    uid = session['user_id']
    profile = db.execute('SELECT id FROM intern_profiles WHERE user_id=?', (uid,)).fetchone()
    db.execute(
        "UPDATE task_assignments SET status='in_progress' WHERE id=? AND intern_id=? AND status='pending'",
        (assignment_id, profile['id'])
    )
    db.commit()
    db.close()
    return redirect(url_for('intern_tasks'))

@app.route('/intern/tasks/<int:assignment_id>/complete', methods=['POST'])
@login_required
@role_required('intern')
def complete_task(assignment_id):
    db = get_db()
    uid = session['user_id']
    profile = db.execute('SELECT id, level, xp FROM intern_profiles WHERE user_id=?', (uid,)).fetchone()
    pid = profile['id']

    assignment = db.execute(
        "SELECT a.*, t.xp_reward, t.title FROM task_assignments a JOIN growth_tasks t ON a.task_id=t.id "
        "WHERE a.id=? AND a.intern_id=?", (assignment_id, pid)
    ).fetchone()

    if assignment and assignment['status'] in ('pending', 'in_progress'):
        now = datetime.now().isoformat()
        db.execute(
            "UPDATE task_assignments SET status='completed', completed_at=? WHERE id=?",
            (now, assignment_id)
        )

        xp_earned = assignment['xp_reward']
        new_xp = profile['xp'] + xp_earned
        new_level = calc_level(new_xp)
        db.execute('UPDATE intern_profiles SET xp=?, level=? WHERE id=?', (new_xp, new_level, pid))

        db.execute(
            'INSERT INTO growth_logs (intern_id, event_type, description, xp_change) VALUES (?,?,?,?)',
            (pid, 'task_completed', f'完成任务「{assignment["title"]}」', xp_earned)
        )

        if new_level > profile['level']:
            db.execute(
                'INSERT INTO growth_logs (intern_id, event_type, description, xp_change) VALUES (?,?,?,0)',
                (pid, 'level_up', f'升级！Lv.{profile["level"]} → Lv.{new_level}')
            )

        db.commit()

    db.close()
    return redirect(url_for('intern_tasks'))

@app.route('/intern/tasks/<int:assignment_id>')
@login_required
@role_required('intern')
def intern_task_detail(assignment_id):
    db = get_db()
    uid = session['user_id']
    profile = db.execute(
        'SELECT ip.*, u.position FROM intern_profiles ip JOIN users u ON ip.user_id=u.id WHERE ip.user_id=?',
        (uid,)
    ).fetchone()
    pid = profile['id']

    assignment = db.execute(
        'SELECT a.*, t.title, t.description, t.category, t.difficulty, t.xp_reward, t.dimension_id '
        'FROM task_assignments a JOIN growth_tasks t ON a.task_id=t.id '
        'WHERE a.id=? AND a.intern_id=?', (assignment_id, pid)
    ).fetchone()

    if not assignment:
        db.close()
        return redirect(url_for('intern_tasks'))

    submissions = db.execute(
        'SELECT * FROM task_submissions WHERE assignment_id=? ORDER BY submitted_at DESC',
        (assignment_id,)
    ).fetchall()

    feedbacks = db.execute(
        'SELECT f.*, u.name as mentor_name FROM feedbacks f '
        'JOIN users u ON f.mentor_id=u.id '
        'WHERE f.intern_id=? ORDER BY f.created_at DESC LIMIT 5',
        (pid,)
    ).fetchall()

    dim_name = None
    if assignment['dimension_id']:
        dim = db.execute('SELECT name FROM skill_dimensions WHERE id=?', (assignment['dimension_id'],)).fetchone()
        dim_name = dim['name'] if dim else None

    skill_node = None
    if dim_name:
        skill_node = db.execute(
            'SELECT * FROM skill_tree_templates WHERE position=? AND name LIKE ? LIMIT 1',
            (profile['position'] or 'frontend', f'%{dim_name}%')
        ).fetchone()

    similar_tasks = db.execute(
        'SELECT a.*, t.title, t.category, t.difficulty, t.xp_reward '
        'FROM task_assignments a JOIN growth_tasks t ON a.task_id=t.id '
        'WHERE a.intern_id=? AND a.id!=? AND t.category=? ORDER BY RANDOM() LIMIT 3',
        (pid, assignment_id, assignment['category'])
    ).fetchall()

    db.close()

    return render_template('intern/task_detail.html',
        assignment=dict(assignment),
        submissions=[dict(s) for s in submissions],
        feedbacks=[dict(f) for f in feedbacks],
        skill_node=dict(skill_node) if skill_node else None,
        similar_tasks=[dict(t) for t in similar_tasks],
        level_title=LEVEL_TITLES[profile['level'] - 1],
    )

@app.route('/intern/tasks/<int:assignment_id>/submit', methods=['POST'])
@login_required
@role_required('intern')
def submit_task(assignment_id):
    db = get_db()
    uid = session['user_id']
    profile = db.execute('SELECT id FROM intern_profiles WHERE user_id=?', (uid,)).fetchone()
    pid = profile['id']

    assignment = db.execute(
        'SELECT id FROM task_assignments WHERE id=? AND intern_id=?',
        (assignment_id, pid)
    ).fetchone()

    if assignment:
        content = request.form.get('content', '')
        if content.strip():
            db.execute(
                'INSERT INTO task_submissions (assignment_id, intern_id, content) VALUES (?,?,?)',
                (assignment_id, pid, content)
            )
            db.commit()

    db.close()
    return redirect(url_for('intern_task_detail', assignment_id=assignment_id))

@app.route('/intern/weekly-report', methods=['GET', 'POST'])
@login_required
@role_required('intern')
def intern_weekly_report():
    db = get_db()
    uid = session['user_id']
    profile = db.execute('SELECT id, start_date FROM intern_profiles WHERE user_id=?', (uid,)).fetchone()
    pid = profile['id']
    start_date = profile['start_date']
    
    # 计算当前是第几周（从入职开始计算）
    if start_date:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        current_week = ((datetime.now() - start_dt).days // 7) + 1
    else:
        current_week = 1

    if request.method == 'POST':
        content = request.form.get('content', '')
        self_rating = request.form.get('self_rating', 3, type=int)
        
        if content:
            existing = db.execute(
                'SELECT id FROM weekly_reports WHERE intern_id=? AND week_number=?',
                (pid, current_week)
            ).fetchone()
            if existing:
                db.execute(
                    'UPDATE weekly_reports SET content=?, self_rating=? WHERE id=?',
                    (content, self_rating, existing['id'])
                )
                flash('周报已更新')
            else:
                db.execute(
                    'INSERT INTO weekly_reports (intern_id, week_number, content, self_rating) VALUES (?,?,?,?)',
                    (pid, current_week, content, self_rating)
                )
                db.execute(
                    'INSERT INTO growth_logs (intern_id, event_type, description, xp_change) VALUES (?,\'report_submitted\',\'提交周报\',50)',
                    (pid,)
                )
                cur_xp = db.execute('SELECT xp FROM intern_profiles WHERE id=?', (pid,)).fetchone()[0]
                new_xp = cur_xp + 50
                new_level = calc_level(new_xp)
                db.execute('UPDATE intern_profiles SET xp=?, level=? WHERE id=?', (new_xp, new_level, pid))
                flash('周报提交成功')
            db.commit()

    reports = db.execute(
        'SELECT * FROM weekly_reports WHERE intern_id=? ORDER BY week_number DESC', (pid,)
    ).fetchall()
    
    # 获取所有反馈
    feedbacks = db.execute(
        'SELECT f.*, u.name as mentor_name FROM feedbacks f '
        'JOIN users u ON f.mentor_id=u.id WHERE f.intern_id=? ORDER BY f.created_at DESC',
        (pid,)
    ).fetchall()
    
    # 解析反馈的 dimension_scores
    fb_list = []
    for f in feedbacks:
        fb = dict(f)
        try:
            fb['dimension_scores'] = json.loads(fb['dimension_scores']) if fb['dimension_scores'] else {}
        except:
            fb['dimension_scores'] = {}
        fb_list.append(fb)
    
    # 给每个周报关联一条最近的反馈（提交日期相近）
    reports_list = []
    used_feedback_ids = set()
    for r in reports:
        rd = dict(r)
        rd['feedback'] = None
        report_date = rd.get('submitted_at', '')[:10]
        if report_date:
            for fb in fb_list:
                if fb['id'] in used_feedback_ids:
                    continue
                fb_date = fb['created_at'][:10] if fb['created_at'] else ''
                if fb_date:
                    try:
                        days_diff = abs((datetime.strptime(fb_date, '%Y-%m-%d') - datetime.strptime(report_date, '%Y-%m-%d')).days)
                        if days_diff <= 7:
                            rd['feedback'] = fb
                            used_feedback_ids.add(fb['id'])
                            break
                    except:
                        pass
        reports_list.append(rd)
    
    # 检查当前周是否已提交
    current_week_submitted = any(r['week_number'] == current_week for r in reports)
    
    db.close()
    return render_template('intern/weekly_report.html', 
                         reports=reports_list, 
                         current_week=current_week,
                         current_week_submitted=current_week_submitted)

@app.route('/intern/weekly-report/<int:report_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('intern')
def intern_weekly_report_edit(report_id):
    db = get_db()
    uid = session['user_id']
    profile = db.execute('SELECT id FROM intern_profiles WHERE user_id=?', (uid,)).fetchone()
    pid = profile['id']

    report = db.execute(
        'SELECT * FROM weekly_reports WHERE id=? AND intern_id=?',
        (report_id, pid)
    ).fetchone()

    if not report:
        db.close()
        return redirect(url_for('intern_weekly_report'))

    if request.method == 'POST':
        content = request.form.get('content', '')
        self_rating = request.form.get('self_rating', 3, type=int)
        if content:
            db.execute(
                'UPDATE weekly_reports SET content=?, self_rating=? WHERE id=?',
                (content, self_rating, report_id)
            )
            db.commit()
            flash('周报已更新')
            db.close()
            return redirect(url_for('intern_weekly_report'))

    db.close()
    return render_template('intern/weekly_report_edit.html', report=dict(report))

@app.route('/intern/feedback')
@login_required
@role_required('intern')
def intern_feedback():
    db = get_db()
    uid = session['user_id']
    profile = db.execute('SELECT id FROM intern_profiles WHERE user_id=?', (uid,)).fetchone()
    feedbacks = db.execute(
        'SELECT f.*, u.name as mentor_name FROM feedbacks f '
        'JOIN users u ON f.mentor_id=u.id WHERE f.intern_id=? ORDER BY f.created_at DESC',
        (profile['id'],)
    ).fetchall()
    db.close()
    return render_template('intern/feedback.html', feedbacks=[dict(f) for f in feedbacks])

@app.route('/intern/score-history')
@login_required
@role_required('intern')
def intern_score_history():
    db = get_db()
    uid = session['user_id']
    profile = db.execute(
        'SELECT ip.*, u.position FROM intern_profiles ip JOIN users u ON ip.user_id=u.id WHERE ip.user_id=?',
        (uid,)
    ).fetchone()
    pid = profile['id']

    history = db.execute(
        'SELECT h.*, d.name as dim_name, u.name as changed_by_name '
        'FROM skill_score_history h '
        'JOIN skill_dimensions d ON h.dimension_id=d.id '
        'LEFT JOIN users u ON h.changed_by=u.id '
        'WHERE h.intern_id=? ORDER BY h.created_at DESC',
        (pid,)
    ).fetchall()

    # 按时间分组评分历史
    history_by_time = {}
    for h in history:
        time_key = h['created_at'][:16]  # 精确到分钟
        if time_key not in history_by_time:
            history_by_time[time_key] = {
                'time': time_key,
                'changed_by': h['changed_by_name'] or '系统',
                'change_reason': h['change_reason'],
                'dimensions': {}
            }
        history_by_time[time_key]['dimensions'][h['dim_name']] = h['score']
    
    # 按时间倒序排列
    sorted_history = sorted(history_by_time.values(), key=lambda x: x['time'], reverse=True)

    current_scores = db.execute(
        'SELECT d.name, s.score FROM skill_scores s JOIN skill_dimensions d ON s.dimension_id=d.id WHERE s.intern_id=?',
        (pid,)
    ).fetchall()
    current_dict = {r['name']: r['score'] for r in current_scores}

    db.close()
    return render_template('intern/score_history.html',
        history=sorted_history,
        dimension_names=DIMENSION_NAMES,
        current_scores=current_dict,
    )

@app.route('/intern/learning')
@login_required
@role_required('intern')
def intern_learning():
    db = get_db()
    uid = session['user_id']
    profile = db.execute(
        'SELECT ip.*, u.position, u.department FROM intern_profiles ip JOIN users u ON ip.user_id=u.id WHERE ip.user_id=?',
        (uid,)
    ).fetchone()

    materials = db.execute(
        'SELECT m.*, u.name as author_name FROM learning_materials m '
        'JOIN users u ON m.author_id=u.id '
        'WHERE m.department=? OR m.department="" ORDER BY m.created_at DESC',
        (profile['department'],)
    ).fetchall()

    db.close()
    return render_template('intern/learning.html', materials=[dict(m) for m in materials])


# ── API endpoints ────────────────────────────────────────

@app.route('/api/intern/ai-chat', methods=['POST'])
@login_required
@role_required('intern')
def api_ai_chat():
    data = request.get_json()
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'error': '请输入问题'}), 400

    db = get_db()
    uid = session['user_id']
    profile = db.execute(
        'SELECT ip.*, u.position FROM intern_profiles ip JOIN users u ON ip.user_id=u.id WHERE ip.user_id=?',
        (uid,)
    ).fetchone()
    pid = profile['id']

    scores = db.execute(
        'SELECT d.name, s.score FROM skill_scores s JOIN skill_dimensions d ON s.dimension_id=d.id WHERE s.intern_id=?',
        (pid,)
    ).fetchall()
    scores_dict = {r['name']: r['score'] for r in scores}

    task_stats = db.execute(
        "SELECT status, COUNT(*) as cnt FROM task_assignments WHERE intern_id=? GROUP BY status", (pid,)
    ).fetchall()
    stats = {r['status']: r['cnt'] for r in task_stats}
    total_tasks = sum(stats.values())
    completed_tasks = stats.get('completed', 0)

    feedback = db.execute(
        'SELECT AVG(rating) as avg_rating FROM feedbacks WHERE intern_id=?', (pid,)
    ).fetchone()
    avg_rating = feedback['avg_rating'] or 0

    unlocked_count = db.execute('SELECT COUNT(*) as cnt FROM skill_unlocks WHERE intern_id=?', (pid,)).fetchone()['cnt']

    db.close()

    system_prompt = f"""你是一位专业的职业发展AI助手，专门帮助实习生成长。

当前实习生的信息：
- 姓名：{session.get('name', '实习生')}
- 等级：Lv.{profile['level']}
- 经验值：{profile['xp']}XP
- 岗位：{profile['position'] or '未设置'}
- 六维能力评分：{scores_dict}
- 任务完成情况：已完成{completed_tasks}/{total_tasks}个
- 导师平均评分：{avg_rating:.1f}/5
- 已解锁技能数：{unlocked_count}

请根据以上信息，给出专业、具体、有建设性的建议。回答要简洁实用，使用中文。"""

    try:
        from openai import OpenAI
        client = OpenAI(api_key=Config.DEEPSEEK_API_KEY, base_url=Config.DEEPSEEK_BASE_URL)
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        return jsonify({'response': ai_response})
        
    except Exception as e:
        return jsonify({'response': f'AI服务暂时不可用，请稍后再试。错误信息：{str(e)}'})


@app.route('/api/intern/growth-twin/<int:intern_id>')
@login_required
def api_growth_twin(intern_id):
    db = get_db()
    profile = db.execute(
        'SELECT ip.*, u.position FROM intern_profiles ip JOIN users u ON ip.user_id=u.id WHERE ip.id=?',
        (intern_id,)
    ).fetchone()
    if not profile:
        db.close()
        return jsonify({'error': 'not found'}), 404

    scores = db.execute(
        'SELECT d.name, s.score FROM skill_scores s JOIN skill_dimensions d ON s.dimension_id=d.id WHERE s.intern_id=?',
        (intern_id,)
    ).fetchall()
    scores_dict = {r['name']: r['score'] for r in scores}

    all_templates = db.execute(
        'SELECT * FROM skill_tree_templates WHERE position=? ORDER BY sort_order',
        (profile['position'] or 'frontend',)
    ).fetchall()
    unlocked = db.execute('SELECT template_id FROM skill_unlocks WHERE intern_id=?', (intern_id,)).fetchall()
    unlocked_ids = {r['template_id'] for r in unlocked}

    logs = db.execute(
        'SELECT * FROM growth_logs WHERE intern_id=? ORDER BY created_at DESC LIMIT 10', (intern_id,)
    ).fetchall()

    db.close()
    return jsonify({
        'level': profile['level'],
        'xp': profile['xp'],
        'level_title': LEVEL_TITLES[profile['level'] - 1],
        'next_xp': xp_for_next_level(profile['level']),
        'scores': scores_dict,
        'radar_data': [scores_dict.get(name, 50) for name in DIMENSION_NAMES],
        'skill_tree': {
            'templates': [dict(t) for t in all_templates],
            'unlocked_ids': list(unlocked_ids),
        },
        'logs': [dict(l) for l in logs],
    })


# ── Leader Pages ─────────────────────────────────────────

@app.route('/leader/dashboard')
@login_required
@role_required('leader')
def leader_dashboard():
    db = get_db()
    uid = session['user_id']
    user = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    dept = user['department']

    interns = db.execute(
        "SELECT ip.*, u.name, u.position, m.name as mentor_name "
        "FROM intern_profiles ip "
        "JOIN users u ON ip.user_id=u.id "
        "LEFT JOIN users m ON ip.mentor_id=m.id "
        "WHERE u.department=? AND ip.status='active' ORDER BY ip.level DESC",
        (dept,)
    ).fetchall()

    avg_level = db.execute(
        "SELECT AVG(level) as avg FROM intern_profiles ip JOIN users u ON ip.user_id=u.id WHERE u.department=? AND ip.status='active'",
        (dept,)
    ).fetchone()['avg'] or 1

    intern_list = []
    for i in interns:
        idata = dict(i)
        scores = db.execute(
            'SELECT d.name, s.score FROM skill_scores s JOIN skill_dimensions d ON s.dimension_id=d.id WHERE s.intern_id=?',
            (i['id'],)
        ).fetchall()
        idata['scores'] = {r['name']: r['score'] for r in scores}
        idata['avg_score'] = round(sum(idata['scores'].values()) / len(idata['scores']), 1) if idata['scores'] else 0
        intern_list.append(idata)

    db.close()
    return render_template('leader/dashboard.html',
        interns=intern_list,
        department=dept,
        avg_level=round(avg_level, 1),
    )

@app.route('/leader/high-potential')
@login_required
@role_required('leader')
def leader_high_potential():
    db = get_db()
    uid = session['user_id']
    user = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    dept = user['department']

    interns = db.execute(
        "SELECT ip.*, u.name, u.position, m.name as mentor_name "
        "FROM intern_profiles ip "
        "JOIN users u ON ip.user_id=u.id "
        "LEFT JOIN users m ON ip.mentor_id=m.id "
        "WHERE u.department=? AND ip.status='active' AND ip.level >= 4 ORDER BY ip.level DESC, ip.xp DESC",
        (dept,)
    ).fetchall()

    db.close()
    return render_template('leader/high_potential.html',
        interns=[dict(i) for i in interns],
        department=dept,
    )

@app.route('/leader/intern/<int:intern_id>')
@login_required
@role_required('leader')
def leader_intern_detail(intern_id):
    db = get_db()
    uid = session['user_id']

    profile = db.execute(
        'SELECT ip.*, u.name, u.position, u.department, m.name as mentor_name '
        'FROM intern_profiles ip '
        'JOIN users u ON ip.user_id=u.id '
        'LEFT JOIN users m ON ip.mentor_id=m.id '
        'WHERE ip.id=?', (intern_id,)
    ).fetchone()

    if not profile:
        db.close()
        return redirect(url_for('leader_dashboard'))

    scores = db.execute(
        'SELECT d.name, s.score FROM skill_scores s JOIN skill_dimensions d ON s.dimension_id=d.id WHERE s.intern_id=?',
        (intern_id,)
    ).fetchall()
    scores_dict = {r['name']: r['score'] for r in scores}

    score_history = db.execute(
        'SELECT h.*, d.name as dim_name, u.name as changed_by_name '
        'FROM skill_score_history h '
        'JOIN skill_dimensions d ON h.dimension_id=d.id '
        'LEFT JOIN users u ON h.changed_by=u.id '
        'WHERE h.intern_id=? ORDER BY h.created_at DESC',
        (intern_id,)
    ).fetchall()

    # 按时间分组评分历史
    history_by_time = {}
    for h in score_history:
        time_key = h['created_at'][:16]  # 精确到分钟
        if time_key not in history_by_time:
            history_by_time[time_key] = {
                'time': time_key,
                'changed_by': h['changed_by_name'] or '系统',
                'change_reason': h['change_reason'],
                'dimensions': {}
            }
        history_by_time[time_key]['dimensions'][h['dim_name']] = h['score']
    
    # 按时间倒序排列
    sorted_history = sorted(history_by_time.values(), key=lambda x: x['time'], reverse=True)

    tasks = db.execute(
        "SELECT a.*, t.title, t.xp_reward FROM task_assignments a "
        "JOIN growth_tasks t ON a.task_id=t.id WHERE a.intern_id=? ORDER BY a.due_date DESC LIMIT 10",
        (intern_id,)
    ).fetchall()

    task_stats = db.execute(
        "SELECT status, COUNT(*) as cnt FROM task_assignments WHERE intern_id=? GROUP BY status", (intern_id,)
    ).fetchall()
    stats = {r['status']: r['cnt'] for r in task_stats}

    feedbacks = db.execute(
        'SELECT f.*, u.name as mentor_name FROM feedbacks f '
        'JOIN users u ON f.mentor_id=u.id WHERE f.intern_id=? ORDER BY f.created_at DESC LIMIT 5',
        (intern_id,)
    ).fetchall()

    db.close()

    strengths = sorted(scores_dict.items(), key=lambda x: x[1], reverse=True)[:2]
    weaknesses = sorted(scores_dict.items(), key=lambda x: x[1])[:2]

    return render_template('leader/intern_detail.html',
        profile=dict(profile),
        scores=scores_dict,
        score_history=sorted_history,
        dimension_names=DIMENSION_NAMES,
        tasks=[dict(t) for t in tasks],
        task_stats=stats,
        feedbacks=[dict(f) for f in feedbacks],
        strengths=strengths,
        weaknesses=weaknesses,
    )

@app.route('/leader/materials', methods=['GET', 'POST'])
@login_required
@role_required('leader')
def leader_materials():
    db = get_db()
    uid = session['user_id']
    user = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '')
        category = request.form.get('category', 'general')
        if title and content:
            db.execute(
                'INSERT INTO learning_materials (title, content, category, author_id, department) VALUES (?,?,?,?,?)',
                (title, content, category, uid, user['department'])
            )
            db.commit()
            flash('学习资料发布成功')

    materials = db.execute(
        'SELECT m.*, u.name as author_name FROM learning_materials m '
        'JOIN users u ON m.author_id=u.id WHERE m.department=? ORDER BY m.created_at DESC',
        (user['department'],)
    ).fetchall()

    db.close()
    return render_template('leader/materials.html', materials=[dict(m) for m in materials])


@app.route('/leader/reports')
@login_required
@role_required('leader')
def leader_reports():
    db = get_db()
    uid = session['user_id']
    user = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    
    # 获取本部门实习生的周报
    reports = db.execute(
        '''SELECT wr.*, u.name as intern_name, ip.user_id
           FROM weekly_reports wr
           JOIN intern_profiles ip ON wr.intern_id=ip.id
           JOIN users u ON ip.user_id=u.id
           WHERE u.department=? AND ip.status='active'
           ORDER BY wr.submitted_at DESC''',
        (user['department'],)
    ).fetchall()
    
    db.close()
    return render_template('leader/reports.html', reports=[dict(r) for r in reports])


@app.route('/leader/report/<int:report_id>/suggest', methods=['POST'])
@login_required
@role_required('leader')
def leader_suggest_report(report_id):
    db = get_db()
    suggestion = request.form.get('suggestion', '').strip()
    
    if suggestion:
        db.execute(
            'UPDATE weekly_reports SET leader_comment=?, leader_reviewed_at=? WHERE id=?',
            (suggestion, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), report_id)
        )
        db.commit()
        flash('建议已提交')
    
    db.close()
    return redirect(url_for('leader_reports'))


# ── Mentor Pages ─────────────────────────────────────────

@app.route('/mentor/dashboard')
@login_required
@role_required('mentor')
def mentor_dashboard():
    db = get_db()
    uid = session['user_id']
    
    # 获取该导师的实习生
    interns = db.execute(
        'SELECT u.*, ip.level, ip.xp FROM users u JOIN intern_profiles ip ON u.id=ip.user_id WHERE ip.mentor_id=?',
        (uid,)
    ).fetchall()
    
    # 计算风险等级
    intern_list = []
    for i in interns:
        intern_dict = dict(i)
        # 简单的风险评估逻辑
        if intern_dict['level'] < 3:
            intern_dict['risk'] = 'danger'
        elif intern_dict['level'] < 5:
            intern_dict['risk'] = 'warning'
        else:
            intern_dict['risk'] = 'ok'
        intern_list.append(intern_dict)
    
    # 获取待批阅的周报
    pending_reports = db.execute(
        '''SELECT wr.*, u.name as intern_name FROM weekly_reports wr 
           JOIN intern_profiles ip ON wr.intern_id=ip.id
           JOIN users u ON ip.user_id=u.id 
           WHERE ip.mentor_id=? AND wr.mentor_reviewed_at IS NULL''',
        (uid,)
    ).fetchall()
    
    # 获取逾期任务
    overdue_tasks = db.execute(
        '''SELECT ta.*, u.name as intern_name FROM task_assignments ta 
           JOIN intern_profiles ip ON ta.intern_id=ip.id
           JOIN users u ON ip.user_id=u.id 
           WHERE ip.mentor_id=? AND ta.status=? AND ta.due_date < ?''',
        (uid, 'in_progress', datetime.now().strftime('%Y-%m-%d'))
    ).fetchall()
    
    db.close()
    return render_template('mentor/dashboard.html', 
                          interns=intern_list, 
                          pending_reports=[dict(r) for r in pending_reports],
                          overdue_tasks=[dict(t) for t in overdue_tasks])


@app.route('/api/mentor/mark-done', methods=['POST'])
@login_required
@role_required('mentor')
def api_mentor_mark_done():
    data = request.get_json()
    item_type = data.get('type')
    item_id = data.get('id')
    
    if not item_type or not item_id:
        return jsonify({'error': '参数错误'}), 400
    
    db = get_db()
    
    if item_type == 'report':
        # 标记周报已批阅
        db.execute(
            'UPDATE weekly_reports SET mentor_reviewed_at=? WHERE id=?',
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), item_id)
        )
    elif item_type == 'task':
        # 标记任务完成
        db.execute(
            "UPDATE task_assignments SET status='completed', completed_at=? WHERE id=?",
            (datetime.now().isoformat(), item_id)
        )
    
    db.commit()
    db.close()
    return jsonify({'success': True})


@app.route('/mentor/feedback', methods=['GET', 'POST'])
@login_required
@role_required('mentor')
def mentor_feedback():
    db = get_db()
    uid = session['user_id']
    
    # 获取该导师的实习生
    interns = db.execute(
        'SELECT u.* FROM users u JOIN intern_profiles ip ON u.id=ip.user_id WHERE ip.mentor_id=?',
        (uid,)
    ).fetchall()
    
    if request.method == 'POST':
        intern_id = request.form.get('intern_id')
        content = request.form.get('content', '').strip()
        feedback_type = request.form.get('type', 'weekly')
        rating = request.form.get('rating', '4')
        
        # 获取六维评分
        dim_scores = []
        for i in range(1, 7):
            dim_scores.append(request.form.get(f'dim_{i}', '70'))
        
        if intern_id and content:
            # 获取实习生profile id
            intern_profile = db.execute('SELECT id FROM intern_profiles WHERE user_id=?', (intern_id,)).fetchone()
            if intern_profile:
                pid = intern_profile['id']
                
                # 构建六维评分字典
                dim_names = ['技术能力', '沟通协作', '业务理解', '主动成长', '问题解决', '工程素养']
                dim_scores_dict = {dim_names[i]: int(dim_scores[i]) for i in range(6)}
                dim_scores_json = json.dumps(dim_scores_dict, ensure_ascii=False)
                
                # 插入反馈
                db.execute(
                    '''INSERT INTO feedbacks (intern_id, mentor_id, type, content, rating, dimension_scores, created_at) 
                       VALUES (?, ?, ?, ?, ?, ?, ?)''',
                    (pid, uid, feedback_type, content, int(rating), dim_scores_json, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                )
                
                # 更新六维评分
                for i, score in enumerate(dim_scores, 1):
                    dim_id = i
                    db.execute(
                        '''INSERT OR REPLACE INTO skill_scores (intern_id, dimension_id, score, updated_at) 
                           VALUES (?, ?, ?, ?)''',
                        (pid, dim_id, int(score), datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    )
                
                db.commit()
                flash('反馈提交成功')
    
    # 获取反馈历史
    history_raw = db.execute(
        '''SELECT f.*, u.name as intern_name FROM feedbacks f 
           JOIN intern_profiles ip ON f.intern_id=ip.id 
           JOIN users u ON ip.user_id=u.id 
           WHERE f.mentor_id=? ORDER BY f.created_at DESC LIMIT 20''',
        (uid,)
    ).fetchall()
    
    # 处理 dimension_scores JSON 字段
    history = []
    for h in history_raw:
        h_dict = dict(h)
        # 确保 dimension_scores 是字典类型
        dim_scores = h_dict.get('dimension_scores', '{}')
        if isinstance(dim_scores, str):
            try:
                h_dict['dimension_scores'] = json.loads(dim_scores) if dim_scores else {}
            except:
                h_dict['dimension_scores'] = {}
        elif dim_scores is None:
            h_dict['dimension_scores'] = {}
        history.append(h_dict)
    
    db.close()
    return render_template('mentor/feedback.html', 
                          interns=[dict(i) for i in interns],
                          history=history)


@app.route('/mentor/plan')
@login_required
@role_required('mentor')
def mentor_plan():
    db = get_db()
    uid = session['user_id']
    
    # 获取该导师的实习生及其详细数据
    interns_raw = db.execute(
        'SELECT u.*, ip.* FROM users u JOIN intern_profiles ip ON u.id=ip.user_id WHERE ip.mentor_id=?',
        (uid,)
    ).fetchall()
    
    interns = []
    for i in interns_raw:
        intern_dict = dict(i)
        pid = i['id']
        
        # 获取六维评分
        scores = db.execute(
            'SELECT d.name, s.score FROM skill_scores s JOIN skill_dimensions d ON s.dimension_id=d.id WHERE s.intern_id=?',
            (pid,)
        ).fetchall()
        intern_dict['scores'] = {r['name']: r['score'] for r in scores}
        
        # 获取任务统计
        task_stats = db.execute(
            "SELECT status, COUNT(*) as cnt FROM task_assignments WHERE intern_id=? GROUP BY status",
            (pid,)
        ).fetchall()
        intern_dict['task_stats'] = {r['status']: r['cnt'] for r in task_stats}
        total_tasks = sum(intern_dict['task_stats'].values())
        completed_tasks = intern_dict['task_stats'].get('completed', 0)
        intern_dict['completion_rate'] = completed_tasks / total_tasks if total_tasks > 0 else 0
        
        # 获取平均评分
        fb = db.execute('SELECT AVG(rating) as avg FROM feedbacks WHERE intern_id=?', (pid,)).fetchone()
        intern_dict['avg_rating'] = fb['avg'] or 0
        
        interns.append(intern_dict)
    
    db.close()
    return render_template('mentor/plan.html', interns=interns, LEVEL_TITLES=LEVEL_TITLES)


@app.route('/api/mentor/plan/<int:intern_id>', methods=['GET'])
@login_required
@role_required('mentor')
def api_mentor_plan(intern_id):
    db = get_db()
    uid = session['user_id']
    
    # 验证权限
    profile = db.execute(
        'SELECT ip.*, u.name, u.position, u.department FROM intern_profiles ip JOIN users u ON ip.user_id=u.id WHERE ip.id=? AND ip.mentor_id=?',
        (intern_id, uid)
    ).fetchone()
    
    if not profile:
        db.close()
        return jsonify({'error': '无权访问'}), 403
    
    # 获取详细数据
    scores = db.execute(
        'SELECT d.name, s.score FROM skill_scores s JOIN skill_dimensions d ON s.dimension_id=d.id WHERE s.intern_id=?',
        (intern_id,)
    ).fetchall()
    scores_dict = {r['name']: r['score'] for r in scores}
    
    task_stats = db.execute(
        "SELECT status, COUNT(*) as cnt FROM task_assignments WHERE intern_id=? GROUP BY status",
        (intern_id,)
    ).fetchall()
    stats = {r['status']: r['cnt'] for r in task_stats}
    total_tasks = sum(stats.values())
    completed_tasks = stats.get('completed', 0)
    
    fb = db.execute('SELECT AVG(rating) as avg FROM feedbacks WHERE intern_id=?', (intern_id,)).fetchone()
    avg_rating = fb['avg'] or 0
    
    # 调用 AI 生成个性化培养计划
    system_prompt = """你是一位经验丰富的带教导师，专门为实习生制定个性化的培养计划。

根据实习生的数据，生成一份针对性的培养计划，包含：
1. 当前能力分析
2. 优势与不足
3. 短期目标（1-2周）
4. 中期目标（1个月）
5. 长期目标（3个月）
6. 具体行动建议

回复格式清晰，使用中文，分点列出。"""
    
    user_prompt = f"""实习生信息：
- 姓名：{profile['name']}
- 当前等级：Lv.{profile['level']}（{LEVEL_TITLES[profile['level']-1]}）
- 经验值：{profile['xp']} XP
- 岗位：{profile['position'] or '未设置'}
- 六维能力评分：{scores_dict}
- 任务完成情况：已完成{completed_tasks}/{total_tasks}个
- 导师平均评分：{avg_rating:.1f}/5"""
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=Config.DEEPSEEK_API_KEY, base_url=Config.DEEPSEEK_BASE_URL)
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        
        plan = response.choices[0].message.content
        db.close()
        return jsonify({'plan': plan, 'name': profile['name']})
        
    except Exception as e:
        db.close()
        return jsonify({'error': f'AI服务暂时不可用：{str(e)}'}), 500


@app.route('/mentor/ai-copilot', methods=['GET', 'POST'])
@login_required
@role_required('mentor')
def mentor_ai_copilot():
    ai_response = None
    
    if request.method == 'POST':
        context = request.form.get('context', '').strip()
        if context:
            system_prompt = """你是一位经验丰富的带教导师AI助手，专门帮助导师更好地指导实习生成长。

请根据导师描述的情境，给出专业、具体、有建设性的带教建议。回答要简洁实用，使用中文。
重点关注：
1. 如何帮助实习生提升能力
2. 如何进行有效的反馈沟通
3. 如何制定合理的培养计划
4. 如何处理实习生遇到的问题"""

            try:
                from openai import OpenAI
                client = OpenAI(api_key=Config.DEEPSEEK_API_KEY, base_url=Config.DEEPSEEK_BASE_URL)
                
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": context}
                    ],
                    max_tokens=1000,
                    temperature=0.7
                )
                
                ai_response = response.choices[0].message.content
                
            except Exception as e:
                ai_response = f'AI服务暂时不可用，请稍后再试。错误信息：{str(e)}'
    
    return render_template('mentor/ai_copilot.html', ai_response=ai_response)


@app.route('/api/mentor/ai-chat', methods=['POST'])
@login_required
@role_required('mentor')
def api_mentor_ai_chat():
    data = request.get_json()
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'response': '请输入问题'}), 400
    
    system_prompt = """你是一位经验丰富的带教导师AI助手，专门帮助导师更好地指导实习生成长。

请根据导师描述的情境，给出专业、具体、有建设性的带教建议。回答要简洁实用，使用中文。
重点关注：
1. 如何帮助实习生提升能力
2. 如何进行有效的反馈沟通
3. 如何制定合理的培养计划
4. 如何处理实习生遇到的问题"""
    
    try:
        from openai import OpenAI
        client = OpenAI(api_key=Config.DEEPSEEK_API_KEY, base_url=Config.DEEPSEEK_BASE_URL)
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        return jsonify({'response': ai_response})
        
    except Exception as e:
        return jsonify({'response': f'AI服务暂时不可用，请稍后再试。错误信息：{str(e)}'})


@app.route('/mentor/intern/<int:intern_id>')
@login_required
@role_required('mentor')
def mentor_intern_detail(intern_id):
    db = get_db()
    uid = session['user_id']
    
    # 验证该实习生是否属于当前导师
    intern = db.execute(
        'SELECT u.*, ip.* FROM users u JOIN intern_profiles ip ON u.id=ip.user_id WHERE u.id=? AND ip.mentor_id=?',
        (intern_id, uid)
    ).fetchone()
    
    if not intern:
        flash('无权访问该实习生信息')
        db.close()
        return redirect(url_for('mentor_dashboard'))
    
    user = dict(intern)
    profile = dict(intern)
    
    # 获取六维评分
    scores = db.execute(
        '''SELECT d.name, s.score FROM skill_scores s 
           JOIN skill_dimensions d ON s.dimension_id=d.id 
           WHERE s.intern_id=?''',
        (profile['id'],)
    ).fetchall()
    scores_dict = {r['name']: r['score'] for r in scores}
    
    # 如果没有评分数据，提供默认值
    if not scores_dict:
        scores_dict = {name: 0 for name in DIMENSION_NAMES}
    
    # 获取任务记录
    tasks = db.execute(
        '''SELECT ta.*, t.title, t.xp_reward FROM task_assignments ta 
           JOIN growth_tasks t ON ta.task_id=t.id 
           WHERE ta.intern_id=? ORDER BY ta.due_date DESC LIMIT 10''',
        (profile['id'],)
    ).fetchall()
    
    # 获取反馈记录
    feedbacks = db.execute(
        '''SELECT f.*, u.name as mentor_name FROM feedbacks f 
           JOIN users u ON f.mentor_id=u.id 
           WHERE f.intern_id=? ORDER BY f.created_at DESC LIMIT 10''',
        (profile['id'],)
    ).fetchall()
    
    # 获取成长记录
    logs = db.execute(
        '''SELECT * FROM growth_logs WHERE intern_id=? ORDER BY created_at DESC LIMIT 15''',
        (profile['id'],)
    ).fetchall()
    
    # 准备雷达图数据
    radar_labels = DIMENSION_NAMES
    radar_data = [scores_dict.get(name, 0) for name in DIMENSION_NAMES]
    
    level_title = LEVEL_TITLES[profile['level'] - 1] if profile['level'] <= len(LEVEL_TITLES) else LEVEL_TITLES[-1]
    
    db.close()
    return render_template('mentor/intern_detail.html',
                          user=user,
                          profile=profile,
                          scores=scores_dict,
                          tasks=[dict(t) for t in tasks],
                          feedbacks=[dict(f) for f in feedbacks],
                          logs=[dict(l) for l in logs],
                          radar_labels=radar_labels,
                          radar_data=radar_data,
                          level_title=level_title)


# ── Admin Pages ─────────────────────────────────────────

@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_users():
    db = get_db()
    users = db.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()
    
    # 获取所有导师
    mentors = db.execute(
        "SELECT id, name FROM users WHERE role='mentor'"
    ).fetchall()
    
    # 获取实习生对应的导师信息
    intern_profiles = db.execute('SELECT user_id, mentor_id FROM intern_profiles').fetchall()
    mentor_map = {str(p['user_id']): p['mentor_id'] for p in intern_profiles}
    
    users_list = [dict(u) for u in users]
    for u in users_list:
        u['mentor_id'] = mentor_map.get(str(u['id']))
    
    db.close()
    return render_template('admin/users.html', 
                           users=users_list, 
                           mentors=[dict(m) for m in mentors])


@app.route('/admin/assign-mentor', methods=['POST'])
@login_required
@role_required('admin')
def admin_assign_mentor():
    intern_user_id = request.form.get('intern_user_id')
    mentor_id = request.form.get('mentor_id')
    
    db = get_db()
    
    # 检查该实习生是否有 intern_profile
    profile = db.execute(
        'SELECT id FROM intern_profiles WHERE user_id=?',
        (intern_user_id,)
    ).fetchone()
    
    if profile:
        db.execute(
            'UPDATE intern_profiles SET mentor_id=? WHERE user_id=?',
            (mentor_id if mentor_id else None, intern_user_id)
        )
    else:
        # 创建新 profile
        db.execute(
            'INSERT INTO intern_profiles (user_id, mentor_id, level, xp, status, created_at) VALUES (?, ?, 1, 0, ?, ?)',
            (intern_user_id, mentor_id if mentor_id else None, 'active', datetime.now().strftime('%Y-%m-%d'))
        )
    
    db.commit()
    db.close()
    flash('导师分配成功')
    return redirect(url_for('admin_users'))


@app.route('/admin/skills')
@login_required
@role_required('admin')
def admin_skills():
    db = get_db()
    
    # 获取所有技能节点（按岗位分组）
    templates = db.execute('SELECT * FROM skill_tree_templates ORDER BY position, sort_order').fetchall()
    
    # 按岗位分组
    skill_map = {}
    for t in templates:
        pos = t['position'] or '未分类'
        if pos not in skill_map:
            skill_map[pos] = []
        skill_map[pos].append(dict(t))
    
    # 获取所有岗位列表
    positions = list(skill_map.keys())
    
    db.close()
    return render_template('admin/skills.html',
                           skill_map=skill_map,
                           positions=positions)


@app.route('/admin/skills/add', methods=['POST'])
@login_required
@role_required('admin')
def admin_add_skill():
    position = request.form.get('position')
    name = request.form.get('name')
    description = request.form.get('description', '')
    level_required = request.form.get('level_required', 1, type=int)
    xp_reward = request.form.get('xp_reward', 100, type=int)
    
    db = get_db()
    
    # 获取该岗位当前最大序号，自动+1
    max_order = db.execute(
        'SELECT MAX(sort_order) as max_order FROM skill_tree_templates WHERE position=?',
        (position,)
    ).fetchone()['max_order']
    
    sort_order = (max_order or 0) + 1
    
    db.execute(
        '''INSERT INTO skill_tree_templates (position, name, description, level_required, xp_reward, sort_order) 
           VALUES (?, ?, ?, ?, ?, ?)''',
        (position, name, description, level_required, xp_reward, sort_order)
    )
    db.commit()
    db.close()
    flash('技能节点添加成功')
    return redirect(url_for('admin_skills'))


@app.route('/admin/skills/<int:template_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_skill(template_id):
    db = get_db()
    
    # 先获取被删除技能的信息（岗位）
    skill = db.execute('SELECT position FROM skill_tree_templates WHERE id=?', (template_id,)).fetchone()
    
    if skill:
        position = skill['position']
        
        # 删除技能
        db.execute('DELETE FROM skill_tree_templates WHERE id=?', (template_id,))
        
        # 获取同岗位剩余的技能，按序号排序
        remaining = db.execute(
            'SELECT id FROM skill_tree_templates WHERE position=? ORDER BY sort_order',
            (position,)
        ).fetchall()
        
        # 重新编号所有剩余技能（从1开始）
        for idx, r in enumerate(remaining):
            db.execute(
                'UPDATE skill_tree_templates SET sort_order=? WHERE id=?',
                (idx + 1, r['id'])
            )
        
        db.commit()
        flash(f'技能节点删除成功，序号已重新排列')
    else:
        flash('技能节点不存在')
    
    db.close()
    return redirect(url_for('admin_skills'))


# ── Run ──────────────────────────────────────────────────

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
