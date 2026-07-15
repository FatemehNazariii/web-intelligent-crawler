// frontend/app/page.js
'use client';

import { useState, useEffect, useRef } from 'react';
import Sidebar from '@/components/Sidebar';
import ChatMessage from '@/components/ChatMessage';
import ChatInput from '@/components/ChatInput';
import Loading from '@/components/Loading';
import Sources from '@/components/Sources';
import { FaSpider } from 'react-icons/fa';

// کلیدهای localStorage
const STORAGE_KEYS = {
  MESSAGES: 'chat_messages',
  SOURCES: 'chat_sources',
  CONVERSATION_ID: 'chat_conversation_id',
  CHATS: 'chat_history',
  CURRENT_CHAT_ID: 'current_chat_id',
};

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [chats, setChats] = useState([]);
  const [currentChatId, setCurrentChatId] = useState(null);
  const [isTranslating, setIsTranslating] = useState(false);
  const messagesEndRef = useRef(null);

  // ============================================================
  // بارگذاری داده‌ها از localStorage
  // ============================================================
  useEffect(() => {
    // بارگذاری تاریخچه چت‌ها
    const storedChats = localStorage.getItem(STORAGE_KEYS.CHATS);
    let parsedChats = [];
    if (storedChats) {
      try {
        parsedChats = JSON.parse(storedChats);
        if (!Array.isArray(parsedChats)) parsedChats = [];
      } catch (e) {
        parsedChats = [];
      }
    }
    setChats(parsedChats);

    // بارگذاری currentChatId
    const storedCurrentId = localStorage.getItem(STORAGE_KEYS.CURRENT_CHAT_ID);
    let activeId = storedCurrentId || null;

    // اگر currentChatId وجود نداشت یا در لیست چت‌ها نبود، یک چت جدید بساز
    if (!activeId || !parsedChats.some(c => c.id === activeId)) {
      activeId = `chat-${Date.now()}-${Math.random().toString(36).substring(7)}`;
      const newChat = {
        id: activeId,
        title: 'New Chat',
        messages: [],
        sources: [],
        timestamp: Date.now(),
      };
      parsedChats = [newChat, ...parsedChats];
      setChats(parsedChats);
      localStorage.setItem(STORAGE_KEYS.CHATS, JSON.stringify(parsedChats));
      localStorage.setItem(STORAGE_KEYS.CURRENT_CHAT_ID, activeId);
    }

    setCurrentChatId(activeId);

    // بارگذاری پیام‌های چت فعلی
    const currentChat = parsedChats.find(c => c.id === activeId);
    if (currentChat) {
      setMessages(currentChat.messages || []);
      setSources(currentChat.sources || []);
      setConversationId(activeId);
    }

    // اگر پیام‌ها خالی بودند، از storage قبلی هم استفاده کن (برای سازگاری)
    if (currentChat && (!currentChat.messages || currentChat.messages.length === 0)) {
      const storedMessages = localStorage.getItem(STORAGE_KEYS.MESSAGES);
      const storedSources = localStorage.getItem(STORAGE_KEYS.SOURCES);
      if (storedMessages) {
        try {
          const parsed = JSON.parse(storedMessages);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setMessages(parsed);
            // به‌روزرسانی چت فعلی
            updateChat(activeId, parsed, storedSources ? JSON.parse(storedSources) : []);
          }
        } catch (e) {}
      }
    }
  }, []);

  // ============================================================
  // ذخیره‌سازی خودکار چت‌ها
  // ============================================================
  const updateChat = (chatId, newMessages, newSources) => {
    setChats(prev => {
      const updated = prev.map(chat => {
        if (chat.id === chatId) {
          const title = newMessages.length > 0 && newMessages[0].role === 'user'
            ? newMessages[0].content.slice(0, 30) + (newMessages[0].content.length > 30 ? '...' : '')
            : chat.title || 'New Chat';
          return {
            ...chat,
            messages: newMessages,
            sources: newSources || [],
            title: title,
            timestamp: Date.now(),
          };
        }
        return chat;
      });
      localStorage.setItem(STORAGE_KEYS.CHATS, JSON.stringify(updated));
      return updated;
    });
  };

  // ذخیره‌سازی خودکار با هر تغییر messages یا sources
  useEffect(() => {
    if (currentChatId) {
      updateChat(currentChatId, messages, sources);
      // همچنین برای سازگاری با کد قبلی
      if (messages.length > 0) {
        localStorage.setItem(STORAGE_KEYS.MESSAGES, JSON.stringify(messages));
      }
      if (sources.length > 0) {
        localStorage.setItem(STORAGE_KEYS.SOURCES, JSON.stringify(sources));
      }
    }
  }, [messages, sources, currentChatId]);

  // ذخیره conversationId
  useEffect(() => {
    if (conversationId) {
      localStorage.setItem(STORAGE_KEYS.CONVERSATION_ID, conversationId);
      localStorage.setItem(STORAGE_KEYS.CURRENT_CHAT_ID, currentChatId);
    }
  }, [conversationId, currentChatId]);

  // اسکرول به انتهای پیام‌ها
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // ============================================================
  // شروع چت جدید
  // ============================================================
  const handleNewChat = () => {
    const newId = `chat-${Date.now()}-${Math.random().toString(36).substring(7)}`;
    const newChat = {
      id: newId,
      title: 'New Chat',
      messages: [],
      sources: [],
      timestamp: Date.now(),
    };
    setChats(prev => {
      const updated = [newChat, ...prev];
      localStorage.setItem(STORAGE_KEYS.CHATS, JSON.stringify(updated));
      return updated;
    });
    setCurrentChatId(newId);
    setConversationId(newId);
    setMessages([]);
    setSources([]);
    setError(null);
    localStorage.setItem(STORAGE_KEYS.CURRENT_CHAT_ID, newId);
    localStorage.removeItem(STORAGE_KEYS.MESSAGES);
    localStorage.removeItem(STORAGE_KEYS.SOURCES);
  };

  // ============================================================
  // بارگذاری یک چت قدیمی
  // ============================================================
  const loadChat = (chatId) => {
    const chat = chats.find(c => c.id === chatId);
    if (!chat) return;
    setCurrentChatId(chatId);
    setConversationId(chatId);
    setMessages(chat.messages || []);
    setSources(chat.sources || []);
    setError(null);
    localStorage.setItem(STORAGE_KEYS.CURRENT_CHAT_ID, chatId);
    localStorage.setItem(STORAGE_KEYS.MESSAGES, JSON.stringify(chat.messages || []));
    localStorage.setItem(STORAGE_KEYS.SOURCES, JSON.stringify(chat.sources || []));
  };

  // ============================================================
  // حذف یک چت
  // ============================================================
  const deleteChat = (chatId) => {
    // حذف چت از لیست
    const updatedChats = chats.filter(c => c.id !== chatId);
    setChats(updatedChats);
    localStorage.setItem(STORAGE_KEYS.CHATS, JSON.stringify(updatedChats));

    // اگر چت فعلی حذف شده است
    if (chatId === currentChatId) {
      if (updatedChats.length > 0) {
        // بارگذاری اولین چت باقی‌مانده
        loadChat(updatedChats[0].id);
      } else {
        // هیچ چتی باقی نمانده، یک چت جدید بساز
        handleNewChat();
      }
    } else {
      // اگر چت فعلی حذف نشده، مطمئن شو که conversationId درست است
      if (currentChatId) {
        localStorage.setItem(STORAGE_KEYS.CURRENT_CHAT_ID, currentChatId);
      }
    }
  };

  // ============================================================
  // ارسال پیام (پژوهش)
  // ============================================================
  const handleSendMessage = async (message) => {
    if (!message || !message.trim()) return;

    // اگر چت فعلی title پیش‌فرض 'New Chat' بود، آن را به موضوع تغییر بده
    const currentChat = chats.find(c => c.id === currentChatId);
    if (currentChat && currentChat.title === 'New Chat') {
      const newTitle = message.trim().slice(0, 30) + (message.trim().length > 30 ? '...' : '');
      setChats(prev => {
        const updated = prev.map(c => {
          if (c.id === currentChatId) {
            return { ...c, title: newTitle };
          }
          return c;
        });
        localStorage.setItem(STORAGE_KEYS.CHATS, JSON.stringify(updated));
        return updated;
      });
    }

    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMessage]);
    setLoading(true);
    setError(null);
    setSources([]);

    try {
      const response = await fetch('http://127.0.0.1:8000/api/research/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: message.trim(),
          language: 'en',
          max_sources: 3,
          conversation_id: conversationId,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Request processing failed');
      }

      const assistantMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.answer || 'Report could not be generated.',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMessage]);
      setSources(data.sources || []);

    } catch (error) {
      setError(error.message || 'Connection error');
      const errorMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: `❌ Error: ${error.message || 'Something went wrong.'}`,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // تابع ترجمه
  // ============================================================
  const handleTranslate = async (text) => {
    if (!text) return null;

    setIsTranslating(true);
    try {
      const response = await fetch('http://127.0.0.1:8000/api/translate/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          target_language: 'fa',
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Translation failed');
      }

      return data.translated_text;

    } catch (error) {
      console.error('Translation error:', error);
      setError('خطا در ترجمه: ' + error.message);
      return null;
    } finally {
      setIsTranslating(false);
    }
  };

  // ============================================================
  // رندر اصلی
  // ============================================================
  return (
    <div className="flex h-screen bg-[#343541] overflow-hidden">
      <Sidebar
        onNewChat={handleNewChat}
        chats={chats}
        currentChatId={currentChatId}
        onLoadChat={loadChat}
        onDeleteChat={deleteChat}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {/* هدر */}
        <header className="flex items-center justify-between px-4 py-3 bg-[#343541] border-b border-[#4e4f60] shrink-0">
          <div className="flex items-center gap-3">
            <FaSpider className="text-[#10a37f] text-2xl" />
            <h1 className="text-white font-semibold text-base">Web Crawler</h1>
          </div>
          <div className="text-sm text-[#acacbe] hidden sm:block">
            {messages.length > 0 ? `${messages.length} messages` : 'New conversation'}
          </div>
        </header>

        {/* محتوای پیام‌ها */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#343541]">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center text-[#acacbe]">
              <div className="w-16 h-16 rounded-full bg-[#444654] flex items-center justify-center mb-4">
                <FaSpider className="text-4xl text-[#10a37f]" />
              </div>
              <h2 className="text-xl font-semibold text-white mb-2">
                Enter a topic to crawl
              </h2>
              <p className="text-sm max-w-md">
                The intelligent web crawler will find relevant pages, analyze them, and generate a comprehensive report.
              </p>
              <div className="flex flex-wrap gap-2 mt-4 justify-center">
                {['Artificial Intelligence', 'Machine Learning', 'Internet of Things', 'Blockchain'].map((topic) => (
                  <button
                    key={topic}
                    onClick={() => handleSendMessage(topic)}
                    className="px-3 py-1.5 bg-[#444654] hover:bg-[#565869] rounded-full text-sm text-[#ececec] transition-colors"
                  >
                    {topic}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, index) => (
                <ChatMessage
                  key={msg.id || index}
                  message={msg}
                  onTranslate={handleTranslate}
                  isTranslating={isTranslating}
                />
              ))}
              {loading && <Loading />}
              {error && (
                <div className="bg-[#444654] rounded-lg p-4 text-red-400 text-sm border border-red-800/30">
                  ⚠️ {error}
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* منابع */}
        {sources.length > 0 && (
          <div className="bg-[#2d2e3a] border-t border-[#4e4f60] px-4 py-2 shrink-0">
            <Sources sources={sources} />
          </div>
        )}

        {/* ورودی */}
        <div className="bg-[#343541] border-t border-[#4e4f60] p-4 shrink-0">
          <ChatInput onSend={handleSendMessage} disabled={loading} />
          <p className="text-xs text-[#565869] text-center mt-2">
            The intelligent crawler may have errors. Please verify important information.
          </p>
        </div>
      </div>
    </div>
  );
}