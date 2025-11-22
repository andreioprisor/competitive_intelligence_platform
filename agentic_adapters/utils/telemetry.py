import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TelemetryCollector:
    """Collects performance metrics and usage data"""
    
    def __init__(self):
        self.start_time = time.time()
        self.events = []
    
    def record_event(
        self,
        stage: str,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Record a telemetry event
        
        Args:
            stage: Pipeline stage (triage, serp, crawl, etc.)
            event_type: Type of event (start, complete, error, etc.)
            data: Additional data to record
            duration: Duration in seconds
            
        Returns:
            Telemetry event dictionary
        """
        event = {
            "timestamp": time.time(),
            "stage": stage,
            "event": event_type,
            "data": data or {},
            "duration_ms": round(duration * 1000, 2) if duration else None
        }
        
        self.events.append(event)
        
        # Log the event
        if duration:
            logger.info(f"{stage}.{event_type} completed in {duration:.3f}s")
        else:
            logger.info(f"{stage}.{event_type}")
        
        return event
    
    def record_api_call(
        self,
        service: str,
        endpoint: str,
        duration: float,
        tokens_used: Optional[int] = None,
        cost_estimate: Optional[float] = None,
        success: bool = True
    ) -> Dict[str, Any]:
        """Record API call metrics"""
        return self.record_event(
            stage="api_call",
            event_type=f"{service}_{endpoint}",
            data={
                "service": service,
                "endpoint": endpoint,
                "tokens_used": tokens_used,
                "cost_estimate": cost_estimate,
                "success": success
            },
            duration=duration
        )
    
    def record_stage_start(self, stage: str) -> Dict[str, Any]:
        """Record the start of a pipeline stage"""
        return self.record_event(stage, "start")
    
    def record_stage_complete(
        self,
        stage: str,
        duration: float,
        output_count: Optional[int] = None,
        success: bool = True
    ) -> Dict[str, Any]:
        """Record the completion of a pipeline stage"""
        return self.record_event(
            stage=stage,
            event_type="complete",
            data={
                "output_count": output_count,
                "success": success
            },
            duration=duration
        )
    
    def record_error(
        self,
        stage: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Record an error event"""
        return self.record_event(
            stage=stage,
            event_type="error",
            data={
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context or {}
            }
        )
    
    def record_crawling_usage(
        self,
        crawl4ai_count: int = 0,
        scraping_dog_count: int = 0,
        bright_data_count: int = 0,
        total_urls: int = 0,
        duration: Optional[float] = None
    ) -> Dict[str, Any]:
        """Record crawling service usage metrics"""
        return self.record_event(
            stage="crawl",
            event_type="service_usage", 
            data={
                "crawl4ai_urls": crawl4ai_count,
                "scraping_dog_urls": scraping_dog_count,
                "bright_data_urls": bright_data_count,
                "total_urls": total_urls,
                "crawl4ai_percentage": round((crawl4ai_count / total_urls * 100) if total_urls > 0 else 0, 1),
                "api_usage_percentage": round(((scraping_dog_count + bright_data_count) / total_urls * 100) if total_urls > 0 else 0, 1),
                "cost_efficiency": "high" if crawl4ai_count >= total_urls * 0.7 else "medium" if crawl4ai_count >= total_urls * 0.4 else "low"
            },
            duration=duration
        )
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all telemetry data"""
        total_duration = time.time() - self.start_time
        
        # Count events by stage
        stage_counts = {}
        stage_durations = {}
        total_tokens = 0
        total_cost = 0.0
        
        # Crawling service metrics
        crawling_metrics = {
            "crawl4ai_urls": 0,
            "scraping_dog_urls": 0, 
            "oxylabs_urls": 0,
            "total_urls": 0,
            "cost_efficiency": "unknown"
        }
        
        for event in self.events:
            stage = event["stage"]
            stage_counts[stage] = stage_counts.get(stage, 0) + 1
            
            if event["duration_ms"]:
                stage_durations[stage] = stage_durations.get(stage, 0) + (event["duration_ms"] / 1000)
            
            # Aggregate tokens and costs
            data = event.get("data", {})
            if data.get("tokens_used"):
                total_tokens += data["tokens_used"]
            if data.get("cost_estimate"):
                total_cost += data["cost_estimate"]
            
            # Aggregate crawling service usage
            if event["event"] == "service_usage" and stage == "crawl":
                crawling_metrics["crawl4ai_urls"] += data.get("crawl4ai_urls", 0)
                crawling_metrics["scraping_dog_urls"] += data.get("scraping_dog_urls", 0)
                crawling_metrics["oxylabs_urls"] += data.get("oxylabs_urls", 0)
                crawling_metrics["total_urls"] += data.get("total_urls", 0)
                crawling_metrics["cost_efficiency"] = data.get("cost_efficiency", "unknown")
        
        # Count errors
        error_count = len([e for e in self.events if e["event"] == "error"])
        
        return {
            "total_duration_s": round(total_duration, 3),
            "total_events": len(self.events),
            "error_count": error_count,
            "stage_counts": stage_counts,
            "stage_durations": {k: round(v, 3) for k, v in stage_durations.items()},
            "total_tokens": total_tokens,
            "estimated_cost": round(total_cost, 4),
            "crawling_services": crawling_metrics,
            "events": self.events
        }
    
    def log_summary(self):
        """Log a summary of telemetry data"""
        summary = self.get_summary()
        
        logger.info("=== QIA Pipeline Summary ===")
        logger.info(f"Total Duration: {summary['total_duration_s']}s")
        logger.info(f"Total Events: {summary['total_events']}")
        logger.info(f"Errors: {summary['error_count']}")
        logger.info(f"Total Tokens: {summary['total_tokens']}")
        logger.info(f"Estimated Cost: ${summary['estimated_cost']}")
        
        # Log crawling service usage
        crawling = summary['crawling_services']
        if crawling['total_urls'] > 0:
            logger.info("=== Crawling Services Usage ===")
            logger.info(f"Total URLs Crawled: {crawling['total_urls']}")
            logger.info(f"Crawl4AI (Free): {crawling['crawl4ai_urls']} URLs")
            logger.info(f"Scraping Dog: {crawling['scraping_dog_urls']} URLs")
            logger.info(f"Oxylabs: {crawling['oxylabs_urls']} URLs")
            logger.info(f"Cost Efficiency: {crawling['cost_efficiency']}")
            
            # Calculate percentages
            if crawling['total_urls'] > 0:
                crawl4ai_pct = (crawling['crawl4ai_urls'] / crawling['total_urls']) * 100
                api_pct = ((crawling['scraping_dog_urls'] + crawling['oxylabs_urls']) / crawling['total_urls']) * 100
                logger.info(f"Free Service Usage: {crawl4ai_pct:.1f}%")
                logger.info(f"Paid API Usage: {api_pct:.1f}%")
        
        for stage, duration in summary['stage_durations'].items():
            count = summary['stage_counts'].get(stage, 0)
            logger.info(f"  {stage}: {duration}s ({count} events)")


class StageTimer:
    """Context manager for timing pipeline stages"""
    
    def __init__(self, telemetry: TelemetryCollector, stage: str):
        self.telemetry = telemetry
        self.stage = stage
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        self.telemetry.record_stage_start(self.stage)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type is None:
            self.telemetry.record_stage_complete(self.stage, duration)
        else:
            self.telemetry.record_error(self.stage, exc_val)
            self.telemetry.record_stage_complete(self.stage, duration, success=False)


def create_telemetry_event(
    stage: str,
    metrics: Dict[str, Any],
    timestamp: Optional[float] = None
) -> Dict[str, Any]:
    """Create a standardized telemetry event"""
    return {
        "timestamp": timestamp or time.time(),
        "stage": stage,
        "metrics": metrics
    }