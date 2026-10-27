import { useCallback, useEffect, useRef, useState } from "react";

import { assistantApi } from "../services/novaApi";
import type { AssistantReply } from "../services/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  reply?: AssistantReply;
  failed?: boolean;
}

interface StoredChat {
  conversationId: string | null;
  messages: ChatMessage[];
}

export const CHAT_STORAGE_PREFIX = "nova_health_chat_";
const MAX_STORED_MESSAGES = 60;

function load(key: string): StoredChat {
  try {
    const raw = window.sessionStorage.getItem(key);
    if (raw) return JSON.parse(raw) as StoredChat;
  } catch {
    // ignore unreadable storage
  }
  return { conversationId: null, messages: [] };
}

let messageCounter = 0;
const nextId = () => `m${Date.now().toString(36)}${(messageCounter++).toString(36)}`;

/**
 * Chat state for the assistant. The conversation is kept in sessionStorage
 * (per signed-in user) so it survives moving to another page and back, and
 * is cleared on sign-out or when the tab closes.
 */
export function useAssistantChat(userId: number) {
  const storageKey = `${CHAT_STORAGE_PREFIX}${userId}`;
  const [chat, setChat] = useState<StoredChat>(() => load(storageKey));
  const [sending, setSending] = useState(false);
  const sendingRef = useRef(false);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(
        storageKey,
        JSON.stringify({ ...chat, messages: chat.messages.slice(-MAX_STORED_MESSAGES) }),
      );
    } catch {
      // storage full or unavailable: the chat still works for this page view
    }
  }, [chat, storageKey]);

  const send = useCallback(
    async (text: string) => {
      const message = text.trim();
      // One message at a time keeps the conversation order unambiguous.
      if (!message || sendingRef.current) return;
      sendingRef.current = true;
      setSending(true);
      const userMessage: ChatMessage = { id: nextId(), role: "user", text: message };
      setChat((current) => ({ ...current, messages: [...current.messages, userMessage] }));

      try {
        const reply = await assistantApi.send(message, chat.conversationId);
        setChat((current) => ({
          conversationId: reply.conversation_id,
          messages: [...current.messages, { id: nextId(), role: "assistant", text: reply.reply, reply }],
        }));
      } catch (error) {
        const detail = error instanceof Error ? error.message : "Something went wrong.";
        setChat((current) => ({
          // A missing conversation (e.g. after a database reset) starts a fresh one next time.
          conversationId: detail.includes("Conversation not found") ? null : current.conversationId,
          messages: [
            ...current.messages,
            {
              id: nextId(),
              role: "assistant",
              failed: true,
              text: `${detail} Your message was not processed. For an emergency, call 112 or 108.`,
            },
          ],
        }));
      } finally {
        sendingRef.current = false;
        setSending(false);
      }
    },
    [chat.conversationId],
  );

  const reset = useCallback(() => setChat({ conversationId: null, messages: [] }), []);

  const lastReply = [...chat.messages].reverse().find((m) => m.reply)?.reply ?? null;
  return { messages: chat.messages, conversationId: chat.conversationId, sending, send, reset, lastReply };
}
