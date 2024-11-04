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
    return true
  })

  const toggleTheme = useCallback(() => {
    const newTheme = !isDarkMode
    setIsDarkMode(newTheme)
    localStorage.setItem('theme', newTheme ? 'dark' : 'light')
  }, [isDarkMode])

  return { isDarkMode, toggleTheme }
}

const useChatbot = () => {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'bot', content: "Welcome to DAO PropTech's AI Investment Advisor! How can I assist you with our real estate offerings today?" }
  ])
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)

  const handleSendMessage = useCallback(async (message: string) => {
    if (message.trim() === '' || isThinking) return;

    const newUserMessage: Message = { role: 'user', content: message.trim() };
    setMessages(prev => [...prev, newUserMessage]);
    setInput('');
    setIsThinking(true);

    try {
      const response = await axios.post('/api/ask', { text: message });

      console.log('API Response:', response); // For debugging

      if (response.data && typeof response.data === 'object' && response.data.text) {
        const botMessage: Message = { role: 'bot', content: response.data.text };
        setMessages(prev => [...prev, botMessage]);
      } else {
        console.error('Unexpected response format:', response.data);
        throw new Error('Unexpected response format');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      let errorMessage = 'Sorry, I encountered an error. Please try again.';
      if (error instanceof Error) {
        errorMessage += ` Error details: ${error.message}`;
      }
      const errorBotMessage: Message = { role: 'bot', content: errorMessage };
      setMessages(prev => [...prev, errorBotMessage]);
    } finally {
      setIsThinking(false);
    }
  }, [isThinking]);

  return { messages, input, setInput, isThinking, handleSendMessage }
}

const MessageComponent = React.memo(({ message, isDarkMode }: { message: Message, isDarkMode: boolean }) => (
  <div className={`flex items-start mb-4 ${message.role === 'user' ? 'justify-end' : ''}`}>
    {message.role === 'bot' && <BotIcon className="w-5 h-5 sm:w-6 sm:h-6 mr-2 text-[#00FFFF] flex-shrink-0" />}
    <div className={`rounded-lg p-2 sm:p-3 max-w-[80%] ${message.role === 'user'
        ? 'bg-[#ADFF2F] text-black'
        : isDarkMode ? 'bg-gray-700' : 'bg-gray-200'
      }`}>
      {message.role === 'user' ? (
        <p className="text-sm sm:text-base break-words">{message.content}</p>
      ) : (
        <Suspense fallback={<div>Loading...</div>}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}  // Add this line
            className={`prose prose-sm max-w-none break-words ${isDarkMode ? 'dark' : ''}`}
            components={{
              a: ({ node, ...props }) => <a {...props} className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer">{props.children}</a>,
              p: ({ node, ...props }) => <p {...props} className={`mb-2 text-sm sm:text-base ${isDarkMode ? 'text-white' : 'text-black'}`} />,
              ul: ({ node, ...props }) => <ul {...props} className="list-disc list-inside mb-2" />,
              ol: ({ node, ...props }) => <ol {...props} className="list-decimal list-inside mb-2" />,
              li: ({ node, ...props }) => <li {...props} className={`mb-1 ${isDarkMode ? 'text-white' : 'text-black'}`} />,
              h1: ({ node, ...props }) => <h1 {...props} className={`text-xl font-bold mb-2 ${isDarkMode ? 'text-white' : 'text-black'}`}>{props.children}</h1>,
              h2: ({ node, ...props }) => <h2 {...props} className={`text-lg font-bold mb-2 ${isDarkMode ? 'text-white' : 'text-black'}`}>{props.children}</h2>,
              h3: ({ node, ...props }) => <h3 {...props} className={`text-md font-bold mb-2 ${isDarkMode ? 'text-white' : 'text-black'}`}>{props.children}</h3>,
              code: ({ node, className, children, ...props }) => {
                const match = /language-(\w+)/.exec(className || '')
                return match ? (
                  <pre className="bg-gray-100 rounded p-2 mb-2 overflow-x-auto">
                    <code className={`language-${match[1]}`} {...props}>
                      {children}
                    </code>
                  </pre>
                ) : (
                  <code {...props} className={`bg-gray-100 rounded px-1 py-0.5 ${isDarkMode ? 'text-black' : ''}`}>
                    {children}
                  </code>
                )
              },
              table: ({node, ...props}) => (
                <table {...props} className={`border-collapse border ${isDarkMode ? 'border-gray-600' : 'border-gray-300'} my-2`} />
              ),
              thead: ({node, ...props}) => (
                <thead {...props} className={isDarkMode ? 'bg-gray-800' : 'bg-gray-100'} />
              ),
              tbody: ({node, ...props}) => <tbody {...props} />,
              tr: ({node, ...props}) => <tr {...props} className="border-b border-gray-300" />,
              th: ({node, ...props}) => <th {...props} className="border border-gray-300 px-4 py-2 text-left" />,
              td: ({node, ...props}) => <td {...props} className="border border-gray-300 px-4 py-2" />,
            }}
          >
            {message.content}
          </ReactMarkdown>
        </Suspense>
      )}
    </div>
    {message.role === 'user' && <UserIcon className="w-5 h-5 sm:w-6 sm:h-6 ml-2 text-[#ADFF2F] flex-shrink-0" />}
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

export default function ChatbotPage() {
  const { isDarkMode, toggleTheme } = useTheme()
  const { messages, input, setInput, isThinking, handleSendMessage } = useChatbot()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  React.useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInput(e.target.value);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !isThinking) {
      handleSendMessage(input);
    }
  };

  return (
    <div className={`flex flex-col h-screen ${isDarkMode ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-800'}`}>
      <header className="bg-gradient-to-r from-[#0066FF] to-[#00FFFF] p-4 text-white font-bold flex items-center justify-between">
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

      <main className="flex-grow flex flex-col overflow-hidden relative">
        {messages.length === 0 && <GeometricShapes />}
        
        {messages.length === 0 ? (
          <div className="flex-grow flex flex-col items-center justify-center px-4">
            <h2 className="text-2xl font-semibold text-center mb-8">How can I assist you with real estate investments today?</h2>
            <div className="w-full max-w-md space-y-4">
              {staticSuggestedQuestions.map((question, index) => (
                <Button
                  key={index}
                  variant="outline"
                  onClick={() => handleSendMessage(question)}
                  className={`w-full text-left ${isDarkMode ? 'bg-gray-800 hover:bg-gray-700' : 'bg-white hover:bg-gray-100'}`}
                >
                  {question}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <ScrollArea className="flex-grow px-4 py-2">
            <div className="max-w-3xl mx-auto">
              {messages.map((message, index) => (
                <MessageComponent key={index} message={message} isDarkMode={isDarkMode} />
              ))}
              {isThinking && (
                <div className="flex items-center mb-4">
                  <BotIcon className="w-6 h-6 mr-2 text-[#00FFFF]" />
                  <div className={`${isDarkMode ? 'bg-gray-700' : 'bg-gray-200'} rounded-lg p-3`}>
                    <Loader2Icon className="w-4 h-4 animate-spin text-[#00FFFF]" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
            <ScrollBar 
              orientation="vertical" 
              className={`w-2 rounded-full transition-colors duration-200 ease-out ${
                isDarkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300'
              }`}
            />
          </ScrollArea>
        )}

        <div className="p-4 flex justify-center">
          <div className={`flex space-x-2 w-full max-w-2xl rounded-full shadow-lg ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
            <Input
              value={input}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder={messages.length === 0 ? "Ask me anything about real estate investments..." : "Type your message..."}
              className={`flex-grow rounded-l-full border-0 focus:ring-0 ${isDarkMode ? 'bg-gray-800 text-white placeholder-gray-400' : 'bg-white text-gray-800 placeholder-gray-500'}`}
              disabled={isThinking}
            />
            <Button
              onClick={() => handleSendMessage(input)}
              className={`rounded-r-full ${isThinking ? 'bg-gray-500' : 'bg-[#ADFF2F] hover:bg-[#9ACD32]'} text-black`}
              disabled={isThinking}
            >
              {isThinking ? <Loader2Icon className="w-4 h-4 animate-spin" /> : <SendIcon className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </main>
    </div>
  )
}
