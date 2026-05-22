# Semble 模型缓存

本目录用于保存 `Semble` 默认模型的 Hugging Face 缓存镜像，供部署脚本离线复用。

## 默认模型

- `minishlab/potion-code-16M`

## 目录结构

部署脚本按 Hugging Face 默认缓存结构查找：

```text
third_party/
  semble/
    huggingface/
      hub/
        models--minishlab--potion-code-16M/
```

需要保留其中的：

- `blobs/`
- `refs/`
- `snapshots/`

部署脚本会把 `blobs/` 视为离线真源。
如果 `snapshots/.../model.safetensors` 是 Git LFS pointer，部署时会自动解析其中的 `oid sha256:...`，
再用对应的 `blobs/<sha256>` 重建真实的 `model.safetensors`，然后再同步到用户缓存。
如果 `blobs/` 中找不到对应实体文件，部署会直接失败，并拒绝覆盖本机 Hugging Face 缓存。

## 导出方式

### Windows

```powershell
.\windows\cache_semble_model.ps1
```

### Linux

```bash
./linux/cache_semble_model.sh
```

导出来源为本机默认缓存目录：

- Windows: `~/.cache/huggingface/hub/models--minishlab--potion-code-16M`
- Linux: `~/.cache/huggingface/hub/models--minishlab--potion-code-16M`

## 说明

- 模型首次联网下载一次即可，后续部署可直接复用仓库中的缓存
- 导出脚本会先校验本机 `snapshot/.../model.safetensors` 是真实二进制文件，不会导出 LFS pointer
- 如果仓库里没有该目录，部署脚本会跳过缓存同步，但仍会继续部署其他配置
