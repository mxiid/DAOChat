"use client"

import * as React from 'react'
import { useRef } from 'react'
import { UserIcon } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import AnimatedLogo from './AnimatedLogo'

interface Message {
  role: 'user' | 'bot';
  content: string;
}

const MessageComponent: React.FC<{
  message: Message;
  isDarkMode: boolean;
  isStreaming: boolean;
}> = React.memo(({ message, isDarkMode, isStreaming }) => {
  const contentRef = useRef<HTMLDivElement>(null);

  const renderContent = () => {
    if (message.role === 'user') {
      return <p className="text-sm sm:text-base break-words">{message.content}</p>;
    }

    return (
      <div ref={contentRef}>
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          className={`prose prose-sm max-w-none break-words ${isDarkMode ? "prose-invert" : ""}`}
          components={{
            p: ({ node, ...props }) => (
              <p {...props} className={`mb-2 text-sm sm:text-base ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            a: ({ node, ...props }) => (
              <a {...props} className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer" />
            ),
            ul: ({ node, ...props }) => (
              <ul {...props} className="list-disc ml-4 space-y-2 mb-2" />
            ),
            ol: ({ node, ...props }) => (
              <ol {...props} className="list-decimal ml-4 space-y-2 mb-2" />
            ),
            li: ({ node, ...props }) => (
              <li {...props} className={`${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            strong: ({ node, ...props }) => (
              <strong {...props} className={`font-bold ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            h1: ({ node, ...props }) => (
              <h1 {...props} className={`text-xl font-bold mb-2 ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            h2: ({ node, ...props }) => (
              <h2 {...props} className={`text-lg font-bold mb-2 ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            h3: ({ node, ...props }) => (
              <h3 {...props} className={`text-base font-bold mb-2 ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            code: ({ node, className, children, ...props }) => {
              const match = /language-(\w+)/.exec(className || "")
              return match ? (
                <pre className={`bg-gray-100 rounded p-2 mb-2 overflow-x-auto ${isDarkMode ? "bg-gray-800" : ""}`}>
                  <code className={`language-${match[1]}`} {...props}>
                    {children}
                  </code>
                </pre>
              ) : (
                <code
                  {...props}
                  className={`bg-gray-100 rounded px-1 py-0.5 ${isDarkMode ? "bg-gray-800 text-white" : "text-black"}`}
                >
                  {children}
                </code>
              )
            },
          }}
        >
          {message.content}
        </ReactMarkdown>
      </div>
    );
  };

  return (
    <div className={`flex items-start mb-4 ${message.role === "user" ? "justify-end" : ""}`}>
      {message.role === "bot" && (
        <div className="w-6 h-6 mr-2 flex-shrink-0 mt-1">
          {isStreaming ? (
            <AnimatedLogo thinking={false} />
          ) : (
            <img 
              src="/emblem.svg" 
              alt="DAO PropTech Emblem" 
              className={`w-full h-full ${isDarkMode ? 'invert' : ''}`}
            />
          )}
        </div>
      )}
      <div
        className={`rounded-lg p-2 sm:p-3 max-w-[80%] ${
          message.role === "user" ? "bg-[#ADFF2F] text-black" : isDarkMode ? "bg-gray-700" : "bg-gray-200"
        }`}
      >
        {renderContent()}
      </div>
      {message.role === "user" && <UserIcon className="w-5 h-5 sm:w-6 sm:h-6 ml-2 text-[#ADFF2F] flex-shrink-0 mt-1" />}
    </div>
  );
});

export default MessageComponent;