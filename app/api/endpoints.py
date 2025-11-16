"""
API 엔드포인트 정의

여행 계획 생성, 장소 검색, 날씨 조회 등
모든 API 엔드포인트를 정의합니다.
"""

from datetime import datetime
from typing import Dict, Any, Optional, Union, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

import os
from dotenv import load_dotenv
load_dotenv()  # .env 파일 로드

from app.services.openai_service import OpenAIService
from app.services.notion_service import NotionService
from app.services.naver_service import NaverService
from app.services.google_maps_service import GoogleMapsService
from app.services.weather_service import WeatherService
from app.services.realtime_transport_service import RealtimeTransportService

# 상수 정의
DEFAULT_COORDINATES = {"lat": 37.5665, "lng": 126.9780}

router = APIRouter()

# =============================================================================
# Request/Response 모델 정의
# =============================================================================

class TravelPlanRequest(BaseModel):
    """여행 계획 생성 요청"""
    prompt: str = Field(
        ..., 
        description="자연어 여행 계획 요청",
        example="서울에서 6시간 맛집 위주로 가족 여행"
    )
    user_id: Optional[str] = Field(
        None,
        description="사용자 ID (선택사항)",
        example="user123"
    )
    preferences: Optional[Dict[str, Any]] = Field(
        None,
        description="추가 선호사항",
        example={
            "budget": 200000,
            "activity_level": "relaxed",
            "food_preferences": ["korean", "cafe"],
            "avoid_crowds": True
        }
    )

class ItineraryItem(BaseModel):
    """일정 항목"""
    time: str = Field(..., description="시간", example="09:00")
    name: str = Field(..., description="장소명", example="경복궁")
    activity: str = Field(..., description="활동", example="궁궐 관람")
    location: str = Field(..., description="주소", example="서울시 종로구")
    duration: str = Field(..., description="소요시간", example="30분")
    description: Optional[str] = Field(None, description="설명")
    transportation: Optional[str] = Field(None, description="대중교통 정보")
    rating: Optional[float] = Field(None, description="평점")
    price: Optional[str] = Field(None, description="비용")
    lat: Optional[float] = Field(None, description="위도")
    lng: Optional[float] = Field(None, description="경도")
    blog_reviews: Optional[List[Dict]] = Field(None, description="네이버 블로그 후기 목록")
    blog_contents: Optional[List[Dict]] = Field(None, description="블로그 내용 전문")
    verified: Optional[bool] = Field(None, description="실제 장소 검증 여부")
    verification_status: Optional[str] = Field(None, description="검증 상태")
    google_info: Optional[Dict] = Field(None, description="Google Places 정보")
    naver_info: Optional[Dict] = Field(None, description="Naver 정보")
    
    class Config:
        extra = "allow"  # 추가 필드 허용

class TravelPlanResponse(BaseModel):
    """여행 계획 생성 응답"""
    plan_id: str = Field(..., description="생성된 계획 ID")
    title: str = Field(..., description="여행 계획 제목")
    summary: str = Field(..., description="계획 요약")
    itinerary: List[ItineraryItem] = Field(..., description="상세 일정")
    total_cost: Union[int, Dict[str, Any]] = Field(..., description="총 예상 비용")
    route_info: Optional[Dict[str, Any]] = Field(None, description="경로 정보")
    notion_url: Optional[str] = Field(None, description="Notion 페이지 URL")
    notion_saved: bool = Field(False, description="Notion 저장 성공 여부")
    notion_error: Optional[str] = Field(None, description="Notion 저장 오류")
    weather_info: Optional[Dict[str, Any]] = Field(None, description="날씨 정보")
    processing_metadata: Optional[Dict[str, Any]] = Field(None, description="8단계 처리 메타데이터")
    created_at: str = Field(..., description="생성 시간")





# =============================================================================
# 헬퍼 함수들
# =============================================================================

async def _generate_8step_itinerary(request: TravelPlanRequest) -> Dict[str, Any]:
    """8단계 아키텍처로 여행 일정 생성"""
    openai_service = OpenAIService()
    ai_itinerary = await openai_service.generate_detailed_itinerary(
        prompt=request.prompt,
        trip_details=request.preferences or {}
    )
    print(f"8단계 처리된 일정 생성: {len(ai_itinerary.get('schedule', []))}개 항목")
    return ai_itinerary

async def _process_8step_itinerary(ai_itinerary: Dict[str, Any]) -> tuple:
    """8단계 처리된 일정 데이터 가공"""
    sample_itinerary = []
    locations_for_route = []
    
    # 8단계 처리 메타데이터 추출
    processing_metadata = ai_itinerary.get('processing_metadata', {})
    
    for item in ai_itinerary.get('schedule', []):
        itinerary_item = ItineraryItem(
            time=item.get('time', '09:00'),
            name=item.get('place_name', ''),
            activity=item.get('activity', ''),
            location=item.get('address', ''),
            duration=item.get('duration', '30분'),
            description=item.get('description', ''),
            transportation=item.get('transportation', ''),
            rating=item.get('rating', 4.0),
            price=item.get('price', '무료'),
            lat=item.get('lat', DEFAULT_COORDINATES['lat']),
            lng=item.get('lng', DEFAULT_COORDINATES['lng'])
        )
        
        # 8단계 처리 데이터 반영
        if hasattr(itinerary_item, '__dict__'):
            itinerary_item.__dict__.update({
                'verified': item.get('verified', False),
                'verification_status': item.get('verification_status', 'unknown'),
                'blog_reviews': item.get('blog_reviews', []),
                'blog_contents': item.get('blog_contents', []),
                'google_info': item.get('google_info', {}),
                'naver_info': item.get('naver_info', {}),
                'processing_step': '8step_verified'
            })
        
        sample_itinerary.append(itinerary_item)
        locations_for_route.append({
            'name': item.get('place_name', ''),
            'lat': item.get('lat', DEFAULT_COORDINATES['lat']),
            'lng': item.get('lng', DEFAULT_COORDINATES['lng'])
        })
    
    # 경로 최적화 및 실시간 대중교통 정보
    maps_service = GoogleMapsService()
    transport_service = RealtimeTransportService()
    
    print(f"🗺️ 경로 최적화 시작: {len(locations_for_route)}개 장소")
    optimized_route = await maps_service.get_optimized_route(locations_for_route)
    print(f"✅ 경로 최적화 완료: {optimized_route.get('total_distance', 'N/A')}")
    
    # 실시간 대중교통 정보 추가
    if locations_for_route:
        first_location = locations_for_route[0]['name']
        last_location = locations_for_route[-1]['name'] if len(locations_for_route) > 1 else first_location
        realtime_transport = await transport_service.get_optimal_route_with_realtime(first_location, last_location)
        optimized_route['realtime_transport'] = realtime_transport
    
    # 경로 정보 및 실시간 대중교통 정보 반영
    if optimized_route.get('route_segments'):
        for i, segment in enumerate(optimized_route['route_segments']):
            if i < len(sample_itinerary):
                sample_itinerary[i].__dict__.update({
                    'route_distance': segment.get('distance', ''),
                    'route_duration': segment.get('duration', ''),
                    'route_steps': segment.get('steps', []),
                    'realtime_transport': optimized_route.get('realtime_transport', {})
                })
    
    return sample_itinerary, optimized_route

async def _get_weather_info(city: str) -> Dict[str, Any]:
    """실시간 날씨 정보 조회"""
    weather_service = WeatherService()
    return await weather_service.get_current_weather(city)

async def _save_to_notion(request: TravelPlanRequest, itinerary: List, route_info: Dict) -> tuple:
    notion_service = NotionService()
    notion_saved = False
    notion_url = None
    notion_error = None
    
    try:
        total_cost = _calculate_total_cost(itinerary)
        notion_data = {
            "title": f"🇰🇷 AI 추천 여행 계획 - {request.prompt[:20]}...",
            "summary": "실제 API 연동으로 검증된 장소들과 최적화된 경로로 구성된 맞춤형 여행 계획입니다.",
            "itinerary": [item.__dict__ if hasattr(item, '__dict__') else item for item in itinerary],
            "total_cost": total_cost,
            "route_info": route_info
        }
        notion_url = notion_service.create_travel_plan_page(notion_data)
        notion_saved = True
        print(f"Notion 저장 성공: {notion_url}")
    except Exception as e:
        notion_error = str(e)
        print(f"Notion 저장 오류: {str(e)}")
    
    return notion_url, notion_saved, notion_error

def _calculate_total_cost(itinerary: List) -> int:
    total_cost = 0
    for item in itinerary:
        # 딕셔너리와 객체 모두 처리
        if isinstance(item, dict):
            price = item.get('price')
        else:
            price = getattr(item, 'price', None)
            
        if price and price != '무료':
            try:
                cost_str = str(price).replace('원', '').replace(',', '').strip()
                if cost_str.isdigit():
                    total_cost += int(cost_str)
            except:
                pass
    return total_cost

def _create_response(plan_id: str, request: TravelPlanRequest, itinerary: List, total_cost: int, route_info: Dict, notion_url: str, notion_saved: bool, notion_error: str, weather_info: Dict, processing_metadata: Dict = None) -> TravelPlanResponse:
    response_data = {
        "plan_id": plan_id,
        "title": f"🇰🇷 AI 추천 여행 계획 - {request.prompt[:20]}...",
        "summary": "8단계 아키텍처로 처리된 실제 API 연동 및 검증된 장소들로 구성된 맞춤형 여행 계획입니다.",
        "itinerary": itinerary,
        "total_cost": {
            'amount': total_cost,
            'currency': 'KRW'
        },
        "route_info": route_info,  # 경로 정보를 최상위로 이동
        "notion_url": notion_url,
        "notion_saved": notion_saved,
        "notion_error": notion_error,
        "weather_info": weather_info,
        "created_at": datetime.now().isoformat()
    }
    
    # 8단계 처리 메타데이터 추가
    if processing_metadata:
        response_data["processing_metadata"] = processing_metadata
    
    return TravelPlanResponse(**response_data)

# =============================================================================
# 메인 API 엔드포인트
# =============================================================================

@router.post("/plan", response_model=TravelPlanResponse)
async def create_travel_plan(
    request: TravelPlanRequest,
    background_tasks: BackgroundTasks
):
    """
    🚀 **8단계 최적화 여행 계획 생성**
    
    자연어 프롬프트를 8단계로 처리하여 최적화된 여행 계획을 생성합니다.
    
    ### 8단계 처리 과정:
    1. 🔍 **스마트 크롤링**: 네이버 검색으로 실제 장소 수집 + 1개월 캐시
    2. 🌦️ **날씨 분석**: 지정 일자 날씨 기반 실내/실외 필터링
    3. 🤖 **AI 종합 분석**: 장소+날씨+선호도 종합 추천
    4. ✅ **할루시네이션 제거**: 실제 존재 여부 재검증
    5. 🗺️ **최적 동선**: Google Maps 최단 경로 계산
    6. 📱 **UI 반영**: 실시간 지도 표시
    7. 🏢 **구역별 세분화**: 장기여행시 구역별 추가 크롤링
    8. 💾 **지능형 캐시**: PostgreSQL 1개월 데이터 보관
    
    ### 사용 예시:
    - "강남 맛집 3일 여행" → 강남 구역별 맛집 크롤링 + 날씨 고려
    - "제주도 비오는 날 데이트" → 실내 장소 우선 추천
    """
    try:
        import uuid
        plan_id = str(uuid.uuid4())
        
        # UI 설정값 추출 및 검증
        preferences = request.preferences or {}
        city = preferences.get('city', 'Seoul')
        travel_style = preferences.get('travel_style', 'custom')
        start_date = preferences.get('start_date')
        end_date = preferences.get('end_date')
        start_time = preferences.get('start_time', '09:00')
        end_time = preferences.get('end_time', '18:00')
        start_location = preferences.get('start_location', '')
        
        print(f"🚀 8단계 아키텍처 시작: {request.prompt}")
        print(f"📍 도시: {city}, 스타일: {travel_style}")
        print(f"⏰ 시간: {start_date} {start_time} ~ {end_date} {end_time}")
        print(f"🏠 출발지: {start_location}")
        
        # 8단계 아키텍처로 실제 여행 일정 생성
        ai_itinerary = await _generate_8step_itinerary(request)
        sample_itinerary, optimized_route = await _process_8step_itinerary(ai_itinerary)
        
        print(f"✅ 8단계 처리 완료: {len(sample_itinerary)}개 장소 생성")
        
        # Notion 저장은 사용자 선택에 따라 결정
        notion_url = None
        notion_saved = False
        notion_error = None
        
        # 비용 계산
        total_cost = _calculate_total_cost(sample_itinerary)
        
        # 날씨 정보 조회 (UI에서 설정한 도시 사용)
        from app.services.city_service import CityService
        city_service = CityService()
        weather_code = city_service.get_weather_code(city)
        weather_info = await _get_weather_info(weather_code)
        
        # 출발지 정보를 경로 최적화에 반영
        if start_location and optimized_route:
            optimized_route['start_location'] = start_location
        
        # 응답 생성 (ItineraryItem 객체를 딕셔너리로 변환)
        itinerary_dicts = []
        for item in sample_itinerary:
            if hasattr(item, '__dict__'):
                item_dict = item.__dict__.copy()
            else:
                item_dict = item
            itinerary_dicts.append(item_dict)
        
        # 8단계 처리 메타데이터 추가 (UI 설정값 포함)
        processing_metadata = {
            'total_verified_places': len(sample_itinerary),
            'matched_places': len([item for item in sample_itinerary if item.__dict__.get('verified', False)]),
            'cache_usage': ai_itinerary.get('cache_usage', {}),
            'weather_forecast': weather_info,
            'optimized_route': optimized_route,
            'ui_settings': {
                'city': city,
                'travel_style': travel_style,
                'start_date': start_date,
                'end_date': end_date,
                'start_time': start_time,
                'end_time': end_time,
                'start_location': start_location
            }
        }
        
        response = _create_response(plan_id, request, itinerary_dicts, total_cost, optimized_route, notion_url, notion_saved, notion_error, weather_info, processing_metadata)
        
        print(f"✅ 8단계 아키텍처 응답 생성 완료: {len(itinerary_dicts)}개 항목")
        return response
        
    except ValueError as ve:
        # 🆕 장소 0개 등 사용자 에러는 400으로 반환 (명확한 메시지)
        print(f"User error in create_travel_plan: {str(ve)}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # 시스템 에러는 500
        import traceback
        print(f"System error in create_travel_plan: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"계획 생성 중 시스템 오류: {str(e)}")

@router.get("/health")
async def health_check():
    """
    ❤️ **서비스 상태 확인**
    
    API 서버와 연결된 외부 서비스들의 상태를 확인합니다.
    """
    status = {
        "service": "Korean Travel Planner API",
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }
    
    # 기본 상태만 반환
    status["apis"] = {
        "openai": "configured" if os.getenv("OPENAI_API_KEY") else "missing",
        "google_maps": "configured" if os.getenv("GOOGLE_MAPS_API_KEY") else "missing",
        "notion": "configured" if os.getenv("NOTION_TOKEN") else "missing",
        "naver": "configured" if os.getenv("NAVER_CLIENT_ID") else "missing"
    }
    
    return status

@router.get("/config")
async def get_config():
    """
    🔧 **프론트엔드 설정**
    
    프론트엔드에서 필요한 API 키 등 설정 정보를 제공합니다.
    """
    return {
        "google_maps_api_key": os.getenv("GOOGLE_MAPS_API_KEY", "")
    }

@router.get("/config/notion-check")
async def check_notion_config():
    """
    🔍 **Notion 설정 자가 진단**
    
    Notion Integration 설정이 올바른지 자가 진단합니다.
    
    **진단 항목:**
    - NOTION_TOKEN 환경변수 설정 여부
    - NOTION_DATABASE_ID 환경변수 설정 여부
    - Database 접근 가능 여부
    - Integration 권한 확인
    
    **응답:**
    ```json
    {
        "success": true/false,
        "token_configured": true/false,
        "database_configured": true/false,
        "database_accessible": true/false,
        "error": "오류 메시지 (optional)",
        "solution": "해결 방법 (optional)"
    }
    ```
    """
    notion_service = NotionService()
    diagnosis_result = notion_service.diagnose_setup()
    
    return diagnosis_result

@router.post("/save-notion")
async def save_to_notion(request: dict):
    """
    💾 **Notion 저장**
    
    사용자가 선택적으로 Notion에 여행 계획을 저장합니다.
    """
    try:
        notion_service = NotionService()
        
        # 🆕 저장 전 설정 확인
        diagnosis = notion_service.diagnose_setup()
        if not diagnosis["success"]:
            return {
                "success": False,
                "error": diagnosis["error"],
                "solution": diagnosis["solution"],
                "message": f"Notion 설정 오류: {diagnosis['error']}"
            }
        
        # 여행 계획 데이터 구성
        notion_data = {
            "title": f"🇰🇷 AI 추천 여행 계획 - {datetime.now().strftime('%Y-%m-%d')}",
            "summary": "실제 API 연동으로 검증된 장소들과 최적화된 경로로 구성된 맞춤형 여행 계획입니다.",
            "itinerary": request.get('itinerary', []),
            "total_cost": request.get('total_cost', 0)
        }
        
        notion_url = notion_service.create_travel_plan_page(notion_data)
        
        # 🆕 mock URL 체크
        if "mock-page" in notion_url or "error-page" in notion_url:
            return {
                "success": False,
                "error": "Notion 설정이 완료되지 않았습니다",
                "solution": "/api/config/notion-check 엔드포인트를 통해 설정을 확인하세요",
                "message": "Notion 저장 실패: 설정을 확인해주세요"
            }
        
        return {
            "success": True,
            "url": notion_url,
            "message": "Notion에 성공적으로 저장되었습니다."
        }
        
    except Exception as e:
        print(f"Notion 저장 오류: {str(e)}")
        
        # 🆕 에러 타입별 구체적인 해결 방법 제시
        error_message = str(e)
        solution = "로그를 확인하거나 Notion 설정을 다시 점검하세요"
        
        if "404" in error_message:
            solution = "Notion에서 Integration에 데이터베이스를 공유했는지 확인하세요. 데이터베이스 페이지 우측 상단 '...' → 'Connections' → Integration 추가"
        elif "401" in error_message or "Unauthorized" in error_message:
            solution = "NOTION_TOKEN이 올바른지 확인하세요. Integration Token은 'secret_'로 시작해야 합니다"
        elif "timeout" in error_message.lower():
            solution = "네트워크 연결을 확인하거나 잠시 후 다시 시도하세요"
        
        return {
            "success": False,
            "error": error_message,
            "solution": solution,
            "message": f"Notion 저장 실패: {error_message}"
        }

@router.post("/route-directions")
async def get_route_directions(request: dict):
    """
    🗺️ **Google Maps 경로 안내**
    
    출발지에서 목적지까지의 실제 경로 정보를 조회합니다.
    
    **지원 모드**:
    - `transit`: 대중교통 (지하철, 버스)
    - `driving`: 자동차
    - `walking`: 도보
    
    **사용 예시**:
    ```json
    {
        "origin": "서울역",
        "destination": "경복궁",
        "mode": "transit"
    }
    ```
    
    **응답 데이터**:
    - 총 거리 및 소요 시간
    - 단계별 상세 안내
    - 대중교통 정보 (노선, 정류장 등)
    - 지도 표시를 위한 polyline 데이터
    """
    try:
        origin = request.get('origin')
        destination = request.get('destination')
        mode = request.get('mode', 'transit')
        
        if not origin or not destination:
            raise HTTPException(status_code=400, detail="출발지와 목적지를 모두 입력해주세요.")
        
        google_service = GoogleMapsService()
        
        # 모드 검증
        allowed_modes = ["transit", "driving", "walking"]
        if mode not in allowed_modes:
            raise HTTPException(
                status_code=400, 
                detail=f"지원되지 않는 모드입니다. 사용 가능: {', '.join(allowed_modes)}"
            )
        
        # Google Maps API로 경로 조회
        directions = await google_service.get_directions(
            origin=origin,
            destination=destination,
            mode=mode
        )
        
        # None 체크 추가
        if not directions:
            raise HTTPException(status_code=404, detail="경로를 찾을 수 없습니다.")
        
        if "error" in directions:
            raise HTTPException(status_code=404, detail=directions["error"])
        
        # 모드별 아이콘 및 설명 추가
        mode_info = {
            "transit": {"icon": "🚇", "name": "대중교통", "color": "#4285F4"},
            "driving": {"icon": "🚗", "name": "자동차", "color": "#34A853"},
            "walking": {"icon": "🚶", "name": "도보", "color": "#EA4335"}
        }
        
        return {
            "success": True,
            "mode": mode,
            "mode_info": mode_info[mode],
            "origin": origin,
            "destination": destination,
            "directions": directions,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        print(f"경로 조회 오류: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"경로 조회 중 오류 발생: {str(e)}")

@router.post("/multi-route-directions")
async def get_multi_route_directions(request: dict):
    """
    🗺️ **다중 모드 경로 비교**
    
    출발지에서 목적지까지 세 가지 모드(대중교통/자동차/도보)의 경로를 동시에 조회합니다.
    
    **사용 예시**:
    ```json
    {
        "origin": "서울역",
        "destination": "경복궁"
    }
    ```
    
    **응답 데이터**:
    - 세 가지 모드 모두의 경로 정보
    - 각 모드별 소요 시간 및 거리 비교
    - 추천 모드 (가장 빠른 경로)
    """
    try:
        origin = request.get('origin')
        destination = request.get('destination')
        
        if not origin or not destination:
            raise HTTPException(status_code=400, detail="출발지와 목적지를 모두 입력해주세요.")
        
        google_service = GoogleMapsService()
        
        # 세 가지 모드로 동시에 경로 조회
        import asyncio
        transit_task = google_service.get_directions(origin, destination, mode="transit")
        driving_task = google_service.get_directions(origin, destination, mode="driving")
        walking_task = google_service.get_directions(origin, destination, mode="walking")
        
        transit_result, driving_result, walking_result = await asyncio.gather(
            transit_task, driving_task, walking_task, return_exceptions=True
        )
        
        # 결과 포맷팅
        results = {
            "transit": {"icon": "🚇", "name": "대중교통", "data": transit_result if not isinstance(transit_result, Exception) else {"error": str(transit_result)}},
            "driving": {"icon": "🚗", "name": "자동차", "data": driving_result if not isinstance(driving_result, Exception) else {"error": str(driving_result)}},
            "walking": {"icon": "🚶", "name": "도보", "data": walking_result if not isinstance(walking_result, Exception) else {"error": str(walking_result)}}
        }
        
        # 추천 모드 결정 (가장 빠른 경로)
        valid_results = []
        for mode, info in results.items():
            if "error" not in info["data"]:
                duration_text = info["data"].get("total_duration", "")
                # "25분" 형식에서 숫자 추출
                import re
                duration_match = re.search(r'(\d+)', duration_text)
                if duration_match:
                    duration_minutes = int(duration_match.group(1))
                    valid_results.append((mode, duration_minutes))
        
        recommended_mode = min(valid_results, key=lambda x: x[1])[0] if valid_results else "transit"
        
        return {
            "success": True,
            "origin": origin,
            "destination": destination,
            "results": results,
            "recommended_mode": recommended_mode,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        print(f"다중 경로 조회 오류: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"다중 경로 조회 중 오류 발생: {str(e)}")


@router.post("/route-directions-naver")
async def get_route_directions_google(request: Dict[str, Any]):
    """
    **Google Maps API 기반 경로 조회**
    
    Google Maps API를 사용하여 정확한 경로 정보를 제공합니다.
    
    **요청 파라미터**:
    - origin: 출발지 (좌표: "lat,lng" 형식)
    - destination: 도착지 (좌표: "lat,lng" 형식)
    - mode: 이동 수단 ("transit", "walking", "driving")
    
    **응답 데이터**:
    - 경로 정보 (거리, 시간, 단계별 안내, polyline)
    - Google Maps 기반 정확한 경로
    """
    try:
        origin = request.get('origin')
        destination = request.get('destination')
        mode = request.get('mode', 'transit')
        
        if not origin or not destination:
            raise HTTPException(status_code=400, detail="출발지와 목적지를 모두 입력해주세요.")
        
        # Google Maps API 호출
        google_service = GoogleMapsService()
        result = await google_service.get_directions(origin, destination, mode)
        
        if not result.get('success'):
            raise HTTPException(status_code=400, detail=result.get('error', '경로를 찾을 수 없습니다.'))
        
        return {
            "success": True,
            "provider": "google",
            "directions": result,
            "mode_info": {
                "transit": {"icon": "🚇", "name": "대중교통"},
                "walking": {"icon": "🚶", "name": "도보"},
                "driving": {"icon": "🚗", "name": "자동차"}
            }.get(mode, {"icon": "🚇", "name": mode})
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        import traceback
        print(f"Google Maps 경로 조회 오류: {str(e)}")
        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"경로 조회 중 오류가 발생했습니다: {str(e)}")