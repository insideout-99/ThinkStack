import { useState } from 'react';
import { DocumentUpload } from './components/DocumentUpload';
import { DocumentList } from './components/DocumentList';
import { ChatInterface } from './components/ChatInterface';

interface AlertState {
  message: string;
  title: string;
  type: 'success' | 'error' | null;
}

function App() {
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);
  const [alert, setAlert] = useState<AlertState>({
    message: '',
    title: '',
    type: null,
  });

  const handleUploadSuccess = () => {
    // Increment trigger to signal DocumentList to reload
    setRefreshTrigger(prev => prev + 1);
  };

  const triggerAlert = (title: string, message: string, type: 'success' | 'error') => {
    setAlert({ title, message, type });
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      setAlert(prev => {
        if (prev.message === message) {
          return { message: '', title: '', type: null };
        }
        return prev;
      });
    }, 5000);
  };

  return (
    <div className="app-container">
      {/* Toast Alert Notification */}
      {alert.type && (
        <div className={`notification ${alert.type}`}>
          <div className="notification-content">
            <div className="notification-title">
              {alert.type === 'success' ? 'Success' : 'Error'}: {alert.title}
            </div>
            <div className="notification-message">{alert.message}</div>
          </div>
          <button 
            className="notification-close"
            onClick={() => setAlert({ message: '', title: '', type: null })}
          >
            &times;
          </button>
        </div>
      )}

      {/* Sidebar Panel */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo-icon">TS</div>
          <h1 className="logo-text">ThinkStack</h1>
        </div>
        
        <div className="sidebar-content">
          {/* File Upload Panel */}
          <DocumentUpload 
            onUploadSuccess={handleUploadSuccess}
            onError={(msg) => triggerAlert('Upload Failed', msg, 'error')}
            onSuccess={(msg) => triggerAlert('Indexing Complete', msg, 'success')}
          />
          
          {/* Ingested File Registry */}
          <DocumentList refreshTrigger={refreshTrigger} />
        </div>
      </aside>

      {/* Primary Chat Console */}
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%' }}>
        <ChatInterface 
          onError={(msg) => triggerAlert('Search Error', msg, 'error')}
        />
      </main>
    </div>
  );
}

export default App;
