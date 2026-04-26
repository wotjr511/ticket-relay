# TicketRelayProcessor

TicketRelayProcessor는 Python 3.9 이상에서 실행되는 백엔드 프로세스입니다.
지정된 폴더를 주기적으로 감시하면서 티켓 JSON 파일을 읽고, 대상 API가 정상 상태일 때만 티켓 데이터를 전달합니다.

## 프로젝트 구조

```text
ticket_relay_processor\
├─ config.ini
├─ main.py
├─ config.py
├─ ticket_watcher.py
├─ api_health_checker.py
├─ ticket_forwarder.py
├─ ticket_logger.py
├─ processor.py
├─ utils.py
├─ requirements.txt
├─ logs\
│  └─ ticket_processing.log
├─ tickets\
└─ README.md
```

## 설치

PowerShell에서 다음 명령을 실행합니다.

```powershell
cd D:\projects\ticket-relay\ticket_relay_processor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 설정

실행 설정은 `config.ini`에서 관리합니다.

```ini
[watch]
directory = ./tickets
poll_interval = 5

[api]
target_url = http://localhost:8000/tickets
health_check_url = http://localhost:8000/health
timeout = 10
max_retries = 3

[logging]
log_dir = ./logs
log_level = INFO
```

설정 항목:

- `watch.directory`: 새 티켓 파일을 감시할 폴더입니다. 상대 경로는 `config.ini`가 있는 폴더 기준으로 해석됩니다.
- `watch.poll_interval`: 티켓 폴더를 다시 확인하는 주기입니다. 단위는 초입니다.
- `api.target_url`: 티켓 JSON을 전달할 대상 API 엔드포인트입니다.
- `api.health_check_url`: 티켓 전달 전 대상 API 상태를 확인할 헬스체크 엔드포인트입니다.
- `api.timeout`: API 요청 제한 시간입니다. 단위는 초입니다.
- `api.max_retries`: 최초 전달 실패 후 재시도할 횟수입니다.
- `logging.log_dir`: 티켓 처리 이력 로그가 저장될 폴더입니다.
- `logging.log_level`: 티켓 처리 이력 로그 레벨입니다. 예: `INFO`, `DEBUG`, `ERROR`.

설정은 코드에서도 안전하게 변경할 수 있습니다.

```python
from config import set_config

set_config("watch", "poll_interval", "10")
set_config("api", "target_url", "http://localhost:8000/tickets")
set_config("logging", "log_level", "INFO")
```

`set_config`는 `config.ini`를 안전하게 갱신한 뒤 활성 설정을 다시 로드합니다.

## 실행

PowerShell에서 다음 명령을 실행합니다.

```powershell
cd D:\projects\ticket-relay\ticket_relay_processor
.\.venv\Scripts\Activate.ps1
python main.py
```

프로세스를 종료하려면 `Ctrl+C`를 누릅니다. 종료 신호를 받으면 현재 처리 루프를 가능한 한 정상적으로 마무리합니다.

## 샘플 티켓 파일

설정된 티켓 폴더에 JSON 파일을 생성합니다. 예: `tickets\ticket-1001.json`

```json
{
  "ticket_id": "TCK-1001",
  "type": 3,
  "subject": "Unable to access account",
  "description": "Customer cannot sign in after password reset.",
  "priority": "high",
  "requester": {
    "name": "Jane Doe",
    "email": "jane@example.com"
  },
  "created_at": "2026-04-25T09:00:00Z"
}
```

필수 필드:

- `type`: `1`부터 `12`까지의 정수 또는 정수 형태의 문자열입니다.

`ticket_id`와 `subject`는 선택 필드입니다. `ticket_id`가 없으면 `ticket_receiver_api`에서 UUID를 자동 생성합니다.
필수 필드 외의 추가 필드는 그대로 유지되며 대상 API로 함께 전달됩니다.

## 처리 방식

1. ticket watcher는 설정된 폴더를 설정된 주기마다 확인합니다.
2. 파일 크기가 짧은 확인 시간 동안 변하지 않을 때만 처리 대상으로 봅니다.
3. 티켓 전달 전 헬스체크 API가 HTTP 2xx 응답을 반환해야 합니다.
4. 유효한 티켓 JSON은 `api.target_url`로 POST 요청됩니다.
5. API 전달 실패 시 지수 백오프 방식으로 재시도합니다.
6. API가 비정상이거나 전달에 실패한 티켓은 다음 처리 주기에 다시 시도될 수 있도록 표시됩니다.
7. JSON 형식이 잘못되었거나 필수 필드가 없는 티켓은 오류로 기록하고 무한 재시도하지 않습니다.

## 로그

일반 애플리케이션 로그는 콘솔과 `ticket_relay_processor.log`에 출력됩니다.

티켓별 처리 이력은 별도 파일에 JSON Lines 형식으로 기록됩니다.

```text
ticket_relay_processor\logs\ticket_processing.log
```

티켓 처리 이력 로그에는 다음 정보가 포함됩니다.

- 티켓 ID 또는 파일명
- 처리 시작 시간
- 처리 종료 시간
- 성공 또는 실패 상태
- 대상 API 응답 상태 코드와 메시지
- 실패 시 오류 메시지
- 처리 소요 시간
- 티켓 내용 요약

예시:

```json
{"error_message": null, "filename": "D:\\projects\\ticket-relay\\ticket_relay_processor\\tickets\\ticket-1001.json", "processing_duration_seconds": 0.142381, "processing_end_time": "2026-04-26T03:25:00.142381+00:00", "processing_start_time": "2026-04-26T03:25:00+00:00", "status": "success", "success": true, "target_api": {"message": "created", "status_code": 201}, "ticket_content_summary": {"field_count": 7, "priority": "high", "subject": "Unable to access account", "ticket_id": "TCK-1001", "type": "3"}, "ticket_id": "TCK-1001"}
```

`ticket_processing.log`는 매일 자동으로 회전됩니다. 회전된 파일명 예시는 다음과 같습니다.

```text
ticket_processing_2026-04-26.log
```
