// frontend/components/ChatMessage.jsx
'use client';

import { useState } from 'react';
import { FaRobot, FaUser, FaLanguage } from 'react-icons/fa';

export default function ChatMessage({ 
  message, 
  onTranslate, 
  isTranslating 
}) {
  const isUser = message.role === 'user';
  const [showTranslation, setShowTranslation] = useState(false);
  const [translatedContent, setTranslatedContent] = useState(null);

  // تشخیص زبان متن
  const hasPersian = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/.test(message.content);
  const hasEnglish = /[a-zA-Z]/.test(message.content);
  const isPersian = hasPersian && !hasEnglish;
  const isEnglish = hasEnglish && !hasPersian;
  const isMixed = hasPersian && hasEnglish;

  // جهت متن
  const textDirection = isPersian ? 'rtl' : 'ltr';
  const textAlign = isPersian ? 'right' : 'left';

  // نمایش دکمه ترجمه فقط برای پیام‌های انگلیسی
  const showTranslateButton = !isUser && isEnglish && message.content.length > 50;

  // تبدیل Markdown ساده به HTML
  const formatContent = (content) => {
    if (!content) return '';
    return content
      .split('\n')
      .map((line) => {
        if (line.startsWith('## ')) {
          return `<h2 class="text-lg font-bold mt-4 mb-2 text-white">${line.slice(3)}</h2>`;
        }
        if (line.startsWith('### ')) {
          return `<h3 class="text-md font-semibold mt-3 mb-1 text-[#9a94b8]">${line.slice(4)}</h3>`;
        }
        if (line.startsWith('- ')) {
          return `<li class="ml-4 text-[#e8e4f0]">${line.slice(2)}</li>`;
        }
        if (line.startsWith('**') && line.endsWith('**')) {
          return `<strong class="text-[#7c6df0]">${line.slice(2, -2)}</strong>`;
        }
        if (line.trim() === '---') {
          return `<hr class="my-4 border-[#2e2a4a]" />`;
        }
        if (line.trim() === '') return '<br/>';
        return `<p class="mb-2 text-[#e8e4f0]">${line}</p>`;
      })
      .join('');
  };

  // هندل کلیک روی دکمه ترجمه
  const handleTranslateClick = async () => {
    if (translatedContent) {
      setShowTranslation(!showTranslation);
      return;
    }

    const result = await onTranslate(message.content);
    if (result) {
      setTranslatedContent(result);
      setShowTranslation(true);
    }
  };

  return (
    <div
      className={`
        flex items-start gap-4 px-4 py-4 fade-in
        ${isUser ? 'bg-[#0f0e1a]' : 'bg-[#0f0e1a]'}
      `}
    >
      {/* آواتار */}
      <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 mt-0.5">
        {isUser ? (
          <div className="w-full h-full rounded-full bg-[#7c6df0] flex items-center justify-center shadow-lg">
            <FaUser className="text-white text-sm" />
          </div>
        ) : (
          <div className="w-full h-full rounded-full bg-gradient-to-br from-[#7c6df0] to-[#4a3a8a] flex items-center justify-center shadow-lg">
            <FaRobot className="text-white text-sm" />
          </div>
        )}
      </div>

      {/* محتوای پیام */}
      <div className="flex-1 min-w-0">
        <div
          className={`
            ${isUser ? 'chat-message-user' : 'chat-message-assistant'}
            message-text
            ${isPersian ? 'message-rtl' : 'message-ltr'}
          `}
          style={{ direction: textDirection, textAlign: textAlign }}
        >
          <div
            className="report-content"
            style={{ direction: textDirection, textAlign: textAlign }}
            dangerouslySetInnerHTML={{
              __html: isUser ? message.content : formatContent(message.content),
            }}
          />
        </div>

        {/* نمایش ترجمه */}
        {showTranslation && translatedContent && (
          <div className="mt-3 p-4 bg-[#1a1730] rounded-xl border border-[#2e2a4a]">
            <div className="text-xs text-[#9a94b8] mb-2 flex items-center gap-1">
              <FaLanguage className="text-sm text-[#7c6df0]" />
              <span>🇮🇷 ترجمه فارسی:</span>
            </div>
            <div 
              className="text-sm text-[#e8e4f0] report-content message-rtl"
              dangerouslySetInnerHTML={{ __html: formatContent(translatedContent) }}
            />
          </div>
        )}

        {/* دکمه ترجمه */}
        {showTranslateButton && (
          <button
            onClick={handleTranslateClick}
            disabled={isTranslating}
            className="mt-2 flex items-center gap-1.5 text-xs text-[#9a94b8] hover:text-[#7c6df0] transition-colors disabled:opacity-50"
          >
            <FaLanguage className="text-sm" />
            {isTranslating ? 'در حال ترجمه...' : (translatedContent ? 'مشاهده ترجمه فارسی' : 'ترجمه به فارسی')}
          </button>
        )}
      </div>
    </div>
  );
}