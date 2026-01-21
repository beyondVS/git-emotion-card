# 🎭 Git Emotion Card

> **"당신의 커밋에는 감정이 담겨 있습니다."**
>
> GitHub 활동 로그를 분석하여 개발자의 현재 상태와 감정을 위트 있는 프로필 카드로 만들어주는 서비스입니다.

## 📖 Project Overview

개발자들은 하루 종일 코드와 씨름하며 기쁨, 분노, 좌절, 그리고 해탈을 경험합니다. 하지만 GitHub 프로필의 잔디(Contribution Graph)는 그저 초록색일 뿐이죠.

**Git Emotion Card**는 단순한 활동 횟수를 넘어, **그 속에 담긴 개발자의 '진짜 상태'**를 분석합니다.
AI가 당신의 커밋 메시지와 이슈 댓글을 읽고, 현재 당신이 "버그와 레슬링 중"인지, "배포 후 평온한 상태"인지 알려줍니다.

### ✨ Key Features

- **📊 GitHub Event Analysis:** Push, Issue, PR, Review 등 다양한 Public 이벤트를 수집합니다.
- **🤖 Persona Generation:** Google Gemini가 분석된 데이터를 바탕으로 위트 있는 상태 메시지와 페르소나를 생성합니다.
    - *예: "키보드 화형식 진행 중", "모니터와 물아일체", "작전 대성공"*
- **⚖️ Neutral Bias Correction:** 개발자 특유의 사무적인 말투(Neutral) 속에 숨겨진 진짜 감정을 찾아냅니다.

## 🛠 Tech Stack

- **Infrastructure:** Docker, Docker Compose
- **Backend:** Python 3.11, Django 5.2
- **Database:** PostgreSQL 15
- **Cache & Queue:** Redis 7, Celery 5
- **AI:** Google Gemini API
- **Tooling:** Ruff, uv, Uvicorn

## 🚀 Getting Started

이 프로젝트는 Docker Compose를 사용하여 손쉽게 로컬 개발 환경을 구축할 수 있습니다.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed
- Google Gemini API Key

### Installation & Run (Docker)

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/git-emotion-card.git
   cd git-emotion-card
   ```

2. **Set up environment variables**
   `backend/.env.example` 파일을 복사하여 `backend/.env` 파일을 생성하고 필요한 키를 입력하세요.
   ```bash
   cp backend/.env.example backend/.env
   ```
   **`backend/.env` 필수 수정 항목:**
    - `GEMINI_API_KEY`: Google AI Studio에서 발급받은 키 입력
    - `SECRET_KEY`: Django 시크릿 키 (임의의 문자열)

3. **Run with Docker Compose**
   ```bash
   docker compose up --build
   ```
    - **Backend API:** `http://localhost:8000`
    - **PostgreSQL:** Port `5432`
    - **Redis:** Port `6379`

4. **Manage Database (Migrations)**
   컨테이너가 실행 중인 상태에서 새 터미널을 열고 실행하세요.
   ```bash
   docker compose exec backend python manage.py migrate
   ```

### Local Development (Optional)

Docker 없이 로컬에서 직접 실행하려면 다음 단계를 따르세요. (Redis 및 PostgreSQL이 로컬에 설치되어 있어야 합니다.)

1. **Install dependencies**
   ```bash
   cd backend
   uv sync
   ```

2. **Run Server**
   ```bash
   uv run python manage.py runserver
   # or with Celery
   uv run celery -A config worker -l info
   ```

## 📂 Project Structure

```
git-emotion-card/
├── backend/
│   ├── config/             # Django settings & Celery config
│   ├── card/               # Django App (Core Logic)
│   ├── playground/         # AI Model Experiments
│   ├── Dockerfile          # Backend Image
│   ├── pyproject.toml      # Dependencies (Managed by uv)
│   └── .env                # Environment Variables (Not committed)
├── docker-compose.yml      # Service Orchestration (App, DB, Redis, Worker)
└── README.md
```

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.