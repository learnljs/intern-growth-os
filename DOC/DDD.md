# 实习能量站（Intern Growth OS）

## 领域驱动设计文档（DDD）

---

# 1. 领域概述

## 1.1 领域定位

本系统属于**企业人才培养**领域，核心域是**实习生成长管理**。

## 1.2 限界上下文划分

```
┌─────────────────────────────────────────────────────────┐
│                    Intern Growth OS                      │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  身份与访问   │  │  成长管理    │  │  协作与反馈   │  │
│  │  Context     │  │  Context     │  │  Context     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  人才洞察    │  │  AI 分析     │  │  系统管理    │  │
│  │  Context     │  │  Context     │  │  Context     │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

| 限界上下文 | 职责 | 核心聚合 |
|------------|------|----------|
| 身份与访问 | 用户注册、登录、权限 | User |
| 成长管理 | 等级、经验、技能树、任务 | InternProfile, GrowthTask, SkillTree |
| 协作与反馈 | 周报、反馈、导师带教 | WeeklyReport, Feedback |
| 人才洞察 | HR 看板、风险预警、部门对比 | TalentPool, RiskAlert |
| AI 分析 | 成长分析、转正预测、AI 助手 | AIAnalysis |
| 系统管理 | 用户管理、种子数据、配置 | SystemConfig |

---

# 2. 身份与访问上下文

## 2.1 聚合：User

### 聚合根：User

**实体属性**：
- id: UserId（值对象）
- email: Email（值对象）
- password_hash: PasswordHash（值对象）
- name: String
- role: UserRole（值对象）
- avatar_url: String
- department: String
- position: String
- created_at: DateTime

### 值对象

#### UserId
```
不可变标识符，全局唯一
```

#### Email
```
- 必须包含 @
- 全局唯一
- 不可变
```

#### PasswordHash
```
- BCrypt 加密存储
- 不可逆
```

#### UserRole
```
枚举值：INTERN / MENTOR / HR / LEADER / ADMIN
```

### 领域事件

| 事件 | 触发时机 | 消费者 |
|------|----------|--------|
| UserRegistered | 用户注册成功 | 成长管理（创建 InternProfile） |
| UserLoggedIn | 用户登录成功 | 无 |

### 仓储接口

```python
class UserRepository:
    def find_by_id(user_id: UserId) -> User
    def find_by_email(email: Email) -> User
    def save(user: User) -> None
    def exists_by_email(email: Email) -> bool
```

---

# 3. 成长管理上下文

## 3.1 聚合：InternProfile

### 聚合根：InternProfile

**实体属性**：
- id: InternProfileId（值对象）
- user_id: UserId（值对象）
- mentor_id: UserId（值对象）
- start_date: Date
- end_date: Date
- level: Level（值对象）
- xp: ExperiencePoints（值对象）
- status: InternStatus（值对象）

### 值对象

#### Level
```
- 范围：1-10
- 不可变
- 包含升级判定逻辑
```

#### ExperiencePoints
```
- 非负整数
- 支持加法运算
- 包含升级阈值判定
```

#### InternStatus
```
枚举值：ACTIVE / COMPLETED / TERMINATED
```

### 领域服务：LevelUpService

```python
class LevelUpService:
    """等级升级判定服务"""
    
    def check_and_upgrade(self, profile: InternProfile) -> Optional[LevelUpEvent]:
        """检查是否满足升级条件，满足则升级并返回事件"""
        # 逻辑：当前 XP >= 下一等级所需 XP
        # 升级后触发 LevelUpEvent
```

### 领域事件

| 事件 | 触发时机 | 消费者 |
|------|----------|--------|
| InternProfileCreated | 实习生注册完成 | 成长管理（初始化技能树） |
| LevelUp | 等级提升 | 成长管理（检查技能解锁） |
| XpEarned | 获得经验值 | 成长管理（检查等级升级） |

### 仓储接口

```python
class InternProfileRepository:
    def find_by_id(profile_id: InternProfileId) -> InternProfile
    def find_by_user_id(user_id: UserId) -> InternProfile
    def find_by_mentor_id(mentor_id: UserId) -> List[InternProfile]
    def save(profile: InternProfile) -> None
    def find_all_active() -> List[InternProfile]
```

---

## 3.2 聚合：GrowthTask

### 聚合根：GrowthTask

**实体属性**：
- id: TaskId（值对象）
- title: String
- description: String
- category: TaskCategory（值对象）
- difficulty: Difficulty（值对象）
- xp_reward: ExperiencePoints（值对象）
- dimension_id: SkillDimensionId（值对象）

### 值对象

#### TaskId
```
不可变标识符，全局唯一
```

#### TaskCategory
```
枚举值：TECHNICAL / BUSINESS / COMMUNICATION / INITIATIVE
```

#### Difficulty
```
- 范围：1-5
- 不可变
```

### 领域事件

| 事件 | 触发时机 | 消费者 |
|------|----------|--------|
| TaskCreated | 任务创建 | 无 |
| TaskAssigned | 任务分配给实习生 | 成长管理（通知实习生） |
| TaskCompleted | 任务完成 | 成长管理（发放 XP、检查技能解锁） |
| TaskOverdue | 任务逾期 | 协作与反馈（通知导师） |

### 仓储接口

```python
class GrowthTaskRepository:
    def find_by_id(task_id: TaskId) -> GrowthTask
    def find_all() -> List[GrowthTask]
    def save(task: GrowthTask) -> None
```

---

## 3.3 聚合：TaskAssignment

### 聚合根：TaskAssignment

**实体属性**：
- id: TaskAssignmentId（值对象）
- task_id: TaskId（值对象）
- intern_id: InternProfileId（值对象）
- assigned_by: UserId（值对象）
- status: AssignmentStatus（值对象）
- due_date: Date
- completed_at: Optional[DateTime]

### 值对象

#### AssignmentStatus
```
枚举值：PENDING / IN_PROGRESS / COMPLETED / OVERDUE
状态流转：
  PENDING → IN_PROGRESS（实习生开始）
  IN_PROGRESS → COMPLETED（实习生完成）
  IN_PROGRESS → OVERDUE（超过截止日期）
```

### 领域服务：AssignmentService

```python
class AssignmentService:
    """任务分配与状态管理服务"""
    
    def assign_task(self, task_id, intern_id, assigned_by, due_date) -> TaskAssignment:
        """分配任务"""
    
    def start_task(self, assignment_id, intern_id) -> None:
        """开始任务（状态流转）"""
    
    def complete_task(self, assignment_id, intern_id) -> XpEarnedEvent:
        """完成任务（发放 XP，返回事件）"""
```

### 仓储接口

```python
class TaskAssignmentRepository:
    def find_by_id(assignment_id: TaskAssignmentId) -> TaskAssignment
    def find_by_intern_id(intern_id: InternProfileId) -> List[TaskAssignment]
    def find_overdue_tasks() -> List[TaskAssignment]
    def save(assignment: TaskAssignment) -> None
```

---

## 3.3.1 聚合：TaskSubmission

### 聚合根：TaskSubmission

**实体属性**：
- id: TaskSubmissionId（值对象）
- assignment_id: TaskAssignmentId（值对象）
- intern_id: InternProfileId（值对象）
- content: String（提交内容）
- submitted_at: DateTime

### 领域事件

| 事件 | 触发时机 | 消费者 |
|------|----------|--------|
| TaskSubmitted | 实习生提交任务内容 | 协作与反馈（通知导师） |

### 仓储接口

```python
class TaskSubmissionRepository:
    def find_by_assignment_id(assignment_id: TaskAssignmentId) -> List[TaskSubmission]
    def save(submission: TaskSubmission) -> None
```

---

## 3.4 聚合：SkillTree

### 聚合根：SkillTreeTemplate

**实体属性**：
- id: SkillTreeTemplateId（值对象）
- position: String（岗位）
- name: String（技能名称）
- description: String
- level_required: Level（值对象）
- xp_reward: ExperiencePoints（值对象）
- prerequisites: List[SkillTreeTemplateId]（前置技能 ID 列表）
- sort_order: int

### 值对象

#### SkillTreeTemplateId
```
不可变标识符，全局唯一
```

### 领域事件

| 事件 | 触发时机 | 消费者 |
|------|----------|--------|
| SkillUnlocked | 技能解锁 | 成长管理（发放 XP） |
| SkillTreeInitialized | 实习生入职，技能树初始化 | 无 |

### 领域服务：SkillUnlockService

```python
class SkillUnlockService:
    """技能解锁判定服务"""
    
    def check_and_unlock(self, intern_id: InternProfileId) -> List[SkillUnlockedEvent]:
        """检查所有未解锁技能，满足条件的自动解锁"""
    
    def manual_unlock(self, intern_id, template_id, unlocked_by) -> SkillUnlockedEvent:
        """导师手动解锁技能"""
```

### 仓储接口

```python
class SkillTreeTemplateRepository:
    def find_by_position(position: str) -> List[SkillTreeTemplate]
    def find_by_id(template_id: SkillTreeTemplateId) -> SkillTreeTemplate
    def save(template: SkillTreeTemplate) -> None

class SkillUnlockRepository:
    def find_by_intern_id(intern_id: InternProfileId) -> List[SkillUnlock]
    def is_unlocked(intern_id: InternProfileId, template_id: SkillTreeTemplateId) -> bool
    def save(unlock: SkillUnlock) -> None
```

---

## 3.5 聚合：SkillScore

### 聚合根：SkillScore

**实体属性**：
- id: SkillScoreId（值对象）
- intern_id: InternProfileId（值对象）
- dimension_id: SkillDimensionId（值对象）
- score: Score（值对象）
- updated_at: DateTime

### 值对象

#### SkillDimensionId
```
不可变标识符，对应六个维度
维度：TECHNICAL / COMMUNICATION / BUSINESS / INITIATIVE / PROBLEM_SOLVING / ENGINEERING
```

#### Score
```
- 范围：0-100
- 不可变
```

### 领域事件

| 事件 | 触发时机 | 消费者 |
|------|----------|--------|
| ScoreChanged | 评分变更 | 成长管理（记录历史） |

### 仓储接口

```python
class SkillScoreRepository:
    def find_by_intern_id(intern_id: InternProfileId) -> List[SkillScore]
    def find_by_intern_and_dimension(intern_id, dimension_id) -> SkillScore
    def save(score: SkillScore) -> None
    def save_batch(scores: List[SkillScore]) -> None
```

---

## 3.5.1 聚合：SkillScoreHistory

### 聚合根：SkillScoreHistory

**实体属性**：
- id: SkillScoreHistoryId（值对象）
- intern_id: InternProfileId（值对象）
- dimension_id: SkillDimensionId（值对象）
- score: Score（值对象）
- changed_by: Optional[UserId]（值对象）
- change_reason: String
- created_at: DateTime

### 仓储接口

```python
class SkillScoreHistoryRepository:
    def find_by_intern_id(intern_id: InternProfileId) -> List[SkillScoreHistory]
    def save(history: SkillScoreHistory) -> None
```

---

## 3.6 聚合：GrowthLog

### 聚合根：GrowthLog

**实体属性**：
- id: GrowthLogId（值对象）
- intern_id: InternProfileId（值对象）
- event_type: GrowthEventType（值对象）
- description: String
- xp_change: int
- created_at: DateTime

### 值对象

#### GrowthEventType
```
枚举值：TASK_COMPLETED / FEEDBACK_RECEIVED / LEVEL_UP / SKILL_UNLOCKED / MILESTONE
```

### 仓储接口

```python
class GrowthLogRepository:
    def find_by_intern_id(intern_id: InternProfileId) -> List[GrowthLog]
    def save(log: GrowthLog) -> None
```

---

# 4. 协作与反馈上下文

## 4.1 聚合：WeeklyReport

### 聚合根：WeeklyReport

**实体属性**：
- id: WeeklyReportId（值对象）
- intern_id: InternProfileId（值对象）
- week_number: int
- content: String（Markdown 格式）
- self_rating: Rating（值对象）
- submitted_at: DateTime
- mentor_comment: Optional[String]
- mentor_reviewed_at: Optional[DateTime]

### 值对象

#### WeeklyReportId
```
不可变标识符，全局唯一
```

#### Rating
```
- 范围：1-5
- 不可变
```

### 领域事件

| 事件 | 触发时机 | 消费者 |
|------|----------|--------|
| WeeklyReportSubmitted | 周报提交 | 协作与反馈（通知导师） |
| WeeklyReportReviewed | 周报批阅 | 协作与反馈（通知实习生） |

### 仓储接口

```python
class WeeklyReportRepository:
    def find_by_id(report_id: WeeklyReportId) -> WeeklyReport
    def find_by_intern_id(intern_id: InternProfileId) -> List[WeeklyReport]
    def find_by_intern_and_week(intern_id, week_number) -> WeeklyReport
    def save(report: WeeklyReport) -> None
```

---

## 4.2 聚合：Feedback

### 聚合根：Feedback

**实体属性**：
- id: FeedbackId（值对象）
- intern_id: InternProfileId（值对象）
- mentor_id: UserId（值对象）
- type: FeedbackType（值对象）
- content: String
- rating: Optional[Rating]（值对象）
- dimension_scores: Dict[SkillDimensionId, Score]（六维评分）
- created_at: DateTime

### 值对象

#### FeedbackId
```
不可变标识符，全局唯一
```

#### FeedbackType
```
枚举值：WEEKLY / MILESTONE / AD_HOC
```

### 领域事件

| 事件 | 触发时机 | 消费者 |
|------|----------|--------|
| FeedbackGiven | 导师给予反馈 | 成长管理（更新六维评分）、AI 分析（触发重新分析） |

### 领域服务：FeedbackService

```python
class FeedbackService:
    """反馈处理服务"""
    
    def give_feedback(self, intern_id, mentor_id, type, content, rating, 
                      dimension_scores) -> Feedback:
        """导师给予反馈，同时更新六维能力评分"""
    
    def update_dimension_scores(self, intern_id: InternProfileId, 
                                 scores: Dict[SkillDimensionId, Score]) -> None:
        """更新实习生的六维能力评分"""
```

### 仓储接口

```python
class FeedbackRepository:
    def find_by_id(feedback_id: FeedbackId) -> Feedback
    def find_by_intern_id(intern_id: InternProfileId) -> List[Feedback]
    def save(feedback: Feedback) -> None
```

---

# 5. 人才洞察上下文

## 5.1 聚合：TalentPool

### 聚合根：TalentPool（查询模型）

**聚合不存储数据，是跨上下文的查询视图。**

### 查询服务：TalentPoolQueryService

```python
class TalentPoolQueryService:
    """人才池查询服务"""
    
    def get_all_interns(self, filters: TalentFilter) -> List[TalentSummary]:
        """获取所有实习生摘要信息（支持筛选）"""
    
    def get_department_stats(self) -> List[DepartmentStats]:
        """获取各部门统计数据"""
    
    def get_high_potential_interns(self, threshold: float) -> List[TalentSummary]:
        """获取高潜人才列表"""
```

### 值对象

#### TalentFilter
```
- department: Optional[String]
- position: Optional[String]
- status: Optional[InternStatus]
- keyword: Optional[String]
```

#### TalentSummary
```
- intern_id
- name
- department
- position
- mentor_name
- level
- status
- conversion_probability
```

#### DepartmentStats
```
- department_name
- intern_count
- avg_level
- avg_conversion_probability
- risk_count
```

---

## 5.2 聚合：RiskAlert

### 聚合根：RiskAlert

**实体属性**：
- id: RiskAlertId（值对象）
- intern_id: InternProfileId（值对象）
- risk_type: RiskType（值对象）
- risk_level: RiskLevel（值对象）
- description: String
- detected_at: DateTime
- status: AlertStatus（值对象）
- handled_by: Optional[UserId]
- handled_at: Optional[DateTime]
- handling_note: Optional[String]

### 值对象

#### RiskAlertId
```
不可变标识符，全局唯一
```

#### RiskType
```
枚举值：
GROWTH_STAGNATION    成长停滞（连续2周无任务完成）
FEEDBACK_MISSING     导师反馈缺失（超过1周无反馈）
REPORT_ABSENCE       周报缺交（连续2周未提交）
SCORE_DECLINE        能力下降（某维度评分持续下降）
LOW_CONVERSION       转正概率低（AI 预测低于40%）
```

#### RiskLevel
```
枚举值：LOW / MEDIUM / HIGH
```

#### AlertStatus
```
枚举值：ACTIVE / HANDLED / DISMISSED
```

### 领域事件

| 事件 | 触发时机 | 消费者 |
|------|----------|--------|
| RiskDetected | 检测到风险 | 人才洞察（通知 HR） |
| RiskHandled | 风险已处理 | 人才洞察（更新状态） |

### 仓储接口

```python
class RiskAlertRepository:
    def find_by_id(alert_id: RiskAlertId) -> RiskAlert
    def find_active_alerts() -> List[RiskAlert]
    def find_by_intern_id(intern_id: InternProfileId) -> List[RiskAlert]
    def save(alert: RiskAlert) -> None
```

---

# 6. AI 分析上下文

## 6.1 聚合：AIAnalysis

### 聚合根：AIAnalysis

**实体属性**：
- id: AIAnalysisId（值对象）
- intern_id: InternProfileId（值对象）
- analysis_type: AnalysisType（值对象）
- content: String（JSON 格式，AI 生成内容）
- created_at: DateTime
- expires_at: DateTime（缓存过期时间）

### 值对象

#### AIAnalysisId
```
不可变标识符，全局唯一
```

#### AnalysisType
```
枚举值：
GROWTH_SUMMARY     成长分析报告（已合并到成长分析页面）
RISK_PREDICTION    转正预测（已合并到成长分析页面）
RECOMMENDATION     学习推荐
MENTOR_ADVICE      导师带教建议
HR_INSIGHT         HR 人才洞察
```

### 领域服务：AIAnalysisService

```python
class AIAnalysisService:
    """AI 分析服务"""
    
    def generate_growth_analysis(self, intern_id: InternProfileId) -> AIAnalysis:
        """生成成长分析报告"""
    
    def generate_conversion_prediction(self, intern_id: InternProfileId) -> AIAnalysis:
        """生成转正预测"""
    
    def generate_mentor_advice(self, context: str) -> AIAnalysis:
        """生成导师带教建议"""
    
    def generate_hr_insight(self) -> AIAnalysis:
        """生成 HR 人才洞察"""
    
    def get_cached_analysis(self, intern_id: InternProfileId, 
                            analysis_type: AnalysisType) -> Optional[AIAnalysis]:
        """获取缓存的分析结果（24小时内有效）"""
```

### 仓储接口

```python
class AIAnalysisRepository:
    def find_by_id(analysis_id: AIAnalysisId) -> AIAnalysis
    def find_by_intern_and_type(intern_id, analysis_type) -> Optional[AIAnalysis]
    def save(analysis: AIAnalysis) -> None
```

---

## 6.2 领域服务：PredictionService

### 转正预测服务

```python
class PredictionService:
    """转正预测服务（规则引擎）"""
    
    def predict(self, intern_id: InternProfileId) -> ConversionPrediction:
        """预测转正概率"""
    
    def calculate_growth_rate(self, intern_id: InternProfileId) -> float:
        """计算能力成长速度"""
    
    def analyze_risk_factors(self, intern_id: InternProfileId) -> List[RiskFactor]:
        """分析风险因素"""
```

### AI 对话服务

```python
class AIChatService:
    """AI对话服务（接入DeepSeek API）"""
    
    def chat(self, intern_id: InternProfileId, question: str) -> str:
        """根据问题和用户数据生成回复"""
        # 使用DeepSeek API，兼容OpenAI接口格式
        # 将用户数据作为上下文传入系统提示
        # 支持的问题类型：
        # - 技术能力提升建议
        # - 沟通协作建议
        # - 业务理解建议
        # - 个人成长建议
        # - 问题解决建议
        # - 工程素养建议
        # - 转正预测咨询
```

### 值对象

#### ConversionPrediction
```
- probability: float (0-100)
- risk_level: RiskLevel
- factors: List[RiskFactor]
- suggestions: List[String]
```

#### RiskFactor
```
- dimension: SkillDimensionId
- current_score: Score
- trend: Trend (IMPROVING / STABLE / DECLINING)
- description: String
```

---

# 7. 系统管理上下文

## 7.1 聚合：SystemConfig

### 聚合根：SystemConfig

**实体属性**：
- id: ConfigId（值对象）
- key: String
- value: String
- description: String
- updated_at: DateTime

### 值对象

#### ConfigKey
```
枚举值：
AI_MODE           AI 模式（openai / claude / mock）
OPENAI_API_KEY    OpenAI API Key
CLAUDE_API_KEY    Claude API Key
SKILL_TREE_TEMPLATES  技能树模板配置
```

### 仓储接口

```python
class SystemConfigRepository:
    def find_by_key(key: ConfigKey) -> SystemConfig
    def save(config: SystemConfig) -> None
    def find_all() -> List[SystemConfig]
```

---

# 8. 领域事件总览

## 8.1 事件清单

| 上下文 | 事件 | 触发时机 | 消费者 |
|--------|------|----------|--------|
| 身份与访问 | UserRegistered | 用户注册成功 | 成长管理（创建 InternProfile） |
| 成长管理 | InternProfileCreated | 实习生档案创建 | 成长管理（初始化技能树） |
| 成长管理 | LevelUp | 等级提升 | 成长管理（检查技能解锁） |
| 成长管理 | XpEarned | 获得经验值 | 成长管理（检查等级升级） |
| 成长管理 | SkillUnlocked | 技能解锁 | 成长管理（发放 XP） |
| 成长管理 | TaskAssigned | 任务分配 | 协作与反馈（通知实习生） |
| 成长管理 | TaskCompleted | 任务完成 | 成长管理（发放 XP） |
| 成长管理 | TaskOverdue | 任务逾期 | 协作与反馈（通知导师） |
| 协作与反馈 | WeeklyReportSubmitted | 周报提交 | 协作与反馈（通知导师） |
| 协作与反馈 | WeeklyReportReviewed | 周报批阅 | 协作与反馈（通知实习生） |
| 协作与反馈 | FeedbackGiven | 导师给予反馈 | 成长管理（更新评分）、成长管理（记录历史） |
| 成长管理 | ScoreChanged | 评分变更 | 成长管理（记录历史） |
| 人才洞察 | RiskDetected | 检测到风险 | 人才洞察（通知 HR） |
| 人才洞察 | RiskHandled | 风险已处理 | 人才洞察（更新状态） |

## 8.2 事件驱动流程

### 实习生成长流程（事件链）

```
TaskCompleted
  → XpEarned
    → LevelUp（条件满足时）
      → SkillUnlocked（条件满足时）
        → GrowthLog 记录
```

### 反馈流程（事件链）

```
FeedbackGiven
  → SkillScore 更新
  → SkillScoreHistory 记录
  → GrowthLog 记录
```

### 风险检测流程（事件链）

```
TaskOverdue / WeeklyReport 缺交 / Feedback 缺失
  → RiskDetected
    → HR 收到通知
```

---

# 9. 聚合关系图

```
                    ┌─────────────┐
                    │    User     │
                    │ (聚合根)    │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────┴──────┐ ┌────┴────┐  ┌──────┴──────┐
     │InternProfile│ │Feedback │  │WeeklyReport │
     │ (聚合根)    │ │(聚合根) │  │ (聚合根)    │
     └──────┬──────┘ └─────────┘  └─────────────┘
            │
     ┌──────┼──────────────┬──────────────┐
     │      │              │              │
┌────┴───┐ ┌┴──────────┐ ┌┴───────────┐ ┌┴──────────┐
│TaskAssign│ │SkillScore │ │GrowthLog   │ │SkillUnlock│
│(聚合根) │ │(聚合根)   │ │(聚合根)    │ │(聚合根)   │
└────┬───┘ └─────┬─────┘ └────────────┘ └───────────┘
     │           │
┌────┴──────┐   ┌┴───────────────┐
│GrowthTask │   │SkillScoreHistory│
│(聚合根)   │   │(聚合根)         │
└────┬──────┘   └────────────────┘
     │
┌────┴──────────┐
│TaskSubmission │
│(聚合根)       │
└───────────────┘
```

---

# 10. 限界上下文通信

## 10.1 上下文映射

| 源上下文 | 目标上下文 | 通信方式 | 事件/数据 |
|----------|------------|----------|-----------|
| 身份与访问 | 成长管理 | 领域事件 | UserRegistered |
| 成长管理 | 成长管理 | 领域事件 | LevelUp, SkillUnlocked, XpEarned |
| 成长管理 | 协作与反馈 | 领域事件 | TaskAssigned, TaskOverdue |
| 协作与反馈 | 成长管理 | 领域事件 | FeedbackGiven |
| 成长管理 | 人才洞察 | 查询 | TalentPoolQueryService |
| 成长管理 | AI 分析 | 查询 | 数据聚合 |
| AI 分析 | 成长管理 | 查询 | 数据聚合 |
| AI 分析 | 人才洞察 | 查询 | 数据聚合 |

## 10.2 共享内核

以下数据在多个上下文中共享：

| 数据 | 共享上下文 | 访问方式 |
|------|------------|----------|
| User | 所有上下文 | 直接读取 |
| InternProfile | 成长管理、协作与反馈、人才洞察、AI 分析 | 直接读取 |
| SkillScore | 成长管理、AI 分析 | 直接读取 |
| GrowthLog | 成长管理、人才洞察 | 直接读取 |

---

# 11. 值对象汇总

| 值对象 | 所属上下文 | 说明 |
|--------|------------|------|
| UserId | 身份与访问 | 用户唯一标识 |
| Email | 身份与访问 | 登录邮箱 |
| PasswordHash | 身份与访问 | 密码哈希 |
| UserRole | 身份与访问 | 用户角色枚举 |
| InternProfileId | 成长管理 | 实习生档案标识 |
| Level | 成长管理 | 等级（1-10） |
| ExperiencePoints | 成长管理 | 经验值 |
| InternStatus | 成长管理 | 实习生状态枚举 |
| TaskId | 成长管理 | 任务标识 |
| TaskCategory | 成长管理 | 任务类别枚举 |
| Difficulty | 成长管理 | 任务难度（1-5） |
| AssignmentStatus | 成长管理 | 任务状态枚举 |
| SkillTreeTemplateId | 成长管理 | 技能树模板标识 |
| SkillScoreId | 成长管理 | 能力评分标识 |
| SkillDimensionId | 成长管理 | 能力维度标识 |
| Score | 成长管理 | 能力分数（0-100） |
| SkillScoreHistoryId | 成长管理 | 评分历史标识 |
| GrowthLogId | 成长管理 | 成长记录标识 |
| GrowthEventType | 成长管理 | 成长事件类型枚举 |
| TaskSubmissionId | 成长管理 | 任务提交标识 |
| WeeklyReportId | 协作与反馈 | 周报标识 |
| Rating | 协作与反馈 | 评分（1-5） |
| FeedbackId | 协作与反馈 | 反馈标识 |
| FeedbackType | 协作与反馈 | 反馈类型枚举 |
| RiskAlertId | 人才洞察 | 风险预警标识 |
| RiskType | 人才洞察 | 风险类型枚举 |
| RiskLevel | 人才洞察 | 风险等级枚举 |
| AlertStatus | 人才洞察 | 预警状态枚举 |
| TalentFilter | 人才洞察 | 人才筛选条件 |
| TalentSummary | 人才洞察 | 人才摘要信息 |
| DepartmentStats | 人才洞察 | 部门统计信息 |
| AIAnalysisId | AI 分析 | AI 分析标识 |
| AnalysisType | AI 分析 | 分析类型枚举 |
| ConversionPrediction | AI 分析 | 转正预测结果 |
| RiskFactor | AI 分析 | 风险因素 |
| ConfigId | 系统管理 | 配置标识 |
| ConfigKey | 系统管理 | 配置键枚举 |

