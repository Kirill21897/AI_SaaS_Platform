import sys
import os
import json

# Add path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.track import Track
from app.models.user import User
from app.models.profile import Profile
from app.schemas.track import TrackCreate
from app.crud.crud_track import create_track
from app.crud.crud_user import create_user
from app.crud.crud_profile import create_profile
from app.schemas.user import UserCreate
from app.schemas.profile import ProfileCreate

demo_users = [
    {
        "email": "backend@demo.com",
        "password": "password123",
        "profile": {
            "first_name": "Алексей",
            "last_name": "Иванов",
            "about": "Backend разработчик с опытом 2 года. Пишу на Python, немного знаю Go.",
            "specialty": "Backend Developer",
            "location": "Москва",
            "employment_format": "Remote",
            "skills": ["python", "sql", "docker", "fastapi"]
        }
    },
    {
        "email": "data@demo.com",
        "password": "password123",
        "profile": {
            "first_name": "Елена",
            "last_name": "Смирнова",
            "about": "Люблю анализировать данные и строить графики.",
            "specialty": "Data Analyst",
            "location": "Санкт-Петербург",
            "employment_format": "Hybrid",
            "skills": ["python", "math", "sql", "tableau"]
        }
    },
    {
        "email": "empty@demo.com",
        "password": "password123",
        "profile": None
    }
]

seed_data = [
    {
        "title": "Backend Python Developer (FastAPI)",
        "description": "Интенсивный трек по изучению Python, асинхронного программирования и фреймворка FastAPI. Вы научитесь строить высоконагруженные микросервисы и работать с базами данных.",
        "specialization": "Backend Developer",
        "region": "Москва",
        "format": "Remote",
        "min_gpa": 4.0,
        "required_skills": {"python": 0.6, "sql": 0.3, "docker": 0.1},
        "tasks": ["Разработка API", "Оптимизация SQL запросов", "Настройка CI/CD"]
    },
    {
        "title": "Frontend React Engineer",
        "description": "Освоение современной экосистемы React: Next.js, хуки, стейт-менеджеры (Redux/Zustand) и SSR.",
        "specialization": "Frontend Developer",
        "region": "Санкт-Петербург",
        "format": "Hybrid",
        "min_gpa": 3.8,
        "required_skills": {"javascript": 0.4, "react": 0.4, "typescript": 0.2},
        "tasks": ["Создание SPA", "Верстка по макетам Figma", "Интеграция с REST API"]
    },
    {
        "title": "Data Scientist / ML Engineer",
        "description": "Погружение в машинное обучение. Классические алгоритмы, нейронные сети, работа с Pandas, Scikit-Learn и PyTorch.",
        "specialization": "Data Science",
        "region": "Global",
        "format": "Remote",
        "min_gpa": 4.5,
        "required_skills": {"python": 0.4, "math": 0.3, "ml": 0.3},
        "tasks": ["Анализ данных", "Обучение моделей", "A/B тестирование"]
    },
    {
        "title": "DevOps / SRE Engineer",
        "description": "Автоматизация процессов, инфраструктура как код (IaC), Kubernetes, мониторинг и логирование.",
        "specialization": "DevOps",
        "region": "Москва",
        "format": "Office",
        "min_gpa": 3.5,
        "required_skills": {"linux": 0.4, "docker": 0.3, "kubernetes": 0.3},
        "tasks": ["Настройка кластеров", "CI/CD пайплайны", "Мониторинг Prometheus"]
    },
    {
        "title": "Fullstack Engineer (MERN)",
        "description": "Изучение полного цикла разработки на стеке MongoDB, Express, React и Node.js. От создания базы данных до деплоя.",
        "specialization": "Fullstack Developer",
        "region": "Global",
        "format": "Remote",
        "min_gpa": 4.2,
        "required_skills": {"javascript": 0.3, "react": 0.3, "nodejs": 0.3, "mongodb": 0.1},
        "tasks": ["Разработка Fullstack приложений", "Настройка авторизации", "Работа с NoSQL"]
    },
    {
        "title": "Android Developer (Kotlin)",
        "description": "Разработка нативных мобильных приложений под Android с использованием Kotlin, Jetpack Compose и Coroutines.",
        "specialization": "Mobile Developer",
        "region": "Казань",
        "format": "Hybrid",
        "min_gpa": 4.0,
        "required_skills": {"kotlin": 0.5, "android sdk": 0.3, "java": 0.2},
        "tasks": ["Создание UI на Compose", "Интеграция с сервером", "Оптимизация производительности"]
    },
    {
        "title": "iOS Developer (Swift)",
        "description": "Разработка под экосистему Apple. Изучение Swift, SwiftUI, архитектуры MVVM и работы с CoreData.",
        "specialization": "Mobile Developer",
        "region": "Москва",
        "format": "Office",
        "min_gpa": 4.2,
        "required_skills": {"swift": 0.5, "ios sdk": 0.3, "xcode": 0.2},
        "tasks": ["Разработка iOS приложений", "Публикация в AppStore", "Анимации в SwiftUI"]
    },
    {
        "title": "Go Backend Engineer",
        "description": "Создание высококонкурентных и производительных сервисов на языке Go. Работа с микросервисами и gRPC.",
        "specialization": "Backend Developer",
        "region": "Global",
        "format": "Remote",
        "min_gpa": 4.4,
        "required_skills": {"golang": 0.6, "grpc": 0.2, "sql": 0.2},
        "tasks": ["Разработка микросервисов", "Профилирование кода", "Написание тестов"]
    },
    {
        "title": "System Analyst",
        "description": "Проектирование архитектуры систем, сбор и анализ требований, написание технических заданий (UML, BPMN).",
        "specialization": "System Analysis",
        "region": "Екатеринбург",
        "format": "Hybrid",
        "min_gpa": 3.9,
        "required_skills": {"uml": 0.3, "sql": 0.3, "api design": 0.4},
        "tasks": ["Сбор требований", "Проектирование API", "Моделирование бизнес-процессов"]
    },
    {
        "title": "QA Automation Engineer",
        "description": "Автоматизация тестирования на Python/Java, работа с Selenium, Playwright и настройка Allure отчетов.",
        "specialization": "QA Engineer",
        "region": "Global",
        "format": "Remote",
        "min_gpa": 3.7,
        "required_skills": {"python": 0.4, "selenium": 0.4, "pytest": 0.2},
        "tasks": ["Написание автотестов", "Интеграция тестов в CI", "Нагрузочное тестирование"]
    },
    {
        "title": "C++ Game Developer",
        "description": "Разработка игровых движков и механик на C++ и Unreal Engine.",
        "specialization": "Game Development",
        "region": "Global",
        "format": "Remote",
        "min_gpa": 4.1,
        "required_skills": {"c++": 0.5, "unreal engine": 0.3, "math": 0.2},
        "tasks": ["Оптимизация рендеринга", "Разработка игровых механик", "Интеграция физики"]
    },
    {
        "title": "Ruby Backend Engineer",
        "description": "Разработка веб-приложений на Ruby on Rails. Быстрое прототипирование и MVP.",
        "specialization": "Backend Developer",
        "region": "Москва",
        "format": "Hybrid",
        "min_gpa": 3.6,
        "required_skills": {"ruby": 0.5, "ruby on rails": 0.3, "postgresql": 0.2},
        "tasks": ["Разработка бизнес-логики", "Интеграция сторонних API", "Написание RSpec тестов"]
    },
    {
        "title": "Product Manager",
        "description": "Управление жизненным циклом IT-продукта. От CustDev до вывода на рынок и анализа метрик.",
        "specialization": "Product Management",
        "region": "Санкт-Петербург",
        "format": "Office",
        "min_gpa": 4.0,
        "required_skills": {"product management": 0.4, "agile": 0.3, "analytics": 0.3},
        "tasks": ["Проведение CustDev", "Приоритизация бэклога", "Анализ A/B тестов"]
    },
    {
        "title": "UI/UX Designer",
        "description": "Проектирование пользовательских интерфейсов. Работа в Figma, создание дизайн-систем и прототипов.",
        "specialization": "Design",
        "region": "Global",
        "format": "Remote",
        "min_gpa": 3.8,
        "required_skills": {"figma": 0.6, "ux research": 0.2, "prototyping": 0.2},
        "tasks": ["Отрисовка макетов", "Создание UI-китов", "Проведение юзабилити-тестов"]
    },
    {
        "title": "Data Analyst",
        "description": "Анализ данных для бизнеса. Работа с SQL, Tableau/PowerBI, и базовым Python.",
        "specialization": "Data Analysis",
        "region": "Москва",
        "format": "Hybrid",
        "min_gpa": 4.0,
        "required_skills": {"sql": 0.5, "python": 0.2, "tableau": 0.3},
        "tasks": ["Построение дашбордов", "Выгрузка данных", "Поиск инсайтов"]
    },
    {
        "title": "Blockchain Engineer",
        "description": "Разработка смарт-контрактов на Solidity, работа с Web3.js и сетями Ethereum/Polygon.",
        "specialization": "Blockchain",
        "region": "Global",
        "format": "Remote",
        "min_gpa": 4.3,
        "required_skills": {"solidity": 0.5, "javascript": 0.3, "web3": 0.2},
        "tasks": ["Написание смарт-контрактов", "Аудит безопасности", "Интеграция с frontend"]
    },
    {
        "title": "Cybersecurity Specialist",
        "description": "Защита инфраструктуры, пентестинг, поиск уязвимостей и аудит кода.",
        "specialization": "Security",
        "region": "Казань",
        "format": "Office",
        "min_gpa": 4.2,
        "required_skills": {"linux": 0.4, "network security": 0.4, "python": 0.2},
        "tasks": ["Проведение пентестов", "Анализ инцидентов", "Настройка WAF"]
    },
    {
        "title": "Technical Writer",
        "description": "Создание технической документации, API-справочников и руководств для разработчиков.",
        "specialization": "Documentation",
        "region": "Global",
        "format": "Remote",
        "min_gpa": 3.5,
        "required_skills": {"markdown": 0.4, "api documentation": 0.4, "english": 0.2},
        "tasks": ["Написание док для API", "Редактура статей", "Работа с OpenAPI/Swagger"]
    },
    {
        "title": "Rust Systems Engineer",
        "description": "Разработка системного ПО, сетевых сервисов и высоконагруженных компонентов на Rust.",
        "specialization": "Systems Programming",
        "region": "Global",
        "format": "Remote",
        "min_gpa": 4.5,
        "required_skills": {"rust": 0.6, "linux": 0.2, "networking": 0.2},
        "tasks": ["Разработка CLI-утилит", "Оптимизация памяти", "Написание многопоточного кода"]
    },
    {
        "title": "1C Developer",
        "description": "Разработка и поддержка конфигураций на платформе 1С:Предприятие 8.",
        "specialization": "Enterprise Development",
        "region": "Екатеринбург",
        "format": "Office",
        "min_gpa": 3.2,
        "required_skills": {"1c": 0.7, "sql": 0.2, "accounting": 0.1},
        "tasks": ["Доработка конфигураций", "Обновление баз", "Интеграция с внешними системами"]
    }
]

def load_seed_data():
    from app.db.base_class import Base
    from app.db.session import engine
    import app.models  # Ensures all models are loaded for create_all
    
    # Create tables if they don't exist yet
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Seed Users
        print("Checking demo users...")
        for u_data in demo_users:
            existing_user = db.query(User).filter(User.email == u_data["email"]).first()
            if not existing_user:
                print(f"Creating user {u_data['email']}...")
                user_in = UserCreate(email=u_data["email"], password=u_data["password"])
                new_user = create_user(db, obj_in=user_in)
                
                if u_data["profile"]:
                    print(f"Creating profile for {u_data['email']}...")
                    prof_data = u_data["profile"]
                    prof_data["user_id"] = new_user.id
                    prof_in = ProfileCreate(**prof_data)
                    create_profile(db, obj_in=prof_in)

        # Check if we already have tracks
        existing = db.query(Track).count()
        if existing > 0:
            print(f"Clearing {existing} existing tracks to load fresh seed data...")
            db.query(Track).delete()
            db.commit()

        print("Loading seed data...")
        for track_dict in seed_data:
            track_in = TrackCreate(**track_dict)
            created = create_track(db, obj_in=track_in)
            print(f"Created track: {created.title}")
            
        print("✅ Seed data loaded successfully!")
    except Exception as e:
        print(f"❌ Error loading seed data: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    load_seed_data()
