import React, { useState } from 'react';

const feedbackOptions = [
  { value: 'correct', label: 'Correct' },
  { value: 'partially_correct', label: 'Partial' },
  { value: 'incorrect', label: 'Incorrect' },
  { value: 'wrong_source', label: 'Wrong source' },
  { value: 'missing_citation', label: 'Missing citation' },
  { value: 'hallucinated', label: 'Hallucinated' },
];

interface FeedbackControlsProps {
  queryLogId?: string;
}

export const FeedbackControls: React.FC<FeedbackControlsProps> = ({ queryLogId }) => {
  const [selected, setSelected] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const submitFeedback = async (rating: string) => {
    setSelected(rating);
    setStatus('Saving...');

    try {
      const response = await fetch('http://localhost:8000/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query_log_id: queryLogId || null,
          rating,
          comment: null,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Feedback could not be saved.');
      }

      setStatus('Saved');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Feedback unavailable');
    }
  };

  return (
    <div className="feedback-controls">
      <span className="feedback-label">Feedback</span>
      <div className="feedback-buttons">
        {feedbackOptions.map((option) => (
          <button
            key={option.value}
            className={`feedback-button ${selected === option.value ? 'selected' : ''}`}
            onClick={() => submitFeedback(option.value)}
            disabled={!queryLogId}
            title={!queryLogId ? 'Query logging requires DATABASE_URL.' : option.label}
          >
            {option.label}
          </button>
        ))}
      </div>
      {status && <span className="feedback-status">{status}</span>}
    </div>
  );
};
