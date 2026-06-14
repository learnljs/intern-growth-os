# 实习能量站（Intern Growth OS）

## 测试驱动开发文档（TDD）

---

# 1. 测试策略

## 1.1 测试金字塔

```
        ╱╲
       ╱  ╲       E2E 测试（少量）
      ╱    ╲      关键业务流程端到端验证
     ╱──────╲
    ╱        ╲    集成测试（中量）
   ╱          ╲   API 接口 + 数据库交互
  ╱────────────╲
 ╱              ╲  单元测试（大量）
╱                ╲ 领域逻辑 + 服务逻辑 + 工具函数
──────────────────
```

## 1.2 测试范围

| 层级 | 测试类型 | 覆盖范围 | 数量占比 |
|------|----------|----------|----------|
| 单元测试 | Domain Service | 领域服务、值对象、领域事件 | 60% |
| 单元测试 | Application Service | 业务流程编排 | 20% |
| 集成测试 | API + DB | 路由 + 数据库操作 | 15% |
| E2E 测试 | 全流程 | 关键用户旅程 | 5% |

## 1.3 测试框架

- **Python**: pytest
- **数据库**: pytest-sqlite（内存数据库）
- **Mock**: unittest.mock
- **覆盖率**: pytest-cov

---

# 2. 单元测试

## 2.1 值对象测试

### 2.1.1 Level 测试

```python
class TestLevel:
    """等级值对象测试"""
    
    def test_level_min_value(self):
        """等级最小值为 1"""
        level = Level(1)
        assert level.value == 1
    
    def test_level_max_value(self):
        """等级最大值为 10"""
        level = Level(10)
        assert level.value == 10
    
    def test_level_out_of_range_raises_error(self):
        """等级超出范围抛出异常"""
        with pytest.raises(ValueError):
            Level(0)
        with pytest.raises(ValueError):
            Level(11)
    
    def test_level_comparison(self):
        """等级可比较大小"""
        assert Level(3) > Level(1)
        assert Level(5) == Level(5)
        assert Level(2) < Level(4)
```

### 2.1.2 ExperiencePoints 测试

```python
class TestExperiencePoints:
    """经验值值对象测试"""
    
    def test_xp_non_negative(self):
        """经验值不能为负"""
        with pytest.raises(ValueError):
            ExperiencePoints(-100)
    
    def test_xp_addition(self):
        """经验值可加法运算"""
        xp1 = ExperiencePoints(100)
        xp2 = ExperiencePoints(50)
        result = xp1 + xp2
        assert result.value == 150
    
    def test_xp_can_reach_level_threshold(self):
        """经验值可判断是否达到升级阈值"""
        xp = ExperiencePoints(200)
        assert xp >= 200  # Lv.2 阈值
```

### 2.1.3 Email 测试

```python
class TestEmail:
    """邮箱值对象测试"""
    
    def test_valid_email(self):
        """有效邮箱格式"""
        email = Email("test@example.com")
        assert email.value == "test@example.com"
    
    def test_invalid_email_no_at(self):
        """缺少 @ 的邮箱抛出异常"""
        with pytest.raises(ValueError):
            Email("testexample.com")
    
    def test_invalid_email_no_domain(self):
        """缺少域名的邮箱抛出异常"""
        with pytest.raises(ValueError):
            Email("test@")
    
    def test_email_immutable(self):
        """邮箱不可变"""
        email = Email("test@example.com")
        with pytest.raises(AttributeError):
            email.value = "new@example.com"
```

### 2.1.4 Score 测试

```python
class TestScore:
    """能力分数值对象测试"""
    
    def test_score_range(self):
        """分数范围 0-100"""
        assert Score(0).value == 0
        assert Score(100).value == 100
    
    def test_score_out_of_range(self):
        """分数超出范围抛出异常"""
        with pytest.raises(ValueError):
            Score(-1)
        with pytest.raises(ValueError):
            Score(101)
    
    def test_score_percentage(self):
        """分数可转换为百分比"""
        score = Score(75)
        assert score.percentage == 0.75
```

---

## 2.2 领域服务测试

### 2.2.1 LevelUpService 测试

```python
class TestLevelUpService:
    """等级升级服务测试"""
    
    def setup_method(self):
        self.service = LevelUpService()
    
    def test_no_upgrade_when_xp_insufficient(self):
        """经验值不足时不升级"""
        profile = InternProfile(
            level=Level(1),
            xp=ExperiencePoints(100)
        )
        result = self.service.check_and_upgrade(profile)
        assert result is None
        assert profile.level == Level(1)
    
    def test_upgrade_when_xp_reaches_threshold(self):
        """经验值达到阈值时升级"""
        profile = InternProfile(
            level=Level(1),
            xp=ExperiencePoints(200)
        )
        event = self.service.check_and_upgrade(profile)
        assert event is not None
        assert profile.level == Level(2)
    
    def test_multi_level_upgrade(self):
        """经验值足够时可连续升级"""
        profile = InternProfile(
            level=Level(1),
            xp=ExperiencePoints(600)
        )
        event = self.service.check_and_upgrade(profile)
        assert profile.level == Level(3)  # 跳级到 Lv.3
    
    def test_max_level_cap(self):
        """最高等级为 10，不再升级"""
        profile = InternProfile(
            level=Level(10),
            xp=ExperiencePoints(50000)
        )
        result = self.service.check_and_upgrade(profile)
        assert result is None
        assert profile.level == Level(10)
```

### 2.2.2 SkillUnlockService 测试

```python
class TestSkillUnlockService:
    """技能解锁服务测试"""
    
    def setup_method(self):
        self.service = SkillUnlockService()
    
    def test_unlock_when_level_met(self):
        """等级满足时解锁技能"""
        profile = InternProfile(level=Level(2), xp=ExperiencePoints(300))
        template = SkillTreeTemplate(
            name="JavaScript",
            level_required=Level(2),
            prerequisites=[]
        )
        unlocked = []
        
        events = self.service.check_and_unlock(profile, template, unlocked)
        assert len(events) == 1
        assert events[0].skill_name == "JavaScript"
    
    def test_no_unlock_when_level_insufficient(self):
        """等级不足时不解锁"""
        profile = InternProfile(level=Level(1), xp=ExperiencePoints(100))
        template = SkillTreeTemplate(
            name="React",
            level_required=Level(3),
            prerequisites=[]
        )
        unlocked = []
        
        events = self.service.check_and_unlock(profile, template, unlocked)
        assert len(events) == 0
    
    def test_no_unlock_when_prerequisite_missing(self):
        """前置技能未解锁时不解锁"""
        profile = InternProfile(level=Level(3), xp=ExperiencePoints(800))
        template = SkillTreeTemplate(
            name="React",
            level_required=Level(3),
            prerequisites=[SkillTreeTemplateId("js_id")]
        )
        unlocked = []  # 前置技能未解锁
        
        events = self.service.check_and_unlock(profile, template, unlocked)
        assert len(events) == 0
    
    def test_unlock_when_all_conditions_met(self):
        """所有条件满足时解锁"""
        profile = InternProfile(level=Level(3), xp=ExperiencePoints(800))
        template = SkillTreeTemplate(
            name="React",
            level_required=Level(3),
            prerequisites=[SkillTreeTemplateId("js_id")]
        )
        unlocked = [SkillTreeTemplateId("js_id")]  # 前置已解锁
        
        events = self.service.check_and_unlock(profile, template, unlocked)
        assert len(events) == 1
    
    def test_manual_unlock_bypasses_conditions(self):
        """导师手动解锁跳过条件检查"""
        profile = InternProfile(level=Level(1), xp=ExperiencePoints(0))
        template = SkillTreeTemplate(
            name="React",
            level_required=Level(5),
            prerequisites=[]
        )
        
        event = self.service.manual_unlock(profile, template, "mentor")
        assert event is not None
```

### 2.2.3 AssignmentService 测试

```python
class TestAssignmentService:
    """任务分配服务测试"""
    
    def setup_method(self):
        self.service = AssignmentService()
    
    def test_assign_task(self):
        """分配任务"""
        assignment = self.service.assign_task(
            task_id=TaskId("task_1"),
            intern_id=InternProfileId("intern_1"),
            assigned_by=UserId("mentor_1"),
            due_date=date(2026, 6, 20)
        )
        assert assignment.status == AssignmentStatus.PENDING
    
    def test_start_task(self):
        """开始任务"""
        assignment = self.service.assign_task(
            task_id=TaskId("task_1"),
            intern_id=InternProfileId("intern_1"),
            assigned_by=UserId("mentor_1"),
            due_date=date(2026, 6, 20)
        )
        self.service.start_task(assignment.id, InternProfileId("intern_1"))
        assert assignment.status == AssignmentStatus.IN_PROGRESS
    
    def test_complete_task(self):
        """完成任务"""
        assignment = self.service.assign_task(
            task_id=TaskId("task_1"),
            intern_id=InternProfileId("intern_1"),
            assigned_by=UserId("mentor_1"),
            due_date=date(2026, 6, 20)
        )
        self.service.start_task(assignment.id, InternProfileId("intern_1"))
        xp_event = self.service.complete_task(assignment.id, InternProfileId("intern_1"))
        
        assert assignment.status == AssignmentStatus.COMPLETED
        assert xp_event is not None
        assert xp_event.xp_amount > 0
    
    def test_cannot_complete_not_started_task(self):
        """未开始的任务不能完成"""
        assignment = self.service.assign_task(
            task_id=TaskId("task_1"),
            intern_id=InternProfileId("intern_1"),
            assigned_by=UserId("mentor_1"),
            due_date=date(2026, 6, 20)
        )
        
        with pytest.raises(InvalidStateError):
            self.service.complete_task(assignment.id, InternProfileId("intern_1"))
    
    def test_wrong_intern_cannot_start_task(self):
        """非本人任务不能开始"""
        assignment = self.service.assign_task(
            task_id=TaskId("task_1"),
            intern_id=InternProfileId("intern_1"),
            assigned_by=UserId("mentor_1"),
            due_date=date(2026, 6, 20)
        )
        
        with pytest.raises(AuthorizationError):
            self.service.start_task(assignment.id, InternProfileId("intern_2"))
```

### 2.2.4 FeedbackService 测试

```python
class TestFeedbackService:
    """反馈服务测试"""
    
    def setup_method(self):
        self.service = FeedbackService()
    
    def test_give_feedback_updates_scores(self):
        """给予反馈更新六维评分"""
        feedback = self.service.give_feedback(
            intern_id=InternProfileId("intern_1"),
            mentor_id=UserId("mentor_1"),
            type=FeedbackType.WEEKLY,
            content="本周表现不错",
            rating=Rating(4),
            dimension_scores={
                SkillDimensionId.TECHNICAL: Score(75),
                SkillDimensionId.COMMUNICATION: Score(80),
                SkillDimensionId.BUSINESS: Score(60),
                SkillDimensionId.INITIATIVE: Score(70),
                SkillDimensionId.PROBLEM_SOLVING: Score(65),
                SkillDimensionId.ENGINEERING: Score(55),
            }
        )
        
        assert feedback is not None
        assert feedback.rating == Rating(4)
        # 六维评分应被更新
    
    def test_feedback_creates_growth_log(self):
        """反馈应创建成长记录"""
        feedback = self.service.give_feedback(
            intern_id=InternProfileId("intern_1"),
            mentor_id=UserId("mentor_1"),
            type=FeedbackType.MILESTONE,
            content="完成项目里程碑",
            rating=Rating(5),
            dimension_scores={}
        )
        
        # 应触发 GrowthLog 记录
```

### 2.2.5 PredictionService 测试

```python
class TestPredictionService:
    """转正预测服务测试"""
    
    def setup_method(self):
        self.service = PredictionService()
    
    def test_high_probability_when_all_good(self):
        """所有指标良好时转正概率高"""
        data = {
            'growth_rate': 0.8,
            'completion_rate': 0.9,
            'avg_mentor_rating': 4.5,
            'avg_self_rating': 4.0,
            'xp': 3000,
            'unlocked_skills': 5,
            'total_skills': 6,
        }
        
        prediction = self.service.predict(data)
        assert prediction.probability >= 70
        assert prediction.risk_level == "low"
    
    def test_low_probability_when_poor_performance(self):
        """表现差时转正概率低"""
        data = {
            'growth_rate': 0.2,
            'completion_rate': 0.3,
            'avg_mentor_rating': 2.0,
            'avg_self_rating': 2.5,
            'xp': 500,
            'unlocked_skills': 1,
            'total_skills': 6,
        }
        
        prediction = self.service.predict(data)
        assert prediction.probability <= 40
        assert prediction.risk_level == "high"
    
    def test_medium_probability(self):
        """中等表现时转正概率中等"""
        data = {
            'growth_rate': 0.5,
            'completion_rate': 0.6,
            'avg_mentor_rating': 3.5,
            'avg_self_rating': 3.0,
            'xp': 1500,
            'unlocked_skills': 3,
            'total_skills': 6,
        }
        
        prediction = self.service.predict(data)
        assert 40 < prediction.probability < 70
        assert prediction.risk_level == "medium"
    
    def test_risk_factors_identified(self):
        """识别风险因素"""
        data = {
            'growth_rate': 0.3,
            'completion_rate': 0.4,
            'avg_mentor_rating': 2.5,
            'avg_self_rating': 2.0,
            'xp': 800,
            'unlocked_skills': 2,
            'total_skills': 6,
        }
        
        prediction = self.service.predict(data)
        assert len(prediction.factors) > 0
        # 应包含具体的风险因素描述
```

---

## 2.3 值对象计算测试

### 2.3.1 经验值升级阈值测试

```python
class TestLevelThresholds:
    """等级升级阈值测试"""
    
    def test_level_2_threshold(self):
        """Lv.2 需要 200 XP"""
        assert calculate_level(200) == 2
    
    def test_level_3_threshold(self):
        """Lv.3 需要 600 XP"""
        assert calculate_level(600) == 3
    
    def test_level_5_threshold(self):
        """Lv.5 需要 2000 XP"""
        assert calculate_level(2000) == 5
    
    def test_level_10_threshold(self):
        """Lv.10 需要 12000 XP"""
        assert calculate_level(12000) == 10
    
    def test_level_between_thresholds(self):
        """XP 在阈值之间时取较低等级"""
        assert calculate_level(300) == 2  # 200-599 → Lv.2
        assert calculate_level(1500) == 4  # 1200-1999 → Lv.4
```

### 2.3.2 雷达图数据计算测试

```python
class TestRadarChartData:
    """雷达图数据计算测试"""
    
    def test_six_dimensions(self):
        """雷达图包含六个维度"""
        scores = {
            'technical': 75,
            'communication': 80,
            'business': 60,
            'initiative': 70,
            'problem_solving': 65,
            'engineering': 55,
        }
        
        chart_data = calculate_radar_chart(scores)
        assert len(chart_data) == 6
    
    def test_dimension_labels(self):
        """六个维度标签正确"""
        labels = get_radar_labels()
        assert labels == [
            '技术能力', '沟通协作', '业务理解',
            '主动成长', '问题解决', '工程素养'
        ]
    
    def test_score_normalization(self):
        """分数标准化为 0-100"""
        scores = {'technical': 75}
        normalized = normalize_score(scores['technical'])
        assert 0 <= normalized <= 100
```

---

# 3. 集成测试

## 3.1 API 接口测试

### 3.1.1 认证接口测试

```python
class TestAuthAPI:
    """认证 API 集成测试"""
    
    def test_register_success(self, client):
        """注册成功"""
        response = client.post('/api/auth/register', json={
            'email': 'new@test.com',
            'password': 'password123',
            'name': '测试用户',
            'role': 'intern',
            'department': '技术部',
            'position': '前端'
        })
        assert response.status_code == 201
        assert 'user_id' in response.json
    
    def test_register_duplicate_email(self, client):
        """重复邮箱注册失败"""
        # 先注册一次
        client.post('/api/auth/register', json={
            'email': 'dup@test.com',
            'password': 'password123',
            'name': '用户1',
            'role': 'intern',
            'department': '技术部',
            'position': '前端'
        })
        
        # 再次注册
        response = client.post('/api/auth/register', json={
            'email': 'dup@test.com',
            'password': 'password456',
            'name': '用户2',
            'role': 'intern',
            'department': '技术部',
            'position': '后端'
        })
        assert response.status_code == 409
    
    def test_login_success(self, client):
        """登录成功"""
        # 先注册
        client.post('/api/auth/register', json={
            'email': 'login@test.com',
            'password': 'password123',
            'name': '登录用户',
            'role': 'intern',
            'department': '技术部',
            'position': '前端'
        })
        
        # 登录
        response = client.post('/api/auth/login', json={
            'email': 'login@test.com',
            'password': 'password123'
        })
        assert response.status_code == 200
        assert 'token' in response.json
    
    def test_login_wrong_password(self, client):
        """密码错误登录失败"""
        response = client.post('/api/auth/login', json={
            'email': 'nonexist@test.com',
            'password': 'wrong'
        })
        assert response.status_code == 401
```

### 3.1.2 实习生接口测试

```python
class TestInternAPI:
    """实习生 API 集成测试"""
    
    def test_get_growth_twin(self, client, auth_headers):
        """获取 Growth Twin 数据"""
        response = client.get('/api/intern/growth-twin/1', headers=auth_headers)
        assert response.status_code == 200
        data = response.json
        assert 'level' in data
        assert 'xp' in data
        assert 'radar_chart' in data
        assert 'skill_tree' in data
    
    def test_get_growth_map(self, client, auth_headers):
        """获取成长分析页面（合并原成长地图和AI分析）"""
        response = client.get('/intern/growth-map', headers=auth_headers)
        assert response.status_code == 200
        # 包含阶段概览、转正预测、优势分析、六维雷达、技能树、AI对话框
    
    def test_ai_chat(self, client, auth_headers):
        """测试AI对话功能（DeepSeek API）"""
        response = client.post('/api/intern/ai-chat', 
            headers=auth_headers,
            json={'question': '如何提升技术能力？'}
        )
        assert response.status_code == 200
        assert 'response' in response.json
        # 验证返回的是真实AI回复而非模板
    
    def test_get_tasks(self, client, auth_headers):
        """获取任务列表"""
        response = client.get('/api/intern/tasks/1', headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json, list)
    
    def test_get_task_detail(self, client, auth_headers):
        """获取任务详情"""
        response = client.get('/intern/tasks/1', headers=auth_headers)
        assert response.status_code == 200
        # 包含任务信息、提交区、推荐任务
    
    def test_submit_task(self, client, auth_headers):
        """提交任务内容"""
        response = client.post('/intern/tasks/1/submit', 
            headers=auth_headers,
            data={'content': '任务完成代码'}
        )
        assert response.status_code == 302  # 重定向
    
    def test_complete_task(self, client, auth_headers):
        """完成任务"""
        response = client.post('/intern/tasks/1/complete', headers=auth_headers)
        assert response.status_code == 302  # 重定向
    
    def test_get_weekly_journal(self, client, auth_headers):
        """获取统一周记视图"""
        response = client.get('/intern/weekly-journal', headers=auth_headers)
        assert response.status_code == 200
        # 包含周报和反馈按周分组
    
    def test_submit_weekly_report(self, client, auth_headers):
        """提交周报"""
        response = client.post('/intern/weekly-report', 
            headers=auth_headers,
            data={
                'week_number': 1,
                'content': '本周完成了登录模块开发',
                'self_rating': 4
            }
        )
        assert response.status_code == 302  # 重定向
    
    def test_edit_weekly_report(self, client, auth_headers):
        """编辑周报"""
        response = client.post('/intern/weekly-report/1/edit', 
            headers=auth_headers,
            data={
                'content': '更新后的周报内容',
                'self_rating': 5
            }
        )
        assert response.status_code == 302  # 重定向
    
    def test_get_score_history(self, client, auth_headers):
        """获取评分历史"""
        response = client.get('/intern/score-history', headers=auth_headers)
        assert response.status_code == 200
        # 包含当前评分和历史记录
    
    def test_get_feedbacks(self, client, auth_headers):
        """获取反馈列表"""
        response = client.get('/intern/feedback', headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json, list)
```

### 3.1.3 导师接口测试

```python
class TestMentorAPI:
    """导师 API 集成测试"""
    
    def test_get_dashboard(self, client, mentor_headers):
        """获取导师驾驶舱数据"""
        response = client.get('/api/mentor/dashboard', headers=mentor_headers)
        assert response.status_code == 200
        data = response.json
        assert 'interns' in data
        assert 'stats' in data
        assert 'todos' in data
    
    def test_give_feedback(self, client, mentor_headers):
        """给予反馈"""
        response = client.post('/api/mentor/feedback', 
            headers=mentor_headers,
            json={
                'intern_id': 1,
                'type': 'weekly',
                'content': '本周表现优秀',
                'rating': 4,
                'dimension_scores': {
                    'technical': 75,
                    'communication': 80,
                    'business': 60,
                    'initiative': 70,
                    'problem_solving': 65,
                    'engineering': 55
                }
            }
        )
        assert response.status_code == 201
    
    def test_assign_task(self, client, mentor_headers):
        """分配任务"""
        response = client.post('/api/mentor/tasks', 
            headers=mentor_headers,
            json={
                'intern_id': 1,
                'title': '完成登录模块',
                'description': '实现用户登录功能',
                'difficulty': 3,
                'xp_reward': 100,
                'due_date': '2026-06-20'
            }
        )
        assert response.status_code == 201
```

### 3.1.4 HR 接口测试

```python
class TestHR_API:
    """HR API 集成测试"""
    
    def test_get_dashboard(self, client, hr_headers):
        """获取 HR 看板数据"""
        response = client.get('/api/hr/dashboard', headers=hr_headers)
        assert response.status_code == 200
        data = response.json
        assert 'total_interns' in data
        assert 'avg_level' in data
        assert 'risk_count' in data
    
    def test_get_talent_pool(self, client, hr_headers):
        """获取人才池"""
        response = client.get('/api/hr/talent-pool', headers=hr_headers)
        assert response.status_code == 200
        assert isinstance(response.json, list)
    
    def test_get_risk_alerts(self, client, hr_headers):
        """获取风险预警"""
        response = client.get('/api/hr/risk-alerts', headers=hr_headers)
        assert response.status_code == 200
        assert isinstance(response.json, list)
```

---

## 3.2 数据库集成测试

```python
class TestDatabaseIntegration:
    """数据库集成测试"""
    
    def test_user_crud(self, db_session):
        """用户增删改查"""
        user = User(
            email="test@test.com",
            password_hash="hashed",
            name="测试",
            role=UserRole.INTERN,
            department="技术部",
            position="前端"
        )
        db_session.add(user)
        db_session.commit()
        
        found = db_session.query(User).filter_by(email="test@test.com").first()
        assert found is not None
        assert found.name == "测试"
    
    def test_intern_profile_creation(self, db_session):
        """实习生档案创建"""
        # 创建用户
        user = User(email="intern@test.com", ...)
        db_session.add(user)
        db_session.commit()
        
        # 创建档案
        profile = InternProfile(
            user_id=user.id,
            start_date=date.today(),
            level=Level(1),
            xp=ExperiencePoints(0),
            status=InternStatus.ACTIVE
        )
        db_session.add(profile)
        db_session.commit()
        
        assert profile.id is not None
    
    def test_skill_scores_batch_update(self, db_session):
        """六维评分批量更新"""
        scores = [
            SkillScore(intern_id=1, dimension_id=1, score=Score(75)),
            SkillScore(intern_id=1, dimension_id=2, score=Score(80)),
            SkillScore(intern_id=1, dimension_id=3, score=Score(60)),
            SkillScore(intern_id=1, dimension_id=4, score=Score(70)),
            SkillScore(intern_id=1, dimension_id=5, score=Score(65)),
            SkillScore(intern_id=1, dimension_id=6, score=Score(55)),
        ]
        db_session.add_all(scores)
        db_session.commit()
        
        result = db_session.query(SkillScore).filter_by(intern_id=1).all()
        assert len(result) == 6
```

---

# 4. E2E 测试

## 4.1 实习生完整成长流程测试

```python
class TestInternGrowthE2E:
    """实习生成长完整流程 E2E 测试"""
    
    def test_complete_growth_flow(self, client):
        """完整的成长流程：注册 → 登录 → 完成任务 → 查看周记 → 获得反馈"""
        
        # 1. 注册实习生
        register_resp = client.post('/api/auth/register', json={
            'email': 'e2e_intern@test.com',
            'password': 'password123',
            'name': 'E2E实习生',
            'role': 'intern',
            'department': '技术部',
            'position': '前端'
        })
        assert register_resp.status_code == 201
        intern_id = register_resp.json['user_id']
        
        # 2. 登录
        login_resp = client.post('/api/auth/login', json={
            'email': 'e2e_intern@test.com',
            'password': 'password123'
        })
        assert login_resp.status_code == 200
        token = login_resp.json['token']
        headers = {'Authorization': f'Bearer {token}'}
        
        # 3. 查看 Growth Twin（初始状态）
        twin_resp = client.get(f'/api/intern/growth-twin/{intern_id}', headers=headers)
        assert twin_resp.status_code == 200
        assert twin_resp.json['level'] == 1
        assert twin_resp.json['xp'] == 0
        
        # 4. 查看任务列表
        tasks_resp = client.get('/intern/tasks', headers=headers)
        assert tasks_resp.status_code == 200
        
        # 5. 查看任务详情
        task_detail_resp = client.get('/intern/tasks/1', headers=headers)
        assert task_detail_resp.status_code == 200
        
        # 6. 提交任务内容
        submit_resp = client.post('/intern/tasks/1/submit', 
            headers=headers,
            data={'content': '任务完成代码'}
        )
        assert submit_resp.status_code == 302
        
        # 7. 完成任务
        complete_resp = client.post('/intern/tasks/1/complete', headers=headers)
        assert complete_resp.status_code == 302
        
        # 8. 提交周报
        report_resp = client.post('/intern/weekly-report', 
            headers=headers,
            data={
                'week_number': 1,
                'content': '本周完成了任务开发',
                'self_rating': 4
            }
        )
        assert report_resp.status_code == 302
        
        # 9. 查看统一周记视图
        journal_resp = client.get('/intern/weekly-journal', headers=headers)
        assert journal_resp.status_code == 200
        
        # 10. 查看更新后的 Growth Twin
        twin_resp = client.get(f'/api/intern/growth-twin/{intern_id}', headers=headers)
        assert twin_resp.json['xp'] > 0
```

## 4.2 导师带教流程测试

```python
class TestMentorFlowE2E:
    """导师带教流程 E2E 测试"""
    
    def test_mentor_complete_flow(self, client):
        """完整流程：登录 → 查看团队 → 分配任务 → 写反馈"""
        
        # 1. 导师登录
        # 2. 查看驾驶舱
        # 3. 查看实习生详情
        # 4. 分配任务
        # 5. 批阅周报
        # 6. 写反馈
        # 7. 使用 AI Copilot
        pass
```

## 4.3 HR 管理流程测试

```python
class TestHRFlowE2E:
    """HR 管理流程 E2E 测试"""
    
    def test_hr_complete_flow(self, client):
        """完整流程：登录 → 查看看板 → 查看风险 → 处理风险"""
        
        # 1. HR 登录
        # 2. 查看全局看板
        # 3. 查看风险预警
        # 4. 处理风险项
        # 5. 查看人才池
        # 6. 查看部门对比
        # 7. 查看 AI 洞察
        pass
```

---

# 5. 测试数据管理

## 5.1 测试数据工厂

```python
class TestDataFactory:
    """测试数据工厂"""
    
    @staticmethod
    def create_intern(name="测试实习生", level=1, xp=0):
        """创建测试实习生"""
        return {
            'email': f'{name}@test.com',
            'password': 'password123',
            'name': name,
            'role': 'intern',
            'department': '技术部',
            'position': '前端'
        }
    
    @staticmethod
    def create_mentor(name="测试导师"):
        """创建测试导师"""
        return {
            'email': f'{name}@test.com',
            'password': 'password123',
            'name': name,
            'role': 'mentor',
            'department': '技术部',
            'position': '前端'
        }
    
    @staticmethod
    def create_task(title="测试任务", difficulty=3, xp_reward=100):
        """创建测试任务"""
        return {
            'title': title,
            'description': '测试任务描述',
            'category': 'technical',
            'difficulty': difficulty,
            'xp_reward': xp_reward
        }
    
    @staticmethod
    def create_dimension_scores(technical=75, communication=80, 
                                 business=60, initiative=70,
                                 problem_solving=65, engineering=55):
        """创建六维评分"""
        return {
            'technical': technical,
            'communication': communication,
            'business': business,
            'initiative': initiative,
            'problem_solving': problem_solving,
            'engineering': engineering
        }
    
    @staticmethod
    def create_score_history(dimension_id=1, score=75, change_reason='导师评估'):
        """创建评分历史"""
        return {
            'dimension_id': dimension_id,
            'score': score,
            'change_reason': change_reason
        }
```

## 5.2 Fixtures

```python
@pytest.fixture
def test_intern(client):
    """测试实习生 fixture"""
    resp = client.post('/api/auth/register', json=TestDataFactory.create_intern())
    return resp.json

@pytest.fixture
def test_mentor(client):
    """测试导师 fixture"""
    resp = client.post('/api/auth/register', json=TestDataFactory.create_mentor())
    return resp.json

@pytest.fixture
def auth_headers(client, test_intern):
    """认证头 fixture"""
    resp = client.post('/api/auth/login', json={
        'email': test_intern['email'],
        'password': 'password123'
    })
    return {'Authorization': f'Bearer {resp.json["token"]}'}

@pytest.fixture
def mentor_headers(client, test_mentor):
    """导师认证头 fixture"""
    resp = client.post('/api/auth/login', json={
        'email': test_mentor['email'],
        'password': 'password123'
    })
    return {'Authorization': f'Bearer {resp.json["token"]}'}
```

---

# 6. 测试覆盖率目标

| 模块 | 目标覆盖率 | 说明 |
|------|------------|------|
| 值对象 | 100% | 所有值对象必须全覆盖 |
| 领域服务 | 95% | 核心业务逻辑必须全覆盖 |
| API 路由 | 90% | 所有接口必须有测试 |
| 数据库操作 | 80% | 关键 CRUD 必须覆盖 |
| 前端页面 | N/A | 由手动测试覆盖 |

---

# 7. 测试执行命令

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行 E2E 测试
pytest tests/e2e/

# 运行并生成覆盖率报告
pytest --cov=app --cov-report=html

# 运行特定测试文件
pytest tests/unit/test_level.py

# 运行特定测试类
pytest tests/unit/test_level.py::TestLevel

# 运行特定测试方法
pytest tests/unit/test_level.py::TestLevel::test_level_min_value
```

