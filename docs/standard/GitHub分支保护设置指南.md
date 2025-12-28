# GitHub 分支保护设置指南

## 文档信息

| 项目 | 内容 |
|------|------|
| 文档版本 | v1.0.0 |
| 创建日期 | 2024-12-28 |
| 适用范围 | AI PPTist System 项目 |
| 配套文档 | [分支管理规范](./分支管理规范.md) |

---

## 1. 什么是分支保护

分支保护（Branch Protection）是 GitHub 提供的一项重要功能，用于防止重要分支被意外修改或删除。

### 主要功能

- 🔒 **禁止直接推送**：强制使用 Pull Request
- ✅ **要求代码审查**：至少需要指定人数审查批准
- 🧪 **要求状态检查通过**：CI/CD 测试必须通过
- 📝 **要求对话解决**：PR 必须解决所有对话
- 🔄 **限制可推送人员**：只有特定人员可以推送
- ⏳ **要求时间延迟**：合并前等待指定时间

---

## 2. 主目录分支保护设置

### 2.1 保护 master 分支

#### 步骤：

1. **进入仓库设置页面**

   访问：`https://github.com/domonic18/ai-pptist-system/settings/branches`

2. **点击 "Add branch protection rule"**

   ![添加分支保护规则]

3. **配置 master 分支保护规则**

   ```
   Branch name pattern: master

   ☑️ Protect matching branches (推荐)

   ┌─────────────────────────────────────────────┐
   │ Settings in this section apply to all      │
   │ protected branches in this repository.     │
   └─────────────────────────────────────────────┘
   ```

4. **配置保护选项**

   ```
   ┌────────────────────────────────────────────────────────────┐
   │ 🔒 Branch protection rules                                │
   ├────────────────────────────────────────────────────────────┤
   │                                                             │
   │ ☑️ Require pull request reviews before merging             │
   │    ☑️ Require approvals                                    │
   │       Number of required approving reviews: 1             │
   │    ☑️ Dismiss stale reviews when new commits are pushed   │
   │    ☑️ Require review from CODEOWNERS                      │
   │    ☑️ Restrict who can push to matching branches           │
   │       ✓ People with admin access                          │
   │    ☐ Require review from Code Owners                      │
   │    ☐ Allow specified actors to bypass required reviews    │
   │                                                             │
   │ ☑️ Require status checks to pass before merging           │
   │    Require branches to be up to date before merging:       │
   │       ⦿ The latest version that passes all checks         │
   │    ☑️ Require branches to be up to date before merging    │
   │                                                             │
   │ ☑️ Require conversation resolution before merging         │
   │                                                             │
   │ ☑️ Limit who can push to matching branches                │
   │       ✓ People with admin access                          │
   │       ⦿ People with write access                          │
   │                                                             │
   │ ☐ Do not allow bypassing the above settings               │
   │                                                             │
   │ ☑️ Include administrators                                 │
   │                                                             │
   └────────────────────────────────────────────────────────────┘
   ```

5. **点击 "Create" 或 "Save changes"**

#### 推荐配置：

| 设置项 | 推荐值 | 说明 |
|--------|--------|------|
| **Require PR reviews** | ✅ | 强制使用PR |
| **Required approving reviews** | 1 | 至少1人审查 |
| **Require status checks** | ✅ | CI测试必须通过 |
| **Require branches to be up to date** | ✅ | 必须是最新的 |
| **Require conversation resolution** | ✅ | 必须解决所有讨论 |
| **Limit who can push** | ✅ | 仅管理员可推送 |
| **Include administrators** | ✅ | 管理员也受限制 |

### 2.2 保护 develop 分支

重复上述步骤，为 develop 分支创建保护规则，配置稍有不同：

```
Branch name pattern: develop

☑️ Require pull request reviews before merging
   ☑️ Require approvals
      Number of required approving reviews: 1

☑️ Require status checks to pass before merging
   Require branches to be up to date before merging:
      ⦿ The latest version that passes all checks

☑️ Require conversation resolution before merging

⦿ Limit who can push to matching branches
   ✓ People with admin access
   ⦿ People with write access

☐ Include administrators  ← develop 可以不限制管理员
```

---

## 3. 子模块分支保护设置

### 3.1 保护 integration/ai-pptist 分支

访问：`https://github.com/domonic18/ai-pptist/settings/branches`

配置与主目录 master 类似：

```
Branch name pattern: integration/ai-pptist

☑️ Require pull request reviews before merging
   ☑️ Require approvals
      Number of required approving reviews: 1

☑️ Require status checks to pass before merging

☑️ Require conversation resolution before merging

☑️ Limit who can push to matching branches
   ✓ People with admin access

☑️ Include administrators
```

### 3.2 保护 develop 分支

子模块的 develop 分支保护配置：

```
Branch name pattern: develop

☑️ Require pull request reviews before merging
   ☑️ Require approvals
      Number of required approving reviews: 1

☑️ Require status checks to pass before merging

☐ Require conversation resolution before merging  ← 可选

⦿ Limit who can push to matching branches
   ✓ People with admin access
   ⦿ People with write access
```

### 3.3 保护 master 分支（只读）

子模块的 master 分支用于上游同步，配置为只读：

```
Branch name pattern: master

☑️ Limit who can push to matching branches
   ✓ People with admin access

☑️ Include administrators

其他选项根据需要配置
```

---

## 4. 通过 GitHub API 设置（高级）

### 4.1 使用 GitHub CLI

安装 GitHub CLI：
```bash
# macOS
brew install gh

# Linux
sudo apt install gh

# Windows
winget install --id GitHub.cli
```

登录：
```bash
gh auth login
```

设置分支保护：
```bash
# 主目录 master 分支
gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  /repos/domonic18/ai-pptist-system/branches/master/protection \
  -f required_pull_request_reviews='{
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  }' \
  -f enforce_admins=true \
  -f required_status_checks='{
    "strict": true,
    "contexts": []
  }' \
  -f restrictions='{
    "users": [],
    "teams": ["admins"]
  }' \
  -f allow_force_pushes=false \
  -f allow_deletions=false
```

### 4.2 使用 cURL

```bash
curl -X PUT \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/domonic18/ai-pptist-system/branches/master/protection \
  -d '{
    "required_pull_request_reviews": {
      "required_approving_review_count": 1
    },
    "enforce_admins": true,
    "required_linear_history": true
  }'
```

---

## 5. CODEOWNERS 配置

配合分支保护，可以设置 CODEOWNERS 文件，确保特定文件需要特定人员审查。

### 5.1 创建 CODEOWNERS 文件

在主目录根目录创建 `.github/CODEOWNERS`：

```
# 主目录 CODEOWNERS

# 所有代码默认需要 Maintainer 审查
* @domonic18

# 后端代码需要后端负责人审查
backend/ @backend-lead

# 前端子模块相关需要前端负责人审查
frontend/ @frontend-lead

# API 变更需要架构师审查
backend/app/api/ @architect-lead

# 文档变更可以宽松一些
docs/ @technical-writer
```

### 5.2 子模块 CODEOWNERS

在 `frontend/.github/CODEOWNERS`：

```
# 子模块 CODEOWNERS

# 所有代码默认审查者
* @frontend-lead @frontend-senior

# 组件相关
src/components/ @component-lead

# 服务层
src/services/ @service-lead

# 类型定义
src/types/ @type-lead

# 样式文件
src/assets/styles/ @designer
```

---

## 6. 状态检查集成

### 6.1 配置 CI 状态检查

在分支保护中，可以要求特定的状态检查必须通过：

```
☑️ Require status checks to pass before merging
   ☑️ Require branches to be up to date before merging

   Search for status checks in the last month for this repository:

   ☑️ ci/ci (GitHub Actions)
   ☑️ codecov/patch (Codecov)
   ☑️ codecov/project (Codecov)
```

### 6.2 创建必需的状态检查

在 `.github/workflows/ci.yml` 中：

```yaml
name: CI

on:
  push:
    branches: [ develop, master ]
  pull_request:
    branches: [ develop, master ]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Run tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest tests/

      - name: Check status
        run: echo "All tests passed"
```

---

## 7. 分支保护最佳实践

### 7.1 推荐策略

| 分支 | 保护级别 | 说明 |
|------|----------|------|
| **master** | 🔒🔒🔒 | 最严格，生产环境 |
| **develop** | 🔒🔒 | 较严格，开发主分支 |
| **integration/ai-pptist** | 🔒🔒 | 较严格，集成分支 |
| **feature/*** | 无 | 自由开发 |

### 7.2 配置建议

**生产分支 (master)**：
- ✅ 禁止直接推送
- ✅ 要求PR审查（至少1人）
- ✅ 要求CI测试通过
- ✅ 要求最新代码
- ✅ 要求对话解决
- ✅ 限制推送权限

**开发分支 (develop)**：
- ✅ 禁止直接推送
- ✅ 要求PR审查（至少1人）
- ✅ 要求CI测试通过
- ⚠️ 可选：不要求最新代码（允许合并）
- ⚠️ 可选：不限制管理员

**集成分支 (integration/ai-pptist)**：
- ✅ 禁止直接推送
- ✅ 要求PR审查（至少1人）
- ✅ 要求CI测试通过
- ✅ 限制推送权限

### 7.3 常见问题

**Q: 如何临时禁用分支保护？**

A: 不建议禁用。如果紧急情况：
1. 临时添加人员到例外列表
2. 或使用 "Bypass branch protection" 选项（如果配置了）

**Q: 为什么我的PR不能合并？**

A: 检查以下几点：
- [ ] 是否有足够的审查批准
- [ ] CI测试是否全部通过
- [ ] 是否有未解决的对话
- [ ] 分支是否是最新的

**Q: 如何允许特定的人绕过审查？**

A: 在分支保护设置中：
```
☑️ Allow specified actors to bypass required reviews
   ✓ @senior-developer
   ✓ @tech-lead
```

---

## 8. 团队协作流程

### 8.1 开发流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    开发流程（分支保护启用后）                 │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. 创建功能分支                                              │
│     git checkout -b feature/xxx                              │
│                                                              │
│  2. 开发并提交                                               │
│     git add . && git commit                                  │
│                                                              │
│  3. 推送到远端（无法直接推送到 master/develop）              │
│     git push origin feature/xxx                               │
│                                                              │
│  4. 创建 Pull Request                                        │
│     在 GitHub 上创建 PR: feature/xxx → develop               │
│                                                              │
│  5. 自动检查执行                                             │
│     • CI 自动运行                                            │
│     • 代码风格检查                                            │
│     • 测试执行                                                │
│                                                              │
│  6. 代码审查                                                 │
│     • 至少1人审查                                            │
│     • 提出修改意见                                            │
│     • 开发者修改                                              │
│     • 审查通过                                                │
│                                                              │
│  7. 确认所有检查通过                                         │
│     • CI 全部通过                                            │
│     • 审查全部批准                                            │
│     • 对话全部解决                                            │
│                                                              │
│  8. 合并 PR                                                  │
│     • 点击 "Merge pull request"                              │
│     • 删除功能分支                                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 权限矩阵

| 角色 | 主目录 master | 主目录 develop | 子模块 integration | 子模块 develop |
|------|---------------|---------------|-------------------|---------------|
| **Maintainer** | 审查 + 合并 | 审查 + 合并 | 审查 + 合并 | 审查 + 合并 |
| **Senior Developer** | 审查 | 审查 + 合并 | 审查 | 审查 + 合并 |
| **Developer** | 提交PR | 提交PR | 提交PR | 提交PR |
| **Contributor** | 提交PR | 提交PR | 提交PR | 提交PR |

---

## 9. 监控和审计

### 9.1 查看分支保护状态

```bash
# 使用 GitHub CLI
gh api /repos/domonic18/ai-pptist-system/branches/master/protection

# 查看所有受保护的分支
gh api /repos/domonic18/ai-pptist-system/branches?protected=true
```

### 9.2 审计日志

GitHub 提供了审计日志功能，可以查看：

- 谁修改了分支保护规则
- 谁绕过了保护
- 谁强制推送了代码

访问：`https://github.com/organizations/[org]/settings/audit-log`

---

## 10. 检查清单

### 分支保护设置检查清单

**主目录 - master 分支**
- [ ] 禁止直接推送
- [ ] 要求PR审查（至少1人）
- [ ] 要求CI测试通过
- [ ] 要求最新代码
- [ ] 要求对话解决
- [ ] 限制推送权限（仅管理员）

**主目录 - develop 分支**
- [ ] 禁止直接推送
- [ ] 要求PR审查（至少1人）
- [ ] 要求CI测试通过
- [ ] 限制推送权限

**子模块 - integration/ai-pptist 分支**
- [ ] 禁止直接推送
- [ ] 要求PR审查（至少1人）
- [ ] 要求CI测试通过
- [ ] 限制推送权限

**子模块 - develop 分支**
- [ ] 禁止直接推送
- [ ] 要求PR审查（至少1人）
- [ ] 要求CI测试通过

**子模块 - master 分支**
- [ ] 限制推送权限（仅管理员）
- [ ] 配置为只读

---

## 11. 故障排查

### 11.1 常见错误

**错误：Cannot push to master**

```
remote: error: GH006: Protected branch update failed for refs/heads/master.
remote: error: At least 1 approving review is required by models with write access.
```

解决：
1. 创建 PR 而不是直接推送
2. 或临时添加到例外列表（不推荐）

**错误：Required status check "ci/ci" is expected**

解决：
1. 确保 CI 配置正确
2. 等待 CI 完成并通过
3. 或暂时移除该检查（不推荐）

**错误：Branch is not up to date**

解决：
1. 更新分支到最新
2. 合并 master 的最新改动
3. 解决冲突后重新推送

---

## 12. 快速参考

### 12.1 分支保护命令速查

```bash
# 查看分支保护状态
gh api /repos/[owner]/[repo]/branches/[branch]/protection

# 设置分支保护
gh api --method PUT \
  /repos/[owner]/[repo]/branches/[branch]/protection \
  -f required_pull_request_reviews='{"required_approving_review_count":1}'

# 移除分支保护
gh api --method DELETE \
  /repos/[owner]/[repo]/branches/[branch]/protection
```

### 12.2 相关链接

- [GitHub 官方文档 - 分支保护](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches)
- [GitHub 官方文档 - CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-on-github/managing-repository-settings/setting-code-owners-for-your-repository)
- [GitHub 官方文档 - CI](https://docs.github.com/en/actions)

---

## 13. 附录

### 13.1 配置文件示例

**主目录 `.github/CODEOWNERS`**：
```
# 默认审查者
* @domonic18

# 分支特定
# @team-frontend负责前端相关
frontend/ @frontend-lead @frontend-senior

# @team-backend负责后端相关
backend/ @backend-lead @backend-senior

# 文档
docs/ @technical-writer
```

### 13.2 工作流示例

**`.github/workflows/branch-protection.yml`**：
```yaml
name: Branch Protection Check

on:
  pull_request:
    branches: [ master, develop ]

jobs:
  check:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v2

      - name: Check branch protection
        run: |
          echo "Checking branch protection..."

          # 检查是否是从正确的分支拉出
          if [[ "${{ github.base_ref }}" != "develop" && "${{ github.base_ref }}" != "master" ]]; then
            echo "Error: PR must target develop or master"
            exit 1
          fi

          echo "Branch protection check passed!"
```

---

## 14. 变更记录

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| v1.0.0 | 2024-12-28 | 初始版本 | Claude Code |
