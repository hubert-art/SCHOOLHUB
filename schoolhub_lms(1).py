import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3, hashlib, secrets, datetime as dt, json, csv, os, re, math, random, time
from pathlib import Path

APP_NAME = 'SchoolHub LMS'
DB_FILE = Path(__file__).with_name('schoolhub.db')
VERSION = '1.0'

COLORS = {'bg':'#F5F7FB','card':'#FFFFFF','primary':'#2563EB','primary_dark':'#1D4ED8','text':'#172033','muted':'#64748B','border':'#E2E8F0','success':'#16A34A','warning':'#D97706','danger':'#DC2626','info':'#0891B2'}
ROLES = ('admin','teacher','student','parent')


def now(): return dt.datetime.now().replace(microsecond=0).isoformat(sep=' ')
def today(): return dt.date.today().isoformat()
def fmt_date(value):
    try: return dt.datetime.fromisoformat(value).strftime('%d %b %Y')
    except Exception: return value or '-'
def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 120000)
    return salt.hex() + '$' + digest.hex()
def verify_password(password, stored):
    try:
        salt, digest = stored.split('$', 1)
        test = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 120000).hex()
        return secrets.compare_digest(test, digest)
    except Exception: return False
def valid_email(value): return bool(re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', value.strip()))
def parse_date(value):
    try: dt.date.fromisoformat(value); return True
    except Exception: return False
def pct(score, maximum): return round((float(score) / float(maximum)) * 100, 2) if maximum else 0.0
def grade_letter(p): return 'A' if p>=90 else 'B' if p>=80 else 'C' if p>=70 else 'D' if p>=60 else 'F'
def gpa_point(p): return {'A':4.0,'B':3.0,'C':2.0,'D':1.0,'F':0.0}[grade_letter(p)]
def performance(p): return 'Excellent' if p>=90 else 'Good' if p>=75 else 'Average' if p>=60 else 'Needs Improvement'
def risk_level(avg, attendance, completion, exam):
    score = 0
    if avg < 60: score += 2
    elif avg < 70: score += 1
    if attendance < 75: score += 2
    elif attendance < 85: score += 1
    if completion < 60: score += 2
    elif completion < 80: score += 1
    if exam < 60: score += 2
    elif exam < 70: score += 1
    return 'High Risk' if score >= 5 else 'Moderate Risk' if score >= 2 else 'Low Risk'

SCHEMA = '''
CREATE TABLE IF NOT EXISTS academic_years(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, start_date TEXT, end_date TEXT, is_current INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, first_name TEXT NOT NULL, last_name TEXT NOT NULL, phone TEXT, profile_image TEXT, status TEXT DEFAULT 'active', created_at TEXT DEFAULT CURRENT_TIMESTAMP, last_login TEXT, is_active INTEGER DEFAULT 1);
CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY, class_name TEXT NOT NULL, grade_level TEXT, section TEXT, academic_year_id INTEGER, room TEXT, class_teacher_id INTEGER, is_active INTEGER DEFAULT 1, FOREIGN KEY(academic_year_id) REFERENCES academic_years(id), FOREIGN KEY(class_teacher_id) REFERENCES teachers(id));
CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, student_number TEXT UNIQUE NOT NULL, date_of_birth TEXT, gender TEXT, address TEXT, emergency_contact TEXT, enrollment_date TEXT, class_id INTEGER, academic_status TEXT DEFAULT 'Active', FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(class_id) REFERENCES classes(id));
CREATE TABLE IF NOT EXISTS teachers(id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, employee_number TEXT UNIQUE NOT NULL, specialization TEXT, hire_date TEXT, department TEXT, qualification TEXT, FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS parents(id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, occupation TEXT, address TEXT, FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS parent_students(id INTEGER PRIMARY KEY, parent_id INTEGER, student_id INTEGER, relationship TEXT, UNIQUE(parent_id,student_id), FOREIGN KEY(parent_id) REFERENCES parents(id) ON DELETE CASCADE, FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS subjects(id INTEGER PRIMARY KEY, name TEXT NOT NULL, code TEXT UNIQUE NOT NULL, description TEXT, department TEXT, credits REAL DEFAULT 1);
CREATE TABLE IF NOT EXISTS teacher_subjects(id INTEGER PRIMARY KEY, teacher_id INTEGER, subject_id INTEGER, class_id INTEGER, UNIQUE(teacher_id,subject_id,class_id), FOREIGN KEY(teacher_id) REFERENCES teachers(id), FOREIGN KEY(subject_id) REFERENCES subjects(id), FOREIGN KEY(class_id) REFERENCES classes(id));
CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY, subject_id INTEGER, teacher_id INTEGER, title TEXT NOT NULL, description TEXT, difficulty TEXT, duration INTEGER DEFAULT 0, created_at TEXT DEFAULT CURRENT_TIMESTAMP, status TEXT DEFAULT 'Published', FOREIGN KEY(subject_id) REFERENCES subjects(id), FOREIGN KEY(teacher_id) REFERENCES teachers(id));
CREATE TABLE IF NOT EXISTS course_modules(id INTEGER PRIMARY KEY, course_id INTEGER, title TEXT NOT NULL, description TEXT, position INTEGER DEFAULT 1, FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS lessons(id INTEGER PRIMARY KEY, module_id INTEGER, title TEXT NOT NULL, content TEXT, position INTEGER DEFAULT 1, estimated_minutes INTEGER DEFAULT 30, published INTEGER DEFAULT 1, FOREIGN KEY(module_id) REFERENCES course_modules(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS enrollments(id INTEGER PRIMARY KEY, student_id INTEGER, course_id INTEGER, enrolled_at TEXT DEFAULT CURRENT_TIMESTAMP, completion_percentage REAL DEFAULT 0, status TEXT DEFAULT 'Active', UNIQUE(student_id,course_id), FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE, FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS assignments(id INTEGER PRIMARY KEY, course_id INTEGER, teacher_id INTEGER, title TEXT NOT NULL, description TEXT, instructions TEXT, assigned_date TEXT, due_date TEXT, max_score REAL DEFAULT 100, status TEXT DEFAULT 'Published', FOREIGN KEY(course_id) REFERENCES courses(id), FOREIGN KEY(teacher_id) REFERENCES teachers(id));
CREATE TABLE IF NOT EXISTS assignment_submissions(id INTEGER PRIMARY KEY, assignment_id INTEGER, student_id INTEGER, submission_text TEXT, submitted_at TEXT, score REAL, feedback TEXT, status TEXT DEFAULT 'Submitted', graded_at TEXT, graded_by INTEGER, UNIQUE(assignment_id,student_id), FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE, FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS exams(id INTEGER PRIMARY KEY, course_id INTEGER, teacher_id INTEGER, title TEXT NOT NULL, description TEXT, exam_date TEXT, duration_minutes INTEGER DEFAULT 30, max_score REAL DEFAULT 100, status TEXT DEFAULT 'Published', exam_type TEXT DEFAULT 'Exam', randomize INTEGER DEFAULT 0, FOREIGN KEY(course_id) REFERENCES courses(id), FOREIGN KEY(teacher_id) REFERENCES teachers(id));
CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY, exam_id INTEGER, question_text TEXT NOT NULL, question_type TEXT, points REAL DEFAULT 1, position INTEGER DEFAULT 1, FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS question_options(id INTEGER PRIMARY KEY, question_id INTEGER, option_text TEXT NOT NULL, is_correct INTEGER DEFAULT 0, FOREIGN KEY(question_id) REFERENCES questions(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS exam_attempts(id INTEGER PRIMARY KEY, exam_id INTEGER, student_id INTEGER, started_at TEXT, submitted_at TEXT, score REAL DEFAULT 0, percentage REAL DEFAULT 0, status TEXT DEFAULT 'In Progress', FOREIGN KEY(exam_id) REFERENCES exams(id), FOREIGN KEY(student_id) REFERENCES students(id));
CREATE TABLE IF NOT EXISTS student_answers(id INTEGER PRIMARY KEY, attempt_id INTEGER, question_id INTEGER, selected_option_id INTEGER, answer_text TEXT, points_awarded REAL DEFAULT 0, UNIQUE(attempt_id,question_id), FOREIGN KEY(attempt_id) REFERENCES exam_attempts(id) ON DELETE CASCADE, FOREIGN KEY(question_id) REFERENCES questions(id));
CREATE TABLE IF NOT EXISTS grades(id INTEGER PRIMARY KEY, student_id INTEGER, subject_id INTEGER, assessment_type TEXT, assessment_id INTEGER, score REAL, max_score REAL, percentage REAL, term TEXT, academic_year_id INTEGER, teacher_id INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(student_id) REFERENCES students(id), FOREIGN KEY(subject_id) REFERENCES subjects(id));
CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY, student_id INTEGER, class_id INTEGER, date TEXT, status TEXT, check_in_time TEXT, check_out_time TEXT, remarks TEXT, recorded_by INTEGER, UNIQUE(student_id,date), FOREIGN KEY(student_id) REFERENCES students(id), FOREIGN KEY(class_id) REFERENCES classes(id));
CREATE TABLE IF NOT EXISTS timetable(id INTEGER PRIMARY KEY, class_id INTEGER, subject_id INTEGER, teacher_id INTEGER, day_of_week TEXT, start_time TEXT, end_time TEXT, room TEXT, FOREIGN KEY(class_id) REFERENCES classes(id));
CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, title TEXT, description TEXT, event_type TEXT, start_datetime TEXT, end_datetime TEXT, location TEXT, created_by INTEGER);
CREATE TABLE IF NOT EXISTS announcements(id INTEGER PRIMARY KEY, title TEXT, content TEXT, author_id INTEGER, target_role TEXT, target_class INTEGER, created_at TEXT DEFAULT CURRENT_TIMESTAMP, priority TEXT DEFAULT 'Normal');
CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, sender_id INTEGER, recipient_id INTEGER, subject TEXT, body TEXT, sent_at TEXT DEFAULT CURRENT_TIMESTAMP, read_at TEXT, is_read INTEGER DEFAULT 0, FOREIGN KEY(sender_id) REFERENCES users(id), FOREIGN KEY(recipient_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, message TEXT, notification_type TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, is_read INTEGER DEFAULT 0, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS achievements(id INTEGER PRIMARY KEY, name TEXT UNIQUE, description TEXT, requirement_type TEXT, requirement_value REAL, points INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS student_achievements(id INTEGER PRIMARY KEY, student_id INTEGER, achievement_id INTEGER, earned_at TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(student_id,achievement_id), FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS learning_progress(id INTEGER PRIMARY KEY, student_id INTEGER, lesson_id INTEGER, completed INTEGER DEFAULT 0, completed_at TEXT, time_spent INTEGER DEFAULT 0, UNIQUE(student_id,lesson_id));
CREATE TABLE IF NOT EXISTS certificates(id INTEGER PRIMARY KEY, student_id INTEGER, course_id INTEGER, certificate_number TEXT UNIQUE, issued_at TEXT, final_score REAL);
CREATE TABLE IF NOT EXISTS study_sessions(id INTEGER PRIMARY KEY, student_id INTEGER, subject_id INTEGER, start_time TEXT, end_time TEXT, duration_minutes INTEGER DEFAULT 0, notes TEXT);
CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT, entity_type TEXT, entity_id INTEGER, timestamp TEXT DEFAULT CURRENT_TIMESTAMP, details TEXT);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE INDEX IF NOT EXISTS idx_grades_student ON grades(student_id); CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id,date); CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id,is_read); CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id,is_read);
'''

class DB:
    def __init__(self, path=DB_FILE):
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('PRAGMA foreign_keys=ON')
        self.conn.executescript(SCHEMA)
        self.seed()
    def q(self, sql, params=(), one=False):
        cur=self.conn.execute(sql,params); rows=cur.fetchone() if one else cur.fetchall(); return rows
    def exec(self, sql, params=()):
        cur=self.conn.execute(sql,params); self.conn.commit(); return cur.lastrowid
    def executemany(self, sql, rows): self.conn.executemany(sql,rows); self.conn.commit()
    def scalar(self, sql, params=()):
        r=self.q(sql,params,True); return r[0] if r else None
    def setting(self,key,default=''):
        v=self.scalar('SELECT value FROM settings WHERE key=?',(key,)); return v if v is not None else default
    def set_setting(self,key,value): self.exec('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,str(value)))
    def seed_user(self, username,email,password,role,first,last,phone=''):
        r=self.q('SELECT id FROM users WHERE email=?',(email,),True)
        if r: return r['id']
        return self.exec('INSERT INTO users(username,email,password_hash,role,first_name,last_name,phone) VALUES(?,?,?,?,?,?,?)',(username,email,hash_password(password),role,first,last,phone))
    def seed(self):
        if not self.scalar('SELECT id FROM academic_years WHERE is_current=1'):
            self.exec('INSERT INTO academic_years(name,start_date,end_date,is_current) VALUES(?,?,?,1)',('2026/2027','2026-08-01','2027-07-31'))
        ay=self.scalar('SELECT id FROM academic_years WHERE is_current=1')
        self.set_setting('school_name','SchoolHub Academy'); self.set_setting('school_address','Nairobi, Kenya'); self.set_setting('school_phone','+254 700 000 000'); self.set_setting('school_email','admin@schoolhub.local')
        admin=self.seed_user('admin','admin@schoolhub.local','Admin123!','admin','Alex','Administrator')
        teacher=self.seed_user('teacher','teacher@schoolhub.local','Teacher123!','teacher','Sarah','Mwangi')
        teacher2=self.seed_user('teacher2','teacher2@schoolhub.local','Teacher123!','teacher','Daniel','Otieno')
        teacher3=self.seed_user('teacher3','teacher3@schoolhub.local','Teacher123!','teacher','Grace','Njeri')
        student=self.seed_user('student','student@schoolhub.local','Student123!','student','James','Kamau')
        parent=self.seed_user('parent','parent@schoolhub.local','Parent123!','parent','Mary','Kamau')
        if not self.scalar('SELECT id FROM teachers'):
            for uid,num,spec,dept,qual in [(teacher,'T001','Mathematics','Sciences','BSc Education'),(teacher2,'T002','Computer Science','Technology','BSc Computer Science'),(teacher3,'T003','English','Languages','BA Education')]:
                self.exec('INSERT INTO teachers(user_id,employee_number,specialization,hire_date,department,qualification) VALUES(?,?,?,?,?,?)',(uid,num,spec,'2024-01-10',dept,qual))
        if not self.scalar('SELECT id FROM parents'):
            self.exec('INSERT INTO parents(user_id,occupation,address) VALUES(?,?,?)',(parent,'Accountant','Nairobi'))
        subjects=[('Mathematics','MATH101','Core mathematics','Sciences',4),('Computer Science','CS101','Programming fundamentals','Technology',4),('English Language','ENG101','Communication and writing','Languages',3),('Physics','PHY101','Mechanics and energy','Sciences',4),('Biology','BIO101','Life sciences','Sciences',4),('Business Studies','BUS101','Entrepreneurship and finance','Business',3)]
        for s in subjects:
            self.exec('INSERT OR IGNORE INTO subjects(name,code,description,department,credits) VALUES(?,?,?,?,?)',s)
        if not self.scalar('SELECT id FROM classes'):
            tids=[self.scalar('SELECT id FROM teachers WHERE employee_number=?',(x,)) for x in ('T001','T002','T003')]
            for i,(name,grade,sec,room,tid) in enumerate([('Form 1A','Form 1','A','Room 101',tids[0]),('Form 2A','Form 2','A','Room 201',tids[1]),('Form 3B','Form 3','B','Room 301',tids[2]),('Form 4A','Form 4','A','Room 401',tids[0])]): self.exec('INSERT INTO classes(class_name,grade_level,section,academic_year_id,room,class_teacher_id) VALUES(?,?,?,?,?,?)',(name,grade,sec,ay,room,tid))
        class1=self.scalar('SELECT id FROM classes WHERE class_name=?',('Form 3B',))
        if not self.scalar('SELECT id FROM students'):
            for i in range(1,13):
                uid = student if i==1 else self.seed_user(f'student{i}',f'student{i}@schoolhub.local','Student123!','student',f'Student{i}','Demo')
                self.exec('INSERT INTO students(user_id,student_number,date_of_birth,gender,address,enrollment_date,class_id) VALUES(?,?,?,?,?,?,?)',(uid,f'STU{i:03d}','2010-0%d-15'%((i%9)+1),'Male' if i%2 else 'Female','Nairobi','2025-01-10',class1 if i<=4 else (self.scalar('SELECT id FROM classes WHERE class_name=?',('Form 1A',)) if i<=7 else self.scalar('SELECT id FROM classes WHERE class_name=?',('Form 4A',)))))
        sid=self.scalar('SELECT id FROM students WHERE user_id=?',(student,)); pid=self.scalar('SELECT id FROM parents WHERE user_id=?',(parent,)); self.exec('INSERT OR IGNORE INTO parent_students(parent_id,student_id,relationship) VALUES(?,?,?)',(pid,sid,'Mother'))
        teacher_ids=[self.scalar('SELECT id FROM teachers WHERE employee_number=?',(x,)) for x in ('T001','T002','T003')]
        class_ids=[r['id'] for r in self.q('SELECT id FROM classes ORDER BY id')]
        sub_ids={r['code']:r['id'] for r in self.q('SELECT id,code FROM subjects')}
        for tid,code,cid in [(teacher_ids[0],'MATH101',class_ids[0]),(teacher_ids[1],'CS101',class_ids[0]),(teacher_ids[2],'ENG101',class_ids[0]),(teacher_ids[0],'PHY101',class_ids[0])]: self.exec('INSERT OR IGNORE INTO teacher_subjects(teacher_id,subject_id,class_id) VALUES(?,?,?)',(tid,sub_ids[code],cid))
        if not self.scalar('SELECT id FROM courses'):
            courses=[('MATH101',teacher_ids[0],'Algebra & Functions','Master algebraic reasoning and functions.','Intermediate',36),('CS101',teacher_ids[1],'Python Programming','Learn programming concepts through practical examples.','Beginner',42),('ENG101',teacher_ids[2],'Academic Writing','Build strong academic writing and communication skills.','Intermediate',30),('PHY101',teacher_ids[0],'Mechanics','Understand motion, forces and energy.','Intermediate',40),('BIO101',teacher_ids[2],'Cell Biology','Explore cells and biological systems.','Beginner',32),('BUS101',teacher_ids[2],'Entrepreneurship','Learn business planning and financial basics.','Beginner',28)]
            for code,tid,title,desc,diff,dur in courses:
                cid=self.exec('INSERT INTO courses(subject_id,teacher_id,title,description,difficulty,duration) VALUES(?,?,?,?,?,?)',(sub_ids[code],tid,title,desc,diff,dur))
                for m in range(1,3):
                    mid=self.exec('INSERT INTO course_modules(course_id,title,description,position) VALUES(?,?,?,?)',(cid,f'Module {m}',f'Core {title} topic {m}.',m))
                    for l in range(1,4): self.exec('INSERT INTO lessons(module_id,title,content,position,estimated_minutes) VALUES(?,?,?,?,?)',(mid,f'Lesson {m}.{l}',f'This is a complete demo lesson for {title}. Read the concepts, take notes, and mark this lesson complete when finished.',l,20))
        math_course=self.scalar('SELECT id FROM courses WHERE title=?',('Algebra & Functions',)); cs_course=self.scalar('SELECT id FROM courses WHERE title=?',('Python Programming',));
        if not self.scalar('SELECT id FROM enrollments'):
            for st in self.q('SELECT id FROM students'):
                for cr in self.q('SELECT id FROM courses'):
                    self.exec('INSERT OR IGNORE INTO enrollments(student_id,course_id,completion_percentage,status) VALUES(?,?,?,?)',(st['id'],cr['id'],random.choice([20,35,55,70,85]),'Active'))
        if not self.scalar('SELECT id FROM assignments'):
            tid=teacher_ids[0]; a=self.exec('INSERT INTO assignments(course_id,teacher_id,title,description,instructions,assigned_date,due_date,max_score) VALUES(?,?,?,?,?,?,?,?)',(math_course,tid,'Quadratic Equations','Practice quadratic equations.','Solve exercises 1-10 and show working.','2026-08-20','2026-09-05',100));
            for st in self.q('SELECT id FROM students LIMIT 8'):
                self.exec('INSERT OR IGNORE INTO assignment_submissions(assignment_id,student_id,submission_text,submitted_at,score,feedback,status) VALUES(?,?,?,?,?,?,?)',(a,st['id'],'Completed solution set.', '2026-08-27 14:00' if st['id']%2 else None, 88 if st['id']%2 else None,'Good work.' if st['id']%2 else None,'Graded' if st['id']%2 else 'Pending'))
        if not self.scalar('SELECT id FROM exams'):
            e=self.exec('INSERT INTO exams(course_id,teacher_id,title,description,exam_date,duration_minutes,max_score,exam_type,randomize) VALUES(?,?,?,?,?,?,?,?,?)',(cs_course,teacher_ids[1],'Python Fundamentals Exam','Assess programming fundamentals.','2026-09-12',25,20,'Exam',1))
            questions=[('What keyword defines a function in Python?','multiple_choice',4,['func','def','function','lambda'],1),('Python lists are mutable.','true_false',4,['True','False'],1),('Which type stores key/value pairs?','multiple_choice',4,['list','tuple','dict','set'],3),('Name the built-in function used to get the length of a sequence.','short_answer',4,[],0),('Which symbol starts a comment?','multiple_choice',4,['//','#','--','/*'],2)]
            for pos,(qt,typ,pts,opts,correct) in enumerate(questions,1):
                q=self.exec('INSERT INTO questions(exam_id,question_text,question_type,points,position) VALUES(?,?,?,?,?)',(e,qt,typ,pts,pos))
                for oi,opt in enumerate(opts,1): self.exec('INSERT INTO question_options(question_id,option_text,is_correct) VALUES(?,?,?)',(q,opt,1 if oi==correct else 0))
        if not self.scalar('SELECT id FROM grades'):
            for st in self.q('SELECT id FROM students LIMIT 10'):
                for code,score in [('MATH101',82+(st['id']%8)),('CS101',76+(st['id']%10)),('ENG101',88-(st['id']%6))]:
                    self.exec('INSERT INTO grades(student_id,subject_id,assessment_type,assessment_id,score,max_score,percentage,term,academic_year_id,teacher_id) VALUES(?,?,?,?,?,?,?,?,?,?)',(st['id'],sub_ids[code],'exam',0,score,100,score,'Term 1',ay,teacher_ids[0]))
        if not self.scalar('SELECT id FROM attendance'):
            for st in self.q('SELECT id,class_id FROM students'):
                for d in range(1,16):
                    date=(dt.date.today()-dt.timedelta(days=d)).isoformat(); status='present' if (st['id']+d)%9 else ('late' if d%5==0 else 'absent')
                    self.exec('INSERT OR IGNORE INTO attendance(student_id,class_id,date,status,check_in_time,recorded_by) VALUES(?,?,?,?,?,?)',(st['id'],st['class_id'],date,status,'08:05' if status!='absent' else None,teacher_ids[0]))
        if not self.scalar('SELECT id FROM events'):
            self.exec('INSERT INTO events(title,description,event_type,start_datetime,end_datetime,location,created_by) VALUES(?,?,?,?,?,?,?)',('Parent-Teacher Meeting','Academic progress discussion.','Meeting','2026-09-03 15:00','2026-09-03 17:00','Main Hall',admin))
            self.exec('INSERT INTO events(title,description,event_type,start_datetime,end_datetime,location,created_by) VALUES(?,?,?,?,?,?,?)',('Science Fair','Student projects exhibition.','School Event','2026-09-10 09:00','2026-09-10 15:00','Science Block',admin))
        if not self.scalar('SELECT id FROM announcements'):
            self.exec('INSERT INTO announcements(title,content,author_id,target_role,created_at,priority) VALUES(?,?,?,?,?,?)',('Welcome to the new term','Welcome to SchoolHub LMS. Please review your timetable and upcoming assessments.',admin,'everyone',now(),'High'))
        if not self.scalar('SELECT id FROM achievements'):
            for x in [('First Lesson','Complete your first lesson','LESSON',1,10),('First Assignment','Submit your first assignment','ASSIGNMENT',1,15),('Perfect Quiz','Score 100% on a quiz','QUIZ',100,30),('Perfect Attendance','Maintain 100% attendance','ATTENDANCE',100,50),('Course Completed','Complete a course','COURSE',100,100),('Study Streak','Reach a 7 day streak','STREAK',7,50)]: self.exec('INSERT INTO achievements(name,description,requirement_type,requirement_value,points) VALUES(?,?,?,?,?)',x)

class SchoolHub(tk.Tk):
    def __init__(self):
        super().__init__(); self.title(APP_NAME); self.geometry('1360x820'); self.minsize(1050,680); self.configure(bg=COLORS['bg']); self.db=DB(); self.user=None; self.current_page='Dashboard'; self.exam_state=None; self.protocol('WM_DELETE_WINDOW',self.on_close); self.style(); self.show_login()
    def style(self):
        s=ttk.Style(self); s.theme_use('clam'); s.configure('.',font=('Segoe UI',10)); s.configure('TFrame',background=COLORS['bg']); s.configure('Card.TFrame',background='white'); s.configure('TLabel',background=COLORS['bg'],foreground=COLORS['text']); s.configure('Card.TLabel',background='white',foreground=COLORS['text']); s.configure('Title.TLabel',font=('Segoe UI',24,'bold'),foreground=COLORS['text']); s.configure('H2.TLabel',font=('Segoe UI',15,'bold'),foreground=COLORS['text']); s.configure('Muted.TLabel',foreground=COLORS['muted']); s.configure('TButton',padding=(12,8)); s.configure('Primary.TButton',background=COLORS['primary'],foreground='white',font=('Segoe UI',10,'bold')); s.map('Primary.TButton',background=[('active',COLORS['primary_dark'])]); s.configure('Treeview',rowheight=32,background='white',fieldbackground='white',borderwidth=0); s.configure('Treeview.Heading',font=('Segoe UI',10,'bold'),padding=8); s.configure('TNotebook',background=COLORS['bg']); s.configure('TNotebook.Tab',padding=(14,8))
    def clear(self):
        for w in self.winfo_children(): w.destroy()
    def show_login(self):
        self.clear(); outer=ttk.Frame(self); outer.pack(fill='both',expand=True); left=tk.Frame(outer,bg=COLORS['primary'],width=470); left.pack(side='left',fill='y'); left.pack_propagate(False); tk.Label(left,text='SchoolHub',font=('Segoe UI',34,'bold'),fg='white',bg=COLORS['primary']).pack(anchor='w',padx=50,pady=(150,8)); tk.Label(left,text='Complete School Learning\nManagement System',font=('Segoe UI',18),fg='white',bg=COLORS['primary'],justify='left').pack(anchor='w',padx=50); tk.Label(left,text='Offline-first academic management for\nstudents, teachers, parents and administrators.',font=('Segoe UI',11),fg='#DBEAFE',bg=COLORS['primary'],justify='left').pack(anchor='w',padx=50,pady=30)
        right=tk.Frame(outer,bg=COLORS['bg']); right.pack(fill='both',expand=True); card=tk.Frame(right,bg='white',highlightbackground=COLORS['border'],highlightthickness=1); card.place(relx=.5,rely=.5,anchor='center',width=480,height=500); tk.Label(card,text='Welcome back',font=('Segoe UI',25,'bold'),bg='white',fg=COLORS['text']).pack(anchor='w',padx=45,pady=(48,5)); tk.Label(card,text='Sign in to continue to your dashboard',font=('Segoe UI',10),bg='white',fg=COLORS['muted']).pack(anchor='w',padx=45,pady=(0,30));
        tk.Label(card,text='Email or username',bg='white',fg=COLORS['text'],font=('Segoe UI',10,'bold')).pack(anchor='w',padx=45); self.login_user=tk.Entry(card,font=('Segoe UI',12),relief='solid',bd=1); self.login_user.pack(fill='x',padx=45,pady=(7,18),ipady=8); tk.Label(card,text='Password',bg='white',fg=COLORS['text'],font=('Segoe UI',10,'bold')).pack(anchor='w',padx=45); self.login_pass=tk.Entry(card,show='*',font=('Segoe UI',12),relief='solid',bd=1); self.login_pass.pack(fill='x',padx=45,pady=(7,22),ipady=8); ttk.Button(card,text='Sign In',style='Primary.TButton',command=self.login).pack(fill='x',padx=45,ipady=5); tk.Label(card,text='Demo: admin@schoolhub.local / Admin123!',bg='white',fg=COLORS['muted']).pack(pady=22); self.login_pass.bind('<Return>',lambda e:self.login()); self.login_user.focus_set()
    def login(self):
        ident=self.login_user.get().strip(); password=self.login_pass.get(); u=self.db.q('SELECT * FROM users WHERE (email=? OR username=?) AND is_active=1',(ident,ident),True)
        if not u or not verify_password(password,u['password_hash']): messagebox.showerror('Sign in failed','Invalid credentials or inactive account.'); return
        self.db.exec('UPDATE users SET last_login=? WHERE id=?',(now(),u['id'])); self.user=dict(u); self.audit('User logged in','users',u['id'],u['email']); self.build_shell()
    def audit(self,action,entity='',entity_id=None,details=''):
        if self.user: self.db.exec('INSERT INTO audit_logs(user_id,action,entity_type,entity_id,details) VALUES(?,?,?,?,?)',(self.user['id'],action,entity,entity_id,details))
    def logout(self): self.audit('User logged out','users',self.user['id']); self.user=None; self.show_login()
    def build_shell(self):
        self.clear(); self.sidebar=tk.Frame(self,bg='#0F172A',width=235); self.sidebar.pack(side='left',fill='y'); self.sidebar.pack_propagate(False); self.main=tk.Frame(self,bg=COLORS['bg']); self.main.pack(side='left',fill='both',expand=True); self.top=tk.Frame(self.main,bg='white',height=70); self.top.pack(fill='x'); self.top.pack_propagate(False); self.content=tk.Frame(self.main,bg=COLORS['bg']); self.content.pack(fill='both',expand=True); self.make_sidebar(); self.refresh_top(); self.navigate('Dashboard')
    def make_sidebar(self):
        for w in self.sidebar.winfo_children(): w.destroy()
        tk.Label(self.sidebar,text='SchoolHub',font=('Segoe UI',22,'bold'),fg='white',bg='#0F172A').pack(anchor='w',padx=22,pady=(24,0)); tk.Label(self.sidebar,text='LMS',font=('Segoe UI',9,'bold'),fg='#93C5FD',bg='#0F172A').pack(anchor='w',padx=24,pady=(0,20)); role=self.user['role']; menus={'student':['Dashboard','My Courses','Lessons','Assignments','Exams','Grades','Attendance','Calendar','Messages','Notifications','Achievements','Certificates','Study Tracker','Profile','Settings'],'teacher':['Dashboard','My Classes','My Courses','Students','Assignments','Exams','Gradebook','Attendance','Calendar','Messages','Announcements','Analytics','Profile','Settings'],'parent':['Dashboard','My Children','Grades','Attendance','Assignments','Exams','Calendar','Messages','Notifications','Reports','Profile','Settings'],'admin':['Dashboard','Users','Students','Teachers','Parents','Classes','Subjects','Courses','Assignments','Exams','Gradebook','Attendance','Timetable','Calendar','Announcements','Messages','Analytics','Reports','Audit Logs','System Settings']}[role]
        self.nav_buttons=[]
        for name in menus:
            b=tk.Button(self.sidebar,text=name,anchor='w',bg='#0F172A',fg='#CBD5E1',activebackground='#1E293B',activeforeground='white',relief='flat',bd=0,font=('Segoe UI',10),padx=24,pady=8,command=lambda n=name:self.navigate(n)); b.pack(fill='x'); self.nav_buttons.append((name,b))
        tk.Frame(self.sidebar,bg='#334155',height=1).pack(fill='x',padx=20,pady=10); tk.Button(self.sidebar,text='Logout',anchor='w',bg='#0F172A',fg='#FCA5A5',activebackground='#1E293B',relief='flat',bd=0,padx=24,pady=9,command=self.logout).pack(fill='x')
    def refresh_top(self):
        for w in self.top.winfo_children(): w.destroy()
        tk.Label(self.top,text=self.current_page,font=('Segoe UI',17,'bold'),bg='white',fg=COLORS['text']).pack(side='left',padx=25); unread=self.db.scalar('SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0',(self.user['id'],)) or 0; msg=self.db.scalar('SELECT COUNT(*) FROM messages WHERE recipient_id=? AND is_read=0',(self.user['id'],)) or 0; tk.Label(self.top,text=f'Messages {msg}   Notifications {unread}',bg='white',fg=COLORS['muted']).pack(side='right',padx=18); tk.Label(self.top,text=f"{self.user['first_name']} {self.user['last_name']}  |  {self.user['role'].title()}",bg='white',fg=COLORS['text'],font=('Segoe UI',10,'bold')).pack(side='right')
    def navigate(self,name):
        self.current_page=name; self.refresh_top();
        for n,b in self.nav_buttons: b.configure(bg='#1D4ED8' if n==name else '#0F172A',fg='white' if n==name else '#CBD5E1')
        for w in self.content.winfo_children(): w.destroy()
        fn=getattr(self,'page_'+re.sub(r'[^a-z]','_',name.lower()),self.page_generic); fn()
    def page_generic(self):
        # Every sidebar destination resolves to a real page. Role-specific pages
        # are dispatched here so no navigation item becomes a dead end.
        handlers = {
            'Students': self.teacher_students_page,
            'My Children': self.page_my_children,
            'Reports': self.reports_page,
            'Assignments': self.parent_assignments_page if self.user['role']=='parent' else self.assignments_page,
            'Exams': self.parent_exams_page if self.user['role']=='parent' else self.exams_page,
            'Grades': self.parent_grades_page,
            'Attendance': self.attendance_page,
            'Messages': self.messages_page,
            'Notifications': self.page_notifications,
            'Calendar': self.page_calendar,
            'Profile': self.page_profile,
            'Settings': self.page_settings,
            'Analytics': self.analytics_page,
            'Gradebook': self.gradebook_page,
            'Announcements': self.announcements_page,
        }
        handler = handlers.get(self.current_page)
        if handler: handler()
        else:
            f = self.scroll(); self.page_title(f, self.current_page, 'This module is available in the current SchoolHub build.')
            tk.Label(f, text='Use the navigation on the left to explore the available records and actions.', bg=COLORS['bg'], fg=COLORS['muted'], font=('Segoe UI',11)).pack(anchor='w', padx=28, pady=20)
    def scroll(self):
        c=tk.Canvas(self.content,bg=COLORS['bg'],highlightthickness=0); sb=ttk.Scrollbar(self.content,orient='vertical',command=c.yview); f=tk.Frame(c,bg=COLORS['bg']); f.bind('<Configure>',lambda e:c.configure(scrollregion=c.bbox('all'))); c.create_window((0,0),window=f,anchor='nw'); c.configure(yscrollcommand=sb.set); c.pack(side='left',fill='both',expand=True); sb.pack(side='right',fill='y'); return f
    def page_title(self,parent,title,subtitle=''):
        ttk.Label(parent,text=title,style='Title.TLabel').pack(anchor='w',padx=26,pady=(24,3));
        if subtitle: ttk.Label(parent,text=subtitle,style='Muted.TLabel').pack(anchor='w',padx=28,pady=(0,18))
    def card(self,parent,title,value,sub='',column=0):
        f=tk.Frame(parent,bg='white',highlightbackground=COLORS['border'],highlightthickness=1); f.grid(row=0,column=column,sticky='nsew',padx=7); tk.Label(f,text=title,bg='white',fg=COLORS['muted'],font=('Segoe UI',10,'bold')).pack(anchor='w',padx=18,pady=(16,3)); tk.Label(f,text=str(value),bg='white',fg=COLORS['text'],font=('Segoe UI',24,'bold')).pack(anchor='w',padx=18); tk.Label(f,text=sub,bg='white',fg=COLORS['muted']).pack(anchor='w',padx=18,pady=(2,16)); return f
    def tree(self,parent,cols,rows,height=12):
        frame=tk.Frame(parent,bg='white'); frame.pack(fill='both',expand=True,padx=26,pady=10); tv=ttk.Treeview(frame,columns=[c[0] for c in cols],show='headings',height=height); y=ttk.Scrollbar(frame,orient='vertical',command=tv.yview); x=ttk.Scrollbar(frame,orient='horizontal',command=tv.xview); tv.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        for key,label,width in cols: tv.heading(key,text=label); tv.column(key,width=width,anchor='w')
        for r in rows: tv.insert('', 'end', values=r)
        tv.grid(row=0,column=0,sticky='nsew'); y.grid(row=0,column=1,sticky='ns'); x.grid(row=1,column=0,sticky='ew'); frame.grid_rowconfigure(0,weight=1); frame.grid_columnconfigure(0,weight=1); return tv
    def buttons(self,parent,items):
        f=tk.Frame(parent,bg=COLORS['bg']); f.pack(fill='x',padx=26,pady=10)
        for text,cmd in items: ttk.Button(f,text=text,style='Primary.TButton' if text in ('Add','Create','Save','Submit','Send','Start') else 'TButton',command=cmd).pack(side='left',padx=(0,8))
        return f
    def stat_data(self,student_id):
        avg=self.db.scalar('SELECT AVG(percentage) FROM grades WHERE student_id=?',(student_id,)) or 0; att=self.db.scalar("SELECT AVG(CASE WHEN status IN ('present','late') THEN 100.0 ELSE 0 END) FROM attendance WHERE student_id=?",(student_id,)) or 0; total=self.db.scalar('SELECT COUNT(*) FROM enrollments WHERE student_id=?',(student_id,)) or 0; comp=self.db.scalar('SELECT AVG(completion_percentage) FROM enrollments WHERE student_id=?',(student_id,)) or 0; gpa=gpa_point(avg); return avg,att,total,comp,gpa
    def current_student(self): return self.db.q('SELECT s.*,u.first_name,u.last_name,u.email,c.class_name FROM students s JOIN users u ON u.id=s.user_id LEFT JOIN classes c ON c.id=s.class_id WHERE s.user_id=?',(self.user['id'],),True)
    def page_dashboard(self):
        f=self.scroll(); role=self.user['role']; self.page_title(f,f'Good day, {self.user["first_name"]}', 'Here is your academic workspace at a glance.')
        if role=='student': self.dashboard_student(f)
        elif role=='teacher': self.dashboard_teacher(f)
        elif role=='parent': self.dashboard_parent(f)
        else: self.dashboard_admin(f)
    def dashboard_student(self,p):
        s=self.current_student(); avg,att,courses,comp,gpa=self.stat_data(s['id']); row=tk.Frame(p,bg=COLORS['bg']); row.pack(fill='x',padx=20); [self.card(row,*x,column=i) for i,x in enumerate([('GPA',f'{gpa:.2f}',performance(avg)),('Average',f'{avg:.1f}%','Academic performance'),('Attendance',f'{att:.0f}%','Present or late'),('Courses',courses,f'{comp:.0f}% average progress')])];
        self.section_table(p,'Upcoming Assignments',self.db.q("SELECT a.title,c.title,a.due_date,COALESCE(s.status,'Pending') FROM assignments a JOIN courses c ON c.id=a.course_id LEFT JOIN assignment_submissions s ON s.assignment_id=a.id AND s.student_id=? WHERE a.due_date>=? ORDER BY a.due_date LIMIT 6",(s['id'],today())),[('title','Assignment',220),('course','Course',220),('due','Due',130),('status','Status',130)]); self.section_table(p,'Recent Grades',self.db.q('SELECT su.name,g.percentage,g.assessment_type,g.created_at FROM grades g JOIN subjects su ON su.id=g.subject_id WHERE g.student_id=? ORDER BY g.id DESC LIMIT 6',(s['id'],)),[('subject','Subject',220),('percentage','Score',120),('type','Type',130),('date','Date',180)])
        insights=[]
        if att<75: insights.append('Attendance Alert: attendance is below 75%.')
        if avg<60: insights.append('Academic Support Recommended: average is below 60%.')
        if comp>90: insights.append('Excellent Consistency: course progress is above 90%.')
        if insights: self.insight_box(p,insights)
    def dashboard_teacher(self,p):
        tid=self.db.scalar('SELECT id FROM teachers WHERE user_id=?',(self.user['id'],)); classes=self.db.scalar('SELECT COUNT(DISTINCT class_id) FROM teacher_subjects WHERE teacher_id=?',(tid,)) or 0; students=self.db.scalar('SELECT COUNT(DISTINCT st.id) FROM teacher_subjects t JOIN students st ON st.class_id=t.class_id WHERE t.teacher_id=?',(tid,)) or 0; courses=self.db.scalar('SELECT COUNT(*) FROM courses WHERE teacher_id=?',(tid,)) or 0; pending=self.db.scalar("SELECT COUNT(*) FROM assignment_submissions s JOIN assignments a ON a.id=s.assignment_id WHERE a.teacher_id=? AND s.status='Pending'",(tid,)) or 0; row=tk.Frame(p,bg=COLORS['bg']); row.pack(fill='x',padx=20); [self.card(row,*x,column=i) for i,x in enumerate([('Classes',classes,'Assigned classes'),('Students',students,'Across your classes'),('Courses',courses,'Courses taught'),('Pending work',pending,'Submissions to review')])]; self.buttons(p,[('Create Assignment',lambda:self.assignment_form()),('Create Exam',lambda:self.exam_form()),('Record Attendance',lambda:self.attendance_page()),('Enter Grades',lambda:self.gradebook_page()),('Send Announcement',lambda:self.announcement_form())]); self.section_table(p,'Recent Submissions',self.db.q('SELECT u.first_name||" "||u.last_name,a.title,s.submitted_at,s.status FROM assignment_submissions s JOIN students st ON st.id=s.student_id JOIN users u ON u.id=st.user_id JOIN assignments a ON a.id=s.assignment_id WHERE a.teacher_id=? ORDER BY s.id DESC LIMIT 8',(tid,)),[('student','Student',220),('assignment','Assignment',240),('submitted','Submitted',180),('status','Status',130)])
    def dashboard_parent(self,p):
        pid=self.db.scalar('SELECT id FROM parents WHERE user_id=?',(self.user['id'],)); children=self.db.q('SELECT s.id,u.first_name,u.last_name,c.class_name FROM parent_students ps JOIN students s ON s.id=ps.student_id JOIN users u ON u.id=s.user_id LEFT JOIN classes c ON c.id=s.class_id WHERE ps.parent_id=?',(pid,)); self.page_title(p,'Children overview',f'{len(children)} linked student(s).');
        for i,ch in enumerate(children):
            avg,att,courses,comp,gpa=self.stat_data(ch['id']); box=tk.Frame(p,bg='white',highlightbackground=COLORS['border'],highlightthickness=1); box.pack(fill='x',padx=26,pady=7); tk.Label(box,text=f"{ch['first_name']} {ch['last_name']}  |  {ch['class_name'] or 'Unassigned'}",font=('Segoe UI',14,'bold'),bg='white',fg=COLORS['text']).pack(anchor='w',padx=18,pady=(14,4)); tk.Label(box,text=f'GPA {gpa:.2f}    Average {avg:.1f}%    Attendance {att:.0f}%    Course progress {comp:.0f}%',bg='white',fg=COLORS['muted']).pack(anchor='w',padx=18,pady=(0,14))
    def dashboard_admin(self,p):
        vals=[('Students',self.db.scalar('SELECT COUNT(*) FROM students') or 0,'Enrolled'),('Teachers',self.db.scalar('SELECT COUNT(*) FROM teachers') or 0,'Faculty'),('Parents',self.db.scalar('SELECT COUNT(*) FROM parents') or 0,'Guardians'),('Classes',self.db.scalar('SELECT COUNT(*) FROM classes') or 0,'Active classes'),('Courses',self.db.scalar('SELECT COUNT(*) FROM courses') or 0,'Learning content')]; row=tk.Frame(p,bg=COLORS['bg']); row.pack(fill='x',padx=20); [self.card(row,*x,column=i) for i,x in enumerate(vals[:5])]; self.section_table(p,'School Performance',self.db.q('SELECT s.name,ROUND(AVG(g.percentage),1),COUNT(g.id) FROM subjects s LEFT JOIN grades g ON g.subject_id=s.id GROUP BY s.id ORDER BY AVG(g.percentage) DESC'),[('subject','Subject',260),('avg','Average',140),('records','Grade records',150)]); self.section_table(p,'Recent Activity',self.db.q('SELECT action,entity_type,timestamp,details FROM audit_logs ORDER BY id DESC LIMIT 10'),[('action','Action',220),('entity','Entity',130),('time','Timestamp',180),('details','Details',320)])
    def insight_box(self,p,items):
        box=tk.Frame(p,bg='#EFF6FF',highlightbackground='#BFDBFE',highlightthickness=1); box.pack(fill='x',padx=26,pady=10); tk.Label(box,text='Academic Insights',font=('Segoe UI',12,'bold'),bg='#EFF6FF',fg='#1E40AF').pack(anchor='w',padx=16,pady=(12,5)); [tk.Label(box,text=x,bg='#EFF6FF',fg='#1E3A8A',anchor='w').pack(fill='x',padx=16,pady=3) for x in items]
    def section_table(self,p,title,rows,cols):
        tk.Label(p,text=title,font=('Segoe UI',14,'bold'),bg=COLORS['bg'],fg=COLORS['text']).pack(anchor='w',padx=28,pady=(18,2)); data=[]
        for r in rows: data.append(tuple(r))
        self.tree(p,cols,data,7)
    def page_my_courses(self):
        if self.user['role']=='student': self.courses_page(student_only=True)
        else: self.courses_page(student_only=False)
    def page_courses(self): self.courses_page()
    def courses_page(self,student_only=False):
        f=self.scroll(); self.page_title(f,'My Courses' if student_only else 'Course Management','Browse, enroll and manage learning content.'); search=tk.StringVar(); top=tk.Frame(f,bg=COLORS['bg']); top.pack(fill='x',padx=26); tk.Entry(top,textvariable=search,width=35).pack(side='left',ipady=6); ttk.Button(top,text='Search',command=lambda:load()).pack(side='left',padx=8); rows_frame=tk.Frame(f,bg=COLORS['bg']); rows_frame.pack(fill='both',expand=True)
        def load():
            for w in rows_frame.winfo_children(): w.destroy()
            q='%'+search.get().strip()+'%'
            rows=self.db.q('SELECT c.id,c.title,s.name,u.first_name||" "||u.last_name,c.difficulty,c.duration,c.status FROM courses c JOIN subjects s ON s.id=c.subject_id JOIN teachers t ON t.id=c.teacher_id JOIN users u ON u.id=t.user_id WHERE c.title LIKE ? OR s.name LIKE ? ORDER BY c.id DESC',(q,q))
            if student_only:
                sid=self.current_student()['id']; rows=self.db.q('SELECT c.id,c.title,s.name,u.first_name||" "||u.last_name,c.difficulty,c.duration,c.status FROM courses c JOIN subjects s ON s.id=c.subject_id JOIN teachers t ON t.id=c.teacher_id JOIN users u ON u.id=t.user_id JOIN enrollments e ON e.course_id=c.id WHERE e.student_id=? AND (c.title LIKE ? OR s.name LIKE ?) ORDER BY c.id DESC',(sid,q,q))
            tv=self.tree(rows_frame,[('id','ID',60),('title','Course',250),('subject','Subject',180),('teacher','Teacher',180),('difficulty','Level',110),('duration','Minutes',100),('status','Status',120)],rows,14)
            if not student_only and self.user['role'] in ('admin','teacher'): self.buttons(rows_frame,[('Create',self.course_form),('Refresh',load)])
            if self.user['role']=='student': self.buttons(rows_frame,[('Open Course',lambda:self.open_course(tv))])
        load()
    def open_course(self,tv):
        sel=tv.selection();
        if not sel: return messagebox.showwarning('Select course','Select a course first.')
        cid=tv.item(sel[0])['values'][0]; self.course_detail(int(cid))
    def course_detail(self,cid):
        for w in self.content.winfo_children(): w.destroy()
        f=self.scroll(); c=self.db.q('SELECT c.*,s.name subject,u.first_name||" "||u.last_name teacher FROM courses c JOIN subjects s ON s.id=c.subject_id JOIN teachers t ON t.id=c.teacher_id JOIN users u ON u.id=t.user_id WHERE c.id=?',(cid,),True); self.page_title(f,c['title'],f"{c['subject']}  |  {c['teacher']}  |  {c['difficulty']}");
        if self.user['role']=='student':
            sid=self.current_student()['id']; self.db.exec('INSERT OR IGNORE INTO enrollments(student_id,course_id) VALUES(?,?)',(sid,cid))
        for m in self.db.q('SELECT * FROM course_modules WHERE course_id=? ORDER BY position',(cid,)):
            box=tk.Frame(f,bg='white',highlightbackground=COLORS['border'],highlightthickness=1); box.pack(fill='x',padx=26,pady=7); tk.Label(box,text=m['title'],font=('Segoe UI',13,'bold'),bg='white',fg=COLORS['text']).pack(anchor='w',padx=16,pady=(12,2)); tk.Label(box,text=m['description'],bg='white',fg=COLORS['muted']).pack(anchor='w',padx=16,pady=(0,8));
            for l in self.db.q('SELECT * FROM lessons WHERE module_id=? ORDER BY position',(m['id'],)):
                done=False
                if self.user['role']=='student': done=bool(self.db.scalar('SELECT completed FROM learning_progress WHERE student_id=? AND lesson_id=?',(sid,l['id'])) or 0)
                b=ttk.Button(box,text=f"{'[Completed] ' if done else ''}{l['title']}  ({l['estimated_minutes']} min)",command=lambda lid=l['id'],cc=cid:self.lesson_view(lid,cc)); b.pack(fill='x',padx=14,pady=3)
    def lesson_view(self,lid,cid):
        l=self.db.q('SELECT l.*,m.title module FROM lessons l JOIN course_modules m ON m.id=l.module_id WHERE l.id=?',(lid,),True); win=tk.Toplevel(self); win.title(l['title']); win.geometry('760x600'); win.configure(bg='white'); tk.Label(win,text=l['title'],font=('Segoe UI',20,'bold'),bg='white',fg=COLORS['text']).pack(anchor='w',padx=28,pady=25); txt=tk.Text(win,wrap='word',font=('Segoe UI',11),relief='flat',bg='#F8FAFC'); txt.pack(fill='both',expand=True,padx=28); txt.insert('1.0',l['content']); txt.configure(state='disabled');
        if self.user['role']=='student':
            sid=self.current_student()['id']; ttk.Button(win,text='Mark Lesson Completed',style='Primary.TButton',command=lambda:self.complete_lesson(win,sid,lid,cid)).pack(pady=20)
    def complete_lesson(self,win,sid,lid,cid): self.db.exec('INSERT INTO learning_progress(student_id,lesson_id,completed,completed_at,time_spent) VALUES(?,?,1,?,0) ON CONFLICT(student_id,lesson_id) DO UPDATE SET completed=1,completed_at=excluded.completed_at',(sid,lid,now())); self.recalc_enrollment(sid,cid); self.check_achievements(sid); self.notify(sid,'Lesson completed','Your learning progress was updated.','achievement'); win.destroy(); messagebox.showinfo('Progress saved','Lesson marked as completed.'); self.navigate('My Courses')
    def recalc_enrollment(self,sid,cid):
        total=self.db.scalar('SELECT COUNT(*) FROM lessons l JOIN course_modules m ON m.id=l.module_id WHERE m.course_id=?',(cid,)) or 0; done=self.db.scalar('SELECT COUNT(*) FROM learning_progress lp JOIN lessons l ON l.id=lp.lesson_id JOIN course_modules m ON m.id=l.module_id WHERE lp.student_id=? AND m.course_id=? AND lp.completed=1',(sid,cid)) or 0; self.db.exec('UPDATE enrollments SET completion_percentage=? WHERE student_id=? AND course_id=?',(pct(done,total),sid,cid))
    def page_lessons(self): self.page_my_courses()
    def page_assignments(self):
        if self.user['role']=='parent': self.parent_assignments_page()
        else: self.assignments_page()
    def assignments_page(self):
        f=self.scroll(); self.page_title(f,'Assignments','Track deadlines, submissions, grades and feedback.'); sid=self.current_student()['id'] if self.user['role']=='student' else None; tid=self.db.scalar('SELECT id FROM teachers WHERE user_id=?',(self.user['id'],)) if self.user['role']=='teacher' else None
        if self.user['role'] in ('teacher','admin'):
            if self.user['role']=='admin': rows=self.db.q('SELECT a.id,a.title,c.title,a.due_date,a.max_score,COUNT(s.id),SUM(CASE WHEN s.status="Pending" THEN 1 ELSE 0 END) FROM assignments a JOIN courses c ON c.id=a.course_id LEFT JOIN assignment_submissions s ON s.assignment_id=a.id GROUP BY a.id ORDER BY a.due_date')
            else: rows=self.db.q('SELECT a.id,a.title,c.title,a.due_date,a.max_score,COUNT(s.id),SUM(CASE WHEN s.status="Pending" THEN 1 ELSE 0 END) FROM assignments a JOIN courses c ON c.id=a.course_id LEFT JOIN assignment_submissions s ON s.assignment_id=a.id WHERE a.teacher_id=? GROUP BY a.id ORDER BY a.due_date',(tid,)); cols=[('id','ID',60),('title','Assignment',230),('course','Course',220),('due','Due',130),('max','Max',80),('submitted','Submissions',110),('pending','Pending',90)]; self.tree(f,cols,rows,15); self.buttons(f,[('Create',self.assignment_form),('Refresh',lambda:self.navigate('Assignments'))])
        else: rows=self.db.q('SELECT a.id,a.title,c.title,a.due_date,a.max_score,COALESCE(s.status,"Pending"),COALESCE(s.score,"-") FROM assignments a JOIN courses c ON c.id=a.course_id JOIN enrollments e ON e.course_id=c.id AND e.student_id=? LEFT JOIN assignment_submissions s ON s.assignment_id=a.id AND s.student_id=? ORDER BY a.due_date',(sid,sid,)); tv=self.tree(f,[('id','ID',60),('title','Assignment',220),('course','Course',210),('due','Due',120),('max','Max',80),('status','Status',130),('score','Score',90)],rows,15); self.buttons(f,[('Submit',lambda:self.submit_assignment(tv)),('Refresh',lambda:self.navigate('Assignments'))])
    def assignment_form(self):
        win=self.form_window('Create Assignment',430,500); entries={}; fields=[('Title',''),('Course','')]; tk.Label(win,text='Title',bg='white').pack(anchor='w',padx=25,pady=(20,3)); e=tk.Entry(win); e.pack(fill='x',padx=25,ipady=5); entries['title']=e; tk.Label(win,text='Course',bg='white').pack(anchor='w',padx=25,pady=(14,3)); courses=self.db.q('SELECT id,title FROM courses WHERE teacher_id=?',(self.db.scalar('SELECT id FROM teachers WHERE user_id=?',(self.user['id'],)),)) if self.user['role']=='teacher' else self.db.q('SELECT id,title FROM courses'); cb=ttk.Combobox(win,values=[f"{r['id']} - {r['title']}" for r in courses],state='readonly'); cb.pack(fill='x',padx=25); entries['course']=cb
        for label,key in [('Description','description'),('Instructions','instructions'),('Assigned date','assigned_date'),('Due date','due_date'),('Maximum score','max_score')]: tk.Label(win,text=label,bg='white').pack(anchor='w',padx=25,pady=(12,3)); x=tk.Entry(win); x.pack(fill='x',padx=25,ipady=5); entries[key]=x
        entries['assigned_date'].insert(0,today()); entries['due_date'].insert(0,(dt.date.today()+dt.timedelta(days=7)).isoformat()); entries['max_score'].insert(0,'100')
        def save():
            title=entries['title'].get().strip(); course=cb.get().split(' - ')[0] if cb.get() else ''; due=entries['due_date'].get().strip();
            if not title or not course or not parse_date(due): return messagebox.showerror('Validation','Title, course and a valid due date are required.',parent=win)
            tid=self.db.scalar('SELECT id FROM teachers WHERE user_id=?',(self.user['id'],)); aid=self.db.exec('INSERT INTO assignments(course_id,teacher_id,title,description,instructions,assigned_date,due_date,max_score) VALUES(?,?,?,?,?,?,?,?)',(int(course),tid,title,entries['description'].get(),entries['instructions'].get(),entries['assigned_date'].get(),due,float(entries['max_score'].get() or 100))); students=self.db.q('SELECT DISTINCT e.student_id FROM enrollments e WHERE e.course_id=?',(int(course),)); [self.notify(r['student_id'],f'New assignment: {title}',f'Due {fmt_date(due)}','assignment') for r in students]; self.audit('Assignment created','assignments',aid,title); win.destroy(); messagebox.showinfo('Saved','Assignment created successfully.'); self.navigate('Assignments')
        ttk.Button(win,text='Save',style='Primary.TButton',command=save).pack(pady=18)
    def submit_assignment(self,tv):
        sel=tv.selection();
        if not sel: return messagebox.showwarning('Select','Select an assignment.')
        aid=int(tv.item(sel[0])['values'][0]); row=self.db.q('SELECT * FROM assignments WHERE id=?',(aid,),True); existing=self.db.q('SELECT * FROM assignment_submissions WHERE assignment_id=? AND student_id=?',(aid,self.current_student()['id']),True)
        win=self.form_window('Submit Assignment',600,440); tk.Label(win,text=row['title'],font=('Segoe UI',16,'bold'),bg='white').pack(anchor='w',padx=25,pady=20); tk.Label(win,text=row['instructions'] or row['description'] or '',bg='white',wraplength=530,justify='left').pack(anchor='w',padx=25); text=tk.Text(win,height=10); text.pack(fill='both',expand=True,padx=25,pady=15); 
        if existing: text.insert('1.0',existing['submission_text'] or '')
        def save():
            if today()>row['due_date']: return messagebox.showerror('Deadline','This assignment is overdue.',parent=win)
            self.db.exec('INSERT INTO assignment_submissions(assignment_id,student_id,submission_text,submitted_at,status) VALUES(?,?,?,?,?) ON CONFLICT(assignment_id,student_id) DO UPDATE SET submission_text=excluded.submission_text,submitted_at=excluded.submitted_at,status="Submitted"',(aid,self.current_student()['id'],text.get('1.0','end').strip(),now())); self.check_achievements(self.current_student()['id']); self.audit('Assignment submitted','assignment_submissions',aid); win.destroy(); messagebox.showinfo('Submitted','Assignment submitted successfully.'); self.navigate('Assignments')
        ttk.Button(win,text='Submit',style='Primary.TButton',command=save).pack(pady=12)
    def page_exams(self):
        if self.user['role']=='parent': self.parent_exams_page()
        else: self.exams_page()
    def exams_page(self):
        f=self.scroll(); self.page_title(f,'Exams','Create, publish, attempt and review assessments.');
        if self.user['role'] in ('teacher','admin'):
            tid=self.db.scalar('SELECT id FROM teachers WHERE user_id=?',(self.user['id'],))
            if self.user['role']=='admin': rows=self.db.q('SELECT e.id,e.title,c.title,e.exam_date,e.duration_minutes,e.max_score,e.status,e.exam_type,COUNT(q.id) FROM exams e JOIN courses c ON c.id=e.course_id LEFT JOIN questions q ON q.exam_id=e.id GROUP BY e.id ORDER BY e.exam_date')
            else: rows=self.db.q('SELECT e.id,e.title,c.title,e.exam_date,e.duration_minutes,e.max_score,e.status,e.exam_type,COUNT(q.id) FROM exams e JOIN courses c ON c.id=e.course_id LEFT JOIN questions q ON q.exam_id=e.id WHERE e.teacher_id=? GROUP BY e.id ORDER BY e.exam_date',(tid,)); tv=self.tree(f,[('id','ID',60),('title','Exam',230),('course','Course',220),('date','Date',130),('duration','Minutes',100),('max','Max',80),('status','Status',100),('type','Type',100),('questions','Questions',100)],rows,14); self.buttons(f,[('Create',self.exam_form),('Manage Questions',lambda:self.question_manager(tv)),('Refresh',lambda:self.navigate('Exams'))])
        else:
            sid=self.current_student()['id']; rows=self.db.q('SELECT e.id,e.title,c.title,e.exam_date,e.duration_minutes,e.max_score,COALESCE(a.status,"Not Started"),COALESCE(a.percentage,"-") FROM exams e JOIN courses c ON c.id=e.course_id JOIN enrollments en ON en.course_id=c.id AND en.student_id=? LEFT JOIN exam_attempts a ON a.exam_id=e.id AND a.student_id=? ORDER BY e.exam_date',(sid,sid,)); tv=self.tree(f,[('id','ID',60),('title','Exam',230),('course','Course',220),('date','Date',130),('duration','Minutes',100),('max','Max',80),('status','Status',130),('score','Result',100)],rows,14); self.buttons(f,[('Start',lambda:self.start_exam(tv)),('Refresh',lambda:self.navigate('Exams'))])
    def exam_form(self):
        win=self.form_window('Create Exam',460,520); labels=[('Title','title'),('Course','course'),('Description','description'),('Exam date','date'),('Duration minutes','duration'),('Maximum score','max')]; ent={}
        for lab,key in labels:
            tk.Label(win,text=lab,bg='white').pack(anchor='w',padx=25,pady=(12,3)); x=ttk.Combobox(win,state='readonly') if key=='course' else tk.Entry(win); x.pack(fill='x',padx=25,ipady=4 if key!='course' else 0); ent[key]=x
        courses=self.db.q('SELECT id,title FROM courses WHERE teacher_id=?',(self.db.scalar('SELECT id FROM teachers WHERE user_id=?',(self.user['id'],)),)); ent['course']['values']=[f"{r['id']} - {r['title']}" for r in courses]; ent['date'].insert(0,(dt.date.today()+dt.timedelta(days=10)).isoformat()); ent['duration'].insert(0,'30'); ent['max'].insert(0,'100')
        def save():
            try: cid=int(ent['course'].get().split(' - ')[0]); duration=int(ent['duration'].get()); maximum=float(ent['max'].get());
            except: return messagebox.showerror('Validation','Course, duration and maximum score must be valid.',parent=win)
            if not ent['title'].get().strip() or not parse_date(ent['date'].get()): return messagebox.showerror('Validation','Enter a title and valid date.',parent=win)
            tid=self.db.scalar('SELECT id FROM teachers WHERE user_id=?',(self.user['id'],)); eid=self.db.exec('INSERT INTO exams(course_id,teacher_id,title,description,exam_date,duration_minutes,max_score) VALUES(?,?,?,?,?,?,?)',(cid,tid,ent['title'].get().strip(),ent['description'].get(),ent['date'].get(),duration,maximum)); self.audit('Exam created','exams',eid,ent['title'].get()); win.destroy(); self.question_manager_by_id(eid)
        ttk.Button(win,text='Create and Add Questions',style='Primary.TButton',command=save).pack(pady=18)
    def question_manager(self,tv):
        sel=tv.selection();
        if not sel: return messagebox.showwarning('Select','Select an exam.')
        self.question_manager_by_id(int(tv.item(sel[0])['values'][0]))
    def question_manager_by_id(self,eid):
        win=self.form_window('Exam Questions',700,620); exam=self.db.q('SELECT * FROM exams WHERE id=?',(eid,),True); tk.Label(win,text=exam['title'],font=('Segoe UI',17,'bold'),bg='white').pack(anchor='w',padx=25,pady=15); box=tk.Frame(win,bg='white'); box.pack(fill='both',expand=True,padx=20); self.tree(box,[('id','ID',50),('q','Question',390),('type','Type',130),('points','Points',80)],[(r['id'],r['question_text'],r['question_type'],r['points']) for r in self.db.q('SELECT * FROM questions WHERE exam_id=? ORDER BY position',(eid,))],10); self.buttons(win,[('Add Question',lambda:self.question_form(eid,win)),('Close',win.destroy)])
    def question_form(self,eid,parent):
        win=self.form_window('Add Question',560,570); tk.Label(win,text='Question',bg='white').pack(anchor='w',padx=25,pady=(18,3)); q=tk.Text(win,height=4); q.pack(fill='x',padx=25); tk.Label(win,text='Type',bg='white').pack(anchor='w',padx=25,pady=(12,3)); typ=ttk.Combobox(win,values=['multiple_choice','true_false','short_answer'],state='readonly'); typ.current(0); typ.pack(fill='x',padx=25); tk.Label(win,text='Points',bg='white').pack(anchor='w',padx=25,pady=(12,3)); pts=tk.Entry(win); pts.insert(0,'1'); pts.pack(fill='x',padx=25); tk.Label(win,text='Options (one per line; prefix * for correct)',bg='white').pack(anchor='w',padx=25,pady=(12,3)); opts=tk.Text(win,height=8); opts.pack(fill='both',expand=True,padx=25)
        def save():
            text=q.get('1.0','end').strip();
            if not text: return messagebox.showerror('Validation','Question text is required.',parent=win)
            try: points=float(pts.get())
            except: return messagebox.showerror('Validation','Points must be numeric.',parent=win)
            pos=(self.db.scalar('SELECT COALESCE(MAX(position),0) FROM questions WHERE exam_id=?',(eid,)) or 0)+1; qid=self.db.exec('INSERT INTO questions(exam_id,question_text,question_type,points,position) VALUES(?,?,?,?,?)',(eid,text,typ.get(),points,pos)); lines=[x.strip() for x in opts.get('1.0','end').splitlines() if x.strip()];
            if typ.get()=='true_false' and not lines: lines=['True','False']
            for line in lines: self.db.exec('INSERT INTO question_options(question_id,option_text,is_correct) VALUES(?,?,?)',(qid,line.lstrip('*').strip(),1 if line.startswith('*') else 0))
            win.destroy(); parent.destroy(); self.question_manager_by_id(eid)
        ttk.Button(win,text='Save Question',style='Primary.TButton',command=save).pack(pady=15)
    def start_exam(self,tv):
        sel=tv.selection();
        if not sel: return messagebox.showwarning('Select','Select an exam.')
        eid=int(tv.item(sel[0])['values'][0]); exam=self.db.q('SELECT * FROM exams WHERE id=?',(eid,),True); qs=self.db.q('SELECT * FROM questions WHERE exam_id=? ORDER BY position',(eid,));
        if not qs: return messagebox.showwarning('No questions','This exam has no questions yet.')
        sid=self.current_student()['id']; existing=self.db.q('SELECT * FROM exam_attempts WHERE exam_id=? AND student_id=? AND status="Submitted" ORDER BY id DESC',(eid,sid),True)
        if existing: return messagebox.showinfo('Already completed',f"You already completed this exam with {existing['percentage']:.1f}%.")
        attempt=self.db.exec('INSERT INTO exam_attempts(exam_id,student_id,started_at,status) VALUES(?,?,?,?)',(eid,sid,now(),'In Progress')); self.exam_state={'attempt':attempt,'exam':dict(exam),'questions':[dict(x) for x in qs],'index':0,'answers':{}}; self.show_exam()
    def show_exam(self):
        for w in self.content.winfo_children(): w.destroy()
        st=self.exam_state; q=st['questions'][st['index']]; self.exam_start_epoch = getattr(self, 'exam_start_epoch', None) or time.time(); f=tk.Frame(self.content,bg=COLORS['bg']); f.pack(fill='both',expand=True,padx=40,pady=30); top=tk.Frame(f,bg='white'); top.pack(fill='x'); tk.Label(top,text=st['exam']['title'],font=('Segoe UI',19,'bold'),bg='white',fg=COLORS['text']).pack(side='left',padx=20,pady=18); remaining=max(0,st['exam']['duration_minutes']*60-int((time.time()-self.exam_start_epoch))); self.exam_timer_label=tk.Label(top,text='',font=('Segoe UI',12,'bold'),bg='white',fg=COLORS['danger']); self.exam_timer_label.pack(side='right',padx=20); tk.Label(f,text=f"Question {st['index']+1} of {len(st['questions'])}   |   {q['points']} points",font=('Segoe UI',11,'bold'),bg=COLORS['bg'],fg=COLORS['muted']).pack(anchor='w',pady=(25,10)); card=tk.Frame(f,bg='white',highlightbackground=COLORS['border'],highlightthickness=1); card.pack(fill='both',expand=True); tk.Label(card,text=q['question_text'],font=('Segoe UI',16,'bold'),wraplength=900,justify='left',bg='white',fg=COLORS['text']).pack(anchor='w',padx=30,pady=30); self.answer_var=tk.StringVar(value=st['answers'].get(q['id'],''));
        if q['question_type'] in ('multiple_choice','true_false'):
            for o in self.db.q('SELECT * FROM question_options WHERE question_id=? ORDER BY id',(q['id'],)): ttk.Radiobutton(card,text=o['option_text'],variable=self.answer_var,value=str(o['id'])).pack(anchor='w',padx=40,pady=8)
        else: self.answer_entry=tk.Entry(card,textvariable=self.answer_var,font=('Segoe UI',12)); self.answer_entry.pack(fill='x',padx=40,pady=15,ipady=8)
        nav=tk.Frame(f,bg=COLORS['bg']); nav.pack(fill='x',pady=15); ttk.Button(nav,text='Previous',command=lambda:self.exam_nav(-1)).pack(side='left'); ttk.Button(nav,text='Next',command=lambda:self.exam_nav(1)).pack(side='left',padx=8); ttk.Button(nav,text='Submit Exam',style='Primary.TButton',command=self.submit_exam).pack(side='right'); self.exam_start_epoch=time.time() if not hasattr(self,'exam_start_epoch') else self.exam_start_epoch; self.update_exam_timer()
    def update_exam_timer(self):
        if not self.exam_state or not self.exam_state.get('attempt'): return
        remaining=self.exam_state['exam']['duration_minutes']*60-int(time.time()-self.exam_start_epoch); self.exam_timer_label.configure(text=f'Time Remaining: {max(0,remaining)//60:02d}:{max(0,remaining)%60:02d}')
        if remaining<=0: self.submit_exam(auto=True)
        else: self.after(1000,self.update_exam_timer)
    def exam_nav(self,d):
        q=self.exam_state['questions'][self.exam_state['index']]; self.exam_state['answers'][q['id']]=self.answer_var.get(); ni=self.exam_state['index']+d
        if 0<=ni<len(self.exam_state['questions']): self.exam_state['index']=ni; self.show_exam()
    def submit_exam(self,auto=False):
        if not self.exam_state: return
        q=self.exam_state['questions'][self.exam_state['index']]; self.exam_state['answers'][q['id']]=self.answer_var.get(); st=self.exam_state; score=0; correct=0
        for q in st['questions']:
            ans=st['answers'].get(q['id'],''); awarded=0
            if q['question_type'] in ('multiple_choice','true_false'):
                op=self.db.q('SELECT * FROM question_options WHERE id=?',(int(ans),),True) if ans.isdigit() else None
                if op and op['is_correct']: awarded=q['points']; correct+=1
            else:
                if ans.strip().lower() in ('len','length','the len function','len()'): awarded=q['points']; correct+=1
            score+=awarded; self.db.exec('INSERT INTO student_answers(attempt_id,question_id,selected_option_id,answer_text,points_awarded) VALUES(?,?,?,?,?) ON CONFLICT(attempt_id,question_id) DO UPDATE SET selected_option_id=excluded.selected_option_id,answer_text=excluded.answer_text,points_awarded=excluded.points_awarded',(st['attempt'],q['id'],int(ans) if ans.isdigit() else None,ans if not ans.isdigit() else '',awarded))
        percentage=pct(score,st['exam']['max_score']); self.db.exec('UPDATE exam_attempts SET submitted_at=?,score=?,percentage=?,status="Submitted" WHERE id=?',(now(),score,percentage,st['attempt'])); self.audit('Exam submitted','exam_attempts',st['attempt'],st['exam']['title']); self.exam_state=None; self.exam_start_epoch=None; self.show_result(st['exam'],score,percentage,correct,len(st['questions']),auto)
    def show_result(self,exam,score,percentage,correct,total,auto=False):
        for w in self.content.winfo_children(): w.destroy()
        f=self.scroll(); self.page_title(f,'Exam Result',exam['title']); box=tk.Frame(f,bg='white',highlightbackground=COLORS['border'],highlightthickness=1); box.pack(fill='x',padx=26,pady=20); tk.Label(box,text=f'{percentage:.1f}%',font=('Segoe UI',42,'bold'),bg='white',fg=COLORS['primary']).pack(pady=(25,5)); tk.Label(box,text=f'Score {score:g} / {exam["max_score"]:g}    |    Correct {correct} / {total}    |    {performance(percentage)}',font=('Segoe UI',12),bg='white',fg=COLORS['muted']).pack(pady=(0,25)); ttk.Button(f,text='Back to Exams',command=lambda:self.navigate('Exams')).pack(padx=26,pady=10)
    def page_grades(self):
        if self.user['role']=='parent': self.parent_grades_page()
        else: self.gradebook_page(student=self.user['role']=='student')
    def gradebook_page_original(self,student=False):
        f=self.scroll(); self.page_title(f,'Grades & Gradebook','Academic scores are calculated from persisted assessment records.');
        if student:
            sid=self.current_student()['id']; rows=self.db.q('SELECT su.name,g.assessment_type,g.score,g.max_score,g.percentage,g.term FROM grades g JOIN subjects su ON su.id=g.subject_id WHERE g.student_id=? ORDER BY su.name,g.id DESC',(sid,)); avg=self.db.scalar('SELECT AVG(percentage) FROM grades WHERE student_id=?',(sid,)) or 0; tk.Label(f,text=f'Overall average: {avg:.1f}%   GPA: {gpa_point(avg):.2f}   Performance: {performance(avg)}',font=('Segoe UI',14,'bold'),bg=COLORS['bg'],fg=COLORS['text']).pack(anchor='w',padx=28,pady=10); self.tree(f,[('subject','Subject',220),('type','Assessment',140),('score','Score',100),('max','Max',90),('percentage','Percentage',120),('term','Term',120)],rows,15)
        else:
            rows=self.db.q('SELECT g.id,u.first_name||" "||u.last_name,s.name,g.assessment_type,g.score,g.max_score,g.percentage FROM grades g JOIN students st ON st.id=g.student_id JOIN users u ON u.id=st.user_id JOIN subjects s ON s.id=g.subject_id ORDER BY g.id DESC'); tv=self.tree(f,[('id','ID',60),('student','Student',220),('subject','Subject',180),('type','Type',120),('score','Score',90),('max','Max',90),('pct','%',90)],rows,15); self.buttons(f,[('Enter Grade',lambda:self.grade_form()),('Refresh',lambda:self.navigate('Gradebook'))])
    def grade_form(self):
        win=self.form_window('Enter Grade',450,430); students=self.db.q('SELECT s.id,u.first_name||" "||u.last_name name FROM students s JOIN users u ON u.id=s.user_id ORDER BY name'); subs=self.db.q('SELECT id,name FROM subjects ORDER BY name');
        ent={}
        for lab,key,vals in [('Student','student',[f"{x['id']} - {x['name']}" for x in students]),('Subject','subject',[f"{x['id']} - {x['name']}" for x in subs]),('Assessment type','type',['assignment','quiz','exam','project','participation'])]: tk.Label(win,text=lab,bg='white').pack(anchor='w',padx=25,pady=(15,3)); c=ttk.Combobox(win,values=vals,state='readonly'); c.pack(fill='x',padx=25); ent[key]=c
        for lab,key,val in [('Score','score',''),('Maximum score','max','100'),('Term','term','Term 1')]: tk.Label(win,text=lab,bg='white').pack(anchor='w',padx=25,pady=(12,3)); e=tk.Entry(win); e.insert(0,val); e.pack(fill='x',padx=25,ipady=5); ent[key]=e
        def save():
            try: sid=int(ent['student'].get().split(' - ')[0]); sub=int(ent['subject'].get().split(' - ')[0]); score=float(ent['score'].get()); maximum=float(ent['max'].get());
            except: return messagebox.showerror('Validation','Complete all fields with valid numbers.',parent=win)
            if score<0 or score>maximum: return messagebox.showerror('Validation','Score must be between 0 and maximum.',parent=win)
            tid=self.db.scalar('SELECT id FROM teachers WHERE user_id=?',(self.user['id'],)); aid=self.db.exec('INSERT INTO grades(student_id,subject_id,assessment_type,score,max_score,percentage,term,academic_year_id,teacher_id) VALUES(?,?,?,?,?,?,?,?,?)',(sid,sub,ent['type'].get(),score,maximum,pct(score,maximum),ent['term'].get(),self.db.scalar('SELECT id FROM academic_years WHERE is_current=1'),tid)); self.notify(sid,'New grade available',f'Your {ent["type"].get()} grade is {pct(score,maximum):.1f}%.','grade'); self.audit('Grade entered','grades',aid); win.destroy(); messagebox.showinfo('Saved','Grade saved successfully.'); self.navigate('Gradebook')
        ttk.Button(win,text='Save',style='Primary.TButton',command=save).pack(pady=18)
    def page_attendance(self): self.attendance_page()
    def attendance_page(self):
        f=self.scroll(); self.page_title(f,'Attendance','Record and monitor attendance.');
        if self.user['role']=='teacher':
            tid=self.db.scalar('SELECT id FROM teachers WHERE user_id=?',(self.user['id'],)); classes=self.db.q('SELECT DISTINCT c.id,c.class_name FROM classes c JOIN teacher_subjects ts ON ts.class_id=c.id WHERE ts.teacher_id=?',(tid,)); cb=ttk.Combobox(f,values=[f"{x['id']} - {x['class_name']}" for x in classes],state='readonly'); cb.pack(anchor='w',padx=26); date=tk.Entry(f); date.insert(0,today()); date.pack(anchor='w',padx=26,pady=8); rows=self.db.q('SELECT s.id,u.first_name||" "||u.last_name,c.class_name FROM students s JOIN users u ON u.id=s.user_id LEFT JOIN classes c ON c.id=s.class_id WHERE s.class_id=? ORDER BY u.last_name',(classes[0]['id'],)) if classes else []; self.attendance_class=cb; self.attendance_date=date; tv=self.tree(f,[('id','Student ID',90),('student','Student',260),('class','Class',180),('status','Status',120)],[(r['id'],r[1],r['class_name'],'') for r in rows],12); self.attendance_tv=tv; self.buttons(f,[('Record',lambda:self.record_attendance(tv)),('Refresh',lambda:self.navigate('Attendance'))]); cb.bind('<<ComboboxSelected>>',lambda e:self.reload_attendance_students(tv))
        else:
            sid=self.current_student()['id'] if self.user['role']=='student' else None
            if self.user['role']=='parent':
                pid=self.db.scalar('SELECT id FROM parents WHERE user_id=?',(self.user['id'],)); sid=self.db.scalar('SELECT student_id FROM parent_students WHERE parent_id=? LIMIT 1',(pid,))
            rows=self.db.q('SELECT date,status,check_in_time,remarks FROM attendance WHERE student_id=? ORDER BY date DESC',(sid,)) if sid else self.db.q('SELECT date,status,COUNT(*) FROM attendance GROUP BY date,status ORDER BY date DESC'); self.tree(f,[('date','Date',160),('status','Status',150),('time','Check in / Count',160),('remarks','Remarks',300)],rows,16)
    def reload_attendance_students(self,tv):
        for x in tv.get_children(): tv.delete(x)
        cid=int(self.attendance_class.get().split(' - ')[0]); rows=self.db.q('SELECT s.id,u.first_name||" "||u.last_name,c.class_name FROM students s JOIN users u ON u.id=s.user_id LEFT JOIN classes c ON c.id=s.class_id WHERE s.class_id=? ORDER BY u.last_name',(cid,)); [tv.insert('','end',values=(r['id'],r['name'],r['class_name'],'present')) for r in rows]
    def record_attendance(self,tv):
        if not self.attendance_class.get() or not parse_date(self.attendance_date.get()): return messagebox.showerror('Validation','Select a class and valid date.')
        cid=int(self.attendance_class.get().split(' - ')[0]); tid=self.db.scalar('SELECT id FROM teachers WHERE user_id=?',(self.user['id'],)); statuses=['present','absent','late','excused']; rows=[]
        for item in tv.get_children():
            vals=list(tv.item(item)['values']); status=vals[3] if vals[3] in statuses else 'present'; rows.append((int(vals[0]),cid,self.attendance_date.get(),status, '08:00' if status!='absent' else None,tid))
        self.db.executemany('INSERT INTO attendance(student_id,class_id,date,status,check_in_time,recorded_by) VALUES(?,?,?,?,?,?) ON CONFLICT(student_id,date) DO UPDATE SET status=excluded.status,class_id=excluded.class_id,check_in_time=excluded.check_in_time,recorded_by=excluded.recorded_by',rows); self.audit('Attendance recorded','attendance',None,f'{len(rows)} students'); messagebox.showinfo('Saved','Attendance recorded successfully.')
    def page_calendar(self):
        f=self.scroll(); self.page_title(f,'Calendar','Upcoming exams, deadlines, meetings and school events.'); rows=self.db.q('SELECT title,event_type,start_datetime,end_datetime,location FROM events WHERE start_datetime>=? ORDER BY start_datetime',(now(),)); self.tree(f,[('title','Event',260),('type','Type',150),('start','Start',180),('end','End',180),('location','Location',200)],rows,16)
    def page_timetable(self):
        f=self.scroll(); self.page_title(f,'Timetable','Weekly class schedule.'); rows=self.db.q('SELECT c.class_name,s.name,u.first_name||" "||u.last_name,t.day_of_week,t.start_time,t.end_time,t.room FROM timetable t JOIN classes c ON c.id=t.class_id JOIN subjects s ON s.id=t.subject_id JOIN teachers te ON te.id=t.teacher_id JOIN users u ON u.id=te.user_id ORDER BY CASE t.day_of_week WHEN "Monday" THEN 1 WHEN "Tuesday" THEN 2 WHEN "Wednesday" THEN 3 WHEN "Thursday" THEN 4 WHEN "Friday" THEN 5 ELSE 6 END,t.start_time'); self.tree(f,[('class','Class',140),('subject','Subject',190),('teacher','Teacher',180),('day','Day',110),('start','Start',90),('end','End',90),('room','Room',110)],rows,16); self.buttons(f,[('Add',self.timetable_form)]) if self.user['role']=='admin' else None
    def timetable_form(self):
        win=self.form_window('Add Timetable Entry',470,500); vals={}; data=[('Class','class',self.db.q('SELECT id,class_name FROM classes')),('Subject','subject',self.db.q('SELECT id,name FROM subjects')),('Teacher','teacher',self.db.q('SELECT t.id,u.first_name||" "||u.last_name name FROM teachers t JOIN users u ON u.id=t.user_id')),('Day','day',['Monday','Tuesday','Wednesday','Thursday','Friday'])]
        for lab,key,vs in data: tk.Label(win,text=lab,bg='white').pack(anchor='w',padx=25,pady=(12,3)); c=ttk.Combobox(win,values=[f"{r['id']} - {r[1] if isinstance(r,tuple) else r['class_name'] if key=='class' else r['name']}" for r in vs],state='readonly') if key!='day' else ttk.Combobox(win,values=vs,state='readonly'); c.pack(fill='x',padx=25); vals[key]=c
        for lab,key,default in [('Start','start','08:00'),('End','end','09:00'),('Room','room','Room 101')]: tk.Label(win,text=lab,bg='white').pack(anchor='w',padx=25,pady=(12,3)); e=tk.Entry(win); e.insert(0,default); e.pack(fill='x',padx=25,ipady=5); vals[key]=e
        def save():
            try: cid=int(vals['class'].get().split(' - ')[0]); sid=int(vals['subject'].get().split(' - ')[0]); tid=int(vals['teacher'].get().split(' - ')[0])
            except: return messagebox.showerror('Validation','Select class, subject and teacher.',parent=win)
            self.db.exec('INSERT INTO timetable(class_id,subject_id,teacher_id,day_of_week,start_time,end_time,room) VALUES(?,?,?,?,?,?,?)',(cid,sid,tid,vals['day'].get(),vals['start'].get(),vals['end'].get(),vals['room'].get())); win.destroy(); self.navigate('Timetable')
        ttk.Button(win,text='Save',style='Primary.TButton',command=save).pack(pady=18)
    def page_messages(self): self.messages_page()
    def messages_page(self):
        f=self.scroll(); self.page_title(f,'Messages','Internal school communication.'); rows=self.db.q('SELECT m.id,u.first_name||" "||u.last_name,m.subject,m.sent_at,m.is_read FROM messages m JOIN users u ON u.id=m.sender_id WHERE m.recipient_id=? ORDER BY m.id DESC',(self.user['id'],)); tv=self.tree(f,[('id','ID',60),('sender','From',220),('subject','Subject',320),('sent','Sent',180),('read','Read',90)],[(r['id'],r['sender'],r['subject'],r['sent_at'],'Yes' if r['is_read'] else 'No') for r in rows],14); self.buttons(f,[('Compose',self.message_form),('Open',lambda:self.open_message(tv))])
    def message_form(self):
        win=self.form_window('Compose Message',560,520); users=self.db.q('SELECT id,first_name||" "||last_name name,role FROM users WHERE id!=? AND is_active=1 ORDER BY name',(self.user['id'],)); tk.Label(win,text='Recipient',bg='white').pack(anchor='w',padx=25,pady=(18,3)); cb=ttk.Combobox(win,values=[f"{u['id']} - {u['name']} ({u['role']})" for u in users],state='readonly'); cb.pack(fill='x',padx=25); tk.Label(win,text='Subject',bg='white').pack(anchor='w',padx=25,pady=(14,3)); sub=tk.Entry(win); sub.pack(fill='x',padx=25,ipady=5); tk.Label(win,text='Message',bg='white').pack(anchor='w',padx=25,pady=(14,3)); body=tk.Text(win,height=10); body.pack(fill='both',expand=True,padx=25)
        def send():
            if not cb.get() or not sub.get().strip(): return messagebox.showerror('Validation','Recipient and subject are required.',parent=win)
            rid=int(cb.get().split(' - ')[0]); mid=self.db.exec('INSERT INTO messages(sender_id,recipient_id,subject,body) VALUES(?,?,?,?)',(self.user['id'],rid,sub.get().strip(),body.get('1.0','end').strip())); self.notify_user(rid,'New message',sub.get().strip(),'message'); self.audit('Message sent','messages',mid); win.destroy(); messagebox.showinfo('Sent','Message sent successfully.'); self.navigate('Messages')
        ttk.Button(win,text='Send',style='Primary.TButton',command=send).pack(pady=12)
    def open_message(self,tv):
        sel=tv.selection();
        if not sel:return
        mid=int(tv.item(sel[0])['values'][0]); m=self.db.q('SELECT m.*,u.first_name||" "||u.last_name sender FROM messages m JOIN users u ON u.id=m.sender_id WHERE m.id=? AND m.recipient_id=?',(mid,self.user['id']),True)
        if not m:return
        self.db.exec('UPDATE messages SET is_read=1,read_at=? WHERE id=?',(now(),mid)); win=self.form_window(m['subject'],700,500); tk.Label(win,text=f"From: {m['sender']}\nSent: {m['sent_at']}",bg='white',fg=COLORS['muted']).pack(anchor='w',padx=25,pady=20); tk.Label(win,text=m['body'],bg='white',fg=COLORS['text'],wraplength=630,justify='left',font=('Segoe UI',11)).pack(anchor='w',padx=25); ttk.Button(win,text='Close',command=lambda:(win.destroy(),self.navigate('Messages'))).pack(pady=25)
    def page_notifications(self):
        f=self.scroll(); self.page_title(f,'Notifications','System events and academic updates.'); rows=self.db.q('SELECT id,title,message,notification_type,created_at,is_read FROM notifications WHERE user_id=? ORDER BY id DESC',(self.user['id'],)); tv=self.tree(f,[('id','ID',60),('title','Title',240),('message','Message',400),('type','Type',130),('date','Date',180),('read','Read',80)],[(r['id'],r['title'],r['message'],r['notification_type'],r['created_at'],'Yes' if r['is_read'] else 'No') for r in rows],16); self.buttons(f,[('Mark all read',lambda:self.mark_notifications())])
    def mark_notifications(self): self.db.exec('UPDATE notifications SET is_read=1 WHERE user_id=?',(self.user['id'],)); self.navigate('Notifications')
    def notify_user(self,uid,title,message,typ='info'): self.db.exec('INSERT INTO notifications(user_id,title,message,notification_type) VALUES(?,?,?,?)',(uid,title,message,typ))
    def notify(self,student_id,title,message,typ='info'):
        uid=self.db.scalar('SELECT user_id FROM students WHERE id=?',(student_id,));
        if uid:self.notify_user(uid,title,message,typ)
    def check_achievements(self,sid):
        lessons=self.db.scalar('SELECT COUNT(*) FROM learning_progress WHERE student_id=? AND completed=1',(sid,)) or 0; assigns=self.db.scalar('SELECT COUNT(*) FROM assignment_submissions WHERE student_id=? AND status IN ("Submitted","Graded")',(sid,)) or 0; avg=self.db.scalar('SELECT AVG(percentage) FROM grades WHERE student_id=?',(sid,)) or 0
        conditions={'FIRST_LESSON':lessons>=1,'FIRST_ASSIGNMENT':assigns>=1,'PERFECT_QUIZ':bool(self.db.scalar('SELECT id FROM grades WHERE student_id=? AND assessment_type="quiz" AND percentage>=100',(sid,))), 'PERFECT_ATTENDANCE':(self.db.scalar("SELECT COUNT(*) FROM attendance WHERE student_id=? AND status='absent'",(sid,)) or 0)==0 and (self.db.scalar('SELECT COUNT(*) FROM attendance WHERE student_id=?',(sid,)) or 0)>5, 'COURSE_COMPLETION':bool(self.db.scalar('SELECT id FROM enrollments WHERE student_id=? AND completion_percentage>=100',(sid,))), 'STUDY_STREAK':self.study_streak(sid)>=7}
        for name,ok in conditions.items():
            if ok:
                aid=self.db.scalar('SELECT id FROM achievements WHERE requirement_type=?',(name,));
                if aid and not self.db.scalar('SELECT id FROM student_achievements WHERE student_id=? AND achievement_id=?',(sid,aid)): self.db.exec('INSERT INTO student_achievements(student_id,achievement_id) VALUES(?,?)',(sid,aid)); self.notify(sid,'Achievement unlocked',name.replace('_',' ').title(),'achievement')
    def study_streak(self,sid):
        dates=set()
        for r in self.db.q('SELECT substr(start_time,1,10) d FROM study_sessions WHERE student_id=? AND start_time IS NOT NULL',(sid,)): dates.add(r['d'])
        for r in self.db.q('SELECT substr(completed_at,1,10) d FROM learning_progress WHERE student_id=? AND completed=1',(sid,)): dates.add(r['d'])
        cur=dt.date.today(); n=0
        while cur.isoformat() in dates: n+=1; cur-=dt.timedelta(days=1)
        return n
    def page_achievements(self):
        f=self.scroll(); self.page_title(f,'Achievements','Earn XP through consistent academic activity.'); sid=self.current_student()['id']; earned=self.db.q('SELECT a.name,a.description,a.points,sa.earned_at FROM student_achievements sa JOIN achievements a ON a.id=sa.achievement_id WHERE sa.student_id=? ORDER BY sa.earned_at DESC',(sid,)); self.tree(f,[('name','Achievement',230),('description','Description',400),('points','XP',80),('date','Earned',180)],earned,14); xp=sum(r['points'] for r in earned); tk.Label(f,text=f'XP: {xp}   Level: {"Academic Champion" if xp>=250 else "Achiever" if xp>=150 else "Scholar" if xp>=80 else "Learner" if xp>=30 else "Beginner"}',font=('Segoe UI',15,'bold'),bg=COLORS['bg'],fg=COLORS['text']).pack(anchor='w',padx=28,pady=15)
    def page_certificates(self):
        f=self.scroll(); self.page_title(f,'Certificates','Certificates issued for completed courses.'); sid=self.current_student()['id']; rows=self.db.q('SELECT c.certificate_number,co.title,c.issued_at,c.final_score FROM certificates c JOIN courses co ON co.id=c.course_id WHERE c.student_id=? ORDER BY c.id DESC',(sid,)); self.tree(f,[('number','Certificate',220),('course','Course',300),('date','Issued',180),('score','Final Score',130)],rows,14); self.buttons(f,[('Generate Certificate',self.generate_certificate)])
    def generate_certificate(self):
        sid=self.current_student()['id']; rows=self.db.q('SELECT e.course_id,co.title,e.completion_percentage FROM enrollments e JOIN courses co ON co.id=e.course_id WHERE e.student_id=? AND e.completion_percentage>=100',(sid,));
        if not rows:return messagebox.showinfo('Not eligible','Complete a course to generate a certificate.')
        course=rows[0]; score=self.db.scalar('SELECT AVG(percentage) FROM grades g JOIN subjects s ON s.id=g.subject_id WHERE g.student_id=? AND s.id=(SELECT subject_id FROM courses WHERE id=?)',(sid,course['course_id'])) or 0; number='SH-'+dt.datetime.now().strftime('%Y%m%d')+'-'+secrets.token_hex(3).upper(); self.db.exec('INSERT INTO certificates(student_id,course_id,certificate_number,issued_at,final_score) VALUES(?,?,?,?,?)',(sid,course['course_id'],number,today(),score)); self.navigate('Certificates'); messagebox.showinfo('Certificate generated',f'Certificate number: {number}\nA printable certificate record has been created.')
    def page_study_tracker(self):
        f=self.scroll(); self.page_title(f,'Study Tracker','Track focused study sessions and learning streaks.'); sid=self.current_student()['id']; row=tk.Frame(f,bg=COLORS['bg']); row.pack(fill='x',padx=20); today_m=self.db.scalar("SELECT COALESCE(SUM(duration_minutes),0) FROM study_sessions WHERE student_id=? AND substr(start_time,1,10)=?",(sid,today())) or 0; week=self.db.scalar("SELECT COALESCE(SUM(duration_minutes),0) FROM study_sessions WHERE student_id=? AND start_time>=?",(sid,(dt.datetime.now()-dt.timedelta(days=7)).isoformat())) or 0; [self.card(row,*x,column=i) for i,x in enumerate([('Today',f'{today_m} min','Focused time'),('This week',f'{week} min','Last 7 days'),('Streak',f'{self.study_streak(sid)} days','Consecutive learning')])]; self.buttons(f,[('Start Study Session',self.study_session_form)]); rows=self.db.q('SELECT s.name,ss.start_time,ss.end_time,ss.duration_minutes,ss.notes FROM study_sessions ss JOIN subjects s ON s.id=ss.subject_id WHERE ss.student_id=? ORDER BY ss.id DESC LIMIT 20',(sid,)); self.tree(f,[('subject','Subject',220),('start','Start',180),('end','End',180),('duration','Minutes',100),('notes','Notes',320)],rows,14)
    def study_session_form(self):
        win=self.form_window('Study Session',460,360); subs=self.db.q('SELECT id,name FROM subjects ORDER BY name'); tk.Label(win,text='Subject',bg='white').pack(anchor='w',padx=25,pady=(20,3)); cb=ttk.Combobox(win,values=[f"{r['id']} - {r['name']}" for r in subs],state='readonly'); cb.pack(fill='x',padx=25); tk.Label(win,text='Duration minutes',bg='white').pack(anchor='w',padx=25,pady=(14,3)); dur=tk.Entry(win); dur.insert(0,'45'); dur.pack(fill='x',padx=25,ipady=5); tk.Label(win,text='Notes',bg='white').pack(anchor='w',padx=25,pady=(14,3)); notes=tk.Entry(win); notes.pack(fill='x',padx=25,ipady=5)
        def save():
            if not cb.get(): return messagebox.showerror('Validation','Select a subject.',parent=win)
            try: minutes=int(dur.get()); assert minutes>0
            except: return messagebox.showerror('Validation','Duration must be a positive integer.',parent=win)
            end=dt.datetime.now(); start=end-dt.timedelta(minutes=minutes); self.db.exec('INSERT INTO study_sessions(student_id,subject_id,start_time,end_time,duration_minutes,notes) VALUES(?,?,?,?,?,?)',(self.current_student()['id'],int(cb.get().split(' - ')[0]),start.isoformat(sep=' '),end.isoformat(sep=' '),minutes,notes.get())); self.check_achievements(self.current_student()['id']); win.destroy(); self.navigate('Study Tracker')
        ttk.Button(win,text='Save Session',style='Primary.TButton',command=save).pack(pady=20)
    def page_profile(self):
        f=self.scroll(); self.page_title(f,'Profile','Manage your personal information.'); box=tk.Frame(f,bg='white'); box.pack(fill='x',padx=26,pady=10); entries={};
        for lab,key,val in [('First name','first_name',self.user['first_name']),('Last name','last_name',self.user['last_name']),('Email','email',self.user['email']),('Phone','phone',self.user.get('phone') or '')]: tk.Label(box,text=lab,bg='white').pack(anchor='w',padx=25,pady=(16,3)); e=tk.Entry(box); e.insert(0,val); e.pack(fill='x',padx=25,ipady=6); entries[key]=e
        tk.Label(box,text=f"Role: {self.user['role'].title()}   |   Account created: {fmt_date(self.user['created_at'])}\nLast login: {fmt_date(self.user['last_login'])}",bg='white',fg=COLORS['muted'],justify='left').pack(anchor='w',padx=25,pady=18); ttk.Button(box,text='Save Profile',style='Primary.TButton',command=lambda:self.save_profile(entries)).pack(anchor='w',padx=25,pady=(0,20))
    def save_profile(self,e):
        email=e['email'].get().strip();
        if not valid_email(email):return messagebox.showerror('Validation','Enter a valid email.')
        try:self.db.exec('UPDATE users SET first_name=?,last_name=?,email=?,phone=? WHERE id=?',(e['first_name'].get().strip(),e['last_name'].get().strip(),email,e['phone'].get().strip(),self.user['id'])); self.user.update({'first_name':e['first_name'].get().strip(),'last_name':e['last_name'].get().strip(),'email':email,'phone':e['phone'].get().strip()}); self.refresh_top(); messagebox.showinfo('Saved','Profile updated successfully.')
        except sqlite3.IntegrityError: messagebox.showerror('Error','That email is already in use.')
    def page_settings(self): self.settings_page()
    def page_system_settings(self): self.settings_page(admin=True)
    def settings_page(self,admin=False):
        f=self.scroll(); self.page_title(f,'System Settings' if admin else 'Settings','Account, school configuration and security.'); box=tk.Frame(f,bg='white'); box.pack(fill='x',padx=26,pady=10); tk.Label(box,text='Change password',font=('Segoe UI',14,'bold'),bg='white').pack(anchor='w',padx=25,pady=18); old=tk.Entry(box,show='*'); new=tk.Entry(box,show='*'); conf=tk.Entry(box,show='*');
        for lab,e in [('Current password',old),('New password',new),('Confirm password',conf)]: tk.Label(box,text=lab,bg='white').pack(anchor='w',padx=25,pady=(6,3)); e.pack(fill='x',padx=25,ipady=6)
        ttk.Button(box,text='Change Password',style='Primary.TButton',command=lambda:self.change_password(old,new,conf)).pack(anchor='w',padx=25,pady=16)
        if admin and self.user['role']=='admin':
            tk.Label(box,text='School configuration',font=('Segoe UI',14,'bold'),bg='white').pack(anchor='w',padx=25,pady=(22,12)); fields={}
            for key,label in [('school_name','School name'),('school_address','Address'),('school_phone','Phone'),('school_email','Email')]: tk.Label(box,text=label,bg='white').pack(anchor='w',padx=25,pady=(7,2)); e=tk.Entry(box); e.insert(0,self.db.setting(key)); e.pack(fill='x',padx=25,ipady=6); fields[key]=e
            ttk.Button(box,text='Save School Settings',style='Primary.TButton',command=lambda:self.save_settings(fields)).pack(anchor='w',padx=25,pady=18)
            tk.Label(box,text=f'Database: {DB_FILE}\nSQLite foreign keys: enabled\nVersion: {VERSION}',bg='white',fg=COLORS['muted'],justify='left').pack(anchor='w',padx=25,pady=15)
    def change_password(self,old,new,conf):
        u=self.db.q('SELECT password_hash FROM users WHERE id=?',(self.user['id'],),True)
        if not verify_password(old.get(),u['password_hash']):return messagebox.showerror('Error','Current password is incorrect.')
        if len(new.get())<8 or new.get()!=conf.get():return messagebox.showerror('Error','New passwords must match and contain at least 8 characters.')
        self.db.exec('UPDATE users SET password_hash=? WHERE id=?',(hash_password(new.get()),self.user['id'])); messagebox.showinfo('Updated','Password changed successfully.')
    def save_settings(self,fields):
        for k,e in fields.items(): self.db.set_setting(k,e.get().strip()); messagebox.showinfo('Saved','School settings saved successfully.')
    def page_analytics(self): self.analytics_page()
    def analytics_page(self):
        f=self.scroll(); self.page_title(f,'Analytics','Calculated educational performance indicators.'); avg=self.db.scalar('SELECT AVG(percentage) FROM grades') or 0; att=self.db.scalar("SELECT AVG(CASE WHEN status IN ('present','late') THEN 100.0 ELSE 0 END) FROM attendance") or 0; completion=self.db.scalar('SELECT AVG(completion_percentage) FROM enrollments') or 0; row=tk.Frame(f,bg=COLORS['bg']); row.pack(fill='x',padx=20); [self.card(row,*x,column=i) for i,x in enumerate([('School average',f'{avg:.1f}%','All recorded grades'),('Attendance',f'{att:.1f}%','Present or late'),('Course completion',f'{completion:.1f}%','Enrollment progress')])]; self.section_table(f,'Performance by Subject',self.db.q('SELECT s.name,ROUND(AVG(g.percentage),1),MIN(g.percentage),MAX(g.percentage),COUNT(g.id) FROM subjects s LEFT JOIN grades g ON g.subject_id=s.id GROUP BY s.id'),[('subject','Subject',240),('avg','Average',120),('min','Lowest',120),('max','Highest',120),('count','Records',100)]); self.section_table(f,'Risk Overview',self.risk_rows(),[('student','Student',260),('average','Average',110),('attendance','Attendance',120),('completion','Completion',120),('exam','Exam',100),('risk','Risk',130)])
    def risk_rows(self):
        out=[]
        for s in self.db.q('SELECT s.id,u.first_name||" "||u.last_name name FROM students s JOIN users u ON u.id=s.user_id'):
            avg,att,_,comp,_=self.stat_data(s['id']); exam=self.db.scalar('SELECT AVG(percentage) FROM grades WHERE student_id=? AND assessment_type="exam"',(s['id'],)) or avg; out.append((s['name'],round(avg,1),round(att,1),round(comp,1),round(exam,1),risk_level(avg,att,comp,exam)))
        return out
    def page_reports(self): self.reports_page()
    def reports_page(self):
        f=self.scroll(); self.page_title(f,'Reports','Export student, grade and attendance data to CSV.'); self.buttons(f,[('Export Students',lambda:self.export_csv('students')),('Export Grades',lambda:self.export_csv('grades')),('Export Attendance',lambda:self.export_csv('attendance')),('Export Assignments',lambda:self.export_csv('assignments'))]); self.section_table(f,'Report Center',[(x[0],x[1]) for x in [('Student academic report','Student information, grades, averages, GPA and attendance'),('Class report','Roster, averages, attendance and ranking'),('School report','Enrollment, attendance and academic performance')]], [('report','Report',250),('description','Contents',600)])
    def export_csv(self,kind):
        queries={'students':('SELECT s.student_number,u.first_name,u.last_name,c.class_name,s.academic_status FROM students s JOIN users u ON u.id=s.user_id LEFT JOIN classes c ON c.id=s.class_id',['Student Number','First Name','Last Name','Class','Status']),'grades':('SELECT u.first_name||" "||u.last_name,s.name,g.assessment_type,g.score,g.max_score,g.percentage,g.term FROM grades g JOIN students st ON st.id=g.student_id JOIN users u ON u.id=st.user_id JOIN subjects s ON s.id=g.subject_id',['Student','Subject','Assessment','Score','Max','Percentage','Term']),'attendance':('SELECT u.first_name||" "||u.last_name,a.date,a.status,a.check_in_time,a.remarks FROM attendance a JOIN students s ON s.id=a.student_id JOIN users u ON u.id=s.user_id',['Student','Date','Status','Check In','Remarks']),'assignments':('SELECT a.title,c.title,a.due_date,s.status,s.score,a.max_score FROM assignments a JOIN courses c ON c.id=a.course_id LEFT JOIN assignment_submissions s ON s.assignment_id=a.id',['Assignment','Course','Due Date','Status','Score','Max'])}; sql,heads=queries[kind]; rows=self.db.q(sql); path=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV','*.csv')],initialfile=f'schoolhub_{kind}.csv');
        if not path:return
        with open(path,'w',newline='',encoding='utf-8-sig') as fh: w=csv.writer(fh); w.writerow(heads); w.writerows([tuple(r) for r in rows]); messagebox.showinfo('Export complete',f'CSV exported to:\n{path}')
    def page_audit_logs(self):
        f=self.scroll(); self.page_title(f,'Audit Logs','Trace important actions across the system.'); rows=self.db.q('SELECT u.first_name||" "||u.last_name,l.action,l.entity_type,l.entity_id,l.timestamp,l.details FROM audit_logs l LEFT JOIN users u ON u.id=l.user_id ORDER BY l.id DESC'); self.tree(f,[('user','User',210),('action','Action',220),('entity','Entity',150),('id','ID',70),('time','Timestamp',180),('details','Details',350)],rows,18)
    def page_users(self): self.admin_users()
    def admin_users(self):
        f=self.scroll(); self.page_title(f,'User Management','Create, activate and manage accounts.'); rows=self.db.q('SELECT id,username,email,role,first_name||" "||last_name,status,last_login FROM users ORDER BY id'); tv=self.tree(f,[('id','ID',60),('username','Username',150),('email','Email',250),('role','Role',100),('name','Name',200),('status','Status',100),('login','Last Login',180)],rows,15); self.buttons(f,[('Add',self.user_form),('Toggle Active',lambda:self.toggle_user(tv)),('Reset Password',lambda:self.reset_password(tv))])
    def user_form(self):
        win=self.form_window('Create User',460,570); ent={}
        for lab,key in [('First name','first'),('Last name','last'),('Username','username'),('Email','email'),('Phone','phone'),('Password','password')]: tk.Label(win,text=lab,bg='white').pack(anchor='w',padx=25,pady=(10,2)); e=tk.Entry(win,show='*' if key=='password' else ''); e.pack(fill='x',padx=25,ipady=5); ent[key]=e
        tk.Label(win,text='Role',bg='white').pack(anchor='w',padx=25,pady=(10,2)); role=ttk.Combobox(win,values=ROLES,state='readonly'); role.set('student'); role.pack(fill='x',padx=25)
        def save():
            vals=[ent[k].get().strip() for k in ('first','last','username','email','password')];
            if not all(vals) or not valid_email(vals[3]) or len(vals[4])<8:return messagebox.showerror('Validation','All fields are required; use a valid email and password of 8+ characters.',parent=win)
            try: uid=self.db.exec('INSERT INTO users(username,email,password_hash,role,first_name,last_name,phone) VALUES(?,?,?,?,?,?,?)',(vals[2],vals[3],hash_password(vals[4]),role.get(),vals[0],vals[1],ent['phone'].get().strip()));
            except sqlite3.IntegrityError:return messagebox.showerror('Duplicate','Username or email already exists.',parent=win)
            if role.get()=='student': self.db.exec('INSERT INTO students(user_id,student_number,enrollment_date) VALUES(?,?,?)',(uid,'STU-'+str(uid),today()))
            elif role.get()=='teacher': self.db.exec('INSERT INTO teachers(user_id,employee_number) VALUES(?,?)',(uid,'T-'+str(uid)))
            elif role.get()=='parent': self.db.exec('INSERT INTO parents(user_id) VALUES(?)',(uid,))
            self.audit('User created','users',uid,vals[3]); win.destroy(); self.navigate('Users')
        ttk.Button(win,text='Create',style='Primary.TButton',command=save).pack(pady=18)
    def toggle_user(self,tv):
        sel=tv.selection();
        if not sel:return
        uid=int(tv.item(sel[0])['values'][0]); u=self.db.q('SELECT role,is_active FROM users WHERE id=?',(uid,),True)
        if u['role']=='admin' and u['is_active'] and self.db.scalar('SELECT COUNT(*) FROM users WHERE role="admin" AND is_active=1')<=1:return messagebox.showerror('Protected','The last active administrator cannot be deactivated.')
        self.db.exec('UPDATE users SET is_active=? ,status=? WHERE id=?',(0 if u['is_active'] else 1,'inactive' if u['is_active'] else 'active',uid)); self.audit('User status changed','users',uid); self.navigate('Users')
    def reset_password(self,tv):
        sel=tv.selection();
        if not sel:return
        uid=int(tv.item(sel[0])['values'][0]); new='Reset-'+secrets.token_hex(4); self.db.exec('UPDATE users SET password_hash=? WHERE id=?',(hash_password(new),uid)); messagebox.showinfo('Password reset',f'Temporary password:\n{new}')
    def page_students(self): self.entity_people('students')
    def page_teachers(self): self.entity_people('teachers')
    def page_parents(self): self.entity_people('parents')
    def entity_people(self,kind):
        f=self.scroll(); self.page_title(f,kind.title(),'Manage school community records.');
        if kind=='students': rows=self.db.q('SELECT s.id,s.student_number,u.first_name||" "||u.last_name,c.class_name,u.email,s.academic_status FROM students s JOIN users u ON u.id=s.user_id LEFT JOIN classes c ON c.id=s.class_id ORDER BY u.last_name'); cols=[('id','ID',60),('number','Student No.',120),('name','Name',240),('class','Class',130),('email','Email',250),('status','Status',130)]
        elif kind=='teachers': rows=self.db.q('SELECT t.id,t.employee_number,u.first_name||" "||u.last_name,t.specialization,t.department,u.email,u.status FROM teachers t JOIN users u ON u.id=t.user_id ORDER BY u.last_name'); cols=[('id','ID',60),('number','Employee No.',120),('name','Name',240),('specialization','Specialization',190),('department','Department',150),('email','Email',250),('status','Status',100)]
        else: rows=self.db.q('SELECT p.id,u.first_name||" "||u.last_name,u.email,p.occupation,COUNT(ps.student_id) FROM parents p JOIN users u ON u.id=p.user_id LEFT JOIN parent_students ps ON ps.parent_id=p.id GROUP BY p.id ORDER BY u.last_name'); cols=[('id','ID',60),('name','Name',250),('email','Email',260),('occupation','Occupation',200),('children','Children',100)]
        self.tree(f,cols,rows,16); self.buttons(f,[('Add',lambda:self.user_form_for(kind)),('Refresh',lambda:self.navigate(kind.title()))])
    def user_form_for(self,kind): self.user_form()
    def page_classes(self): self.simple_crud('Classes','SELECT c.id,c.class_name,c.grade_level,c.section,ay.name,c.room,u.first_name||" "||u.last_name FROM classes c LEFT JOIN academic_years ay ON ay.id=c.academic_year_id LEFT JOIN teachers t ON t.id=c.class_teacher_id LEFT JOIN users u ON u.id=t.user_id ORDER BY c.id',[('id','ID',60),('name','Class',180),('grade','Grade',130),('section','Section',100),('year','Academic Year',150),('room','Room',120),('teacher','Class Teacher',220)],self.class_form)
    def page_subjects(self): self.simple_crud('Subjects','SELECT id,name,code,department,credits,description FROM subjects ORDER BY name',[('id','ID',60),('name','Name',220),('code','Code',120),('department','Department',180),('credits','Credits',90),('description','Description',350)],self.subject_form)
    def page_courses(self): self.courses_page()
    def simple_crud(self,title,sql,cols,form):
        f=self.scroll(); self.page_title(f,title,'Persistent records stored in SQLite.'); tv=self.tree(f,cols,self.db.q(sql),16); self.buttons(f,[('Add',form),('Refresh',lambda:self.navigate(title))])
    def class_form(self):
        win=self.form_window('Create Class',450,420); vals={}; teachers=self.db.q('SELECT t.id,u.first_name||" "||u.last_name name FROM teachers t JOIN users u ON u.id=t.user_id');
        for lab,key,default in [('Class name','name','Form 1B'),('Grade level','grade','Form 1'),('Section','section','B'),('Room','room','Room 102')]: tk.Label(win,text=lab,bg='white').pack(anchor='w',padx=25,pady=(12,2)); e=tk.Entry(win); e.insert(0,default); e.pack(fill='x',padx=25,ipady=5); vals[key]=e
        tk.Label(win,text='Class teacher',bg='white').pack(anchor='w',padx=25,pady=(12,2)); cb=ttk.Combobox(win,values=[f"{t['id']} - {t['name']}" for t in teachers],state='readonly'); cb.pack(fill='x',padx=25)
        def save():
            tid=int(cb.get().split(' - ')[0]) if cb.get() else None; self.db.exec('INSERT INTO classes(class_name,grade_level,section,academic_year_id,room,class_teacher_id) VALUES(?,?,?,?,?,?)',(vals['name'].get(),vals['grade'].get(),vals['section'].get(),self.db.scalar('SELECT id FROM academic_years WHERE is_current=1'),vals['room'].get(),tid)); win.destroy(); self.navigate('Classes')
        ttk.Button(win,text='Save',style='Primary.TButton',command=save).pack(pady=18)
    def subject_form(self):
        win=self.form_window('Create Subject',460,440); ent={}
        for lab,key in [('Name','name'),('Code','code'),('Department','department'),('Credits','credits'),('Description','description')]: tk.Label(win,text=lab,bg='white').pack(anchor='w',padx=25,pady=(12,2)); e=tk.Entry(win); e.pack(fill='x',padx=25,ipady=5); ent[key]=e
        def save():
            if not ent['name'].get() or not ent['code'].get():return messagebox.showerror('Validation','Name and code are required.',parent=win)
            try:self.db.exec('INSERT INTO subjects(name,code,department,credits,description) VALUES(?,?,?,?,?)',(ent['name'].get(),ent['code'].get(),ent['department'].get(),float(ent['credits'].get() or 1),ent['description'].get()))
            except sqlite3.IntegrityError:return messagebox.showerror('Duplicate','Subject code already exists.',parent=win)
            win.destroy(); self.navigate('Subjects')
        ttk.Button(win,text='Save',style='Primary.TButton',command=save).pack(pady=18)
    def course_form(self):
        win=self.form_window('Create Course',500,520); subs=self.db.q('SELECT id,name FROM subjects'); teachers=self.db.q('SELECT t.id,u.first_name||" "||u.last_name name FROM teachers t JOIN users u ON u.id=t.user_id'); fields={}
        for lab,key,vals in [('Title','title',None),('Subject','subject',subs),('Teacher','teacher',teachers),('Difficulty','difficulty',['Beginner','Intermediate','Advanced']),('Duration (minutes)','duration',None)]: tk.Label(win,text=lab,bg='white').pack(anchor='w',padx=25,pady=(12,2)); x=ttk.Combobox(win,values=([f"{r['id']} - {r['name']}" for r in vals] if isinstance(vals,list) and vals and isinstance(vals[0],sqlite3.Row) else vals),state='readonly' if vals else 'normal'); x.pack(fill='x',padx=25,ipady=4); fields[key]=x
        def save():
            try:sid=int(fields['subject'].get().split(' - ')[0]); tid=int(fields['teacher'].get().split(' - ')[0]); dur=int(fields['duration'].get() or 0)
            except:return messagebox.showerror('Validation','Select subject/teacher and enter a duration.',parent=win)
            cid=self.db.exec('INSERT INTO courses(subject_id,teacher_id,title,description,difficulty,duration) VALUES(?,?,?,?,?,?)',(sid,tid,fields['title'].get().strip(),'Created from SchoolHub LMS.',fields['difficulty'].get() or 'Beginner',dur)); mid=self.db.exec('INSERT INTO course_modules(course_id,title,description,position) VALUES(?,?,?,1)',(cid,'Module 1','First learning module')); self.db.exec('INSERT INTO lessons(module_id,title,content,position,estimated_minutes) VALUES(?,?,?,?,?)',(mid,'Introduction','Add your lesson content here.',1,20)); win.destroy(); self.navigate('Courses')
        ttk.Button(win,text='Create',style='Primary.TButton',command=save).pack(pady=18)
    def page_my_classes(self):
        f=self.scroll(); self.page_title(f,'My Classes','Classes and students assigned to you.'); tid=self.db.scalar('SELECT id FROM teachers WHERE user_id=?',(self.user['id'],)); rows=self.db.q('SELECT c.id,c.class_name,c.grade_level,c.room,COUNT(s.id) FROM classes c JOIN teacher_subjects ts ON ts.class_id=c.id LEFT JOIN students s ON s.class_id=c.id WHERE ts.teacher_id=? GROUP BY c.id',(tid,)); self.tree(f,[('id','ID',60),('class','Class',200),('grade','Grade',140),('room','Room',120),('students','Students',100)],rows,14)
    def page_my_children(self): self.dashboard_parent(self.scroll())
    def page_announcements(self): self.announcements_page()
    def announcements_page(self):
        f=self.scroll(); self.page_title(f,'Announcements','Publish targeted school communications.'); rows=self.db.q('SELECT a.id,a.title,a.target_role,a.priority,a.created_at,u.first_name||" "||u.last_name FROM announcements a JOIN users u ON u.id=a.author_id ORDER BY a.id DESC'); tv=self.tree(f,[('id','ID',60),('title','Title',280),('target','Target',130),('priority','Priority',110),('date','Created',180),('author','Author',200)],rows,15); self.buttons(f,[('Create',self.announcement_form)])
    def announcement_form(self):
        win=self.form_window('New Announcement',570,500); tk.Label(win,text='Title',bg='white').pack(anchor='w',padx=25,pady=(20,3)); title=tk.Entry(win); title.pack(fill='x',padx=25,ipady=5); tk.Label(win,text='Target role',bg='white').pack(anchor='w',padx=25,pady=(14,3)); target=ttk.Combobox(win,values=['everyone','student','teacher','parent'],state='readonly'); target.set('everyone'); target.pack(fill='x',padx=25); tk.Label(win,text='Priority',bg='white').pack(anchor='w',padx=25,pady=(14,3)); pri=ttk.Combobox(win,values=['Normal','High','Urgent'],state='readonly'); pri.set('Normal'); pri.pack(fill='x',padx=25); tk.Label(win,text='Content',bg='white').pack(anchor='w',padx=25,pady=(14,3)); body=tk.Text(win,height=10); body.pack(fill='both',expand=True,padx=25)
        def save():
            aid=self.db.exec('INSERT INTO announcements(title,content,author_id,target_role,priority) VALUES(?,?,?,?,?)',(title.get().strip(),body.get('1.0','end').strip(),self.user['id'],target.get(),pri.get())); role=target.get(); users=self.db.q('SELECT id FROM users WHERE is_active=1'+('' if role=='everyone' else ' AND role=?'),() if role=='everyone' else (role,)); [self.notify_user(u['id'],title.get().strip(),body.get('1.0','end').strip(),'announcement') for u in users]; self.audit('Announcement published','announcements',aid); win.destroy(); self.navigate('Announcements')
        ttk.Button(win,text='Publish',style='Primary.TButton',command=save).pack(pady=14)
    def page_students_dummy(self): pass
    def gradebook_page(self, student=False):
        return self.gradebook_page_original(student)

    def teacher_students_page(self):
        f=self.scroll(); self.page_title(f,'Students','Students belonging to your assigned classes.')
        tid=self.db.scalar('SELECT id FROM teachers WHERE user_id=?',(self.user['id'],))
        rows=self.db.q('SELECT DISTINCT s.id,s.student_number,u.first_name||" "||u.last_name,c.class_name,u.email,s.academic_status FROM students s JOIN users u ON u.id=s.user_id LEFT JOIN classes c ON c.id=s.class_id JOIN teacher_subjects ts ON ts.class_id=s.class_id WHERE ts.teacher_id=? ORDER BY u.last_name,u.first_name',(tid,))
        self.tree(f,[('id','ID',60),('number','Student No.',120),('name','Name',250),('class','Class',150),('email','Email',260),('status','Status',130)],rows,16)

    def page_my_children(self):
        f=self.scroll(); self.page_title(f,'My Children','Academic monitoring for children linked to your parent account.')
        pid=self.db.scalar('SELECT id FROM parents WHERE user_id=?',(self.user['id'],))
        rows=self.db.q('SELECT s.id,u.first_name||" "||u.last_name,c.class_name,COUNT(g.id),ROUND(COALESCE(AVG(g.percentage),0),1) FROM parent_students ps JOIN students s ON s.id=ps.student_id JOIN users u ON u.id=s.user_id LEFT JOIN classes c ON c.id=s.class_id LEFT JOIN grades g ON g.student_id=s.id WHERE ps.parent_id=? GROUP BY s.id',(pid,))
        self.tree(f,[('id','Student ID',100),('name','Child',260),('class','Class',160),('grades','Grade Records',130),('average','Average',120)],rows,12)

    def parent_grades_page(self):
        f=self.scroll(); self.page_title(f,'Grades','Grades for your linked children only.')
        pid=self.db.scalar('SELECT id FROM parents WHERE user_id=?',(self.user['id'],))
        rows=self.db.q('SELECT u.first_name||" "||u.last_name,su.name,g.assessment_type,g.score,g.max_score,g.percentage,g.term FROM grades g JOIN students st ON st.id=g.student_id JOIN users u ON u.id=st.user_id JOIN parent_students ps ON ps.student_id=st.id JOIN subjects su ON su.id=g.subject_id WHERE ps.parent_id=? ORDER BY g.id DESC',(pid,))
        self.tree(f,[('student','Student',220),('subject','Subject',190),('type','Assessment',130),('score','Score',90),('max','Max',80),('percentage','%',90),('term','Term',120)],rows,16)

    def parent_assignments_page(self):
        f=self.scroll(); self.page_title(f,'Assignments','Assignments for your linked children.')
        pid=self.db.scalar('SELECT id FROM parents WHERE user_id=?',(self.user['id'],))
        rows=self.db.q('SELECT u.first_name||" "||u.last_name,a.title,c.title,a.due_date,COALESCE(sub.status,"Pending"),COALESCE(sub.score,"-") FROM parent_students ps JOIN students st ON st.id=ps.student_id JOIN users u ON u.id=st.user_id JOIN enrollments en ON en.student_id=st.id JOIN courses c ON c.id=en.course_id JOIN assignments a ON a.course_id=c.id LEFT JOIN assignment_submissions sub ON sub.assignment_id=a.id AND sub.student_id=st.id WHERE ps.parent_id=? ORDER BY a.due_date',(pid,))
        self.tree(f,[('student','Student',210),('assignment','Assignment',220),('course','Course',220),('due','Due',120),('status','Status',120),('score','Score',90)],rows,16)

    def parent_exams_page(self):
        f=self.scroll(); self.page_title(f,'Exams','Exam schedule and results for your linked children.')
        pid=self.db.scalar('SELECT id FROM parents WHERE user_id=?',(self.user['id'],))
        rows=self.db.q('SELECT u.first_name||" "||u.last_name,e.title,c.title,e.exam_date,e.duration_minutes,COALESCE(a.status,"Not Started"),COALESCE(a.percentage,"-") FROM parent_students ps JOIN students st ON st.id=ps.student_id JOIN users u ON u.id=st.user_id JOIN enrollments en ON en.student_id=st.id JOIN courses c ON c.id=en.course_id JOIN exams e ON e.course_id=c.id LEFT JOIN exam_attempts a ON a.exam_id=e.id AND a.student_id=st.id WHERE ps.parent_id=? ORDER BY e.exam_date',(pid,))
        self.tree(f,[('student','Student',210),('exam','Exam',230),('course','Course',210),('date','Date',120),('duration','Minutes',100),('status','Status',120),('result','Result',90)],rows,16)

    def parent_reports_page(self):
        f=self.scroll(); self.page_title(f,'Reports','Parent academic reports for linked children.')
        pid=self.db.scalar('SELECT id FROM parents WHERE user_id=?',(self.user['id'],))
        rows=self.db.q('SELECT u.first_name||" "||u.last_name,c.class_name,ROUND(COALESCE(AVG(g.percentage),0),1),ROUND(COALESCE(AVG(CASE WHEN a.status IN ("present","late") THEN 100.0 ELSE 0 END),0),1) FROM parent_students ps JOIN students s ON s.id=ps.student_id JOIN users u ON u.id=s.user_id LEFT JOIN classes c ON c.id=s.class_id LEFT JOIN grades g ON g.student_id=s.id LEFT JOIN attendance a ON a.student_id=s.id WHERE ps.parent_id=? GROUP BY s.id',(pid,))
        self.tree(f,[('student','Student',240),('class','Class',160),('average','Average',120),('attendance','Attendance',130)],rows,12)
        self.buttons(f,[('Export Grades',lambda:self.export_csv('grades')),('Export Attendance',lambda:self.export_csv('attendance'))])

    def reports_page(self):
        if self.user['role']=='parent': return self.parent_reports_page()
        return self.reports_page_admin()

    def reports_page_admin(self):
        f=self.scroll(); self.page_title(f,'Reports','Export student, grade and attendance data to CSV.'); self.buttons(f,[('Export Students',lambda:self.export_csv('students')),('Export Grades',lambda:self.export_csv('grades')),('Export Attendance',lambda:self.export_csv('attendance')),('Export Assignments',lambda:self.export_csv('assignments'))]); self.section_table(f,'Report Center',[(x[0],x[1]) for x in [('Student academic report','Student information, grades, averages, GPA and attendance'),('Class report','Roster, averages, attendance and ranking'),('School report','Enrollment, attendance and academic performance')]], [('report','Report',250),('description','Contents',600)])

    def form_window(self,title,w,h):
        win=tk.Toplevel(self); win.title(title); win.geometry(f'{w}x{h}'); win.configure(bg='white'); win.transient(self); win.grab_set(); return win
    def page_my_courses_dummy(self): pass
    def page_my_children_dummy(self): pass
    def page_system_settings_dummy(self): pass
    def page_users_dummy(self): pass
    def page_reports_dummy(self): pass
    def page_profile_dummy(self): pass
    def page_settings_dummy(self): pass
    def page_messages_dummy(self): pass
    def page_calendar_dummy(self): pass
    def page_notifications_dummy(self): pass
    def page_achievements_dummy(self): pass
    def page_certificates_dummy(self): pass
    def page_study_tracker_dummy(self): pass
    def page_analytics_dummy(self): pass
    def on_close(self):
        try:self.db.conn.close()
        finally:self.destroy()

if __name__=='__main__':
    SchoolHub().mainloop()
