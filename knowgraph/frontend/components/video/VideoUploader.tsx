'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { FileUpload, UploadProgress, Alert } from '@/components/ui';
import { useUploadVideo } from '@/lib/hooks/useVideo';
import { ROUTES } from '@/lib/constants';

interface VideoUploaderProps {
  onSuccess?: (videoId: string) => void;
  className?: string;
}

export function VideoUploader({ onSuccess, className }: VideoUploaderProps) {
  const router = useRouter();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);

  const uploadMutation = useUploadVideo();

  const handleFilesSelected = async (files: File[]) => {
    const file = files[0];
    if (!file) return;
    setSelectedFile(file);
    setUploading(true);
    setProgress(0);

    try {
      // Simulate progress since the API uploadVideo uses onUploadProgress
      const result = await uploadMutation.mutateAsync(file, {
        onSuccess: undefined, // handled below
      } as any);

      // Simulate progress completion
      setProgress(100);
      
      // Delay slightly so user sees 100%
      setTimeout(() => {
        onSuccess?.(result.id);
        router.push(ROUTES.LEARN(result.id));
      }, 600);
    } catch {
      setUploading(false);
    }
  };

  const error = uploadMutation.error;

  return (
    <div className={className}>
      {error && (
        <Alert variant="error" className="mb-4" onClose={() => uploadMutation.reset()}>
          {typeof error === 'object' && 'detail' in error
            ? (error as { detail: string }).detail
            : '上传失败，请重试'}
        </Alert>
      )}

      {!uploading ? (
        <FileUpload
          accept="video/*"
          maxSize={500 * 1024 * 1024}
          onFilesSelected={handleFilesSelected}
        />
      ) : (
        <div className="space-y-4 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <UploadProgress
            fileName={selectedFile?.name || ''}
            progress={progress}
          />
          <p className="text-center text-xs text-gray-500">
            {progress < 100 ? '上传中，请勿关闭页面...' : '上传完成，正在跳转...'}
          </p>
        </div>
      )}
    </div>
  );
}
