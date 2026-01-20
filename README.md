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
- **🧠 AI Emotion Detection:** `RoBERTa` 기반 모델을 사용하여 텍스트에 담긴 미세한 감정(기쁨, 분노, 불안, 슬픔 등)을 분석합니다.
- **🤖 Persona Generation:** Google Gemini가 분석된 데이터를 바탕으로 위트 있는 상태 메시지와 페르소나를 생성합니다.
    - *예: "키보드 화형식 진행 중", "모니터와 물아일체", "작전 대성공"*
- **⚖️ Neutral Bias Correction:** 개발자 특유의 사무적인 말투(Neutral) 속에 숨겨진 진짜 감정을 찾아냅니다.

## 🛠 Tech Stack

- **Language:** Python 3.11
- **Framework:** Django 5.2
- **AI & ML:**
    - Hugging Face Transformers (`xlm-roberta-base-finetuned-kor-8-emotions`)
    - Google Gemini API
- **Tooling:** Ruff, uv

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Google Gemini API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/git-emotion-card.git
   cd git-emotion-card
   ```

2. **Set up environment variables**
   `.env` 파일을 생성하고 필요한 키를 입력하세요.
   ```bash
   # backend/.env
   GITHUB_TOKEN=your_github_token
   GEMINI_API_KEY=your_gemini_api_key
   SECRET_KEY=your_django_secret_key
   ```

3. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   # or if you use uv
   uv sync
   ```

4. **Run the server**
   ```bash
   python manage.py runserver
   ```

## 📂 Project Structure

```
git-emotion-card/
├── backend/
│   ├── config/             # Django settings & configurations
│   ├── card/               # Django App(기능 구현)
│   ├── playground/         # 기능 테스트
│   ├── manage.py
│   └── pyproject.toml      # Dependencies & Tool settings
└── README.md
└── AGENTS.md               # AI Agent 동작 정의
```

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.
