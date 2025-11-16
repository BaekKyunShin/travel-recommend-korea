"""
동적 지역 컨텍스트 생성 서비스 (Dynamic Location Context Service)

프롬프트에서 감지된 지역에 대한 정보가 DB에 없을 경우,
실시간으로 네이버/구글/AI에서 지역 정보를 수집하여 컨텍스트를 생성합니다.

청도, 합천, 밀양 등 소도시부터 전국 어디든 자동 대응 가능.
"""

from typing import Dict, Any, List, Optional
import asyncio
import re
from datetime import datetime, timedelta

from app.services.naver_service import NaverService
from app.services.google_maps_service import GoogleMapsService
from app.services.openai_service import OpenAIService
from app.services.blog_crawler_service import BlogCrawlerService


class DynamicLocationContextService:
    """동적 지역 컨텍스트 생성기"""
    
    def __init__(self):
        self.naver_service = NaverService()
        self.google_service = GoogleMapsService()
        self.blog_crawler = BlogCrawlerService()
        # 순환 참조 방지: OpenAI 인스턴스는 필요시에만 생성
        self._openai_service = None
    
    @property
    def openai_service(self):
        """지연 로딩으로 OpenAI 서비스 초기화"""
        if self._openai_service is None:
            from openai import AsyncOpenAI
            import os
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self._openai_service = AsyncOpenAI(api_key=api_key)
        return self._openai_service
    
    async def generate_location_context(
        self, 
        location_name: str, 
        location_type: str = 'district'  # 'district', 'city', 'neighborhood'
    ) -> Dict[str, Any]:
        """
        지역명으로부터 동적 컨텍스트 생성
        
        Args:
            location_name: 지역명 (예: '청도', '밀양', '합천')
            location_type: 지역 타입
        
        Returns:
            {
                'characteristics': [...],
                'popular_times': {...},
                'target_demographics': [...],
                'price_range': 'medium',
                'cuisine_preferences': [...],
                'nearby_landmarks': [...],
                'best_for': [...],
                'atmosphere': '...',
                'lat': 위도,
                'lng': 경도,
                'generated_at': 생성 시간,
                'data_sources': [...]
            }
        """
        print(f"\n{'='*80}")
        print(f"🔍 동적 지역 컨텍스트 생성: {location_name}")
        print(f"{'='*80}")
        
        # 병렬로 다양한 소스에서 데이터 수집
        tasks = [
            self._get_location_coordinates(location_name),
            self._crawl_naver_characteristics(location_name),
            self._crawl_popular_places(location_name),
            self._infer_ai_characteristics(location_name)
        ]
        
        coords, naver_data, places_data, ai_data = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 예외 처리
        if isinstance(coords, Exception):
            print(f"⚠️ 좌표 조회 실패: {coords}")
            coords = {'lat': 35.5, 'lng': 128.5}  # 한국 중부 기본값
        
        if isinstance(naver_data, Exception):
            print(f"⚠️ 네이버 크롤링 실패: {naver_data}")
            naver_data = {}
        
        if isinstance(places_data, Exception):
            print(f"⚠️ 장소 데이터 수집 실패: {places_data}")
            places_data = {}
        
        if isinstance(ai_data, Exception):
            print(f"⚠️ AI 추론 실패: {ai_data}")
            ai_data = {}
        
        # 데이터 융합
        context = self._merge_context_data(location_name, coords, naver_data, places_data, ai_data)
        
        print(f"✅ {location_name} 컨텍스트 생성 완료")
        print(f"   특성: {', '.join(context.get('characteristics', [])[:3])}")
        print(f"   추천 음식: {', '.join(context.get('cuisine_preferences', [])[:3])}")
        print(f"   좌표: ({context.get('lat')}, {context.get('lng')})")
        
        return context
    
    async def _get_location_coordinates(self, location_name: str) -> Dict[str, float]:
        """Google Places API로 지역 중심 좌표 획득"""
        try:
            print(f"📍 좌표 조회: {location_name}")
            
            # Google Places API 사용 (get_place_details)
            search_query = f"{location_name}, 대한민국"
            place_details = await self.google_service.get_place_details(location_name, "대한민국")
            
            if place_details and 'lat' in place_details and 'lng' in place_details:
                print(f"   ✅ 좌표 획득: ({place_details['lat']}, {place_details['lng']})")
                return {'lat': place_details['lat'], 'lng': place_details['lng']}
            else:
                print(f"   ⚠️ 좌표 미발견, 기본값 사용")
                return {'lat': 35.5, 'lng': 128.5}
                
        except Exception as e:
            print(f"   ❌ 좌표 조회 오류: {e}")
            return {'lat': 35.5, 'lng': 128.5}
    
    async def _crawl_naver_characteristics(self, location_name: str) -> Dict[str, Any]:
        """네이버 검색으로 지역 특성 크롤링"""
        try:
            print(f"🔍 네이버 크롤링: {location_name} 특성")
            
            # 다양한 키워드로 검색
            keywords = [
                f"{location_name} 특징",
                f"{location_name} 유명한",
                f"{location_name} 관광",
                f"{location_name} 먹거리"
            ]
            
            all_results = []
            for keyword in keywords:
                # ✅ 올바른 메서드명: search_blogs (복수형!)
                results = await self.naver_service.search_blogs(keyword, display=5)
                if results:
                    all_results.extend(results)
            
            # 블로그 내용 분석
            characteristics = self._extract_characteristics_from_blogs(all_results)
            
            print(f"   ✅ 특성 추출: {len(characteristics)}개")
            return {
                'raw_blogs': all_results,
                'characteristics': characteristics
            }
            
        except Exception as e:
            print(f"   ❌ 네이버 크롤링 오류: {e}")
            return {}
    
    async def _crawl_popular_places(self, location_name: str) -> Dict[str, Any]:
        """인기 장소 및 POI 크롤링"""
        try:
            print(f"🏢 인기 장소 크롤링: {location_name}")
            
            # 네이버 지역 검색
            place_keywords = [
                f"{location_name} 맛집",
                f"{location_name} 카페",
                f"{location_name} 관광지"
            ]
            
            places = []
            for keyword in place_keywords:
                # ✅ 올바른 메서드명: search_places!
                results = await self.naver_service.search_places(keyword, display=10)
                if results:
                    places.extend(results)
            
            # 음식 카테고리 추출
            cuisine_types = self._extract_cuisine_types(places)
            
            print(f"   ✅ 장소 수집: {len(places)}개, 음식 종류: {len(cuisine_types)}개")
            return {
                'places': places,
                'cuisine_types': cuisine_types
            }
            
        except Exception as e:
            print(f"   ❌ 장소 크롤링 오류: {e}")
            return {}
    
    async def _infer_ai_characteristics(self, location_name: str) -> Dict[str, Any]:
        """GPT-4로 지역 특성 추론"""
        try:
            if not self.openai_service:
                print(f"   ⚠️ OpenAI API 키 없음, AI 추론 스킵")
                return {}
            
            print(f"🤖 AI 특성 추론: {location_name}")
            
            prompt = f"""
{location_name}은 대한민국의 어떤 지역인가요? 다음 정보를 JSON 형식으로 제공해주세요:

{{
    "region_type": "도시/군/구/동 등 지역 타입",
    "province": "광역시/도",
    "known_for": ["대표 특징 1", "대표 특징 2", "대표 특징 3"],
    "tourist_attractions": ["관광명소 1", "관광명소 2"],
    "local_food": ["특산물/음식 1", "특산물/음식 2"],
    "atmosphere": "지역 분위기 (예: 전통적, 현대적, 자연친화적)",
    "target_visitors": ["주요 방문객 유형 1", "주요 방문객 유형 2"],
    "best_season": "방문 최적 시기",
    "price_level": "low/medium/high"
}}

실제 정보만 제공하고, 확실하지 않으면 빈 배열로 응답하세요.
"""
            
            response = await self.openai_service.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "당신은 한국 지리 및 관광 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # GPT-4 지원
                max_completion_tokens=500
            )
            
            content = response.choices[0].message.content
            
            # JSON 추출
            import json
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                ai_info = json.loads(json_match.group(0))
                print(f"   ✅ AI 추론 완료: {ai_info.get('region_type', 'N/A')}")
                return ai_info
            else:
                print(f"   ⚠️ AI 응답 파싱 실패")
                return {}
            
        except Exception as e:
            print(f"   ❌ AI 추론 오류: {e}")
            return {}
    
    def _extract_characteristics_from_blogs(self, blog_items: List[Dict]) -> List[str]:
        """블로그 내용에서 특성 키워드 추출"""
        characteristics = []
        
        # 빈 리스트 체크
        if not blog_items:
            return []
        
        # 빈도 분석을 위한 키워드 카운터
        keyword_counts = {}
        
        for blog in blog_items[:20]:  # 최대 20개 블로그 분석
            # dict 또는 객체 모두 처리
            if isinstance(blog, dict):
                title = blog.get('title', '')
                description = blog.get('description', '')
            else:
                title = getattr(blog, 'title', '')
                description = getattr(blog, 'description', '')
            
            # HTML 태그 제거
            title = re.sub(r'<[^>]+>', '', str(title))
            description = re.sub(r'<[^>]+>', '', str(description))
            
            combined_text = title + ' ' + description
            
            # 특성 키워드 패턴 매칭
            patterns = [
                r'(유명|맛집|핫플|인기|추천)',
                r'(전통|역사|문화|축제)',
                r'(자연|경치|풍경|산|강|바다)',
                r'(체험|활동|레저)',
                r'(카페|디저트|빵집)',
                r'(숙박|호텔|펜션)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, combined_text)
                for match in matches:
                    keyword_counts[match] = keyword_counts.get(match, 0) + 1
        
        # 빈도 높은 상위 키워드 선택
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        characteristics = [keyword for keyword, count in sorted_keywords[:10]]
        
        return characteristics
    
    def _extract_cuisine_types(self, places: List[Dict]) -> List[str]:
        """장소 데이터에서 음식 카테고리 추출"""
        cuisine_types = set()
        
        # 빈 리스트 체크
        if not places:
            return []
        
        for place in places:
            # dict 또는 객체 모두 처리
            if isinstance(place, dict):
                category = place.get('category', '')
                title = place.get('title', '')
            else:
                category = getattr(place, 'category', '')
                title = getattr(place, 'title', '')
            
            # 카테고리 파싱 (예: "음식점>한식>육류,고기")
            if '음식점' in str(category):
                parts = str(category).split('>')
                if len(parts) > 1:
                    cuisine_types.add(parts[1].strip())
            
            # 타이틀에서 음식 종류 추출
            # HTML 태그 제거
            title_clean = re.sub(r'<[^>]+>', '', str(title))
            
            food_keywords = ['한식', '중식', '일식', '양식', '카페', '디저트', '빵', '고기', '해산물', '치킨']
            for keyword in food_keywords:
                if keyword in title_clean:
                    cuisine_types.add(keyword)
        
        return list(cuisine_types)
    
    def _merge_context_data(
        self,
        location_name: str,
        coords: Dict,
        naver_data: Dict,
        places_data: Dict,
        ai_data: Dict
    ) -> Dict[str, Any]:
        """다양한 소스의 데이터를 하나의 컨텍스트로 융합"""
        
        # 특성 통합
        characteristics = []
        if naver_data.get('characteristics'):
            characteristics.extend(naver_data['characteristics'][:5])
        if ai_data.get('known_for'):
            characteristics.extend(ai_data['known_for'][:3])
        
        # 중복 제거
        characteristics = list(set(characteristics))[:10]
        
        # 음식 종류 통합
        cuisine_preferences = places_data.get('cuisine_types', [])
        if ai_data.get('local_food'):
            cuisine_preferences.extend(ai_data['local_food'])
        cuisine_preferences = list(set(cuisine_preferences))[:8]
        
        # 타겟 방문객
        target_demographics = ai_data.get('target_visitors', ['관광객', '가족', '커플'])
        
        # 가격대
        price_range = ai_data.get('price_level', 'medium')
        
        # 분위기
        atmosphere = ai_data.get('atmosphere', 'local_charm')
        
        # 인근 랜드마크 (구글 Places로부터)
        nearby_landmarks = []
        if coords.get('lat') and coords.get('lng'):
            # 주요 POI 3개 정도 추가
            for place in places_data.get('places', [])[:3]:
                nearby_landmarks.append({
                    'name': place.get('title', '').replace('<b>', '').replace('</b>', ''),
                    'lat': coords.get('lat', 35.5),
                    'lng': coords.get('lng', 128.5),
                    'type': 'poi'
                })
        
        # 최적 활동
        best_for = ai_data.get('tourist_attractions', [])[:5]
        if not best_for:
            best_for = ['관광', '맛집 탐방', '휴식']
        
        context = {
            'characteristics': characteristics,
            'popular_times': {
                '점심': '12:00-13:30',
                '저녁': '18:00-20:00'
            },
            'target_demographics': target_demographics,
            'price_range': price_range,
            'cuisine_preferences': cuisine_preferences,
            'nearby_landmarks': nearby_landmarks,
            'best_for': best_for,
            'atmosphere': atmosphere,
            'lat': coords.get('lat', 35.5),
            'lng': coords.get('lng', 128.5),
            'generated_at': datetime.now().isoformat(),
            'data_sources': ['naver', 'google', 'ai'],
            'cache_until': (datetime.now() + timedelta(days=30)).isoformat()
        }
        
        return context

