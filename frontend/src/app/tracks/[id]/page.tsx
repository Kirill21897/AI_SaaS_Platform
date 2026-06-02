"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppHeader } from "@/components/app-header";
import { fetchAPI } from "@/lib/api";

type Track = {
  id: number;
  title: string;
  description: string;
  specialization: string;
  region?: string | null;
  format?: string | null;
  min_gpa?: number | null;
  required_skills?: Record<string, number>;
  tasks?: string[];
};

function formatTrackMode(value?: string | null): string {
  if (!value) return "Не указан";
  if (value === "Remote") return "Удаленно";
  if (value === "Office" || value === "Onsite") return "Офис";
  if (value === "Hybrid") return "Гибрид";
  return value;
}

function formatSkillWeight(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export default function TrackDetailsPage(props: { params: Promise<{ id: string }> }) {
  const [track, setTrack] = useState<Track | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    async function loadTrack() {
      setLoading(true);
      setError("");
      try {
        const { id } = await props.params;
        const data = await fetchAPI<Track>(`/tracks/${id}`);
        if (!isMounted) return;
        setTrack(data);
      } catch (e: unknown) {
        if (!isMounted) return;
        const message = e instanceof Error ? e.message : "Не удалось загрузить программу";
        setError(message);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadTrack();
    return () => {
      isMounted = false;
    };
  }, [props.params]);

  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader />
      <main className="mx-auto w-full max-w-5xl px-4 py-8">
        <div className="mb-6 flex flex-wrap items-center gap-3">
          <Link
            href="/tracks"
            className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
          >
            Назад к программам
          </Link>
          {track && (
            <Link
              href={`/tracks?highlight=${track.id}`}
              className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
            >
              Открыть в каталоге
            </Link>
          )}
        </div>

        {loading ? (
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="text-slate-600">Загрузка программы...</div>
          </section>
        ) : error ? (
          <section className="rounded-2xl border border-red-200 bg-red-50 p-6 shadow-sm">
            <div className="text-red-700">{error}</div>
          </section>
        ) : track ? (
          <div className="grid gap-6 lg:grid-cols-[1.7fr_1fr]">
            <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 flex flex-wrap gap-2 text-xs">
                <span className="rounded-full bg-blue-100 px-3 py-1 font-semibold text-blue-700">
                  Программа
                </span>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">
                  {track.specialization}
                </span>
              </div>

              <h1 className="text-3xl font-bold text-slate-900">{track.title}</h1>
              <p className="mt-4 text-base leading-7 text-slate-700">{track.description}</p>

              {track.tasks && track.tasks.length > 0 && (
                <div className="mt-8">
                  <h2 className="text-lg font-semibold text-slate-900">Что включает программа</h2>
                  <div className="mt-3 space-y-3">
                    {track.tasks.map((task) => (
                      <div key={task} className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                        {task}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </section>

            <aside className="space-y-6">
              <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-slate-900">Параметры</h2>
                <div className="mt-4 space-y-3 text-sm text-slate-700">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-500">Регион</span>
                    <span className="font-medium">{track.region ?? "Не указан"}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-500">Формат</span>
                    <span className="font-medium">{formatTrackMode(track.format)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-500">Минимальный GPA</span>
                    <span className="font-medium">
                      {typeof track.min_gpa === "number" && track.min_gpa > 0 ? track.min_gpa : "Не требуется"}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-slate-500">ID программы</span>
                    <span className="font-medium">{track.id}</span>
                  </div>
                </div>
              </section>

              <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h2 className="text-lg font-semibold text-slate-900">Навыки</h2>
                {track.required_skills && Object.keys(track.required_skills).length > 0 ? (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {Object.entries(track.required_skills).map(([skill, weight]) => (
                      <span
                        key={skill}
                        className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-sm text-slate-700"
                      >
                        {skill} · {formatSkillWeight(weight)}
                      </span>
                    ))}
                  </div>
                ) : (
                  <div className="mt-4 text-sm text-slate-500">Навыки не указаны.</div>
                )}
              </section>
            </aside>
          </div>
        ) : null}
      </main>
    </div>
  );
}
