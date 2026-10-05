import logging
import json
import os
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request, Depends, BackgroundTasks
from typing import Optional

from app.pdf_ai_tools_services.ai_summarizer_service import AiSummarizerService
from app.utils.file_handler import save_upload_file_tmp

logger = logging.getLogger(__name__)

router = APIRouter()

def _get_request_id(request: Request) -> str:
    rid = request.headers.get('X-Request-ID')
    if not rid:
        rid = getattr(request.state, 'request_id', uuid.uuid4().hex[:16])
    return rid

@router.post('/ai-summary/upload')
async def upload_for_summary(
    request: Request,
    file: UploadFile = File(...)
):
    user_id = _get_request_id(request)
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail='Only PDF files are supported.')
    temp_path = await save_upload_file_tmp(file)
    job_id = AiSummarizerService.create_job(
        user_id=user_id,
        original_filename=file.filename,
        file_path=temp_path
    )
    return {'job_id': job_id, 'status': 'uploaded'}

@router.post('/ai-summary/process')
async def process_summary(
    request: Request,
    background_tasks: BackgroundTasks,
    job_id: str = Form(...),
    summary_type: str = Form('medium'),
    custom_prompt: Optional[str] = Form(None)
):
    user_id = _get_request_id(request)
    background_tasks.add_task(
        AiSummarizerService.process_job,
        job_id=job_id,
        user_id=user_id,
        summary_type=summary_type
    )
    return {'status': 'processing', 'job_id': job_id}

@router.get('/ai-summary/status/{job_id}')
async def get_summary_status(
    request: Request,
    job_id: str
):
    user_id = _get_request_id(request)
    status_data = AiSummarizerService.get_job_status(user_id, job_id)
    if not status_data:
        raise HTTPException(status_code=404, detail='Job not found.')
    return status_data

@router.get('/ai-summary/result/{job_id}')
async def get_summary_result(
    request: Request,
    job_id: str
):
    user_id = _get_request_id(request)
    result = AiSummarizerService.get_job_result(user_id, job_id)
    if not result:
        raise HTTPException(status_code=404, detail='Job result not found.')
    return result

@router.get('/ai-summary/history')
async def get_summary_history(
    request: Request
):
    user_id = _get_request_id(request)
    history = AiSummarizerService.get_user_history(user_id)
    return {'history': history}

@router.delete('/ai-summary/history/{job_id}')
async def delete_summary_history(
    request: Request,
    job_id: str
):
    user_id = _get_request_id(request)
    success = AiSummarizerService.delete_history_item(user_id, job_id)
    if not success:
        raise HTTPException(status_code=404, detail='History item not found.')
    return {'status': 'success', 'message': 'Deleted successfully.'}
