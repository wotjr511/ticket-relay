# Ticket Processing System

**End-to-End Ticket Relay & Processing Platform**

디렉토리에 생성된 티켓 파일을 실시간으로 감시 → Health Check → FastAPI 서버로 전달 → Type(1~12)에 따라 처리하는 **티켓 처리 시스템**입니다.

## 프로젝트 구성

- **ticket_relay_processor** — Producer (Watcher + Health Check + Forwarder)
- **ticket_receiver_api** — Consumer (FastAPI + Type Dispatcher)

## 기술 스택
- Python 3.9+
- FastAPI
- watchdog, requests, pydantic
- Docker & Docker Compose (예정)

## 빠른 시작

```bash
# 1. Repository 클론
git clone https://github.com/wotjr511/ticket-relay.git
cd ticket-relay

# 2. Receiver API 실행
cd ticket_receiver_api
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py

# 3. Relay Processor 실행 (새 터미널)
cd ../ticket_relay_processor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py