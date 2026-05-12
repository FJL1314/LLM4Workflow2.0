from schemas import genericRubricRequest,DraftRubricRequest,RestfulModel,ReportRequest,SimulationRequest,FinalRubricRequest
from db import Database
from fastapi.middleware.cors import CORSMiddleware
from service import generate_draft_rubric,generate_dag_report,generate_simulation_results,generate_final_task_specific_rubric
from fastapi import Body, FastAPI, Request, HTTPException, Form, File, Depends, Query, Path
import json
import time
from util import to_serializable,generic_RUBRICS,merge_rubrics

def get_uid(request: Request):
    return 1

app = FastAPI(title="Workflow Rubric Service")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)




db = Database()
@app.on_event("startup")
async def startup():
    db_config = {
        "dbname": "llm4workflow",
        "user": "postgres",
        "password": "",
        "host": "localhost",
        "port": 5432
    }
    db.connect(**db_config)

@app.get("/workflow/rubic/list")
async def list_workflow_rubic(uid: int = Depends(get_uid)):
    try:
        query = """
            SELECT workflow_id, task, sim_results, report, univeral_rubric, create_time, update_time,workflow_generate_id
            FROM workflow_rubic
            WHERE uid = %s
            ORDER BY workflow_generate_id desc
        """
        records = db.fetch_query(query, (uid,))

        result = []
        for row in records:
            item = dict(row)

            for key in ["task", "sim_results", "report", "final_rubric"]:
                value = item.get(key)
                if value is None:
                    item[key] = {}
                elif isinstance(value, str):
                    try:
                        item[key] = json.loads(value)
                    except Exception:
                        pass

            result.append(item)

        return RestfulModel(code=200, msg="success", data=result)
    except Exception as e:
        print("list_workflow_rubic error =", repr(e))
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")



@app.post("/workflow/rubic/update")
async def upsert_workflow_rubic(req: dict):
    try:
        workflow_id = req.get("workflow_id")
        task = req.get("task")

        check_query = """
            SELECT id FROM workflow_rubic WHERE workflow_id = %s
        """
        exists = db.fetch_query(check_query, (workflow_id,))
        print("exists",exists)
        if exists:
            query = """
                UPDATE workflow_rubic
                SET task = %s
                WHERE workflow_id = %s
            """
            params = (task, workflow_id)
        else:
            query = """
                INSERT INTO workflow_rubic (workflow_id, task, uid)
                VALUES (%s, %s, %s)
            """
            params = (workflow_id, task,1)

        db.execute_query(query, params)

        return RestfulModel(code=200, msg="success")
    except Exception as e:
        return RestfulModel(code=-1, msg=f"An error occurred: {str(e)}")





@app.post("/workflow/rubric/generic")
async def generate_workflow_generic_rubric(
    uid: int = Depends(get_uid),
    req: genericRubricRequest = Body(...)
):
    try:
        workflow_id = int(req.workflow_id)
        task = req.task
        generic_rubric = generic_RUBRICS
        serializable_rubric = to_serializable(generic_rubric)
        now_ts = int(time.time() * 1000)
        serializable_task = task
        if isinstance(task, (dict, list)):
            serializable_task = json.dumps(task, ensure_ascii=False)

        check_query = """
            SELECT id
            FROM workflow_rubic
            WHERE workflow_id = %s
            LIMIT 1
        """
        existed = db.fetch_query(check_query, (workflow_id,))

        if existed and len(existed) > 0:
            update_query = """
                UPDATE workflow_rubic
                SET task = %s,
                    univeral_rubric = %s,
                    update_time = %s
                WHERE workflow_id = %s
            """
            db.execute_query(
                update_query,
                (
                    serializable_task,
                    json.dumps(serializable_rubric, ensure_ascii=False),
                    now_ts,
                    workflow_id,
                )
            )
            record_id = existed[0]["id"] if isinstance(existed[0], dict) else existed[0][0]
        else:
            insert_query = """
                INSERT INTO workflow_rubic (
                    uid,
                    workflow_id,
                    task,
                    univeral_rubric,
                    create_time,
                    update_time
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            db.execute_query(
                insert_query,
                (
                    uid,
                    workflow_id,
                    serializable_task,
                    json.dumps(serializable_rubric, ensure_ascii=False),
                    now_ts,
                    now_ts,
                )
            )
            record_id = None

        return RestfulModel(
            code=200,
            msg="generic rubric generated successfully",
            data={
                "id": record_id,
                "workflow_id": workflow_id,
                "task": task,
                "generic_rubric": serializable_rubric
            }
        )
    except Exception as e:
        print("generate_workflow_generic_rubric error =", repr(e))
        return RestfulModel(
            code=-1,
            msg=f"An error occurred: {str(e)}",
            data=None
        )



@app.post("/workflow/rubric/draft")
async def draft_rubric(req: DraftRubricRequest):
    try:
        result = await generate_draft_rubric(req.task)

        now_ts = int(time.time() * 1000)

        dimensions_json = [
            {
                "theme": d.theme,
                "tips": d.tips,
                "weight": d.weight,
                "description": d.description
            }
            for d in result.dimensions
        ]
        update_query = """
            UPDATE workflow_rubic
            SET draft_rubric = %s,
                update_time = %s
            WHERE workflow_id = %s
        """
        try:
            db.execute_query(
                update_query,
                (
                    json.dumps(dimensions_json),
                    now_ts,
                    int(req.workflow_id),
                )
            )
        except Exception as db_err:
            print("DB write failed:", db_err)
        return RestfulModel(
            code=200,
            msg="success",
            data={
                "dimensions": dimensions_json
            }
        )
    except Exception as e:
        return RestfulModel(
            code=-1,
            msg=f"An error occurred: {str(e)}",
            data=None
        )

@app.post("/workflow/rubric/simulation")
async def generate_workflow_simulation_results(req: SimulationRequest):
    try:
        workflow_id = req.workflow_id
        task = req.task

        sim_results = await generate_simulation_results(task)

        now_ts = int(time.time() * 1000)

        sql = """
        INSERT INTO workflow_rubic (workflow_id, task, sim_results, update_time)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (workflow_id)
        DO UPDATE SET
            task = EXCLUDED.task,
            sim_results = EXCLUDED.sim_results,
            update_time = EXCLUDED.update_time
        """

        params = (
            workflow_id,
            json.dumps(task, ensure_ascii=False),
            json.dumps(sim_results, ensure_ascii=False),
            now_ts,
        )

        db.execute_query(sql, params)
        return RestfulModel(
            code=200,
            msg="success",
            data={
                "sim_results": sim_results
            }
        )
    except Exception as e:
        return RestfulModel(
            code=-1,
            msg=f"An error occurred: {str(e)}",
            data=None
        )

@app.post("/workflow/rubric/final")
async def generate_final_rubric(req: FinalRubricRequest):
    try:
        workflow_id = req.workflow_id
        task = req.task
        draft_rubric = req.draft_rubric
        print("draft_rubric.....",draft_rubric)
        sim_results = req.sim_results

        final_rubric = await generate_final_task_specific_rubric(
            draft_rubric=draft_rubric,
            sim_results=sim_results,
            task=task
        )
        print("final_rubric =", final_rubric)

        now_ts = int(time.time() * 1000)

        sql = """
        INSERT INTO workflow_rubic (
            workflow_id, task, draft_rubric, sim_results, final_rubric, update_time
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (workflow_id)
        DO UPDATE SET
            task = EXCLUDED.task,
            draft_rubric = EXCLUDED.draft_rubric,
            sim_results = EXCLUDED.sim_results,
            final_rubric = EXCLUDED.final_rubric,
            update_time = EXCLUDED.update_time
        """

        params = (
            workflow_id,
            json.dumps(task, ensure_ascii=False),
            json.dumps(draft_rubric, ensure_ascii=False),
            json.dumps(sim_results, ensure_ascii=False),
            json.dumps(final_rubric, ensure_ascii=False),
            now_ts,
        )

        db.execute_query(sql, params)

        return RestfulModel(
            code=200,
            msg="success",
            data={
                "final_rubric": final_rubric
            }
        )
    except Exception as e:
        print("generate_final_rubric error =", e)
        return RestfulModel(
            code=-1,
            msg=f"An error occurred: {str(e)}",
            data=None
        )



@app.post("/workflow/rubric/report")
async def report(req: ReportRequest):
    try:
        merged_rubric = merge_rubrics(
            req.generic_rubric,
            req.final_rubric,
        )

        if not merged_rubric:
            return RestfulModel(
                code=-1,
                msg="No rubric dimensions selected.",
                data=None
            )

        generic_count = len(req.generic_rubric or [])
        draft_count = len(req.final_rubric or [])

        result = await generate_dag_report(
            task=req.task,
            rubric=merged_rubric,
        )

        if isinstance(result, dict):
            result_dict = result
        elif hasattr(result, "__dict__"):
            result_dict = dict(result.__dict__)
        else:
            result_dict = {
                "raw_result": str(result)
            }
        result_dict = to_serializable(result)

        old_meta = result_dict.get("rubric_metadata", {}) or {}
        result_dict["rubric_metadata"] = {
            **old_meta,
            "type": old_meta.get("type", "merged_selected"),
            "source": old_meta.get("source", "generic+draft"),
            "total_dimensions": len(merged_rubric),
            "generic_dimensions": len(req.generic_rubric or []),
            "task_specific_dimensions": len(req.final_rubric or []),
        }

        now_ts = int(time.time() * 1000)

        try:
            update_query = """
                UPDATE workflow_rubic
                SET report = %s,
                    update_time = %s
                WHERE workflow_id = %s
            """
            affected = db.execute_query(
                update_query,
                (
                    json.dumps(result_dict, ensure_ascii=False),
                    now_ts,
                    req.workflow_id,
                )
            )
            print("affected rows =", affected)
        except Exception as db_err:
            print("DB write failed:", db_err)

        print("result_dict =", result_dict)

        return RestfulModel(
            code=200,
            msg="success",
            data=result_dict
        )

    except Exception as e:
        import traceback
        print("report error =", repr(e))
        traceback.print_exc()
        return RestfulModel(
            code=-1,
            msg=str(e),
            data=None
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8001, reload=True)