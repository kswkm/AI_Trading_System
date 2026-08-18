# 설정 가이드

## 1. 의존성 설치

```bash
pip install -r requirements.txt
```

## 2. 환경 변수 설정

`env.example` 파일을 복사해 실제 환경 변수 파일을 만듭니다.

```bash
copy env.example .env
```

필수 값:
- `TOSS_CLIENT_ID`
- `TOSS_CLIENT_SECRET`
- `GMAIL_ADDRESS`
- `GMAIL_APP_PASSWORD`

## 3. 실행

```bash
python main.py
```

## 4. 주의사항
- 이 프로젝트는 주문이나 결제를 수행하지 않고 분석 보고서만 생성합니다.
- 토스 API 문서와 응답 구조가 변경될 수 있으니, 운영 전 테스트가 필요합니다.
- 민감 정보는 `.env`에만 두고 저장소에 커밋하지 마세요.
