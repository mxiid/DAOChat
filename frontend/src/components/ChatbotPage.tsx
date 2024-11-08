"use client"

import * as React from 'react'
import { useState, useCallback, useRef, lazy, Suspense } from 'react'
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import { ScrollArea, ScrollBar } from "./ui/scroll-area"
import { SendIcon, BotIcon, UserIcon, Loader2Icon, SunIcon, MoonIcon } from 'lucide-react'
import axios from 'axios'
import remarkGfm from 'remark-gfm'  // Add this import

const ReactMarkdown = lazy(() => import('react-markdown'))

interface Message {
  role: 'user' | 'bot';
  content: string;
}

const staticSuggestedQuestions = [
  "What is DAO PropTech?",
  "How does real estate tokenization work?",
  "What are the benefits of investing through DAO PropTech?",
  "Can you explain the concept of fractional ownership?"
];

const useTheme = () => {
  const [isDarkMode, setIsDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') === 'dark'
    }
    return false
  })

  const toggleTheme = useCallback(() => {
    const newTheme = !isDarkMode
    setIsDarkMode(newTheme)
    localStorage.setItem('theme', newTheme ? 'dark' : 'light')
    if (newTheme) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDarkMode])

  React.useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [isDarkMode])

  return { isDarkMode, toggleTheme }
}

const useChatbot = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [botState, setBotState] = useState<'idle' | 'thinking' | 'streaming'>('idle')
  const [streamingMessage, setStreamingMessage] = useState('')

  const handleSendMessage = useCallback(async (message: string) => {
    if (message.trim() === '' || botState !== 'idle') return;

    const newUserMessage: Message = { role: 'user', content: message.trim() };
    setMessages(prev => [...prev, newUserMessage]);
    setInput('');
    setBotState('thinking');
    setStreamingMessage('');

    try {
      const response = await fetch('/api/ask', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: message }),
      });

      if (!response.ok) throw new Error('Stream response was not ok');
      
      const reader = response.body?.getReader();
      if (!reader) throw new Error('No reader available');

      const decoder = new TextDecoder();
      let accumulatedMessage = '';

      setBotState('streaming');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              accumulatedMessage += data.token;
              setStreamingMessage(accumulatedMessage);
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }

      const botMessage: Message = { role: 'bot', content: accumulatedMessage };
      setMessages(prev => [...prev, botMessage]);
      
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage = error instanceof Error ? error.message : 'An error occurred';
      const errorBotMessage: Message = { 
        role: 'bot', 
        content: `Sorry, I encountered an error: ${errorMessage}` 
      };
      setMessages(prev => [...prev, errorBotMessage]);
    } finally {
      setBotState('idle');
      setStreamingMessage('');
    }
  }, [botState]);

  return { messages, input, setInput, botState, streamingMessage, handleSendMessage }
}

const MessageComponent = React.memo(({ 
  message, 
  isDarkMode, 
  isStreaming 
}: { 
  message: Message; 
  isDarkMode: boolean; 
  isStreaming?: boolean 
}) => (
  <div className={`flex items-start mb-4 ${message.role === "user" ? "justify-end" : ""}`}>
    {message.role === "bot" && <BotIcon className="w-5 h-5 sm:w-6 sm:h-6 mr-2 text-[#00FFFF] flex-shrink-0 mt-1" />}
    <div
      className={`rounded-lg p-2 sm:p-3 max-w-[80%] ${
        message.role === "user" ? "bg-[#ADFF2F] text-black" : isDarkMode ? "bg-gray-700" : "bg-gray-200"
      }`}
    >
      <div className="relative">
        {message.role === "user" ? (
          <p className="text-sm sm:text-base break-words">{message.content}</p>
        ) : (
          <Suspense fallback={<div>Loading...</div>}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              className={`prose prose-sm max-w-none break-words ${isDarkMode ? "prose-invert" : ""}`}
              components={{
                a: ({ node, ...props }) => (
                  <a {...props} className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer" />
                ),
                p: ({ node, ...props }) => (
                  <p {...props} className={`mb-2 text-sm sm:text-base ${isDarkMode ? "text-white" : "text-black"}`} />
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
            {isStreaming && (
              <span 
                className={`inline-block w-0.5 h-4 ml-0.5 -mb-0.5 animate-pulse ${
                  isDarkMode ? "bg-white" : "bg-black"
                }`} 
                aria-hidden="true"
              />
            )}
          </Suspense>
        )}
      </div>
    </div>
    {message.role === "user" && <UserIcon className="w-5 h-5 sm:w-6 sm:h-6 ml-2 text-[#ADFF2F] flex-shrink-0 mt-1" />}
  </div>
))

const GeometricShapes = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none">
    <div className="absolute top-10 left-10 w-20 h-20 bg-blue-500 opacity-20 transform rotate-45"></div>
    <div className="absolute bottom-20 right-20 w-32 h-32 bg-teal-500 opacity-20 rounded-lg transform -rotate-12"></div>
    <div className="absolute top-1/3 right-1/4 w-16 h-16 bg-indigo-500 opacity-20 transform rotate-12"></div>
    <div className="absolute bottom-1/4 left-1/3 w-24 h-24 bg-purple-500 opacity-20 rounded-full"></div>
  </div>
)

const ThinkingIndicator = ({ state }: { state: 'thinking' | 'streaming' }) => (
  <div className="flex items-center space-x-2 text-gray-400 mb-2">
    <BotIcon className="w-5 h-5 text-[#00FFFF]" />
    {state === 'thinking' ? (
      <>
        <span className="text-sm">Thinking</span>
        <span className="flex space-x-1">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
        </span>
      </>
    ) : (
      <span className="w-2 h-4 bg-gray-400 animate-pulse"></span>
    )}
  </div>
)

export default function ChatbotPage() {
  const { isDarkMode, toggleTheme } = useTheme()
  const { messages, input, setInput, botState, streamingMessage, handleSendMessage } = useChatbot()
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    if (scrollAreaRef.current) {
      const scrollArea = scrollAreaRef.current
      scrollArea.scrollTop = scrollArea.scrollHeight
    }
  }, [messages, streamingMessage, botState])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value)
  }

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && botState !== 'thinking' && input.trim()) {
      handleSendMessage(input)
    }
  }

  return (
    <div className={`flex flex-col min-h-[100dvh] ${isDarkMode ? 'dark bg-gray-900' : 'bg-white'}`}>
      <header className="bg-gradient-to-r from-[#0066FF] to-[#00FFFF] p-4 text-white font-bold flex items-center justify-between sticky top-0 z-50 shadow-md">
        <div className="flex items-center">
          <BotIcon className="mr-2" />
          <span className="text-lg">DAO PropTech Assistant</span>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={toggleTheme} 
          className="bg-white/10 hover:bg-white/20 text-white border-transparent hover:border-white transition-colors"
        >
          {isDarkMode ? <SunIcon className="h-4 w-4" /> : <MoonIcon className="h-4 w-4" />}
        </Button>
      </header>

      <main className="flex-1 flex flex-col overflow-hidden relative pb-[env(safe-area-inset-bottom)]">
        {messages.length === 0 && <GeometricShapes />}
        
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4 py-8">
            <h2 className={`text-2xl font-semibold text-center mb-8 ${isDarkMode ? 'text-white' : 'text-gray-800'}`}>
              How can I assist you with real estate investments today?
            </h2>
            <div className="w-full max-w-md space-y-4">
              {staticSuggestedQuestions.map((question, index) => (
                <Button
                  key={index}
                  variant="outline"
                  onClick={() => handleSendMessage(question)}
                  className={`w-full text-left justify-start h-auto whitespace-normal ${
                    isDarkMode ? 'bg-gray-800 hover:bg-gray-700 text-white' : 'bg-white hover:bg-gray-100 text-gray-800'
                  }`}
                >
                  {question}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <ScrollArea className="flex-1" ref={scrollAreaRef}>
            <div className="px-4 py-2 max-w-3xl mx-auto">
              {messages.map((message, index) => (
                <MessageComponent 
                  key={index} 
                  message={message} 
                  isDarkMode={isDarkMode}
                  isStreaming={false}
                />
              ))}
              {botState !== 'idle' && (
                <>
                  <ThinkingIndicator state={botState} />
                  {botState === 'streaming' && (
                    <MessageComponent
                      message={{ role: 'bot', content: streamingMessage }}
                      isDarkMode={isDarkMode}
                      isStreaming={true}
                    />
                  )}
                </>
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        )}

        <div className="sticky bottom-0 z-50">
          <div className="p-4 bg-gradient-to-t from-inherit via-inherit to-transparent">
            <div className={`flex space-x-2 w-full max-w-2xl mx-auto rounded-full shadow-lg ${
              isDarkMode ? 'bg-gray-800' : 'bg-white'
            }`}>
              <Input
                value={input}
                onChange={handleInputChange}
                onKeyPress={handleKeyPress}
                placeholder={messages.length === 0 ? "Ask me anything about real estate investments..." : "Type your message..."}
                className={`flex-grow rounded-l-full border-0 focus:ring-0 ${
                  isDarkMode ? 'bg-gray-800 text-white placeholder-gray-400' : 'bg-white text-gray-800 placeholder-gray-500'
                }`}
                disabled={botState !== 'idle'}
              />
              <Button
                onClick={() => handleSendMessage(input)}
                className={`rounded-r-full ${
                  botState !== 'idle' ? 'bg-gray-500' : 'bg-[#ADFF2F] hover:bg-[#9ACD32]'
                } text-black`}
                disabled={botState !== 'idle' || !input.trim()}
              >
                {botState !== 'idle' ? <Loader2Icon className="w-4 h-4 animate-spin" /> : <SendIcon className="w-4 h-4" />}
              </Button>
            </div>
          </div>
          <div className={`text-center text-xs pb-1 ${
            isDarkMode ? 'text-gray-400' : 'text-gray-500'
          }`}>
            DAO Chat may make mistakes. Use with discretion.
          </div>
        </div>
      </main>
    </div>
  )
}
