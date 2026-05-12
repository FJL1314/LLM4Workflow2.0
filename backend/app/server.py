import json
import tempfile
from typing import Optional
import os
from fastapi import Body, FastAPI, Request, HTTPException, Form, File, Depends, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from langserve import add_routes
from pydantic import BaseModel
from create_game import CREATE_GAME_PROMPT, create_game_chain_with_history
from custom_api import custom_api_chain
from db import Database
from rag import rewrite_query_chain, REWRITE_QUERY_PROMPT, RAG
from schema import RestfulModel, TaskInfo, PromptInfo, UpdateWorkflow, CollectionData, QueryData,WorkflowRubicSaveRequest,UniversalRubricRequest,WorkflowRubricDetailRequest
from utils import VECTOR_BASE_PATH,clean_json_markdown,transform_workflow_dag_to_rubic_task,to_serializable
from vectorStore import VectorStore
from write_dag import WRITE_DAG_PROMPT, write_dag_chain
from write_xml import write_xml_chain, WRITE_XML_PROMPT

app = FastAPI(
    title="Workflow Generator Server",
    version="2.0",
    description="A api server using Langchain's Runnable interfaces for generating workflows",
)
# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

db = Database()

@app.on_event("startup")
async def startup():
    db_config = {
        "dbname": "llm4workflow2.0",
        "user": "",
        "password": "",
        "host": "localhost",
        "port": 5432
    }
    db.connect(**db_config)


@app.on_event("shutdown")
async def shutdown():
    db.close()


@app.middleware("http")
async def add_uid_to_state(request: Request, call_next):
    request.state.uid = 1
    response = await call_next(request)
    return response


def get_uid(request: Request):
    return request.state.uid


@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


class CreateGameRequest(BaseModel):
    input: str
    session_id: str

@app.post("/workflow/create_game")
async def create_game(req: CreateGameRequest):
    result = create_game_chain_with_history.invoke(
        {"input": req.input},
        config={"configurable": {"session_id": req.session_id}}
    )
    return RestfulModel(data=result)


from pydantic import BaseModel
from typing import Any, Dict

class InvokeConfigurable(BaseModel):
    session_id: str

class InvokeConfig(BaseModel):
    configurable: InvokeConfigurable

class InvokeRequest(BaseModel):
    input: Dict[str, Any]
    config: InvokeConfig


@app.post("/workflow/create_game/invoke")
async def create_game_invoke(req: InvokeRequest):
    print("req.input =", req.input)
    print("req.config =", req.config.dict())
    result = create_game_chain_with_history.invoke(
        req.input,
        req.config.dict()
    )
    return {"output": result}

@app.delete("/workflow/delete")
async def delete_workflow(uid: int = Depends(get_uid), id: int = Query(..., description="The ID of the workflow")):
    try:
        query = """
            DELETE FROM workflow WHERE uid = %s AND id = %s
        """
        params = (uid, id)
        db.execute_query(query, params)
        return RestfulModel(code=200, msg="Workflow deleted successfully")
    except Exception as e:
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")

@app.post("/workflow/write_dag/invoke")
async def write_dag_invoke(req: InvokeRequest):
    try:
        cfg = req.config.dict() if req.config else None
        data = req.input or {}

        text = data.get("text", "")
        task_list = data.get("task_list", "")
        api_list = data.get("api_list", "[]")

        real_input = {
            "text": text,
            "task_list": task_list,
            "api_list": api_list,
        }

        print("write_dag real_input =", real_input)
        print("write_dag config =", cfg)

        result = write_dag_chain.invoke(real_input, config=cfg)
        print(" result =", result)
        return {"output": result}
    except Exception as e:
        print("write_dag_invoke error =", repr(e))
        raise HTTPException(status_code=500, detail=str(e))


from pydantic import BaseModel
from typing import Any, Dict, Optional
from fastapi import HTTPException

class InvokeConfigurable(BaseModel):
    session_id: Optional[str] = None

class InvokeConfig(BaseModel):
    configurable: Optional[InvokeConfigurable] = None

class InvokeRequest(BaseModel):
    input: Dict[str, Any]
    config: Optional[InvokeConfig] = None


@app.post("/workflow/write_xml/invoke")
async def write_xml_invoke(req: InvokeRequest):
    try:
        cfg = req.config.dict() if req.config else None

        print("write_xml req.input =", req.input)
        print("write_xml req.config =", cfg)

        result = write_xml_chain.invoke(
            req.input,
            config=cfg
        )
        return {"output": result}
    except Exception as e:
        print("write_xml_invoke error =", repr(e))
        raise HTTPException(status_code=500, detail=str(e))



add_routes(
    app,
    rewrite_query_chain,
    path="/workflow/rewrite_query",
)

add_routes(
    app,
    custom_api_chain,
    path="/workflow/api/custom",
)

add_routes(
    app,
    write_dag_chain,
    path="/workflow/write_dag",
)

add_routes(
    app,
    write_xml_chain,
    path="/workflow/write_xml",
)


@app.get("/workflow/list")
async def list_workflow(uid: int = Depends(get_uid)):
    try:
        query = """
            SELECT id  FROM workflow w WHERE uid = %s ORDER BY id DESC;
        """
        workflow_records = db.fetch_query(query, (uid,))
        converted_data = [{
            "id": item['id']
        } for item in workflow_records]
        return RestfulModel(data=converted_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.get("/workflow/add")
async def add_workflow(uid: int = Depends(get_uid),
                       session_id: str = Query(..., description="Session ID for create workflow message store")):
    try:
        query = """
              INSERT INTO workflow (uid, create_game_session_id)
              VALUES (%s, %s)
              """
        params = (uid, session_id,)
        db.execute_query(query, params)
        res = db.fetch_query("""
            SELECT id from workflow where uid = %s and create_game_session_id = %s ORDER BY id DESC LIMIT 1""",
                             (uid, session_id,))
        if res:
            return RestfulModel(data={"id": res[0]['id']}, msg="Workflow created successfully")
        else:
            return RestfulModel(code=-1, msg="No workflow found")
    except Exception as e:
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")


@app.post("/workflow/update")
async def update_workflow(update_data: UpdateWorkflow = Body(...)):
    # TODO: validate params
    if not update_data:
        raise HTTPException(status_code=400, detail="No update data provided")
    update_fields = update_data.dict(exclude_unset=True)
    print("update_fields:+",update_fields)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    if 'api_list' in update_fields:
        print("api_list")
        update_fields['api_list'] = json.dumps((update_fields['api_list']))

    set_clause = ", ".join([f"{field} = %({field})s" for field in update_fields])
    print("set_clause",set_clause)
    query = f"UPDATE workflow SET {set_clause} WHERE id = %(id)s"
    print("query",query)

    db.execute_query(query, update_fields)
    return {"msg": "Workflow updated successfully"}


@app.get("/workflow/info/{workflow_id}")
async def get_workflow_info(workflow_id: int = Path(..., title="The ID of the workflow")):
    try:
        query = """
               SELECT * FROM workflow w WHERE id = %s;
           """
        record = db.fetch_query(query, (workflow_id,))
        if record[0]:
            data = {
                'id': record[0]['id'],
                'session_id': record[0]['create_game_session_id'],
                'describe': record[0]['describe'],
                'extracted_task': record[0]['extracted_task'],
                'rewrite_queries': record[0]['rewrite_queries'],
                'api_list': record[0]['api_list'],
                'dag': record[0]['dag'],
                'xml': record[0]['xml']
            }
            return RestfulModel(data=data)
        else:
            return RestfulModel(code=-1, msg="No workflow found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.get("/workflow/retrieve/params/{workflow_id}")
async def get_workflow_describe(workflow_id: int = Path(..., title="The ID of the workflow")):
    try:
        query = """
        SELECT extracted_task, rewrite_queries from workflow where id=%s
        """
        print("query",query)
        res = db.fetch_query(query, (workflow_id,))
        text = res[0]['extracted_task']
        if res[0]['rewrite_queries']:
            k = len(res[0]['rewrite_queries'])
        else:
            k = len(text.split('\n'))
        if text:
            return RestfulModel[TaskInfo](data={'text': text, 'k': k})
        else:
            return RestfulModel(code=-1, msg="No workflow found")
    except Exception as e:
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")


@app.post("/workflow/retrieve/docs")
async def get_relevant_docs(uid: int = Depends(get_uid), requestData: QueryData = Body()):
    try:
        query = """ SELECT collection_name FROM collection WHERE uid=%s and is_selected=true"""
        current_collection = db.fetch_query(query, (uid,))
        if len(current_collection) == 0:
            return RestfulModel(code=-1, msg="select collection first")
        rag = RAG(db_directory=VECTOR_BASE_PATH, collection_name=current_collection[0][0])
        print("requestData",requestData)
        docs = rag.mq_retrieve_documents(requestData.queries)
        print("docs",docs)
        return RestfulModel(data=docs)
    except Exception as e:
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")


@app.get("/workflow/prompt/info")
async def get_prompts_info():
    return RestfulModel[PromptInfo](data={
        'create_game_prompt': CREATE_GAME_PROMPT,
        'rewrite_query_prompt': REWRITE_QUERY_PROMPT,
        'write_dag_prompt': WRITE_DAG_PROMPT,
        'write_xml_prompt': WRITE_XML_PROMPT,
    })


async def get_vector_store(user_namespace: str = '') -> VectorStore:
    """Get the vector store for the current user."""
    return VectorStore(f'{VECTOR_BASE_PATH}/{user_namespace}')



# workflowrubic workflowrubic workflowrubic workflowrubicworkflowrubic workflowrubicworkflowrubic workflowrubicworkflowrubic workflowrubicworkflowrubic workflowrubicworkflowrubic workflowrubic
@app.post("/workflow/rubic/save")
async def save_workflow_rubic(
    uid: int = Depends(get_uid),
    request_data: WorkflowRubicSaveRequest = Body(...)
):
    try:
        workflow_id = request_data.workflow_id
        print("workflow_id =", workflow_id)

        query = """
            SELECT id, dag
            FROM workflow
            WHERE uid = %s AND id = %s
        """
        records = db.fetch_query(query, (uid, workflow_id))
        print("records =", records)

        if not records:
            return RestfulModel(code=-1, msg="No workflow found")

        dag_raw = records[0][1] if isinstance(records[0], (list, tuple)) else records[0]["dag"]
        print("dag_raw =", dag_raw)
        print("dag_raw type =", type(dag_raw))

        if not dag_raw:
            return RestfulModel(code=-1, msg="Workflow dag is empty")

        if isinstance(dag_raw, str):
            dag_clean = clean_json_markdown(dag_raw)
            print("dag_clean =", dag_clean)
            dag_data = json.loads(dag_clean)
        else:
            dag_data = dag_raw

        print("dag_data =", dag_data)

        task_data = transform_workflow_dag_to_rubic_task(workflow_id, dag_data)
        print("task_data =", task_data)

        import time
        now_ts = int(time.time() * 1000)

        check_query = """
            SELECT id FROM workflow_rubic
            WHERE workflow_id = %s
        """
        exists = db.fetch_query(check_query, (workflow_id,))

        if exists:
            update_query = """
                UPDATE workflow_rubic
                SET task = %s,
                    update_time = %s
                WHERE workflow_id = %s
            """
            db.execute_query(
                update_query,
                (
                    json.dumps(task_data, ensure_ascii=False),
                    now_ts,
                    workflow_id
                )
            )
        else:
            insert_query = """
                INSERT INTO workflow_rubic (
                    uid, workflow_id, task, sim_results, report, final_rubric, create_time, update_time
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            db.execute_query(
                insert_query,
                (
                    uid,
                    workflow_id,
                    json.dumps(task_data, ensure_ascii=False),
                    json.dumps({}),
                    json.dumps({}),
                    json.dumps({}),
                    now_ts,
                    now_ts
                )
            )

        print("workflow_rubic saved")

        return RestfulModel(
            code=200,
            msg="Workflow rubic saved successfully",
            data=task_data
        )

    except Exception as e:
        print("save_workflow_rubic error =", repr(e))
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")




@app.post("/workflow/rubic/add")
async def add_workflow_rubic(uid: int = Depends(get_uid)):
    try:
        import time
        return RestfulModel(code=200, msg="Please create rubric task by custom input")
    except Exception as e:
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")

@app.get("/workflow/rubic/info/{workflow_id}")
async def get_workflow_rubic_info(workflow_id: int, uid: int = Depends(get_uid)):
    try:
        query = """
            SELECT workflow_id, task, draft_rubric, sim_results, report, final_rubric, create_time, update_time
            FROM workflow_rubic
            WHERE uid = %s AND workflow_id = %s
        """
        records = db.fetch_query(query, (uid, workflow_id))

        if not records:
            return RestfulModel(code=-1, msg="No workflow rubic found")

        row = records[0]
        item = dict(row) if not isinstance(row, (list, tuple)) else {
            "workflow_id": row[0],
            "task": row[1],
            "draft_rubric": row[2],
            "sim_results": row[3],
            "report": row[4],
            "univeral_rubric": row[5],
            "create_time": row[6],
            "update_time": row[7],
        }

        for key in ["task", "draft_rubric", "sim_results", "report", "final_rubric"]:
            value = item.get(key)
            if value is None:
                item[key] = {}
            elif isinstance(value, str):
                try:
                    item[key] = json.loads(value)
                except Exception:
                    pass

        return RestfulModel(code=200, msg="success", data=item)
    except Exception as e:
        print("get_workflow_rubic_info error =", repr(e))
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")



@app.delete("/workflow_rubic/delete/{id}")
async def delete_workflow_rubic(id: int):
    print("id",id)
    print(type(id))
    try:
        query="""
            DELETE FROM workflow_rubic WHERE workflow_id = %s
        """
        params=(id,)
        print(query)
        db.execute_query(query,params)
        return RestfulModel(code=200,mas="workflow evalute delete successfully")
    except Exception as e:
        return RestfulModel(code=-1,mas=f"An error occurred:{str(e)}")


# collection collection collection collection collection collection collection collection collection collection collection collection
@app.get("/collection/list")
async def list_collections():
    try:
        query = """
            SELECT collection_name,  collection_describe, create_time, is_selected FROM collection ORDER BY create_time DESC
        """
        collections = db.fetch_query(query)
        return RestfulModel(data=[{
            "collection_name": item['collection_name'],
            "collection_describe": item['collection_describe'],
            "create_time": item['create_time'],
            "is_selected": item['is_selected']
        } for item in collections])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


def json_file_2_documents(file: bytes):
    import os
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(file)
            temp_file_path = temp_file.name
        rag = RAG(doc_path=temp_file_path, db_directory=VECTOR_BASE_PATH)
        documents = rag.doc_loader()
        return documents
    except Exception as e:
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")
    finally:
        os.remove(temp_file_path)


@app.post("/collection/create")
async def add_collection_docs(uid: int = Depends(get_uid), file: bytes = File(...), collection_name: str = Form(...),
                              collection_describe: Optional[str] = Form(None), create_time: str = Form(...)):
    try:
        vectorStore = VectorStore(path=VECTOR_BASE_PATH)
        documents = json_file_2_documents(file)
        print("documents",documents)
        print("len documents", len(documents))

        vectorStore.add_docs(collection_name=collection_name, docs=documents)
        query = """
        INSERT INTO collection (uid, collection_name, collection_describe, create_time, is_selected, file)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        params = (uid, collection_name, collection_describe or '', create_time, False, file)
        db.execute_query(query, params)
        return RestfulModel(code=200, msg="Collection created successfully")
    except Exception as e:
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")


@app.post("/collection/select")
async def select_collection(uid: int = Depends(get_uid), collection_data: CollectionData = Body()):
    try:
        query = """ SELECT collection_name FROM collection WHERE uid=%s and is_selected=true"""
        current_collection = db.fetch_query(query, (uid,))
        if len(current_collection) != 0:
            db.execute_query(""" UPDATE collection set is_selected = false WHERE uid=%s and collection_name=%s""",
                             (uid, current_collection[0][0]))
        db.execute_query(""" UPDATE collection set is_selected = true WHERE uid=%s and collection_name=%s""",
                         (uid, collection_data.collection_name))
        return RestfulModel(code=200, msg="Collection selected successfully")
    except Exception as e:
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")


@app.delete("/collection/delete")
async def delete_collection(uid: int = Depends(get_uid), collection_name: str = None):
    try:
        vectorStore = VectorStore(path=VECTOR_BASE_PATH)
        vectorStore.delete_collection(collection_name)
        query = """
               DELETE FROM collection WHERE uid=%s and collection_name = %s
               """
        params = (uid, collection_name)
        db.execute_query(query, params)
        return RestfulModel(code=200, msg="Collection deleted successfully")
    except Exception as e:
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")




if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
