# Capstone Survey Platform

설문 생성, 응답 수집, 신뢰도/품질 분석을 위한 웹 플랫폼입니다.

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [주요 기능](#주요-기능)
- [기술 스택](#기술-스택)
- [빠른 시작](#빠른-시작)
- [저장소 구조](#저장소-구조)
- [문서 안내](#문서-안내)
- [배포 요약](#배포-요약)
- [최종 제출 체크리스트](#최종-제출-체크리스트)

## 프로젝트 소개

이 프로젝트는 설문 문항과 응답 로그를 기반으로
신뢰도 지표(응답 성실성)와 문항 평가 결과를 제공하는 서비스입니다.

## 주요 기능

| 기능 | 설명 |
| --- | --- |
| 설문 생성/편집 | 관리자 화면에서 설문 생성 및 수정 |
| 응답 수집 | 내부 링크, 공개 링크, 1회용 공개 링크 응답 |
| 응답 로그 분석 | 문항별 체류시간, 변경횟수, 재방문, 오프라인 이벤트 수집 |
| 결과 분석 | 품질(quality), 구성도(construct), 통계(statistics) 평가 |
| CSV 내보내기 | 응답 feature / 문항 평가 CSV 다운로드 |

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Frontend | React, Vite, TypeScript, TailwindCSS |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite |
| AI | OpenAI API (chat/embedding) |
| Deploy | AWS Amplify (frontend), EC2 (backend) |

## 빠른 시작

1. 백엔드 실행 가이드: `backend/README.md`
2. 프론트 실행 가이드: `frontend/README.md`
3. 배포 전환 가이드: `docs/aws-deploy-checklist.md`

## 저장소 구조

```text
capcapcap/
├─ frontend/          # 프론트엔드 앱
├─ backend/           # 백엔드 앱
├─ docs/              # 제출/운영 문서
│  ├─ aws-deploy-checklist.md
│  └─ archive/        # 제출 불필요 문서 보관
└─ README.md
```

## 문서 안내

| 문서 | 용도 | 제출 기준 |
| --- | --- | --- |
| `README.md` | 저장소 개요/진입점 | 유지 |
| `frontend/README.md` | 프론트 실행/환경변수 | 유지 |
| `backend/README.md` | 백엔드 실행/환경변수/API | 유지 |
| `docs/aws-deploy-checklist.md` | AWS 전환/배포 절차 | 유지 |
| `docs/archive/*` | 실험/인수인계/중간 문서 | 보관 |

## 배포 요약

- 최종 배포 브랜치: `main`
- 프론트 필수: `VITE_USE_MOCK_API=false`
- 백엔드 필수: `OPENAI_API_KEY`, `FRONTEND_ORIGINS`
- 상세 절차: `docs/aws-deploy-checklist.md`

## 최종 제출 체크리스트

- [ ] `main` 브랜치에 최종 코드 반영 확인
- [ ] 프론트 환경변수 확인 (`VITE_USE_MOCK_API=false`)
- [ ] 백엔드 환경변수 확인 (`OPENAI_API_KEY`, `FRONTEND_ORIGINS`)
- [ ] `/health` 정상 응답 확인
- [ ] `/docs`(Swagger) 화면 확인
- [ ] 공개 링크 생성/응답/결과 분석 스모크 테스트 완료
- [ ] 제출 문서 세트 최신 상태 확인
