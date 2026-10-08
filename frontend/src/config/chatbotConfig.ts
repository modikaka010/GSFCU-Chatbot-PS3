import type { ChatErrorCode } from '../types/chatbot';

const env =
  ((import.meta as unknown as { env?: Record<string, string | undefined> }).env) ?? {};

export type TransportKind = 'mock' | 'rest' | 'socket';

export const chatbotConfig = {
  /** e.g. VITE_CHAT_API_URL=https://api.example.com  (never hardcode production URLs) */
  apiBaseUrl: env.VITE_CHAT_API_URL ?? '',
  /** Optional Socket.IO/WebSocket URL, used only when transport = 'socket'. */
  socketUrl: env.VITE_CHAT_SOCKET_URL ?? '',
  profileUrl: env.VITE_USER_PROFILE_URL ?? '',
  /** No API URL configured => mock. Override with VITE_CHAT_TRANSPORT=rest|socket|mock. */
  transport: (env.VITE_CHAT_TRANSPORT ??
    (env.VITE_CHAT_API_URL ? 'rest' : 'mock')) as TransportKind,

  endpoints: {
    message: '/chat/message',
    conversations: '/chat/conversations',
    conversation: (id: string) => `/chat/conversations/${encodeURIComponent(id)}`,
    profile: '/api/user/profile',
  },

  requestTimeoutMs: 30_000,
  maxMessageLength: 2000,
  assistantName: 'GSFC University Assistant',
  zIndex: 1000,

  /** Small prompt bubble above the launcher on page load. Edit the copy here. */
  teaser: {
    message: "Hello! I'm the GSFC University Assistant. 👋 Have a question about the university? I can help.",
    questions: ['Which programs does GSFC University offer?', 'How do I apply for admission?'],
    showAfterMs: 1500,
  },

  /** User-facing copy. Raw backend errors are never shown. */
  errorMessages: {
    network: "I'm having trouble connecting right now. Please try again.",
    timeout: 'That took longer than expected. Please try again.',
    auth: 'Your session has expired. Please sign in again to continue.',
    empty: "I couldn't come up with a response. Please try rephrasing your question.",
    server: 'Something went wrong on our side. Please try again in a moment.',
    disconnected: 'The connection was lost. Please try again.',
  } satisfies Record<ChatErrorCode, string>,
} as const;