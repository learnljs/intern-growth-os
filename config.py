import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'intern-growth-os-secret-key-2026')
    DATABASE = os.path.join(BASE_DIR, 'growth_os.db')
    
    AI_MODE = os.getenv('AI_MODE', 'mock')  # 'openai' | 'claude' | 'mock' | 'deepseek'
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY', '')
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')
    AI_CACHE_HOURS = 24
