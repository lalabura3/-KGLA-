'use client';

import Link from 'next/link';
import { ROUTES } from '@/lib/constants';
import { Button, EmptyState } from '@/components/ui';
import { Header } from '@/components/layout';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-white">
      <Header />
      <main className="mx-auto max-w-4xl px-4 py-16 sm:px-6">
        {/* Hero */}
        <section className="text-center">
          <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl">
            视频内容，
            <br />
            <span className="text-indigo-600">转化为知识图谱</span>
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-lg text-gray-500">
            上传视频，自动生成笔记与知识图谱，以图谱视角掌握每一个知识点。
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link href={ROUTES.DASHBOARD}>
              <Button variant="primary" size="lg">
                开始学习
              </Button>
            </Link>
            <Link href={ROUTES.HISTORY}>
              <Button variant="outline" size="lg">
                查看历史
              </Button>
            </Link>
          </div>
        </section>

        {/* Features */}
        <section className="mt-24 grid gap-8 sm:grid-cols-3">
          {[
            { emoji: '🎬', title: '上传视频', desc: '支持多种格式，自动转码与语音识别' },
            { emoji: '📝', title: '智能笔记', desc: 'AI 自动分段摘要，关键帧提取' },
            { emoji: '🕸️', title: '知识图谱', desc: '结构化知识点，可视化关系网络' },
          ].map((f) => (
            <div
              key={f.title}
              className="rounded-xl border border-gray-100 bg-gray-50 p-6 text-center"
            >
              <div className="text-3xl">{f.emoji}</div>
              <h3 className="mt-3 font-semibold text-gray-900">{f.title}</h3>
              <p className="mt-1 text-sm text-gray-500">{f.desc}</p>
            </div>
          ))}
        </section>

        {/* Placeholder for video upload */}
        <section className="mt-16">
          <EmptyState
            icon={<span className="text-4xl">📤</span>}
            title="上传你的第一个视频"
            description="选择视频文件，开始你的知识图谱学习之旅"
            action={{ label: '上传视频', onClick: () => {} }}
          />
        </section>
      </main>
    </div>
  );
}
