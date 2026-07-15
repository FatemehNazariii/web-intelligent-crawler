// frontend/components/ChatInput.jsx
'use client';

import { useState, useRef, useEffect } from 'react';
import { FaArrowUp } from 'react-icons/fa';

export default function ChatInput({ onSend, disabled = false }) {
  const [input, setInput] = useState('');
  const [direction, setDirection] = useState('ltr');
  const textareaRef = useRef(null);

  const detectDirection = (text) => {
    const persianRegex = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
    return persianRegex.test(text) ? 'rtl' : 'ltr';
  };

  useEffect(() => {
    setDirection(detectDirection(input));
  }, [input]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSend(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2 max-w-3xl mx-auto w-full bg-[#1a1730] rounded-2xl border border-[#2e2a4a] focus-within:border-[#7c6df0] transition-colors p-1.5 shadow-lg"
    >
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Enter a research topic..."
        disabled={disabled}
        rows={1}
        dir={direction}
        className="flex-1 bg-transparent text-[#e8e4f0] placeholder-[#6a6488] outline-none resize-none px-3 py-2 text-sm min-h-[48px] max-h-[200px]"
        style={{
          fontFamily: 'inherit',
          textAlign: direction === 'rtl' ? 'right' : 'left',
        }}
      />

      <button
        type="submit"
        disabled={disabled || !input.trim()}
        className={`
          w-10 h-10 rounded-xl flex items-center justify-center
          ${input.trim() && !disabled
            ? 'bg-[#7c6df0] hover:bg-[#6a5bd8] text-white shadow-lg shadow-[#7c6df0]/30'
            : 'bg-[#2e2a4a] text-[#6a6488] cursor-not-allowed'}
          transition-all duration-200 shrink-0
        `}
      >
        <FaArrowUp className="text-sm" />
      </button>
    </form>
  );
}