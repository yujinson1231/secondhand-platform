# Tiny Second-hand Shopping Platform

간단한 중고거래 플랫폼입니다.

Flask 기반 서버 렌더링 웹 애플리케이션으로, 회원가입/로그인, 상품 등록·조회·검색, 전체/1:1 실시간 채팅,
유저·상품 신고 및 자동 차단/휴면 처리, 유저 간 포인트 송금, 마이페이지, 관리자 페이지를 제공합니다.

## 기술 스택

- Python 3.11+ / Flask 3
- Flask-SQLAlchemy (SQLite)
- Flask-Login (세션 기반 인증)
- Flask-WTF (폼 검증 + CSRF 방어)
- Flask-SocketIO + Socket.IO (실시간 채팅)
- Flask-Limiter (로그인/회원가입 요청 속도 제한)
- bleach (채팅 메시지 서버 측 새니타이징)

## 주요 기능

| 요구사항 | 구현 위치 |
|---|---|
| 회원가입 / 로그인 | [app/auth.py](app/auth.py) |
| 상품 등록 / 조회 / 상세 / 검색 | [app/products.py](app/products.py), [app/main.py](app/main.py) |
| 전체 채팅 / 1:1 채팅 | [app/chat.py](app/chat.py), [app/sockets.py](app/sockets.py) |
| 유저·상품 신고, 자동 차단/휴면 | [app/reports.py](app/reports.py) |
| 유저 간 송금 (포인트) | [app/transactions.py](app/transactions.py) |
| 마이페이지 (소개글/비밀번호 변경) | [app/profile.py](app/profile.py) |
| 관리자 페이지 (유저/상품/신고 관리, 조치 감사 로그) | [app/admin.py](app/admin.py) |

보안 기능으로 계정별 로그인 실패 잠금, 세션 자동 만료, 채팅 메시지 rate limiting(도배 방지)도 포함되어
있습니다. 개발 과정에서 고려한 보안 약점과 대응 방법은 [SECURITY.md](SECURITY.md)에, 체크리스트 재점검으로
실제 결함을 발견하고 수정한 과정은 [REPORT.md](REPORT.md) 4.3절/6장에 정리되어 있습니다.

## 환경 설정 및 실행 방법

### 1. 준비물

- Python 3.11 이상
- (선택) 휴대폰 등 다른 기기로 접속 테스트를 하려는 경우: 같은 Wi-Fi에 있다면 PC의 로컬 IP로 바로 접속
  가능하고, 네트워크가 다르거나 확실하지 않다면 `ngrok`(무료 계정 필요, 아래 5번 참고)을 쓰면 됩니다.

### 2. 저장소 클론 및 가상환경 설정

```bash
git clone <이 저장소 URL>
cd secondhand-platform

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. 환경 변수 설정

`.env.example`을 복사해서 `.env` 파일을 만들고 값을 채워주세요.

```bash
cp .env.example .env
```

`SECRET_KEY`는 아래 명령으로 무작위 값을 생성해서 채워 넣으세요. 

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

`.env` 파일 예시:

```ini
SECRET_KEY=<위에서 생성한 무작위 값>
FLASK_ENV=development
DATABASE_URL=sqlite:///app.db
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<원하는 관리자 비밀번호>
STARTING_BALANCE=100000
REPORT_THRESHOLD=3
```

- `ADMIN_USERNAME` / `ADMIN_PASSWORD`: 서버를 처음 실행할 때 자동으로 생성되는 관리자 계정입니다.
  **이 계정은 DB에 해당 아이디가 존재하지 않을 때 딱 한 번만 생성됩니다.** 즉, 서버를 이미 한 번 실행해서
  admin 계정이 만들어진 뒤에 `.env`의 `ADMIN_PASSWORD`만 바꿔서 재실행해도 기존 계정의 비밀번호는 자동으로
  바뀌지 않습니다. 비밀번호를 바꾸고 싶다면 (a) `instance/app.db`를 삭제하고 서버를 재실행해 전체를 초기화하거나
  (b) 관리자 계정으로 로그인해 마이페이지에서 비밀번호를 변경하세요.
- `STARTING_BALANCE`: 신규 가입자에게 지급되는 초기 포인트(가상 잔액)입니다.
- `REPORT_THRESHOLD`: 이 횟수 이상 신고되면 상품은 자동 차단, 유저는 자동 휴면 처리됩니다.

`.env` 파일은 `.gitignore`에 포함되어 있어 저장소에 커밋되지 않습니다.

### 4. 서버 실행

```bash
python run.py
```

- 기본적으로 `http://0.0.0.0:5000`에서 실행되어, 같은 네트워크의 다른 기기(휴대폰 등)에서도 접속할 수 있습니다.
- 컴퓨터 자신에게서 테스트할 때는 `http://localhost:5000` (또는 `http://127.0.0.1:5000`)으로 접속하세요.

### 5. 다른 기기(휴대폰 등)에서 접속하기 — ngrok 사용 (추천)

**PC와 휴대폰이
같은 Wi-Fi에 있다는 보장이 없는 상황**에서는 LAN IP 대신 `ngrok`으로 터널링하는 방법을 강력히 추천합니다.
같은 Wi-Fi 여부, 공유기 설정, WSL의 네트워킹 모드(NAT/미러링) 등 로컬 네트워크 환경에 전혀 영향받지 않고
어디서든 접속 가능한 공인 URL이 생기기 때문입니다.

1. [ngrok](https://ngrok.com/downloads)에서 무료 계정을 만들고 본인 OS에 맞는 설치 파일을 받아 설치합니다.
2. ngrok 대시보드에서 본인 authtoken을 확인한 뒤, 터미널에서 한 번만 등록합니다.
   ```bash
   ngrok config add-authtoken <내 authtoken>
   ```
3. 한 터미널에서는 이 프로젝트의 서버를 켜두고 (`python run.py`), **다른 터미널**을 새로 열어 아래 명령을 실행합니다.
   ```bash
   ngrok http 5000
   ```
4. ngrok이 출력하는 `Forwarding` 줄의 `https://xxxx.ngrok-free.app` 형태 주소를 그대로 휴대폰 브라우저에
   입력하면 접속됩니다. 실시간 채팅(Socket.IO)도 이 주소를 통해 정상적으로 동작합니다.
5. ngrok 무료 플랜은 처음 접속 시 경고 페이지가 한 번 뜰 수 있는데, "Visit Site" 버튼을 누르면 넘어갑니다.
6. 검사가 끝나면 ngrok 터미널을 Ctrl+C로 종료해 터널을 닫으세요. (열려 있는 동안은 URL을 아는 누구나
   접속할 수 있는 공개 주소이므로, 필요한 시간에만 켜두는 것이 안전합니다.)

> 같은 Wi-Fi에 있는 게 확실한 상황이라면, ngrok 없이도 콘솔에
> 출력되는 `http://<PC의 로컬 IP>:5000` 주소(Windows는 `ipconfig`, macOS/Linux는 `ifconfig`/`ip addr`로 확인)를
> 휴대폰에 그대로 입력해 접속할 수 있습니다. 다만 WSL을 사용 중이라면 기본(NAT) 네트워킹 모드에서는 외부 기기가
> WSL 내부로 접속하지 못할 수 있어(`.wslconfig`에 `networkingMode=mirrored` 설정 필요), 위 ngrok 방법이 더 확실합니다.

### 6. 접속 및 테스트

1. 4~5번에서 확인한 주소로 접속
2. 회원가입 후 로그인
3. 상품 등록, 검색, 채팅, 신고, 송금, 마이페이지 기능을 사용해볼 수 있습니다.
4. `.env`에 설정한 `ADMIN_USERNAME` / `ADMIN_PASSWORD`로 로그인하면 상단 메뉴에 "관리자" 링크가 나타나며,
   `/admin`에서 전체 유저/상품/신고 내역을 관리할 수 있습니다.

## 운영/배포 시 주의사항

- `FLASK_ENV=production`으로 설정하면 디버그 모드가 꺼지고 세션 쿠키에 `Secure` 속성이 붙습니다.
  **여러 사람이 접속 가능한 환경(같은 Wi-Fi, ngrok 등)에서는 반드시 `FLASK_ENV=production`으로 실행하세요.**
  디버그 모드가 켜진 채로 네트워크에 노출하면 Werkzeug 인터랙티브 디버거를 통해 임의 코드 실행으로
  이어질 수 있는 위험이 있습니다.
- 기본 SQLite + 개발용 서버(Werkzeug)는 과제/데모 목적입니다. 실제 서비스라면 PostgreSQL 등의 운영급 DB와 gunicorn/eventlet 기반 WSGI 서버, Flask-Limiter의 Redis 스토리지 등을 사용해야 합니다.

## 프로젝트 구조

```
secondhand-platform/
├── run.py                 # 앱 실행 진입점 (SocketIO 포함)
├── config.py               # 설정값 (환경변수 기반)
├── requirements.txt
├── .env.example
├── app/
│   ├── __init__.py         # 앱 팩토리, 보안 헤더, 에러 핸들러
│   ├── extensions.py       # db, login_manager, csrf, socketio, limiter
│   ├── models.py            # User, Product, Report, ChatMessage, Transaction
│   ├── forms.py              # WTForms (서버 측 입력 검증 + CSRF)
│   ├── decorators.py         # admin_required 등
│   ├── auth.py                # 회원가입/로그인/로그아웃
│   ├── main.py                 # 홈/검색
│   ├── products.py              # 상품 등록/조회/삭제, 이미지 업로드 검증
│   ├── chat.py                   # 채팅 페이지 라우트
│   ├── sockets.py                  # SocketIO 이벤트 (실시간 채팅, 방 권한 검증)
│   ├── reports.py                   # 신고, 자동 차단/휴면
│   ├── transactions.py               # 포인트 송금 (원자적 잔액 갱신)
│   ├── profile.py                     # 마이페이지
│   ├── admin.py                        # 관리자 페이지
│   ├── templates/
│   └── static/
└── SECURITY.md              # 보안 약점 점검 및 대응 내역
```
