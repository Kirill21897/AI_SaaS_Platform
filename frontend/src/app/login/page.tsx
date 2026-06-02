'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { login, register } from '@/lib/api';

const DEMO_PASSWORD = process.env.NEXT_PUBLIC_DEMO_PASSWORD ?? '';
const DEMO_USERS = [
  {
    label: 'Backend Developer',
    icon: '👨‍💻',
    email: process.env.NEXT_PUBLIC_DEMO_BACKEND_EMAIL ?? '',
  },
  {
    label: 'Data Analyst',
    icon: '📊',
    email: process.env.NEXT_PUBLIC_DEMO_DATA_EMAIL ?? '',
  },
  {
    label: 'Пустой профиль',
    icon: '👻',
    email: process.env.NEXT_PUBLIC_DEMO_EMPTY_EMAIL ?? '',
  },
].filter((user) => user.email);

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    
    try {
      if (isLogin) {
        await login(email, password);
        router.push('/profile');
      } else {
        await register(email, password);
        await login(email, password);
        router.push('/profile');
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4 text-gray-900">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h1 className="mb-2 text-center text-2xl font-bold">
          {isLogin ? 'Вход' : 'Регистрация'}
        </h1>
        <p className="mb-6 text-center text-sm text-slate-500">
          Войдите в платформу, чтобы работать с профилем, чатом и образовательными треками.
        </p>
        
        {error && (
          <div className="bg-red-100 text-red-700 p-3 rounded mb-4 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-900"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Пароль</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full p-2 border rounded focus:ring-blue-500 focus:border-blue-500 bg-white text-gray-900"
            />
          </div>
          
          <button
            type="submit"
            className="w-full bg-blue-600 text-white p-2 rounded hover:bg-blue-700 transition font-medium"
          >
            {isLogin ? 'Войти' : 'Зарегистрироваться'}
          </button>
        </form>

        <div className="mt-8 border-t border-slate-200 pt-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-3 text-center">Демо-аккаунты (Quick Login)</h3>
          {DEMO_USERS.length > 0 ? (
            <div className="grid grid-cols-1 gap-2">
              {DEMO_USERS.map((user) => (
                <button
                  key={user.email}
                  type="button"
                  onClick={() => { setEmail(user.email); setPassword(DEMO_PASSWORD); setIsLogin(true); }}
                  className="w-full bg-slate-100 text-slate-700 p-2 rounded text-sm hover:bg-slate-200 transition text-left flex justify-between items-center"
                >
                  <span>{user.icon} {user.label}</span>
                  <span className="text-xs text-slate-400">{user.email}</span>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500 text-center">
              Демо-аккаунты не настроены. Добавьте `NEXT_PUBLIC_DEMO_*` переменные в `frontend/.env.local`.
            </p>
          )}
        </div>

        <div className="mt-6 text-center">
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="text-blue-600 hover:underline text-sm"
          >
            {isLogin ? 'Нет аккаунта? Зарегистрироваться' : 'Уже есть аккаунт? Войти'}
          </button>
        </div>
        <div className="mt-4 text-center text-sm">
          <Link href="/" className="text-slate-500 hover:text-slate-800 hover:underline">
            На главную
          </Link>
        </div>
      </div>
    </div>
  );
}
