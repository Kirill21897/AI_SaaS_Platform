"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { AppHeader } from "@/components/app-header";
import { fetchAPI } from "@/lib/api";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  meta?: {
    startedAt?: number;
    firstChunkAt?: number;
    finishedAt?: number;
    chunkCount?: number;
    charCount?: number;
    aborted?: boolean;
    error?: string;
  };
};

type ChatStore = {
  messages: ChatMessage[];
  sessionKey?: string;
  renderCards?: boolean;
  showMeta?: boolean;
  rawMode?: boolean;
};

declare global {
  interface Window {
    __AI_SAAS_DASH_STORE__?: ChatStore;
  }
}

function getDashStore(): ChatStore {
  if (typeof window === "undefined") return { messages: [] };
  if (!window.__AI_SAAS_DASH_STORE__) {
    window.__AI_SAAS_DASH_STORE__ = { messages: [] };
  }
  return window.__AI_SAAS_DASH_STORE__;
}

type HealthInfo = {
  ollama_base_url?: string;
  ollama_version?: string;
  chat_model?: string;
  chat_model_loaded?: boolean;
  error?: string;
};

function getErrorMessage(e: unknown): string {
  if (typeof e === "string") return e;
  if (e && typeof e === "object" && "message" in e) {
    const msg = (e as { message?: unknown }).message;
    if (typeof msg === "string") return msg;
  }
  return "Ошибка";
}

function isAbortError(e: unknown): boolean {
  if (!e || typeof e !== "object") return false;
  const name = (e as { name?: unknown }).name;
  return name === "AbortError";
}

type AgentState = {
  session_id: string;
  stage?: string;
  filters: Record<string, unknown>;
  last: {
    tool?: string | null;
    arguments?: Record<string, unknown>;
    query?: string | null;
    offset?: number;
    limit?: number;
  };
  history_count: number;
  history_tail: unknown[];
};

type Track = {
  id: number;
  title: string;
  description: string;
  specialization: string;
  region?: string | null;
  format?: string | null;
  required_skills?: Record<string, number>;
  tasks?: string[];
};

function parseTrackCardTag(tag: string): { id: number; score?: number; skills?: string[] } | null {
  const attrs: Record<string, string> = {};
  for (const match of tag.matchAll(/(\w+)="([^"]*)"/g)) {
    attrs[match[1]] = match[2];
  }
  const id = Number(attrs.id);
  if (!Number.isFinite(id)) return null;
  const score = attrs.score !== undefined ? Number(attrs.score) : undefined;
  const skills = attrs.skills
    ? attrs.skills
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean)
    : undefined;
  return {
    id,
    score: Number.isFinite(score as number) ? (score as number) : undefined,
    skills,
  };
}

function TrackCard(props: { id: number; score?: number; skills?: string[] }) {
  const { id, score, skills } = props;
  const [track, setTrack] = useState<Track | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    let isMounted = true;
    fetchAPI<Track>(`/tracks/${id}`)
      .then((data) => {
        if (!isMounted) return;
        setTrack(data);
      })
      .catch((e: unknown) => {
        if (!isMounted) return;
        setError(getErrorMessage(e) || "Не удалось загрузить трек");
      });

    return () => {
      isMounted = false;
    };
  }, [id]);

  return (
    <div className="my-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="rounded bg-blue-100 px-2 py-1 text-xs font-bold uppercase tracking-wider text-blue-700">
          Рекомендация
        </span>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          {typeof score === "number" && <span>Match: {score}%</span>}
          <span>ID: {id}</span>
        </div>
      </div>

      {error ? (
        <div className="text-sm text-red-700">{error}</div>
      ) : track ? (
        <>
          <h3 className="text-lg font-semibold text-slate-900">{track.title}</h3>
          <p className="mt-1 text-sm text-slate-600">{track.description}</p>
          <div className="mt-3 flex flex-wrap gap-2 text-xs">
            <span className="rounded bg-slate-50 px-2 py-1 text-slate-700 border border-slate-200">
              {track.specialization}
            </span>
            <span className="rounded bg-slate-50 px-2 py-1 text-slate-700 border border-slate-200">
              {track.region ?? "—"}
            </span>
            <span className="rounded bg-slate-50 px-2 py-1 text-slate-700 border border-slate-200">
              {track.format ?? "—"}
            </span>
          </div>

          {skills && skills.length > 0 && (
            <div className="mt-3">
              <div className="text-xs font-semibold text-slate-600 mb-1">Совпали навыки</div>
              <div className="flex flex-wrap gap-2">
                {skills.map((s) => (
                  <span key={s} className="rounded-full bg-blue-600/10 px-3 py-1 text-xs text-blue-700">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4">
            <Link
              href={`/tracks?highlight=${id}`}
              className="inline-flex items-center rounded border border-slate-300 bg-white px-4 py-1.5 text-sm hover:bg-slate-50 transition-colors"
            >
              Открыть в “Треках”
            </Link>
          </div>
        </>
      ) : (
        <div className="text-sm text-slate-600">Загрузка...</div>
      )}
    </div>
  );
}

function renderAssistant(content: string) {
  const parts = content.split(/(<TRACK_CARD\b[^>]*\/>)/);
  return parts.map((part, index) => {
    const parsed = part.startsWith("<TRACK_CARD") ? parseTrackCardTag(part) : null;
    if (parsed) return <TrackCard key={`${parsed.id}-${index}`} id={parsed.id} score={parsed.score} skills={parsed.skills} />;
    return <span key={index}>{part}</span>;
  });
}

type Scenario = { name: string; steps: string[] };

export default function DashboardPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
  const [health, setHealth] = useState<HealthInfo | null>(null);
  const [healthError, setHealthError] = useState<string>("");
  const [healthLoading, setHealthLoading] = useState(false);

  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    const store = getDashStore();
    if (store.messages.length > 0) {
      return store.messages.map((m) => ({ ...m, streaming: false }));
    }
    return [
      {
        role: "assistant",
        content:
          "Дашборд для тестирования агента. Нажимай на команды справа или напиши свой запрос.\n\nПодсказки:\n- «покажи фильтры»\n- «только Remote в Москве»\n- «подбери треки»\n- «ещё»",
      },
    ];
  });
  const [isLoading, setIsLoading] = useState(false);
  const [sessionKey, setSessionKey] = useState(() => getDashStore().sessionKey ?? "");
  const [sessionKeyDraft, setSessionKeyDraft] = useState(() => getDashStore().sessionKey ?? "");
  const [renderCards, setRenderCards] = useState(() => getDashStore().renderCards ?? true);
  const [showMeta, setShowMeta] = useState(() => getDashStore().showMeta ?? true);
  const [rawMode, setRawMode] = useState(() => getDashStore().rawMode ?? false);
  const [lastRequestMeta, setLastRequestMeta] = useState<ChatMessage["meta"] | null>(null);
  const [agentState, setAgentState] = useState<AgentState | null>(null);
  const [agentStateError, setAgentStateError] = useState<string>("");
  const [agentStateLoading, setAgentStateLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    const store = getDashStore();
    store.messages = messages.map((m) => ({ ...m, streaming: false }));
  }, [messages]);

  useEffect(() => {
    const store = getDashStore();
    store.sessionKey = sessionKey;
    store.renderCards = renderCards;
    store.showMeta = showMeta;
    store.rawMode = rawMode;
  }, [sessionKey, renderCards, showMeta, rawMode]);

  const scrollToBottom = (behavior: ScrollBehavior) => {
    messagesEndRef.current?.scrollIntoView({ behavior });
  };

  useEffect(() => {
    scrollToBottom(isLoading ? "auto" : "smooth");
  }, [messages.length, isLoading]);

  const refreshHealth = async () => {
    setHealthLoading(true);
    setHealthError("");
    try {
      const data = await fetchAPI<HealthInfo>("/chat/health");
      setHealth(data);
    } catch (e: unknown) {
      setHealth(null);
      setHealthError(getErrorMessage(e) || "Не удалось получить health");
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    const id = window.setTimeout(() => {
      refreshHealth();
    }, 0);
    return () => window.clearTimeout(id);
  }, []);

  const refreshAgentState = async (overrideSessionKey?: string) => {
    setAgentStateLoading(true);
    setAgentStateError("");
    try {
      const headers: HeadersInit = {};
      const key = (overrideSessionKey ?? sessionKey).trim();
      if (key) headers["X-Session-ID"] = key;
      const data = await fetchAPI<AgentState>("/chat/state", { headers });
      setAgentState(data);
    } catch (e: unknown) {
      setAgentState(null);
      setAgentStateError(getErrorMessage(e) || "Не удалось получить state");
    } finally {
      setAgentStateLoading(false);
    }
  };

  const resetAgentState = async () => {
    setAgentStateLoading(true);
    setAgentStateError("");
    try {
      const headers: HeadersInit = {};
      if (sessionKey.trim()) headers["X-Session-ID"] = sessionKey.trim();
      await fetchAPI("/chat/reset", { method: "POST", headers });
      await refreshAgentState();
    } catch (e: unknown) {
      setAgentStateError(getErrorMessage(e) || "Не удалось сбросить state");
    } finally {
      setAgentStateLoading(false);
    }
  };

  useEffect(() => {
    const id = window.setTimeout(() => {
      refreshAgentState();
    }, 0);
    return () => window.clearTimeout(id);
  }, []);

  const stop = () => {
    abortRef.current?.abort();
    abortRef.current = null;
  };

  const clearChat = () => {
    stop();
    setMessages([
      {
        role: "assistant",
        content:
          "Чат очищен.\n\nПодсказки:\n- «покажи фильтры»\n- «только Remote в Москве»\n- «подбери треки»\n- «ещё»",
      },
    ]);
  };

  const sendUserMessage = async (userMsg: string) => {
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);

    const startedAt = performance.now();
    setLastRequestMeta({ startedAt });

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      if (sessionKey.trim()) headers["X-Session-ID"] = sessionKey.trim();

      const response = await fetch(`${apiUrl}/chat/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify({ message: userMsg }),
        signal: controller.signal,
      });

      if (response.status === 401 || response.status === 403) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Пожалуйста, войдите в систему, чтобы использовать чат." },
        ]);
        return;
      }

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(`${response.status}: ${text || "Network response was not ok"}`);
      }

      const assistantIndex = messages.length + 1;
      setMessages((prev) => [...prev, { role: "assistant", content: "…", streaming: true, meta: { startedAt } }]);

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

      if (!reader) {
        const text = await response.text();
        const finishedAt = performance.now();
        setMessages((prev) => {
          const next = [...prev];
          const last = next[assistantIndex];
          if (last?.role === "assistant") {
            last.content = text || "Ой, пустой ответ от сервера.";
            last.streaming = false;
            last.meta = { startedAt, finishedAt, firstChunkAt: finishedAt, chunkCount: 1, charCount: (text || "").length };
          }
          return next;
        });
        setLastRequestMeta({ startedAt, finishedAt, firstChunkAt: finishedAt, chunkCount: 1, charCount: (text || "").length });
        return;
      }

      let accumulated = "";
      let rafId: number | null = null;
      let firstChunkAt: number | null = null;
      let chunkCount = 0;

      const flush = () => {
        rafId = null;
        setMessages((prev) => {
          const next = [...prev];
          const last = next[assistantIndex];
          if (last?.role === "assistant") last.content = accumulated;
          return next;
        });
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        if (!value) continue;
        if (firstChunkAt === null) firstChunkAt = performance.now();
        chunkCount += 1;
        accumulated += decoder.decode(value, { stream: true });
        if (rafId === null) rafId = window.requestAnimationFrame(flush);
      }

      decoder.decode();
      if (rafId !== null) {
        window.cancelAnimationFrame(rafId);
        rafId = null;
      }
      flush();

      const finishedAt = performance.now();
      const resolvedFirstChunkAt = firstChunkAt ?? finishedAt;
      const meta = {
        startedAt,
        firstChunkAt: resolvedFirstChunkAt,
        finishedAt,
        chunkCount,
        charCount: accumulated.length,
      };

      setMessages((prev) => {
        const next = [...prev];
        const last = next[assistantIndex];
        if (last?.role === "assistant") {
          last.streaming = false;
          last.meta = meta;
        }
        return next;
      });

      setLastRequestMeta(meta);
    } catch (e: unknown) {
      const finishedAt = performance.now();
      const isAbort = isAbortError(e);
      const err = isAbort ? "abort" : getErrorMessage(e);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: isAbort ? "Остановлено." : `Ошибка: ${err}`,
          meta: { startedAt, finishedAt, firstChunkAt: finishedAt, aborted: isAbort, error: isAbort ? undefined : err },
        },
      ]);
      setLastRequestMeta({ startedAt, finishedAt, firstChunkAt: finishedAt, aborted: isAbort, error: isAbort ? undefined : err });
    } finally {
      abortRef.current = null;
      setIsLoading(false);
      refreshAgentState();
    }
  };

  const scenarios: Scenario[] = useMemo(
    () => [
      { name: "Сброс и подбор", steps: ["очисти фильтры", "подбери треки"] },
      { name: "Remote Москва Backend", steps: ["только Remote в Москве", "подбери треки"] },
      { name: "Обзор базы", steps: ["покажи треки", "ещё"] },
      { name: "Explore дизайн", steps: ["что есть по дизайну?", "ещё"] },
    ],
    []
  );

  const [selectedScenario, setSelectedScenario] = useState(scenarios[0]?.name ?? "");
  const [scenarioRunning, setScenarioRunning] = useState(false);

  const runScenario = async () => {
    const scenario = scenarios.find((s) => s.name === selectedScenario);
    if (!scenario || scenarioRunning) return;
    setScenarioRunning(true);
    try {
      for (const step of scenario.steps) {
        await sendUserMessage(step);
      }
    } finally {
      setScenarioRunning(false);
    }
  };

  const quickActions: { label: string; message: string }[] = [
    { label: "Показать фильтры", message: "покажи фильтры" },
    { label: "Очистить фильтры", message: "очисти фильтры" },
    { label: "Remote", message: "только Remote" },
    { label: "Москва", message: "в Москве" },
    { label: "Backend", message: "backend" },
    { label: "Frontend", message: "frontend" },
    { label: "Design", message: "дизайн" },
    { label: "Подбор", message: "подбери треки" },
    { label: "Каталог", message: "покажи треки" },
    { label: "Ещё", message: "ещё" },
  ];

  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader />
      <main className="mx-auto w-full max-w-7xl px-4 py-6">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Агент</h1>
            <p className="text-sm text-slate-600">
              Чат + панель тестирования tool-calling, фильтров, сценариев и скорости стрима.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={refreshHealth}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
              disabled={healthLoading}
            >
              Обновить health
            </button>
            <button
              type="button"
              onClick={clearChat}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
              disabled={isLoading}
            >
              Очистить чат
            </button>
            <button
              type="button"
              onClick={stop}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
              disabled={!isLoading}
            >
              Стоп
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <section className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="border-b border-slate-200 px-4 py-3 flex items-center justify-between gap-3">
              <div className="text-sm font-semibold text-slate-900">Чат</div>
              <div className="flex items-center gap-3 text-xs text-slate-600">
                <label className="inline-flex items-center gap-2">
                  <input type="checkbox" checked={renderCards} onChange={(e) => setRenderCards(e.target.checked)} />
                  Карточки
                </label>
                <label className="inline-flex items-center gap-2">
                  <input type="checkbox" checked={showMeta} onChange={(e) => setShowMeta(e.target.checked)} />
                  Метрики
                </label>
                <label className="inline-flex items-center gap-2">
                  <input type="checkbox" checked={rawMode} onChange={(e) => setRawMode(e.target.checked)} />
                  Raw
                </label>
              </div>
            </div>

            <div className="h-[560px] overflow-y-auto p-4 space-y-4">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[78%] rounded-lg px-4 py-3 whitespace-pre-wrap ${
                      msg.role === "user"
                        ? "bg-blue-600 text-white"
                        : "bg-slate-50 text-slate-900 border border-slate-200"
                    }`}
                  >
                    {msg.role === "assistant" ? (
                      msg.streaming || rawMode || !renderCards ? (
                        msg.content
                      ) : (
                        renderAssistant(msg.content)
                      )
                    ) : (
                      msg.content
                    )}
                    {showMeta && msg.role === "assistant" && msg.meta && (
                      <div className="mt-2 text-[11px] text-slate-500">
                        {typeof msg.meta.startedAt === "number" &&
                          typeof msg.meta.firstChunkAt === "number" && (
                            <span className="mr-3">
                              TTFB: {Math.max(0, msg.meta.firstChunkAt - msg.meta.startedAt).toFixed(0)}ms
                            </span>
                          )}
                        {typeof msg.meta.startedAt === "number" &&
                          typeof msg.meta.finishedAt === "number" && (
                            <span className="mr-3">
                              Total: {Math.max(0, msg.meta.finishedAt - msg.meta.startedAt).toFixed(0)}ms
                            </span>
                          )}
                        {typeof msg.meta.chunkCount === "number" && (
                          <span className="mr-3">Chunks: {msg.meta.chunkCount}</span>
                        )}
                        {typeof msg.meta.charCount === "number" && <span>Chars: {msg.meta.charCount}</span>}
                        {msg.meta.aborted && <span className="ml-3">aborted</span>}
                        {msg.meta.error && <span className="ml-3 text-red-700">{msg.meta.error}</span>}
                      </div>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <div className="border-t border-slate-200 p-4">
              <Composer onSend={sendUserMessage} disabled={isLoading} />
            </div>
          </section>

          <aside className="space-y-6">
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-center justify-between">
                <div className="text-sm font-semibold text-slate-900">Статус</div>
                <Link href="/login" className="text-sm text-blue-700 hover:underline">
                  Войти
                </Link>
              </div>
              {healthError ? (
                <div className="text-sm text-red-700">{healthError}</div>
              ) : health ? (
                <div className="space-y-2 text-sm text-slate-700">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-500">Ollama</span>
                    <span className="font-medium">{health.ollama_base_url ?? "—"}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-500">Version</span>
                    <span className="font-medium">{health.ollama_version ?? "—"}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-500">Model</span>
                    <span className="font-medium">{health.chat_model ?? "—"}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-500">Loaded</span>
                    <span className={`font-medium ${health.chat_model_loaded ? "text-green-700" : "text-slate-700"}`}>
                      {health.chat_model_loaded ? "yes" : "no"}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-slate-600">—</div>
              )}
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="text-sm font-semibold text-slate-900">Agent Trace</div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => refreshAgentState()}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs hover:bg-slate-50"
                    disabled={agentStateLoading}
                  >
                    Обновить
                  </button>
                  <button
                    type="button"
                    onClick={resetAgentState}
                    className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs hover:bg-slate-50"
                    disabled={agentStateLoading || isLoading}
                  >
                    Сбросить
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                <div>
                  <div className="mb-1 text-xs font-semibold text-slate-600">Session key (опционально)</div>
                  <div className="flex gap-2">
                    <input
                      value={sessionKeyDraft}
                      onChange={(e) => setSessionKeyDraft(e.target.value)}
                      placeholder="demo-1"
                      className="flex-1 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm hover:bg-slate-50"
                      onClick={() => {
                        const next = Math.random().toString(36).slice(2, 10);
                        setSessionKeyDraft(next);
                        setSessionKey(next);
                        refreshAgentState(next);
                      }}
                      disabled={isLoading}
                    >
                      Rand
                    </button>
                    <button
                      type="button"
                      className="rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
                      onClick={() => {
                        const next = sessionKeyDraft.trim();
                        setSessionKey(next);
                        refreshAgentState(next);
                      }}
                      disabled={isLoading || agentStateLoading}
                    >
                      Применить
                    </button>
                  </div>
                  <div className="mt-1 text-[11px] text-slate-500">
                    Если пусто — используется session = user_id. Если задано — user_id:sessionKey.
                  </div>
                </div>

                {agentStateError ? (
                  <div className="text-sm text-red-700">{agentStateError}</div>
                ) : agentState ? (
                  <div className="space-y-3 text-sm text-slate-700">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-slate-500">Session</span>
                      <span className="font-medium truncate">{agentState.session_id}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-slate-500">Stage</span>
                      <span className="font-medium">{agentState.stage ?? "—"}</span>
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-slate-500">History</span>
                      <span className="font-medium">{agentState.history_count}</span>
                    </div>
                    <div>
                      <div className="mb-1 text-xs font-semibold text-slate-600">Last tool</div>
                      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs whitespace-pre-wrap">
                        {JSON.stringify(agentState.last ?? {}, null, 2)}
                      </div>
                    </div>
                    <div>
                      <div className="mb-1 text-xs font-semibold text-slate-600">Filters</div>
                      <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs whitespace-pre-wrap">
                        {JSON.stringify(agentState.filters ?? {}, null, 2)}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-slate-600">—</div>
                )}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-3 text-sm font-semibold text-slate-900">Быстрые команды</div>
              <div className="grid grid-cols-2 gap-2">
                {quickActions.map((a) => (
                  <button
                    key={a.label}
                    type="button"
                    className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-800 hover:bg-slate-100"
                    onClick={() => sendUserMessage(a.message)}
                    disabled={isLoading}
                  >
                    {a.label}
                  </button>
                ))}
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-3 text-sm font-semibold text-slate-900">Сценарии</div>
              <div className="space-y-3">
                <select
                  value={selectedScenario}
                  onChange={(e) => setSelectedScenario(e.target.value)}
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm"
                  disabled={scenarioRunning || isLoading}
                >
                  {scenarios.map((s) => (
                    <option key={s.name} value={s.name}>
                      {s.name}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  onClick={runScenario}
                  className="w-full rounded-lg bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
                  disabled={scenarioRunning || isLoading}
                >
                  Запустить
                </button>
              </div>
              <div className="mt-3 text-xs text-slate-500">
                Подсказка: сценарии удобно использовать для демонстрации фильтров и follow-up «ещё».
              </div>
            </section>

            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
              <div className="mb-3 text-sm font-semibold text-slate-900">Метрики последнего запроса</div>
              {lastRequestMeta ? (
                <div className="space-y-2 text-sm text-slate-700">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-500">TTFB</span>
                    <span className="font-medium">
                      {typeof lastRequestMeta.startedAt === "number" && typeof lastRequestMeta.firstChunkAt === "number"
                        ? `${Math.max(0, lastRequestMeta.firstChunkAt - lastRequestMeta.startedAt).toFixed(0)}ms`
                        : "—"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-500">Total</span>
                    <span className="font-medium">
                      {typeof lastRequestMeta.startedAt === "number" && typeof lastRequestMeta.finishedAt === "number"
                        ? `${Math.max(0, lastRequestMeta.finishedAt - lastRequestMeta.startedAt).toFixed(0)}ms`
                        : "—"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-500">Chunks</span>
                    <span className="font-medium">{lastRequestMeta.chunkCount ?? "—"}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-500">Chars</span>
                    <span className="font-medium">{lastRequestMeta.charCount ?? "—"}</span>
                  </div>
                </div>
              ) : (
                <div className="text-sm text-slate-600">—</div>
              )}
            </section>
          </aside>
        </div>
      </main>
    </div>
  );
}

function Composer(props: { disabled: boolean; onSend: (message: string) => Promise<void> }) {
  const { disabled, onSend } = props;
  const [input, setInput] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const msg = input.trim();
    if (!msg) return;
    setInput("");
    await onSend(msg);
  };

  return (
    <form onSubmit={submit} className="flex gap-3">
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Сообщение для агента…"
        className="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        disabled={disabled}
      />
      <button
        type="submit"
        disabled={disabled || !input.trim()}
        className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
      >
        Отправить
      </button>
    </form>
  );
}
