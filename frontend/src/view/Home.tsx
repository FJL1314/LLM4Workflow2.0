
import { Layout, theme } from 'antd';
import { Route, Routes, useNavigate } from 'react-router-dom';

import ExternalLinkIcon from '@/assets/external-link.svg?react';
import Logo from '@/assets/logo.svg?react';
import ReadmeViewer from './components/MarkDownViewer/MardkDownViewer';
import Setting from './setting/Setting';
import { UserOutlined } from '@ant-design/icons';
import Workflow from './workflow/Workflow';
import { useEventEmitter } from 'ahooks';
import KnowledgeBase from './knowledgeBase/KnowledgeBase';
import WorkflowManage from './workflowManage/WorkflowManage';
import Evaluation from './evaluation/Evaluation';
import EvaluationDetail from './evaluation/EvaluationDetail';
import WorkflowEvaluateManage from './evaluation/WorkflowEvaluateManage';
import WorkflowEvaluate from './evaluation/WorkflowEvaluate';

const { Header, Content } = Layout;

function Home() {
  const {
    token: { colorPrimary, borderRadiusLG },
  } = theme.useToken();

  const refresh$ = useEventEmitter();
  const navigate = useNavigate();

  return (
    <Layout className="min-h-screen">
      <Header
        className="shadow flex items-center justify-between px-4 bg-white"
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 100,
          width: '100%',
        }}
      >
        <div className="flex items-center">
          <div
            className="font-bold text-2xl cursor-pointer flex items-center"
            onClick={() => navigate('/')}
          >
            <Logo style={{ width: 40, height: 40 }} />
            <span className="ml-2">LLM4Workflow2.0</span>
          </div>

          <a
            target="blank"
            href="https://github.com/ISEC-AHU/EdgeWorkflow"
            className="ml-12 flex items-center"
          >
            <span className="mr-1">EdgeWorkflow</span>
            <ExternalLinkIcon
              style={{ '--hover-color': colorPrimary } as React.CSSProperties}
            />
          </a>
        </div>

        <div className="flex items-center">
          <UserOutlined className="cursor-pointer" style={{ fontSize: 20 }} />
        </div>
      </Header>

      <Content style={{ background: '#f5f7fa' }}>
        <div className="flex w-full">
          <div
            className="w-[290px] shrink-0 bg-white border-r shadow-sm overflow-y-auto"
            style={{
              height: 'calc(100vh - 64px)',
              position: 'sticky',
              top: 64,
            }}
          >
            <Setting refresh$={refresh$} />
          </div>

            <div
              className="flex-1 box-border"
              style={{
                minHeight: 'calc(100vh - 64px)',
              }}
            >
              <div className="w-full px-6">
              <Routes>
                <Route path="/" element={<ReadmeViewer />} />
                <Route path="knowledge-base" element={<KnowledgeBase />} />
                <Route path="workflow-manage" element={<WorkflowManage />} />
                <Route
                  path="workflow/:workflowId"
                  element={<Workflow refresh$={refresh$} />}
                />
                <Route
                  path="workflow/add"
                  element={<Workflow refresh$={refresh$} />}
                />
                <Route path="evaluation" element={<Evaluation />} />
                <Route path="evaluation/:id" element={<EvaluationDetail />} />
                <Route
                  path="workflow-evaluate-manage"
                  element={<WorkflowEvaluateManage />}
                />
                <Route
                  path="workflow-evaluate/add"
                  element={<WorkflowEvaluate />}
                />
                <Route
                  path="workflow-evaluate/:workflowId"
                  element={<WorkflowEvaluate />}
                />
              </Routes>
            </div>
          </div>
        </div>
      </Content>
    </Layout>
  );
}

export default Home;