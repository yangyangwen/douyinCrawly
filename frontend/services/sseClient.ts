/**
 * SSE client implemented with fetch streaming so custom headers can be sent.
 */

import { DouyinWork } from '../types';
import { buildRequestHeaders } from './api';

export type SSEEventType = 'task_result' | 'task_status' | 'task_error' | 'log';

export interface TaskResultEvent {
  task_id: string;
  data: DouyinWork[];
  total: number;
}

export interface TaskStatusEvent {
  task_id: string;
  status: string;
  progress?: number;
  result_count?: number;
  detected_type?: string;
  total?: number;
  is_incremental?: boolean;
}

export interface TaskErrorEvent {
  task_id: string;
  error: string;
}

export interface LogEvent {
  id: string;
  timestamp: string;
  level: string;
  message: string;
}

type EventHandler<T> = (data: T) => void;

const CONNECTING = 0;
const OPEN = 1;
const CLOSED = 2;

class SSEClient {
  private abortController: AbortController | null = null;
  private url = '';
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 5;
  private readonly reconnectDelay = 2000;
  private connectionState: typeof CONNECTING | typeof OPEN | typeof CLOSED = CLOSED;
  private manuallyClosed = false;

  private handlers: {
    task_result: Set<EventHandler<TaskResultEvent>>;
    task_status: Set<EventHandler<TaskStatusEvent>>;
    task_error: Set<EventHandler<TaskErrorEvent>>;
    log: Set<EventHandler<LogEvent>>;
  } = {
    task_result: new Set(),
    task_status: new Set(),
    task_error: new Set(),
    log: new Set(),
  };

  connect(url: string): void {
    if (this.connectionState === OPEN || this.connectionState === CONNECTING) {
      console.warn('[SSE] already connected or connecting');
      return;
    }

    this.url = url;
    this.manuallyClosed = false;
    console.log('[SSE] connecting...', url);
    void this.openConnection();
  }

  private async openConnection(): Promise<void> {
    if (!this.url) {
      return;
    }

    this.connectionState = CONNECTING;
    const abortController = new AbortController();
    this.abortController = abortController;

    try {
      const response = await fetch(this.url, {
        method: 'GET',
        headers: buildRequestHeaders(
          {
            Accept: 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
          { includeJsonContentType: false },
        ),
        cache: 'no-store',
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`SSE HTTP ${response.status}`);
      }

      if (!response.body) {
        throw new Error('SSE response body is empty');
      }

      console.log('[SSE] connected');
      this.connectionState = OPEN;
      this.reconnectAttempts = 0;
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) {
          buffer += decoder.decode();
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        buffer = this.processBuffer(buffer);
      }

      if (buffer.trim()) {
        this.processMessage(buffer);
      }

      if (!this.manuallyClosed && !abortController.signal.aborted) {
        console.warn('[SSE] connection closed by server');
        this.connectionState = CLOSED;
        this.scheduleReconnect();
      }
    } catch (error) {
      if (abortController.signal.aborted || this.manuallyClosed) {
        return;
      }

      this.connectionState = CLOSED;
      console.error('[SSE] connection error:', error);
      this.scheduleReconnect();
    } finally {
      if (this.abortController === abortController) {
        this.abortController = null;
      }

      if (this.connectionState === CONNECTING) {
        this.connectionState = CLOSED;
      }
    }
  }

  private processBuffer(buffer: string): string {
    const chunks = buffer.split(/\r?\n\r?\n/);
    const remainder = chunks.pop() ?? '';

    for (const chunk of chunks) {
      this.processMessage(chunk);
    }

    return remainder;
  }

  private processMessage(message: string): void {
    if (!message.trim()) {
      return;
    }

    let eventType: SSEEventType | null = null;
    const dataLines: string[] = [];

    for (const rawLine of message.split(/\r?\n/)) {
      if (!rawLine || rawLine.startsWith(':')) {
        continue;
      }

      const separatorIndex = rawLine.indexOf(':');
      const field = separatorIndex === -1 ? rawLine : rawLine.slice(0, separatorIndex);
      let value = separatorIndex === -1 ? '' : rawLine.slice(separatorIndex + 1);

      if (value.startsWith(' ')) {
        value = value.slice(1);
      }

      if (field === 'event' && this.isKnownEventType(value)) {
        eventType = value;
      }

      if (field === 'data') {
        dataLines.push(value);
      }
    }

    if (!eventType || dataLines.length === 0) {
      return;
    }

    this.handleEvent(eventType, { data: dataLines.join('\n') } as MessageEvent);
  }

  private isKnownEventType(value: string): value is SSEEventType {
    return value === 'task_result' || value === 'task_status' || value === 'task_error' || value === 'log';
  }

  private handleEvent<T extends SSEEventType>(
    eventType: T,
    event: MessageEvent,
  ): void {
    try {
      const data = JSON.parse(event.data);
      const handlers = this.handlers[eventType] as Set<EventHandler<unknown>>;

      handlers.forEach(handler => {
        try {
          handler(data);
        } catch (error) {
          console.error(`[SSE] failed to handle ${eventType}:`, error);
        }
      });
    } catch (error) {
      console.error(`[SSE] failed to parse ${eventType}:`, error);
    }
  }

  private scheduleReconnect(): void {
    if (this.manuallyClosed) {
      return;
    }

    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[SSE] max reconnect attempts reached');
      return;
    }

    this.reconnectAttempts += 1;
    console.log(
      `[SSE] reconnecting in ${this.reconnectDelay / 1000}s (${this.reconnectAttempts}/${this.maxReconnectAttempts})`,
    );

    this.reconnectTimer = setTimeout(() => {
      if (this.connectionState === CLOSED && !this.manuallyClosed) {
        console.log('[SSE] reconnecting...');
        void this.openConnection();
      }
    }, this.reconnectDelay);
  }

  disconnect(): void {
    this.manuallyClosed = true;
    this.connectionState = CLOSED;

    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }

    console.log('[SSE] disconnected');
    this.reconnectAttempts = 0;
  }

  isConnected(): boolean {
    return this.connectionState === OPEN;
  }

  onTaskResult(handler: EventHandler<TaskResultEvent>): () => void {
    this.handlers.task_result.add(handler);
    return () => this.handlers.task_result.delete(handler);
  }

  onTaskStatus(handler: EventHandler<TaskStatusEvent>): () => void {
    this.handlers.task_status.add(handler);
    return () => this.handlers.task_status.delete(handler);
  }

  onTaskError(handler: EventHandler<TaskErrorEvent>): () => void {
    this.handlers.task_error.add(handler);
    return () => this.handlers.task_error.delete(handler);
  }

  onLog(handler: EventHandler<LogEvent>): () => void {
    this.handlers.log.add(handler);
    return () => this.handlers.log.delete(handler);
  }

  on<T extends SSEEventType>(
    eventType: T,
    handler: EventHandler<
      T extends 'task_result' ? TaskResultEvent :
      T extends 'task_status' ? TaskStatusEvent :
      T extends 'task_error' ? TaskErrorEvent :
      LogEvent
    >,
  ): () => void {
    const handlers = this.handlers[eventType] as Set<EventHandler<unknown>>;
    handlers.add(handler);
    return () => handlers.delete(handler);
  }

  removeAllHandlers(): void {
    this.handlers.task_result.clear();
    this.handlers.task_status.clear();
    this.handlers.task_error.clear();
    this.handlers.log.clear();
  }
}

export const sseClient = new SSEClient();

export default sseClient;
