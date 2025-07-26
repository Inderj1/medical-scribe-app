import json
import logging
import queue
import threading
import time
from typing import Dict, Optional
from dataclasses import asdict
import redis

from app.services.enhanced_transcription_service import TranscriptionJob

logger = logging.getLogger(__name__)


class TranscriptionQueue:
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.local_queue = queue.PriorityQueue()
        self.processing_jobs: Dict[str, TranscriptionJob] = {}
        self.failed_jobs: Dict[str, Dict] = {}
        self.max_retries = 3
        self.job_timers: Dict[str, threading.Timer] = {}
        
    def add_job(self, job: TranscriptionJob, priority: int = 1):
        """Add transcription job to queue"""
        if self.redis_client:
            try:
                # Use Redis for distributed processing
                job_data = asdict(job)
                # Convert audio data to base64 for JSON serialization
                if isinstance(job_data.get('audio_data'), bytes):
                    import base64
                    job_data['audio_data'] = base64.b64encode(job_data['audio_data']).decode('utf-8')
                    job_data['audio_data_encoded'] = True  # Flag to decode later
                # Add to sorted set with priority as score
                self.redis_client.zadd(
                    "transcription_queue", 
                    {json.dumps(job_data): priority}
                )
                logger.info(f"Added job {job.id} to Redis queue with priority {priority}")
            except Exception as e:
                logger.error(f"Failed to add job to Redis: {e}, falling back to local queue")
                self._add_to_local_queue(job, priority)
        else:
            self._add_to_local_queue(job, priority)
        
        logger.info(f"Added transcription job {job.id} to queue")
    
    def _add_to_local_queue(self, job: TranscriptionJob, priority: int):
        """Add job to local priority queue"""
        # Priority queue uses min heap, so lower number = higher priority
        self.local_queue.put((priority, time.time(), job))
    
    def get_job(self) -> Optional[TranscriptionJob]:
        """Get next job from queue"""
        try:
            if self.redis_client:
                # Get highest priority job from Redis
                result = self.redis_client.zpopmin("transcription_queue", count=1)
                if result:
                    job_data_str, _ = result[0]
                    job_dict = json.loads(job_data_str)
                    # Decode audio data if it was encoded
                    if job_dict.get('audio_data_encoded'):
                        import base64
                        job_dict['audio_data'] = base64.b64decode(job_dict['audio_data'])
                        del job_dict['audio_data_encoded']
                    return TranscriptionJob(**job_dict)
            else:
                if not self.local_queue.empty():
                    _, _, job = self.local_queue.get_nowait()
                    return job
        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"Error getting job from queue: {e}")
        return None
    
    def mark_processing(self, job: TranscriptionJob):
        """Mark job as currently being processed"""
        self.processing_jobs[job.id] = job
        
        # Set a timeout for the job (30 seconds)
        def timeout_handler():
            if job.id in self.processing_jobs:
                logger.warning(f"Job {job.id} timed out, marking as failed")
                self.mark_failed(job, "Processing timeout")
        
        timer = threading.Timer(30.0, timeout_handler)
        timer.start()
        self.job_timers[job.id] = timer
    
    def mark_completed(self, job_id: str):
        """Mark job as completed"""
        if job_id in self.processing_jobs:
            del self.processing_jobs[job_id]
        
        # Cancel timeout timer
        if job_id in self.job_timers:
            self.job_timers[job_id].cancel()
            del self.job_timers[job_id]
        
        logger.info(f"Job {job_id} completed successfully")
    
    def mark_failed(self, job: TranscriptionJob, error: str):
        """Mark job as failed and handle retry logic"""
        job.retry_count += 1
        job.status = "failed"
        
        if job.id in self.processing_jobs:
            del self.processing_jobs[job.id]
        
        # Cancel timeout timer
        if job.id in self.job_timers:
            self.job_timers[job.id].cancel()
            del self.job_timers[job.id]
        
        if job.retry_count < self.max_retries:
            # Retry with exponential backoff
            retry_delay = 2 ** job.retry_count
            
            def retry_job():
                job.status = "retrying"
                # Increase priority for retry (lower number = higher priority)
                self.add_job(job, priority=0)
            
            timer = threading.Timer(retry_delay, retry_job)
            timer.start()
            
            logger.info(f"Retrying job {job.id} in {retry_delay} seconds (attempt {job.retry_count})")
        else:
            self.failed_jobs[job.id] = {
                "job": asdict(job), 
                "error": error, 
                "failed_at": time.time()
            }
            logger.error(f"Job {job.id} failed permanently after {job.retry_count} attempts: {error}")
    
    def get_queue_status(self) -> Dict:
        """Get current queue status"""
        if self.redis_client:
            try:
                queue_size = self.redis_client.zcard("transcription_queue")
            except:
                queue_size = self.local_queue.qsize()
        else:
            queue_size = self.local_queue.qsize()
        
        return {
            "queue_size": queue_size,
            "processing_jobs": len(self.processing_jobs),
            "failed_jobs": len(self.failed_jobs),
            "processing_job_ids": list(self.processing_jobs.keys()),
            "failed_job_ids": list(self.failed_jobs.keys())
        }
    
    def clear_failed_jobs(self):
        """Clear failed jobs history"""
        self.failed_jobs.clear()
        logger.info("Cleared failed jobs history")
    
    def requeue_failed_job(self, job_id: str) -> bool:
        """Requeue a specific failed job"""
        if job_id in self.failed_jobs:
            job_data = self.failed_jobs[job_id]["job"]
            job = TranscriptionJob(**job_data)
            job.retry_count = 0  # Reset retry count
            job.status = "pending"
            
            self.add_job(job, priority=1)
            del self.failed_jobs[job_id]
            
            logger.info(f"Requeued failed job {job_id}")
            return True
        return False
    
    def cleanup(self):
        """Clean up resources"""
        # Cancel all active timers
        for timer in self.job_timers.values():
            timer.cancel()
        self.job_timers.clear()
        
        # Clear queues
        self.processing_jobs.clear()
        
        if self.redis_client:
            try:
                self.redis_client.delete("transcription_queue")
            except:
                pass
        
        logger.info("Transcription queue cleaned up")