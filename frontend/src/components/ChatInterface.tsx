import React, { useState, useRef, useEffect } from 'react';

interface Citation {
  document_name: string;
  page_number: number;
  text: string;
  score: number;
  file_type?: string;
  source_info?: string;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
}

interface ChatInterfaceProps {
  onError: (message: string) => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ onError }) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [showSourcesMap, setShowSourcesMap] = useState<Record<number, boolean>>({});
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const getErrorMessage = (error: unknown, fallback: string) => {
    return error instanceof Error ? error.message : fallback;
  };

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // Auto-resize input textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  const toggleSources = (index: number) => {
    setShowSourcesMap(prev => ({
      ...prev,
      [index]: !prev[index]
    }));
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userQuery = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userQuery }]);
    setLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userQuery }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to get answer.');
      }

      const result = await response.json();
      setMessages(prev => [
        ...prev, 
        { 
          role: 'assistant', 
          content: result.answer,
          citations: result.citations 
        }
      ]);
    } catch (err: unknown) {
      onError(getErrorMessage(err, 'Server connection failed.'));
      // Add a fallback error bubble so the chat flow isn't broken
      setMessages(prev => [
        ...prev,
        { 
          role: 'assistant', 
          content: 'Error: Could not retrieve an answer. Ensure the backend is running and your GEMINI_API_KEY is configured.' 
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderMessageContent = (text: string, citations?: Citation[]) => {
    if (!citations || citations.length === 0) {
      return <span>{text}</span>;
    }

    // Split text by references like [1], [2], etc.
    const parts = text.split(/(\[\d+\])/g);
    return (
      <>
        {parts.map((part, idx) => {
          const match = part.match(/\[(\d+)\]/);
          if (match) {
            const index = parseInt(match[1], 10) - 1;
            if (index >= 0 && index < citations.length) {
              const cit = citations[index];
              const sourceLabel = cit.file_type === 'url' && cit.source_info
                ? `${cit.document_name} - ${cit.source_info}`
                : `${cit.document_name} - Page ${cit.page_number}`;
              return (
                <span 
                  key={idx} 
                  className="citation-reference" 
                  title={sourceLabel}
                >
                  {match[1]}
                </span>
              );
            }
          }
          return <span key={idx}>{part}</span>;
        })}
      </>
    );
  };

  return (
    <div className="main-content">
      <div className="chat-header">
        <div className="chat-header-info">
          <h2>KnowFlow Assistant</h2>
          <p>Interact with your enterprise documents using natural language</p>
        </div>
        <div className="status-badge">
          <span className="status-dot"></span>
          Vector index ready
        </div>
      </div>

      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="empty-chat">
            <div className="empty-chat-icon">?</div>
            <h3>Ask Anything</h3>
            <p>
              Upload your employee handbook, policy docs, or service guides, and ask questions. 
              The AI will extract answers and reference sources with page-level citations.
            </p>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div className={`message-row ${msg.role}`} key={index}>
              <div className="message-bubble">
                <div style={{ whiteSpace: 'pre-line' }}>
                  {renderMessageContent(msg.content, msg.citations)}
                </div>

                {msg.citations && msg.citations.length > 0 && (
                  <div className="sources-section">
                    <button 
                      className="sources-toggle"
                      onClick={() => toggleSources(index)}
                    >
                      {showSourcesMap[index] ? 'Hide Citations' : `Show Citations (${msg.citations.length})`}
                    </button>
                    {showSourcesMap[index] && (
                      <div className="sources-list">
                        {msg.citations.map((cit, cIdx) => (
                          <div className="source-card" key={cIdx}>
                            <div className="source-card-header">
                              <span style={{ fontSize: '12px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '80%' }}>
                                {cit.file_type === 'url' ? 'URL' : 'Document'}: {cit.document_name}
                              </span>
                              <span className="source-card-index">
                                {cit.file_type === 'url' ? `[${cIdx + 1}] URL` : `[${cIdx + 1}] Page ${cit.page_number}`}
                              </span>
                            </div>
                            {cit.file_type === 'url' && cit.source_info && (
                              <div className="source-card-url">{cit.source_info}</div>
                            )}
                            <div className="source-card-snippet">
                              "{cit.text}"
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))
        )}

        {loading && (
          <div className="message-row assistant">
            <div className="message-bubble thinking-bubble">
              <div className="dot"></div>
              <div className="dot"></div>
              <div className="dot"></div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-panel">
        <div className="input-container">
          <textarea
            ref={textareaRef}
            rows={1}
            className="chat-input"
            placeholder="Ask a question about your documents..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={loading}
          />
          <button 
            className="send-button"
            onClick={handleSend}
            disabled={loading || !input.trim()}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};
