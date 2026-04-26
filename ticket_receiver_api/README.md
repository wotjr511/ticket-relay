# TicketReceiverAPI

TicketReceiverAPI는 Relay Processor로부터 전달받은 JSON 티켓을 수신하여, `type` 값에 따라 12개의 전용 핸들러 중 하나로 라우팅하여 처리한 후 성공 응답을 반환하는 경량 FastAPI 서비스입니다. Health Check 엔드포인트도 제공하여 업스트림 시스템에서 상태를 확인할 수 있습니다.

## 프로젝트 구조

ticket_receiver_api/
├── main.py
├── config.py
├── models.py
├── handlers.py
├── dispatcher.py
├── utils.py
├── requirements.txt
├── README.md
└── .env.example

## 설치 방법 (Windows)

cd ticket_receiver_api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

## 설정 (Configuration)

환경 변수로 설정을 관리하며, pydantic-settings를 사용합니다. 모든 변수는 TICKET_RECEIVER_ 접두사를 가집니다.

.env.example 파일을 복사하여 사용하세요:

copy .env.example .env

### 주요 설정 항목

- TICKET_RECEIVER_HOST: 서버 바인딩 호스트 (기본값: 0.0.0.0)
- TICKET_RECEIVER_PORT: 서버 포트 (기본값: 8000)
- TICKET_RECEIVER_LOG_LEVEL: 로그 레벨 (기본값: INFO)
- TICKET_RECEIVER_LOG_FILE: 로그 파일 경로 (기본값: ticket_receiver_api.log)
- TICKET_RECEIVER_CORS_ORIGINS: CORS 허용 Origin (기본값: *)
- TICKET_RECEIVER_RELOAD: 개발용 reload 활성화 (기본값: false)

## 실행 방법

python main.py

또는 uvicorn 직접 실행:

uvicorn main:app --host 0.0.0.0 --port 8000

API 문서는 다음 주소에서 확인할 수 있습니다:
- http://localhost:8000/docs
- http://localhost:8000/redoc

## 주요 엔드포인트

### GET /health

curl http://localhost:8000/health

### POST /tickets

curl -X POST http://localhost:8000/tickets ^
  -H "Content-Type: application/json" ^
  -d "{\"type\": 3, \"title\": \"Sample Ticket\", \"data\": {\"source\": \"relay\"}}"

## Dispatcher Pattern

dispatcher.py에서 TicketDispatcher 클래스가 type 값을 기준으로 12개의 핸들러(handle_type_1 ~ handle_type_12) 중 하나를 선택하여 호출합니다.

handlers.py에 각 타입별 실제 처리 로직을 구현하시면 됩니다.

## 로깅

로그는 콘솔과 설정된 로그 파일에 동시에 기록됩니다.