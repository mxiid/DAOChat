from typing import Dict, List
from datetime import datetime, timedelta
from sqlalchemy import func
from .models import ChatSession, ChatMessage

class ChatAnalytics:
    def __init__(self, db_session):
        self.db = db_session

    async def get_session_metrics(self, time_range: timedelta) -> Dict:
        since = datetime.utcnow() - time_range
        return {
            'total_sessions': await self.db.query(ChatSession)
                .filter(ChatSession.created_at >= since)
                .count(),
            'avg_messages_per_session': await self.db.query(
                func.avg(func.count(ChatMessage.id))
            )
            .filter(ChatMessage.created_at >= since)
            .group_by(ChatMessage.session_id)
            .scalar(),
            'total_tokens': await self.db.query(func.sum(ChatMessage.tokens))
                .filter(ChatMessage.created_at >= since)
                .scalar()
        }

    async def get_popular_topics(self) -> List[Dict]:
        # Implement topic extraction and analysis
        pass 