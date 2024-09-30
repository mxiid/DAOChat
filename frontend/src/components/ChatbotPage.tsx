import * as React from 'react'
import { useState, useEffect, useCallback } from 'react'
import { Button } from "./ui/button.tsx"
import { Input } from "./ui/input.tsx"
import { ScrollArea } from "./ui/scroll-area.tsx"
import { SendIcon, BotIcon, UserIcon, Loader2Icon } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface Message {
  role: 'user' | 'bot';
  content: string;
}

interface SuggestQuestionsRequest {
  context: string;
}

export default function ChatbotPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'bot', content: 'Hello! How can I assist you with real estate investments today?' }
  ])
  const [input, setInput] = useState('')
  const [isThinking, setIsThinking] = useState(false)
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([])
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false)
  const [isDarkMode, setIsDarkMode] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const defaultSuggestedQuestions = [
    { icon: <ImageIcon className="w-6 h-6" />, text: "Show investment opportunities" },
    { icon: <SearchIcon className="w-6 h-6" />, text: "Explain value-based pricing" },
    { icon: <FileTextIcon className="w-6 h-6" />, text: "Summarize market trends" },
    { icon: <PenToolIcon className="w-6 h-6" />, text: "Calculate potential returns" },
  ]

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleSend = useCallback(async () => {
    if (input.trim() && !isThinking) {
      const newUserMessage: Message = { role: 'user', content: input.trim() };
      setMessages(prev => [...prev, newUserMessage]);
      setInput('');
      setIsThinking(true);

      try {
        const response = await fetch('http://localhost:8000/ask', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ text: input.trim() }),
        })
        const data = await response.json()
        const newBotMessage: Message = { role: 'bot', content: data.answer };
        setMessages(prev => [...prev, newBotMessage]);
        await generateSuggestedQuestions(data.answer)
      } catch (error) {
        console.error('Error:', error)
        const errorMessage: Message = { role: 'bot', content: 'Sorry, an error occurred. Please try again.' };
        setMessages(prev => [...prev, errorMessage]);
      } finally {
        setIsThinking(false);
      }
    }
  }, [input, isThinking])

  const generateSuggestedQuestions = async (lastAnswer: string) => {
    setIsLoadingSuggestions(true);
    try {
      const request: SuggestQuestionsRequest = { context: lastAnswer };
      const response = await fetch('http://localhost:8000/suggest_questions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      })
      if (!response.ok) {
        throw new Error('Failed to fetch suggested questions');
      }
      const data = await response.json()
      setSuggestedQuestions(data.suggested_questions || [])
    } catch (error) {
      console.error('Error generating suggested questions:', error)
      setSuggestedQuestions([])
    } finally {
      setIsLoadingSuggestions(false);
    }
  }

  const handleSuggestedQuestion = async (question: string) => {
    setInput(question);
    await handleSend();
  }

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode)
  }

  return (
    <div className={`flex flex-col items-center justify-center min-h-screen ${isDarkMode ? 'bg-gradient-to-b from-gray-900 to-gray-800 text-white' : 'bg-gradient-to-b from-gray-100 to-white text-gray-800'} p-4`}>
      <div className={`w-full max-w-2xl ${isDarkMode ? 'bg-gray-800' : 'bg-white'} rounded-lg shadow-xl overflow-hidden`}>
        {/* Header */}
        <div className="bg-gradient-to-r from-[#0066FF] to-[#00FFFF] p-4 text-white font-bold flex items-center justify-between">
          <div className="flex items-center">
            <BotIcon className="mr-2" />
            DAO PropTech Assistant
          </div>
          <Button variant="outline" size="icon" onClick={toggleTheme} className="text-white border-white hover:bg-white/20">
            {isDarkMode ? <SunIcon className="h-4 w-4" /> : <MoonIcon className="h-4 w-4" />}
          </Button>
        </div>

        {/* Main Chat Area */}
        <ScrollArea className="h-[400px] p-4">
          {messages.map((message, index) => (
            <div key={index} className={`flex items-start mb-4 ${message.role === 'user' ? 'justify-end' : ''}`}>
              {message.role === 'bot' && <BotIcon className="w-6 h-6 mr-2 text-[#00FFFF]" />}
              <div className={`rounded-lg p-3 max-w-[70%] ${
                message.role === 'user' 
                  ? 'bg-[#ADFF2F] text-black' 
                  : isDarkMode ? 'bg-gray-700' : 'bg-gray-200'
              }`}>
                {message.role === 'user' ? (
                  message.content
                ) : (
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    className="prose prose-sm max-w-none"
                    components={{
                      a: ({node, ...props}) => <a {...props} className="text-blue-500 hover:underline" target="_blank" rel="noopener noreferrer">{props.children}</a>,
                      p: ({node, ...props}) => <p {...props} className="mb-2" />,
                      ul: ({node, ...props}) => <ul {...props} className="list-disc list-inside mb-2" />,
                      ol: ({node, ...props}) => <ol {...props} className="list-decimal list-inside mb-2" />,
                      li: ({node, ...props}) => <li {...props} className="mb-1" />,
                      h1: ({node, ...props}) => <h1 {...props} className="text-xl font-bold mb-2">{props.children}</h1>,
                      h2: ({node, ...props}) => <h2 {...props} className="text-lg font-bold mb-2">{props.children}</h2>,
                      h3: ({node, ...props}) => <h3 {...props} className="text-md font-bold mb-2">{props.children}</h3>,
                      code: ({node, className, children, ...props}) => {
                        const match = /language-(\w+)/.exec(className || '')
                        return match ? (
                          <pre className="bg-gray-100 rounded p-2 mb-2 overflow-x-auto">
                            <code className={`language-${match[1]}`} {...props}>
                              {children}
                            </code>
                          </pre>
                        ) : (
                          <code {...props} className="bg-gray-100 rounded px-1 py-0.5">
                            {children}
                          </code>
                        )
                      },
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                )}
              </div>
              {message.role === 'user' && <UserIcon className="w-6 h-6 ml-2 text-[#ADFF2F]" />}
            </div>
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

        {/* Suggested Questions */}
        <div className="grid grid-cols-2 gap-2 p-4">
          {(suggestedQuestions.length > 0 ? suggestedQuestions : defaultSuggestedQuestions.map(q => q.text)).map((question, index) => (
            <Button
              key={index}
              variant="outline"
              size="lg"
              onClick={() => handleSuggestedQuestion(question)}
              className={`flex items-center justify-start space-x-2 ${
                isDarkMode 
                  ? 'bg-gray-700 hover:bg-gray-600 text-white border-gray-600' 
                  : 'bg-gray-200 hover:bg-gray-300 text-gray-800 border-gray-300'
              }`}
              disabled={isThinking}
            >
              {defaultSuggestedQuestions[index]?.icon}
              <span className="text-sm">{question}</span>
            </Button>
          ))}
        </div>

        {/* Input Area */}
        <div className={`p-4 ${isDarkMode ? 'bg-gray-700' : 'bg-gray-200'}`}>
          <div className="flex space-x-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              className={`flex-grow ${
                isDarkMode 
                  ? 'bg-gray-600 text-white placeholder-gray-400 border-gray-500' 
                  : 'bg-white text-gray-800 placeholder-gray-500 border-gray-300'
              }`}
              disabled={isThinking}
            />
            <Button 
              onClick={handleSend} 
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
