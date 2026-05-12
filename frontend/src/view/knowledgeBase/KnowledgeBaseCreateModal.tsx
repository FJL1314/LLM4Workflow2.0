import React from 'react';
import { Button, Form, Input, Modal, Upload, message } from 'antd';
import { UploadOutlined } from '@ant-design/icons';
import { createCollection } from '@/api/api';

interface Props {
  open: boolean;
  onCancel: () => void;
  onSuccess: () => void;
}

interface FormValues {
  name: string;
  description?: string;
  file: any[];
}

const KnowledgeBaseCreateModal: React.FC<Props> = ({
  open,
  onCancel,
  onSuccess,
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = React.useState(false);

  const handleFinish = async (values: FormValues) => {
    try {
      const formData = new FormData();
      formData.append('collection_name', values.name);
      formData.append('collection_describe', values.description || '');
      formData.append('create_time', Date.now().toString());

      if (values.file?.[0]?.originFileObj) {
        formData.append('file', values.file[0].originFileObj);
      }

      setLoading(true);
      const res = await createCollection(formData);

      if (res.code === 200) {
        message.success(res.msg || 'Creation successful');
        form.resetFields();
        onSuccess();
      } else {
        message.error(res.msg || 'Creation failed');
      }
    } catch (error) {
      message.error('Creation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title="Create a new knowledge base"
      open={open}
      onCancel={onCancel}
      footer={null}
      destroyOnClose
      maskClosable={false}
      width={680}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleFinish}
        autoComplete="off"
      >
        <Form.Item
          label="Knowledge base name"
          name="name"
          rules={[{ required: true, message: 'Please enter the knowledge base name.' }]}
        >
          <Input placeholder="Please enter the knowledge base name." />
        </Form.Item>

        <Form.Item label="Knowledge base description" name="description">
          <Input.TextArea
            rows={4}
            placeholder="Please enter a description of the knowledge base."
          />
        </Form.Item>

        <Form.Item
          label="Upload tool/API description document"
          name="file"
          valuePropName="fileList"
          getValueFromEvent={(e) => e?.fileList}
          rules={[{ required: true, message: 'Please upload the file.' }]}
        >
          <Upload
            name="file"
            accept=".json,.csv,.pdf,application/json,text/csv,application/pdf"
            multiple={false}
            maxCount={1}
            beforeUpload={() => false}
          >
            <Button icon={<UploadOutlined />}>Select file</Button>
          </Upload>
        </Form.Item>

        <div className="text-gray-400 text-sm mb-4">
          It supports uploading tools or API description documents, 
          which the system will use for subsequent parsing, segmentation, and vectorized storage.
        </div>

        <div className="flex justify-end gap-3">
          <Button onClick={onCancel}>Cancel</Button>
          <Button type="primary" htmlType="submit" loading={loading}>
            Create
          </Button>
        </div>
      </Form>
    </Modal>
  );
};

export default KnowledgeBaseCreateModal;