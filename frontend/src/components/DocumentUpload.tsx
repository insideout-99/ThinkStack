import React, { useState, useRef } from 'react';

interface DocumentUploadProps {
  onUploadSuccess: () => void;
  onError: (message: string) => void;
  onSuccess: (message: string) => void;
}

export const DocumentUpload: React.FC<DocumentUploadProps> = ({
  onUploadSuccess,
  onError,
  onSuccess,
}) => {
  const [dragActive, setDragActive] = useState<boolean>(false);
  const [uploading, setUploading] = useState<boolean>(false);
  const [crawling, setCrawling] = useState<boolean>(false);
  const [urlInput, setUrlInput] = useState<string>('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const getErrorMessage = (error: unknown, fallback: string) => {
    return error instanceof Error ? error.message : fallback;
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const processFile = async (file: File) => {
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    const allowed = ['.pdf', '.docx', '.txt', '.md'];
    
    if (!allowed.includes(ext)) {
      onError('Only PDF, DOCX, TXT, and MD files are supported in Phase 2.');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to index file.');
      }

      const result = await response.json();
      onSuccess(`Successfully indexed ${file.name} (${result.chunks_count} chunks)`);
      onUploadSuccess();
    } catch (err: unknown) {
      onError(getErrorMessage(err, 'Server error during upload.'));
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleCrawlUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanUrl = urlInput.trim();
    if (!cleanUrl) return;

    if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
      onError('Invalid URL. Must start with http:// or https://');
      return;
    }

    setCrawling(true);
    try {
      const response = await fetch('http://localhost:8000/api/url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: cleanUrl })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to crawl URL.');
      }

      await response.json();
      onSuccess(`Successfully indexed webpage: "${cleanUrl}"`);
      setUrlInput('');
      onUploadSuccess();
    } catch (err: unknown) {
      onError(getErrorMessage(err, 'Server error crawling webpage.'));
    } finally {
      setCrawling(false);
    }
  };

  return (
    <div className="document-upload-panel" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* File Upload Area */}
      <div 
        className={`upload-container ${dragActive ? 'drag-active' : ''}`}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={triggerFileSelect}
      >
        <input 
          ref={fileInputRef}
          type="file" 
          className="file-input" 
          accept=".pdf,.docx,.txt,.md"
          onChange={handleFileInput}
          disabled={uploading || crawling}
        />
        
        {uploading ? (
          <div>
            <span className="upload-icon">...</span>
            <p className="upload-text">Processing and embedding file...</p>
            <p className="upload-subtext">Generating vectors for Qdrant</p>
          </div>
        ) : (
          <div>
            <span className="upload-icon">FILE</span>
            <p className="upload-text">
              {dragActive ? 'Drop file here' : 'Index Document File'}
            </p>
            <p className="upload-subtext">PDF, DOCX, TXT, or MD support</p>
          </div>
        )}
      </div>

      {/* URL Ingestion Form */}
      <div className="url-ingest-container" style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px' }}>
        <h4 className="section-title" style={{ marginBottom: '10px' }}>Index Webpage</h4>
        <form onSubmit={handleCrawlUrl} style={{ display: 'flex', gap: '8px' }}>
          <input
            type="text"
            className="url-input"
            placeholder="https://example.com/docs"
            value={urlInput}
            onChange={(e) => setUrlInput(e.target.value)}
            disabled={uploading || crawling}
            style={{
              flex: 1,
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              borderRadius: '10px',
              padding: '8px 12px',
              fontSize: '13px',
              color: 'var(--text-primary)',
              outline: 'none',
              transition: 'border-color 0.2s ease'
            }}
          />
          <button
            type="submit"
            className="crawl-button"
            disabled={uploading || crawling || !urlInput.trim()}
            style={{
              background: 'var(--accent-secondary)',
              color: 'white',
              border: 'none',
              borderRadius: '10px',
              padding: '8px 16px',
              fontSize: '13px',
              fontWeight: '600',
              cursor: 'pointer',
              opacity: (uploading || crawling || !urlInput.trim()) ? 0.5 : 1,
              transition: 'all 0.2s ease'
            }}
          >
            {crawling ? 'Indexing...' : 'Index'}
          </button>
        </form>
      </div>
    </div>
  );
};
