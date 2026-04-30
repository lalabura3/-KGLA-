import { useState, useRef } from 'react';
import { uploadVideo, importVideoLink } from '../lib/api';

export default function VideoUpload({ onUploadComplete }) {
  const [tab, setTab] = useState('upload'); // 'upload' | 'link'
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [linkUrl, setLinkUrl] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const handleFileUpload = async (file) => {
    if (!file) return;
    setUploading(true);
    setProgress(0);
    try {
      const result = await uploadVideo(file, file.name, (e) => {
        if (e.total) setProgress(Math.round((e.loaded / e.total) * 100));
      });
      onUploadComplete?.(result);
    } catch (err) {
      alert('上传失败: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
      setProgress(0);
    }
  };

  const handleLinkImport = async () => {
    if (!linkUrl.trim()) return;
    setUploading(true);
    try {
      const result = await importVideoLink(linkUrl.trim());
      onUploadComplete?.(result);
      setLinkUrl('');
    } catch (err) {
      alert('导入失败: ' + (err.response?.data?.detail || err.message));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
      {/* Tabs */}
      <div className="flex gap-4 mb-6">
        <button
          onClick={() => setTab('upload')}
          className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
            tab === 'upload'
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-gray-400 hover:text-gray-600'
          }`}
        >
          📤 上传视频
        </button>
        <button
          onClick={() => setTab('link')}
          className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
            tab === 'link'
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-gray-400 hover:text-gray-600'
          }`}
        >
          🔗 粘贴链接
        </button>
      </div>

      {tab === 'upload' ? (
        <div
          className={`upload-zone ${dragOver ? 'dragging' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFileUpload(e.dataTransfer.files[0]); }}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="video/mp4,video/flv,video/avi,video/mov,video/mkv,video/webm"
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files[0])}
          />

          {uploading ? (
            <div className="space-y-3">
              <div className="text-4xl">⏳</div>
              <p className="text-gray-600 font-medium">正在上传...</p>
              <div className="w-64 mx-auto bg-gray-100 rounded-full h-2">
                <div
                  className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-sm text-gray-400">{progress}%</p>
            </div>
          ) : (
            <>
              <div className="text-5xl mb-3">🎬</div>
              <p className="text-gray-600 font-medium mb-1">
                拖拽视频到此处，或点击选择文件
              </p>
              <p className="text-sm text-gray-400">
                支持 MP4 / FLV / AVI / MOV / MKV / WebM（最大 500MB）
              </p>
            </>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <input
            type="text"
            value={linkUrl}
            onChange={(e) => setLinkUrl(e.target.value)}
            placeholder="粘贴 B站 / YouTube / 百度网盘链接..."
            className="w-full px-4 py-3 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            disabled={uploading}
          />
          <button
            onClick={handleLinkImport}
            disabled={uploading || !linkUrl.trim()}
            className={`w-full py-3 rounded-xl font-medium text-white transition-all ${
              uploading || !linkUrl.trim()
                ? 'bg-gray-300 cursor-not-allowed'
                : 'bg-primary-500 hover:bg-primary-600 active:scale-[0.98]'
            }`}
          >
            {uploading ? '正在导入...' : '导入视频链接'}
          </button>
        </div>
      )}
    </div>
  );
}
