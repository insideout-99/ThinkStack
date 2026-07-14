import React, { useEffect, useState } from 'react';

type ActivityTab = 'ingestion' | 'queries' | 'feedback';

interface IngestionEvent {
  id: string;
  source_name: string;
  source_type: string;
  event_type: string;
  status: string;
  chunk_count?: number | null;
  error_message?: string | null;
  created_at?: string | null;
}

interface QueryLog {
  id: string;
  query: string;
  status: string;
  latency_ms?: number | null;
  error_message?: string | null;
  created_at?: string | null;
}

interface FeedbackRecord {
  id: string;
  rating: string;
  comment?: string | null;
  created_at?: string | null;
}

interface ActivityPanelProps {
  refreshTrigger: number;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

export const ActivityPanel: React.FC<ActivityPanelProps> = ({ refreshTrigger }) => {
  const [activeTab, setActiveTab] = useState<ActivityTab>('ingestion');
  const [ingestionEvents, setIngestionEvents] = useState<IngestionEvent[]>([]);
  const [queryLogs, setQueryLogs] = useState<QueryLog[]>([]);
  const [feedback, setFeedback] = useState<FeedbackRecord[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const loadActivity = async () => {
      setLoading(true);
      try {
        const [eventsResponse, queryLogsResponse, feedbackResponse] = await Promise.all([
          fetch(`${API_BASE}/api/ingestion-events?limit=8`),
          fetch(`${API_BASE}/api/query-logs?limit=8`),
          fetch(`${API_BASE}/api/feedback?limit=8`),
        ]);

        if (!eventsResponse.ok || !queryLogsResponse.ok || !feedbackResponse.ok) {
          throw new Error('Activity history is unavailable.');
        }

        const [eventsData, queryLogsData, feedbackData] = await Promise.all([
          eventsResponse.json(),
          queryLogsResponse.json(),
          feedbackResponse.json(),
        ]);

        if (!active) return;
        setIngestionEvents(eventsData);
        setQueryLogs(queryLogsData);
        setFeedback(feedbackData);
        setError(null);
      } catch (err: unknown) {
        if (!active) return;
        setError('Backend unavailable. Start the FastAPI server on port 8000 to view activity history.');
      } finally {
        if (!active) return;
        setLoading(false);
      }
    };

    loadActivity();

    return () => {
      active = false;
    };
  }, [refreshTrigger]);

  const formatDate = (value?: string | null) => {
    if (!value) return 'No timestamp';

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return 'No timestamp';

    return date.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const renderIngestion = () => {
    if (ingestionEvents.length === 0) {
      return <div className="activity-empty">No ingestion events yet.</div>;
    }

    return ingestionEvents.map((event) => (
      <div className="activity-item" key={event.id}>
        <div className="activity-row">
          <span className={`activity-status ${event.status}`}>{event.status}</span>
          <span className="activity-time">{formatDate(event.created_at)}</span>
        </div>
        <div className="activity-title" title={event.source_name}>{event.source_name}</div>
        <div className="activity-meta">
          {event.source_type.toUpperCase()} - {event.event_type}
          {event.chunk_count !== null && event.chunk_count !== undefined ? ` - ${event.chunk_count} chunks` : ''}
        </div>
        {event.error_message && <div className="activity-error">{event.error_message}</div>}
      </div>
    ));
  };

  const renderQueries = () => {
    if (queryLogs.length === 0) {
      return <div className="activity-empty">No query logs yet.</div>;
    }

    return queryLogs.map((log) => (
      <div className="activity-item" key={log.id}>
        <div className="activity-row">
          <span className={`activity-status ${log.status}`}>{log.status}</span>
          <span className="activity-time">{formatDate(log.created_at)}</span>
        </div>
        <div className="activity-title" title={log.query}>{log.query}</div>
        <div className="activity-meta">
          {log.latency_ms !== null && log.latency_ms !== undefined ? `${log.latency_ms} ms` : 'No latency'}
        </div>
        {log.error_message && <div className="activity-error">{log.error_message}</div>}
      </div>
    ));
  };

  const renderFeedback = () => {
    if (feedback.length === 0) {
      return <div className="activity-empty">No feedback yet.</div>;
    }

    return feedback.map((record) => (
      <div className="activity-item" key={record.id}>
        <div className="activity-row">
          <span className="activity-status success">{record.rating.replaceAll('_', ' ')}</span>
          <span className="activity-time">{formatDate(record.created_at)}</span>
        </div>
        {record.comment && <div className="activity-meta">{record.comment}</div>}
      </div>
    ));
  };

  return (
    <div className="activity-panel">
      <div className="activity-header">
        <h4 className="section-title">Activity</h4>
        {loading && <span className="activity-loading">Loading</span>}
      </div>

      <div className="activity-tabs" role="tablist" aria-label="Activity history">
        <button type="button" className={activeTab === 'ingestion' ? 'active' : ''} onClick={() => setActiveTab('ingestion')}>
          Ingest
        </button>
        <button type="button" className={activeTab === 'queries' ? 'active' : ''} onClick={() => setActiveTab('queries')}>
          Queries
        </button>
        <button type="button" className={activeTab === 'feedback' ? 'active' : ''} onClick={() => setActiveTab('feedback')}>
          Feedback
        </button>
      </div>

      {error ? (
        <div className="activity-empty error">{error}</div>
      ) : (
        <div className="activity-list">
          {activeTab === 'ingestion' && renderIngestion()}
          {activeTab === 'queries' && renderQueries()}
          {activeTab === 'feedback' && renderFeedback()}
        </div>
      )}
    </div>
  );
};
