# Semble Offline Bundle

用途：把 `semble` 本地语义索引用到的 Hugging Face 模型整理成可离线分发目录，供上传网盘后在其他机器手工下发，也供本仓库部署脚本按“有模型则部署、无模型则 skip”方式自动检查。

## 模型信息

- Tool: `semble 0.3.3`
- Default model: `minishlab/potion-code-16M`
- Local snapshot source: `C:\Users\hasee\.cache\huggingface\hub\models--minishlab--potion-code-16M\snapshots\86848193a842865570d9c8d3e7d268b66ab52752`
- Main weights file: `model\minishlab--potion-code-16M\model.safetensors`
- SHA256: `CA6159081A6E96CEBE4AD878E5E8437BFCCC761E8DB16223370149CD2FAA6C0B`
- Size: `64299272` bytes

## 目录结构

```text
semble_offline_bundle/
├── README.md
└── model/
    └── minishlab--potion-code-16M/
        ├── config.json
        ├── model.safetensors
        ├── modules.json
        ├── README.md
        ├── tokenizer.json
        └── train.py
```

## 仓库内默认部署行为

- 部署脚本检查仓库内 `semble_offline_bundle/model/minishlab--potion-code-16M/model.safetensors` 是否存在
- 若存在：自动复制到本机 Hugging Face 缓存目录，并写入 `refs/main`
- 若不存在：打印日志并跳过，不中断其他 agent 配置部署

目标缓存路径：

- Windows: `%USERPROFILE%\.cache\huggingface\hub\models--minishlab--potion-code-16M\snapshots\86848193a842865570d9c8d3e7d268b66ab52752`
- Linux: `$HOME/.cache/huggingface/hub/models--minishlab--potion-code-16M/snapshots/86848193a842865570d9c8d3e7d268b66ab52752`

## 推荐分发方式

当前仓库已经内置这份离线模型 bundle，作为共享部署输入。

如果需要给仓库外的机器继续分发，推荐直接复用当前目录内容，不要再拆成新的不一致副本。

推荐把整个 `semble_offline_bundle` 上传到：

- 网盘
- 对象存储
- 制品库
- Release 附件

## 其他机器上的部署方式

### 方式 A：放到 Hugging Face 本地缓存快照目录

目标机建议放到：

`%USERPROFILE%\.cache\huggingface\hub\models--minishlab--potion-code-16M\snapshots\86848193a842865570d9c8d3e7d268b66ab52752`

同时需要保证 `refs\main` 指向该 snapshot 版本。如果目标机没有现成缓存目录，建议直接在目标机先联网运行一次 `semble` 初始化，再用这份目录覆盖对应 snapshot 内容。

### 方式 B：作为显式本地模型目录使用

如果后续工作流允许给 `semble` 传本地模型路径，则直接把：

`model\minishlab--potion-code-16M`

作为 `model_path` 使用，比模拟 HF 缓存更稳。

## 校验

Windows PowerShell：

```powershell
Get-FileHash -Algorithm SHA256 .\model\minishlab--potion-code-16M\model.safetensors
```

返回值应为：

`CA6159081A6E96CEBE4AD878E5E8437BFCCC761E8DB16223370149CD2FAA6C0B`

## 当前结论

- 这份 bundle 已包含 `semble` 默认模型的最小可用文件集合
- 当前未包含 Python 解释器、`semble` 包本体或其依赖轮子
- 当前更适合作为“仓库内离线模型资产包”，不是完整安装包
- 当前仓库部署脚本已支持“检测到 bundle 模型则自动部署，否则打印 skip 日志”
