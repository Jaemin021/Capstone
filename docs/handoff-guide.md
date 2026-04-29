# 실행 및 배포 안내

## 현재 앱 흐름

이 프로젝트는 설문을 만드는 관리자 화면과, 응답자가 실제로 설문에 답하는 응답 화면이 함께 들어 있는 로컬 웹앱입니다.

- 관리자 화면: `http://127.0.0.1:5173/`
- 설문 생성: `http://127.0.0.1:5173/survey/create`
- 응답자 화면: `http://127.0.0.1:5173/survey/{survey_id}/respond`
- 결과 통계: `http://127.0.0.1:5173/survey/{survey_id}/results`
- 백엔드 문서: `http://127.0.0.1:8010/docs`

응답자 화면에서는 상단 관리자 메뉴가 보이지 않도록 분리했습니다. 응답자는 설문 응답만 하고, 대시보드나 결과 통계 화면으로 이동할 수 없습니다.

## 설문 링크 공유 방식

`127.0.0.1` 또는 `localhost`는 각자 자기 컴퓨터를 뜻합니다. 그래서 `http://127.0.0.1:5173/survey/.../respond` 링크를 그대로 다른 사람에게 보내면 상대방 컴퓨터에서는 열리지 않습니다.

같은 와이파이 안에서 테스트하려면:

1. 내 PC의 IPv4 주소를 확인합니다.
   ```powershell
   ipconfig
   ```
2. 백엔드를 외부 기기에서 접근 가능하게 실행합니다.
   ```powershell
   cd backend\survey\backend
   ..\..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8010
   ```
3. 프론트 `.env.local`을 내 PC IP로 바꿉니다.
   ```env
   VITE_API_BASE_URL=http://내_PC_IP:8010
   VITE_USE_MOCK_API=false
   ```
4. 프론트를 외부 기기에서 접근 가능하게 실행합니다.
   ```powershell
   cd frontend
   npm.cmd run dev -- --host 0.0.0.0 --port 5173
   ```
5. 응답자에게 아래 형태의 링크를 공유합니다.
   ```text
   http://내_PC_IP:5173/survey/{survey_id}/respond
   ```

Windows 방화벽에서 Node.js 또는 Python 접근 허용을 물어보면 허용해야 합니다.

학교 밖, 카카오톡 등 외부 네트워크로 배포하려면 로컬 PC가 아니라 실제 서버, 클라우드, 터널링 도구 같은 배포 환경이 필요합니다.

## USB로 넘길 때

USB로 폴더를 통째로 넘길 수는 있지만, 다른 조원 PC에서 바로 실행된다고 보장되지는 않습니다. 특히 Windows 가상환경 `.venv`는 PC 경로와 Python 설치 위치 영향을 받기 때문에 새 PC에서 다시 만드는 것이 안전합니다.

권장 전달 방식:

1. 프로젝트 폴더를 USB로 복사합니다.
2. 다른 PC에 Node.js와 Python을 설치합니다.
   - Node.js 22 계열 권장
   - Python 3.13 계열 권장
3. 백엔드 환경을 설치합니다.
   ```powershell
   cd backend
   python -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
4. 백엔드 `.env`를 만듭니다.
   ```powershell
   copy survey\backend\.env.example survey\backend\.env
   ```
   `survey\backend\.env`에 실제 `OPENAI_API_KEY`를 넣습니다.
5. 프론트 의존성을 설치합니다.
   ```powershell
   cd ..\frontend
   npm.cmd install
   ```
6. 프론트 `.env.local`을 확인합니다.
   ```env
   VITE_API_BASE_URL=http://127.0.0.1:8010
   VITE_USE_MOCK_API=false
   ```

## 로컬 실행법

터미널 1: 백엔드

```powershell
cd backend\survey\backend
..\..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8010
```

터미널 2: 프론트

```powershell
cd frontend
npm.cmd run dev
```

브라우저에서 접속:

```text
http://127.0.0.1:5173/
```

## 결과 통계가 안 나오는 경우

Cronbach alpha와 CITC 통계는 최소 2개 이상의 완료 응답이 있어야 계산됩니다. 응답이 1개뿐이면 통계 분석은 실패하는 것이 정상입니다.

설문 목록에서 각 설문별 응답 수를 확인하고, 응답이 2개 이상 쌓인 뒤 결과 통계 화면에서 통계 분석을 실행하세요.
