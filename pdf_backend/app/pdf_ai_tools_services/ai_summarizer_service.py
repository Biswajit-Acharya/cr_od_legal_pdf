import os
import uuid
import logging
import httpx
import fitz  # PyMuPDF
from datetime import datetime
from typing import Dict, Any, List, Optional
import asyncio

logger = logging.getLogger(__name__)

# Temporary in-memory store for jobs and history, simulating a database.
# In a real Nexora deployment, this would be replaced with SQLAlchemy models.
_JOBS_DB: Dict[str, Dict[str, Any]] = {}
_HISTORY_DB: List[Dict[str, Any]] = []

class AiSummarizerService:
    
    @classmethod
    def get_ai_config(cls) -> Dict[str, str]:
        return {
            "provider": os.environ.get("AI_PROVIDER", "ollama"),
            "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            "model": os.environ.get("OLLAMA_MODEL", "gemma3:1b")
        }
        
    @classmethod
    def create_job(cls, user_id: str, original_filename: str, file_path: str) -> str:
        job_id = str(uuid.uuid4())
        _JOBS_DB[job_id] = {
            "id": job_id,
            "user_id": user_id,
            "original_filename": original_filename,
            "file_path": file_path,
            "status": "Uploading",
            "created_at": datetime.utcnow().isoformat(),
            "progress": 0,
            "summary_type": None,
            "result": None,
            "error": None
        }
        return job_id

    @classmethod
    def get_job_status(cls, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        job = _JOBS_DB.get(job_id)
        if not job or job["user_id"] != user_id:
            return None
        return {
            "status": job["status"],
            "progress": job.get("progress", 0),
            "error": job.get("error")
        }

    @classmethod
    def get_job_result(cls, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        job = _JOBS_DB.get(job_id)
        if not job or job["user_id"] != user_id:
            return None
        return {
            "result": job.get("result"),
            "summary_type": job.get("summary_type"),
            "original_filename": job.get("original_filename")
        }

    @classmethod
    def get_user_history(cls, user_id: str) -> List[Dict[str, Any]]:
        return [h for h in _HISTORY_DB if h["user_id"] == user_id]

    @classmethod
    def delete_user_history(cls, job_id: str, user_id: str) -> bool:
        global _HISTORY_DB
        initial_len = len(_HISTORY_DB)
        _HISTORY_DB = [h for h in _HISTORY_DB if not (h["id"] == job_id and h["user_id"] == user_id)]
        return len(_HISTORY_DB) < initial_len

    @classmethod
    async def process_job(cls, job_id: str, user_id: str, summary_type: str) -> Dict[str, Any]:
        job = _JOBS_DB.get(job_id)
        if not job or job["user_id"] != user_id:
            raise ValueError("Job not found or unauthorized")
        
        job["summary_type"] = summary_type
        
        # In a real app, this should be dispatched to a background worker (e.g. Celery/RedisQ).
        # For this implementation, we run it asynchronously here to immediately return the result or error.
        
        try:
            job["status"] = "Extracting text"
            job["progress"] = 10
            
            # 1. Extract text
            text = cls._extract_text(job["file_path"], job)
            
            if not text.strip():
                # Attempt OCR fallback if empty
                job["status"] = "OCR processing"
                job["progress"] = 30
                text = cls._extract_ocr(job["file_path"])
            
            if not text.strip():
                raise ValueError("No readable text was found in this PDF.")
                
            job["status"] = "Preparing content"
            job["progress"] = 40
            
            cleaned_text = cls._clean_text(text)
            
            # 2. Chunking
            chunks = cls._chunk_text(cleaned_text)
            
            job["status"] = "Summarizing"
            job["progress"] = 50
            
            # 3. Call AI
            summary = await cls._generate_summary(chunks, summary_type, job)
            
            job["status"] = "Completed"
            job["progress"] = 100
            job["result"] = summary
            job["completed_at"] = datetime.utcnow().isoformat()
            
            # Save to history
            history_record = {
                "id": job_id,
                "user_id": user_id,
                "original_filename": job["original_filename"],
                "summary_type": summary_type,
                "result": summary,
                "created_at": job["created_at"],
                "completed_at": job["completed_at"]
            }
            _HISTORY_DB.append(history_record)
            
            return {"success": True, "job_id": job_id, "summary": summary}
            
        except Exception as e:
            logger.error(f"Summarization failed for job {job_id}: {e}")
            job["status"] = "Failed"
            job["error"] = str(e)
            raise ValueError(str(e))
        finally:
            # Cleanup temp file
            cls._cleanup_file(job["file_path"])


    @classmethod
    def _extract_text(cls, file_path: str, job: Dict[str, Any]) -> str:
        text_content = []
        try:
            doc = fitz.open(file_path)
            if doc.is_encrypted:
                raise ValueError("PDF is password-protected or encrypted.")
            
            page_count = len(doc)
            for i, page in enumerate(doc):
                text_content.append(page.get_text())
                # Update progress roughly
                if i % 10 == 0 and page_count > 0:
                    job["progress"] = 10 + int((i / page_count) * 20)
            doc.close()
        except fitz.FileDataError:
            raise ValueError("Corrupted or invalid PDF file.")
        
        return "\n".join(text_content)

    @classmethod
    def _extract_ocr(cls, file_path: str) -> str:
        # Isolated helper for OCR.
        # In this implementation, we attempt to use paddleocr if available.
        # If not available or fails, return empty to trigger the "No readable text" error.
        try:
            from paddleocr import PaddleOCR
            import numpy as np
            
            ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
            text_content = []
            
            doc = fitz.open(file_path)
            for page in doc:
                pix = page.get_pixmap()
                img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
                
                # Convert to RGB if needed
                if pix.n == 4:
                    import cv2
                    img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    
                result = ocr.ocr(img, cls=True)
                if result and result[0]:
                    for line in result[0]:
                        text_content.append(line[1][0])
            doc.close()
            return "\n".join(text_content)
        except ImportError:
            logger.warning("PaddleOCR not installed, skipping OCR fallback.")
            return ""
        except Exception as e:
            logger.warning(f"OCR failed: {e}")
            return ""

    @classmethod
    def _clean_text(cls, text: str) -> str:
        import re
        # Normalize whitespace but preserve paragraphs
        text = re.sub(r'[\r\n]{3,}', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        return text.strip()

    @classmethod
    def _chunk_text(cls, text: str, max_chars_per_chunk: int = 6000) -> List[str]:
        # Rough token estimation: 4 chars ~ 1 token. 6000 chars ~ 1500 tokens
        # Safe for gemma3:1b context limits
        chunks = []
        current_chunk = ""
        
        paragraphs = text.split("\n\n")
        for p in paragraphs:
            if len(current_chunk) + len(p) < max_chars_per_chunk:
                current_chunk += p + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = p + "\n\n"
                
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks if chunks else [text]

    @classmethod
    async def _generate_summary(cls, chunks: List[str], summary_type: str, job: Dict[str, Any]) -> str:
        config = cls.get_ai_config()
        
        if config["provider"] != "ollama":
            raise ValueError(f"Provider {config['provider']} not currently implemented.")
        
        base_url = config["base_url"]
        model = config["model"]
        
        prompt_templates = {
            "short": "Provide a very concise summary capturing only the most important points. Avoid unnecessary details. Document chunk:\n{text}",
            "medium": "Provide a balanced summary including major facts, findings, and conclusions. Document chunk:\n{text}",
            "detailed": "Provide a comprehensive and detailed summary preserving important facts, sections, names, and conclusions. Document chunk:\n{text}"
        }
        
        prompt_template = prompt_templates.get(summary_type, prompt_templates["medium"])
        
        chunk_summaries = []
        total_chunks = len(chunks)
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # First check if Ollama is accessible
            try:
                await client.get(base_url)
            except httpx.RequestError:
                raise ValueError("Local AI service is currently unavailable. Please ensure Ollama is running.")

            for i, chunk in enumerate(chunks):
                prompt = prompt_template.format(text=chunk)
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                }
                
                try:
                    response = await client.post(f"{base_url}/api/generate", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    chunk_sum = data.get("response", "").strip()
                    if chunk_sum:
                        chunk_summaries.append(chunk_sum)
                    
                    job["progress"] = 50 + int(((i + 1) / total_chunks) * 40)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        raise ValueError(f"AI model '{model}' not found in Ollama.")
                    raise ValueError(f"AI service error: {e.response.text}")
                except httpx.RequestError:
                    raise ValueError("Failed to communicate with AI provider.")

        if not chunk_summaries:
            raise ValueError("AI returned an empty response.")

        # If multiple chunks, synthesize them
        if len(chunk_summaries) > 1:
            job["status"] = "Finalizing"
            combined = "\n\n---\n\n".join(chunk_summaries)
            synth_prompt = f"Synthesize the following summaries into one single coherent final summary. Ensure a smooth flow and eliminate repetition.\n\n{combined}"
            payload = {
                "model": model,
                "prompt": synth_prompt,
                "stream": False
            }
            async with httpx.AsyncClient(timeout=120.0) as client:
                try:
                    response = await client.post(f"{base_url}/api/generate", json=payload)
                    response.raise_for_status()
                    final_summary = response.json().get("response", "").strip()
                    return final_summary or "\n\n".join(chunk_summaries)
                except:
                    # Fallback to concatenated if synthesis fails
                    return "\n\n".join(chunk_summaries)
        else:
            return chunk_summaries[0]

    @classmethod
    def _cleanup_file(cls, file_path: str):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
