import React, { useState } from 'react';

interface FeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (rating: number, feedback: string, email: string) => void;
}

const EMOJI_RATINGS = [
  { emoji: '😡', value: 1 },
  { emoji: '😟', value: 2 },
  { emoji: '😐', value: 3 },
  { emoji: '🙂', value: 4 },
  { emoji: '😍', value: 5 },
];

const FeedbackModal: React.FC<FeedbackModalProps> = ({ isOpen, onClose, onSubmit }) => {
  const [rating, setRating] = useState<number | null>(null);
  const [email, setEmail] = useState('');
  const [feedback, setFeedback] = useState('');
  const [errors, setErrors] = useState<{
    rating?: string;
    email?: string;
    feedback?: string;
  }>({});

  if (!isOpen) return null;

  const validateEmail = (email: string) => {
    if (!email) return true; // Email is optional
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const validateForm = () => {
    const newErrors: typeof errors = {};

    // Rating validation (required)
    if (rating === null) {
      newErrors.rating = 'Please select a rating';
    }

    // Email validation (optional but must be valid if provided)
    if (email && !validateEmail(email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    // Feedback validation (optional but with min/max length if provided)
    if (feedback && (feedback.length < 10 || feedback.length > 500)) {
      newErrors.feedback = 'Feedback must be between 10 and 500 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = () => {
    if (validateForm()) {
      onSubmit(rating!, feedback, email);
      onClose();
      // Reset form
      setRating(null);
      setEmail('');
      setFeedback('');
      setErrors({});
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white dark:bg-gray-800 rounded-xl shadow-xl w-full max-w-md mx-4 p-6 space-y-6">
        {/* Close button */}
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          aria-label="Close feedback form"
          title="Close"
        >
          <svg 
            className="w-6 h-6" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* Title */}
        <h2 className="text-2xl font-semibold text-center text-gray-900 dark:text-white">
          How was your experience?
        </h2>

        {/* Emoji Rating */}
        <div className="space-y-2">
          <div className="flex justify-center gap-4">
            {EMOJI_RATINGS.map(({ emoji, value }) => (
              <button
                key={value}
                onClick={() => {
                  setRating(value);
                  setErrors({ ...errors, rating: undefined });
                }}
                className={`text-3xl transition-transform ${
                  rating === value 
                    ? 'transform scale-125' 
                    : 'opacity-50 hover:opacity-100 hover:scale-110'
                }`}
              >
                {emoji}
              </button>
            ))}
          </div>
          {errors.rating && (
            <p className="text-red-500 text-sm text-center">{errors.rating}</p>
          )}
        </div>

        {/* Email Input */}
        <div className="space-y-2">
          <input
            type="email"
            placeholder="Your email (optional)"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setErrors({ ...errors, email: undefined });
            }}
            className={`w-full px-4 py-2 rounded-lg border ${
              errors.email 
                ? 'border-red-500 focus:ring-red-500' 
                : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500 dark:focus:ring-blue-400'
            } bg-white dark:bg-gray-700 text-gray-900 dark:text-white
            focus:ring-2 focus:border-transparent`}
          />
          {errors.email && (
            <p className="text-red-500 text-sm">{errors.email}</p>
          )}
        </div>

        {/* Feedback Input */}
        <div className="space-y-2">
          <textarea
            placeholder="Your feedback (optional, min 10 characters if provided)"
            value={feedback}
            onChange={(e) => {
              setFeedback(e.target.value);
              setErrors({ ...errors, feedback: undefined });
            }}
            rows={3}
            className={`w-full px-4 py-2 rounded-lg border ${
              errors.feedback 
                ? 'border-red-500 focus:ring-red-500' 
                : 'border-gray-300 dark:border-gray-600 focus:ring-blue-500 dark:focus:ring-blue-400'
            } bg-white dark:bg-gray-700 text-gray-900 dark:text-white
            focus:ring-2 focus:border-transparent`}
          />
          {feedback && (
            <p className={`text-sm ${feedback.length > 500 ? 'text-red-500' : 'text-gray-500 dark:text-gray-400'}`}>
              {feedback.length}/500 characters
            </p>
          )}
          {errors.feedback && (
            <p className="text-red-500 text-sm">{errors.feedback}</p>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4">
          <button
            onClick={handleSubmit}
            disabled={rating === null}
            className={`flex-1 px-4 py-2 rounded-lg font-medium text-white
                     ${rating === null 
                       ? 'bg-gray-400 cursor-not-allowed' 
                       : 'bg-blue-500 hover:bg-blue-600'}`}
          >
            Submit
          </button>
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 rounded-lg font-medium text-gray-700 dark:text-gray-300 
                     border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700"
          >
            Skip
          </button>
        </div>
      </div>
    </div>
  );
};

export default FeedbackModal; 