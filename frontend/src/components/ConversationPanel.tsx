"use client";

import type { ConversationMessage } from "@/lib/api";

interface ConversationPanelProps {
  messages: ConversationMessage[];
}

export default function ConversationPanel({ messages }: ConversationPanelProps) {
  if (messages.length === 0) {
    return (
      <div className="flex h-48 items-center justify-center text-sm text-zinc-400">
        Start speaking to begin the conversation.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 overflow-y-auto max-h-96 p-2">
      {messages.map((msg, i) => (
        <div
          key={i}
          className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[80%] rounded-lg px-4 py-2 text-sm ${
              msg.role === "user"
                ? "bg-blue-600 text-white"
                : "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
            }`}
          >
            {msg.content}
          </div>
        </div>
      ))}
    </div>
  );
}
