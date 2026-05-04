/**
 * AI Session Ledger — types and seed data
 * Tracks Zed / Claude / Cursor session outputs as a searchable, collapsible log.
 * Stored as JSON; loaded at build time or client-side from /data/ledger/sessions.json
 */

export type LedgerRole = 'user' | 'assistant' | 'system' | 'tool';
export type LedgerTag =
  | 'models'
  | 'training'
  | 'distillation'
  | 'architecture'
  | 'ollama'
  | 'lmstudio'
  | 'zeta'
  | 'nanochat'
  | 'todo'
  | 'fix'
  | 'setup'
  | 'vision'
  | 'reasoning'
  | 'code'
  | 'pipeline'
  | 'manifest'
  | 'vc';

export type LedgerMessage = {
  id: string;
  role: LedgerRole;
  /** Markdown content */
  content: string;
  /** ISO timestamp */
  ts: string;
  /** Collapsed by default in UI if true */
  collapsed?: boolean;
  /** Code blocks or tool outputs embedded in this message */
  attachments?: LedgerAttachment[];
};

export type LedgerAttachment = {
  kind: 'code' | 'table' | 'shell' | 'json' | 'todo';
  label: string;
  content: string;
  lang?: string;
};

export type LedgerEntry = {
  id: string;
  /** Short title shown in the ledger index */
  title: string;
  /** One-line summary */
  summary: string;
  /** ISO date */
  date: string;
  /** Source tool */
  source: 'zed' | 'cursor' | 'copilot' | 'manual';
  tags: LedgerTag[];
  messages: LedgerMessage[];
  /** Todo items extracted from this session */
  todos?: LedgerTodo[];
};

export type LedgerTodo = {
  id: string;
  text: string;
  status: 'open' | 'done' | 'blocked';
  priority: 'high' | 'mid' | 'low';
  tags: LedgerTag[];
};
