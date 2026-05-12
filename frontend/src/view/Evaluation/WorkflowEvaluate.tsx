import { Button, Card, Col, Divider, message, Row, Space, Spin, Steps, Tag, Typography } from 'antd';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { unwrapApiResponse } from '@/utils/apiHelper';
import {
  generateDraftRubric,
  generateFinalRubric,
  generateReport,
  generateSimulationResults,
  generategenericRubric,
  getWorkflowEvaluateDetail,
  updateWorkflowEvaluate,
} from '@/api/api';

import type { DagData, EvaluateRecord, SimulationResults } from './types';
import { extractTaskInfo, prettyJson } from './utils';
import WorkflowContentCard from './components/WorkflowContentCard';
import DagPreviewCard from './components/DagPreviewCard';
import RubricDimensionList from './components/RubricDimensionList';
import SimulationResultsCard from './components/SimulationResultsCard';
import ReportCard from './components/ReportCard';

const { Title, Text } = Typography;

export default function WorkflowEvaluate() {
  const params = useParams();
  const detailId =
    params.id || (params as any).workflow_id || (params as any).workflowId || '';

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [pageLoading, setPageLoading] = useState(false);
  const [evaluateRecord, setEvaluateRecord] = useState<EvaluateRecord | null>(null);

  const [taskInput, setTaskInput] = useState('');
  const [userRequestInput, setUserRequestInput] = useState('');

  const [parsedTaskObject, setParsedTaskObject] = useState<any>(null);
  const [parsedDagData, setParsedDagData] = useState<DagData | null>(null);
  const [parsedWorkflowId, setParsedWorkflowId] = useState('');

  const [loadinggenericRubric, setLoadinggenericRubric] = useState(false);
  const [loadingDraftRubric, setLoadingDraftRubric] = useState(false);
  const [loadingReport, setLoadingReport] = useState(false);
  const [simulationLoading, setSimulationLoading] = useState(false);

  const [genericRubric, setgenericRubric] = useState<any[]>([]);
  const [draftRubric, setDraftRubric] = useState<any[]>([]);
  const [report, setReport] = useState<any>(null);
  const [simulationResults, setSimulationResults] = useState<SimulationResults | null>(null);

  const [selectedgenericRubric, setSelectedgenericRubric] = useState<any[]>([]);
  const [selectedDraftRubric, setSelectedDraftRubric] = useState<any[]>([]);

  const [loadingFinalRubric, setLoadingFinalRubric] = useState(false);
  const [finalRubric, setFinalRubric] = useState<any[]>([]);
  const [selectedFinalRubric, setSelectedFinalRubric] = useState<any[]>([]);

  const finalWorkflowId = parsedWorkflowId || String(evaluateRecord?.workflow_id || '');

  const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

  useEffect(() => {
    if (!detailId) return;
    initPage();
  }, [detailId]);

  useEffect(() => {
    if (!finalWorkflowId) return;

    const timer = setTimeout(async () => {
      try {
        await updateWorkflowEvaluate({
          workflow_id: finalWorkflowId,
          task: taskInput,
          user_request: userRequestInput,
        });
      } catch (error) {
        console.error('error:', error);
      }
    }, 600);

    return () => clearTimeout(timer);
  }, [taskInput, userRequestInput, finalWorkflowId]);

  useEffect(() => {
    if (!taskInput?.trim()) {
      setParsedTaskObject(null);
      setParsedDagData(null);
      setUserRequestInput('');
      setParsedWorkflowId('');
      return;
    }

    const { parsedTask, userRequest, dagData, workflowId } = extractTaskInfo(taskInput);

    if (parsedTask && typeof parsedTask === 'object') {
      setParsedTaskObject(parsedTask);
      setParsedDagData(dagData);
      if (userRequest && !userRequestInput) {
        setUserRequestInput(userRequest);
      }
      setParsedWorkflowId(workflowId || '');
    } else {
      setParsedTaskObject(null);
      setParsedDagData(null);
      setParsedWorkflowId('');
    }
  }, [taskInput]);

  const initPage = async () => {
    try {
      setPageLoading(true);

      const res = await getWorkflowEvaluateDetail({ workflow_id: detailId });
      const evalRes = (res as any)?.data?.data ?? (res as any)?.data ?? res;

      if (!evalRes) {
        message.warning('No workflow evaluation detail found.');
        return;
      }

      setEvaluateRecord(evalRes);

      const taskValue = evalRes?.task ?? '';
      setTaskInput(typeof taskValue === 'string' ? taskValue : prettyJson(taskValue));

      const initgeneric = evalRes?.generic_rubric ?? evalRes?.univeral_rubric ?? [];
      const initDraft = evalRes?.draft_rubric ?? [];
      const initFinal = evalRes?.final_rubric ?? [];

      setgenericRubric(Array.isArray(initgeneric) ? initgeneric : []);
      setDraftRubric(Array.isArray(initDraft) ? initDraft : []);
      setSelectedgenericRubric(Array.isArray(initgeneric) ? initgeneric : []);
      setSelectedDraftRubric(Array.isArray(initDraft) ? initDraft : []);
      setReport(evalRes?.report ?? null);
      setSimulationResults(evalRes?.sim_results ?? null);
      setFinalRubric(Array.isArray(initFinal) ? initFinal : []);
      setSelectedFinalRubric(Array.isArray(initFinal) ? initFinal : []);
    } catch (error) {
      console.error('initPage error =', error);
      message.error('Failed to load workflow evaluation detail.');
    } finally {
      setPageLoading(false);
    }
  };

  const currentTask = useMemo(() => {
    if (parsedTaskObject) return parsedTaskObject;
    try {
      return JSON.parse(taskInput);
    } catch {
      return taskInput;
    }
  }, [taskInput, parsedTaskObject]);

  const dagData = useMemo(() => parsedDagData, [parsedDagData]);

  const filteredDraftRubric = useMemo(() => {
    if (!Array.isArray(draftRubric)) return [];
    const genericThemeSet = new Set(
      (Array.isArray(genericRubric) ? genericRubric : [])
        .map((item: any) => item?.theme)
        .filter(Boolean)
    );

    return draftRubric.filter(
      (item: any) => item?.theme && !genericThemeSet.has(item.theme)
    );
  }, [draftRubric, genericRubric]);

  const handleToggleRubric = (
    type: "generic" | "draft" | "final",
    item: any,
    checked: boolean
  ) => {
    if (type === "generic") {
      setSelectedgenericRubric((prev) => {
        if (checked) {
          if (prev.some((x) => x.theme === item.theme)) return prev;
          return [...prev, item];
        }
        return prev.filter((x) => x.theme !== item.theme);
      });
    } else if (type === "final") {
      setSelectedFinalRubric((prev) => {
        if (checked) {
          if (prev.some((x) => x.theme === item.theme)) return prev;
          return [...prev, item];
        }
        return prev.filter((x) => x.theme !== item.theme);
      });
    } else {
      console.warn("Draft rubric toggle ignored");
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const isJson =
      file.type === 'application/json' || file.name.toLowerCase().endsWith('.json');

    if (!isJson) {
      message.warning('Please upload a JSON file.');
      event.target.value = '';
      return;
    }

    try {
      const text = await file.text();

      try {
        JSON.parse(text);
      } catch {
        message.error('The uploaded file is not valid JSON.');
        event.target.value = '';
        return;
      }

      setTaskInput(prettyJson(text));
      message.success('JSON file uploaded successfully.');
    } catch (error) {
      console.error(error);
      message.error('Failed to read the uploaded file.');
    } finally {
      event.target.value = '';
    }
  };

  const handleGenerategenericRubric = async () => {
    const start = Date.now();

    if (!finalWorkflowId) {
      message.warning('workflow_id is missing.');
      return;
    }
    if (!currentTask) {
      message.warning('task is empty.');
      return;
    }

    try {
      setLoadinggenericRubric(true);

      const res = await generategenericRubric({
        workflow_id: finalWorkflowId,
        task: currentTask,
      });

      const duration = Date.now() - start;
      if (duration < 2500) await sleep(2500 - duration);

      const data = (res as any)?.data ?? res;
      const genericDimensions = data?.generic_rubric ?? data?.data?.generic_rubric ?? [];

      if ((res as any)?.code === 200 || genericDimensions.length > 0) {
        setgenericRubric(genericDimensions);
        setSelectedgenericRubric(genericDimensions);
        message.success('generic rubric generated successfully');
      } else {
        message.error((res as any)?.msg || 'Failed to generate generic rubric');
      }
    } catch (e) {
      console.error(e);
      message.error('Failed to generate generic rubric');
    } finally {
      setLoadinggenericRubric(false);
    }
  };

  const handleGenerateDraftRubric = async () => {
    const start = Date.now();

    if (!finalWorkflowId) {
      message.warning('workflow_id is missing.');
      return;
    }
    if (!currentTask) {
      message.warning('task is empty.');
      return;
    }

    try {
      setLoadingDraftRubric(true);

      const res = await generateDraftRubric({
        workflow_id: finalWorkflowId,
        task: currentTask,
      });
      const duration = Date.now() - start;
      if (duration < 3500) await sleep(3500 - duration);

      const draftDimensions = res?.data?.dimensions ?? [];
      setDraftRubric(draftDimensions);
      setSelectedDraftRubric(draftDimensions);
      message.success('Draft Rubric generated successfully.');
    } catch (error: any) {
      console.error(error);
      message.error('Failed to generate task-specific Rubric.');
    } finally {
      setLoadingDraftRubric(false);
    }
  };

  const handleGenerateSimulationResults = async () => {
    if (!finalWorkflowId) {
      message.warning('workflow_id is missing.');
      return;
    }
    if (!currentTask) {
      message.warning('task is empty.');
      return;
    }

    try {
      setSimulationLoading(true);

      const res = await generateSimulationResults({
        workflow_id: finalWorkflowId,
        task: currentTask,
      });

      const parsed = unwrapApiResponse<any>(res);
      const simResults =
        parsed?.data?.sim_results ??
        parsed?.raw?.data?.sim_results ??
        parsed?.raw?.sim_results ??
        null;

      if (parsed.code === 200 && simResults) {
        setSimulationResults(simResults);
        message.success('Simulation results generated successfully');
        return;
      }

      message.error(parsed.msg || 'Failed to generate simulation results');
    } catch (error: any) {
      console.error(error);
      message.error(
        error?.response?.data?.msg ||
          error?.response?.data?.detail ||
          error?.message ||
          'Failed to generate simulation results'
      );
    } finally {
      setSimulationLoading(false);
    }
  };
  const handleGenerateFinalRubric = async () => {
    if (!finalWorkflowId) {
      message.warning('workflow_id is missing.');
      return;
    }

    if (!currentTask) {
      message.warning('task is empty.');
      return;
    }

    if (!Array.isArray(draftRubric) || draftRubric.length === 0) {
      message.warning('Please generate draft rubric first.');
      return;
    }

    if (!simulationResults) {
      message.warning('Please generate simulation results first.');
      return;
    }

    try {
      setLoadingFinalRubric(true);
      console.log('draftRubric before final request =', draftRubric);

      const res = await generateFinalRubric({
        workflow_id: finalWorkflowId,
        task: currentTask,
        draft_rubric: draftRubric,
        sim_results: simulationResults,
      });

      const parsed = unwrapApiResponse<any>(res);
      console.log('final rubric parsed =', parsed);

      const finalRubricData =
        parsed?.data?.final_rubric ??
        parsed?.raw?.data?.final_rubric ??
        parsed?.raw?.final_rubric ??
        [];

      if (parsed.code === 200 && Array.isArray(finalRubricData)) {
        setFinalRubric(finalRubricData);
        setSelectedFinalRubric(finalRubricData);
        message.success('Final task-specific rubric generated successfully');
        return;
      }

      message.error(parsed.msg || 'Failed to generate final task-specific rubric');
    } catch (error: any) {
      console.error('generate final rubric error ->', error);
      message.error(
        error?.response?.data?.msg ||
          error?.response?.data?.detail ||
          error?.message ||
          'Failed to generate final task-specific rubric'
      );
    } finally {
      setLoadingFinalRubric(false);
    }
  };

  const handleGenerateReport = async () => {
    const start = Date.now();

    if (!finalWorkflowId) {
      message.warning('workflow_id is missing.');
      return;
    }
    if (!currentTask) {
      message.warning('task is empty.');
      return;
    }
    if (selectedgenericRubric.length === 0 && selectedFinalRubric.length === 0) {
      message.warning('Please select at least one rubric dimension.');
      return;
    }

    try {
      setLoadingReport(true);
      

      const res = await generateReport({
        workflow_id: finalWorkflowId,
        task: currentTask,
        generic_rubric: selectedgenericRubric,
        final_rubric: selectedFinalRubric,
      });

      const duration = Date.now() - start;
      if (duration < 7800) await sleep(7800 - duration);

      const reportData = (res as any)?.data ?? null;

      if ((res as any)?.code !== 200 || !reportData) {
        message.error((res as any)?.msg || 'Failed to generate Report.');
        return;
      }

      setReport(reportData);
      message.success('Report generated successfully.');
    } catch (error) {
      console.error(error);
      message.error('Failed to generate Report.');
    } finally {
      setLoadingReport(false);
    }
  };

  const stepItems = [
    { title: 'generic Rubric Generation' },
    { title: 'Task-Specific Rubric Drafting' },
    { title: 'Multi-Agent Discrepancy Analysis' },
    { title: 'Task-Specific Rubric Refinement' },
    { title: 'Evaluation Result Generation' },
  ];

  return (
    <div className="min-h-screen bg-[#f5f7fb] p-6">
      <Spin spinning={pageLoading}>
        <div className="mb-6 flex items-center justify-between">
          <div>
            <Title level={3} className="!mb-1">
              Workflow Evaluation
            </Title>
            <Text type="secondary">
              Four-step evaluation process for workflow rubric, simulation, and report generation
            </Text>
          </div>

          {/* <Space>
            <Tag color="blue">
              Workflow ID: {finalWorkflowId || evaluateRecord?.workflow_id || '-'}
            </Tag>
          </Space> */}
        </div>

        <Card className="mb-6 rounded-2xl shadow-sm">
          <Steps items={stepItems} current={-1} />
        </Card>

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <WorkflowContentCard
              fileInputRef={fileInputRef}
              taskInput={taskInput}
              userRequestInput={userRequestInput}
              onTaskChange={setTaskInput}
              onUserRequestChange={setUserRequestInput}
              onUploadClick={handleUploadClick}
              onFileChange={handleFileChange}
            />
          </Col>

          <Col xs={24} lg={12}>
            <DagPreviewCard dagData={dagData} />
          </Col>
        </Row>

        <div className="mt-6 space-y-6">
          <Card
            title="Stage 1: generic Rubric Generation"
            className="rounded-2xl shadow-sm"
            extra={
              <Button
                type="primary"
                loading={loadinggenericRubric}
                onClick={handleGenerategenericRubric}
              >
                Generate generic Rubric
              </Button>
            }
          >
            <div className="flex items-center justify-between">
              <Text type="secondary">Generate the generic rubric for this workflow task.</Text>
              <Text type="secondary">Selected: {selectedgenericRubric.length}</Text>
            </div>

            <Divider />

            <RubricDimensionList
              dimensions={genericRubric}
              type="generic"
              selectedItems={selectedgenericRubric}
              onToggle={handleToggleRubric}
            />
          </Card>

          <Card
            title="Stage 2: Task-Specific Rubric Drafting"
            className="rounded-2xl shadow-sm"
            extra={
              <Button
                type="primary"
                loading={loadingDraftRubric}
                onClick={handleGenerateDraftRubric}
              >
                Generate Draft Task-specific Rubric
              </Button>
            }
          >
            <div className="flex items-center justify-between">
              <Text type="secondary">Generate the draft task-specific rubric for this workflow task.</Text>
              <Text type="secondary">Selected: {selectedDraftRubric.length}</Text>
            </div>

            <Divider />

            <RubricDimensionList
              dimensions={filteredDraftRubric}
              type="draft"
              selectedItems={selectedDraftRubric}
              onToggle={handleToggleRubric}
            />
          </Card>

          <SimulationResultsCard
            loading={simulationLoading}
            simulationResults={simulationResults}
            onGenerate={handleGenerateSimulationResults}
          />
          <Card
            title="Stage 4: Task-Specific Rubric Refinement"
            className="rounded-2xl shadow-sm"
            extra={
              <Button
                type="primary"
                loading={loadingFinalRubric}
                onClick={handleGenerateFinalRubric}
              >
                Refinement Task-specific Rubric
              </Button>
            }
          >
            <div className="flex items-center justify-between">
              <Text type="secondary">
                Refine the draft rubric using multi-agent discrepancy analysis report.
              </Text>
              <Text type="secondary">
                Selected: {selectedFinalRubric.length}
              </Text>
            </div>

            <Divider />

            <RubricDimensionList
              dimensions={finalRubric}
              type="final"
              selectedItems={selectedFinalRubric}
              onToggle={handleToggleRubric}
            />
          </Card>      
          <ReportCard
            loading={loadingReport}
            report={report}
            selectedCount={selectedgenericRubric.length + selectedFinalRubric.length}
            onGenerate={handleGenerateReport}
          />
        </div>
      </Spin>
    </div>
  );
}