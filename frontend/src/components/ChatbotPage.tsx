import * as React from 'react'
import { useState, useCallback, useRef, lazy, Suspense } from 'react'
import { Button } from "./ui/button.tsx"
import { Input } from "./ui/input.tsx"
import { ScrollArea } from "./ui/scroll-area.tsx"
import { SendIcon, BotIcon, UserIcon, Loader2Icon, SunIcon, MoonIcon } from 'lucide-react'
import axios from 'axios'

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
  const [showSuggestedQuestions, setShowSuggestedQuestions] = useState(true)

  const handleSendMessage = useCallback(async (message: string) => {
    if (message.trim() === '' || isThinking) return;

    const newUserMessage: Message = { role: 'user', content: message.trim() };
    setMessages(prev => [...prev, newUserMessage]);
    setInput('');
    setIsThinking(true);
    setShowSuggestedQuestions(false);

    try {
      const response = await axios.post('/api/ask', { text: message });

      if (response.data && response.data.answer) {
        const botMessage: Message = { role: 'bot', content: response.data.answer };
        setMessages(prev => [...prev, botMessage]);
      } else {
        throw new Error('Unexpected response format');
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = { role: 'bot', content: 'Sorry, I encountered an error. Please try again.' };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsThinking(false);
    }
  }, [isThinking]);

  return { messages, input, setInput, isThinking, showSuggestedQuestions, handleSendMessage }
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
            remarkPlugins={[]}
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

export default function ChatbotPage() {
  const { isDarkMode, toggleTheme } = useTheme()
  const { messages, input, setInput, isThinking, showSuggestedQuestions, handleSendMessage } = useChatbot()
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
    <div className={`flex flex-col items-center justify-center min-h-screen ${isDarkMode ? 'bg-gradient-to-b from-gray-900 to-gray-800 text-white' : 'bg-gradient-to-b from-gray-100 to-white text-gray-800'} p-2 sm:p-4`}>
      <div className={`w-full max-w-2xl ${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-xl overflow-hidden`}>
        <div className="bg-gradient-to-r from-[#0066FF] to-[#00FFFF] p-3 sm:p-4 text-white font-bold flex items-center justify-between">
          <div className="flex items-center">
            <BotIcon className="mr-2" />
            <span className="text-sm sm:text-base">DAO PropTech Assistant</span>
          </div>
          <Button variant="outline" size="sm" onClick={toggleTheme} className="text-white border-white hover:bg-white/20">
            {isDarkMode ? <SunIcon className="h-4 w-4" /> : <MoonIcon className="h-4 w-4" />}
          </Button>
        </div>

        <ScrollArea className="h-[350px] sm:h-[400px] p-2 sm:p-4">
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
        </ScrollArea>

        {showSuggestedQuestions && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 p-2 sm:p-4">
            {staticSuggestedQuestions.map((question, index) => (
              <Button
                key={index}
                variant="outline"
                size="sm"
                onClick={() => handleSendMessage(question)}
                className={`flex items-center justify-start space-x-2 text-xs sm:text-sm ${isDarkMode
                    ? 'bg-gray-700 hover:bg-gray-600 text-white border-gray-600'
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-800 border-gray-300'
                  }`}
                disabled={isThinking}
              >
                <span className="truncate">{question}</span>
              </Button>
            ))}
          </div>
        )}

        <div className={`p-2 sm:p-4 ${isDarkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
          <div className="flex space-x-2">
            <Input
              value={input}
              onChange={handleInputChange}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              className={`flex-grow text-sm sm:text-base ${isDarkMode
                  ? 'bg-gray-600 text-white placeholder-gray-400 border-gray-500'
                  : 'bg-white text-gray-800 placeholder-gray-500 border-gray-300'
                }`}
              disabled={isThinking}
            />
            <Button
              onClick={() => handleSendMessage(input)}
              className={`${isThinking ? 'bg-gray-500' : 'bg-[#ADFF2F] hover:bg-[#9ACD32]'} text-black`}
              disabled={isThinking}
            >
              {isThinking ? <Loader2Icon className="w-4 h-4 animate-spin" /> : <SendIcon className="w-4 h-4" />}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}