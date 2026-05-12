import './workflow.css';

import { Button, Card } from 'antd';
import { PromptParamsResponse } from '@/api/schema';
import { RemoteRunnable } from '@langchain/core/runnables/remote';
import RewriteFormModal from './RewriteModal';
import { Runnable } from '@langchain/core/runnables';
import { apiBaseUrl } from '@/utils/constants';
import { getPromptParams } from '@/api/api';
import { useParams } from 'react-router-dom';
import { useRequest } from 'ahooks';
import { useState } from 'react';

const runnableConfigs = {
  options: {
    timeout: 60000,
  },
};

const rewrite_query_chain: Runnable = new RemoteRunnable({
  url: `${apiBaseUrl}/workflow/rewrite_query`,
  ...runnableConfigs,
});

export interface SetValueParams {
  extracted_task: string;
  rewrite_queries: string[];
}

interface RwriteQueryProps {
  prompt?: string;
  setValue: (params: SetValueParams) => void;
}

const RewriteQuery: React.FC<RwriteQueryProps> = (props) => {
  const [open, setOpen] = useState(false);
  const { workflowId } = useParams();
  const [confirmLoading, setConfirmLoading] = useState(false);

  const { run, data: ParamsData } = useRequest(getPromptParams, {
    manual: true,
  });

  const onOpenModal = () => {
    setOpen(true);
    run(workflowId as string);
  };

  const handleRewrite = async (values: PromptParamsResponse) => {
    try {
      setConfirmLoading(true);
      const res = await rewrite_query_chain.invoke({ ...values });

      if (res?.length !== values.k) {
        throw new Error('Rewrite query failed');
      } else {
        props.setValue({ extracted_task: values.text, rewrite_queries: res });
        setOpen(false);
      }
    } catch (e) {
      console.log('queryRewrite error:', e);
      throw new Error('Rewrite query failed');
    } finally {
      setConfirmLoading(false);
    }
  };

  return (
    <Card className="mb-4 rounded-xl shadow-sm">
      <div className="flex items-center justify-between px-1 py-1">
        <div className="text-[15px] font-semibold text-gray-800">
          Stage 3: Task Rewriting
        </div>

        <Button type="primary" onClick={onOpenModal}>
          Set Params
        </Button>
      </div>

      <div className="px-1 pb-3 text-sm text-gray-400">
        Rewrite the extracted task into multiple retrieval-friendly queries.
      </div>
      <div className="mb-4 border-t border-gray-100" />

      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
        <div className="mb-2 text-sm font-medium text-gray-700">Prompt</div>

        <div className="whitespace-pre-wrap text-sm text-gray-600">
          {props?.prompt
            ? props.prompt.split('\n').map((line, index) => (
                <div className="mb-2" key={index}>
                  {line}
                </div>
              ))
            : 'No prompt available.'}
        </div>
      </div>

      <RewriteFormModal
        initialValues={{
          text: ParamsData?.data.text,
          k: ParamsData?.data.k,
        }}
        confirmLoading={confirmLoading}
        open={open}
        onRewrite={handleRewrite}
        onCancel={() => setOpen(false)}
      />
    </Card>
  );
};

export default RewriteQuery;