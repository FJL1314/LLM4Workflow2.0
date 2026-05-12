import React from 'react';
import { Button, Card, List, Popconfirm, message } from 'antd';
import {
  PlusOutlined,
  ApartmentOutlined,
  DeleteOutlined,
} from '@ant-design/icons';
import { deleteWorkflow, getWorkflowList } from '@/api/api';
import { useNavigate } from 'react-router-dom';
import { useRequest } from 'ahooks';

const WorkflowManage: React.FC = () => {
  const navigate = useNavigate();

  const { data, loading, refresh } = useRequest(getWorkflowList);

  const { run: runDeleteWorkflow, loading: deleteLoading } = useRequest(
    async (id: string) => {
      return await deleteWorkflow(id);
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

  const workflowList = data?.data || [];

  return (
    <div className="p-6 bg-[#f5f7fa] min-h-[calc(100vh-66px)]">
      <Card className="rounded-xl shadow-sm mb-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center text-[24px] font-bold mb-2">
              <ApartmentOutlined className="mr-2" />
              Workflow Generation
            </div>
            <div className="text-gray-500">
              Used for creating, viewing and managing workflows in the system, 
              and supports accessing the workflow details page to generate workflows based on a large language model.
            </div>
          </div>

          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate('/workflow/add')}
          >
            New a workflow generation task
          </Button>
        </div>
      </Card>

      <Card
        className="rounded-xl shadow-sm"
        title={<span className="font-semibold">Workflow Generate Task List</span>}
        loading={loading}
      >
        <List
          dataSource={workflowList}
          locale={{ emptyText: 'No Generate Workflow Task available.' }}
          renderItem={(item: any) => (
            <List.Item className="hover:bg-gray-50 rounded-md px-4">
              <div className="w-full flex items-center justify-between">
                <div
                  className="cursor-pointer"
                  onClick={() => navigate(`/workflow/${item.id}`)}
                >
                  <div className="font-medium text-[16px]">
                    Workflow {item.id}
                  </div>
                  <div className="text-gray-400 text-sm mt-1">
                    Click to enter the generate workflow task details page
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    type="link"
                    onClick={() => navigate(`/workflow/${item.id}`)}
                  >
                    Enter
                  </Button>

                  <Popconfirm
                    title="Confirm deletion of this generate workflow task?"
                    okText="Delete"
                    cancelText="Cancel"
                    onConfirm={() => runDeleteWorkflow(String(item.id))}
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

export default WorkflowManage;