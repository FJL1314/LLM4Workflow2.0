export interface TaskNode {
  id?: string;
  name?: string;
  label?: string;
  task?: string;
  description?: string;
  arguments?: any[];
  [key: string]: any;
}

export interface TaskLink {
  source: string;
  target: string;
  [key: string]: any;
}

export interface DagData {
  task_nodes: TaskNode[];
  task_links: TaskLink[];
  [key: string]: any;
}

export interface EvaluateRecord {
  id?: string;
  uid?: string;
  workflow_id?: string;
  task?: any;
  generic_rubric?: any;
  univeral_rubric?: any;
  draft_rubric?: any;
  sim_results?: any;
  report?: any;
  final_rubric?: any;
  create_time?: string;
  update_time?: string;
  [key: string]: any;
}

export interface SimulationResults {
  task_id?: string;
  step_scores: Record<string, Record<string, number>>;
  discriminatory_power: Record<string, number>;
  high_discrimination_steps: string[];
  low_discrimination_steps: string[];
  model_rankings: Record<string, number>;
  summary: {
    n_models: number;
    n_steps: number;
    avg_discriminatory_power: number;
    high_discrimination_count: number;
    low_discrimination_count: number;
  };
}