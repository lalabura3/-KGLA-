'use client';

import { useRef, useState, useEffect, useCallback, type ReactNode } from 'react';
import { cn } from '@/lib/utils/cn';

interface VideoPlayerProps {
  src?: string;
  poster?: string;
  title?: string;
  className?: string;
  onTimeUpdate?: (currentTime: number) => void;
  onPlay?: () => void;
  onPause?: () => void;
  onEnded?: () => void;
  /** 加载中占位 */
  loadingOverlay?: ReactNode;
  /** 空状态占位 */
  emptyOverlay?: ReactNode;
}

export function VideoPlayer({
  src,
  poster,
  title,
  className,
  onTimeUpdate,
  onPlay,
  onPause,
  onEnded,
  loadingOverlay,
  emptyOverlay,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showControls, setShowControls] = useState(true);
  const [isSeeking, setIsSeeking] = useState(false);
  const controlsTimerRef = useRef<ReturnType<typeof setTimeout>>();

  // ── Format time ──
  const fmt = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, '0')}`;
  };

  // ── Auto-hide controls ──
  const resetControlsTimer = useCallback(() => {
    setShowControls(true);
    if (controlsTimerRef.current) clearTimeout(controlsTimerRef.current);
    controlsTimerRef.current = setTimeout(() => {
      if (isPlaying) setShowControls(false);
    }, 3000);
  }, [isPlaying]);

  useEffect(() => {
    return () => {
      if (controlsTimerRef.current) clearTimeout(controlsTimerRef.current);
    };
  }, []);

  // ── Play/Pause ──
  const togglePlay = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (video.paused) {
      video.play().catch(() => {});
    } else {
      video.pause();
    }
  }, []);

  // ── Seek ──
  const handleSeek = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const bar = progressRef.current;
    const video = videoRef.current;
    if (!bar || !video || !duration) return;
    const rect = bar.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    video.currentTime = pct * duration;
  }, [duration]);

  // ── Volume ──
  const handleVolumeChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseFloat(e.target.value);
    setVolume(v);
    setIsMuted(v === 0);
    if (videoRef.current) videoRef.current.volume = v;
  }, []);

  const toggleMute = useCallback(() => {
    const video = videoRef.current;
    if (!video) return;
    if (isMuted) {
      video.volume = volume || 0.5;
      setIsMuted(false);
    } else {
      video.volume = 0;
      setIsMuted(true);
    }
  }, [isMuted, volume]);

  // ── Fullscreen ──
  const toggleFullscreen = useCallback(async () => {
    const el = containerRef.current;
    if (!el) return;
    if (document.fullscreenElement) {
      await document.exitFullscreen();
    } else {
      await el.requestFullscreen();
    }
  }, []);

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  // ── Keyboard shortcuts ──
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      switch (e.code) {
        case 'Space':
          e.preventDefault();
          togglePlay();
          break;
        case 'KeyF':
          toggleFullscreen();
          break;
        case 'KeyM':
          toggleMute();
          break;
        case 'ArrowRight': {
          const v = videoRef.current;
          if (v) v.currentTime = Math.min(v.currentTime + 10, duration);
          break;
        }
        case 'ArrowLeft': {
          const v = videoRef.current;
          if (v) v.currentTime = Math.max(v.currentTime - 10, 0);
          break;
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [togglePlay, toggleFullscreen, toggleMute, duration]);

  if (!src) {
    return (
      <div
        ref={containerRef}
        className={cn(
          'relative flex items-center justify-center overflow-hidden rounded-xl bg-gradient-to-br from-indigo-50 to-purple-50',
          className,
        )}
        style={{ aspectRatio: '16 / 9' }}
      >
        {emptyOverlay || (
          <div className="text-center">
            <svg className="mx-auto h-16 w-16 text-indigo-200" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 010 1.972l-11.54 6.347a1.125 1.125 0 01-1.667-.986V5.653z" />
            </svg>
            <p className="mt-3 text-sm text-gray-400">暂无视频源</p>
          </div>
        )}
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={cn('group relative overflow-hidden rounded-xl bg-black', className)}
      style={{ aspectRatio: '16 / 9' }}
      onMouseMove={resetControlsTimer}
      onMouseEnter={() => setShowControls(true)}
      onMouseLeave={() => isPlaying && setShowControls(false)}
    >
      {/* ── Video element ── */}
      <video
        ref={videoRef}
        src={src}
        poster={poster}
        className="h-full w-full object-contain"
        preload="metadata"
        onClick={togglePlay}
        onLoadedMetadata={() => {
          const v = videoRef.current;
          if (v) {
            setDuration(v.duration);
            setIsLoaded(true);
            setIsLoading(false);
          }
        }}
        onLoadedData={() => setIsLoading(false)}
        onWaiting={() => setIsLoading(true)}
        onCanPlay={() => setIsLoading(false)}
        onError={() => {
          setError('视频加载失败');
          setIsLoading(false);
        }}
        onTimeUpdate={() => {
          const v = videoRef.current;
          if (v) {
            setCurrentTime(v.currentTime);
            onTimeUpdate?.(v.currentTime);
          }
        }}
        onPlay={() => { setIsPlaying(true); onPlay?.(); }}
        onPause={() => { setIsPlaying(false); onPause?.(); }}
        onEnded={() => { setIsPlaying(false); onEnded?.(); }}
      />

      {/* ── Loading overlay ── */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/40">
          {loadingOverlay || (
            <div className="flex flex-col items-center gap-3">
              <svg className="h-10 w-10 animate-spin text-white" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeDasharray="31.4 31.4" strokeLinecap="round" />
              </svg>
            </div>
          )}
        </div>
      )}

      {/* ── Error overlay ── */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60">
          <div className="text-center">
            <svg className="mx-auto h-10 w-10 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <p className="mt-2 text-sm text-red-300">{error}</p>
          </div>
        </div>
      )}

      {/* ── Center play button (when paused) ── */}
      {!isPlaying && isLoaded && !error && (
        <button
          onClick={togglePlay}
          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white/20 p-5 backdrop-blur-sm transition-transform hover:scale-110"
          aria-label="播放"
        >
          <svg className="h-8 w-8 text-white" viewBox="0 0 24 24" fill="currentColor">
            <path d="M8 5.14v14.72a1 1 0 001.5.86l11-7.36a1 1 0 000-1.72l-11-7.36A1 1 0 008 5.14z" />
          </svg>
        </button>
      )}

      {/* ── Controls bar ── */}
      <div
        className={cn(
          'absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent px-4 pb-3 pt-10 transition-opacity duration-300',
          showControls ? 'opacity-100' : 'opacity-0 pointer-events-none',
        )}
      >
        {/* Progress bar */}
        <div
          ref={progressRef}
          className="group/progress mb-3 cursor-pointer py-1"
          onClick={handleSeek}
        >
          <div className="relative h-1 rounded-full bg-white/30 transition-all group-hover/progress:h-1.5">
            <div
              className="absolute left-0 top-0 h-full rounded-full bg-indigo-400 transition-all"
              style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
            />
            <div
              className="absolute top-1/2 h-3 w-3 -translate-y-1/2 rounded-full bg-white shadow-md opacity-0 transition-opacity group-hover/progress:opacity-100"
              style={{ left: `${duration ? (currentTime / duration) * 100 : 0}%`, marginLeft: '-6px' }}
            />
          </div>
        </div>

        {/* Bottom controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Play/Pause */}
            <button onClick={togglePlay} className="text-white hover:text-indigo-300 transition-colors" aria-label={isPlaying ? '暂停' : '播放'}>
              {isPlaying ? (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                </svg>
              ) : (
                <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M8 5.14v14.72a1 1 0 001.5.86l11-7.36a1 1 0 000-1.72l-11-7.36A1 1 0 008 5.14z" />
                </svg>
              )}
            </button>

            {/* Time */}
            <span className="text-xs text-white/80 font-mono tabular-nums">
              {fmt(currentTime)} / {fmt(duration)}
            </span>
          </div>

          <div className="flex items-center gap-3">
            {/* Volume */}
            <div className="flex items-center gap-1.5 group/vol">
              <button onClick={toggleMute} className="text-white/80 hover:text-white transition-colors" aria-label={isMuted ? '取消静音' : '静音'}>
                {isMuted || volume === 0 ? (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51A8.796 8.796 0 0021 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06a8.99 8.99 0 003.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z" />
                  </svg>
                ) : (
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3A4.5 4.5 0 0014 8.5v7a4.49 4.49 0 002.5-3.5zm2.5 0A7.5 7.5 0 0017 5.07v2.07a5.5 5.5 0 010 9.72v2.07A7.5 7.5 0 0019 12z" />
                  </svg>
                )}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={isMuted ? 0 : volume}
                onChange={handleVolumeChange}
                className="w-0 origin-left scale-x-0 transition-all group-hover/vol:w-20 group-hover/vol:scale-x-100 h-1 accent-indigo-400 cursor-pointer"
                aria-label="音量"
              />
            </div>

            {/* Title (if provided) */}
            {title && (
              <span className="max-w-[200px] truncate text-xs text-white/60 hidden sm:block">
                {title}
              </span>
            )}

            {/* Fullscreen */}
            <button onClick={toggleFullscreen} className="text-white/80 hover:text-white transition-colors" aria-label={isFullscreen ? '退出全屏' : '全屏'}>
              {isFullscreen ? (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z" />
                </svg>
              ) : (
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
