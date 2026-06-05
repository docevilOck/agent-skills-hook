# git-commit-standard

本目录提供 git commit / release 规范 skill。该 skill 已按通用仓库工作流重写：默认不写死具体项目路径，而是要求先读取当前仓库的 AGENTS、release 配置、版本文件、固件归档目录和历史提交。

## 依赖

- **`git-commit-template`**（强制）：定义 commit message 的模板、字段和写作风格。加载本 skill 时必须同步加载。

## 文件

```text
git-commit-standard/
├── SKILL.md
├── README.md
└── ../git-commit-template/
    ├── SKILL.md
    └── README.md
```

## 作用

该 skill 用于约束执行 commit 前的版本、日期、修改者、README/changelog 和固件产物归档，重点规则包括：

- 版本来源必须从当前仓库规则中发现，不能写死某个项目路径
- 时间格式沿用仓库历史；若无固定格式使用 `YYYY.MM.DD`
- 修改者来源于 `git config user.name`
- 每完成一个完整可发布闭环，按仓库规则递增 beta/build/release 字段；普通中间提交不强制递增
- 每次执行 commit 相关操作时，只要存在代码改动，不论是 commit 还是 amend，不论是否修改版本号，都必须先重新编译并更新最新固件产物，再同步 README/changelog 总结；这是硬性门禁
- 版本递进和固件产物同步是两个独立门禁；未递进版本、只是 amend、只是 fix 都不能作为跳过固件产物的理由
- amend 如果改动了版本号、版本宏、构建输入、release 配置或产物命名相关内容，必须重新编译固件、刷新当前版本归档产物，并把这些更新一起重新暂存后再 amend
- README/changelog 可能需要汇总多个 commit，而不是只记录当前 commit；若仓库要求一版本一条，同版本改动必须合并到同一版本块，并用二级分点表达独立事项
- 固件产物需要按历史目录和命名规则归档；不同构建宏/变体可能对应不同目录
- 允许仓库维护 `.agents/release-config.md` 或等价文件记录版本源、构建变体、产物目录、changelog 路径和上次 release 边界

## 提交说明

commit message 的模板和书写规范由 `git-commit-template` 定义；加载本 skill 时自动遵循。

仅当用户明确点名 `git-commit-standard`，或 `AGENTS.md` 明确要求标准提交/版本/固件归档时，才调用本 skill；其他情况下不要自动加载。
