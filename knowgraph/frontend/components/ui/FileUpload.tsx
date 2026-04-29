'use client';

import { cn } from '@/lib/utils/cn';
import { useState, useRef, useCallback, type DragEvent, type ReactNode } from 'react';

interface FileUploadProps {
  accept?: string;
  maxSize?: number; // bytes
  maxFiles?: number;
  multiple?: boolean;
  disabled?: boolean;
  onFilesSelected: (files: File[]) => void;
  className?: string;
  children?: ReactNode;
}

export function FileUpload({
  accept,
  maxSize = 500 * 1024 * 1024, // 500MB default
  maxFiles = 1,
  multiple = false,
  disabled = false,
  onFilesSelected,
  className,
  children,
}: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validate = useCallback(
    (files: File[]): File[] => {
      setError(null);
      if (files.length > maxFiles) {
        setError(`最多上传 ${maxFiles} 个文件`);
        return [];
      }
      const oversized = files.filter((f) => f.size > maxSize);
      if (oversized.length > 0) {
        setError(`文件大小不能超过 ${Math.round(maxSize / 1024 / 1024)}MB`);
        return [];
      }
      return files;
    },
    [maxSize, maxFiles],
  );

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList || disabled) return;
      const files = Array.from(fileList);
      const valid = validate(files);
      if (valid.length > 0) onFilesSelected(valid);
    },
    [disabled, validate, onFilesSelected],
  );

  const handleDrag = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (e.type === 'dragenter' || e.type === 'dragover') {
        setDragActive(true);
      } else if (e.type === 'dragleave') {
        setDragActive(false);
      }
    },
    [],
  );

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (!disabled) handleFiles(e.dataTransfer.files);
    },
    [disabled, handleFiles],
  );

  return (
    <div className={cn('w-full', className)}>
      <div
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="点击或拖拽文件上传"
        className={cn(
          'relative flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition-all',
          dragActive
            ? 'border-primary-500 bg-primary-50'
            : 'border-gray-300 bg-gray-50 hover:border-primary-400 hover:bg-primary-50/50',
          disabled && 'cursor-not-allowed opacity-50',
        )}
        onClick={() => !disabled && inputRef.current?.click()}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            !disabled && inputRef.current?.click();
          }
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          disabled={disabled}
          className="sr-only"
          onChange={(e) => handleFiles(e.target.files)}
        />
        {children || (
          <>
            <svg
              className="mb-3 h-10 w-10 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z"
              />
            </svg>
            <p className="text-sm font-medium text-gray-700">
              {dragActive ? '释放文件以上传' : '点击或拖拽文件到此处上传'}
            </p>
            <p className="mt-1 text-xs text-gray-500">
              {accept ? `支持格式: ${accept}` : '支持视频文件'} · 最大 {Math.round(maxSize / 1024 / 1024)}MB
            </p>
          </>
        )}
      </div>
      {error && (
        <p className="mt-2 text-xs text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

/** 上传进度条 */
interface UploadProgressProps {
  fileName: string;
  progress: number; // 0-100
  className?: string;
}

export function UploadProgress({ fileName, progress, className }: UploadProgressProps) {
  return (
    <div className={cn('w-full', className)}>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="truncate text-gray-700">{fileName}</span>
        <span className="ml-2 shrink-0 text-gray-500">{Math.round(progress)}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
        <div
          className="h-full rounded-full bg-primary-600 transition-all duration-300"
          style={{ width: `${progress}%` }}
          role="progressbar"
          aria-valuenow={progress}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
    </div>
  );
}
