import { Button, Card, Empty, Table, Tag } from 'antd';
import { useMemo } from 'react';
import type { SimulationResults } from '../types';

interface Props {
  loading: boolean;
  simulationResults: SimulationResults | null;
  onGenerate: () => void;
}

export default function SimulationResultsCard({
  loading,
  simulationResults,
  onGenerate,
}: Props) {
  const simulationSummaryItems = useMemo(() => {

    if (!simulationResults) return [];
    return [
      { label: 'Models', value: simulationResults.summary?.n_models ?? 0 },
      { label: 'Steps', value: simulationResults.summary?.n_steps ?? 0 },
      {
        label: 'Avg. Discriminatory Power',
        value: Number(simulationResults.summary?.avg_discriminatory_power ?? 0).toFixed(3),
      },
      {
        label: 'High-Discrimination Steps',
        value: simulationResults.summary?.high_discrimination_count ?? 0,
      },
      {
        label: 'Low-Discrimination Steps',
        value: simulationResults.summary?.low_discrimination_count ?? 0,
      },
    ];
  }, [simulationResults]);

  const rankingData = useMemo(() => {
    if (!simulationResults) return [];
    return Object.entries(simulationResults.model_rankings || {})
      .map(([model, score]) => ({
        key: model,
        model,
        score: Number(score),
      }))
      .sort((a, b) => b.score - a.score)
      .map((item, index) => ({
        ...item,
        rank: index + 1,
      }));
  }, [simulationResults]);

  const stepTableData = useMemo(() => {
    if (!simulationResults?.step_scores) return [];
    return Object.entries(simulationResults.step_scores).map(([step, modelScores]) => {
      const values = Object.values(modelScores || {}).map((v) => Number(v));
      const avg = values.length ? values.reduce((sum, v) => sum + v, 0) / values.length : 0;
      return {
        key: step,
        step,
        ...modelScores,
        avg,
      };
    });
  }, [simulationResults]);

  const stepTableColumns = useMemo(() => {
    if (!simulationResults?.step_scores) return [];
    const firstStep = Object.values(simulationResults.step_scores || {})[0] || {};
    const modelNames = Object.keys(firstStep);

    return [
      { title: 'Step', dataIndex: 'step', key: 'step' },
      ...modelNames.map((model) => ({
        title: model,
        dataIndex: model,
        key: model,
        render: (value: number) => Number(value).toFixed(3),
      })),
      {
        title: 'Avg',
        dataIndex: 'avg',
        key: 'avg',
        render: (value: number) => Number(value).toFixed(3),
      },
    ];
  }, [simulationResults]);

  const discriminationData = useMemo(() => {
    if (!simulationResults?.discriminatory_power) return [];
    return Object.entries(simulationResults.discriminatory_power).map(([step, value]) => ({
      key: step,
      step,
      value: Number(value),
    }));
  }, [simulationResults]);

  return (
    <Card
      title="Stage 3: Multi-Agent Discrepancy Analysis"
      className="rounded-2xl shadow-sm mb-6"
      extra={
        <Button type="primary" loading={loading} onClick={onGenerate}>
        Discrepancy Analysis
        </Button>
      }
    >
      {!simulationResults ? (
        <Empty description="No simulation results yet" />
      ) : (
        <div className="space-y-6">
          <div>
            <div className="text-[16px] font-semibold mb-3">Simulation Summary</div>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {simulationSummaryItems.map((item) => (
                <Card key={item.label} size="small" className="rounded-xl">
                  <div className="text-gray-500 text-sm">{item.label}</div>
                  <div className="text-[20px] font-semibold text-black mt-1">{item.value}</div>
                </Card>
              ))}
            </div>
          </div>

          <div>
            <div className="text-[16px] font-semibold mb-3">Model Rankings</div>
            <Table
              size="small"
              pagination={false}
              dataSource={rankingData}
              columns={[
                { title: 'Rank', dataIndex: 'rank', key: 'rank', width: 80 },
                { title: 'Model', dataIndex: 'model', key: 'model' },
                {
                  title: 'Score',
                  dataIndex: 'score',
                  key: 'score',
                  render: (value: number) => Number(value).toFixed(3),
                },
              ]}
            />
          </div>

          <div>
            <div className="text-[16px] font-semibold mb-3">Step-wise Simulation Matrix</div>
            <Table
              size="small"
              pagination={false}
              scroll={{ x: true }}
              dataSource={stepTableData}
              columns={stepTableColumns}
            />
          </div>

          <div>
            <div className="text-[16px] font-semibold mb-3">Discrimination Analysis</div>

            <div className="flex flex-wrap gap-3 mb-4">
              <Tag color="blue">
                High-discrimination steps: {simulationResults.high_discrimination_steps?.length || 0}
              </Tag>
              <Tag color="default">
                Low-discrimination steps: {simulationResults.low_discrimination_steps?.length || 0}
              </Tag>
            </div>

            <Table
              size="small"
              pagination={false}
              dataSource={discriminationData}
              columns={[
                { title: 'Step', dataIndex: 'step', key: 'step' },
                {
                  title: 'Discriminatory Power',
                  dataIndex: 'value',
                  key: 'value',
                  render: (value: number) => Number(value).toFixed(3),
                },
              ]}
            />

            {(simulationResults.summary?.avg_discriminatory_power ?? 0) === 0 && (
              <div className="mt-3 text-gray-500 text-sm">
                All models produced highly consistent simulation scores across steps,
                indicating low discriminative variance in this workflow.
              </div>
            )}
          </div>
        </div>
      )}
    </Card>
  );
}