# 实习能量站（Intern Growth OS）

## 部署指南

> 本指南介绍三种部署到公网的方案，按推荐度排序。

---

## 🚀 方案一：Render（推荐，免费 + 零运维）

**优点**：免费额度足够 Demo、自动 HTTPS、Github 自动部署

### 准备工作

1. **创建 `requirements.txt`**（已存在，确认包含）：
```
Flask
requests
```

2. **创建 `Procfile`**（项目根目录）：
```
web: python app.py
```

3. **修改 `app.py` 监听端口**（最后一行）：
```python
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
```

4. **将代码推到 GitHub**

### 部署步骤

1. 访问 https://render.com 用 GitHub 登录
2. 点击 `New +` → `Web Service`
3. 选择你的 GitHub 仓库
4. 填写：
   - Name: `intern-growth-os`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python app.py`
5. 点击 `Create Web Service`
6. 等待部署完成（约 3-5 分钟），获得公网链接如 `https://intern-growth-os.onrender.com`

### 注意事项

- 免费版会在 15 分钟无访问后休眠，首次访问需等待 30 秒唤醒
- SQLite 数据库会随容器重启而重置，建议演示前重新初始化数据

---

## ☁️ 方案二：阿里云 / 腾讯云轻量服务器（国内访问快）

**优点**：国内访问无延迟、数据持久化

### 步骤

1. 购买轻量应用服务器（最低配置约 60 元/月）
2. 选择系统：Ubuntu 22.04
3. SSH 登录后执行：
```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx -y
git clone <你的仓库>
cd "Intern Growth OS"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 init_db.py
nohup python3 app.py > app.log 2>&1 &
```
4. 配置 Nginx 反向代理（端口 80 → 5000）
5. 申请免费 SSL（Let's Encrypt）

---

## 🐍 方案三：PythonAnywhere（最简单，纯 Python）

1. 注册 https://www.pythonanywhere.com
2. 上传项目文件（或 GitHub 拉取）
3. 创建 Web App → 选 Flask
4. 修改 WSGI 配置文件指向 `app.py`
5. 重新加载，获得 `xxx.pythonanywhere.com` 链接

---

## 📦 部署前 Checklist

- [ ] `requirements.txt` 完整
- [ ] DeepSeek API Key 通过环境变量配置（不要硬编码）
- [ ] `app.run(debug=False)` 关闭调试模式
- [ ] 数据库初始化（`python init_db.py`）
- [ ] 创建管理员账号（admin@growth.com / admin123）

---

## 🔐 环境变量配置

将敏感信息（如 DeepSeek API Key）改为环境变量：

```python
# app.py
import os
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
```

在部署平台（Render/服务器）配置：
```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
SECRET_KEY=随机生成的密钥
```
