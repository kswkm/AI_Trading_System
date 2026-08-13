# 설정 가이드

## 1. 의존성 설치

```bash
pip install -r requirements.txt
```

## 2. 환경 변수 설정

`config/.env.example` 파일을 복사해 실제 환경 변수 파일을 만듭니다.

```bash
copy config\.env.example .env
```

필수 값:
- `TOSS_CLIENT_ID`
- `TOSS_CLIENT_SECRET`
- `TOSS_ACCOUNT_NUMBER`
- `TOSS_ACCOUNT_PASSWORD`
- `CLAUDE_API_KEY`

선택 값:
- `FINNHUB_API_KEY`
- `GMAIL_ADDRESS`
- `GMAIL_APP_PASSWORD`

## 3. 실행

```bash
python main.py
```

## 4. 주의사항
- 실제 주문은 실서버 환경에서 수행해야 합니다.
- 토스 API 문서와 응답 구조가 변경될 수 있으니, 운영 전 테스트가 필요합니다.
- 민감 정보는 `.env`에만 두고 저장소에 커밋하지 마세요.
