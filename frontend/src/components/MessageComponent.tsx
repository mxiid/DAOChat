"use client"

import * as React from 'react'
import { useRef } from 'react'
import { UserIcon } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Message {
  role: 'user' | 'bot';
  content: string;
}

interface TableProps extends React.TableHTMLAttributes<HTMLTableElement> {
  node?: any;
  children?: React.ReactNode;
}

interface TableChildProps {
  props?: {
    children?: React.ReactNode;
  };
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
              <p {...props} className={`mb-4 text-sm sm:text-base ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            a: ({ node, ...props }) => (
              <a {...props} className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer" />
            ),
            ul: ({ node, ...props }) => (
              <ul {...props} className="list-disc pl-5 mb-4 space-y-2" />
            ),
            ol: ({ node, ...props }) => (
              <ol {...props} className="list-decimal pl-5 mb-4 space-y-2" />
            ),
            li: ({ node, ...props }) => (
              <li {...props} className={`text-sm sm:text-base ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            strong: ({ node, ...props }) => (
              <strong {...props} className={`font-bold ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            h1: ({ node, ...props }) => (
              <h1 {...props} className={`text-2xl font-bold mb-4 mt-6 ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            h2: ({ node, ...props }) => (
              <h2 {...props} className={`text-xl font-semibold mb-3 mt-5 ${isDarkMode ? "text-white" : "text-black"}`} />
            ),
            h3: ({ node, ...props }) => (
              <h3 {...props} className={`text-lg font-medium mb-2 mt-4 ${isDarkMode ? "text-white" : "text-black"}`} />
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
                <code
                  {...props}
                  className={`bg-gray-100 rounded px-1 py-0.5 ${isDarkMode ? "bg-gray-800 text-white" : "text-black"}`}
                >
                  {children}
                </code>
              )
            },
            table: ({ node, children, ...props }: TableProps) => {
              const childrenArray = React.Children.toArray(children);
              if (childrenArray.length < 2) return null;

              const thead = childrenArray[0] as React.ReactElement;
              const tbody = childrenArray[1] as React.ReactElement;

              if (!thead?.props?.children || !tbody?.props?.children) {
                return null;
              }

              const headerChildren = React.Children.toArray(thead.props.children) as React.ReactElement[];
              const bodyChildren = React.Children.toArray(tbody.props.children) as React.ReactElement[];

              return (
                <div className="overflow-x-auto mb-4 border border-gray-200 dark:border-gray-700 rounded-lg">
                  <table {...props} className="min-w-full divide-y divide-gray-200 dark:divide-gray-700 bg-white dark:bg-gray-800">
                    <thead className="bg-gray-100 dark:bg-gray-800">
                      <tr>
                        {headerChildren.map((th: React.ReactElement, index) => (
                          <th
                            key={index}
                            className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-gray-700 dark:text-gray-300 border-r last:border-r-0 border-gray-200 dark:border-gray-700"
                          >
                            {th.props.children}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="bg-white dark:bg-gray-800">
                      {bodyChildren.map((tr: React.ReactElement, index) => {
                        const cells = React.Children.toArray(tr.props.children) as React.ReactElement[];
                        return (
                          <tr key={index} className="hover:bg-gray-50 dark:hover:bg-gray-700">
                            {cells.map((td: React.ReactElement, cellIndex) => (
                              <td
                                key={cellIndex}
                                className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300 border-r last:border-r-0 border-gray-200 dark:border-gray-700 border-t"
                              >
                                {td.props.children}
                              </td>
                            ))}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              );
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
          <img 
            src="/emblem.svg" 
            alt="DAO PropTech Emblem" 
            className={`w-full h-full ${isDarkMode ? 'invert' : ''}`}
          />
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