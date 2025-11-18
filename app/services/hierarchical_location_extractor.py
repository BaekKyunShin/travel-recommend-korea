"""
계층적 지역 추출기 (Hierarchical Location Extractor)

사용자 프롬프트에서 시 > 구 > 동 > POI 계층 구조를 추출하여
지역 특정성을 최대한 보존합니다.

🆕 지능형 확장: 고정 DB에 없는 지역은 AI+Google로 자동 학습
"""

from typing import Dict, Any, List, Tuple, Optional
import re
import asyncio


class HierarchicalLocationExtractor:
    """프롬프트에서 계층적 지역 정보 추출 (정적 DB + 동적 학습)"""
    
    def __init__(self):
        # 지능형 해석기 lazy loading
        self._intelligent_resolver = None
    
    @property
    def intelligent_resolver(self):
        """지연 로딩으로 IntelligentLocationResolver 초기화"""
        if self._intelligent_resolver is None:
            from app.services.intelligent_location_resolver import get_intelligent_resolver
            self._intelligent_resolver = get_intelligent_resolver()
        return self._intelligent_resolver
    
    async def _extract_city_with_ai(self, prompt: str) -> Optional[str]:
        """
        AI를 활용하여 프롬프트에서 도시명 추출 (Redis 캐싱 적용)
        
        예: "전남 순천에서 맛집" → "순천"
            "경상남도 거창 여행" → "거창"
            "강원도 양양 서핑" → "양양"
        
        Returns:
            추출된 도시명 또는 None
        """
        try:
            from openai import AsyncOpenAI
            import os
            import json
            
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                return None
            
            # 🆕 Redis 캐싱 확인
            from app.services.ai_cache_service import get_ai_cache_service
            ai_cache = get_ai_cache_service()
            
            cached_result = ai_cache.get_cached_ai_response('city_extraction', prompt)
            if cached_result:
                city = cached_result.get('city')
                lat = cached_result.get('lat')
                lng = cached_result.get('lng')
                country = cached_result.get('country')
                print(f"   ⚡ AI 도시 추출 (캐시): {city}")
                if lat and lng:
                    print(f"   ⚡ AI 좌표 (캐시): ({lat}, {lng})")
                # ✅ dict 전체를 반환 (호출하는 곳에서 dict를 기대함)
                return cached_result
            
            client = AsyncOpenAI(api_key=api_key)
            
            extraction_prompt = f"""🌍 다음 문장에서 여행 목적지의 "도시명"과 "정확한 좌표"를 추출하세요.

문장: "{prompt}"

규칙:
- "~에서" 뒤에 나오는 지명이 목적지입니다
- **전세계 모든 도시 지원** (일본, 프랑스, 미국, 한국 등)
- 유명 도시의 정확한 중심 좌표를 제공하세요
- 동명이인 도시가 있으면 더 유명한 곳을 선택하세요
- "출발지"가 아닌 "목적지"를 추출

JSON만 응답하세요:
{{"city": "도시명", "lat": 위도, "lng": 경도, "country": "국가명"}}

예시:
- "교토에서" → {{"city": "교토", "lat": 35.0116, "lng": 135.7681, "country": "일본"}}
- "도쿄 시부야" → {{"city": "도쿄", "lat": 35.6762, "lng": 139.6503, "country": "일본"}}
- "파리 에펠탑" → {{"city": "파리", "lat": 48.8566, "lng": 2.3522, "country": "프랑스"}}
- "순천 맛집" → {{"city": "순천", "lat": 34.9506, "lng": 127.4872, "country": "대한민국"}}"""
            
            print(f"   🔄 GPT-5 API 호출 중...")
            print(f"   📤 요청 모델: gpt-5")
            print(f"   📤 분석 대상 문장: '{prompt}'")
            print(f"   📤 요청 프롬프트 길이: {len(extraction_prompt)} 문자")
            
            try:
                response = await client.chat.completions.create(
                    model="gpt-5",
                    messages=[
                        {"role": "system", "content": "당신은 전세계 지명 추출 및 좌표 분석 전문가입니다."},
                        {"role": "user", "content": extraction_prompt}
                    ],
                    max_completion_tokens=10000
                )
                
                print(f"   ✅ OpenAI API 호출 성공")
                
                # 전체 응답 객체 확인
                print(f"   🔍 전체 응답 타입: {type(response)}")
                print(f"   🔍 응답 속성: {dir(response)[:10]}")  # 처음 10개만
                
                # 응답 구조 상세 분석
                print(f"   📊 response.id: {response.id if hasattr(response, 'id') else 'N/A'}")
                print(f"   📊 response.model: {response.model if hasattr(response, 'model') else 'N/A'}")
                print(f"   📊 response.choices 존재: {hasattr(response, 'choices')}")
                
                if hasattr(response, 'choices'):
                    print(f"   📊 choices 개수: {len(response.choices)}")
                    
                    if len(response.choices) > 0:
                        choice = response.choices[0]
                        print(f"   📊 choice[0] 타입: {type(choice)}")
                        print(f"   📊 choice[0].finish_reason: {choice.finish_reason if hasattr(choice, 'finish_reason') else 'N/A'}")
                        print(f"   📊 choice[0].message 존재: {hasattr(choice, 'message')}")
                        
                        if hasattr(choice, 'message'):
                            message = choice.message
                            print(f"   📊 message 타입: {type(message)}")
                            print(f"   📊 message.content 존재: {hasattr(message, 'content')}")
                            print(f"   📊 message.content 타입: {type(message.content) if hasattr(message, 'content') else 'N/A'}")
                            print(f"   📊 message.content 값: {repr(message.content) if hasattr(message, 'content') else 'N/A'}")
                    else:
                        print(f"   ⚠️ choices 배열이 비어있음")
                        return None
                else:
                    print(f"   ❌ response에 choices 속성 없음")
                    return None
                
                raw_content = response.choices[0].message.content
                
                print(f"   📏 content 길이: {len(raw_content) if raw_content else 0} 문자")
                
                if not raw_content or not raw_content.strip():
                    print(f"   ⚠️ GPT-5 빈 응답 반환")
                    print(f"   🔍 content is None: {raw_content is None}")
                    print(f"   🔍 content == '': {raw_content == ''}")
                    return None
                    
            except Exception as api_error:
                print(f"   ❌ OpenAI API 호출 실패!")
                print(f"   ❌ 에러 타입: {type(api_error).__name__}")
                print(f"   ❌ 에러 메시지: {str(api_error)}")
                return None
            
            print(f"   📥 원본 GPT-5 응답: {raw_content[:200]}")
            
            # JSON 추출 (마크다운 코드 블록 제거)
            import re
            
            content = raw_content.strip()
            
            # 마크다운 코드 블록 제거
            content = re.sub(r'```json\s*', '', content)
            content = re.sub(r'```\s*', '', content)
            content = content.strip()
            
            # JSON 객체 추출 시도 (여러 패턴)
            json_patterns = [
                r'\{[^{}]*"city"[^{}]*"lat"[^{}]*"lng"[^{}]*\}',  # city + lat + lng
                r'\{[^{}]*"city"[^{}]*\}',  # 단순 패턴 (fallback)
                r'\{\s*"city"\s*:\s*"[^"]*"\s*\}',  # 엄격한 패턴 (fallback)
            ]
            
            json_match = None
            for pattern in json_patterns:
                json_match = re.search(pattern, content, re.DOTALL)
                if json_match:
                    content = json_match.group(0).strip()
                    print(f"   🔍 JSON 추출 성공 (패턴 매칭)")
                    break
            
            if not json_match:
                print(f"   ⚠️ JSON 패턴 매칭 실패")
                print(f"   정제된 내용: {content[:200]}")
                return None
            
            print(f"   📤 정제된 JSON: {content[:200]}")
            
            try:
                result = json.loads(content)
                
                city = result.get('city')
                lat = result.get('lat')
                lng = result.get('lng')
                country = result.get('country')
                
                if city and city != 'null' and city.lower() != 'null':
                    print(f"   🤖 AI 도시 추출 성공: {city}")
                    if lat and lng:
                        print(f"   🌍 AI 좌표 추출 성공: ({lat}, {lng})")
                        if country:
                            print(f"   🌍 국가: {country}")
                    # Redis에 캐싱
                    ai_cache.save_ai_response('city_extraction', prompt, result)
                    return result  # 🆕 딕셔너리 전체 반환
                else:
                    print(f"   ℹ️ AI 응답: city={city} (null 또는 빈값)")
                    return None
            except json.JSONDecodeError as e:
                print(f"   ⚠️ JSON 파싱 실패: {e}")
                print(f"   시도한 파싱: {content}")
                return None
                
        except Exception as e:
            print(f"   ⚠️ AI 도시 추출 실패: {type(e).__name__}: {e}")
            import traceback
            print(f"   스택 트레이스:\n{traceback.format_exc()}")
            return None
    
    # ✨ 정적 데이터 완전 제거 - AI + Google Maps가 동적으로 처리
    # GPT-5가 모든 도시를 이해하고, Google Geocoding이 좌표를 제공하므로 불필요
    KOREAN_LOCATIONS = {
        # 빈 딕셔너리 (호환성 유지용)
        # AI가 전국 모든 도시를 동적으로 처리합니다
    }
    
    # 원래 여기 519줄의 하드코딩 데이터가 있었지만 제거됨
    # 이유: GPT-5 + Google Geocoding으로 무한 확장 가능
    
    # ✨ POI와 컨텍스트도 AI가 자동 처리 (하드코딩 불필요)
    # Google Places가 "강남역 근처 맛집" 검색 자동 처리
    # GPT-5가 "직장인 점심" 같은 컨텍스트 자동 이해
    
    POI_KEYWORDS = {  # 빈 딕셔너리 (호환성)
    }
    
    CONTEXT_PATTERNS = {  # 빈 딕셔너리 (호환성)
    }
    
    
    # # 컨텍스트 키워드 패턴
    # CONTEXT_PATTERNS = {
    #     '시간대': {
    #         '아침': ['아침', '모닝', '조식', '브런치'],
    #         '점심': ['점심', '런치', '중식', '낮'],
    #         '저녁': ['저녁', '디너', '석식'],
    #         '야식': ['야식', '밤', '심야', '새벽']
    #     },
    #     '타겟': {
    #         '직장인': ['직장인', '회사원', '오피스', '워커', 'IT', '업무', '비즈니스'],
    #         '학생': ['학생', '대학생', '고등학생', '청소년'],
    #         '가족': ['가족', '아이', '어린이', '유아', '키즈'],
    #         '데이트': ['데이트', '연인', '커플', '애인'],
    #         '혼자': ['혼자', '혼밥', '혼술', '1인']
    #     },
    #     '목적': {
    #         '회의': ['회의', '미팅', '세미나', '컨퍼런스'],
    #         '모임': ['모임', '약속', '술자리', '회식'],
    #         '산책': ['산책', '걷기', '조깅', '운동'],
    #         '쇼핑': ['쇼핑', '구경', '구매']
    #     }
    # }
    
    async def extract_location_hierarchy(self, prompt: str) -> Dict[str, Any]:
        """
        프롬프트에서 계층적 지역 정보 추출
        
        Args:
            prompt: 사용자 프롬프트 (예: "서울 마곡 LG사이언스파크 근처 IT 직장인 점심 맛집")
        
        Returns:
            {
                'city': '서울',
                'district': '강서구',
                'neighborhood': '마곡동',
                'poi': ['LG사이언스파크', '마곡나루역'],
                'context': {
                    '시간대': ['점심'],
                    '타겟': ['직장인', 'IT'],
                    '목적': []
                },
                'search_radius_km': 1.0,
                'lat': 37.5614,
                'lng': 126.8279,
                'location_specificity': 'high'  # high/medium/low
            }
        """
        result = {
            'country': None,  # 🌍 글로벌: 국가 (예: South Korea, Japan, France)
            'state': None,    # 🌍 글로벌: 주/도 (예: 강원도, California, Île-de-France)
            'city': None,
            'district': None,
            'neighborhood': None,
            'poi': [],
            'context': {
                '시간대': [],
                '타겟': [],
                '목적': []
            },
            'search_radius_km': 3.0,  # 기본값: 도시 레벨
            'lat': None,
            'lng': None,
            'location_specificity': 'low'
        }
        
        # 🆕 1. 출발지 제거: "출발지: XXX에서 시작하여" 한 덩어리로 제거
        cleaned_prompt = prompt
        
        # ⚠️ CRITICAL: "출발지: ... 에서 시작하여"를 한 번에 제거해야 "청도에서"를 보존
        # "출발지: 대한민국 인천광역시에서 시작하여" → 한 번에 제거
        # "청도에서" → 유지!
        start_location_pattern = r'출발지\s*[:：]\s*[^청]+?에서\s+시작하여\s*'
        
        before = cleaned_prompt
        cleaned_prompt = re.sub(start_location_pattern, '', cleaned_prompt, flags=re.IGNORECASE)
        
        if before != cleaned_prompt:
            removed = before.replace(cleaned_prompt, '***REMOVED***')
            print(f"   🗑️ 출발지 제거: {removed[:150]}")
        
        print(f"🧹 출발지 제거 후 프롬프트: '{cleaned_prompt}'")
        
        # 🌍 AI로 도시 + 좌표 추출 (GPT-5가 전세계 도시를 이해함)
        print(f"\n   🤖 AI로 도시 + 좌표 추출 시도 중...")
        ai_extracted_data = await self._extract_city_with_ai(cleaned_prompt)
        
        if ai_extracted_data and isinstance(ai_extracted_data, dict):
            result['city'] = ai_extracted_data.get('city')
            ai_lat = ai_extracted_data.get('lat')
            ai_lng = ai_extracted_data.get('lng')
            ai_country = ai_extracted_data.get('country')
            
            if result['city']:
                print(f"✅ AI가 도시 추출 성공: '{result['city']}'")
                if ai_country:
                    print(f"   🌍 국가: {ai_country}")
                
                # 🆕 AI 좌표가 있으면 저장 (나중에 우선 사용)
                if ai_lat and ai_lng:
                    result['ai_lat'] = ai_lat
                    result['ai_lng'] = ai_lng
                    print(f"   ✅ AI 좌표 저장: ({ai_lat}, {ai_lng})")
                    print(f"   💡 AI 좌표를 Google Geocoding보다 우선 사용합니다!")
        else:
            print(f"   ❌ AI 도시 추출 실패 - 사용자에게 명확한 입력 요청 필요")
            result['city'] = None  # ✅ 기본값 대신 None 반환
        
        # ✨ 정적 DB 제거로 인한 단순화
        # AI가 추출한 도시를 그대로 사용 (동/구 구분 불필요)
        # Google Places가 알아서 해당 지역 장소를 찾아줌
        
        if result['city']:
            result['search_radius_km'] = 5.0  # 도시 레벨: 넓은 반경
            result['location_specificity'] = 'medium'
            print(f"✅ AI 추출 도시 사용: '{result['city']}' (반경 5km)")
        
        # ✨ POI와 컨텍스트 추출 제거
        # Google Places가 "강남역 근처" 자동 처리
        # GPT-5가 "직장인 점심" 같은 컨텍스트 자동 이해
        # 하드코딩 불필요!
        
        # 6. 좌표 변환 (AI 좌표 우선, 없으면 Google Geocoding)
        if result.get('ai_lat') and result.get('ai_lng'):
            # 🆕 AI 좌표가 있으면 우선 사용
            result['lat'] = result['ai_lat']
            result['lng'] = result['ai_lng']
            print(f"\n✅ AI 좌표 사용: ({result['lat']}, {result['lng']})")
            # 임시 키 제거
            del result['ai_lat']
            del result['ai_lng']
        else:
            # AI 좌표가 없으면 Google Geocoding 사용 (기존 로직)
            print(f"\n⚠️ AI 좌표 없음, Google Geocoding 사용")
            result['lat'], result['lng'] = await self._get_coordinates(
                result['city'], 
                result['district'], 
                result['neighborhood'],
                result['poi']
            )
        
        # 7. 검색 쿼리 생성용 텍스트
        result['location_text'] = self._build_location_text(result)
        
        print(f"\n📍 지역 계층 추출 결과:")
        print(f"   도시: {result['city']}")
        print(f"   구: {result['district']}")
        print(f"   동: {result['neighborhood']}")
        print(f"   POI: {result['poi']}")
        print(f"   컨텍스트: {result['context']}")
        print(f"   검색 반경: {result['search_radius_km']}km")
        print(f"   위치 정밀도: {result['location_specificity']}")
        print(f"   좌표: ({result['lat']}, {result['lng']})")
        
        return result
  

    async def _get_coordinates(
        self, 
        city: Optional[str], 
        district: Optional[str], 
        neighborhood: Optional[str],
        pois: List[str]
    ) -> Tuple[float, float]:
        """
        ✨ Google Geocoding만 사용하여 좌표 조회
        하드코딩 완전 제거로 전국 무한 지원
        
        Args:
            city: 도시명 (예: 부평, 천안, 밀양)
            district, neighborhood, pois: 무시 (AI가 이미 최적 도시 추출)
        
        Returns:
            (위도, 경도) 튜플
        """
        if not city:
            print(f"⚠️ 도시 없음, 기본 좌표 반환 (서울)")
            return (37.5665, 126.9780)  # 서울 기본 좌표
        
        print(f"   🌍 Google Geocoding으로 '{city}' 좌표 조회 중...")
        
        try:
            # Google Maps Geocoding API 호출
            from app.services.google_maps_service import GoogleMapsService
            google_service = GoogleMapsService()
            
            # 한국 지역으로 한정하여 검색
            location_text = f"{city}, 대한민국"
            result = await google_service.geocode(location_text)
            
            if result and 'lat' in result and 'lng' in result:
                lat, lng = result['lat'], result['lng']
                print(f"   ✅ Google Geocoding 성공: ({lat:.4f}, {lng:.4f})")
                return (lat, lng)
            else:
                print(f"   ⚠️ Google Geocoding 실패 → 기본 좌표")
                return "⚠️ Google Geocoding 실패"
                
        except Exception as e:
            print(f"   ❌ Geocoding 에러: {e}")
            return "❌ Geocoding 에러"


    def _build_location_text(self, location_hierarchy: Dict) -> str:
        """검색 쿼리용 위치 텍스트 생성"""
        parts = []
        
        if location_hierarchy['city']:
            parts.append(location_hierarchy['city'])
        
        if location_hierarchy['district']:
            parts.append(location_hierarchy['district'])
        
        if location_hierarchy['neighborhood']:
            parts.append(location_hierarchy['neighborhood'])
        
        if location_hierarchy['poi']:
            parts.extend(location_hierarchy['poi'][:2])  # 최대 2개 POI
        
        return ' '.join(parts)

