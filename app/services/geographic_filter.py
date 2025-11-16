"""
지리적 필터링 레이어 (Geographic Filtering Layer)

좌표 기반으로 검색 결과를 필터링하여
요청 지역 외의 장소를 제거합니다.
"""

from typing import Dict, Any, List
from math import radians, sin, cos, sqrt, atan2


class GeographicFilter:
    """좌표 기반 실시간 필터링"""
    
    def filter_by_distance(
        self, 
        places: List[Dict[str, Any]], 
        center_lat: float, 
        center_lng: float, 
        radius_km: float,
        location_text: str = ""
    ) -> List[Dict[str, Any]]:
        """
        중심점으로부터 반경 내 장소만 필터링
        
        Args:
            places: 검색된 장소 리스트
            center_lat: 중심점 위도
            center_lng: 중심점 경도
            radius_km: 반경 (km)
            location_text: 로깅용 지역명
        
        Returns:
            필터링된 장소 리스트 (거리순 정렬)
        """
        if not center_lat or not center_lng:
            print(f"⚠️ 중심 좌표가 없어 지리적 필터링을 건너뜁니다.")
            return places
        
        filtered = []
        excluded = []
        
        for place in places:
            # 장소 좌표 추출 (여러 소스에서 시도)
            place_lat = (
                place.get('lat') or 
                place.get('google_info', {}).get('lat') or
                place.get('mapx')  # 네이버 API
            )
            place_lng = (
                place.get('lng') or 
                place.get('google_info', {}).get('lng') or
                place.get('mapy')  # 네이버 API
            )
            
            # 네이버 좌표 변환 (카텍좌표 → WGS84)
            if isinstance(place_lat, str):
                try:
                    place_lat = self._convert_naver_coord(float(place_lat), 'lat')
                except:
                    place_lat = None
            
            if isinstance(place_lng, str):
                try:
                    place_lng = self._convert_naver_coord(float(place_lng), 'lng')
                except:
                    place_lng = None
            
            if not (place_lat and place_lng):
                # 좌표가 없는 장소는 제외
                print(f"   ⚠️ 좌표 없음: {place.get('name', 'Unknown')}")
                continue
            
            # 거리 계산
            distance = self._haversine_distance(
                center_lat, center_lng, place_lat, place_lng
            )
            
            # 반경 내 여부 확인
            if distance <= radius_km:
                place['distance_from_center_km'] = round(distance, 2)
                place['within_requested_area'] = True
                filtered.append(place)
            else:
                place['distance_from_center_km'] = round(distance, 2)
                place['within_requested_area'] = False
                excluded.append(place)
        
        # 로깅
        print(f"\n📍 지리적 필터링 결과 ({location_text}):")
        print(f"   중심 좌표: ({center_lat:.4f}, {center_lng:.4f})")
        print(f"   검색 반경: {radius_km}km")
        print(f"   ✅ 포함: {len(filtered)}개")
        print(f"   ❌ 제외: {len(excluded)}개")
        
        if excluded:
            print(f"\n   제외된 장소 (요청 지역 외):")
            for place in excluded[:5]:  # 상위 5개만
                print(f"      - {place.get('name', 'Unknown')}: {place['distance_from_center_km']}km")
        
        # 거리순 정렬 (가까운 순)
        filtered.sort(key=lambda x: x['distance_from_center_km'])
        
        return filtered
    
    def calculate_distance(
        self, 
        lat1: float, 
        lng1: float, 
        lat2: float, 
        lng2: float
    ) -> float:
        """
        두 좌표 간 거리 계산 (km) - Public API
        """
        return self._haversine_distance(lat1, lng1, lat2, lng2)
    
    def _haversine_distance(
        self, 
        lat1: float, 
        lng1: float, 
        lat2: float, 
        lng2: float
    ) -> float:
        """
        Haversine 공식으로 두 좌표 간 거리 계산 (km)
        
        지구를 구로 가정하여 두 점 사이의 대원 거리(great-circle distance) 계산
        """
        R = 6371  # 지구 반지름 (km)
        
        # 라디안 변환
        lat1_rad = radians(lat1)
        lng1_rad = radians(lng1)
        lat2_rad = radians(lat2)
        lng2_rad = radians(lng2)
        
        # 차이 계산
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        # Haversine 공식
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlng/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        distance = R * c
        
        return distance
    
    def _convert_naver_coord(self, coord: float, coord_type: str) -> float:
        """
        네이버 좌표계(카텍) → WGS84 변환 (간이 버전)
        
        실제로는 더 정교한 변환이 필요하지만, 
        근사값으로 처리 (네이버 API가 이미 WGS84로 제공하는 경우가 많음)
        """
        # 네이버 로컬 API는 이미 WGS84 좌표계를 사용하므로
        # 변환 없이 그대로 반환
        return coord
    
    def add_distance_scores(
        self, 
        places: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        거리 기반 점수 추가 (가까울수록 높은 점수)
        
        Score = 10 * (1 - distance / max_distance)
        """
        if not places:
            return places
        
        max_distance = max(p.get('distance_from_center_km', 0) for p in places)
        
        if max_distance == 0:
            max_distance = 1  # 0으로 나누기 방지
        
        for place in places:
            distance = place.get('distance_from_center_km', 0)
            
            # 거리 점수 (0~10점)
            distance_score = 10 * (1 - distance / max_distance)
            place['distance_score'] = round(distance_score, 2)
        
        return places
    
    def rerank_by_distance_and_rating(
        self, 
        places: List[Dict[str, Any]],
        distance_weight: float = 0.4,
        rating_weight: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        거리와 평점을 결합한 종합 점수로 재정렬
        
        Args:
            places: 장소 리스트
            distance_weight: 거리 점수 가중치 (0~1)
            rating_weight: 평점 가중치 (0~1)
        
        Returns:
            재정렬된 장소 리스트
        """
        # 거리 점수 추가
        places = self.add_distance_scores(places)
        
        for place in places:
            # 평점 추출 (여러 소스 시도)
            rating = (
                place.get('rating') or
                place.get('google_info', {}).get('rating') or
                0
            )
            
            # 평점 정규화 (0~10점)
            normalized_rating = (rating / 5.0) * 10 if rating > 0 else 0
            
            # 거리 점수
            distance_score = place.get('distance_score', 5)
            
            # 종합 점수
            final_score = (
                distance_score * distance_weight +
                normalized_rating * rating_weight
            )
            
            place['final_score'] = round(final_score, 2)
        
        # 종합 점수로 정렬
        places.sort(key=lambda x: x.get('final_score', 0), reverse=True)
        
        print(f"\n🏆 종합 점수 기반 재정렬 완료:")
        print(f"   가중치 - 거리: {distance_weight}, 평점: {rating_weight}")
        
        for i, place in enumerate(places[:5], 1):
            print(f"   {i}. {place.get('name', 'Unknown')}")
            print(f"      거리: {place.get('distance_from_center_km', 0)}km")
            print(f"      평점: {place.get('rating', 0)}/5.0")
            print(f"      종합 점수: {place.get('final_score', 0)}/10.0")
        
        return places
    
    def filter_by_address(
        self,
        places: List[Dict[str, Any]],
        required_district: str = None,
        required_neighborhood: str = None
    ) -> List[Dict[str, Any]]:
        """
        주소 텍스트 기반 추가 필터링
        
        좌표가 부정확한 경우를 대비한 보조 필터
        """
        if not (required_district or required_neighborhood):
            return places
        
        filtered = []
        
        for place in places:
            address = place.get('address', '') or place.get('google_info', {}).get('address', '')
            
            # 주소가 없으면 제외
            if not address:
                continue
            
            # 구 필터링
            if required_district and required_district not in address:
                print(f"   ❌ 주소 불일치 (구): {place.get('name')} - {address}")
                continue
            
            # 동 필터링
            if required_neighborhood and required_neighborhood not in address:
                print(f"   ❌ 주소 불일치 (동): {place.get('name')} - {address}")
                continue
            
            filtered.append(place)
        
        return filtered

