"use client";

import { useState } from "react";

import Sidebar from "../components/Sidebar";
import ChatInput from "../components/ChatInput";
import ChatMessage from "../components/ChatMessage";
import Loading from "../components/Loading";
import Sources from "../components/Sources";

export default function Home() {
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      type: "text",
      content:
        "سلام 👋\nمن یک Smart Research Assistant هستم. یک موضوع وارد کن تا در وب جستجو کنم، منابع مرتبط را بخوانم و یک پاسخ خلاصه و ساختارمند تحویل بدهم.",
    },
  ]);

  const sendMessage = async () => {
    if (!topic.trim() || loading) return;

    const userTopic = topic.trim();

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        type: "text",
        content: userTopic,
      },
    ]);

    setTopic("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/api/crawl/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic: userTopic,
        }),
      });

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          type: "report",
          content: data.final_summary,
          topic: data.topic,
          count: data.count,
          results: data.results || [],
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          type: "text",
          content:
            "❌ خطا در ارتباط با سرور. مطمئن شو Django backend روی http://127.0.0.1:8000 اجراست.",
        },
      ]);
    }

    setLoading(false);
  };

  return (
    <div className="flex h-screen bg-[#343541] text-white">
      <Sidebar />

      <main className="flex flex-col flex-1 h-screen">
        <div className="border-b border-gray-700 p-4 text-center font-semibold">
          Smart Research Assistant
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto">
            {messages.map((msg, index) => (
              <ChatMessage key={index} role={msg.role}>
                {msg.type === "report" ? (
                  <div>
                    <div className="mb-3 text-sm text-gray-300">
                      برای موضوع{" "}
                      <span className="font-semibold text-white">
                        {msg.topic}
                      </span>
                      ، تعداد{" "}
                      <span className="font-semibold text-white">
                        {msg.count}
                      </span>{" "}
                      منبع مرتبط بررسی شد.
                    </div>

                    <h2 className="font-bold text-lg mb-3">📌 Final Answer</h2>

                    <p className="leading-8 text-gray-100">{msg.content}</p>

                    <Sources results={msg.results} />
                  </div>
                ) : (
                  <p className="leading-8">{msg.content}</p>
                )}
              </ChatMessage>
            ))}

            {loading && (
              <ChatMessage role="assistant">
                <Loading />
              </ChatMessage>
            )}
          </div>
        </div>

        <ChatInput topic={topic} setTopic={setTopic} onSend={sendMessage} />
      </main>
    </div>
  );
}