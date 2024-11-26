"use client"

import React, { useState, useRef, useEffect } from 'react';
import { UserIcon } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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

  const renderContent = () => {
    if (message.role === 'user') {
      return <p className="text-sm sm:text-base break-words">{message.content}</p>;
    }

    return (
      <div ref={contentRef} className="overflow-hidden">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          className={`prose prose-sm max-w-none break-words whitespace-pre-wrap ${isDarkMode ? "prose-invert" : ""}`}
          components={{
            p: ({ node, ...props }) => (
              <p {...props} className={`whitespace-pre-wrap mb-3 text-sm sm:text-base ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            a: ({ node, ...props }) => (
              <a {...props} className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer" />
            ),
            ul: ({ node, ...props }) => (
              <ul {...props} className="list-disc pl-5 mb-3 space-y-2" />
            ),
            ol: ({ node, ...props }) => (
              <ol {...props} className="list-decimal pl-5 mb-3 space-y-2" />
            ),
            li: ({ node, ...props }) => (
              <li {...props} className={`text-sm sm:text-base ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            strong: ({ node, ...props }) => (
              <strong {...props} className={`font-bold ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            h1: ({ node, ...props }) => (
              <h1 {...props} className={`text-2xl font-bold mb-3 mt-4 ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            h2: ({ node, ...props }) => (
              <h2 {...props} className={`text-xl font-semibold mb-3 mt-4 ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            h3: ({ node, ...props }) => (
              <h3 {...props} className={`text-lg font-medium mb-2 mt-3 ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            code: ({ node, className, children, ...props }) => {
              const match = /language-(\w+)/.exec(className || "");
              return match ? (
                <pre className={`bg-gray-100 rounded p-2 mb-4 overflow-x-auto ${isDarkMode ? "bg-gray-800" : ""}`}>
                  <code className={`language-${match[1]}`} {...props}>
                    {children}
                  </code>
                </pre>
              ) : (
                <code {...props} className={`bg-gray-100 rounded px-1 py-0.5 ${isDarkMode ? "bg-gray-800 text-white" : "text-black"}`}>
                  {children}
                </code>
              )
            },
            table: ({ node, ...props }) => (
              <div className="overflow-x-auto mb-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                <table {...props} className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800" />
              </div>
            ),
            thead: ({ node, ...props }) => (
              <thead {...props} className="bg-gray-50 dark:bg-gray-800" />
            ),
            th: ({ node, ...props }) => (
              <th {...props} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider bg-gray-50 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-r last:border-r-0 border-gray-200 dark:border-gray-700" />
            ),
            td: ({ node, ...props }) => (
              <td {...props} className="px-4 py-3 text-sm bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 border-r last:border-r-0 border-gray-200 dark:border-gray-700 border-t" />
            )
          }}
        >
          {message.content}
        </ReactMarkdown>
      </div>
    );
  };

  return (
    <div className={`flex flex-col mb-4 ${message.role === "user" ? "items-end" : "items-start"}`}>
      <div className="flex items-start">
        {message.role === "bot" && (
          <div className="w-6 h-6 mr-2 flex-shrink-0 mt-1">
            <img 
              src="/emblem.svg" 
              alt="DAO PropTech Emblem" 
              className={`w-full h-full ${isDarkMode ? 'invert' : ''}`}
            />
          </div>
        )}
        <div className={`rounded-lg p-2 sm:p-3 max-w-[80%] ${
          message.role === "user" ? "bg-[#ADFF2F] text-black" : isDarkMode ? "bg-gray-700" : "bg-gray-200"
        }`}>
          {renderContent()}
        </div>
        {message.role === "user" && <UserIcon className="w-5 h-5 sm:w-6 sm:h-6 ml-2 text-[#ADFF2F] flex-shrink-0 mt-1" />}
      </div>
      {message.role === 'bot' && !isStreaming && (
        <div className="flex items-center gap-2 mt-2 ml-8">
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
  );
};

export default MessageComponent;