"""
ASR WER Benchmark — Word Error Rate evaluation toolkit for 学知图谱.

Purpose:
    Evaluate Whisper large-v3 transcription accuracy against human-verified
    reference transcripts.  Target WER ≤ 8% for MVP acceptance.

Usage:
    # Generate test manifest from a directory of videos + reference transcripts
    python wer_benchmark.py init --video-dir ./videos --ref-dir ./references

    # Run WER evaluation on a specific model
    python wer_benchmark.py evaluate --model whisper-large-v3 --manifest manifest.json

    # Generate WER report
    python wer_benchmark.py report --results results.json --output wer_report.md

Test Set Design (5 categories, 4 samples each = 20 total):
    ┌─────────────────────┬──────────────────────────────────┐
    │ Category            │ Description                       │
    ├─────────────────────┼──────────────────────────────────┤
    │ native_mandarin     │ Clear standard Mandarin           │
    │ accented_mandarin   │ Regional accents (Sichuan/Canton) │
    │ mixed_zh_en         │ Chinese + English code-switching  │
    │ fast_speech         │ Rapid speech (>200 chars/min)     │
    │ noisy_background    │ Moderate background noise (-15dB) │
    └─────────────────────┴──────────────────────────────────┘
"""
import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ──────────────────────────────────────────────
# Data Structures
# ──────────────────────────────────────────────
@dataclass
class TestSample:
    """A single test sample for WER evaluation."""

    id: str
    category: str  # one of: native_mandarin, accented_mandarin, mixed_zh_en, fast_speech, noisy_background
    video_path: str
    reference_transcript: str
    duration_seconds: float
    description: str
    expected_result: Optional[str] = None  # set after evaluation
    wer: Optional[float] = None  # set after evaluation


@dataclass
class WERManifest:
    """Collection of test samples forming the WER benchmark."""

    name: str = "学知图谱-ASR-WER-Benchmark"
    version: str = "1.0.0"
    target_wer: float = 0.08  # 8%
    samples: list[TestSample] = field(default_factory=list)


# ──────────────────────────────────────────────
# WER Calculation
# ──────────────────────────────────────────────
def char_error_rate(reference: str, hypothesis: str) -> float:
    """
    Calculate Character Error Rate (CER) — preferred for Chinese.
    Uses Levenshtein distance on character level.

    CER = (Substitutions + Insertions + Deletions) / N_reference
    """
    ref_chars = list(reference.replace(" ", ""))
    hyp_chars = list(hypothesis.replace(" ", ""))

    n = len(ref_chars)
    m = len(hyp_chars)

    # DP matrix
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref_chars[i - 1] == hyp_chars[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,       # deletion
                dp[i][j - 1] + 1,       # insertion
                dp[i - 1][j - 1] + cost  # substitution
            )

    distance = dp[n][m]
    return distance / max(n, 1)


def word_error_rate(reference: str, hypothesis: str) -> float:
    """
    Calculate Word Error Rate (WER) — used for English/mixed content.
    """
    ref_words = reference.split()
    hyp_words = hypothesis.split()

    n = len(ref_words)
    m = len(hyp_words)

    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = 0 if ref_words[i - 1] == hyp_words[j - 1] else 1
            dp[i][j] = min(
                dp[i - 1][j] + 1,
                dp[i][j - 1] + 1,
                dp[i - 1][j - 1] + cost,
            )

    distance = dp[n][m]
    return distance / max(n, 1)


# ──────────────────────────────────────────────
# Test Manifest Generation
# ──────────────────────────────────────────────
SAMPLE_MANIFEST_TEMPLATE: list[dict] = [
    # ── Category 1: Native Mandarin (clear, standard) ──
    {
        "id": "native_01",
        "category": "native_mandarin",
        "video_path": "videos/native_mandarin/lecture_cs_basics.mp4",
        "duration_seconds": 120,
        "description": "Standard Mandarin CS lecture, clear pronunciation, quiet environment",
        "reference_transcript": "今天我们来学习计算机科学的基础知识。计算机由硬件和软件两部分组成，硬件包括CPU、内存和存储设备，软件则包括操作系统和应用程序。",
    },
    {
        "id": "native_02",
        "category": "native_mandarin",
        "video_path": "videos/native_mandarin/history_lecture.mp4",
        "duration_seconds": 90,
        "description": "History lecture in standard Mandarin",
        "reference_transcript": "唐朝是中国历史上最强盛的朝代之一，当时的都城长安是世界上最繁华的都市，吸引了来自各国的商人和学者。",
    },
    {
        "id": "native_03",
        "category": "native_mandarin",
        "video_path": "videos/native_mandarin/math_tutorial.mp4",
        "duration_seconds": 150,
        "description": "Mathematics tutorial with formula explanations",
        "reference_transcript": "微积分的基本思想是研究变化率，导数描述了函数在某一点的变化速度，而积分则计算了函数在区间上的累积效应。",
    },
    {
        "id": "native_04",
        "category": "native_mandarin",
        "video_path": "videos/native_mandarin/literature_course.mp4",
        "duration_seconds": 110,
        "description": "Literature analysis in standard Mandarin",
        "reference_transcript": "《红楼梦》是中国古典文学的巅峰之作，曹雪芹通过贾宝玉和林黛玉的爱情故事，展现了封建社会的兴衰和人性的复杂。",
    },
    # ── Category 2: Accented Mandarin ──
    {
        "id": "accent_01",
        "category": "accented_mandarin",
        "video_path": "videos/accented_mandarin/sichuan_lecture.mp4",
        "duration_seconds": 100,
        "description": "Sichuan-accented Mandarin lecture",
        "reference_transcript": "四川盆地位于中国西南部，气候温和湿润，物产丰富，被称为天府之国，是中国重要的农业和工业基地。",
    },
    {
        "id": "accent_02",
        "category": "accented_mandarin",
        "video_path": "videos/accented_mandarin/cantonese_mandarin.mp4",
        "duration_seconds": 95,
        "description": "Cantonese-accented Mandarin",
        "reference_transcript": "粤港澳大湾区是中国经济最发达的地区之一，包括香港、澳门和广东九个城市，总人口超过七千万。",
    },
    {
        "id": "accent_03",
        "category": "accented_mandarin",
        "video_path": "videos/accented_mandarin/dongbei_lecture.mp4",
        "duration_seconds": 85,
        "description": "Northeastern-accented Mandarin",
        "reference_transcript": "东北三省是中国的老工业基地，近年来正在进行产业转型，发展高新技术产业和现代服务业。",
    },
    {
        "id": "accent_04",
        "category": "accented_mandarin",
        "video_path": "videos/accented_mandarin/hunan_lecture.mp4",
        "duration_seconds": 105,
        "description": "Hunan-accented Mandarin lecture",
        "reference_transcript": "湖南的文化底蕴深厚，岳麓书院是中国古代四大书院之一，培养了大批杰出人才。",
    },
    # ── Category 3: Mixed Chinese-English ──
    {
        "id": "mixed_01",
        "category": "mixed_zh_en",
        "video_path": "videos/mixed_zh_en/ai_tutorial.mp4",
        "duration_seconds": 130,
        "description": "AI tutorial with frequent English technical terms",
        "reference_transcript": "Transformer模型的核心是self-attention机制，它允许模型在处理sequence时，关注到输入的所有位置之间的关系，这比传统的RNN和LSTM有更好的并行性。",
    },
    {
        "id": "mixed_02",
        "category": "mixed_zh_en",
        "video_path": "videos/mixed_zh_en/programming_lesson.mp4",
        "duration_seconds": 140,
        "description": "Programming lesson mixing Chinese with English code terms",
        "reference_transcript": "在Python中，我们可以使用decorator来修改函数的行为，这是一种典型的aspect-oriented programming的思想，可以让你在不修改原有代码的情况下增加功能。",
    },
    {
        "id": "mixed_03",
        "category": "mixed_zh_en",
        "video_path": "videos/mixed_zh_en/business_english.mp4",
        "duration_seconds": 115,
        "description": "Business lecture with English terminology",
        "reference_transcript": "SWOT分析是strategic management中最基本的工具之一，通过评估strengths、weaknesses、opportunities和threats来制定企业战略。",
    },
    {
        "id": "mixed_04",
        "category": "mixed_zh_en",
        "video_path": "videos/mixed_zh_en/biology_lecture.mp4",
        "duration_seconds": 125,
        "description": "Biology lecture mixing Chinese with Latin/scientific terms",
        "reference_transcript": "CRISPR-Cas9技术是gene editing领域的革命性突破，它利用guide RNA来定位目标DNA序列，然后通过Cas9蛋白进行精确切割。",
    },
    # ── Category 4: Fast Speech ──
    {
        "id": "fast_01",
        "category": "fast_speech",
        "video_path": "videos/fast_speech/rapid_lecture.mp4",
        "duration_seconds": 80,
        "description": "Rapid lecture (~250 chars/min)",
        "reference_transcript": "量子力学的核心在于波粒二象性，微观粒子既表现出粒子的特性也表现出波动的特性，海森堡不确定性原理指出我们无法同时精确测量粒子的位置和动量。",
    },
    {
        "id": "fast_02",
        "category": "fast_speech",
        "video_path": "videos/fast_speech/debate_clip.mp4",
        "duration_seconds": 60,
        "description": "Fast-paced debate excerpt",
        "reference_transcript": "我认为人工智能的发展必须受到伦理约束，不能为了技术进步而忽视对人类基本权利的保障，我们需要建立一个全球性的AI治理框架。",
    },
    {
        "id": "fast_03",
        "category": "fast_speech",
        "video_path": "videos/fast_speech/news_broadcast.mp4",
        "duration_seconds": 75,
        "description": "News broadcast at fast pace (~230 chars/min)",
        "reference_transcript": "今天的主要新闻有，国务院发布了关于促进数字经济发展的指导意见，央行宣布降低存款准备金率以支持实体经济发展，国际方面联合国大会通过了气候变化新决议。",
    },
    {
        "id": "fast_04",
        "category": "fast_speech",
        "video_path": "videos/fast_speech/ted_style_talk.mp4",
        "duration_seconds": 90,
        "description": "TED-style rapid talk",
        "reference_transcript": "创新的本质不是发明全新的东西，而是将已有的技术以新的方式组合起来，创造性地解决人们真正关心的问题，这才是创新的核心驱动力。",
    },
    # ── Category 5: Noisy Background ──
    {
        "id": "noisy_01",
        "category": "noisy_background",
        "video_path": "videos/noisy_background/classroom_recording.mp4",
        "duration_seconds": 100,
        "description": "Classroom recording with ambient noise (-15dB SNR)",
        "reference_transcript": "同学们请注意，下周的期中考试范围包括第一章到第五章的所有内容，重点复习第三章的函数和第四章的导数部分。",
    },
    {
        "id": "noisy_02",
        "category": "noisy_background",
        "video_path": "videos/noisy_background/coffee_shop_lecture.mp4",
        "duration_seconds": 110,
        "description": "Lecture recorded in coffee shop environment",
        "reference_transcript": "用户体验设计的核心原则是以人为本，我们需要通过用户研究来理解用户的需求、目标和痛点，然后通过迭代设计来不断优化产品。",
    },
    {
        "id": "noisy_03",
        "category": "noisy_background",
        "video_path": "videos/noisy_background/outdoor_interview.mp4",
        "duration_seconds": 85,
        "description": "Outdoor interview with wind noise",
        "reference_transcript": "这个项目对我们团队来说是一个巨大的挑战，但我们有信心在规定时间内完成任务，因为我们已经做了充分的前期准备和风险评估。",
    },
    {
        "id": "noisy_04",
        "category": "noisy_background",
        "video_path": "videos/noisy_background/conference_talk.mp4",
        "duration_seconds": 120,
        "description": "Conference talk with audience murmur",
        "reference_transcript": "根据我们的研究数据，采用新的教学方法后，学生的平均成绩提高了百分之十五，学习积极性也有显著提升，这证明了教学改革的必要性和有效性。",
    },
]


# ──────────────────────────────────────────────
# CLI Interface
# ──────────────────────────────────────────────
def cmd_init(args):
    """Initialize a WER test manifest from a template."""
    manifest = WERManifest()
    for sample_dict in SAMPLE_MANIFEST_TEMPLATE:
        manifest.samples.append(TestSample(**sample_dict))

    output_path = args.output or "wer_manifest.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "name": manifest.name,
                "version": manifest.version,
                "target_wer": manifest.target_wer,
                "samples": [
                    {k: v for k, v in s.__dict__.items()}
                    for s in manifest.samples
                ],
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"✅ WER manifest written to {output_path}")
    print(f"   Total samples: {len(manifest.samples)}")
    categories = {}
    for s in manifest.samples:
        categories[s.category] = categories.get(s.category, 0) + 1
    for cat, count in categories.items():
        print(f"   - {cat}: {count} samples")


def cmd_evaluate(args):
    """Run WER evaluation (placeholder — integrated with actual Whisper pipeline)."""
    print("⚠️  WER evaluation requires a running Whisper service.")
    print("   Integration points:")
    print("   1. Load manifest from", args.manifest)
    print("   2. For each sample: transcribe → compare with reference → compute CER/WER")
    print("   3. Output results to", args.output or "wer_results.json")
    print()
    print("   Example integration code:")
    print("   ```python")
    print("   from wer_benchmark import char_error_rate, word_error_rate, WERManifest")
    print("   manifest = WERManifest.from_json(args.manifest)")
    print("   results = []")
    print("   for sample in manifest.samples:")
    print("       hypothesis = whisper_service.transcribe(sample.video_path)")
    print("       cer = char_error_rate(sample.reference_transcript, hypothesis)")
    print("       results.append({...})")
    print("   ```")


def cmd_report(args):
    """Generate WER report from evaluation results."""
    with open(args.results, "r", encoding="utf-8") as f:
        results = json.load(f)

    lines = [
        "# 📊 ASR WER Benchmark Report",
        "",
        f"**Target WER:** ≤ 8%",
        f"**Samples evaluated:** {len(results.get('results', []))}",
        "",
        "## Per-Category Summary",
        "",
        "| Category | Samples | Avg WER | Min WER | Max WER | Pass (≤8%) |",
        "|----------|---------|---------|---------|---------|------------|",
    ]

    by_category = {}
    for r in results.get("results", []):
        cat = r["category"]
        by_category.setdefault(cat, []).append(r["wer"])

    overall_wers = []
    for cat, wers in sorted(by_category.items()):
        avg = sum(wers) / len(wers)
        overall_wers.extend(wers)
        passed = sum(1 for w in wers if w <= 0.08)
        lines.append(
            f"| {cat} | {len(wers)} | {avg:.2%} | {min(wers):.2%} | {max(wers):.2%} | {passed}/{len(wers)} |"
        )

    overall_avg = sum(overall_wers) / len(overall_wers) if overall_wers else 0
    overall_pass = sum(1 for w in overall_wers if w <= 0.08)
    lines.extend([
        "",
        f"## Overall",
        f"- **Average WER:** {overall_avg:.2%}",
        f"- **Pass rate:** {overall_pass}/{len(overall_wers)} ({overall_pass/len(overall_wers):.1%})" if overall_wers else "- **Pass rate:** N/A",
        f"- **Verdict:** {'✅ PASS' if overall_avg <= 0.08 else '❌ FAIL' if overall_wers else '⚠️ No data'}",
    ])

    report = "\n".join(lines)
    output_path = args.output or "wer_report.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ Report written to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="ASR WER Benchmark for 学知图谱"
    )
    subparsers = parser.add_subparsers(dest="command")

    # init
    p_init = subparsers.add_parser("init", help="Generate WER test manifest")
    p_init.add_argument("--output", help="Output JSON path")

    # evaluate
    p_eval = subparsers.add_parser("evaluate", help="Run WER evaluation")
    p_eval.add_argument("--manifest", default="wer_manifest.json")
    p_eval.add_argument("--model", default="whisper-large-v3")
    p_eval.add_argument("--output", help="Results JSON path")

    # report
    p_report = subparsers.add_parser("report", help="Generate WER report")
    p_report.add_argument("--results", default="wer_results.json")
    p_report.add_argument("--output", help="Report output path")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "report":
        cmd_report(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
