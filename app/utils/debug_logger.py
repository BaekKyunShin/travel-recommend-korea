"""
디버깅 로거 - 응답 크기 모니터링

데이터 크기 에러 디버깅을 위한 유틸리티
"""

import json
from typing import Any, Dict

def log_response_size(data: Any, context: str = "") -> int:
    """
    응답 크기를 로깅하고 경고 표시
    
    Args:
        data: 측정할 데이터 (dict, list, str 등)
        context: 컨텍스트 정보 (예: "API Response", "Schedule Frame")
    
    Returns:
        size_bytes: 바이트 단위 크기
    """
    try:
        size_bytes = len(json.dumps(data, ensure_ascii=False))
        size_kb = size_bytes / 1024
        size_mb = size_kb / 1024
        
        if size_mb >= 1:
            print(f"📊 [{context}] 응답 크기: {size_mb:.2f} MB ({size_bytes:,} bytes)")
            if size_mb > 5:
                print(f"   ⚠️⚠️⚠️ 경고: 응답이 매우 큼 (>5MB) - 프론트엔드 성능 저하 가능!")
        elif size_kb >= 100:
            print(f"📊 [{context}] 응답 크기: {size_kb:.2f} KB ({size_bytes:,} bytes)")
            if size_kb > 500:
                print(f"   ⚠️ 경고: 응답이 큼 (>500KB) - 최적화 권장")
        else:
            print(f"📊 [{context}] 응답 크기: {size_kb:.2f} KB ({size_bytes:,} bytes)")
        
        return size_bytes
    
    except Exception as e:
        print(f"❌ [{context}] 응답 크기 측정 실패: {e}")
        return 0


def log_data_breakdown(data: Dict[str, Any], context: str = "") -> None:
    """
    딕셔너리 데이터의 각 키별 크기를 분석
    
    Args:
        data: 분석할 딕셔너리
        context: 컨텍스트 정보
    """
    if not isinstance(data, dict):
        print(f"⚠️ [{context}] data는 dict 타입이 아닙니다: {type(data)}")
        return
    
    print(f"\n📊 [{context}] 데이터 구성 분석:")
    total_size = 0
    
    for key, value in data.items():
        try:
            value_json = json.dumps(value, ensure_ascii=False)
            size_bytes = len(value_json)
            size_kb = size_bytes / 1024
            total_size += size_bytes
            
            # 값의 타입 정보
            if isinstance(value, list):
                type_info = f"list[{len(value)}]"
            elif isinstance(value, dict):
                type_info = f"dict[{len(value)}]"
            elif isinstance(value, str):
                type_info = f"str[{len(value)}]"
            else:
                type_info = type(value).__name__
            
            # 크기가 큰 필드만 출력
            if size_kb > 10:
                print(f"   '{key}': {size_kb:.2f} KB ({type_info})")
                if size_kb > 100:
                    print(f"      ⚠️ 큰 필드 - 압축 또는 페이징 고려")
        
        except Exception as e:
            print(f"   '{key}': 크기 측정 실패 ({e})")
    
    print(f"   === 총 크기: {total_size / 1024:.2f} KB ===\n")


def suggest_optimization(size_kb: float) -> None:
    """
    응답 크기에 따른 최적화 제안
    
    Args:
        size_kb: 응답 크기 (KB)
    """
    if size_kb > 500:
        print(f"\n💡 최적화 제안:")
        print(f"   1. 장소 설명 길이 제한 (현재 무제한 → 최대 200자)")
        print(f"   2. 블로그 리뷰 수 감소 (장소당 5개 → 3개)")
        print(f"   3. 일정별 장소 수 제한 (1일당 10개 → 8개)")
        print(f"   4. 프론트엔드 페이징 또는 무한 스크롤 도입")
        print(f"   5. 이미지 URL 대신 썸네일 URL 사용\n")

