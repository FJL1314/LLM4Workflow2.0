import { Card, Typography } from 'antd';
import FlowChart from '../../components/FlowGraph/FlowChart';
import type { DagData } from '../types';

const { Text } = Typography;

interface Props {
  dagData: DagData | null;
}

export default function DagPreviewCard({ dagData }: Props) {
  return (
    <Card title="DAG Preview" className="h-full rounded-2xl shadow-sm">
      {dagData ? (
        <div className="rounded-xl border border-[#e5e6eb] bg-white p-3">
          <Text strong>Graph View</Text>
          <div className="mt-3 h-[420px] overflow-hidden rounded-xl border border-[#f0f0f0] bg-white">
            <FlowChart width="100%" height={420} taskData={dagData} />
          </div>
        </div>
      ) : (
        <div className="flex h-[460px] items-center justify-center text-gray-400">
          No DAG data available
        </div>
      )}
    </Card>
  );
}