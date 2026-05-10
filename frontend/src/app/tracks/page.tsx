"use client";

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
  is_active?: boolean;
  required_skills?: Record<string, number>;
  tasks?: string[];
};

type TrackForm = {
  title: string;
  description: string;
  specialization: string;
  region: string;
  format: string;
  min_gpa: number;
  skillsText: string;
  tasksText: string;
};

const defaultForm: TrackForm = {
  title: "",
  description: "",
  specialization: "",
  region: "Global",
  format: "Remote",
  min_gpa: 0,
  skillsText: "python:0.5,sql:0.3",
  tasksText: "Изучение программы, Практические задания",
};

export default function TracksPage() {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [form, setForm] = useState<TrackForm>(defaultForm);

  async function loadTracks() {
    setError("");
    try {
      const data = await fetchAPI("/tracks");
      setTracks(data ?? []);
    } catch (err: any) {
      setError(err.message ?? "Не удалось загрузить треки");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTracks();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsSubmitting(true);
    try {
      const required_skills = Object.fromEntries(
        form.skillsText
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean)
          .map((item) => {
            const [name, weight] = item.split(":");
            return [name.trim().toLowerCase(), Number(weight ?? 0)];
          })
      );

      const payload = {
        title: form.title,
        description: form.description,
        specialization: form.specialization,
        region: form.region,
        format: form.format,
        min_gpa: Number(form.min_gpa),
        is_active: true,
        required_skills,
        tasks: form.tasksText
          .split(",")
          .map((task) => task.trim())
          .filter(Boolean),
      };

      await fetchAPI("/tracks", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      setForm(defaultForm);
      await loadTracks();
    } catch (err: any) {
      setError(err.message ?? "Не удалось добавить трек");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    setError("");
    try {
      await fetchAPI(`/tracks/${id}`, { method: "DELETE" });
      setTracks((prev) => prev.filter((track) => track.id !== id));
    } catch (err: any) {
      setError(err.message ?? "Не удалось удалить трек");
    }
  };

  return (
    <div className="min-h-screen">
      <AppHeader />
      <main className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-8 lg:grid-cols-[1fr_380px]">
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h1 className="text-2xl font-bold text-slate-900">Образовательные треки</h1>
          <p className="mt-1 text-sm text-slate-500">Список доступных программ с возможностью удаления.</p>

          {error && <div className="mt-4 rounded-lg bg-red-100 px-3 py-2 text-sm text-red-700">{error}</div>}

          {loading ? (
            <p className="mt-6 text-slate-500">Загрузка треков...</p>
          ) : (
            <div className="mt-6 grid gap-3">
              {tracks.map((track) => (
                <article key={track.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <h3 className="font-semibold text-slate-900">{track.title}</h3>
                      <p className="mt-1 text-sm text-slate-600">{track.description}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDelete(track.id)}
                      className="rounded-lg border border-red-300 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
                    >
                      Удалить
                    </button>
                  </div>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <span className="rounded bg-slate-100 px-2 py-1 text-slate-600">{track.specialization}</span>
                    <span className="rounded bg-slate-100 px-2 py-1 text-slate-600">{track.region ?? "—"}</span>
                    <span className="rounded bg-slate-100 px-2 py-1 text-slate-600">{track.format ?? "—"}</span>
                  </div>
                </article>
              ))}
              {tracks.length === 0 && <p className="text-sm text-slate-500">Треки пока не добавлены.</p>}
            </div>
          )}
        </section>

        <section className="h-fit rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-xl font-semibold text-slate-900">Добавить трек</h2>
          <form onSubmit={handleCreate} className="mt-4 space-y-3">
            <input className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Название" value={form.title} onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))} required />
            <textarea className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Описание" value={form.description} onChange={(e) => setForm((prev) => ({ ...prev, description: e.target.value }))} rows={3} required />
            <input className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Специализация" value={form.specialization} onChange={(e) => setForm((prev) => ({ ...prev, specialization: e.target.value }))} required />
            <div className="grid grid-cols-2 gap-3">
              <input className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Регион" value={form.region} onChange={(e) => setForm((prev) => ({ ...prev, region: e.target.value }))} />
              <select className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" value={form.format} onChange={(e) => setForm((prev) => ({ ...prev, format: e.target.value }))}>
                <option value="Remote">Remote</option>
                <option value="Office">Office</option>
                <option value="Hybrid">Hybrid</option>
              </select>
            </div>
            <input className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" type="number" step="0.1" min="0" max="5" placeholder="Минимальный GPA" value={form.min_gpa} onChange={(e) => setForm((prev) => ({ ...prev, min_gpa: Number(e.target.value) }))} />
            <input className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Навыки (python:0.5,sql:0.3)" value={form.skillsText} onChange={(e) => setForm((prev) => ({ ...prev, skillsText: e.target.value }))} />
            <input className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" placeholder="Задачи (через запятую)" value={form.tasksText} onChange={(e) => setForm((prev) => ({ ...prev, tasksText: e.target.value }))} />
            <button type="submit" disabled={isSubmitting} className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
              {isSubmitting ? "Сохраняю..." : "Добавить трек"}
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
