import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BarChart3, Copy, Eye, FilePenLine, FilePlus2, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { createPublicSurveyLink, deleteSurvey, getSurveyList } from '../api/surveyApi'
import { LoadingSpinner } from '../components/LoadingSpinner'
import { useSurveyStore } from '../store/surveyStore'
import { useToastStore } from '../store/toastStore'
import type { SurveyListResponse } from '../types/survey'

function resolvePublicRespondUrl(origin: string, publicPath: string) {
  if (!origin) {
    return publicPath
  }

  try {
    const base = origin.endsWith('/') ? origin : `${origin}/`
    return new URL(publicPath, base).toString()
  } catch {
    return `${origin}${publicPath.startsWith('/') ? publicPath : `/${publicPath}`}`
  }
}

export function SurveyListPage() {
  const queryClient = useQueryClient()
  const pushToast = useToastStore((state) => state.pushToast)
  const resetDraft = useSurveyStore((state) => state.resetDraft)
  const surveyListQuery = useQuery({
    queryKey: ['survey-list'],
    queryFn: getSurveyList,
    retry: false,
  })
  const surveys = surveyListQuery.data?.surveys ?? []
  const origin = typeof window === 'undefined' ? '' : window.location.origin
  const configuredPublicOrigin = (import.meta.env.VITE_PUBLIC_APP_ORIGIN || '').trim()
  const publicOrigin = configuredPublicOrigin || origin
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; title: string } | null>(null)
  const [publicLinkLoadingId, setPublicLinkLoadingId] = useState<string | null>(null)

  const deleteSurveyMutation = useMutation<void, Error, string, { previous?: SurveyListResponse }>({
    mutationFn: deleteSurvey,
    onMutate: async (surveyId) => {
      await queryClient.cancelQueries({ queryKey: ['survey-list'] })
      const previous = queryClient.getQueryData<SurveyListResponse>(['survey-list'])

      if (previous) {
        queryClient.setQueryData<SurveyListResponse>(['survey-list'], {
          ...previous,
          surveys: previous.surveys.filter((survey) => survey.survey_id !== surveyId),
        })
      }

      return { previous }
    },
    onError: (error, _surveyId, context) => {
      console.error('[survey-list] delete mutation failed', error)
      if (context?.previous) {
        queryClient.setQueryData(['survey-list'], context.previous)
      }

      pushToast({
        type: 'error',
        title: '설문 삭제 실패',
        description: error.message || '삭제 중 오류가 발생했습니다.',
      })
    },
    onSuccess: () => {
      pushToast({
        type: 'success',
        title: '설문 삭제 완료',
      })
    },
    onSettled: () => {
      setDeleteTarget(null)
      queryClient.invalidateQueries({ queryKey: ['survey-list'] })
    },
  })

  const copyPublicRespondLink = async (surveyId: string) => {
    setPublicLinkLoadingId(surveyId)

    try {
      const link = await createPublicSurveyLink(surveyId, false)
      const isMockPublicLink =
        link.access_key.startsWith('mock-') ||
        link.public_path.includes('/public/s/mock-') ||
        link.public_path.includes('/public/o/mock-')
      const url = resolvePublicRespondUrl(publicOrigin, link.public_path)

      try {
        await navigator.clipboard.writeText(url)
        pushToast({
          type: 'success',
          title: '공유 링크 복사 완료',
          description: url,
        })
      } catch {
        pushToast({
          type: 'info',
          title: '공유 링크',
          description: url,
        })
      }

      if (isMockPublicLink) {
        pushToast({
          type: 'error',
          title: 'Mock 링크가 생성되었습니다',
          description:
            '배포 환경에서 VITE_USE_MOCK_API=false 설정이 필요합니다. 현재 링크는 다른 기기에서 동작하지 않을 수 있습니다.',
        })
      }
    } catch (error) {
      console.error('[survey-list] create public link failed', error)
      pushToast({
        type: 'error',
        title: '공유 링크 생성 실패',
        description: '링크 생성 중 오류가 발생했습니다.',
      })
    } finally {
      setPublicLinkLoadingId(null)
    }
  }

  return (
    <>
      <section className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-lg font-black text-slate-950">저장된 설문</h1>
            <p className="mt-1 text-sm text-slate-600">
              만든 설문을 확인하고, 미리보기 또는 결과 통계로 이동할 수 있습니다.
            </p>
          </div>
          <Link
            to="/survey/create"
            onClick={resetDraft}
            className="inline-flex items-center justify-center gap-2 rounded-md bg-teal-600 px-4 py-2 text-sm font-bold text-white hover:bg-teal-700"
          >
            <FilePlus2 size={17} />
            새 설문 만들기
          </Link>
        </div>

        {surveyListQuery.isLoading ? <LoadingSpinner compact label="설문 목록 불러오는 중" /> : null}

        {surveyListQuery.isError ? (
          <div className="rounded-lg bg-rose-50 p-4 text-sm font-semibold text-rose-900">
            설문 목록을 불러오지 못했습니다. 백엔드 서버가 실행 중인지 확인해 주세요.
          </div>
        ) : null}

        {!surveyListQuery.isLoading && !surveyListQuery.isError && surveys.length === 0 ? (
          <div className="rounded-lg bg-slate-50 p-4 text-sm leading-6 text-slate-600">
            아직 저장된 설문이 없습니다. 설문을 생성하면 목록에 표시됩니다.
          </div>
        ) : null}

        {surveys.length > 0 ? (
          <div className="space-y-3">
            {surveys.map((survey) => {
              const deletingId = deleteSurveyMutation.variables
              const isDeletingThis = deleteSurveyMutation.isPending && deletingId === survey.survey_id
              const isGeneratingPublicLink = publicLinkLoadingId === survey.survey_id

              return (
                <article key={survey.survey_id} className="rounded-lg border border-slate-200 p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div className="min-w-0">
                      <h2 className="truncate text-base font-black text-slate-950">{survey.title}</h2>
                      <p className="mt-1 text-xs font-semibold text-slate-500">ID: {survey.survey_id}</p>
                      <div className="mt-3 flex flex-wrap gap-2 text-xs font-bold text-slate-600">
                        <span className="rounded-md bg-slate-100 px-2 py-1">문항 {survey.normal_item_count}개</span>
                        <span className="rounded-md bg-slate-100 px-2 py-1">전체 표시 문항 {survey.item_count}개</span>
                        <span className="rounded-md bg-slate-100 px-2 py-1">응답 {survey.response_count}개</span>
                        {survey.last_response_at ? (
                          <span className="rounded-md bg-slate-100 px-2 py-1">
                            마지막 응답 {new Date(survey.last_response_at).toLocaleString()}
                          </span>
                        ) : null}
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                      <Link
                        to={`/survey/${survey.survey_id}/edit`}
                        className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
                      >
                        <FilePenLine size={15} />
                        수정
                      </Link>
                      <button
                        type="button"
                        className="inline-flex items-center gap-2 rounded-md border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50"
                        disabled={isGeneratingPublicLink}
                        onClick={() => copyPublicRespondLink(survey.survey_id)}
                      >
                        {isGeneratingPublicLink ? (
                          <LoadingSpinner compact label="링크 생성 중" />
                        ) : (
                          <>
                            <Copy size={15} />
                            공유 링크
                          </>
                        )}
                      </button>
                      <Link
                        to={`/survey/${survey.survey_id}/respond?preview=1`}
                        className="inline-flex items-center gap-2 rounded-md border border-indigo-300 px-3 py-2 text-sm font-bold text-indigo-700 hover:bg-indigo-50"
                      >
                        <Eye size={15} />
                        설문 미리보기
                      </Link>
                      <Link
                        to={`/survey/${survey.survey_id}/results`}
                        className="inline-flex items-center gap-2 rounded-md bg-slate-900 px-3 py-2 text-sm font-bold text-white hover:bg-slate-800"
                      >
                        <BarChart3 size={15} />
                        결과 통계
                      </Link>
                      <button
                        type="button"
                        className="inline-flex items-center gap-2 rounded-md border border-rose-300 px-3 py-2 text-sm font-bold text-rose-700 hover:bg-rose-50 disabled:border-slate-200 disabled:text-slate-400"
                        disabled={deleteSurveyMutation.isPending}
                        onClick={() => setDeleteTarget({ id: survey.survey_id, title: survey.title })}
                      >
                        {isDeletingThis ? <LoadingSpinner compact label="삭제 중" /> : <Trash2 size={15} />}
                        {isDeletingThis ? null : '삭제'}
                      </button>
                    </div>
                  </div>
                </article>
              )
            })}
          </div>
        ) : null}
      </section>

      {deleteTarget ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 px-4">
          <section className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl">
            <h2 className="text-lg font-black text-slate-950">설문 삭제 확인</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              이 설문을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.
            </p>
            <p className="mt-2 rounded-md bg-slate-50 px-3 py-2 text-sm font-semibold text-slate-700">
              {deleteTarget.title}
            </p>
            <div className="mt-5 flex gap-2">
              <button
                type="button"
                className="inline-flex flex-1 items-center justify-center rounded-md border border-slate-300 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:text-slate-400"
                disabled={deleteSurveyMutation.isPending}
                onClick={() => setDeleteTarget(null)}
              >
                취소
              </button>
              <button
                type="button"
                className="inline-flex flex-1 items-center justify-center rounded-md bg-rose-600 px-4 py-2 text-sm font-bold text-white hover:bg-rose-700 disabled:bg-slate-300"
                disabled={deleteSurveyMutation.isPending}
                onClick={() => deleteSurveyMutation.mutate(deleteTarget.id)}
              >
                삭제
              </button>
            </div>
          </section>
        </div>
      ) : null}
    </>
  )
}
