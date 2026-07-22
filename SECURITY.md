# 보안 점검 내역 (Security Checklist)

개발 과정에서 항목별로 어떤 보안 약점을 고려했고, 실제 코드에서 어떻게 대응했는지 정리한 문서입니다.
보고서의 "보안 약점 점검 및 대응" 항목에 그대로 활용할 수 있습니다.

이 문서는 두 단계로 작성되었습니다: (1) 최초 구현 시점에 고려한 항목들, (2) 완성 후 별도의 보안
체크리스트(회원가입/프로필 관리, 상품 등록/관리, 실시간 채팅, 안전 거래/신고 4개 영역)로 코드를 다시
점검하면서 **실제로 빠져 있던 4가지 항목을 발견하고 수정한 내역**(4-1~4-4). 2단계에서 발견한 항목들은
"체크리스트로 확인 → 코드에서 실제로 확인 → 수정 → 재검증"의 과정을 그대로 거쳤다.

## 1. SQL Injection

- **약점**: 사용자 입력을 문자열로 조립해 SQL을 실행하면 SQL Injection이 발생할 수 있음.
- **대응**: 모든 DB 접근을 SQLAlchemy ORM의 `select()` / 파라미터 바인딩 방식으로만 작성하고, 문자열 포매팅으로
  SQL을 직접 조립하는 코드는 전혀 사용하지 않음. 검색 기능([app/main.py](app/main.py))도 `Product.name.ilike(...)`
  파라미터 바인딩을 사용하며, 사용자가 `%`, `_` 같은 LIKE 와일드카드 문자를 입력해도 리터럴로 처리되도록 이스케이프 처리.

## 2. XSS (Cross-Site Scripting)

- **약점**: 상품명/설명, 소개글, 채팅 메시지 등 사용자 입력이 그대로 HTML에 삽입되면 저장형/DOM 기반 XSS 위험.
- **대응**:
  - 서버 렌더링 템플릿은 Jinja2 autoescape가 기본 적용되어 있고, 프로젝트 전체에서 `|safe` / `Markup`을 한 번도
    사용하지 않아 사용자 입력이 항상 이스케이프된 채로 출력됨.
  - 실시간 채팅 메시지는 서버 측에서 `bleach.clean()`으로 한 번 더 새니타이징([app/sockets.py](app/sockets.py)).
  - 브라우저에서 실시간 메시지를 DOM에 삽입할 때 `innerHTML`이 아닌 `textContent`만 사용
    ([app/static/js/chat.js](app/static/js/chat.js))하여, 메시지에 HTML 태그가 포함되어도 텍스트로만 렌더링됨.

## 3. CSRF (Cross-Site Request Forgery)

- **약점**: 로그인된 사용자가 악성 사이트를 방문했을 때, 그 사이트가 사용자 몰래 우리 서버에 상태 변경 요청(삭제, 송금 등)을
  보낼 수 있음.
- **대응**: `Flask-WTF`의 `CSRFProtect`를 앱 전체에 적용([app/extensions.py](app/extensions.py)). WTForms로 만든
  폼은 `form.hidden_tag()`, 그 외 순수 HTML 폼(로그아웃, 관리자 액션 버튼 등)은 `csrf_token()`으로 hidden input을
  수동 삽입하여 **예외 없이 모든 POST 폼에 CSRF 토큰이 포함**되도록 함. 코드 전체에 `csrf.exempt`는 한 곳도 없음.

## 4. 인증 및 세션 관리

- **비밀번호 저장**: 평문 저장 없이 `werkzeug.security.generate_password_hash`(salt 포함 scrypt 해시)로만 저장
  ([app/models.py](app/models.py)).
- **계정 존재 여부 노출(사용자 열거) 방지**: 로그인 실패 시 "아이디가 없습니다" / "비밀번호가 틀렸습니다"를 구분하지 않고
  항상 동일한 메시지를 반환. 또한 아이디가 존재하지 않는 경우에도 더미 해시로 `check_password_hash`를 호출해
  타이밍 차이로 계정 존재 여부가 유추되는 것을 방지([app/auth.py](app/auth.py)).
- **IP 기준 요청 속도 제한**: `Flask-Limiter`로 로그인(분당 15회), 회원가입(분당 10회) 요청을 IP 기준으로 제한.
- **세션 쿠키 하드닝**: `HttpOnly`(JS로 쿠키 탈취 불가), `SameSite=Lax`(크로스사이트 요청에 쿠키 미전송),
  운영 환경(`FLASK_ENV=production`)에서는 `Secure` 속성까지 추가([config.py](config.py)).
- **휴면 계정 로그인 차단**: `User.is_active`를 오버라이드해 `status != "active"`인 계정은 flask-login이
  자동으로 로그인 자체를 거부하도록 함. 이미 로그인된 세션이 이후 휴면 처리되는 경우까지 고려해,
  매 요청마다 `before_request`에서 현재 세션 사용자의 상태를 재확인 후 즉시 로그아웃 처리
  ([app/__init__.py](app/__init__.py)).
- **세션 자동 만료 (체크리스트 재점검에서 발견 → 수정, 4-1)**: `PERMANENT_SESSION_LIFETIME`(12시간)을 `config.py`에
  설정만 해두고, 실제로 세션을 "영구 세션"으로 표시하는 `session.permanent = True` 호출이 어디에도 없어 설정이
  전혀 적용되지 않고 있었음(개발자도구로 쿠키의 `Expires`가 `Session`으로만 표시되는 것으로 직접 확인). `login()`
  에서 `login_user()` 호출 직전에 `session.permanent = True`를 추가해 실제로 12시간 뒤 자동 로그아웃되도록 수정
  ([app/auth.py](app/auth.py)).
- **계정별 로그인 실패 잠금 (체크리스트 재점검에서 발견 → 수정, 4-2)**: 기존에는 IP당 요청 횟수 제한만 있어, 공격자가
  여러 IP를 바꿔가며 한 계정을 대상으로 무제한 대입 공격을 시도할 수 있었음. `User`에 `failed_login_count`,
  `locked_until` 컬럼을 추가하고, 로그인 실패 시 카운트를 올려 5회 이상이면 15분간 해당 **계정 자체**를 잠그도록
  구현([app/models.py](app/models.py), [app/auth.py](app/auth.py)). 로그인 성공 시 카운트/잠금을 초기화.
  - **구현 중 실제로 발견한 버그**: 잠금 시각을 `datetime.now(timezone.utc)`(시간대 있는 값)로 저장했는데, SQLite는
    `DateTime` 컬럼을 저장/조회할 때 시간대 정보를 보존하지 않아 다시 불러온 값은 시간대 없는(naive) 값이 됨.
    이 둘을 비교하는 순간 `TypeError: can't compare offset-naive and offset-aware datetimes`로 로그인 자체가
    500 에러로 죽는 문제가 실제 테스트에서 발생함. `now = datetime.now(timezone.utc).replace(tzinfo=None)`로
    시간대 정보를 뗀 값을 만들어 저장/비교 양쪽에 동일하게 사용하도록 통일해 해결.

## 5. 인가(Authorization) / IDOR / 권한 상승

- **상품 수정·삭제**: 본인이 등록한 상품인지 서버에서 재검증(`product.seller_id != current_user.id` → 403)
  ([app/products.py](app/products.py)). 클라이언트가 다른 사람의 상품 ID로 삭제를 요청해도 차단됨.
- **관리자 권한**: `role` 값은 클라이언트가 보낼 수 없고 DB의 세션 연결된 `current_user`에서만 판단.
  `/admin` 블루프린트 전체에 `before_request`로 로그인 + 관리자 권한 검사를 걸어, 일반 유저가 URL을 직접
  입력해도 403이 되도록 함([app/admin.py](app/admin.py), [app/decorators.py](app/decorators.py)).
- **관리자 계정 보호**: 관리자 계정은 휴면 처리/삭제 대상에서 제외, 관리자는 본인 계정을 삭제할 수 없도록 방지.
- **채팅방 접근 통제**: 1:1 채팅방 이름(`dm:<a>:<b>`)을 클라이언트가 마음대로 정할 수 있지만, 서버(SocketIO 이벤트
  핸들러)에서 방 이름에 포함된 두 유저 ID 중 하나가 현재 로그인한 유저인지 검증한 뒤에만 `join`/메시지 전송을 허용
  ([app/sockets.py](app/sockets.py)). 방 이름만 추측해서 남의 대화를 엿듣거나 메시지를 보내는 것을 방지.

## 6. 관리자 조치 감사 로그 (체크리스트 재점검에서 발견 → 수정, 4-3)

- **약점**: 관리자가 유저를 휴면 처리하거나 상품을 차단/삭제해도, "누가 언제 왜 그렇게 했는지"를 기록하는 감사
  로그(audit log)가 전혀 없어 사후 추적/책임 소재 확인이 불가능했음. `Report`(신고 접수 자체)는 기록되지만,
  그에 대한 "관리자의 조치"는 DB 상태만 바뀔 뿐 별도 기록이 남지 않는 것을 코드 리뷰로 확인.
- **대응**: `AuditLog` 테이블(누가/무엇을/언제)을 신설하고, 관리자 라우트의 상태 변경 동작 6곳
  (`suspend_user`, `activate_user`, `delete_user`, `block_product`, `unblock_product`, `delete_product`)
  전부에서 DB 상태 변경과 같은 트랜잭션 안에서 `AuditLog` 레코드를 함께 커밋하도록 구현
  ([app/models.py](app/models.py), [app/admin.py](app/admin.py)). 삭제 계열(`delete_user`, `delete_product`)은
  대상이 지워지기 전에 로그를 먼저 기록해 `target_id`를 안전하게 남기도록 순서를 맞춤. 관리자 전용 조회 화면
  (`/admin/audit-logs`)도 추가해 실제로 기록이 쌓이는지 확인 가능.

## 7. 파일 업로드

- **약점**: 업로드 파일 확장자를 검증하지 않으면 스크립트 파일 업로드/실행, 원본 파일명을 그대로 사용하면
  경로 조작(Path Traversal)이나 다른 사용자 파일 덮어쓰기 위험이 있음.
- **대응**([app/products.py](app/products.py)):
  - 폼 단(`FileAllowed`, `FileSize`)과 서버 단(`ALLOWED_IMAGE_EXTENSIONS` 화이트리스트) 이중으로 확장자를 검증.
  - 저장 파일명은 사용자가 보낸 파일명을 절대 사용하지 않고, `uuid4().hex + 검증된 확장자` 형태로 서버가
    직접 생성 → 경로 조작/파일 덮어쓰기/실행 가능한 파일 업로드 위험 원천 차단.
  - 요청 전체 크기 상한(`MAX_CONTENT_LENGTH = 5MB`)을 Flask 설정으로 강제.

## 8. 레이스 컨디션 (송금 기능)

- **약점**: "잔액 조회 → 조건 확인 → 차감"을 애플리케이션 레벨에서 순서대로 처리하면, 동시에 여러 요청이 들어왔을 때
  둘 다 "잔액 충분" 판단을 통과해 잔액이 마이너스가 되는 이중 출금(TOCTOU) 문제가 생길 수 있음.
  이는 실제 결제 시스템에서 반복적으로 발생해온 대표적 버그 유형.
- **대응**: 송금 기능은 실제 결제 연동 없이 **내부 포인트(가상 잔액) 시스템**으로 구현. 잔액 차감을
  `UPDATE users SET balance = balance - :amount WHERE id = :id AND balance >= :amount` 형태의 단일 조건부
  UPDATE 문으로 처리하여, 잔액 확인과 차감을 하나의 원자적 DB 연산으로 묶음. `rowcount == 0`이면 잔액 부족으로
  판단해 롤백([app/transactions.py](app/transactions.py)). 자기 자신에게 송금하는 것도 별도로 차단.

## 9. 신고/차단 기능 어뷰징 방지

- **중복 신고 방지**: `Report` 테이블에 `(reporter_id, target_type, target_id)` 유니크 제약을 DB 레벨로 걸어,
  같은 유저가 같은 대상을 여러 번 신고해 인위적으로 차단 임계치를 넘기는 것을 방지([app/models.py](app/models.py)).
- **자기 신고 방지**: 본인 상품/본인 계정은 신고할 수 없도록 서버에서 검증([app/reports.py](app/reports.py)).
- **자동 차단/휴면 임계치**: 신고 횟수를 애플리케이션 코드가 아니라 DB의 실제 `Report` 레코드 수를 매번 다시
  집계해서 판단하므로, 클라이언트가 신고 횟수 값을 조작해 보낼 수 있는 여지가 없음.

## 10. 실시간 채팅 메시지 Rate Limiting (체크리스트 재점검에서 발견 → 수정, 4-4)

- **약점**: 인증/방 권한/내용 새니타이징은 되어 있었지만, 한 유저가 초당 수십~수백 개의 메시지를 연속으로 보내
  채팅방을 도배(spam)하는 것을 막는 장치가 없었음. `Flask-Limiter`는 일반 HTTP 라우트에만 적용되고 Socket.IO
  이벤트에는 적용되지 않는다는 점을 확인.
- **대응**: 유저별로 "최근 10초 동안 보낸 메시지 수"를 서버 메모리에서 직접 추적하는 간단한 고정 윈도우(fixed
  window) 카운터를 구현. 10초 동안 5개를 초과하면 그 이후 메시지는 저장·브로드캐스트하지 않고 조용히 무시함
  ([app/sockets.py](app/sockets.py)).
- **참고 (범위 구분)**: 이 기능은 "로그인한 한 명의 유저가 채팅을 도배하는 것"을 막는 애플리케이션 레벨 스팸
  방지 기능이다. 여러 계정/여러 IP를 동원한 분산 공격이나 네트워크 레벨의 대량 트래픽 공격(DoS/DDoS)은 이
  기능의 방어 범위 밖이며, 일반적으로 방화벽·CDN·리버스 프록시 등 인프라 레벨에서 대응해야 하는 별개의 주제로
  본 과제 범위 밖으로 남겨둔다.

## 11. 보안 HTTP 헤더 및 CSP

- 모든 응답에 `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`(클릭재킹 방지),
  `Referrer-Policy: strict-origin-when-cross-origin`, 엄격한 `Content-Security-Policy`
  (`script-src 'self'`, 인라인 스크립트 전면 금지)를 적용([app/__init__.py](app/__init__.py)).
- **개발 중 실제로 발견한 문제**: 처음에는 채팅 페이지에 `<script>` 인라인 코드로 Socket.IO 로직을 작성했는데,
  브라우저에서 실제로 테스트해보니 CSP의 `script-src 'self'` 정책 때문에 인라인 스크립트가 조용히 차단되어
  채팅 전송이 동작하지 않는 문제를 발견함. "동작만 하면 되니 CSP에 `unsafe-inline`을 추가"하는 대신, 모든
  채팅 로직을 외부 정적 파일([app/static/js/chat.js](app/static/js/chat.js))로 분리하고 방/유저 정보는
  `data-*` 속성으로 전달하는 방식으로 재작성해 CSP를 느슨하게 하지 않고 문제를 해결함. 삭제 확인창
  (`onsubmit="confirm(...)"`) 같은 인라인 이벤트 핸들러도 동일한 이유로 전부 제거하고
  `data-confirm` 속성 + 위임 이벤트 리스너([app/static/js/confirm.js](app/static/js/confirm.js)) 방식으로 교체함.
  → 실제 테스트(체크리스트 검증 단계)를 통해서만 발견할 수 있었던 문제였고, "보안 설정을 강화했더니 기능이 깨져서
  다시 완화한다"가 아니라 "기능 구현 방식을 바꿔서 보안 설정을 유지한다"는 원칙을 지킨 사례.
- Socket.IO는 `cors_allowed_origins`를 지정하지 않아 기본값(동일 출처만 허용)으로 두어, 다른 사이트에서
  우리 서버의 웹소켓에 연결하는 것을 차단.

## 12. 에러 처리 / 정보 노출

- 운영 환경(`FLASK_ENV=production`)에서는 Flask 디버그 모드가 꺼져 스택 트레이스나 소스 코드가 노출되지 않음.
  400/403/404/413/500에 대해 공통 에러 페이지를 렌더링([app/__init__.py](app/__init__.py))하여 내부 구현
  세부사항이 사용자에게 노출되지 않도록 함.
- 로그인 실패 메시지를 통일해 계정 존재 여부가 에러 메시지로 드러나지 않도록 함 (4번 항목과 동일 맥락).

## 13. Mass Assignment 방지

- 모든 폼은 WTForms로 필드를 화이트리스트 방식으로 명시하고, `request.form`을 통째로 모델에 대입하는 코드는
  전혀 없음. 예를 들어 회원가입 시 `role`, `balance`, `status` 같은 민감한 필드는 폼에 아예 존재하지 않고
  서버 코드에서 고정값으로만 설정됨([app/auth.py](app/auth.py)).

## 14. 타임존(UTC/KST) 표시 정확성

- **문제**: 모든 시각은 `models.utcnow()`로 UTC 기준으로 저장하는데(서버 위치와 무관하게 일관성을 유지하기
  위한 올바른 설계), 화면에 표시할 때 이를 변환 없이 그대로 출력하고 있어서 한국 사용자에게는 실제 시각보다
  9시간 느리게 보이는 문제가 실제 테스트 중 발견됨 — 관리자 감사 로그(6번 항목)처럼 "언제 조치했는지"가
  핵심인 기록에서는 시각 정확성이 곧 감사 로그의 신뢰성과 직결되므로 단순 표시 버그 이상의 의미가 있음.
- **대응**: 저장 방식(UTC)은 그대로 유지하고, **표시할 때만** 한국 시간(UTC+9)으로 변환하는 Jinja2 커스텀 필터
  `kst`를 추가([app/__init__.py](app/__init__.py))해 신고 목록/송금 내역/감사 로그/채팅 이력 등 서버 렌더링
  화면에 일괄 적용. 실시간 채팅(Socket.IO로 전송되는 메시지)은 별도 경로라 서버가 보내는 ISO 타임스탬프에
  `tzinfo=UTC`를 명시적으로 붙여([app/sockets.py](app/sockets.py)) 브라우저의 `Date` 객체가 이를 UTC로
  올바르게 해석하고 사용자의 로컬 시간대로 자동 변환하도록 수정.

## 15. 사용하지 않은/도입하지 않은 항목과 이유

- **Open Redirect**: 로그인 성공 후 리다이렉트를 항상 `main.index`로 고정하고, `next` 쿼리 파라미터를 신뢰해
  리다이렉트하는 기능은 구현하지 않음. 편의성은 다소 떨어지지만, 검증되지 않은 리다이렉트 대상으로 인한
  피싱 위험을 원천적으로 제거하기 위한 선택.
- **Rate limiting 저장소**: 로그인/회원가입 제한(`Flask-Limiter`)은 현재 인메모리 저장소를 사용 중이며, 단일
  프로세스로 실행하는 과제/데모 환경에서는 문제가 없으나, 여러 워커로 스케일아웃하는 실제 서비스라면 Redis 등
  공유 저장소로 교체해야 함. 채팅 메시지 rate limiting(10번 항목)의 메모리 딕셔너리도 동일한 한계를 가짐
  (서버 재시작 시 카운터 초기화, 다중 워커 환경에서는 워커별로 따로 카운트됨).
- **DoS/DDoS 방어**: 10번 항목에서 구현한 채팅 rate limiting은 "한 유저의 도배 방지"이며, 분산된 다중 계정/IP를
  이용한 공격이나 네트워크 레벨의 대량 트래픽 공격에 대한 방어는 아님. 이런 방어는 일반적으로 애플리케이션
  코드가 아니라 방화벽/CDN/리버스 프록시 등 인프라 레벨에서 다루는 별개의 주제로 보고 과제 범위 밖으로 둠.
- **DB 마이그레이션 도구 부재**: `Flask-Migrate` 같은 스키마 마이그레이션 도구를 쓰지 않고 `db.create_all()`에
  의존하기 때문에, 이번에 `AuditLog` 테이블과 `User`의 `failed_login_count`/`locked_until` 컬럼을 추가할 때
  기존 SQLite 파일(`instance/app.db`)을 삭제하고 재생성해야 했다(테스트 데이터 손실). 과제 범위에서는
  문제가 되지 않지만, 실 서비스라면 마이그레이션 도구 도입이 필요하다.
