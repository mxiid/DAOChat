"use client"

import React, { useState, useRef, useEffect } from 'react';
import { UserIcon } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import FeedbackModal from './FeedbackModal';

const ThumbIcon = ({ type, active }: { type: 'up' | 'down'; active: boolean }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    viewBox="0 0 24 24" 
    fill="none"
    stroke="currentColor" 
    strokeWidth="2"
    strokeLinecap="round" 
    strokeLinejoin="round"
    className={`h-5 w-5 transition-all duration-200 ${active ? 'fill-current text-blue-500' : 'text-gray-400'}`}
  >
    {type === 'up' ? (
      <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
    ) : (
      <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
    )}
  </svg>
);

interface Message {
  role: 'user' | 'bot';
  content: string;
  id?: number;
}

interface MessageComponentProps {
  message: Message;
  isDarkMode: boolean;
  isStreaming: boolean;
}

const MessageComponent: React.FC<MessageComponentProps> = ({ message, isDarkMode, isStreaming }) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);
  const [showFeedbackModal, setShowFeedbackModal] = useState(false);

  useEffect(() => {
    if (contentRef.current && isStreaming) {
      const scrollContainer = contentRef.current.closest('.custom-scrollbar');
      if (scrollContainer) {
        scrollContainer.scrollTo({
          top: scrollContainer.scrollHeight,
          behavior: 'auto'
        });
      }
    }
  }, [isStreaming, message.content]);

  const handleFeedback = async (type: 'up' | 'down') => {
    if (!message.id) return;
    
    try {
      const response = await fetch(`/api/message/${message.id}/feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          thumbs_up: type === 'up',
          thumbs_down: type === 'down',
        }),
      });

      if (response.ok) {
        setFeedback(type === feedback ? null : type);
      }
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  const handleDetailedFeedback = async (rating: number, feedback: string, email: string) => {
    if (!message.id) return;
    
    try {
      await fetch(`/api/message/${message.id}/detailed-feedback`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          rating,
          feedback_text: feedback,
          email,
        }),
      });
    } catch (error) {
      console.error('Error submitting detailed feedback:', error);
    } finally {
      setShowFeedbackModal(false);
    }
  };

  const renderContent = () => {
    if (message.role === 'user') {
      return <p className="text-sm sm:text-base break-words whitespace-pre-wrap">{message.content}</p>;
    }

    return (
      <div ref={contentRef} className="w-full overflow-hidden">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          className="markdown-content"
          components={{
            p: ({ node, ...props }) => (
              <p {...props} className="mb-2 text-sm sm:text-base leading-relaxed break-words" />
            ),
            a: ({ node, ...props }) => (
              <a {...props} className="text-blue-500 hover:underline break-words" target="_blank" rel="noopener noreferrer" />
            ),
            ul: ({ node, ...props }) => (
              <ul {...props} className="list-disc pl-6 mb-4 space-y-1" />
            ),
            ol: ({ node, ...props }) => (
              <ol {...props} className="list-decimal pl-6 mb-4 space-y-1" />
            ),
            li: ({ node, ...props }) => (
              <li {...props} className={`text-sm sm:text-base leading-relaxed ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            strong: ({ node, ...props }) => (
              <strong {...props} className={`font-semibold ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            h1: ({ node, ...props }) => (
              <h1 {...props} className={`text-xl font-bold mb-2 ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            h2: ({ node, ...props }) => (
              <h2 {...props} className={`text-lg font-semibold mb-2 ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            h3: ({ node, ...props }) => (
              <h3 {...props} className={`text-base font-medium mb-2 ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            code: ({ node, className, children, ...props }) => {
              const match = /language-(\w+)/.exec(className || "");
              return match ? (
                <pre className={`rounded-md p-2 mb-4 overflow-x-auto ${isDarkMode ? "bg-gray-800" : "bg-gray-100"}`}>
                  <code className={`language-${match[1]} block text-sm font-mono ${isDarkMode ? "text-gray-100" : "text-gray-800"}`} {...props}>
                    {children}
                  </code>
                </pre>
              ) : (
                <code {...props} className={`font-mono text-sm px-1 py-0.5 rounded ${isDarkMode ? "bg-gray-800 text-gray-100" : "bg-gray-100 text-gray-800"}`}>
                  {children}
                </code>
              )
            },
            table: ({ node, ...props }) => (
              <div className="w-full overflow-x-auto my-2">
                <table {...props} className="w-full border-collapse border border-gray-300 dark:border-gray-700" />
              </div>
            ),
            thead: ({ node, ...props }) => (
              <thead {...props} className={`${isDarkMode ? "bg-gray-800" : "bg-gray-100"}`} />
            ),
            th: ({ node, ...props }) => (
              <th 
                {...props} 
                className={`p-2 text-left text-sm border border-gray-300 dark:border-gray-700 ${
                  isDarkMode ? "text-gray-200" : "text-gray-900"
                }`}
              />
            ),
            td: ({ node, ...props }) => (
              <td 
                {...props} 
                className={`p-2 text-sm border border-gray-300 dark:border-gray-700 ${
                  isDarkMode ? "text-gray-300" : "text-gray-700"
                }`}
              />
            ),
            blockquote: ({ node, ...props }) => (
              <blockquote {...props} className={`border-l-4 pl-4 my-2 ${
                isDarkMode ? "border-gray-600 text-gray-300" : "border-gray-300 text-gray-700"
              }`} />
            ),
            hr: ({ node, ...props }) => (
              <hr {...props} className="my-4 border-t border-gray-300 dark:border-gray-700" />
            )
          }}
        >
          {message.content}
        </ReactMarkdown>
      </div>
    );
  };

  return (
    <>
      <div className={`flex flex-col mb-2 ${message.role === "user" ? "items-end" : "items-start"} w-full`}>
        <div className={`flex items-start ${message.role === "user" ? "justify-end" : "justify-start"} w-full px-2 sm:px-0`}>
          {message.role === "bot" && (
            <div className="w-6 h-6 mr-2 flex-shrink-0 mt-1">
              <img 
                src="/emblem.svg" 
                alt="DAO PropTech Emblem" 
                className={`w-full h-full ${isDarkMode ? 'invert' : ''}`}
              />
            </div>
          )}
          <div className={`rounded-lg p-2 sm:p-3 ${
            message.role === "user" 
              ? "bg-[#ADFF2F] text-black max-w-[85%] sm:max-w-[75%]" 
              : isDarkMode 
                ? "bg-gray-700 w-full" 
                : "bg-gray-200 w-full"
          }`}>
            {renderContent()}
          </div>
          {message.role === "user" && <UserIcon className="w-5 h-5 sm:w-6 sm:h-6 ml-2 text-[#ADFF2F] flex-shrink-0 mt-1" />}
        </div>
        {message.role === 'bot' && !isStreaming && (
          <div className="flex items-center gap-2 mt-1 ml-8">
            <button 
              onClick={() => handleFeedback('up')}
              className="feedback-btn p-1 rounded-full transition-all duration-200 hover:bg-gray-100 dark:hover:bg-gray-800"
              aria-label="Thumbs up"
            >
              <ThumbIcon type="up" active={feedback === 'up'} />
            </button>
            <button 
              onClick={() => handleFeedback('down')}
              className="feedback-btn p-1 rounded-full transition-all duration-200 hover:bg-gray-100 dark:hover:bg-gray-800"
              aria-label="Thumbs down"
            >
              <ThumbIcon type="down" active={feedback === 'down'} />
            </button>
          </div>
        )}
      </div>
      <FeedbackModal 
        isOpen={showFeedbackModal}
        onClose={() => setShowFeedbackModal(false)}
        onSubmit={handleDetailedFeedback}
      />
    </>
  );
};

export default MessageComponent;