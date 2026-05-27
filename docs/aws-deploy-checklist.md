# AWS 배포 전환 체크리스트 (develop5 -> main)

이 체크리스트는 아래 구성 기준입니다.
- 프론트엔드: AWS Amplify
- 백엔드 API: EC2 (FastAPI)
- 최종 배포 브랜치: `main`

## 0) 전환 전 안전 준비

1. 전환 시간 동안 코드 변경을 잠시 멈춥니다.
2. `main`에 `develop5` 최종 코드가 반영됐는지 확인합니다.
3. 전환 전에 백업용 태그(또는 브랜치)를 남깁니다.

예시:

```bash
git checkout main
git pull --ff-only origin main
git tag submission-2026-05-28
git push origin submission-2026-05-28
```

## 1) GitHub 브랜치 운영 정책

1. 배포 기준 브랜치를 `main`으로 고정합니다.
2. 검증 완료 전까지 `develop5`는 롤백용으로 유지합니다.
3. 운영 스모크 테스트 통과 후에만 기존 브랜치를 삭제합니다.

## 2) Amplify 전환 (프론트엔드)

Amplify 콘솔에서:
1. `main` 브랜치를 연결/활성화합니다.
2. 기존 `develop5` 브랜치 환경변수를 `main`으로 복사합니다.
3. `VITE_PUBLIC_APP_ORIGIN`을 `main` 도메인으로 변경합니다.
4. `main` 브랜치를 재배포합니다.

필수 환경변수:

```env
VITE_USE_MOCK_API=false
VITE_API_BASE_URL=https://<YOUR_BACKEND_DOMAIN_OR_PUBLIC_IP>
VITE_PUBLIC_APP_ORIGIN=https://<MAIN_BRANCH_AMPLIFY_DOMAIN>
VITE_REQUIRE_MOBILE_RESPOND=false
```

주의:
- `VITE_API_BASE_URL`은 모바일 네트워크에서도 접근 가능해야 합니다.
- 공용 사용자 대상에서는 사설 IP(`172.x.x.x`, `192.168.x.x`, `10.x.x.x`)를 사용하지 않습니다.

## 3) EC2 전환 (백엔드)

EC2 접속 후:

```bash
cd <backend_repo_path>
git fetch origin
git rev-parse --short HEAD
git rev-parse --short origin/main
```

차이가 있으면 `main` 배포:

```bash
git checkout main
git pull --ff-only origin main
```

서비스 재시작:

```bash
sudo systemctl restart <backend_service_name>
sudo systemctl status <backend_service_name> --no-pager
sudo journalctl -u <backend_service_name> -n 200 --no-pager
```

## 4) 백엔드 런타임 환경변수 확인

백엔드 환경변수에 아래 값이 있어야 합니다.
- `OPENAI_API_KEY` (품질/구성도 평가용)
- `FRONTEND_ORIGINS`에 `main` 프론트 도메인 포함

전환 직후 권장 설정:
- 짧은 과도기 동안 `main + 기존 develop5 도메인` 동시 허용

예시:

```env
FRONTEND_ORIGINS=https://<MAIN_BRANCH_AMPLIFY_DOMAIN>,https://<OLD_DEVELOP5_DOMAIN>
OPENAI_API_KEY=sk-...
```

환경변수 수정 시 백엔드를 다시 재시작합니다.

## 5) 헬스체크 + 스모크 테스트

헬스체크 엔드포인트:

```text
GET /health
```

빠른 확인:

```bash
curl -s https://<BACKEND_HOST>/health
```

확인 포인트:
- `status: "ok"`
- `openai_api_key_configured: true|false`
- `allowed_origins: [...]`

프론트 스모크 테스트:
1. 강력 새로고침 (`Ctrl+F5`)
2. 설문 생성
3. 공개 링크 생성
4. 링크가 `.../public/s/mock-...` 형태가 아닌지 확인
5. 모바일로 응답 제출
6. 결과 페이지 진입
7. `quality / construct / statistics` 실행
8. CSV 2종 다운로드 확인

품질 평가 호출 시 HTML이 오거나 엉뚱한 응답이 오면:
- 프론트가 잘못된 API 주소를 호출 중일 수 있습니다.
- `VITE_API_BASE_URL`을 재확인합니다.
- Amplify `main` 빌드에 최신 환경변수가 반영됐는지 확인합니다.

## 6) 브랜치 정리 (검증 통과 후)

모든 테스트 통과 후 실행:

```bash
git push origin --delete develop5
```

로컬 정리(선택):

```bash
git branch -d develop5
```

## 7) 롤백 절차

전환 후 문제 발생 시:
1. Amplify에서 `develop5` 배포를 즉시 재활성화합니다.
2. EC2 백엔드를 이전 기준으로 되돌립니다.

```bash
git checkout develop5
git pull --ff-only origin develop5
sudo systemctl restart <backend_service_name>
```

3. 장애 시각/원인/복구 시간 기록을 남깁니다.

## 8) 제출 전 문서 정리 정책

문서를 일괄 삭제하지 말고, 운영/채점에 필요한 문서만 남깁니다.

권장 유지:
- `README.md`
- `docs/aws-deploy-checklist.md`

권장 정리(삭제 또는 보관):
- 실험 계획 문서
- 임시 인수인계 메모
- 중간 분석 초안

안전한 정리 순서:
1. 먼저 `docs/archive/`로 이동
2. 배포/채점 체크리스트 정상 동작 확인
3. 최종 확인 후 archive 삭제