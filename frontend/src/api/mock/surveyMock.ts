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

const riskyWords = ['always', 'never', 'all', 'completely', 'must', 'very']

const sampleItemTexts = [
  'It was easy to find the information I needed while using the service.',
  'The survey item wording was clear and easy to understand.',
  'I felt similar survey items appeared repeatedly during response.',
  'Overall, this service met my expectations.',
]

export async function mockEvaluateItemQuality(
  request: EvaluateItemQualityRequest,
): Promise<ItemQualityResult> {
  await wait()

  const flaggedWords = riskyWords.filter((word) => request.text.includes(word))
  const tooShortPenalty = request.text.trim().length < 12 ? 22 : 0
  const doubleBarrelPenalty =
    request.text.includes('and') || request.text.includes('or') ? 12 : 0
  const score = Math.max(
    34,
    Math.min(96, 88 - flaggedWords.length * 13 - tooShortPenalty - doubleBarrelPenalty),
  )

  return {
    score,
    flaggedWords,
    suggestion:
      score <= 60
        ? 'Based on your recent experience, did this service help you achieve your goal?'
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
    trapItem: `${request.surveyContext || 'this survey'}: if you are reading carefully, choose 'Neutral' for this item.`,
    suggestedPosition: Math.min(Math.max(request.items.length - 1, 1), request.items.length),
  }
}

export async function mockGenerateReverseItem(
  request: GenerateReverseRequest,
): Promise<GenerateReverseResponse> {
  await wait(540)

  return {
    reverseItem: `In reverse wording: ${request.originalItem.replace(/[.?]$/g, '')}, but I did not feel that way.`,
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
          ? 'Trap-item error and unusual response-time deviation were detected.'
          : 'Response pattern is within the normal range.',
    }
  })

  const sincere_count = respondents.filter((row) => row.reliabilityScore >= 55).length
  const insincere_count = respondents.length - sincere_count

  return {
    survey_id: 'mock-survey',
    total_count: respondents.length,
    sincere_count,
    insincere_count,
    high_count: sincere_count,
    mid_count: 0,
    low_count: insincere_count,
    distribution: [
      { level: 'sincere', label: '성실', count: sincere_count },
      { level: 'insincere', label: '비성실', count: insincere_count },
    ],
    respondents,
  }
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
