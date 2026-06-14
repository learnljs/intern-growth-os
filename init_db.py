import sqlite3
import os
from config import Config

def get_db():
    db = sqlite3.connect(Config.DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db

def init_db():
    db = get_db()
    
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('intern','mentor','hr','leader','admin')),
            avatar_url TEXT DEFAULT '',
            department TEXT DEFAULT '',
            position TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS intern_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            mentor_id INTEGER,
            start_date DATE,
            end_date DATE,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            status TEXT DEFAULT 'active' CHECK(status IN ('active','completed','terminated')),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (mentor_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS skill_dimensions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            max_score INTEGER DEFAULT 100
        );

        CREATE TABLE IF NOT EXISTS skill_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id INTEGER NOT NULL,
            dimension_id INTEGER NOT NULL,
            score INTEGER DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (intern_id) REFERENCES intern_profiles(id),
            FOREIGN KEY (dimension_id) REFERENCES skill_dimensions(id),
            UNIQUE(intern_id, dimension_id)
        );

        CREATE TABLE IF NOT EXISTS skill_score_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id INTEGER NOT NULL,
            dimension_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            changed_by INTEGER,
            change_reason TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (intern_id) REFERENCES intern_profiles(id),
            FOREIGN KEY (dimension_id) REFERENCES skill_dimensions(id),
            FOREIGN KEY (changed_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS skill_tree_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            position TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            level_required INTEGER DEFAULT 1,
            xp_reward INTEGER DEFAULT 100,
            prerequisites TEXT DEFAULT '[]',
            sort_order INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS skill_unlocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id INTEGER NOT NULL,
            template_id INTEGER NOT NULL,
            unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            unlocked_by TEXT DEFAULT 'system',
            FOREIGN KEY (intern_id) REFERENCES intern_profiles(id),
            FOREIGN KEY (template_id) REFERENCES skill_tree_templates(id),
            UNIQUE(intern_id, template_id)
        );

        CREATE TABLE IF NOT EXISTS growth_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'technical',
            difficulty INTEGER DEFAULT 1,
            xp_reward INTEGER DEFAULT 50,
            dimension_id INTEGER,
            FOREIGN KEY (dimension_id) REFERENCES skill_dimensions(id)
        );

        CREATE TABLE IF NOT EXISTS task_assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            intern_id INTEGER NOT NULL,
            assigned_by INTEGER NOT NULL,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending','in_progress','completed','overdue')),
            due_date DATE,
            completed_at DATETIME,
            FOREIGN KEY (task_id) REFERENCES growth_tasks(id),
            FOREIGN KEY (intern_id) REFERENCES intern_profiles(id),
            FOREIGN KEY (assigned_by) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS weekly_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id INTEGER NOT NULL,
            week_number INTEGER NOT NULL,
            content TEXT DEFAULT '',
            self_rating INTEGER DEFAULT 3,
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            mentor_comment TEXT DEFAULT '',
            mentor_reviewed_at DATETIME,
            leader_comment TEXT DEFAULT '',
            leader_reviewed_at DATETIME,
            FOREIGN KEY (intern_id) REFERENCES intern_profiles(id)
        );

        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id INTEGER NOT NULL,
            mentor_id INTEGER NOT NULL,
            type TEXT DEFAULT 'weekly' CHECK(type IN ('weekly','milestone','ad_hoc')),
            content TEXT DEFAULT '',
            rating INTEGER,
            dimension_scores TEXT DEFAULT '{}',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (intern_id) REFERENCES intern_profiles(id),
            FOREIGN KEY (mentor_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS growth_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT DEFAULT '',
            xp_change INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (intern_id) REFERENCES intern_profiles(id)
        );

        CREATE TABLE IF NOT EXISTS ai_analysis_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            intern_id INTEGER NOT NULL,
            analysis_type TEXT NOT NULL,
            content TEXT DEFAULT '',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (intern_id) REFERENCES intern_profiles(id)
        );

        CREATE TABLE IF NOT EXISTS task_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignment_id INTEGER NOT NULL,
            intern_id INTEGER NOT NULL,
            content TEXT DEFAULT '',
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (assignment_id) REFERENCES task_assignments(id),
            FOREIGN KEY (intern_id) REFERENCES intern_profiles(id)
        );

        CREATE TABLE IF NOT EXISTS learning_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT DEFAULT '',
            category TEXT DEFAULT 'general',
            author_id INTEGER NOT NULL,
            department TEXT DEFAULT '',
            attachments TEXT DEFAULT '[]',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (author_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT DEFAULT '',
            description TEXT DEFAULT '',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    ''')
    
    db.commit()
    db.close()
    print("Database initialized successfully.")

if __name__ == '__main__':
    init_db()
