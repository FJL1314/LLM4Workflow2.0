
export interface RequestData<T> {
  code: number;
  data: T;
  msg?: string;
}

export interface WorkflowInfoPayload {
  id: string;
  uid?: number;
  session_id?: string;
  describe?: string;
  extracted_task?: string;
  rewrite_queries?: string[];
  api_list?: any[];
  dag?: string;
  xml?: string;
}

export interface PromptInfo {
  [key: string]: string;
}

export interface PromptParamsResponse {
  k?: number;
  text: string;
}

export interface EmbeddingType {
  page_content: string;
  metadata: {
    source: string;
    seq_num: number;
  };
  type: string;
}

export interface RetrievedDocs {
  [key: string]: {
    doc: EmbeddingType[];
    score: number;
  }[];
}

export type CollectionType = {
  key?: string;
  collection_name: string;
  collection_describe?: string;
  create_time: string;
  file?: FormData;
};

export type WorkflowType = {
  id: number;
  session_id: string;
  message: string;
};
