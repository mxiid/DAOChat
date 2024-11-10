"use client"

import * as React from 'react'
import { useState, useCallback, useRef } from 'react'
import { Button } from "./ui/button"
import { Input } from "./ui/input"
import { ScrollArea } from "./ui/scroll-area"
import { SendIcon, Loader2Icon, SunIcon, MoonIcon } from 'lucide-react'
import MessageComponent from './MessageComponent'


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

const GeometricShapes = () => (
  <div className="absolute inset-0 overflow-hidden pointer-events-none">
    <div className="absolute top-10 left-10 w-20 h-20 bg-blue-500 opacity-20 transform rotate-45"></div>
    <div className="absolute bottom-20 right-20 w-32 h-32 bg-teal-500 opacity-20 rounded-lg transform -rotate-12"></div>
    <div className="absolute top-1/3 right-1/4 w-16 h-16 bg-indigo-500 opacity-20 transform rotate-12"></div>
    <div className="absolute bottom-1/4 left-1/3 w-24 h-24 bg-purple-500 opacity-20 rounded-full"></div>
  </div>
)

const ThinkingIndicator = ({ state, isDarkMode }: { state: 'thinking' | 'streaming' | 'idle', isDarkMode: boolean }) => {
  if (state === 'idle') return null;

  return (
    <div className="flex items-center space-x-2 mb-4">
      <div className="w-6 h-6 mr-2">
        <img 
          src="/emblem.svg" 
          alt="DAO PropTech Emblem" 
          className={`w-full h-full ${isDarkMode ? 'invert' : ''}`}
        />
      </div>
      <div className="flex items-center space-x-2 text-gray-400">
        <span className="text-sm">{state === 'thinking' ? 'Thinking' : 'Streaming'}</span>
        <span className="flex space-x-1">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
        </span>
      </div>
    </div>
  );
};

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
    <div className={`flex flex-col min-h-[100dvh] ${isDarkMode ? 'bg-gray-900' : 'bg-white'}`}>
      <header className="bg-transparent backdrop-blur-sm p-4 font-bold flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center">
          <img 
            src="/emblem.svg" 
            alt="DAO PropTech Emblem" 
            className={`w-6 h-6 mr-2 ${isDarkMode ? 'invert' : ''}`}
          />
          <span className="!text-black dark:!text-white">DAO Chat</span>
        </div>
        <Button 
          variant="outline" 
          size="sm" 
          onClick={toggleTheme} 
          className={`bg-white/10 hover:bg-white/20 dark:bg-gray-800/10 dark:hover:bg-gray-700/20 
            border-gray-200/40 dark:border-gray-700/40 hover:border-gray-300 dark:hover:border-gray-600 
            transition-colors !text-black dark:!text-white`}
        >
          {isDarkMode ? <SunIcon className="h-4 w-4" /> : <MoonIcon className="h-4 w-4" />}
        </Button>
      </header>

      <main className="flex-1 flex flex-col overflow-hidden relative pb-[env(safe-area-inset-bottom)]">
        {messages.length === 0 && <GeometricShapes />}
        
        {messages.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4 py-8">
            <img 
              src="/emblem.svg" 
              alt="DAO PropTech Emblem" 
              className={`w-24 h-24 mb-8 ${
                isDarkMode ? 'invert' : ''
              }`}
            />
            <h2 className={`text-2xl font-semibold text-center mb-8 ${
              isDarkMode ? 'text-white' : 'text-gray-800'
            }`}>
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
              <div className={`transition-opacity duration-300 ${botState !== 'idle' ? 'opacity-100' : 'opacity-0'}`}>
                <ThinkingIndicator state={botState} isDarkMode={isDarkMode} />
              </div>
              {botState === 'streaming' && (
                <MessageComponent
                  message={{ role: 'bot', content: streamingMessage }}
                  isDarkMode={isDarkMode}
                  isStreaming={true}
                />
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
