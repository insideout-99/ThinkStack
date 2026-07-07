import React, { useEffect, useState } from 'react';

interface IngestedDocument {
  name: string;
  file_type: string;
  total_pages: number;
  department?: string | null;
  category?: string | null;
  author?: string | null;
  tags?: string[];
  uploaded_at?: string | null;
}

interface DocumentListProps {
  refreshTrigger: number;
}

export const DocumentList: React.FC<DocumentListProps> = ({ refreshTrigger }) => {
  const [documents, setDocuments] = useState<IngestedDocument[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const getErrorMessage = (error: unknown, fallback: string) => {
    return error instanceof Error ? error.message : fallback;
  };

  useEffect(() => {
    let active = true;

    fetch('http://localhost:8000/api/documents')
      .then((response) => {
        if (!response.ok) {
          throw new Error('Failed to load documents list.');
        }
        return response.json();
      })
      .then((data: IngestedDocument[]) => {
        if (!active) return;
        setDocuments(data);
        setError(null);
      })
      .catch((err: unknown) => {
        if (!active) return;
        setError(getErrorMessage(err, 'Error fetching document list.'));
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [refreshTrigger]);

  const getFileIcon = (fileType: string) => {
    switch (fileType?.toLowerCase()) {
      case 'pdf':
        return 'PDF';
      case 'docx':
        return 'DOC';
      case 'txt':
      case 'md':
        return 'TXT';
      case 'url':
        return 'URL';
      default:
        return 'DOC';
    }
  };

  const getFileTypeName = (fileType: string) => {
    switch (fileType?.toLowerCase()) {
      case 'pdf':
        return 'PDF';
      case 'docx':
        return 'Word';
      case 'txt':
        return 'Text';
      case 'md':
        return 'Markdown';
      case 'url':
        return 'Webpage';
      default:
        return 'Document';
    }
  };

  const formatDate = (value?: string | null) => {
    if (!value) return null;

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return null;

    return date.toLocaleDateString();
  };

  if (loading && documents.length === 0) {
    return (
      <div className="document-list-container">
        <h4 className="section-title">Knowledge Base</h4>
        <div style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '12px 0' }}>
          Loading document inventory...
        </div>
      </div>
    );
  }

  return (
    <div className="document-list-container">
      <h4 className="section-title">Knowledge Base ({documents.length})</h4>
      
      {error && (
        <div style={{ color: 'var(--color-error)', fontSize: '12px', margin: '4px 0' }}>
          Could not connect to database
        </div>
      )}

      <div className="document-list">
        {documents.length === 0 ? (
          <div className="empty-docs">
            No indexed documents yet. Index a file or webpage to start!
          </div>
        ) : (
          documents.map((doc, idx) => (
            <div className="document-item" key={idx}>
              <span className="document-icon" style={{ fontSize: '22px' }}>
                {getFileIcon(doc.file_type)}
              </span>
              <div className="document-info">
                <div className="document-name" title={doc.name}>
                  {doc.name}
                </div>
                <div className="document-meta">
                  {getFileTypeName(doc.file_type)} - {doc.total_pages} {doc.file_type === 'url' ? 'snapshot' : (doc.total_pages === 1 ? 'page' : 'pages')}
                </div>
                <div className="document-meta">
                  {[doc.department, doc.category, doc.author, formatDate(doc.uploaded_at)].filter(Boolean).join(' - ') || 'No metadata'}
                </div>
                {doc.tags && doc.tags.length > 0 && (
                  <div className="document-tags">
                    {doc.tags.slice(0, 3).map((tag) => (
                      <span className="document-tag" key={tag}>{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
