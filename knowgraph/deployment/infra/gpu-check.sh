#!/bin/bash
# =============================================================================
# 学知图谱 — GPU 驱动验证脚本
# 验证 4×4090 服务器是否满足部署条件
# Usage: bash infra/gpu-check.sh
# =============================================================================

set -e

echo "╔══════════════════════════════════════════════╗"
echo "║  学知图谱 — GPU 驱动验证                     ║"
echo "║  Target: 4× NVIDIA RTX 4090                  ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Color helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_pass() { echo -e "  ${GREEN}✓${NC} $1"; }
check_fail() { echo -e "  ${RED}✗${NC} $1"; }
check_warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }

FAIL_COUNT=0

# =========================================================================
# 1. NVIDIA Driver
# =========================================================================
echo "━━━ 1. NVIDIA 驱动 ━━━"
if command -v nvidia-smi &>/dev/null; then
    DRIVER_VER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader | head -1)
    check_pass "nvidia-smi 可用 — 驱动版本: $DRIVER_VER"

    # Check driver >= 525 (required for CUDA 12)
    MAJOR_VER=$(echo "$DRIVER_VER" | cut -d. -f1)
    if [ "$MAJOR_VER" -ge 525 ]; then
        check_pass "驱动版本 >= 525 (满足 CUDA 12 要求)"
    else
        check_fail "驱动版本过低，需要 >= 525"
        ((FAIL_COUNT++))
    fi
else
    check_fail "nvidia-smi 不可用 — NVIDIA 驱动未安装"
    ((FAIL_COUNT++))
fi

# =========================================================================
# 2. GPU 数量与型号
# =========================================================================
echo ""
echo "━━━ 2. GPU 信息 ━━━"
GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
GPU_NAMES=$(nvidia-smi --query-gpu=name --format=csv,noheader | paste -sd ',' -)

echo "  GPU 数量: $GPU_COUNT"
echo "  GPU 型号: $GPU_NAMES"

if [ "$GPU_COUNT" -ge 4 ]; then
    check_pass "GPU 数量 >= 4，满足分区方案要求"
else
    check_warn "GPU 数量: $GPU_COUNT (目标: 4). 将自动降级分区方案"
fi

# Check if all are RTX 4090
NON_4090=$(nvidia-smi --query-gpu=name --format=csv,noheader | grep -v "4090" || true)
if [ -z "$NON_4090" ]; then
    check_pass "所有 GPU 均为 RTX 4090"
else
    check_warn "检测到非 4090 GPU: $NON_4090"
fi

# =========================================================================
# 3. 显存信息
# =========================================================================
echo ""
echo "━━━ 3. 显存信息 ━━━"
TOTAL_VRAM=0
for i in $(seq 0 $((GPU_COUNT - 1))); do
    VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits -i $i | tr -d ' ')
    VRAM_GB=$((VRAM / 1024))
    FREE=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits -i $i | tr -d ' ')
    FREE_GB=$((FREE / 1024))
    echo "  GPU $i: ${VRAM_GB}GB 总显存 / ${FREE_GB}GB 可用"
    TOTAL_VRAM=$((TOTAL_VRAM + VRAM_GB))
done
echo "  总显存: ${TOTAL_VRAM}GB"

if [ "$TOTAL_VRAM" -ge 72 ]; then
    check_pass "总显存 >= 72GB，满足 Whisper + LLM 需求"
else
    check_fail "总显存不足，需要 >= 72GB"
    ((FAIL_COUNT++))
fi

# =========================================================================
# 4. CUDA 版本
# =========================================================================
echo ""
echo "━━━ 4. CUDA 版本 ━━━"
if command -v nvcc &>/dev/null; then
    CUDA_VER=$(nvcc --version | grep "release" | awk '{print $6}' | cut -c2-)
    check_pass "CUDA 版本: $CUDA_VER"
else
    # Check from nvidia-smi
    CUDA_VER=$(nvidia-smi | grep "CUDA Version" | awk '{print $9}')
    check_pass "CUDA 版本 (nvidia-smi): $CUDA_VER (nvcc 未安装，容器内不影响)"
fi

# =========================================================================
# 5. Docker
# =========================================================================
echo ""
echo "━━━ 5. Docker 环境 ━━━"
if command -v docker &>/dev/null; then
    DOCKER_VER=$(docker --version | awk '{print $3}' | tr -d ',')
    check_pass "Docker 可用 — 版本: $DOCKER_VER"
else
    check_fail "Docker 未安装"
    ((FAIL_COUNT++))
fi

# Docker Compose
if docker compose version &>/dev/null; then
    COMPOSE_VER=$(docker compose version --short 2>/dev/null || docker compose version | head -1)
    check_pass "Docker Compose 可用"
else
    check_fail "Docker Compose 不可用"
    ((FAIL_COUNT++))
fi

# =========================================================================
# 6. NVIDIA Container Toolkit
# =========================================================================
echo ""
echo "━━━ 6. NVIDIA Container Toolkit ━━━"
if docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi &>/dev/null; then
    check_pass "nvidia-container-toolkit 正常 — GPU 可传入容器"
else
    check_fail "nvidia-container-toolkit 不可用 — 请执行:"
    echo "          sudo apt install -y nvidia-container-toolkit"
    echo "          sudo nvidia-ctk runtime configure --runtime=docker"
    echo "          sudo systemctl restart docker"
    ((FAIL_COUNT++))
fi

# =========================================================================
# 7. 存储检查
# =========================================================================
echo ""
echo "━━━ 7. 存储空间 ━━━"
DISK_AVAIL=$(df -BG / | awk 'NR==2 {print $4}' | tr -d 'G')
DISK_TOTAL=$(df -BG / | awk 'NR==2 {print $2}' | tr -d 'G')
echo "  根分区: ${DISK_AVAIL}GB 可用 / ${DISK_TOTAL}GB 总"

if [ -d /data ]; then
    DATA_AVAIL=$(df -BG /data 2>/dev/null | awk 'NR==2 {print $4}' | tr -d 'G' || echo "N/A")
    echo "  /data: ${DATA_AVAIL}GB 可用"
fi

# =========================================================================
# 8. GPU 分区方案建议
# =========================================================================
echo ""
echo "━━━ 8. GPU 分区方案建议 ━━━"
echo ""
echo "   ┌─────────┬──────────────────────┬──────────────┐"
echo "   │  GPU    │  服务                │  预期显存     │"
echo "   ├─────────┼──────────────────────┼──────────────┤"
echo "   │  GPU 0  │  Whisper large-v3    │  ~5-6 GB     │"
echo "   │  GPU 1  │  LLM (Qwen 14B)      │  ~8-10 GB    │"
echo "   │  GPU 2  │  LLM 扩展 / 预留     │  ~8-10 GB    │"
echo "   │  GPU 3  │  缓冲 / 开发调试     │  —           │"
echo "   └─────────┴──────────────────────┴──────────────┘"
echo ""

# =========================================================================
# Summary
# =========================================================================
echo "╔══════════════════════════════════════════════╗"
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo -e "║  ${GREEN}✓ 所有检查通过 — 环境就绪，可以部署${NC}            ║"
else
    echo -e "║  ${RED}✗ ${FAIL_COUNT} 项检查失败 — 请先解决以上问题${NC}            ║"
fi
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "下一步："
echo "  1. 配置环境变量: cp .env.example .env && nano .env"
echo "  2. 一键部署:      bash scripts/deploy.sh"
echo "  3. 启动监控:      docker compose -f infra/monitoring/docker-compose.monitoring.yml up -d"

exit $FAIL_COUNT
