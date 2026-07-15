// frontend/components/Sidebar.jsx
'use client';

import { useState } from 'react';
import { FaPlus, FaBars, FaSpider, FaTrash, FaClock } from 'react-icons/fa';

export default function Sidebar({
  onNewChat,
  chats = [],
  currentChatId,
  onLoadChat,
  onDeleteChat,
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const toggleSidebar = () => setIsOpen(!isOpen);

  const handleDelete = (chatId, e) => {
    e.stopPropagation();
    setConfirmDelete(chatId);
  };

  const confirmDeleteChat = (chatId) => {
    onDeleteChat(chatId);
    setConfirmDelete(null);
  };

  const cancelDelete = () => setConfirmDelete(null);

  return (
    <>
      <button
        onClick={toggleSidebar}
        className="md:hidden fixed top-3 left-3 z-50 bg-[#0a0815] text-white p-2.5 rounded-xl shadow-lg border border-[#2e2a4a]"
      >
        <FaBars className="text-xl" />
      </button>

      <div
        className={`
          fixed md:static inset-y-0 left-0 z-40
          w-64 bg-[#0a0815] flex flex-col
          transition-transform duration-300 ease-in-out
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
          md:translate-x-0
          border-r border-[#1a1730]
        `}
      >
        {/* هدر سایدبار */}
        <div className="flex items-center gap-2 px-3 h-14 border-b border-[#1a1730] shrink-0">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#7c6df0] to-[#4a3a8a] flex items-center justify-center shadow-lg">
            <FaSpider className="text-white text-lg" />
          </div>
          <span className="text-white font-semibold text-sm">Web Crawler</span>
        </div>

        {/* دکمه New Chat */}
        <button
          onClick={() => {
            onNewChat();
            setIsOpen(false);
          }}
          className="flex items-center gap-2 mx-3 mt-4 px-3 py-2.5 rounded-xl border border-[#2e2a4a] text-white text-sm hover:bg-[#1a1730] hover:border-[#7c6df0] transition-all"
        >
          <FaPlus className="text-[#7c6df0] text-sm" />
          <span>New Chat</span>
        </button>

        {/* لیست چت‌ها */}
        <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
          {chats.length === 0 ? (
            <div className="text-[#6a6488] text-xs text-center py-6">
              No chats yet
            </div>
          ) : (
            chats.map((chat) => (
              <div
                key={chat.id}
                onClick={() => {
                  if (chat.id !== currentChatId) {
                    onLoadChat(chat.id);
                    setIsOpen(false);
                  }
                }}
                className={`
                  group flex items-center justify-between px-3 py-2 rounded-xl cursor-pointer
                  ${chat.id === currentChatId
                    ? 'bg-[#1a1730] text-white border border-[#2e2a4a]'
                    : 'text-[#9a94b8] hover:bg-[#1a1730]'
                  }
                  transition-all
                `}
              >
                <div className="flex items-center gap-2.5 truncate">
                  <FaClock className="text-[#6a6488] text-xs shrink-0" />
                  <span className="text-sm truncate">
                    {chat.title || 'Untitled'}
                  </span>
                </div>

                {confirmDelete === chat.id ? (
                  <div className="flex items-center gap-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        confirmDeleteChat(chat.id);
                      }}
                      className="text-xs text-red-400 hover:text-red-300 bg-red-900/30 px-2 py-0.5 rounded"
                    >
                      Yes
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        cancelDelete();
                      }}
                      className="text-xs text-[#6a6488] hover:text-white px-2 py-0.5 rounded"
                    >
                      No
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={(e) => handleDelete(chat.id, e)}
                    className="opacity-0 group-hover:opacity-100 text-[#6a6488] hover:text-red-400 transition-all"
                  >
                    <FaTrash className="text-xs" />
                  </button>
                )}
              </div>
            ))
          )}
        </div>

        {/* پایین سایدبار */}
        <div className="border-t border-[#1a1730] p-3 shrink-0">
          <div className="text-[#6a6488] text-xs text-center">
            {chats.length} chats · v1.0.0
          </div>
        </div>
      </div>

      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 md:hidden"
          onClick={toggleSidebar}
        />
      )}
    </>
  );
}