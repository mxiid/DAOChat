"use client"

import React, { useState } from 'react';
import { useRef, useEffect } from 'react'
import { UserIcon } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const ThumbUpIcon = ({ active }: { active?: boolean }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    fill={active ? "currentColor" : "none"} 
    viewBox="0 0 24 24" 
    stroke="currentColor" 
    className={`h-5 w-5 transition-all duration-200 ${
      active ? 'text-green-500 transform scale-110' : 'text-gray-500 hover:text-green-500'
    }`}
  >
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
  </svg>
);

const ThumbDownIcon = ({ active }: { active?: boolean }) => (
  <svg 
    xmlns="http://www.w3.org/2000/svg" 
    fill={active ? "currentColor" : "none"} 
    viewBox="0 0 24 24" 
    stroke="currentColor" 
    className={`h-5 w-5 transition-all duration-200 ${
      active ? 'text-red-500 transform scale-110' : 'text-gray-500 hover:text-red-500'
    }`}
  >
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018c.163 0 .326.02.485.06L17 4m-7 10v2a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5 0v2a2 2 0 01-2 2h-2.5" />
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
  const contentRef = useRef<HTMLDivElement>(null)
  const [feedback, setFeedback] = useState<'up' | 'down' | null>('up');

  useEffect(() => {
    if (contentRef.current && isStreaming) {
      const scrollContainer = contentRef.current.closest('.custom-scrollbar')
      if (scrollContainer) {
        scrollContainer.scrollTo({
          top: scrollContainer.scrollHeight,
          behavior: 'auto'
        })
      }
    }
  }, [isStreaming, message.content])

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
      })

      if (response.ok) {
        setFeedback(type)
      }
    } catch (error) {
      console.error('Error submitting feedback:', error)
    }
  }

  const renderContent = () => {
    if (message.role === 'user') {
      return <p className="text-sm sm:text-base break-words">{message.content}</p>
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
              const match = /language-(\w+)/.exec(className || "")
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
        {message.role === 'bot' && !isStreaming && (
          <div className="feedback-buttons flex items-center gap-2 mt-2">
            <button 
              onClick={() => handleFeedback('up')}
              className={`feedback-btn p-2 rounded-full transition-all duration-200 
                ${feedback === 'up' 
                  ? 'bg-green-100 dark:bg-green-900/30 ring-2 ring-green-500' 
                  : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
              aria-label="Thumbs up"
              title="Thumbs up"
            >
              <ThumbUpIcon active={feedback === 'up'} />
              <span className="sr-only">Thumbs up</span>
            </button>
            <button 
              onClick={() => handleFeedback('down')}
              className={`feedback-btn p-2 rounded-full transition-all duration-200 
                ${feedback === 'down' 
                  ? 'bg-red-100 dark:bg-red-900/30 ring-2 ring-red-500' 
                  : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
              aria-label="Thumbs down"
              title="Thumbs down"
            >
              <ThumbDownIcon active={feedback === 'down'} />
              <span className="sr-only">Thumbs down</span>
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className={`flex items-start mb-4 ${message.role === "user" ? "justify-end" : ""}`}>
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
  )
}

export default MessageComponent