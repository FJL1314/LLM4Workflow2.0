
import { Breadcrumb, Button, Card, Input } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { FC, useEffect, useState } from 'react';
import RewriteQuery, { SetValueParams } from './RewriteQuery';
import {
  addWorkflow,
  create_game_chain,
  getPromptInfo,
  getWorkflowInfoById,
  saveWorkflowRubic,
  updateWorkflow,
  write_dag_chain,
  write_xml_chain,
} from '@/api/api';
import { useNavigate, useParams } from 'react-router-dom';

import { EventEmitter } from 'ahooks/lib/useEventEmitter';
import FlowChart from '../components/FlowGraph/FlowChart';
import MarkdownRenderer from '../components/MarkdownRender';
import RetrieveApi from './Retrieve';
import { useRequest } from 'ahooks';
import { v4 as uuidv4 } from 'uuid';
type StepSectionProps = {
  title: string;
  description: string;
  buttonText: string;
  loading?: boolean;
  onClick?: () => void;
  children?: React.ReactNode;
};

const StepSection: FC<StepSectionProps> = ({
  title,
  description,
  buttonText,
  loading = false,
  onClick,
  children,
}) => {
  return (
    <div className="mb-4 rounded-xl border border-gray-200 bg-white shadow-sm">

      <div className="flex items-center justify-between px-4 py-3">
        <div className="text-[15px] font-semibold text-gray-800">{title}</div>
        <Button type="primary" loading={loading} onClick={onClick}>
          {buttonText}
        </Button>
      </div>


      <div className="px-4 pb-3 text-sm text-gray-400">{description}</div>


      <div className="border-t border-gray-100" />

      <div className="p-4">{children}</div>
    </div>
  );
};

const Workflow: FC<{ refresh$: EventEmitter<void> }> = function (props) {
  const { workflowId } = useParams();
  // const { workflowId } = useParams();
  const navigate = useNavigate();
  const pageTitle = workflowId
  ? `Workflow${workflowId}`
  : 'Create a new workflow';
  const [text, setText] = useState('workflow: ');
  // 'workflow:The web service workflow passes the gene sequence name(i.e., the gene accession number) to invoke a genomics data web service. If the call is successful, the results will be displayed in three different ways: one is to display the gene sequence in XML format (the default return format of the service), another is to display the sequence of elements extracted from XML, and the last one is to display an HTML document converted from XML. If the call fails, the error message returned by the service will be displayed.'

  const [loading1, setLoading1] = useState(false);
  const [loading2, setLoading2] = useState(false);
  const [loading5, setLoading5] = useState(false);
  const [loading6, setLoading6] = useState(false);
  // const [isCollapsed, setIsCollapsed] = useState(true);

  const { data: promptData, mutate } = useRequest(getPromptInfo, {
    onSuccess: (res) => {
      if (res.code === 200) {
        mutate((oldData) => {
          return {
            ...oldData,
            data: Object.fromEntries(
              Object.entries(oldData.data).map(([key, value]) => [
                key,
                value.replace(/\{\{/g, '{').replace(/\}\}/g, '}'),
              ])
            ),
          };
        });
      }
    },
  });

  const {
    refresh,
    run,
    data: workflowInfo,
  } = useRequest(getWorkflowInfoById, {
    defaultParams: [workflowId as string],
    manual: true,
    onSuccess: (res) => {
      if (res.code === 200) {
        setText(res.data?.describe || 'workflow:');
      }
    },
  });

  useEffect(() => {
    if (workflowId) {
      run(workflowId);
    }
  }, [workflowId, run]);

  const { run: update } = useRequest(updateWorkflow, {
    defaultParams: [{ id: workflowId as string }],
    manual: true,
    onSuccess: () => refresh(),
  });

  /**
   * @description: create a new workflow and refresh the workflow list
   * @return {*}
   */
  const handleStep1 = async () => {
    try {
      const session_id = uuidv4().toString();
      const { code, data } = await addWorkflow(session_id);
      if (code === 200) {
        navigate(`/workflow/${data.id}`);
        props.refresh$.emit();
        await createGame(session_id);
      }
    } catch (e) {
      console.log('addWorkflow error:', e);
    }
  };

  const createGame = async (session_id: string) => {
    try {
      setLoading1(true);
      await create_game_chain.invoke(
        { input: '' },
        { configurable: { session_id } }
      );
      refresh();
    } catch (e) {
      console.log('createGame error:', e);
    } finally {
      setLoading1(false);
    }
  };

  const handleStep2 = async () => {
    try {
      setLoading2(true);
      const res = await create_game_chain.invoke(
        { input: text },
        { configurable: { session_id: workflowInfo?.data.session_id } }
      );
      setLoading2(false);
      update({
        id: workflowId as string,
        describe: text,
        extracted_task: res as string,
      });
    } catch (e) {
      setLoading2(false);
      console.log('extractTask error:', e);
    }
  };

  const handleStep3 = async ({
    extracted_task,
    rewrite_queries,
  }: SetValueParams) => {
    try {

      await update({
        id: workflowId as string,
        extracted_task,
        rewrite_queries,
      });

    } catch (e) {
    }
  };

  const handleWriteDag = async () => {
    try {
      setLoading5(true);
      const res = await write_dag_chain.invoke(
        {
          text: workflowInfo?.data?.describe,
          task_list: workflowInfo?.data.extracted_task,
          api_list: JSON.stringify(
            workflowInfo?.data.api_list
              ?.filter((item) => item.status == 1)
              .map((item) => ({
                ...item.doc,
              }))
          ),
        },
        { configurable: { session_id: workflowInfo?.data.session_id } }
      );
      update({
        id: workflowId as string,
        dag: res as string,
      });
      setLoading5(false);
    } catch (e) {
      setLoading5(false);
      console.log('writeDag error:', e);
    }
  };

  const handleWriteXML = async () => {
    try {
      setLoading6(true);

      const res = await write_xml_chain.invoke({
        dag: workflowInfo?.data?.dag,
      });

      await update({
        id: workflowId as string,
        xml: res as string,
      });

      // await saveWorkflowRubic(workflowId as string);

      refresh();
    } catch (e) {
      console.log('WriteXML error:', e);
    } finally {
      setLoading6(false);
    }
  };

  return (
    <div className="workflow w-full max-w-none">
      <div className="mb-4">
        <div className="flex items-start justify-between">
          <div>
            <div className="text-[40px] leading-none font-semibold text-[#262626]">
              Workflow Generation
            </div>
            <div className="mt-3 text-[18px] text-[#8c8c8c]">
              process for workflow generation based LLM
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Button
              type="text"
              icon={<ArrowLeftOutlined style={{ fontSize: 18 }} />}
              onClick={() => navigate('/workflow-manage')}
              className="flex items-center justify-center hover:bg-gray-100"
            />
            <div className="rounded border border-[#91caff] bg-[#f0f5ff] px-3 py-1 text-[16px] text-[#1677ff]">
              Workflow ID: {workflowId || 'New'}
            </div>
          </div>
        </div>
      </div>
      <div className="mb-4 rounded-2xl bg-white px-6 py-5 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between text-gray-400 text-[16px]">
          <div className="flex items-center flex-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-500">
              1
            </div>
            <span className="ml-3">Create Game</span>
            <div className="mx-4 h-px flex-1 bg-gray-200" />
          </div>

          <div className="flex items-center flex-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-500">
              2
            </div>
            <span className="ml-3">Task Extraction</span>
            <div className="mx-4 h-px flex-1 bg-gray-200" />
          </div>

          <div className="flex items-center flex-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-500">
              3
            </div>
            <span className="ml-3">Task Rewriting</span>
            <div className="mx-4 h-px flex-1 bg-gray-200" />
          </div>

          <div className="flex items-center flex-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-500">
              4
            </div>
            <span className="ml-3">API Retrieval</span>
            <div className="mx-4 h-px flex-1 bg-gray-200" />
          </div>

          <div className="flex items-center flex-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-500">
              5
            </div>
            <span className="ml-3">DAG Generation</span>
            <div className="mx-4 h-px flex-1 bg-gray-200" />
          </div>

          <div className="flex items-center">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gray-100 text-gray-500">
              6
            </div>
            <span className="ml-3">XML Generation</span>
          </div>
        </div>
      </div>
      {/* Stage 1: Create Game */}
      <StepSection
        title="Stage 1: Create Game"
        description="Initialize the workflow session for this task."
        buttonText="Create Game"
        loading={loading1}
        onClick={handleStep1}
      >
        <div className="rounded-lg border border-gray-100 bg-gray-50 p-4">
          <div className="mb-3 text-sm font-medium text-gray-700">Prompt</div>
          <div className="text-sm text-gray-600 whitespace-pre-wrap">
            {promptData?.data?.['create_game_prompt'] || 'No prompt available.'}
          </div>

          <div className="mt-4 rounded-md bg-white px-3 py-2 text-sm text-gray-600 border border-gray-200">
            Status: {workflowInfo && !loading1 ? 'OK' : 'Not generated'}
          </div>
        </div>
      </StepSection>
      {/* Stage 2: Task Extraction */}
      <StepSection
        title="Stage 2: Task Extraction"
        description="Extract the executable task description from the user request."
        buttonText="Generate Task"
        loading={loading2}
        onClick={handleStep2}
      >
        <div className="space-y-4">
          <div>
            <div className="mb-2 text-sm font-medium text-gray-700">User Input</div>
            <Input.TextArea
              styles={{
                textarea: {
                  fontSize: 16,
                },
              }}
              value={text}
              autoSize={{ minRows: 4, maxRows: 8 }}
              onChange={(e) => setText(e.target.value)}
            />
          </div>

          <div>
            <div className="mb-2 text-sm font-medium text-gray-700">
              Extracted Task
            </div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700 whitespace-pre-wrap">
              {workflowInfo?.data?.extracted_task || 'No extracted task yet.'}
            </div>
          </div>
        </div>
      </StepSection>
      {/* Stage 3: Rewrite Task */}
      <RewriteQuery
        prompt={promptData?.data?.['rewrite_query_prompt']}
        setValue={handleStep3}
      />
      {/* Stage 4：Retrieve task apis */}
      <RetrieveApi
        query_list={workflowInfo?.data?.rewrite_queries}
        api_list={workflowInfo?.data?.api_list}
        update={update}
      />
      {/* Stage 5：Write dag */}
      <StepSection
        title="Stage 5: Workflow DAG Generation"
        description="Generate the workflow DAG based on the selected APIs and extracted tasks."
        buttonText="Generate DAG"
        loading={loading5}
        onClick={handleWriteDag}
      >
        <div className="space-y-4">
          <div>
            <div className="mb-2 text-sm font-medium text-gray-700">Prompt</div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700 whitespace-pre-wrap">
              {promptData?.data?.['write_dag_prompt'] || 'No prompt available.'}
            </div>
          </div>

          <div>
            <div className="mb-2 text-sm font-medium text-gray-700">DAG Result</div>
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              {workflowInfo?.data?.dag ? (
                <MarkdownRenderer markdown={workflowInfo?.data?.dag} />
              ) : (
                <div className="text-sm text-gray-400">No DAG generated yet.</div>
              )}
            </div>
          </div>
        </div>
      </StepSection>
      {/* Stage 6：flow xml */}
      <StepSection
        title="Stage 6: Workflow Model Generation"
        description="Convert the generated DAG into executable XML workflow format."
        buttonText="Generate XML"
        loading={loading6}
        onClick={handleWriteXML}
      >
        <div className="space-y-4">
          <div>
            <div className="mb-2 text-sm font-medium text-gray-700">Prompt</div>
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-sm text-gray-700 whitespace-pre-wrap">
              {promptData?.data?.['write_xml_prompt'] || 'No prompt available.'}
            </div>
          </div>

          {workflowInfo?.data?.xml && (
            <div>
              <div className="mb-2 text-sm font-medium text-gray-700">Flow Preview</div>
              <div className="rounded-lg border border-gray-200 bg-[#f8fafc] p-4">
                <FlowChart
                  width={'80%'}
                  height={150}
                  xmlData={workflowInfo?.data?.xml}
                />
              </div>
            </div>
          )}

          <div>
            <div className="mb-2 text-sm font-medium text-gray-700">XML Result</div>
            <div className="rounded-lg border border-gray-200 bg-white p-4">
              {workflowInfo?.data?.xml ? (
                <MarkdownRenderer markdown={workflowInfo?.data?.xml} />
              ) : (
                <div className="text-sm text-gray-400">No XML generated yet.</div>
              )}
            </div>
          </div>
        </div>
      </StepSection>
    </div>
  );
};

export default Workflow;
