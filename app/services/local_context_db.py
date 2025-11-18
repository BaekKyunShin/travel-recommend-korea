"""
지역 맥락 데이터베이스 (Local Context Database)

🆕 AI 기반 동적 생성으로 대체됨
이제 이 클래스는 호환성을 위한 빈 구현만 제공합니다.
"""

from typing import Dict, Any, List, Optional


class LocalContextDB:
    """
    ✨ AI가 모든 지역 정보를 동적으로 생성하므로 이 DB는 더 이상 필요하지 않습니다.
    
    호환성을 위해 빈 메서드만 제공합니다.
    """
    
    def __init__(self):
        """초기화 (아무것도 하지 않음)"""
        pass
    
    def get_context(self, location: str) -> Dict[str, Any]:
        """
        ✨ AI가 대신 처리하므로 빈 딕셔너리 반환
        
        Args:
            location: 지역명
        
        Returns:
            빈 딕셔너리 (AI가 동적 생성)
        """
        return {}
    
    async def get_or_create_context(self, location: str, lat: Optional[float] = None, lng: Optional[float] = None) -> Dict[str, Any]:
        """
        ✨ AI가 대신 처리하므로 빈 딕셔너리 반환
        
        Args:
            location: 지역명
            lat: 위도 (미사용)
            lng: 경도 (미사용)
        
        Returns:
            빈 딕셔너리 (AI가 동적 생성)
        """
        print(f"   ℹ️ LocalContextDB 호출됨 (AI 동적 생성으로 대체됨): {location}")
        return {}
    
    def cleanup_expired_cache(self):
        """캐시 정리 (아무것도 하지 않음)"""
        return 0
    
    def enrich_search_with_context(
        self,
        location: str,
        user_request: str,
        time_context: Optional[List[str]] = None,
        target_context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        ✨ AI가 대신 처리하므로 빈 응답 반환
        
        Returns:
            enriched=False (AI가 처리)
        """
        return {
            'original_request': user_request,
            'enriched': False
        }
    
    def get_price_range_filter(self, price_range: str) -> tuple:
        """가격 범위 반환 (기본값)"""
        return (8000, 15000)
    
    def get_all_contexts(self) -> Dict[str, Dict]:
        """빈 딕셔너리 반환"""
        return {}
    
    def search_by_characteristic(self, characteristic: str) -> List[str]:
        """빈 리스트 반환"""
        return []
