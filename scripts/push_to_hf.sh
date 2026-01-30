#!/usr/bin/env bash
# 把当前最新代码推到 Hugging Face Space（先提交到 main，再更新 hf-main 并推送）
set -e
cd "$(dirname "$0")/.."

echo "=== 1. 检查未提交的修改 ==="
if ! git diff --quiet || ! git diff --cached --quiet || [ -n "$(git status --porcelain)" ]; then
  echo "当前有未提交的修改。请先提交到 main："
  echo "  git add -A"
  echo "  git commit -m '你的提交说明'"
  echo "  git push origin main   # 可选：同步到 GitHub"
  echo ""
  read -p "是否现在执行 git add -A && git commit？(y/N) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "请输入 commit message: " msg
    git add -A
    git commit -m "${msg:-Update for HF Spaces}"
  else
    echo "已取消。请先提交后再运行此脚本。"
    exit 1
  fi
fi

echo ""
echo "=== 2. 用当前 main 重建 hf-main（并移除二进制文件）==="
# 备份当前 hf-main 的 ref（可选）
git branch -D hf-main 2>/dev/null || true
git checkout -b hf-main main

FILTER_BRANCH_SQUELCH_WARNING=1 git filter-branch -f --index-filter \
  'git rm -q --cached --ignore-unmatch \
    assets/logo_nus.png \
    assets/logo_sjtu.png \
    assets/screenshot_performance.png \
    assets/screenshot_performance_zh.png \
    assets/screenshot_semantic_scholar.png' -- hf-main

git checkout main
echo ""
echo "=== 3. 推送到 Hugging Face ==="
git push hf hf-main:main --force
echo ""
echo "完成。请到 https://huggingface.co/spaces/yancan/CiteScan 查看构建状态。"
