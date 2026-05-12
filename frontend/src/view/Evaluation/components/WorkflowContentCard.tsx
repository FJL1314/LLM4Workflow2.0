import { Button, Card, Input, Typography } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import React from 'react';

const { Text } = Typography;
const { TextArea } = Input;

interface Props {
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  taskInput: string;
  userRequestInput: string;
  onTaskChange: (value: string) => void;
  onUserRequestChange: (value: string) => void;
  onUploadClick: () => void;
  onFileChange: (event: React.ChangeEvent<HTMLInputElement>) => void;
}

export default function WorkflowContentCard({
  fileInputRef,
  taskInput,
  userRequestInput,
  onTaskChange,
  onUserRequestChange,
  onUploadClick,
  onFileChange,
}: Props) {
  return (
    <Card
      className="h-full rounded-2xl shadow-sm"
      title={
        <div className="flex w-full items-center justify-between">
          <span>Workflow Content</span>
          <Button icon={<UploadOutlined />} onClick={onUploadClick}>
            Upload JSON
          </Button>
        </div>
      }
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".json,application/json"
        style={{ display: 'none' }}
        onChange={onFileChange}
      />

      <div className="space-y-4">
        <div>
          <Text strong>Task / Workflow Content</Text>
          <TextArea
            value={taskInput}
            onChange={(e) => onTaskChange(e.target.value)}
            autoSize={{ minRows: 10, maxRows: 20 }}
            className="mt-2"
            placeholder="Input workflow task JSON or plain text"
          />
        </div>

        <div>
          <Text strong>User Request</Text>
          <TextArea
            value={userRequestInput}
            onChange={(e) => onUserRequestChange(e.target.value)}
            autoSize={{ minRows: 4, maxRows: 8 }}
            className="mt-2"
            placeholder="User request will be auto parsed from task JSON"
          />
        </div>
      </div>
    </Card>
  );
}