import type {
  CitcPredictRequest,
  CitcPredictResponse,
  EvaluateItemQualityRequest,
  GenerateReverseRequest,
  GenerateReverseResponse,
  GenerateTrapRequest,
  GenerateTrapResponse,
  ItemQualityResult,
  ItemStatsResponse,
  ReliabilityRespondent,
  SurveyReliabilityResponse,
} from '../../types/survey'

const wait = (ms = 550) => new Promise((resolve) => window.setTimeout(resolve, ms))

const riskyWords = ['항상', '절대', '모두', '전혀', '무조건', '완벽하게', '매우']

const sampleItemTexts = [
  '서비스 이용 과정에서 필요한 정보를 쉽게 찾을 수 있었다.',
  '설문 문항의 표현이 명확하고 이해하기 쉬웠다.',
  '응답 과정에서 같은 의미의 문항이 반복된다고 느꼈다.',
  '전반적으로 이 서비스는 나의 기대를 충족했다.',
]

export async function mockEvaluateItemQuality(
  request: EvaluateItemQualityRequest,
): Promise<ItemQualityResult> {
  await wait()

  const flaggedWords = riskyWords.filter((word) => request.text.includes(word))
  const tooShortPenalty = request.text.trim().length < 12 ? 22 : 0
  const doubleBarrelPenalty =
    request.text.includes('그리고') || request.text.includes('또는') ? 12 : 0
  const score = Math.max(
    34,
    Math.min(96, 88 - flaggedWords.length * 13 - tooShortPenalty - doubleBarrelPenalty),
  )

  return {
    score,
    flaggedWords,
    suggestion:
      score <= 60
        ? '최근 이용 경험을 기준으로, 이 서비스의 핵심 기능이 목적 달성에 도움이 되었다고 느끼셨나요?'
        : null,
  }
}

export async function mockPredictCitc(
  request: CitcPredictRequest,
): Promise<CitcPredictResponse> {
  await wait(680)

  return {
    results: request.items.map((item, index) => {
      const embeddingScore = Math.max(0.18, Math.min(0.88, 0.72 - index * 0.04))
      const llmScore = item.text.length < 12 ? 0.24 : Math.max(0.32, 0.82 - index * 0.035)

      return {
        id: item.id,
        embeddingScore: Number(embeddingScore.toFixed(2)),
        llmScore: Number(llmScore.toFixed(2)),
        citcScore: Number((embeddingScore * 0.55 + llmScore * 0.45).toFixed(2)),
      }
    }),
  }
}

export async function mockGenerateTrapItem(
  request: GenerateTrapRequest,
): Promise<GenerateTrapResponse> {
  await wait(620)

  return {
    trapItem: `${request.surveyContext || '본 설문'}의 내용을 꼼꼼히 읽었다면 이 문항에는 '보통'을 선택해 주세요.`,
    suggestedPosition: Math.min(Math.max(request.items.length - 1, 1), request.items.length),
  }
}

export async function mockGenerateReverseItem(
  request: GenerateReverseRequest,
): Promise<GenerateReverseResponse> {
  await wait(540)

  return {
    reverseItem: `반대로 표현하면, ${request.originalItem.replace(/[.?]$/g, '')}고 느끼지 않았다.`,
  }
}

export async function mockGetSurveyReliability(): Promise<SurveyReliabilityResponse> {
  await wait(520)

  const respondents: ReliabilityRespondent[] = Array.from({ length: 36 }, (_, index) => {
    const baseScore = 94 - ((index * 11) % 58)
    const reliabilityScore = index % 9 === 0 ? 42 + index : baseScore
    const timePerItem = [24 + index, 18 + (index % 5) * 4, 21 + (index % 7), 16 + index]

    return {
      id: `R-${String(index + 1).padStart(3, '0')}`,
      submittedAt: `2026-04-${String(12 + (index % 12)).padStart(2, '0')} 14:${String(
        (index * 7) % 60,
      ).padStart(2, '0')}`,
      reliabilityScore,
      timePerItem,
      flagged: reliabilityScore < 60,
      reason:
        reliabilityScore < 60
          ? '함정 문항 오답 및 응답 시간 편차가 감지되었습니다.'
          : '응답 패턴이 정상 범위입니다.',
    }
  })

  return { respondents }
}

export async function mockGetSurveyItemStats(): Promise<ItemStatsResponse> {
  await wait(520)

  return {
    items: sampleItemTexts.map((text, index) => ({
      itemId: `item-${index + 1}`,
      text,
      mean: Number((3.4 + index * 0.21).toFixed(2)),
      variance: Number((index === 2 ? 0.18 : 0.72 + index * 0.13).toFixed(2)),
      count: 34 + index,
      missing: index % 2,
      distribution: [3 + index, 6 + index, 9 + index, 12 - index, 7 + index],
    })),
  }
}
