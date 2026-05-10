import Link from "next/link";
import { AppHeader } from "@/components/app-header";

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-50">
      <AppHeader />
      <main className="mx-auto w-full max-w-6xl px-4 py-12">
        <div className="rounded-3xl border border-slate-200 bg-white p-10 shadow-sm mb-8 text-center">
          <p className="mb-4 inline-flex rounded-full bg-blue-100 px-3 py-1 text-sm font-semibold text-blue-700 uppercase tracking-wide">
            Agentic RAG Platform MVP
          </p>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 mb-6">AI SaaS Platform</h1>
          <p className="mx-auto max-w-2xl text-lg text-slate-600 mb-10">
            Интеллектуальная система рекомендаций карьерно-образовательных треков на базе Agentic RAG. 
            Протестируйте подбор программ с помощью AI-ассистента.
          </p>

          <div className="flex flex-wrap justify-center gap-4">
            <Link href="/chat" className="rounded-xl bg-blue-600 px-8 py-4 text-center font-medium text-white hover:bg-blue-700 shadow-md transition">
              🤖 Начать диалог с AI
            </Link>
            <Link href="/profile" className="rounded-xl border border-slate-300 bg-white px-8 py-4 text-center font-medium text-slate-700 hover:bg-slate-50 transition">
              👤 Мой профиль
            </Link>
            <Link href="/tracks" className="rounded-xl border border-slate-300 bg-white px-8 py-4 text-center font-medium text-slate-700 hover:bg-slate-50 transition">
              📚 База треков
            </Link>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <span>🚀 Как тестировать?</span>
            </h2>
            <ol className="space-y-4 text-slate-600 text-sm list-decimal list-inside ml-2">
              <li>
                <strong className="text-slate-800">Выберите профиль:</strong> Перейдите на страницу <Link href="/login" className="text-blue-600 hover:underline">Входа</Link> и используйте <b>Quick Login</b> (например, Backend Developer).
              </li>
              <li>
                <strong className="text-slate-800">Проверьте данные:</strong> Откройте <Link href="/profile" className="text-blue-600 hover:underline">Профиль</Link> и посмотрите навыки. При необходимости измените их.
              </li>
              <li>
                <strong className="text-slate-800">Используйте Чат:</strong> Откройте <Link href="/chat" className="text-blue-600 hover:underline">Чат</Link> и попросите подобрать вам программу. Агент учтет ваши навыки и формат работы!
              </li>
              <li>
                <strong className="text-slate-800">Управление треками:</strong> В разделе <Link href="/tracks" className="text-blue-600 hover:underline">Треки</Link> можно добавить новые программы, которые сразу станут доступны для поиска.
              </li>
            </ol>
          </div>
          
          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <h2 className="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
              <span>🏗 Архитектура MVP</span>
            </h2>
            <ul className="space-y-3 text-slate-600 text-sm">
              <li className="flex items-start gap-2">
                <span className="mt-0.5 text-blue-500">✓</span>
                <span><b>Frontend:</b> Next.js, TailwindCSS, Streaming UI.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-0.5 text-blue-500">✓</span>
                <span><b>Backend:</b> FastAPI, PostgreSQL (пользователи и треки).</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-0.5 text-blue-500">✓</span>
                <span><b>Vector DB:</b> Qdrant для семантического поиска.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-0.5 text-blue-500">✓</span>
                <span><b>Agent State:</b> Redis хранит историю чата и текущий этап (State Machine).</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-0.5 text-blue-500">✓</span>
                <span><b>AI Layer:</b> GPT-4o-mini (через OpenRouter/OpenAI).</span>
              </li>
            </ul>
          </div>
        </div>
      </main>
    </div>
  );
}
