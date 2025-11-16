"""
지능형 지역 해석기 (Intelligent Location Resolver)

🧠 Zero-Knowledge 접근: 어떤 지역이든 자동으로 학습하여 처리

OpenAI + Google Geocoding + Wikipedia를 조합하여
전 세계 모든 지역의 좌표와 컨텍스트를 자동으로 수집합니다.

예시:
- "양양 서피비치" → 강원도 양양군 (38.0752, 128.6189)
- "합천 해인사" → 경상남도 합천군 (35.5667, 128.1657)
- "제천 의림지" → 충청북도 제천시 (37.1326, 128.1907)
"""

from typing import Dict, Any, Tuple, Optional
import asyncio
import json
import re
from openai import AsyncOpenAI
import os


class IntelligentLocationResolver:
    """AI 기반 지능형 지역 해석기"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
        
        # 학습 캐시 (런타임 메모리)
        self.learned_locations = {}
    
    async def resolve_location(
        self, 
        location_name: str,
        context_hint: str = ""  # "맛집", "관광", "숙박" 등 힌트
    ) -> Dict[str, Any]:
        """
        지역명을 지능적으로 해석하여 좌표 + 컨텍스트 반환
        
        Args:
            location_name: 지역명 (예: "양양", "제천", "청도")
            context_hint: 사용자 요청 컨텍스트 힌트
        
        Returns:
            {
                'location_name': '양양',
                'full_name': '강원도 양양군',
                'province': '강원도',
                'region_type': '군',
                'lat': 38.0752,
                'lng': 128.6189,
                'characteristics': ['서핑', '해변', '설악산'],
                'famous_for': ['낙산사', '하조대', '서피비치'],
                'local_cuisine': ['물회', '오징어순대', '막국수'],
                'tourist_type': ['해양레저', '자연관광', '서핑'],
                'confidence': 0.95,  # 신뢰도
                'data_source': 'openai+google',
                'learned_at': '2025-10-31T...'
            }
        """
        print(f"\n{'='*80}")
        print(f"🧠 지능형 지역 해석: '{location_name}'")
        print(f"{'='*80}")
        
        # 1. 캐시 확인
        if location_name in self.learned_locations:
            print(f"   ✅ 학습 캐시 히트: {location_name}")
            return self.learned_locations[location_name]
        
        # 2. AI로 지역 정보 추론 (병렬 처리)
        tasks = [
            self._ask_openai_location_info(location_name, context_hint),
            self._get_coordinates_from_google(location_name)
        ]
        
        ai_result, google_coords = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        if isinstance(ai_result, Exception):
            print(f"   ⚠️ AI 추론 실패: {ai_result}")
            ai_result = {}
        
        if isinstance(google_coords, Exception):
            print(f"   ⚠️ Google 좌표 실패: {google_coords}")
            google_coords = {}
        
        # 3. 데이터 융합
        location_info = self._merge_location_data(
            location_name, 
            ai_result, 
            google_coords
        )
        
        # 4. 학습 캐시 저장
        self.learned_locations[location_name] = location_info
        
        print(f"✅ {location_name} 해석 완료")
        print(f"   전체 이름: {location_info.get('full_name', 'N/A')}")
        print(f"   좌표: ({location_info.get('lat')}, {location_info.get('lng')})")
        print(f"   특징: {', '.join(location_info.get('characteristics', [])[:3])}")
        
        return location_info
    
    async def _ask_openai_location_info(
        self, 
        location_name: str,
        context_hint: str = ""
    ) -> Dict[str, Any]:
        """OpenAI에게 지역 정보 질의"""
        
        if not self.client:
            print(f"   ⚠️ OpenAI API 키 없음, AI 추론 스킵")
            return {}
        
        try:
            print(f"   🤖 OpenAI에게 '{location_name}' 정보 질의...")
            
            system_prompt = """당신은 대한민국 지리 및 관광 전문가입니다. 
지역명을 입력받으면 다음 정보를 JSON 형식으로 정확하게 제공하세요.

중요: 확실하지 않은 정보는 빈 배열로 응답하세요."""

            user_prompt = f"""
대한민국의 '{location_name}'에 대해 다음 정보를 JSON 형식으로 제공해주세요:

{{
    "full_name": "정식 행정구역명 (예: 강원도 양양군, 경상북도 청도군)",
    "province": "광역시/도 (예: 강원도, 경상북도)",
    "region_type": "시/군/구 등 행정단위",
    "characteristics": ["대표 특징 1", "대표 특징 2", "대표 특징 3"],
    "famous_for": ["유명한 장소/명소 1", "유명한 장소/명소 2", "유명한 장소/명소 3"],
    "local_cuisine": ["특산 음식/먹거리 1", "특산 음식/먹거리 2"],
    "tourist_type": ["관광 유형 (예: 해양레저, 역사문화, 자연휴양)"],
    "nearby_cities": ["인근 주요 도시"],
    "best_season": "방문 최적 시기",
    "typical_visit_duration": "평균 여행 기간 (예: 당일치기, 1박2일)"
}}

{f'사용자 요청 맥락: {context_hint}' if context_hint else ''}

**중요:** 
1. 실제로 존재하는 정보만 제공
2. 확실하지 않으면 빈 배열 []
3. 유명하지 않은 소도시도 정확히 분석
4. JSON만 출력 (설명 없이)
"""
            
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # 낮은 온도로 정확성 향상 (GPT-4 지원)
                max_completion_tokens=800
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON 추출
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                ai_info = json.loads(json_match.group(0))
                print(f"   ✅ AI 정보 획득: {ai_info.get('full_name', 'N/A')}")
                return ai_info
            else:
                print(f"   ⚠️ AI 응답 JSON 파싱 실패")
                return {}
                
        except Exception as e:
            print(f"   ❌ OpenAI 질의 오류: {e}")
            return {}
    
    async def _get_coordinates_from_google(self, location_name: str) -> Dict[str, float]:
        """Google Geocoding API로 정확한 좌표 획득"""
        try:
            print(f"   🗺️ Google Geocoding: '{location_name}, 대한민국'")
            
            # Google Maps Geocoding API 직접 호출
            import aiohttp
            from app.services.ssl_helper import create_http_session
            
            api_key = os.getenv("GOOGLE_MAPS_API_KEY")
            if not api_key:
                print(f"   ⚠️ Google API 키 없음")
                return {}
            
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': f"{location_name}, 대한민국",
                'key': api_key,
                'language': 'ko',
                'region': 'kr'
            }
            
            async with create_http_session() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        
                        if data['status'] == 'OK' and data['results']:
                            location = data['results'][0]['geometry']['location']
                            lat = location['lat']
                            lng = location['lng']
                            
                            # 주소 구성 요소 추출
                            address_components = data['results'][0].get('address_components', [])
                            formatted_address = data['results'][0].get('formatted_address', '')
                            
                            print(f"   ✅ 좌표 획득: ({lat}, {lng})")
                            print(f"   주소: {formatted_address}")
                            
                            return {
                                'lat': lat,
                                'lng': lng,
                                'formatted_address': formatted_address,
                                'address_components': address_components
                            }
                        else:
                            print(f"   ⚠️ Geocoding 실패: {data.get('status')}")
                            return {}
                    else:
                        print(f"   ⚠️ Google API 응답 오류: {response.status}")
                        return {}
                        
        except Exception as e:
            print(f"   ❌ Geocoding 오류: {e}")
            return {}
    
    def _merge_location_data(
        self,
        location_name: str,
        ai_result: Dict[str, Any],
        google_coords: Dict[str, Any]
    ) -> Dict[str, Any]:
        """AI 정보 + Google 좌표 융합"""
        
        from datetime import datetime
        
        # 좌표 우선순위: Google > AI 추정
        lat = google_coords.get('lat', 35.5)
        lng = google_coords.get('lng', 128.5)
        
        # AI 정보 우선 사용
        full_name = ai_result.get('full_name', location_name)
        province = ai_result.get('province', '')
        
        # Google 주소로 보완
        if not province and google_coords.get('formatted_address'):
            address = google_coords['formatted_address']
            # "강원도 양양군" 같은 패턴 추출
            province_match = re.search(r'([\w]+(?:도|특별시|광역시))', address)
            if province_match:
                province = province_match.group(1)
        
        merged_data = {
            'location_name': location_name,
            'full_name': full_name,
            'province': province,
            'region_type': ai_result.get('region_type', '시/군'),
            'lat': lat,
            'lng': lng,
            'characteristics': ai_result.get('characteristics', []),
            'famous_for': ai_result.get('famous_for', []),
            'local_cuisine': ai_result.get('local_cuisine', []),
            'tourist_type': ai_result.get('tourist_type', []),
            'nearby_cities': ai_result.get('nearby_cities', []),
            'best_season': ai_result.get('best_season', '사계절'),
            'typical_visit_duration': ai_result.get('typical_visit_duration', '1박2일'),
            'confidence': self._calculate_confidence(ai_result, google_coords),
            'data_source': 'openai+google',
            'learned_at': datetime.now().isoformat(),
            'google_address': google_coords.get('formatted_address', ''),
            'visit_count': 1  # 방문 빈도 추적
        }
        
        return merged_data
    
    def _calculate_confidence(self, ai_result: Dict, google_coords: Dict) -> float:
        """데이터 신뢰도 계산 (0-1)"""
        confidence = 0.0
        
        # Google 좌표 있으면 +0.5
        if google_coords.get('lat') and google_coords.get('lng'):
            confidence += 0.5
        
        # AI 정보 풍부도
        if ai_result.get('full_name'):
            confidence += 0.1
        if ai_result.get('famous_for'):
            confidence += 0.1
        if ai_result.get('local_cuisine'):
            confidence += 0.1
        if ai_result.get('characteristics'):
            confidence += 0.1
        if ai_result.get('province'):
            confidence += 0.1
        
        return min(confidence, 1.0)
    
    async def batch_resolve_locations(
        self, 
        location_names: list[str]
    ) -> Dict[str, Dict[str, Any]]:
        """여러 지역을 병렬로 해석"""
        print(f"🔄 배치 지역 해석 시작: {len(location_names)}개")
        
        tasks = [self.resolve_location(name) for name in location_names]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        resolved = {}
        for name, result in zip(location_names, results):
            if isinstance(result, Exception):
                print(f"   ❌ {name} 실패: {result}")
            else:
                resolved[name] = result
        
        print(f"✅ 배치 해석 완료: {len(resolved)}개 성공")
        return resolved
    
    def get_visit_statistics(self) -> Dict[str, Any]:
        """학습된 지역 통계"""
        sorted_by_visits = sorted(
            self.learned_locations.items(),
            key=lambda x: x[1].get('visit_count', 0),
            reverse=True
        )
        
        return {
            'total_learned': len(self.learned_locations),
            'top_10_visited': [
                {
                    'name': name,
                    'visits': info.get('visit_count', 0),
                    'province': info.get('province', 'N/A')
                }
                for name, info in sorted_by_visits[:10]
            ]
        }
    
    def increment_visit(self, location_name: str):
        """지역 방문 횟수 증가"""
        if location_name in self.learned_locations:
            self.learned_locations[location_name]['visit_count'] += 1


# 싱글톤 인스턴스
_resolver_instance = None

def get_intelligent_resolver() -> IntelligentLocationResolver:
    """전역 싱글톤 인스턴스 반환"""
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = IntelligentLocationResolver()
    return _resolver_instance

