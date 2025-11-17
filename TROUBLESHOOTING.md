# 🔧 트러블슈팅 가이드

## 🚨 "결과가 표시되지 않고 빈 페이지로 돌아감" 문제

### 증상
- API 처리 완료 (로그: "📡 Naver Blog API 호출...")
- 결과가 표시되지 않음
- 빈 페이지로 돌아감

### 원인 진단

#### 1단계: 브라우저 콘솔 확인 (F12)

```javascript
// 다음 에러가 있는지 확인:
- Uncaught TypeError
- Cannot read property
- displayResults is not defined
- 기타 빨간색 에러 메시지
```

#### 2단계: 네트워크 탭 확인

```
1. F12 → Network 탭
2. 여행 계획 생성 버튼 클릭
3. /api/travel/plan 요청 확인
4. Response 탭에서 응답 데이터 확인
   - Status: 200 OK인지?
   - Response body에 itinerary 있는지?
```

#### 3단계: 로그 확인

Docker 로그:
```bash
docker-compose logs -f app | grep -A 10 "완료"
```

### 일반적인 해결 방법

#### 방법 1: 브라우저 캐시 완전 삭제
```
Cmd + Shift + R (Mac)
Ctrl + Shift + R (Windows)

또는 시크릿 모드로 테스트
```

#### 방법 2: API 응답 구조 확인

Console에서:
```javascript
// API 응답 후 다음 명령어 실행
console.log(currentTravelPlan);
console.log(document.getElementById('results'));
```

#### 방법 3: displayResults 함수 에러 확인

script.js 3355번 라인 주변에 try-catch 추가:
```javascript
async function displayResults(data) {
    try {
        console.log('📊 displayResults 시작:', data);
        // ... 기존 코드
    } catch (error) {
        console.error('❌ displayResults 에러:', error);
        alert('결과 표시 중 오류: ' + error.message);
    }
}
```

### 자주 발생하는 케이스

#### Case 1: itinerary가 빈 배열
```
원인: AI가 일정을 생성하지 못함
해결: 백엔드 로그 확인
```

#### Case 2: displayResults 함수 에러
```
원인: data 구조가 예상과 다름
해결: console.log(data) 확인
```

#### Case 3: CSS 문제
```
원인: results 요소가 hidden 상태로 남음
해결: 
document.getElementById('results').classList.remove('hidden');
```

---

## 🧪 디버깅 체크리스트

### 브라우저 콘솔에서 실행:

```javascript
// 1. API 요청 확인
fetch('/api/travel/config')
  .then(r => r.json())
  .then(d => console.log('Config:', d));

// 2. 결과 영역 확인
console.log('Results element:', document.getElementById('results'));

// 3. 로딩 상태 확인
console.log('Loading hidden:', document.getElementById('loading').classList.contains('hidden'));
```

### Docker 로그 확인:

```bash
# 에러 로그 필터
docker-compose logs app | grep -i error

# 최근 100줄
docker-compose logs --tail=100 app

# 실시간 로그
docker-compose logs -f app
```

---

## 💡 즉시 해결 방법

### 임시 수정: hideLoading() 후 results 강제 표시

script.js의 displayResults 함수 시작 부분에 추가:
```javascript
async function displayResults(data) {
    console.log('🎯 displayResults 호출됨:', data);
    
    hideLoading();
    
    // 강제로 results 표시
    const resultsElement = document.getElementById('results');
    if (resultsElement) {
        resultsElement.classList.remove('hidden');
        console.log('✅ results 영역 표시');
    } else {
        console.error('❌ results 요소를 찾을 수 없음!');
    }
    
    // ... 나머지 코드
}
```

---

## 🚀 다음 단계

1. **브라우저 콘솔 스크린샷** 캡처해서 보여주시면 정확한 원인 파악 가능
2. **네트워크 탭 Response** 확인
3. **Docker 로그**에서 에러 확인

어느 것이든 정보를 주시면 정확한 해결책을 제시하겠습니다!

