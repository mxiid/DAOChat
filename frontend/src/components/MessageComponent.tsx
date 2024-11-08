"use client"

import * as React from 'react'
import { useState, useEffect, useRef } from 'react'
import { BotIcon, UserIcon } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Message {
  role: 'user' | 'bot';
  content: string;
}

const MessageComponent: React.FC<{
  message: Message;
  isDarkMode: boolean;
  isStreaming: boolean;
}> = React.memo(({ message, isDarkMode, isStreaming }) => {
  const [showCursor, setShowCursor] = useState(isStreaming);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setShowCursor(isStreaming);
  }, [isStreaming]);

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [message.content]);

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
            // ... rest of the markdown components ...
          }}
        >
          {message.content}
        </ReactMarkdown>
        {showCursor && (
          <span
            className={`inline-block w-2 h-4 align-middle ${
              isDarkMode ? "bg-white" : "bg-black"
            } animate-pulse`}
            aria-hidden="true"
          />
        )}
      </div>
    );
  };

  return (
    <div className={`flex items-start mb-4 ${message.role === "user" ? "justify-end" : ""}`}>
      {message.role === "bot" && <BotIcon className="w-5 h-5 sm:w-6 sm:h-6 mr-2 text-[#00FFFF] flex-shrink-0 mt-1" />}
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