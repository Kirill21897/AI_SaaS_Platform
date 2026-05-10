'use client';

import { useState, useEffect } from 'react';
import { fetchAPI } from '@/lib/api';
import { AppHeader } from '@/components/app-header';

export default function ProfilePage() {
  const [profile, setProfile] = useState<any>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [newSkill, setNewSkill] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const data = await fetchAPI('/profiles/me');
      setProfile(data);
    } catch (err: any) {
      if (err.message.includes('404') || err.message.includes('not found')) {
        // Профиль еще не создан
        setProfile({
          first_name: '',
          last_name: '',
          about: '',
          specialty: '',
          skills: [],
          location: '',
          employment_format: 'Remote',
          completeness_score: 0,
        });
        setIsEditing(true);
      } else if (err.message.includes('401') || err.message.includes('403') || err.message.includes('credentials')) {
        // Временно отключили редирект для разработки
        // router.push('/login');
        setError('Нет доступа, но мы продолжаем в mock-режиме.');
      } else {
        setError('Не удалось загрузить профиль');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setError('');
    try {
      const isNewProfile = profile.id === undefined;
      const method = isNewProfile ? 'POST' : 'PUT';
      const endpoint = isNewProfile ? '/profiles/' : '/profiles/me';
      
      const savedProfile = await fetchAPI(endpoint, {
        method,
        body: JSON.stringify(profile),
      });
      
      setProfile(savedProfile);
      setIsEditing(false);
    } catch (err: any) {
      setError(err.message || 'Ошибка при сохранении профиля');
    }
  };

  const addSkill = () => {
    if (newSkill && !profile.skills.includes(newSkill)) {
      setProfile({...profile, skills: [...profile.skills, newSkill]});
      setNewSkill('');
    }
  };

  const removeSkill = (skillToRemove: string) => {
    setProfile({
      ...profile,
      skills: profile.skills.filter((s: string) => s !== skillToRemove)
    });
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center"><p>Загрузка...</p></div>;

  return (
    <div className="min-h-screen">
      <AppHeader />
      <div className="mx-auto max-w-3xl space-y-6 px-4 py-8 sm:px-6 lg:px-8 text-gray-900">
        <div className="flex justify-between items-center">
          <h1 className="text-3xl font-bold">Личный кабинет</h1>
        </div>

        {error && (
          <div className="bg-red-100 text-red-700 p-4 rounded-lg">
            {error}
          </div>
        )}

        {/* Completeness Score Card */}
        {profile && (
          <>
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold mb-2">Заполненность профиля</h2>
              <div className="w-full bg-gray-200 rounded-full h-4 mb-2">
                <div 
                  className="bg-blue-600 h-4 rounded-full transition-all duration-500" 
                  style={{ width: `${profile.completeness_score || 0}%` }}
                ></div>
              </div>
              <p className="text-sm text-gray-600">
                Ваш профиль заполнен на {profile.completeness_score || 0}%. 
                {(profile.completeness_score || 0) < 100 && ' Заполните остальные данные для более точных рекомендаций треков.'}
              </p>
            </div>

            {/* Profile Info Form */}
            <div className="bg-white shadow rounded-lg p-6 space-y-4">
              <h2 className="text-xl font-semibold border-b pb-2">Личные данные</h2>
              
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Имя</label>
                  <input 
                    type="text" 
                    value={profile.first_name || ''} 
                    onChange={(e) => setProfile({...profile, first_name: e.target.value})}
                    className={`mt-1 block w-full rounded-md shadow-sm p-2 border focus:ring-blue-500 ${isEditing ? 'border-blue-300 bg-white' : 'border-gray-200 bg-gray-50'}`}
                    readOnly={!isEditing}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Фамилия</label>
                  <input 
                    type="text" 
                    value={profile.last_name || ''} 
                    onChange={(e) => setProfile({...profile, last_name: e.target.value})}
                    className={`mt-1 block w-full rounded-md shadow-sm p-2 border focus:ring-blue-500 ${isEditing ? 'border-blue-300 bg-white' : 'border-gray-200 bg-gray-50'}`}
                    readOnly={!isEditing}
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700">О себе</label>
                  <textarea 
                    value={profile.about || ''} 
                    onChange={(e) => setProfile({...profile, about: e.target.value})}
                    rows={3}
                    className={`mt-1 block w-full rounded-md shadow-sm p-2 border focus:ring-blue-500 ${isEditing ? 'border-blue-300 bg-white' : 'border-gray-200 bg-gray-50'}`}
                    readOnly={!isEditing}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Специализация</label>
                  <input 
                    type="text" 
                    value={profile.specialty || ''} 
                    onChange={(e) => setProfile({...profile, specialty: e.target.value})}
                    className={`mt-1 block w-full rounded-md shadow-sm p-2 border focus:ring-blue-500 ${isEditing ? 'border-blue-300 bg-white' : 'border-gray-200 bg-gray-50'}`}
                    readOnly={!isEditing}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Формат работы</label>
                  <select 
                    value={profile.employment_format || 'Remote'} 
                    onChange={(e) => setProfile({...profile, employment_format: e.target.value})}
                    className={`mt-1 block w-full rounded-md shadow-sm p-2 border focus:ring-blue-500 ${isEditing ? 'border-blue-300 bg-white' : 'border-gray-200 bg-gray-50 appearance-none'}`}
                    disabled={!isEditing}
                  >
                    <option value="Remote">Remote</option>
                    <option value="Office">Office</option>
                    <option value="Hybrid">Hybrid</option>
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700">Навыки</label>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {(profile.skills || []).map((skill: string) => (
                      <span key={skill} className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
                        {skill}
                        {isEditing && (
                          <button onClick={() => removeSkill(skill)} className="ml-2 text-blue-500 hover:text-blue-700 font-bold">&times;</button>
                        )}
                      </span>
                    ))}
                  </div>
                  {isEditing && (
                    <div className="mt-3 flex gap-2">
                      <input 
                        type="text" 
                        value={newSkill}
                        onChange={(e) => setNewSkill(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && addSkill()}
                        placeholder="Новый навык (нажмите Enter)"
                        className="flex-1 rounded-md border-blue-300 shadow-sm p-2 border focus:ring-blue-500"
                      />
                      <button onClick={addSkill} className="bg-gray-200 px-4 py-2 rounded text-sm font-medium hover:bg-gray-300">Добавить</button>
                    </div>
                  )}
                </div>
              </div>
              
              <div className="pt-4 flex justify-end">
                {isEditing ? (
                  <div className="space-x-3">
                    <button 
                      onClick={() => {
                        if (profile.id) {
                          setIsEditing(false);
                          loadProfile(); // Reset changes
                        }
                      }} 
                      className="bg-gray-200 text-gray-800 px-4 py-2 rounded shadow hover:bg-gray-300 transition"
                    >
                      Отмена
                    </button>
                    <button 
                      onClick={handleSave} 
                      className="bg-green-600 text-white px-4 py-2 rounded shadow hover:bg-green-700 transition"
                    >
                      Сохранить
                    </button>
                  </div>
                ) : (
                  <button 
                    onClick={() => setIsEditing(true)} 
                    className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition"
                  >
                    Редактировать
                  </button>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
