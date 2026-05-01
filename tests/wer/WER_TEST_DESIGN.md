# ASR WER Benchmark — 测试集设计文档

## 1. 概述

本测试集用于评估 Whisper large-v3 在「学知图谱」项目中的语音识别准确率。目标 WER ≤ 8%。

## 2. 测试集设计

### 2.1 分类维度（5类 × 4样本 = 20个测试样本）

| 类别 | 英文标识 | 描述 | 样本数 |
|------|---------|------|--------|
| 标准普通话 | `native_mandarin` | 清晰标准普通话，安静环境 | 4 |
| 方言口音 | `accented_mandarin` | 四川/广东/东北/湖南口音 | 4 |
| 中英混合 | `mixed_zh_en` | 中文穿插英技术术语/代码 | 4 |
| 快速语速 | `fast_speech` | 语速 > 200字/分钟 | 4 |
| 背景噪音 | `noisy_background` | 教室/咖啡馆/户外等环境噪音 | 4 |

### 2.2 每个样本包含

- 视频片段 (60-150秒)
- 人工校对参考文本
- 标注信息 (口音类型、噪音水平、语速)

## 3. WER 计算方法

### 中文: CER (Character Error Rate)

```
CER = (S + I + D) / N_ref

S = 替换数 (Substitutions)
I = 插入数 (Insertions)
D = 删除数 (Deletions)
N_ref = 参考文本字符数
```

### 中英混合/英文: WER (Word Error Rate)

```
WER = (S + I + D) / N_ref  (以词为单位)
```

## 4. 验收标准

| 指标 | 目标 | 最低可接受 |
|------|------|-----------|
| 整体平均 WER/CER | ≤ 8% | ≤ 10% |
| 标准普通话 | ≤ 5% | ≤ 7% |
| 方言口音 | ≤ 12% | ≤ 15% |
| 中英混合 | ≤ 8% | ≤ 10% |
| 快速语速 | ≤ 10% | ≤ 12% |
| 背景噪音 | ≤ 10% | ≤ 15% |

## 5. 使用方法

```bash
# 1. 生成测试清单
python wer_benchmark.py init --output wer_manifest.json

# 2. 运行评估（需 Whisper 服务就绪）
python wer_benchmark.py evaluate --manifest wer_manifest.json --model whisper-large-v3 --output wer_results.json

# 3. 生成报告
python wer_benchmark.py report --results wer_results.json --output wer_report.md
```

## 6. 数据准备注意事项

- 视频片段应截取连续的自然场景，避免刻意录制
- 参考文本需由至少2人独立校对，不一致处协商确定
- 每个类别建议收集 6-8 个样本，取 4 个入测试集，剩余做 development set
- 方言口音样本需标注具体口音类型和强度等级
