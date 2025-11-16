# 일정 다양성 개선 구현 완료

## 구현 날짜
2025-11-16

## 구현 내용

### 1. 긴급 버그 수정 ✅
- **문제**: 순천 추천 요청 시 서울 관광지가 추천되는 버그
- **원인**: `enhanced_place_discovery_service.py`에서 도시 오버라이드("Auto" → "순천")가 `openai_service.py`로 전달되지 않음
- **해결책**:
  - `enhanced_place_discovery_service.py`: 반환값에 `resolved_city` 필드 추가
  - `openai_service.py`: AI가 추출한 실제 도시명 사용 (라인 247-251)
  - AI 프롬프트에 올바른 도시명 검증 로그 추가 (라인 522)

### 2. AI 스케줄 프레이머 도입 ✅
새 파일: `app/services/ai_schedule_framer.py`

**핵심 기능**:
- AI가 시간대별 활동 계획의 "틀" 생성 (장소명 제외)
- 시간대별로 적절한 장소 유형 자동 결정 (맛집, 카페, 관광지 등)
- 다양성 보장: 같은 유형이 연속되지 않도록
- Redis 캐싱으로 성능 최적화 (TTL: 7일)

**폴백 메커니즘**:
- AI 실패 시 규칙 기반 프레임 생성
- 패턴: 관광 → 점심 → 카페 → 관광 → 저녁

### 3. 순차적 장소 검색 로직 ✅
`enhanced_place_discovery_service.py`에 추가:
- `discover_places_sequential()`: 스케줄 틀을 순회하며 실제 장소 검색
- `_search_places_nearby()`: 특정 위치 근처에서 키워드로 장소 검색
- 이전 위치 기준 근처 검색으로 동선 최적화
- 중복 방지 메커니즘

### 4. OpenAI Service 리팩토링 ✅
`openai_service.py` 수정:

**새로운 방식 (환경 변수로 전환 가능)**:
```python
USE_SCHEDULE_FRAMER=true  # 기본값
```

**3단계 파이프라인**:
1. AI 스케줄 프레이머: 시간대별 활동 계획 "틀" 생성
2. 순차적 장소 검색: 틀에 맞춰 실제 장소 채우기
3. 경로 최적화: Google Maps로 최종 경로 최적화

**새 메서드**: `_generate_with_schedule_framer()` (라인 1455-1598)

### 5. 도보 경로 렌더링 ✅
`frontend/script.js` 수정:

**자동 이동 수단 선택 (거리 기반)**:
- 0.5km 이하: 도보 🚶
- 5km 이하: 대중교통 🚇
- 5km 이상: 자동차 🚗

**새 함수**:
- `calculateTotalDistance()`: Haversine 공식으로 총 거리 계산
- `updateRouteWithMode()`: 이동 수단 변경 시 경로 재렌더링

### 6. 이동 수단 선택 UI ✅
`frontend/index.html` + `frontend/script.js`

**UI 컴포넌트**:
- 3개 버튼: 대중교통 / 자동차 / 도보
- 자동 선택 정보 표시
- 수동 선택 시 실시간 경로 업데이트

**색상 코딩**:
- 대중교통: 파란색 (#4285F4)
- 자동차: 빨간색 (#EA4335)
- 도보: 초록색 (#34A853)

## 환경 변수 설정

`.env` 파일에 추가할 내용:

```bash
# AI 스케줄 프레이머 사용 여부 (기본값: true)
USE_SCHEDULE_FRAMER=true

# 기존 환경 변수 유지
OPENAI_API_KEY=your_openai_api_key
REDIS_HOST=localhost
REDIS_PORT=6379
NAVER_CLIENT_ID=your_naver_client_id
NAVER_CLIENT_SECRET=your_naver_client_secret
GOOGLE_MAPS_API_KEY=your_google_maps_api_key
```

## 서버 시작 방법

### 1. Redis 시작 (필수)
```bash
docker-compose up -d redis
# 또는
redis-server
```

### 2. Python 서버 시작
```bash
cd /Users/jh.choi/Documents/venv/travel-recommend-korea
python -m uvicorn app.main:app --reload
```

### 3. 프론트엔드 접속
브라우저에서 `http://localhost:8000` 또는 `http://localhost:8000/index.html` 접속

## 테스트 시나리오

### 시나리오 1: 순천 2박3일 여행
**입력**:
```
프롬프트: "전남 순천에서 2박3일 여행 추천해줘"
시작일: 2025-12-05
종료일: 2025-12-07
시작 시간: 09:00
종료 시간: 18:00
```

**예상 결과**:
- ✅ 도시: 순천 (서울 X)
- ✅ 다양한 장소 유형: 관광지 → 맛집 → 카페 → 관광지
- ✅ 시간대별 적절한 추천:
  - 11:00-13:00: 맛집
  - 13:30-15:00: 카페
  - 15:00-18:00: 관광지
  - 18:00-20:00: 저녁 맛집

### 시나리오 2: 부산 1박2일 실외 데이트
**입력**:
```
프롬프트: "부산에서 1박2일 실외 데이트 코스 짜줘"
시작일: 2025-11-08
종료일: 2025-11-09
```

**예상 결과**:
- ✅ 실외 장소 우선: 해변, 공원, 산책로
- ✅ 숙박 포함
- ✅ 오후/저녁 스케줄 포함
- ✅ 도보/대중교통 자동 선택

### 시나리오 3: 이동 수단 변경
**테스트 순서**:
1. 여행 계획 생성
2. 지도에서 경로 확인
3. "이동 수단" UI에서 버튼 클릭
4. 경로가 선택한 수단으로 재렌더링되는지 확인

## 알려진 제한사항

1. **GPT-5 API 비용**: 새로운 방식은 AI 호출이 많아 비용 증가 가능
   - 해결책: Redis 캐싱으로 완화

2. **Google Maps API 제한**: Directions API 호출 횟수 제한
   - 해결책: 필요 시에만 호출

3. **폴백 모드**: AI 실패 시 기존 방식으로 자동 전환
   - 환경 변수: `USE_SCHEDULE_FRAMER=false`

## 파일 변경 목록

### 새로 생성된 파일
- `app/services/ai_schedule_framer.py` (370줄)

### 수정된 파일
- `app/services/enhanced_place_discovery_service.py` (+165줄)
- `app/services/openai_service.py` (+156줄)
- `frontend/script.js` (+148줄)
- `frontend/index.html` (+22줄)

## 다음 단계 (선택사항)

1. **성능 최적화**: 
   - AI 호출 병렬화
   - 더 공격적인 캐싱 전략

2. **사용자 피드백 수집**:
   - 추천 만족도 평가
   - 선호하는 장소 유형 학습

3. **고급 기능**:
   - 사용자 맞춤형 추천 (이전 여행 기록 기반)
   - 실시간 혼잡도 반영
   - 날씨 변화 시 대안 일정 자동 생성

## 롤백 방법

새로운 방식이 문제가 있을 경우:

```bash
# .env 파일 수정
USE_SCHEDULE_FRAMER=false

# 서버 재시작
python -m uvicorn app.main:app --reload
```

기존 키워드 기반 방식으로 자동 전환됩니다.

