import { Radar } from '@ant-design/plots';
import { Button, Card, Col, Descriptions, Divider, Progress, Row, Tag, Typography } from 'antd';
import { useMemo, useRef } from 'react';

const { Text } = Typography;

interface Props {
  loading: boolean;
  report: any;
  selectedCount: number;
  onGenerate: () => void;
}

export default function ReportCard({
  loading,
  report,
  selectedCount,
  onGenerate,
}: Props) {
  const radarRef = useRef<any>(null);
  const radarWrapRef = useRef<HTMLDivElement | null>(null);

  const downloadRadarJpg = () => {
    const canvas = radarWrapRef.current?.querySelector('canvas') as HTMLCanvasElement | null;
    if (!canvas) return;

    const scale = 4;

    const exportCanvas = document.createElement('canvas');
    exportCanvas.width = canvas.width * scale;
    exportCanvas.height = canvas.height * scale;

    const ctx = exportCanvas.getContext('2d');
    if (!ctx) return;

    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, exportCanvas.width, exportCanvas.height);
    ctx.scale(scale, scale);
    ctx.drawImage(canvas, 0, 0);

    exportCanvas.toBlob(
      (blob) => {
        if (!blob) return;

        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');

        a.href = url;
        a.download = 'workflow-radar-chart.jpg';
        a.click();

        URL.revokeObjectURL(url);
      },
      'image/jpeg',
      0.98
    );
  };

  const radarData = useMemo(() => {
    if (!report?.dimension_scores || !Array.isArray(report.dimension_scores)) return [];

    return report.dimension_scores.map((item: any) => ({
      shortName: item.dimension_name,
      fullName: item.dimension_name,
      score: Number(item.score || 0),
    }));
  }, [report]);

  const normalizedScore = useMemo(() => {
    if (!report) return 0;
    return Number(report.normalized_score || 0);
  }, [report]);

  const reportMeta = useMemo(() => report?.rubric_metadata || {}, [report]);

  const evaluatorModelText = useMemo(() => {
    if (!report?.evaluator_model) return '-';
    return String(report.evaluator_model).replace('gemini/', '').replace(/-/g, ' ');
  }, [report]);

  const evaluationTimeText = useMemo(() => {
    const raw = report?.evaluation_timestamp;
    if (!raw) return '-';

    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return raw;

    return date.toLocaleString('zh-CN', { hour12: false });
  }, [report]);

  const scoreTags = useMemo(() => {
    if (!report?.dimension_scores || !Array.isArray(report.dimension_scores)) return [];

    return report.dimension_scores.map((item: any) => {
      const score = Number(item.score || 0);

      let color = 'default';
      let label = `${item.dimension_name} general`;

      if (score >= 4.5) {
        color = 'success';
        label = `${item.dimension_name} excellent`;
      } else if (score >= 4.0) {
        color = 'processing';
        label = `${item.dimension_name} good`;
      } else if (score >= 3.0) {
        color = 'warning';
        label = `${item.dimension_name} medium`;
      } else {
        color = 'error';
        label = `${item.dimension_name} weak`;
      }

      return { color, label };
    });
  }, [report]);

  const radarConfig = {
    data: radarData,
    xField: 'shortName',
    yField: 'score',

    height: 560,
    autoFit: true,

    theme: {
      styleSheet: {
        fontFamily: 'Times New Roman',
      },
    },

    meta: {
      score: { min: 0, max: 5 },
    },

    appendPadding: [50, 80, 50, 80],

    area: {
      style: {
        fillOpacity: 0.25,
      },
    },

    line: {
      style: {
        lineWidth: 2,
        stroke: '#1677ff',
      },
    },

    point: {
      size: 4,
      style: {
        stroke: '#1677ff',
        lineWidth: 1,
      },
    },

    axis: {
      x: {
        labelFontFamily: 'Times New Roman',
        labelFontWeight: 900,
        labelFill: '#000000',
        labelFontSize: 15,
        labelFormatter: (text: string) => {

          const words = text.split(' ');
          const lines: string[] = [];

          for (let i = 0; i < words.length; i += 2) {
            lines.push(words.slice(i, i + 2).join(' '));
          }

          return lines.join('\n');
        },
      },

      y: {
        labelFontFamily: 'Times New Roman',
        labelFill: '#666666',
        labelFontSize: 12,
      },
    },

    legend: {
      color: false,
    },
  };

  return (
    <Card
      title="Stage 5: Evaluation Result Generation"
      className="rounded-2xl shadow-sm"
      extra={
        <Button type="primary" loading={loading} onClick={onGenerate}>
          Generate Evaluation Report
        </Button>
      }
    >
      <div className="flex items-center justify-between">
        <Text type="secondary">
          Generate the evaluation report from the selected rubric dimensions.
        </Text>
        <Text type="secondary">Total Selected: {selectedCount}</Text>
      </div>

      <Divider />

      {report ? (
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={14}>
            <Card
              title="Multidimensional evaluation radar chart"
              size="small"
              className="rounded-xl"
              extra={
                <Button size="small" onClick={downloadRadarJpg}>
                  Save HD JPG
                </Button>
              }
            >
            <div
              ref={radarWrapRef}
              style={{
                height: 560,
                maxWidth: 760,
                margin: '0 auto',
              }}
            >
              <Radar
                {...radarConfig}
                onReady={(plot) => {
                  radarRef.current = plot;
                }}
              />
            </div>
            </Card>
          </Col>

          <Col xs={24} lg={10}>
            <Card title="Evaluation Summary" size="small" className="rounded-xl">
              <div className="mb-4">
                <Text strong>Overall score</Text>
                <div className="mt-2">
                  <Progress
                    percent={Number(((normalizedScore / 5) * 100).toFixed(0))}
                    format={() => `${normalizedScore.toFixed(2)} / 5`}
                  />
                </div>
              </div>

              <Descriptions column={1} bordered size="small" className="mb-4">
                <Descriptions.Item label="score">
                  {normalizedScore.toFixed(2)}
                </Descriptions.Item>

                <Descriptions.Item label="Number of evaluation dimensions">
                  {reportMeta.total_dimensions ?? report?.dimension_scores?.length ?? '-'}
                </Descriptions.Item>

                <Descriptions.Item label="generic dimensions">
                  {reportMeta.generic_dimensions ?? '-'}
                </Descriptions.Item>

                <Descriptions.Item label="Task-specific dimensions">
                  {reportMeta.task_specific_dimensions ?? '-'}
                </Descriptions.Item>

                <Descriptions.Item label="Evaluation model">
                  {evaluatorModelText}
                </Descriptions.Item>

                <Descriptions.Item label="Evaluation time">
                  {evaluationTimeText}
                </Descriptions.Item>
              </Descriptions>

              <div className="flex flex-wrap gap-2">
                {scoreTags.slice(0, 4).map((item: any, index: number) => (
                  <Tag key={index} color={item.color}>
                    {item.label}
                  </Tag>
                ))}
              </div>
            </Card>
          </Col>
        </Row>
      ) : (
        <div className="py-8 text-center text-gray-400">No report generated yet</div>
      )}
    </Card>
  );
}