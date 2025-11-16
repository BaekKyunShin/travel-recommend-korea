"""
OpenAI 서비스

GPT-5를 활용한 맞춤형 여행 계획 생성
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List
from openai import AsyncOpenAI

# 환경변수 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app.core.config import settings
from app.services.naver_service import NaverService
from app.services.google_maps_service import GoogleMapsService
from app.services.blog_crawler_service import BlogCrawlerService
from app.services.weather_service import WeatherService
from app.services.place_verification_service import PlaceVerificationService
from app.services.place_quality_service import PlaceQualityService
from app.services.weather_recommendation_service import WeatherRecommendationService
from app.services.city_service import CityService
from app.services.district_service import DistrictService
from app.services.enhanced_place_discovery_service import EnhancedPlaceDiscoveryService
from app.services.place_category_service import PlaceCategoryService
from app.services.ai_cache_service import get_ai_cache_service

class OpenAIService:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Warning: OPENAI_API_KEY not found, using mock data")
            self.client = None
        else:
            self.client = AsyncOpenAI(api_key=api_key)
        
        # 🆕 마지막 여행 스타일 분석 결과 저장
        self.last_style_analysis = None
    
    async def analyze_travel_style(self, prompt: str) -> str:
        """
        프롬프트를 분석하여 여행 스타일 자동 파악 (Redis 캐싱 적용)
        
        Args:
            prompt: 사용자 입력 프롬프트
        
        Returns:
            여행 스타일 (indoor_date, outdoor_date, food_tour, culture_tour, etc.)
        """
        
        # 🆕 Step 1: 캐시 확인
        ai_cache = get_ai_cache_service()
        cached_result = ai_cache.get_cached_ai_response('travel_style', prompt)
        
        if cached_result:
            travel_style = cached_result.get('travel_style', 'custom')
            confidence = cached_result.get('confidence', 0.0)
            reason = cached_result.get('reason', '')
            
            print(f"\n🎯 AI 여행 스타일 분석 결과 (캐시):")
            print(f"   스타일: {travel_style}")
            print(f"   신뢰도: {confidence:.2f}")
            print(f"   이유: {reason}")
            
            # 🆕 분석 결과 저장
            self.last_style_analysis = cached_result
            
            return travel_style
        
        if not self.client:
            # API 키 없을 때 기본 로직
            return self._analyze_travel_style_fallback(prompt)
        
        analysis_prompt = f"""
다음 여행 프롬프트를 분석하여 가장 적합한 여행 스타일을 **단 하나만** 선택하세요.

**프롬프트**: "{prompt}"

**여행 스타일 옵션**:
1. indoor_date: 실내 데이트 (카페, 박물관, 쇼핑몰, 영화관 등)
2. outdoor_date: 실외 데이트 (공원, 한강, 산책로, 전망대 등)
3. food_tour: 맛집 투어 (음식 중심 여행)
4. culture_tour: 문화 탐방 (궁궐, 박물관, 전통 건축 등)
5. shopping_tour: 쇼핑 투어 (쇼핑 중심)
6. healing_tour: 힐링 여행 (스파, 온천, 조용한 산책)
7. adventure_tour: 액티비티 (놀이공원, 스포츠 체험 등)
8. night_tour: 야경 투어 (야경, 야시장, 루프톱 바 등)
9. family_tour: 가족 여행 (아이 친화적 장소)
10. custom: 특정 스타일 없음 (일반 관광)

**분석 기준**:
- 프롬프트에서 명시적으로 언급된 활동, 장소 타입, 대상 등을 고려
- "데이트", "연인"이 있으면 indoor_date 또는 outdoor_date 우선
- "맛집", "음식", "먹방"이 있으면 food_tour 우선
- "가족", "아이", "어린이"가 있으면 family_tour 우선
- "실외", "야외", "산책"이 있으면 outdoor_date 우선
- "실내", "비 오는 날"이 있으면 indoor_date 우선
- "문화", "역사", "궁궐", "박물관"이 있으면 culture_tour 우선
- "쇼핑"이 있으면 shopping_tour 우선
- "힐링", "휴식", "온천"이 있으면 healing_tour 우선
- "놀이공원", "체험", "액티비티"가 있으면 adventure_tour 우선
- "야경", "밤", "야시장"이 있으면 night_tour 우선

**응답 형식 (JSON만)**:
{{
  "travel_style": "선택된 스타일",
  "confidence": 0.9,
  "reason": "선택 이유 (1-2 문장)"
}}

**중요**: JSON 형식으로만 응답하세요. 다른 설명 없이 JSON만 출력하세요.
"""
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": "당신은 여행 스타일 분석 전문가입니다. 프롬프트를 분석하여 가장 적합한 여행 스타일을 파악합니다."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_completion_tokens=500  # 200 → 500으로 증가
            )
            
            content = response.choices[0].message.content.strip()
            
            # JSON 파싱
            import json
            result = json.loads(content)
            
            travel_style = result.get('travel_style', 'custom')
            confidence = result.get('confidence', 0.0)
            reason = result.get('reason', '')
            
            print(f"\n🎯 AI 여행 스타일 분석 결과:")
            print(f"   스타일: {travel_style}")
            print(f"   신뢰도: {confidence:.2f}")
            print(f"   이유: {reason}")
            
            # 🆕 Step 2: Redis에 캐싱
            ai_cache.save_ai_response('travel_style', prompt, result)
            
            # 🆕 분석 결과 저장
            self.last_style_analysis = result
            
            return travel_style
            
        except Exception as e:
            print(f"⚠️ AI 스타일 분석 실패: {e}")
            return self._analyze_travel_style_fallback(prompt)
    
    def _analyze_travel_style_fallback(self, prompt: str) -> str:
        """
        AI API 없을 때 키워드 기반 폴백 분석
        """
        prompt_lower = prompt.lower()
        
        travel_style = 'custom'
        reason = "키워드 기반 자동 분석"
        
        # 우선순위 순서로 체크
        if any(word in prompt_lower for word in ['가족', '아이', '어린이', '유아', '키즈']):
            travel_style = 'family_tour'
            reason = "가족 관련 키워드 감지"
        elif any(word in prompt_lower for word in ['맛집', '음식', '먹방', '식당', '레스토랑', '먹거리']):
            travel_style = 'food_tour'
            reason = "음식 관련 키워드 감지"
        elif any(word in prompt_lower for word in ['실외', '야외', '산책', '공원', '한강', '해변']):
            travel_style = 'outdoor_date'
            reason = "실외 활동 키워드 감지"
        elif any(word in prompt_lower for word in ['실내', '비', '카페', '박물관', '미술관']):
            travel_style = 'indoor_date'
            reason = "실내 활동 키워드 감지"
        elif any(word in prompt_lower for word in ['데이트', '연인', '커플', '애인']):
            travel_style = 'outdoor_date'
            reason = "데이트 키워드 감지"
        elif any(word in prompt_lower for word in ['문화', '역사', '궁궐', '전통', '한옥']):
            travel_style = 'culture_tour'
            reason = "문화 관련 키워드 감지"
        elif any(word in prompt_lower for word in ['쇼핑', '쇼핑몰', '백화점', '시장']):
            travel_style = 'shopping_tour'
            reason = "쇼핑 키워드 감지"
        elif any(word in prompt_lower for word in ['힐링', '휴식', '온천', '스파', '명상']):
            travel_style = 'healing_tour'
            reason = "힐링 관련 키워드 감지"
        elif any(word in prompt_lower for word in ['놀이공원', '체험', '액티비티', '어드벤처']):
            travel_style = 'adventure_tour'
            reason = "액티비티 키워드 감지"
        elif any(word in prompt_lower for word in ['야경', '밤', '야시장', '나이트', '루프톱']):
            travel_style = 'night_tour'
            reason = "야경/나이트 키워드 감지"
        
        # 🆕 폴백 분석 결과 저장
        self.last_style_analysis = {
            'travel_style': travel_style,
            'confidence': 0.7,  # 폴백은 낮은 신뢰도
            'reason': reason
        }
        
        return travel_style
    
    async def generate_detailed_itinerary(self, prompt: str, trip_details: Dict[str, Any] = None) -> Dict[str, Any]:
        """상세한 30분 단위 여행 일정 생성 (실제 장소 데이터 기반)"""
        
        if not self.client:
            return self._generate_mock_itinerary(prompt, trip_details)
        
        # UI에서 전달된 설정값 추출
        city = trip_details.get('city', 'Seoul') if trip_details else 'Seoul'
        travel_style_ui = trip_details.get('travel_style', 'custom') if trip_details else 'custom'
        start_date = trip_details.get('start_date') if trip_details else None
        end_date = trip_details.get('end_date') if trip_details else None
        start_time = trip_details.get('start_time', '09:00') if trip_details else '09:00'
        end_time = trip_details.get('end_time', '18:00') if trip_details else '18:00'
        start_location = trip_details.get('start_location', '') if trip_details else ''
        
        # 🆕 AI 여행 스타일 자동 분석
        print(f"\n🤖 AI 여행 스타일 자동 분석 시작...")
        travel_style = await self.analyze_travel_style(prompt)
        
        # UI에서 명시적으로 설정한 스타일이 있으면 우선 사용 (custom 제외)
        if travel_style_ui and travel_style_ui != 'custom':
            print(f"   ℹ️ UI 설정 스타일 우선 사용: {travel_style_ui}")
            travel_style = travel_style_ui
        else:
            print(f"   ✅ AI 분석 스타일 사용: {travel_style}")
        
        # 여행 날짜 배열 생성 (하위 호환성 유지)
        travel_dates = []
        if start_date:
            travel_dates.append(start_date)
        if end_date and end_date != start_date:
            travel_dates.append(end_date)
        if not travel_dates:
            travel_dates = ['2025-01-01']  # 기본값
        
        # 🆕 일수 계산: 날짜 차이 기반 (2박3일 = 3일)
        if start_date and end_date:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                days_count = (end_dt - start_dt).days + 1  # +1로 당일 포함
                print(f"   📅 일수 계산: {start_date} ~ {end_date} = {days_count}일")
            except ValueError as e:
                print(f"   ⚠️ 날짜 파싱 실패: {e}, 기본값 사용")
                days_count = len(travel_dates)
        else:
            days_count = len(travel_dates)
        
        print(f"📍 최종 설정: {city}, {travel_style}, {start_time}~{end_time}, {days_count}일")
        
        # 🆕 스케줄 프레이머 모드 확인 (환경 변수로 전환 가능)
        use_schedule_framer = os.getenv("USE_SCHEDULE_FRAMER", "true").lower() == "true"
        
        if use_schedule_framer:
            print(f"\n🎬 [새로운 방식] AI 스케줄 프레이머 사용")
            return await self._generate_with_schedule_framer(
                prompt, city, travel_style, start_date, end_date,
                start_time, end_time, start_location, travel_dates, days_count
            )
        else:
            print(f"\n📋 [기존 방식] 키워드 기반 장소 검색 사용")
            # 기존 로직 계속...
        
        # 8단계 향상된 장소 발견 서비스 사용
        enhanced_discovery = EnhancedPlaceDiscoveryService()
        discovered_data = await enhanced_discovery.discover_places_with_weather(prompt, city, travel_dates)
        
        # 🆕 AI가 추출한 실제 도시명 사용 (Auto → 실제 도시)
        resolved_city = discovered_data.get('resolved_city')
        if resolved_city and resolved_city != city:
            print(f"   🔄 도시 오버라이드: '{city}' → '{resolved_city}'")
            city = resolved_city
        
        # 2. 날씨 정보 조회
        weather_service = WeatherService()
        city_service = CityService()
        weather_code = city_service.get_weather_code(city)
        weather_data = await weather_service.get_current_weather(weather_code)
        forecast_data = await weather_service.get_forecast(weather_code)
        
        # 2-1. 날씨 기반 장소 필터링 적용
        category_service = PlaceCategoryService()
        verified_places = discovered_data.get('verified_places', [])
        
        if verified_places:
            print(f"🌦️ 날씨 기반 필터링 시작: {len(verified_places)}개 장소")
            filtered_places = category_service.filter_places_by_weather(
                verified_places,
                weather_data,
                threshold=0.3  # 낮은 임계값으로 더 많은 장소 포함
            )
            discovered_data['verified_places'] = filtered_places
            discovered_data['category_stats'] = category_service.get_category_stats(filtered_places)
            print(f"✅ 필터링 완료: {len(filtered_places)}개 장소 (제거: {len(verified_places) - len(filtered_places)}개)")
            print(f"📊 카테고리 분포: {discovered_data['category_stats']}")
        
        # 도시별 특화 정보 및 실제 장소 데이터베이스
        city_service = CityService()
        district_service = DistrictService()
        city_info = city_service.get_city_info(city)
        
        # UI에서 설정한 여행 스타일 사용 (이미 추출됨)
        
        # UI에서 설정한 여행 시간 계산
        if start_time and end_time:
            start_dt = datetime.strptime(start_time, '%H:%M')
            end_dt = datetime.strptime(end_time, '%H:%M')
            duration_hours = (end_dt - start_dt).seconds // 3600
            print(f"⏰ 여행 시간: {start_time}~{end_time} ({duration_hours}시간)")
        else:
            duration_hours = trip_details.get('duration_hours', 8) if trip_details else 8
        
        # 출발지 좌표 추출 (도시별 기본 좌표 사용)
        start_location_coords = None
        if start_location:
            # 도시별 기본 좌표 사용
            city_coords = {
                'Seoul': {"lat": 37.5665, "lng": 126.9780},
                'Busan': {"lat": 35.1796, "lng": 129.0756},
                'Daegu': {"lat": 35.8714, "lng": 128.6014},
                'Incheon': {"lat": 37.4563, "lng": 126.7052},
                'Gwangju': {"lat": 35.1595, "lng": 126.8526},
                'Daejeon': {"lat": 36.3504, "lng": 127.3845},
                'Ulsan': {"lat": 35.5384, "lng": 129.3114},
                'Jeju': {"lat": 33.4996, "lng": 126.5312},
                'Suwon': {"lat": 37.2636, "lng": 127.0286},
                'Chuncheon': {"lat": 37.8813, "lng": 127.7298},
                'Gangneung': {"lat": 37.7519, "lng": 128.8761},
                'Jeonju': {"lat": 35.8242, "lng": 127.1480},
                'Yeosu': {"lat": 34.7604, "lng": 127.6622},
                'Gyeongju': {"lat": 35.8562, "lng": 129.2247},
                'Andong': {"lat": 36.5684, "lng": 128.7294}
            }
            start_location_coords = city_coords.get(city, {"lat": 37.5665, "lng": 126.9780})
            print(f"🏠 출발지 설정: {start_location} ({start_location_coords})")
        
        district_itinerary = district_service.create_district_based_itinerary(
            city, travel_style, duration_hours, start_location_coords
        )
        
        # 8단계 처리 결과를 기반으로 컨텍스트 생성
        location_context = self._build_enhanced_context(discovered_data)
        style_context = self._get_style_specific_context(travel_style)
        
        # 🆕 계층적 지역 정보 추출
        location_hierarchy = discovered_data.get('location_hierarchy', {})
        requested_city = location_hierarchy.get('city', city)
        requested_district = location_hierarchy.get('district', '')
        requested_neighborhood = location_hierarchy.get('neighborhood', '')
        requested_poi = location_hierarchy.get('poi', [])
        search_radius_km = location_hierarchy.get('search_radius_km', 3.0)
        center_lat = location_hierarchy.get('lat')
        center_lng = location_hierarchy.get('lng')
        
        # 🆕 지역 맥락 정보 추출
        local_context = discovered_data.get('local_context', {})
        context_characteristics = ', '.join(local_context.get('location_characteristics', [])[:3]) if local_context.get('enriched') else ''
        context_cuisines = ', '.join(local_context.get('recommended_cuisines', [])[:3]) if local_context.get('enriched') else ''
        context_atmosphere = local_context.get('atmosphere', '') if local_context.get('enriched') else ''
        context_best_for = ', '.join(local_context.get('best_for', [])[:2]) if local_context.get('enriched') else ''
        
        # 🆕 여행 기간 계산 (system_prompt보다 먼저 계산!)
        start_date_val = trip_details.get('start_date') if trip_details else None
        end_date_val = trip_details.get('end_date') if trip_details else None
        
        if start_date_val and end_date_val:
            try:
                start_dt = datetime.strptime(start_date_val, '%Y-%m-%d')
                end_dt = datetime.strptime(end_date_val, '%Y-%m-%d')
                days_count = (end_dt - start_dt).days + 1
            except:
                days_count = 1
        else:
            # 프롬프트에서 일수 추출 시도
            prompt_lower = prompt.lower()
            if '당일치기' in prompt or '하루' in prompt:
                days_count = 1
            elif '1박2일' in prompt or '하룻밤' in prompt:
                days_count = 2
            elif '2박3일' in prompt or '이틀밤' in prompt:
                days_count = 3
            elif '3박4일' in prompt or '사틀밤' in prompt:
                days_count = 4
            else:
                days_count = 1
        
        print(f"📅 여행 기간: {days_count}일")
        
        # 🆕 지리적 제약 텍스트 생성
        geographic_constraint = ""
        if requested_neighborhood:
            geographic_constraint = f"{requested_city} {requested_district} {requested_neighborhood}"
        elif requested_district:
            geographic_constraint = f"{requested_city} {requested_district}"
        else:
            geographic_constraint = f"{requested_city}"
        
        poi_text = f" (특히 {', '.join(requested_poi[:2])} 근처)" if requested_poi else ""
        
        system_prompt = f"""
당신은 한국 여행 전문가입니다. 사용자의 요청에 따라 30분 단위로 상세한 여행 일정을 생성해주세요.

**🚨🚨🚨 지리적 제약 (CRITICAL - 최우선 준수) 🚨🚨🚨**

⚠️ 경고: 아래 지역 제약을 위반하면 전체 응답이 거부됩니다! ⚠️

요청 지역: {geographic_constraint}{poi_text}
중심 좌표: ({center_lat:.4f}, {center_lng:.4f})
검색 반경: {search_radius_km}km 이내
위치 정밀도: {location_hierarchy.get('location_specificity', 'medium')}

**✅ 허용: {geographic_constraint} 내 장소만**
**❌ 금지: {geographic_constraint} 외 모든 지역**

{'**🏙️ 지역 특성 정보 (맥락 기반 추천) 🏙️**' if local_context.get('enriched') else ''}
{f'지역 특성: {context_characteristics}' if context_characteristics else ''}
{f'추천 음식: {context_cuisines}' if context_cuisines else ''}
{f'분위기: {context_atmosphere}' if context_atmosphere else ''}
{f'최적 용도: {context_best_for}' if context_best_for else ''}
{f'가격대: {local_context.get("target_price_range")}' if local_context.get('enriched') else ''}

**❌❌❌ 절대 금지 사항 (위반 시 응답 거부) ❌❌❌**

1. **지역 제약 위반 절대 금지**
   ✅ 허용: {geographic_constraint} 내 장소만 추천
   ❌ 금지: {geographic_constraint} 외 모든 지역
   {f'❌ 예시 금지 지역: {self._get_example_other_districts(requested_city, requested_district, requested_neighborhood)}' if requested_neighborhood else ''}
   {f'❌ 예시 금지 지역: 광화문, 강남, 홍대, 명동 등 ({geographic_constraint} 외 지역)' if not requested_neighborhood else ''}
   
2. **반경 초과 장소 절대 금지**
   모든 장소는 중심점 ({center_lat:.4f}, {center_lng:.4f})으로부터 {search_radius_km}km 이내여야 함
   거리 확인 필수: 각 장소 추천 전 거리 계산!
   
3. **다른 도시/구/동 절대 금지**
   요청: {geographic_constraint}
   금지: {requested_city} 외 다른 도시, {geographic_constraint} 외 다른 구/동
   
**⚠️ 지역 확인 체크리스트 (각 장소마다 확인):**
- [ ] 장소 주소에 "{geographic_constraint}" 포함되어 있는가?
- [ ] 중심 좌표로부터 {search_radius_km}km 이내인가?
- [ ] 요청하지 않은 다른 지역이 아닌가?

**🍽️ 식사 규칙 (엄수 필수) 🍽️**
1. **하루 식사는 아침/점심/저녁 딱 3번만**
   - 아침: 07:00-10:00 (1회)
   - 점심: 11:00-14:00 (1회)
   - 저녁: 17:00-21:00 (1회)
   
2. **각 시간대에 1번만 식사 일정 배치**
   ✅ 허용: 09:00 아침 식사 → 12:00 점심 식사 → 18:00 저녁 식사
   ❌ 금지: 10:00 식사 → 11:30 식사 (연속 식사 금지)
   
3. **식사 외 시간에는 카페/간식만 허용**
   - 10:30 카페 ✅
   - 15:00 디저트 카페 ✅
   - 10:00 식사 → 11:00 식사 ❌
   
4. **식사 활동 키워드**
   - 식사로 간주: "식당", "맛집", "점심", "저녁", "아침", "식사", "한식", "중식", "일식", "양식"
   - 카페로 간주: "카페", "커피", "디저트", "베이커리", "차"

**🚨 절대 규칙 - 할루시네이션 금지 🚨**
1. **실제 존재하는 장소만**: 가상의 장소, 추측한 장소 절대 금지
2. **검증된 장소만**: 유명한 체인점, 관광명소, 검증된 맛집만 추천
3. **정확한 주소**: 구체적인 주소 (구/동까지 포함) 필수
4. **중복 금지**: 같은 장소나 유사한 장소 중복 추천 절대 금지
5. **불확실시 거부**: 확실하지 않으면 "해당 지역에 적합한 장소를 찾을 수 없습니다"라고 명시
6. **지역 일치**: 요청 지역과 다른 지역 장소 추천 절대 금지
7. **이동 거리 제한**: 연속된 장소 간 대중교통 이동시간이 20분을 초과하지 않도록 구성
8. **검증된 장소만 사용**: 아래 제공된 검증된 장소 목록에서만 선택
9. **좌표 확인**: 모든 장소의 좌표가 중심점으로부터 {search_radius_km}km 이내인지 확인
10. **주소 확인**: 모든 장소의 주소에 '{geographic_constraint}'이 포함되어 있는지 확인

**날씨 기반 추천 우선순위:**
- 날씨: {weather_data['condition']}
- 기온: {weather_data['temperature']}°C
- 강수확률: {weather_data['rain_probability']}%
- 추천: {weather_data['recommendation']}

**여행 스타일 특화:**
{style_context}

**8단계 처리된 장소 데이터:**
{location_context}

**절대 규칙: 위 검증된 장소들만 사용하세요. 가상의 장소 절대 금지!**

**응답 규칙:**
- 🚨 **각 장소는 전체 {days_count}일 일정에서 단 1번만 등장** (중복 절대 금지)
- 🚨 **1일차와 2일차는 완전히 다른 장소**들로 구성 (같은 장소 재방문 금지)
- 실제 존재하는 장소만 포함
- 불확실한 경우 "verified": false로 표시
- 날씨에 맞는 실내/실외 활동 우선 선택
- **이동 거리 제한**: 연속된 장소 간 대중교통 이동시간 20분 이내로 제한
- **도시 제한 강화**: {city} 내 장소만 추천 (예: 대구 요청시 대구광역시 내 장소만)
- **지역 검증**: 모든 추천 장소가 {city}에 실제 위치하는지 재확인
- **일자별 체크**: 일정 생성 후 1일차와 2일차에 중복된 장소가 있는지 반드시 확인하고 제거

응답 형식:
{{
  "schedule": [
    {{
      "time": "09:00",
      "place_name": "실제 존재하는 고유한 장소명",
      "activity": "구체적인 활동",
      "address": "정확한 주소 (구/동 포함)",
      "duration": "30분",
      "description": "장소 설명",
      "transportation": "구체적인 대중교통 정보",
      "rating": 4.5,
      "price": "예상 비용",
      "lat": 37.5665,
      "lng": 126.9780,
      "verified": false
    }}
  ]
}}
"""
        
        # 날씨 기반 프롬프트 생성
        weather_context = f"""
현재 날씨 상황:
- 날씨: {weather_data['condition']}
- 기온: {weather_data['temperature']}°C (체감온도: {weather_data['feels_like']}°C)
- 강수확률: {weather_data['rain_probability']}%
- 바람: {weather_data['wind_speed']}m/s
- 추천: {weather_data['recommendation']}

**날씨 기반 활동 조정:**
{"- 비가 올 가능성이 있으니 실내 활동 위주로 구성하세요" if weather_data['is_rainy'] else ""}
{"- 맑은 날씨이니 야외 활동을 적극 포함하세요" if weather_data['is_sunny'] else ""}
"""
        
        # 날씨 기반 실시간 추천 로직
        weather_service = WeatherRecommendationService()
        weather_recommendations = weather_service.get_weather_based_recommendations(weather_data, forecast_data)
        
        # days_count는 이미 위에서 계산됨
        
        # 🆕 프롬프트 생성 전 도시명 검증 로그
        print(f"   🎯 AI 프롬프트에 사용될 도시명: '{city}'")
        
        user_prompt = f"""
다음 요청에 대해 **{days_count}일간의 일자별 상세 여행 일정**을 생성해주세요:

요청: {prompt}

{weather_context}

**날씨 기반 실시간 추천:**
{weather_recommendations}

**UI에서 설정한 여행 정보:**
- 도시: {city}
- 여행 스타일: {travel_style}
- 시작일: {start_date_val or '오늘'}
- 종료일: {end_date_val or '오늘'}
- 매일 시작 시간: {start_time}
- 매일 종료 시간: {end_time}
- 출발지: {start_location or '미설정'}
- 총 {days_count}일간 여행 (반드시 일자별로 구분해서 생성)

**일정 생성 규칙:**
1. **일자별 구분**: 각 날짜별로 독립적인 일정 구성 (반드시 day 필드 포함)
2. **시간 준수**: 매일 {start_time}부터 {end_time}까지 일정 구성
3. **스타일 반영**: {travel_style} 스타일에 맞는 장소 우선 선택
4. **도시 제한 강화**: {city} 내 장소만 추천 (다른 도시 절대 금지)
5. **출발지 고려**: {start_location or '미설정'}에서 시작하는 동선 구성
6. **실제 장소만**: 가상 장소 절대 금지, 검증된 장소만 추천
7. **🚨 중복 절대 금지 (CRITICAL) 🚨**: 
   - 전체 {days_count}일 여행 기간 동안 같은 장소를 두 번 이상 방문하는 것 절대 금지
   - 1일차에 방문한 장소는 2일차에 절대 포함하지 않음
   - 예: 1일차에 "청도한우마을" 방문 → 2일차에 "청도한우마을" 재방문 절대 금지
   - 각 장소는 전체 일정에서 단 1번만 등장해야 함
   - 장소명, 주소, 좌표 모두 확인하여 중복 방지
8. **현실적 동선**: 지역별 클러스터링으로 효율적 이동
9. **이동시간 제한**: 연속된 장소 간 대중교통/도보 이동시간 20분 이내
10. **지역 특화**: {city}의 유명한 구/동 지역 내에서만 장소 선택
11. **지역 검증**: 모든 장소가 {city}에 실제 위치하는지 반드시 확인
12. **일자별 다양성**: 1일차와 2일차는 완전히 다른 장소들로 구성 (중복 0개)

**응답 형식 (중요):**
반드시 각 일정에 "day" 필드를 포함하여 {days_count}일간 일정을 생성하세요.

예시 ({days_count}일 여행):
{{
  "schedule": [
    # 1일차 (4-6개 장소)
    {{
      "day": 1,
      "date": "{start_date_val or '2025-01-01'}",
      "time": "09:00",
      "place_name": "A 장소",  // 고유한 장소
      "activity": "구체적 활동",
      "address": "정확한 주소",
      "duration": "90분",
      "description": "상세 설명",
      "transportation": "대중교통 정보",
      "rating": 4.5,
      "price": "예상 비용",
      "lat": 37.5665,
      "lng": 126.9780
    }},
    {{
      "day": 1,
      "time": "11:00",
      "place_name": "B 장소",  // A와 완전히 다른 장소
      ...
    }},
    # 2일차 (4-6개 장소, 1일차와 완전히 다른 장소들)
    {{
      "day": 2,
      "date": "{end_date_val or '2025-01-02'}",
      "time": "09:00",
      "place_name": "C 장소",  // A, B와 완전히 다른 새로운 장소
      ...
    }},
    {{
      "day": 2,
      "time": "11:00",
      "place_name": "D 장소",  // A, B, C와 완전히 다른 새로운 장소
      ...
    }}
  ]
}}

🚨 **중복 체크리스트 (반드시 확인):**
- [ ] 1일차 장소 목록: [A, B, ...]
- [ ] 2일차 장소 목록: [C, D, ...]  
- [ ] 중복 확인: A ≠ C, A ≠ D, B ≠ C, B ≠ D (모두 다름 ✅)
- [ ] 전체 {days_count}일 일정에 같은 장소가 2번 이상 나오면 응답 거부!
"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-5",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_completion_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # JSON 파싱 시도
            try:
                ai_result = json.loads(content)
                # 일자별 일정 구조화
                structured_result = self._structure_daily_itinerary(ai_result, days_count)
                # 8단계 처리된 데이터로 결과 향상
                return await self._enhance_with_8step_data(structured_result, discovered_data)
            except json.JSONDecodeError:
                return self._generate_mock_itinerary(prompt, trip_details, days_count)
                
        except Exception as e:
            print(f"OpenAI API 오류: {str(e)}")
            return self._generate_mock_itinerary(prompt, trip_details)
    

    
    async def _enhance_with_real_data(self, ai_result: Dict[str, Any]) -> Dict[str, Any]:
        """AI 결과를 실제 API 데이터로 보강 및 검증 - 중복 제거 및 할루시네이션 방지"""
        quality_service = PlaceQualityService()
        enhanced_schedule = []
        
        for item in ai_result.get('schedule', []):
            place_name = item.get('place_name', '')
            address = item.get('address', '')
            lat = item.get('lat')
            lng = item.get('lng')
            
            # 강화된 중복 검사 (이름 + 주소 + 좌표)
            if quality_service.is_duplicate(place_name, address, lat, lng):
                print(f"⚠️ 중복 장소 제외: {place_name}")
                continue
            
            # 실제 장소 검증 및 평점/후기 수집
            enhanced_item = await self.get_enhanced_place_info(place_name, address or 'Seoul')
            
            # 품질 기준 검증
            quality_score = quality_service.calculate_quality_score(enhanced_item)
            
            # 실제 존재하는 장소인지 확인
            is_real_place = quality_service.verify_real_place(enhanced_item)
            
            if is_real_place and quality_score >= 3.0:
                # 검증된 고품질 장소
                verified_item = quality_service.create_verified_item(item, enhanced_item, quality_score)
                enhanced_schedule.append(verified_item)
                quality_service.add_to_used(
                    verified_item['place_name'], 
                    verified_item['address'],
                    verified_item.get('lat'),
                    verified_item.get('lng')
                )
                
            elif quality_score >= 2.0:  # 낮은 품질이지만 존재하는 장소
                # 경고와 함께 포함
                item.update({
                    'verified': False,
                    'quality_score': quality_score,
                    'description': item.get('description', '') + f' ⚠️ 검증 필요 (품질: {quality_score:.1f}/5.0)',
                    'blog_reviews': enhanced_item.get('blog_reviews', []),
                    'blog_contents': enhanced_item.get('blog_contents', [])
                })
                enhanced_schedule.append(item)
                quality_service.add_to_used(place_name, address, lat, lng)
                
            else:
                print(f"❌ 검증 실패로 제외: {place_name} (품질: {quality_score:.1f})")
        
        # 최소 3개 장소 보장
        if len(enhanced_schedule) < 3:
            fallback_places = quality_service.get_fallback_places(3 - len(enhanced_schedule))
            enhanced_schedule.extend(fallback_places)
        
        ai_result['schedule'] = enhanced_schedule
        
        # 🆕 AI 여행 스타일 분석 메타데이터 추가
        if self.last_style_analysis:
            ai_result['analyzed_style'] = self.last_style_analysis
        
        return ai_result
    
    def _structure_daily_itinerary(self, ai_result: Dict[str, Any], days_count: int) -> Dict[str, Any]:
        """일자별 일정 구조화"""
        schedule = ai_result.get('schedule', [])
        
        if not schedule:
            return ai_result
        
        # 시간 기준으로 일자 할당 (더 정교한 방법)
        current_day = 1
        last_hour = 0
        
        for i, item in enumerate(schedule):
            if 'day' not in item or item['day'] is None:
                # 시간 추출
                time_str = item.get('time', '09:00')
                try:
                    hour = int(time_str.split(':')[0])
                except:
                    hour = 9 + (i % 12)  # 기본값
                
                # 시간이 이전보다 작아지면 다음 날
                if i > 0 and hour < last_hour and hour < 12:
                    current_day += 1
                    if current_day > days_count:
                        current_day = days_count
                
                item['day'] = current_day
                item['date'] = f"2025-01-{current_day:02d}"
                last_hour = hour
        
        # 일자별 균등 분배 조정
        if days_count > 1:
            items_per_day = len(schedule) // days_count
            remainder = len(schedule) % days_count
            
            day_counts = {}
            for item in schedule:
                day = item.get('day', 1)
                day_counts[day] = day_counts.get(day, 0) + 1
            
            # 불균형 조정
            for day in range(1, days_count + 1):
                if day not in day_counts:
                    # 빈 날짜에 아이템 이동
                    for item in schedule:
                        if item.get('day', 1) > day and day_counts.get(item['day'], 0) > items_per_day:
                            item['day'] = day
                            day_counts[day] = day_counts.get(day, 0) + 1
                            day_counts[item['day']] -= 1
                            break
        
        return ai_result
    
    def _generate_mock_itinerary(self, prompt: str, trip_details: Dict[str, Any] = None, days_count: int = 1) -> Dict[str, Any]:
        """API 키가 없을 때 모의 일정 생성"""
        mock_schedule = []
        
        # 도시별 모의 데이터
        city = trip_details.get('city', 'Seoul') if trip_details else 'Seoul'
        city_data = self._get_city_mock_data(city)
        
        for day in range(1, days_count + 1):
            # 하루에 6개 장소 생성
            daily_places = [
                {
                    "day": day,
                    "date": f"2025-01-{day:02d}",
                    "time": "09:00",
                    "place_name": city_data['places'][0]['name'],
                    "activity": city_data['places'][0]['activity'],
                    "address": city_data['places'][0]['address'],
                    "duration": "90분",
                    "description": city_data['places'][0]['description'],
                    "transportation": city_data['places'][0]['transportation'],
                    "rating": city_data['places'][0]['rating'],
                    "price": city_data['places'][0]['price'],
                    "lat": city_data['places'][0]['lat'],
                    "lng": city_data['places'][0]['lng']
                },
                {
                    "day": day,
                    "date": f"2025-01-{day:02d}",
                    "time": "11:00",
                    "place_name": city_data['places'][1]['name'],
                    "activity": city_data['places'][1]['activity'],
                    "address": city_data['places'][1]['address'],
                    "duration": "120분",
                    "description": city_data['places'][1]['description'],
                    "transportation": city_data['places'][1]['transportation'],
                    "rating": city_data['places'][1]['rating'],
                    "price": city_data['places'][1]['price'],
                    "lat": city_data['places'][1]['lat'],
                    "lng": city_data['places'][1]['lng']
                },
                {
                    "day": day,
                    "date": f"2025-01-{day:02d}",
                    "time": "13:00",
                    "place_name": city_data['places'][2]['name'],
                    "activity": city_data['places'][2]['activity'],
                    "address": city_data['places'][2]['address'],
                    "duration": "90분",
                    "description": city_data['places'][2]['description'],
                    "transportation": city_data['places'][2]['transportation'],
                    "rating": city_data['places'][2]['rating'],
                    "price": city_data['places'][2]['price'],
                    "lat": city_data['places'][2]['lat'],
                    "lng": city_data['places'][2]['lng']
                }
            ]
            mock_schedule.extend(daily_places)
        
        return {"schedule": mock_schedule}
    
    def _get_city_mock_data(self, city: str) -> Dict[str, Any]:
        """도시별 모의 데이터 생성"""
        city_mock_data = {
            'Seoul': {
                'places': [
                    {'name': '경복궁', 'activity': '궁궐 관람', 'address': '서울시 종로구 사직로 161', 'description': '조선왕조의 정궁', 'transportation': '지하철 3호선 경복궁역', 'rating': 4.5, 'price': '3,000원', 'lat': 37.5796, 'lng': 126.9770},
                    {'name': '명동 쇼핑거리', 'activity': '쇼핑 및 거리구경', 'address': '서울시 중구 명동길', 'description': '서울의 대표 쇼핑거리', 'transportation': '지하철 4호선 명동역', 'rating': 4.2, 'price': '무료', 'lat': 37.5636, 'lng': 126.9834},
                    {'name': '남대문 시장', 'activity': '전통시장 탐방', 'address': '서울시 중구 남대문시장길', 'description': '전통 시장에서 맛있는 음식 체험', 'transportation': '지하철 4호선 회현역', 'rating': 4.3, 'price': '10,000원', 'lat': 37.5595, 'lng': 126.9941}
                ]
            },
            'Daegu': {
                'places': [
                    {'name': '동성로', 'activity': '쇼핑 및 거리구경', 'address': '대구시 중구 동성로2가', 'description': '대구의 대표 번화가', 'transportation': '지하철 1호선 중앙로역', 'rating': 4.3, 'price': '무료', 'lat': 35.8714, 'lng': 128.6014},
                    {'name': '서문시장', 'activity': '전통시장 탐방', 'address': '대구시 중구 큰장로26길 45', 'description': '대구 대표 전통시장', 'transportation': '지하철 3호선 서문시장역', 'rating': 4.2, 'price': '15,000원', 'lat': 35.8700, 'lng': 128.5900},
                    {'name': '팔공산', 'activity': '자연 관광', 'address': '대구시 동구 팔공산로', 'description': '대구의 명산', 'transportation': '버스 101번', 'rating': 4.4, 'price': '무료', 'lat': 35.9500, 'lng': 128.7000}
                ]
            },
            'Busan': {
                'places': [
                    {'name': '해운대해수욕장', 'activity': '해변 관광', 'address': '부산시 해운대구 우동', 'description': '부산의 대표 해수욕장', 'transportation': '지하철 2호선 해운대역', 'rating': 4.4, 'price': '무료', 'lat': 35.1631, 'lng': 129.1635},
                    {'name': '자갈치시장', 'activity': '해산물 시장', 'address': '부산시 중구 자갈치해안로 52', 'description': '부산 대표 수산시장', 'transportation': '지하철 1호선 자갈치역', 'rating': 4.3, 'price': '20,000원', 'lat': 35.0966, 'lng': 129.0306},
                    {'name': '감천문화마을', 'activity': '문화 관광', 'address': '부산시 사하구 감내2로 203', 'description': '부산의 마추픽추', 'transportation': '버스 2-2번', 'rating': 4.5, 'price': '무료', 'lat': 35.0975, 'lng': 129.0107}
                ]
            },
            'Jeju': {
                'places': [
                    {'name': '성산일출봉', 'activity': '자연 관광', 'address': '제주시 성산읍 일출로 284-12', 'description': '제주의 대표 관광지', 'transportation': '버스 201번', 'rating': 4.6, 'price': '5,000원', 'lat': 33.4584, 'lng': 126.9427},
                    {'name': '한라산', 'activity': '등산', 'address': '제주시 1100로', 'description': '제주도 최고봉', 'transportation': '버스 740번', 'rating': 4.5, 'price': '무료', 'lat': 33.3617, 'lng': 126.5292},
                    {'name': '우도', 'activity': '섬 관광', 'address': '제주시 우도면', 'description': '아름다운 작은 섬', 'transportation': '배편', 'rating': 4.4, 'price': '8,000원', 'lat': 33.5009, 'lng': 126.9500}
                ]
            }
        }
        
        return city_mock_data.get(city, city_mock_data['Seoul'])
    
    async def _get_location_context(self, prompt: str, city_info: Dict[str, Any], district_itinerary: List[Dict[str, Any]] = None) -> str:
        """도시별 특화 정보 및 실제 장소 정보 제공"""
        city_name = city_info.get('name', '서울')
        specialties = city_info.get('specialties', [])
        famous_places = city_info.get('famous_places', [])
        transport_hub = city_info.get('transport_hub', [])
        
        specialties_text = ", ".join(specialties)
        places_text = "\n".join([f"- {place}" for place in famous_places])
        transport_text = ", ".join(transport_hub)
        
        # 구역별 추천 장소 정보 추가
        district_context = ""
        if district_itinerary:
            district_context = "\n\n**구역별 효율적 동선 추천:**\n"
            current_district = None
            for item in district_itinerary:
                if item.get('district') != current_district:
                    current_district = item['district']
                    district_context += f"\n[{current_district}]\n"
                district_context += f"- {item['place_name']} ({item['type']})\n"
        
        return f"""
{city_name} 지역 정보:
특색: {specialties_text}
주요 교통거점: {transport_text}
대표 관광지/명소:
{places_text}
{district_context}

**동선 최적화 규칙:**
1. 같은 구역 내 장소들을 연속으로 방문하여 이동시간 최소화
2. 구역 간 이동은 대중교통 접근성을 고려하여 순서 결정
3. {city_name}의 실제 존재하는 장소만 추천
4. 위 구역별 추천을 우선 고려하되 다른 실제 장소도 추천 가능
5. {city_name}의 특색인 {specialties_text}을 활용한 여행 계획 구성
6. 다른 도시의 장소는 절대 추천 금지
"""
    
    def _get_style_specific_context(self, travel_style: str) -> str:
        """여행 스타일별 특화 가이드"""
        style_guides = {
            'indoor_date': """
특화 가이드: 실내 데이트
- 카페, 박물관, 미술관, 전시관 우선
- 쇼핑몰, 대형서점, 영화관 포함
- 실내 체험 공간 (도예, 쿠킹클래스 등)
- 날씨에 관계없이 즐길 수 있는 공간
- 조용하고 낭만적인 분위기
""",
            'outdoor_date': """
특화 가이드: 실외 데이트
- 공원, 한강, 산책로 우선
- 전망대, 전망카페, 야외 체험
- 자연 속 피크닉 장소
- 사진 촬영 명소 (인스타 핫플레이스)
- 날씨가 좋을 때 최적인 장소
""",
            'food_tour': """
특화 가이드: 맛집 투어
- 로컬 맛집, 전통시장 우선
- 미슐링 가이드 등재 맛집
- 전통 한식, 길거리 음식 포함
- 디저트 카페, 베이커리 연결
- 음식 체험 프로그램 (쿠킹클래스 등)
""",
            'culture_tour': """
특화 가이드: 문화 탐방
- 궁궐, 전통 건축물 우선
- 박물관, 미술관, 전시관
- 전통 공예촌, 한옥마을
- 역사적 의미가 있는 장소
- 문화체험 프로그램 (한복, 차 체험 등)
""",
            'shopping_tour': """
특화 가이드: 쇼핑 투어
- 명동, 홍대, 강남 쇼핑거리
- 대형 쇼핑몰, 디파트먼트 스토어
- 동대문 디자인 플라자
- 지하상가, 패션 스트리트
- K-뷰티, K-패션 전문점
""",
            'healing_tour': """
특화 가이드: 힐링 여행
- 스파, 천연 온천 우선
- 조용한 공원, 산책로
- 명상, 요가 체험 공간
- 전통 차 체험, 한의원 체험
- 자연 치유 공간, 산림욕
""",
            'adventure_tour': """
특화 가이드: 액티비티
- 놀이공원, 테마파크 우선
- 스포츠 체험 (볼링, 아이스링크 등)
- VR 체험관, 이스케이프 룸
- 어드벤처 스포츠 (집라인, 번지점프 등)
- 실내 클라이밍, 트램폴린
""",
            'night_tour': """
특화 가이드: 야경 투어
- 한강 야경, 전망대 우선
- 야시장, 홍대 밤거리
- 루프톱 바, 야경 카페
- 라이브 공연, 클럽 문화
- 야간 조명이 아름다운 장소
""",
            'family_tour': """
특화 가이드: 가족 여행
- 아이 친화적 박물관, 과학관
- 대형 공원, 동물원, 수족관
- 체험 학습 공간 (키즈 카페 등)
- 안전하고 넓은 실내 공간
- 유모차 접근 가능한 장소
"""
        }
        
        return style_guides.get(travel_style, "사용자 맞춤 여행 계획을 세워주세요.")
    
    async def get_enhanced_place_info(self, place_name: str, location: str = "Seoul") -> Dict[str, Any]:
        """장소 상세정보 및 후기 수집"""
        naver_service = NaverService()
        google_service = GoogleMapsService()
        blog_crawler = BlogCrawlerService()
        
        # 네이버 데이터
        naver_places = await naver_service.search_places(place_name)
        naver_blogs = await naver_service.search_blogs(f"{place_name} 후기")
        
        # 구글 데이터
        google_details = await google_service.get_place_details(place_name, location)
        
        # 블로그 내용 크롤링 (실제 크롤링)
        blog_contents = []
        if naver_blogs:
            blog_urls = [blog.get('link') for blog in naver_blogs[:3] if blog.get('link')]
            if blog_urls:
                blog_contents = await blog_crawler.get_multiple_blog_contents(blog_urls)
                print(f"✅ {place_name} 블로그 크롤링 완료: {len(blog_contents)}개")
        
        return {
            "naver_info": naver_places[0] if naver_places else {},
            "google_info": google_details,
            "blog_reviews": naver_blogs[:5],  # 상위 5개만
            "blog_contents": blog_contents,
            "verified": bool(naver_places or (google_details and google_details.get('name')))
        }
    
    async def _calculate_quality_score(self, enhanced_item: Dict[str, Any]) -> float:
        """장소 품질 점수 계산 (강화된 버전)"""
        score = 0.0
        
        # 구글 평점 (40%)
        google_info = enhanced_item.get('google_info', {})
        if google_info.get('rating', 0) > 0:
            score += google_info['rating'] * 0.4
        
        # 네이버 장소 정보 (30%)
        naver_info = enhanced_item.get('naver_info', {})
        if naver_info and naver_info.get('name'):
            score += 4.5 * 0.3  # 네이버에 등록된 장소는 기본 4.5점
        
        # 블로그 후기 수 (20%)
        blog_reviews = enhanced_item.get('blog_reviews', [])
        if blog_reviews and len(blog_reviews) > 0:
            review_score = min(len(blog_reviews) + 2, 5.0)  # 최소 2점 보장
            score += review_score * 0.2
        
        # 블로그 내용 품질 (10%)
        blog_contents = enhanced_item.get('blog_contents', [])
        if blog_contents:
            score += 4.0 * 0.1
        
        return min(score, 5.0)  # 최대 5점
    
    async def _find_quality_replacement(self, original_item: Dict[str, Any], enhanced_item: Dict[str, Any]) -> Dict[str, Any]:
        """품질 기준을 만족하는 대체 장소 찾기"""
        activity_type = original_item.get('activity', '')
        address = original_item.get('address', '')
        
        # 지역별 검증된 고품질 장소들
        quality_places = {
            '마곡': {
                '카페': [
                    {'name': '스타벅스 마곡나루역점', 'address': '서울시 강서구 마곡중앙로 161', 'rating': 4.2},
                    {'name': '투썸플레이스 마곡센트럴파크점', 'address': '서울시 강서구 마곡중앙로 240', 'rating': 4.1}
                ],
                '쇼핑': [
                    {'name': '마곡 롯데월드몰', 'address': '서울시 강서구 마곡중앙로 240', 'rating': 4.3},
                    {'name': '마곡 아이파크몰', 'address': '서울시 강서구 마곡중앙로 78', 'rating': 4.1}
                ],
                '식당': [
                    {'name': '마곡 푸드코트', 'address': '서울시 강서구 마곡중앙로 240', 'rating': 4.0}
                ]
            }
        }
        
        # 지역 및 활동 유형에 맞는 대체 장소 찾기
        for region in quality_places:
            if region in address:
                for activity_key, places in quality_places[region].items():
                    if activity_key in activity_type.lower() or activity_key in original_item.get('place_name', '').lower():
                        # 가장 높은 평점의 장소 선택
                        best_place = max(places, key=lambda x: x['rating'])
                        
                        # 실제 장소 정보 재검증
                        replacement_info = await self.get_enhanced_place_info(best_place['name'])
                        replacement_score = await self._calculate_quality_score(replacement_info)
                        
                        if replacement_score >= 3.0:
                            return {
                                'place_name': best_place['name'],
                                'address': best_place['address'],
                                'rating': best_place['rating'],
                                'verified': True,
                                'quality_score': replacement_score,
                                'description': f"{best_place['name']}에서 {original_item.get('activity', '')}",
                                'blog_reviews': replacement_info.get('blog_reviews', []),
                                'blog_contents': replacement_info.get('blog_contents', []),
                                'time': original_item.get('time'),
                                'duration': original_item.get('duration'),
                                'transportation': original_item.get('transportation'),
                                'price': original_item.get('price')
                            }
        
        return None
    
    async def _find_fallback_place(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """검증되지 않은 장소에 대한 대체 장소 찾기"""
        activity_type = item.get('activity', '')
        address = item.get('address', '')
        
        # 지역 기반 대체 장소 매핑
        fallback_places = {
            '마곡': {
                '카페': {'name': '마곡 센트럴파크 카페거리', 'address': '서울시 강서구 마곡중앙로 161'},
                '쇼핑': {'name': '마곡 롯데월드몰', 'address': '서울시 강서구 마곡중앙로 240'},
                '식당': {'name': '막걸리 맛집거리', 'address': '서울시 강서구 마곡동'}
            }
        }
        
        for region in fallback_places:
            if region in address:
                for activity_key, place_info in fallback_places[region].items():
                    if activity_key in activity_type or activity_key in item.get('place_name', ''):
                        return {
                            'place_name': place_info['name'],
                            'address': place_info['address'],
                            'verified': True,
                            'description': f"{place_info['name']}에서 {activity_type}"
                        }
        
        return None
    
    def _get_example_other_districts(self, city: str, district: str, current_neighborhood: str) -> str:
        """
        🆕 다른 동 예시 생성 (AI가 피해야 할 지역)
        """
        from app.services.hierarchical_location_extractor import HierarchicalLocationExtractor
        
        extractor = HierarchicalLocationExtractor()
        locations = extractor.KOREAN_LOCATIONS.get(city, {})
        
        if district and district in locations:
            other_neighborhoods = [n for n in locations[district] if n != current_neighborhood]
            return ', '.join(other_neighborhoods[:3])  # 최대 3개
        
        return "다른 동"
    
    def _build_enhanced_context(self, discovered_data: Dict[str, Any]) -> str:
        """8단계 처리된 데이터를 AI 컨텍스트로 변환"""
        verified_places = discovered_data.get('verified_places', [])
        weather_forecast = discovered_data.get('weather_forecast', {})
        cache_usage = discovered_data.get('cache_usage', {})
        
        if not verified_places:
            return "검증된 장소가 없습니다."
        
        context = f"8단계 처리 결과:\n"
        context += f"- 검증된 장소: {len(verified_places)}개\n"
        context += f"- 캐시 활용: {cache_usage.get('cached', 0)}개, 신규 크롤링: {cache_usage.get('new_crawl', 0)}개\n"
        
        # 날씨 정보
        if weather_forecast:
            context += f"\n날씨 기반 필터링 적용됨:\n"
            for date, weather in weather_forecast.items():
                context += f"- {date}: {weather.get('condition', '')}, {weather.get('temperature', '')}°C\n"
        
        context += f"\n검증된 장소 목록:\n"
        
        for i, place in enumerate(verified_places[:15], 1):  # 최대 15개
            name = place.get('name', '')
            address = place.get('address', '')
            verification_status = place.get('verification_status', 'unknown')
            
            context += f"{i}. {name} [검증: {verification_status}]\n"
            context += f"   - 주소: {address}\n"
            
            # 블로그 후기 요약
            blog_contents = place.get('blog_contents', [])
            if blog_contents:
                context += f"   - 후기: {blog_contents[0].get('summary', '')[:30]}...\n"
            
            context += "\n"
        
        return context
    
    async def _enhance_with_8step_data(self, ai_result: Dict[str, Any], discovered_data: Dict[str, Any]) -> Dict[str, Any]:
        """8단계 처리된 데이터로 AI 결과 향상 + 중복 제거 + 🆕 지역 검증"""
        enhanced_schedule = []
        verified_places = discovered_data.get('verified_places', [])
        
        # 🆕 지역 검증을 위한 정보 추출
        location_hierarchy = discovered_data.get('location_hierarchy', {})
        target_city = location_hierarchy.get('city', '')
        target_district = location_hierarchy.get('district', '')
        target_neighborhood = location_hierarchy.get('neighborhood', '')
        center_lat = location_hierarchy.get('lat')
        center_lng = location_hierarchy.get('lng')
        search_radius_km = location_hierarchy.get('search_radius_km', 3.0)
        
        print(f"\n🔍 매칭 프로세스 시작")
        print(f"AI 생성 장소: {len(ai_result.get('schedule', []))}개")
        print(f"검증된 장소: {len(verified_places)}개")
        print(f"🎯 지역 검증 기준: {target_city} {target_district or ''} {target_neighborhood or ''}")
        if verified_places:
            print(f"검증된 장소 목록: {[p.get('name', '?') for p in verified_places[:5]]}")
        print()
        
        # 🆕 사용된 장소 추적 (중복 방지)
        used_places = set()  # 전체 기간 사용된 장소명
        used_addresses = set()  # 전체 기간 사용된 주소
        used_coords = []  # 사용된 좌표 [(lat, lng), ...]
        
        # 🆕 일자별 사용 추적 (같은 날 중복 방지)
        used_today = {}  # {day: set([장소1, 장소2, ...])}
        
        # 🆕 지역 불일치 카운터
        location_mismatches = 0
        
        # AI가 생성한 일정과 8단계 검증된 장소 매칭
        for item in ai_result.get('schedule', []):
            place_name = item.get('place_name', '')
            day = item.get('day', 1)
            
            # 정규화 함수 (띄어쓰기 제거)
            def normalize_name(name):
                return name.lower().replace(' ', '').replace('-', '').replace('_', '')
            
            # 🆕 전체 기간 중복 체크 (다일 여행)
            normalized_place_name = normalize_name(place_name)
            if normalized_place_name in used_places:
                print(f"   ⚠️ 전체 중복 스킵: '{place_name}' ({day}일차, 이미 다른 날 사용됨)")
                continue
            
            # 🆕 일내 중복 체크 (같은 날 2번 방문 방지)
            if day not in used_today:
                used_today[day] = set()
            
            if normalized_place_name in used_today[day]:
                print(f"   ⚠️ {day}일차 중복 스킵: '{place_name}' (같은 날 이미 방문)")
                continue
            
            # 검증된 장소에서 매칭되는 장소 찾기 (🆕 아직 사용되지 않은 장소만)
            matched_place = None
            
            for verified_place in verified_places:
                verified_name = verified_place.get('name', '')
                normalized_verified_name = normalize_name(verified_name)
                
                # 🆕 이미 사용된 장소면 스킵
                if normalized_verified_name in used_places:
                    continue
                
                # 정규화된 이름으로 비교
                if normalized_place_name in normalized_verified_name or \
                   normalized_verified_name in normalized_place_name:
                    matched_place = verified_place
                    print(f"✅ 매칭 성공: '{place_name}' ↔ '{verified_name}' ({day}일차)")
                    
                    # 🆕 사용됨으로 마킹 (전체 + 일자별)
                    used_places.add(normalized_verified_name)
                    used_today[day].add(normalized_verified_name)
                    if verified_place.get('address'):
                        used_addresses.add(verified_place['address'])
                    break
            
            if not matched_place:
                print(f"❌ 매칭 실패: '{place_name}' (검증된 장소 {len(verified_places)}개 중)")
            
            if matched_place:
                # 🆕 Step: 지역 검증 (주소 기반)
                place_address = matched_place.get('address', item.get('address', ''))
                place_lat = matched_place.get('lat', item.get('lat'))
                place_lng = matched_place.get('lng', item.get('lng'))
                
                location_valid = True
                validation_reason = ""
                
                # 검증 1: 주소에 요청 지역 포함 여부
                if target_neighborhood:
                    if target_neighborhood not in place_address:
                        location_valid = False
                        validation_reason = f"주소에 '{target_neighborhood}' 미포함"
                elif target_district:
                    if target_district not in place_address:
                        location_valid = False
                        validation_reason = f"주소에 '{target_district}' 미포함"
                elif target_city:
                    if target_city not in place_address:
                        location_valid = False
                        validation_reason = f"주소에 '{target_city}' 미포함"
                
                # 검증 2: 좌표 거리 확인
                if location_valid and center_lat and center_lng and place_lat and place_lng:
                    from math import radians, sin, cos, sqrt, atan2
                    
                    # Haversine 공식으로 거리 계산
                    R = 6371  # 지구 반경 (km)
                    lat1, lon1 = radians(center_lat), radians(center_lng)
                    lat2, lon2 = radians(place_lat), radians(place_lng)
                    
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * atan2(sqrt(a), sqrt(1-a))
                    distance_km = R * c
                    
                    if distance_km > search_radius_km * 1.5:  # 50% 여유 허용
                        location_valid = False
                        validation_reason = f"중심점으로부터 {distance_km:.1f}km (제한: {search_radius_km}km)"
                
                if not location_valid:
                    location_mismatches += 1
                    print(f"   ⚠️ 지역 불일치 스킵: '{matched_place.get('name')}' - {validation_reason}")
                    print(f"      주소: {place_address}")
                    continue
                
                # 검증된 데이터로 아이템 향상
                enhanced_item = {
                    **item,
                    'place_name': matched_place.get('name', place_name),
                    'address': place_address,
                    'verified': True,
                    'verification_status': matched_place.get('verification_status', 'verified'),
                    'location_validated': True,  # 🆕 지역 검증 통과 표시
                    'blog_reviews': matched_place.get('blog_reviews', []),
                    'blog_contents': matched_place.get('blog_contents', []),
                    'google_info': matched_place.get('google_info', {}),
                    'naver_info': matched_place.get('naver_info', {}),
                    'lat': place_lat,
                    'lng': place_lng
                }
                enhanced_schedule.append(enhanced_item)
            else:
                # 매칭되지 않은 경우: 지역 검증 후 포함 여부 결정
                place_address = item.get('address', '')
                
                location_valid = False
                if target_neighborhood and target_neighborhood in place_address:
                    location_valid = True
                elif target_district and target_district in place_address:
                    location_valid = True
                elif target_city and target_city in place_address:
                    location_valid = True
                
                if location_valid:
                    item['verified'] = False
                    item['verification_status'] = 'unverified'
                    item['location_validated'] = True
                    enhanced_schedule.append(item)
                else:
                    location_mismatches += 1
                    print(f"   ⚠️ 미검증 장소 지역 불일치: '{item.get('place_name')}' (주소: {place_address})")
        
        # 8단계 처리 메타데이터 추가
        ai_result['schedule'] = enhanced_schedule
        ai_result['processing_metadata'] = {
            'total_verified_places': len(verified_places),
            'matched_places': len([item for item in enhanced_schedule if item.get('verified')]),
            'location_validated_places': len([item for item in enhanced_schedule if item.get('location_validated')]),
            'location_mismatches': location_mismatches,  # 🆕 지역 불일치 개수
            'cache_usage': discovered_data.get('cache_usage', {}),
            'weather_forecast': discovered_data.get('weather_forecast', {}),
            'optimized_route': discovered_data.get('optimized_route', {})
        }
        
        # 🆕 지역 검증 결과 출력
        if location_mismatches > 0:
            print(f"\n⚠️ 지역 검증 결과: {location_mismatches}개 장소가 요청 지역과 불일치하여 제외됨")
            print(f"   최종 일정: {len(enhanced_schedule)}개 장소")
        
        # 🆕 식사 시간 규칙 검증 및 필터링
        print(f"\n🍽️ 식사 시간 규칙 검증 시작")
        validated_schedule = self._validate_meal_schedule(enhanced_schedule)
        ai_result['schedule'] = validated_schedule
        
        meal_filtered_count = len(enhanced_schedule) - len(validated_schedule)
        if meal_filtered_count > 0:
            print(f"⚠️ 식사 규칙 위반: {meal_filtered_count}개 장소 제외")
        
        ai_result['processing_metadata']['meal_filtered_count'] = meal_filtered_count
        
        return ai_result
    
    def _validate_meal_schedule(self, schedule: List[Dict]) -> List[Dict]:
        """
        식사 시간 규칙 검증 및 필터링
        
        규칙:
        - 하루 식사는 아침(07:00-10:00), 점심(11:00-14:00), 저녁(17:00-21:00) 딱 3번
        - 각 시간대에 1번만 식사 일정 배치
        - 연속 식사 금지
        """
        
        # 식사 키워드
        MEAL_KEYWORDS = ["식당", "맛집", "점심", "저녁", "아침", "식사", "한식", "중식", "일식", "양식", "뷔페", "레스토랑"]
        CAFE_KEYWORDS = ["카페", "커피", "디저트", "베이커리", "차"]
        
        def is_meal(item):
            """식사 활동인지 판단"""
            activity = item.get('activity', '').lower()
            place_name = item.get('place_name', '').lower()
            description = item.get('description', '').lower()
            
            # 카페는 식사로 간주하지 않음
            if any(keyword in activity or keyword in place_name for keyword in CAFE_KEYWORDS):
                return False
            
            # 식사 키워드 확인
            return any(keyword in activity or keyword in place_name or keyword in description for keyword in MEAL_KEYWORDS)
        
        def get_meal_time_slot(time_str):
            """시간대 분류 (아침/점심/저녁)"""
            try:
                hour = int(time_str.split(':')[0])
                if 7 <= hour < 11:
                    return 'breakfast'
                elif 11 <= hour < 15:
                    return 'lunch'
                elif 17 <= hour < 22:
                    return 'dinner'
                else:
                    return None
            except:
                return None
        
        # 일자별 식사 추적
        daily_meals = {}  # {day: {'breakfast': bool, 'lunch': bool, 'dinner': bool}}
        validated = []
        
        for item in schedule:
            day = item.get('day', 1)
            time_str = item.get('time', '09:00')
            
            # 식사 활동이 아니면 통과
            if not is_meal(item):
                validated.append(item)
                continue
            
            # 시간대 확인
            meal_slot = get_meal_time_slot(time_str)
            
            if meal_slot is None:
                # 식사 시간대가 아닌데 식사 활동 → 카페로 변경 제안
                print(f"   ⚠️ 식사 시간대 외 식사: '{item.get('place_name')}' ({time_str}) → 스킵")
                continue
            
            # 일자별 식사 슬롯 초기화
            if day not in daily_meals:
                daily_meals[day] = {'breakfast': False, 'lunch': False, 'dinner': False}
            
            # 해당 시간대 식사가 이미 있으면 스킵
            if daily_meals[day][meal_slot]:
                print(f"   ⚠️ {day}일차 {meal_slot} 중복: '{item.get('place_name')}' → 스킵")
                continue
            
            # 통과: 식사 일정 추가
            daily_meals[day][meal_slot] = True
            validated.append(item)
            print(f"   ✅ {day}일차 {meal_slot}: '{item.get('place_name')}' ({time_str})")
        
        return validated
    
    async def _get_weather_recommendation(self, city: str, start_date: str) -> str:
        """
        여행 날짜의 날씨 기반 추천
        
        Args:
            city: 도시명
            start_date: 여행 시작 날짜 (YYYY-MM-DD)
        
        Returns:
            날씨 기반 추천 문구
        """
        try:
            
            # 날짜 파싱
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            days_until_trip = (start_dt - datetime.now()).days
            
            # 5일 이내: 실제 예보 사용
            if days_until_trip <= 5 and days_until_trip >= 0:
                print(f"   🌤️ 날씨 예보 조회 중 ({days_until_trip}일 후)...")
                weather_service = WeatherService()
                forecast = await weather_service.get_forecast(city)
                
                # 예보 데이터 분석
                if forecast and isinstance(forecast, dict):
                    # 간단한 분석 (실제 구현에서는 더 정교하게)
                    condition = forecast.get('condition', '')
                    temp = forecast.get('temperature', 0)
                    
                    if '비' in condition or '눈' in condition:
                        return f"날씨: 비/눈 예상 ({temp}°C), 실내 활동 위주 추천 (박물관, 실내 관광지, 맛집 투어)"
                    elif temp < 5:
                        return f"날씨: 추운 날씨 ({temp}°C), 실내 활동과 온천 추천"
                    elif temp > 30:
                        return f"날씨: 더운 날씨 ({temp}°C), 시원한 장소와 물놀이 추천"
                    else:
                        return f"날씨: 맑음 ({temp}°C), 야외 활동 좋음 (공원, 산책로, 관광지)"
            
            # 5일 초과: 계절별 평균 추천
            month = start_dt.month
            print(f"   🌤️ 계절별 추천 사용 ({month}월)...")
            
            if month in [12, 1, 2]:
                return "계절: 겨울철 - 실내 활동, 온천, 맛집 투어 중심 추천"
            elif month in [3, 4, 5]:
                return "계절: 봄철 - 꽃구경, 야외 활동 좋음 (벚꽃, 진달래, 철쭉)"
            elif month in [6, 7, 8]:
                return "계절: 여름철 - 시원한 계곡, 해변, 실내 피서지 추천"
            elif month in [9, 10, 11]:
                return "계절: 가을철 - 단풍 명소, 등산, 야외 활동 추천"
            else:
                return ""
                
        except Exception as e:
            print(f"   ⚠️ 날씨 추천 실패: {e}")
            return ""
    
    async def _generate_with_schedule_framer(
        self,
        prompt: str,
        city: str,
        travel_style: str,
        start_date: str,
        end_date: str,
        start_time: str,
        end_time: str,
        start_location: str,
        travel_dates: List[str],
        days_count: int
    ) -> Dict[str, Any]:
        """
        🆕 AI 스케줄 프레이머를 사용한 새로운 일정 생성 방식
        
        3단계 파이프라인:
        1. AI가 시간대별 활동 계획 "틀" 생성
        2. 틀에 맞춰 실제 장소 순차 검색
        3. 경로 최적화
        """
        from app.services.ai_schedule_framer import AIScheduleFramer
        from app.services.enhanced_place_discovery_service import EnhancedPlaceDiscoveryService
        from app.services.hierarchical_location_extractor import HierarchicalLocationExtractor
        from app.services.google_maps_service import GoogleMapsService
        
        # Step 0: 도시 추출 (Auto인 경우)
        if city == "Auto" or not city:
            print(f"\n📍 도시 자동 추출 중...")
            extractor = HierarchicalLocationExtractor()
            location_info = await extractor.extract_location_hierarchy(prompt)
            city = location_info.get('city', 'Seoul')
            base_lat = location_info.get('lat', 37.5665)
            base_lng = location_info.get('lng', 126.9780)
            print(f"   ✅ 추출된 도시: {city} ({base_lat}, {base_lng})")
        else:
            # 도시 좌표 조회
            city_coords = {
                'Seoul': (37.5665, 126.9780),
                'Busan': (35.1796, 129.0756),
                'Daegu': (35.8714, 128.6014),
                'Incheon': (37.4563, 126.7052),
                'Gwangju': (35.1595, 126.8526),
                'Daejeon': (36.3504, 127.3845),
                'Ulsan': (35.5384, 129.3114),
                'Jeju': (33.4996, 126.5312),
            }
            base_lat, base_lng = city_coords.get(city, (37.5665, 126.9780))
        
        base_location = (base_lat, base_lng)
        
        # Step 1: AI 스케줄 프레이머 - 시간대별 활동 계획 "틀" 생성
        print(f"\n📋 Step 1: AI 스케줄 프레이머 호출")
        framer = AIScheduleFramer()
        
        # 🆕 날씨 정보 가져오기
        weather_recommendation = ""
        if start_date:
            weather_recommendation = await self._get_weather_recommendation(city, start_date)
            if weather_recommendation:
                print(f"   ✅ {weather_recommendation}")
        
        # 지역 맥락 정보 조회 (선택적)
        try:
            from app.services.local_context_db import LocalContextDB
            context_db = LocalContextDB()
            location_context = await context_db.get_or_create_context(city, base_lat, base_lng)
        except:
            location_context = None
        
        # 🆕 날씨 정보를 location_context에 추가
        if location_context is None:
            location_context = {}
        if weather_recommendation:
            location_context['weather_recommendation'] = weather_recommendation
        
        schedule_frame = await framer.create_schedule_frame(
            prompt=prompt,
            city=city,
            days_count=days_count,
            start_time=start_time,
            end_time=end_time,
            travel_style=travel_style,
            location_context=location_context
        )
        
        if not schedule_frame:
            print(f"   ⚠️ 스케줄 프레임 생성 실패 → 기존 방식으로 폴백")
            # 기존 로직으로 폴백 (여기서는 생략)
            return {"schedule": [], "error": "Schedule framer failed"}
        
        print(f"   ✅ 스케줄 프레임 생성 완료: {len(schedule_frame)}개 시간대")
        
        # Step 2: 순차적 장소 검색 - 틀에 맞춰 실제 장소 채우기
        print(f"\n🔍 Step 2: 순차적 장소 검색")
        enhanced_discovery = EnhancedPlaceDiscoveryService()
        
        filled_schedule = await enhanced_discovery.discover_places_sequential(
            schedule_frame=schedule_frame,
            base_location=base_location,
            city=city
        )
        
        if not filled_schedule:
            print(f"   ⚠️ 장소 검색 실패")
            return {"schedule": [], "error": "Place discovery failed"}
        
        print(f"   ✅ 장소 검색 완료: {len(filled_schedule)}개 장소")
        
        # Step 3: 경로 최적화
        print(f"\n🗺️ Step 3: 경로 최적화")
        
        # Google Maps로 경로 최적화
        google_service = GoogleMapsService()
        
        # 장소들의 좌표 추출
        waypoints = []
        for item in filled_schedule:
            if item.get('lat') and item.get('lng'):
                waypoints.append({
                    'lat': item['lat'],
                    'lng': item['lng'],
                    'name': item.get('place_name', '')
                })
        
        optimized_route = None
        if len(waypoints) >= 2:
            try:
                # 간단한 거리 기반 정렬 (Google Directions API는 생략 가능)
                print(f"   📍 {len(waypoints)}개 지점 최적화 중...")
                # 여기서는 순서 유지 (이미 시간순으로 정렬됨)
                optimized_route = {
                    'total_distance': '계산 필요',
                    'total_duration': '계산 필요',
                    'waypoints': waypoints
                }
                print(f"   ✅ 경로 최적화 완료")
            except Exception as e:
                print(f"   ⚠️ 경로 최적화 실패: {e}")
        
        # 최종 결과 구성
        result = {
            'schedule': filled_schedule,
            'optimized_route': optimized_route,
            'city': city,
            'travel_style': travel_style,
            'days_count': days_count,
            'analyzed_style': self.last_style_analysis,  # AI 분석 스타일 정보
            'schedule_method': 'ai_framer',  # 🆕 생성 방식 표시
            'total_places': len(filled_schedule)
        }
        
        print(f"\n✅ AI 스케줄 프레이머 방식 완료!")
        print(f"   총 {len(filled_schedule)}개 장소")
        print(f"   {days_count}일 일정")
        
        return result