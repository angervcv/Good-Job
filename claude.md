---
name: karpathy-guidelines
description: Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria.
license: MIT
---
# Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes, derived from [Andrej Karpathy&#39;s observations](https://x.com/karpathy/status/2015883857489522876) on LLM coding pitfalls.

**Tradeoff:** These guidelines bias toward caution over speed. No exceptions.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:

```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## 5. Verify Before Push

**Push 前必须本地跑通。**

涉及以下变更时，push 前必须执行 `python -c "from app.main import main"` 验证全部模块导入正确：

- import 语句变更
- 函数重命名/移动
- 数据库结构变更
- 新增/删除模块文件

涉及数据层变更时，额外验证关键函数：
```
python -c "
from data.db.queries import get_or_create_user, get_user_category_progress, get_total_question_count
u = get_or_create_user('_verify_')
print(f'user={u[\"id\"]}, progress={len(get_user_category_progress(u[\"id\"]))} cats, questions={get_total_question_count()}')
"
```

## [附加要求]

* 输出和思考一律使用中文
* 不要过度使用emoji，合理的使用是可以的
* 使用者地区位于中国大陆，类似github的网站和资源可能无法直接访问，需要代理或访问镜像
* pip install使用阿里云镜像
* 以暗猜接口为耻，以认真查阅为荣
  以模糊执行为耻，以寻求确认为荣
  以盲想业务为耻，以人类确认为荣
  以创造接口为耻，以复用现有为荣
  以跳过验证为耻，以主动测试为荣
  以破坏架构为耻，以遵循规范为荣
  以假装理解为耻，以诚实无知为荣
  以盲目修改为耻，以谨慎重构为荣
