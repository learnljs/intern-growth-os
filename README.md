# 实习能量站（Intern Growth OS）

> **AI 驱动的实习生成长导航与带教协同平台**  
> 让实习生成长过程：可视化 · 可预测 · 可干预

---

## ✨ 功能介绍

### 🎮 Growth Twin 数字分身
游戏化等级（Lv.1 → Lv.10），经验值驱动成长，每个等级有专属称号

### 📊 六维能力雷达图
从 **技术能力、沟通协作、业务理解、主动成长、问题解决、工程素养** 六个维度精细评估

### 🌳 岗位专属技能树
按岗位自动匹配技能路径，管理员可视化配置技能节点

### 🤖 AI 能力加持
- **实习生**：AI 成长助手实时问答 + 转正预测
- **导师**：AI 带教助手 + 个性化培养计划生成

### 📝 三方协同周报
实习生提交 → 导师评语（含六维评分） → 主管建议，完整记录

---

## 🎭 角色与界面配色

| 角色 | 主色 | 核心功能 |
|------|------|----------|
| 🟠 实习生 | 橙色 | 仪表盘、成长任务、周报、AI 助手 |
| 🟢 带教导师 | 绿色 | 任务管理、反馈评分、培养计划、AI 带教 |
| 🟣 部门主管 | 紫色 | 部门概况、周报审阅、高潜识别、资料管理 |
| 🔵 管理员 | 灰蓝 | 用户管理、导师分配、技能树配置 |

---

## 🔑 演示账号

### 管理员
| 邮箱 | 密码 | 角色 |
|------|------|------|
| `admin@growth.com` | `admin123` | 管理员 |

### 其他角色
其他角色的账号需要自行注册：
1. 打开首页 → 选择对应角色入口
2. 点击「注册」填写信息
3. 注册成功后登录使用

---

## 🚀 本地运行

### 环境要求
- Python 3.8+

### 安装与启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库
python init_db.py

# 3. 启动服务
python app.py

# 4. 打开浏览器访问
# http://127.0.0.1:5000
```

---

## 📁 项目结构

```
Intern Growth OS/
├── app.py                   # 主应用
├── init_db.py               # 数据库初始化
├── config.py                # 配置文件
├── requirements.txt         # 依赖清单
├── growth_os.db             # SQLite 数据库
├── static/
│   ├── css/style.css        # 样式
│   └── js/app.js            # 脚本
├── templates/
│   ├── base.html            # 基础模板
│   ├── layout.html          # 布局（含侧边栏导航）
│   ├── landing.html         # 首页
│   ├── login.html           # 登录
│   ├── register.html        # 注册
│   ├── intern/              # 实习生页面
│   ├── mentor/              # 导师页面
│   ├── leader/              # 主管页面
│   └── admin/               # 管理员页面
└── DOC/
    ├── SPEC.md              # 需求规格说明书
    ├── DEPLOY.md            # 部署指南
    └── PROPOSAL.md          # 方案说明
```

---

## ⚙️ 技术栈

| 组件 | 技术 |
|------|------|
| 后端框架 | Flask 3.x |
| 数据库 | SQLite |
| 前端 | HTML + CSS + JavaScript |
| 图表 | Chart.js（雷达图） |
| AI 模型 | DeepSeek API (`deepseek-chat`) |

---

## 📄 文档

- [需求规格说明书](DOC/SPEC.md)
- [部署指南](DOC/DEPLOY.md)
- [方案说明（1000字）](DOC/PROPOSAL.md)

---

## 🛠️ 配置 AI API

在 `app.py` 中找到以下配置项，替换为你的 API Key：

```python
DEEPSEEK_API_KEY = 'sk-你的API-KEY'
DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
```

---

## 📝 许可

仅供学习和演示使用。
