import React from 'react';
import { Button, Card, Popconfirm,List,message} from 'antd';
import { FileSearchOutlined, PlusOutlined } from '@ant-design/icons';
import { getWorkflowRubicList } from '@/api/api';
import { useNavigate } from 'react-router-dom';
import { useRequest } from 'ahooks';
import { DeleteOutlined } from '@ant-design/icons';
import { deleteWorkflowEvaluate } from '@/api/api';
const WorkflowEvaluateManage: React.FC = () => {
  const navigate = useNavigate();

  const { data, loading,refresh } = useRequest(getWorkflowRubicList);

  const workflowList = data?.data || [];
  const { run: runDeleteEvaluate, loading: deleteLoading } = useRequest(
    async (id: string) => {
      return await deleteWorkflowEvaluate(id);
    },
    {
      manual: true,
      onSuccess: (res) => {
        if (res.code === 200) {
          message.success(res.msg || 'Deletion successful');
          refresh();
        } else {
          message.error(res.msg || 'Deletion failed');
        }
      },
      onError: () => {
        message.error('Deletion failed');
      },
    }
  );

  return (
    <div className="p-6 bg-[#f5f7fa] min-h-[calc(100vh-66px)]">
      <Card className="rounded-xl shadow-sm mb-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center text-[24px] font-bold mb-2">
              <FileSearchOutlined className="mr-2" />
              Workflow Evaluation
            </div>
            <div className="text-gray-500">
              Used to view and manage workflow tasks awaiting evaluation, 
              supporting their subsequent entry into the evaluation process.
            </div>
          </div>

          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/workflow-evaluate/add')}
          >
            New a workflow evaluation task
          </Button>
        </div>
      </Card>

      <Card
        className="rounded-xl shadow-sm"
        title={<span className="font-semibold">Workflow Evaluation Task List</span>}
        loading={loading}
      >
        <List
          dataSource={workflowList}
          locale={{ emptyText: 'No workflow evaluation tasks available.' }}
          renderItem={(item: any) => (
            <List.Item className="hover:bg-gray-50 rounded-md px-4">
              <div className="w-full flex items-center justify-between">
                <div
                  className="cursor-pointer"
                  onClick={() => navigate(`/workflow-evaluate/${item.workflow_id}`)}
                >
                  <div className="font-medium text-[16px]">
                    Workflow {item.workflow_generate_id}
                  </div>
                  <div className="text-gray-400 text-sm mt-1">
                    Click to enter the workflow evaluation details page
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    type="link"
                    onClick={() => navigate(`/workflow-evaluate/${item.workflow_id}`)}
                  >
                    Enter
                  </Button>

                  <Popconfirm
                    title="Confirm deletion of this workflow evaluation task?"
                    okText="Delete"
                    cancelText="Cancel"
                    onConfirm={() => runDeleteEvaluate(String(item.workflow_id))}
                  >
                    <Button
                      type="text"
                      danger
                      icon={<DeleteOutlined />}
                      loading={deleteLoading}
                    />
                  </Popconfirm>
                </div>
              </div>
            </List.Item>
          )}
        />
      </Card>
    </div>
  );
};

export default WorkflowEvaluateManage;