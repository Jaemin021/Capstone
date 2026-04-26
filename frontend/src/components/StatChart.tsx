import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

/**
 * 컴포넌트: StatChart
 * 역할: Recharts 기반 막대 차트를 재사용 가능하게 렌더링한다.
 */
export interface ChartDataPoint {
  name: string
  value: number
}

export interface StatChartProps {
  data: ChartDataPoint[]
  height?: number
  barColor?: string
  valueLabel?: string
}

export function StatChart({
  data,
  height = 280,
  barColor = '#0f766e',
  valueLabel = '값',
}: StatChartProps) {
  return (
    <div className="w-full" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 12, right: 12, bottom: 8, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="name" tick={{ fill: '#475569', fontSize: 12 }} />
          <YAxis tick={{ fill: '#475569', fontSize: 12 }} allowDecimals={false} />
          <Tooltip
            cursor={{ fill: '#f1f5f9' }}
            formatter={(value) => [value, valueLabel]}
            contentStyle={{
              borderRadius: 8,
              border: '1px solid #e2e8f0',
              boxShadow: '0 8px 24px rgba(15, 23, 42, 0.08)',
            }}
          />
          <Bar dataKey="value" fill={barColor} radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
