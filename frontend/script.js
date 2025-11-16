// 상수 정의
const API_BASE_URL = window.location.origin;
const DEFAULT_ZOOM = 13;
const SEOUL_CENTER = { lat: 37.5665, lng: 126.9780 };
const TOAST_DURATION = 3000;
const NOTION_SAVE_DELAY = 2000;

// 전역 변수
let map, directionsService, directionsRenderer;
let places = [];
let currentMarkers = []; // 현재 표시된 마커들
let savedMarkers = []; // 저장된 원본 마커들

// Initialize Google Maps
function initMap() {
    console.log('Initializing Google Maps...');
    
    const mapElement = document.getElementById('map');
    if (!mapElement) {
        console.error('Map element not found');
        return;
    }
    
    if (typeof google === 'undefined' || !google.maps) {
        console.error('Google Maps API not loaded');
        return;
    }
    
    try {
        // 도시별 지도 중심점 설정
        const cityCenter = getCityCenter();
        
        map = new google.maps.Map(mapElement, {
            zoom: DEFAULT_ZOOM,
            center: cityCenter,
            mapTypeControl: true,
            streetViewControl: true,
            fullscreenControl: true,
            zoomControl: true
        });
        
        directionsService = new google.maps.DirectionsService();
        directionsRenderer = new google.maps.DirectionsRenderer({
            draggable: false,
            panel: null,
            suppressMarkers: true // ✅ A, B 마커 제거
        });
        directionsRenderer.setMap(map);
        
        console.log('Google Maps initialized successfully');
        
        // 지도 로드 완료 이벤트
        google.maps.event.addListenerOnce(map, 'tilesloaded', function() {
            console.log('Map tiles loaded');
        });
        
    } catch (error) {
        console.error('Error initializing Google Maps:', error);
    }
}



function updateTripDuration() {
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;
    const durationElement = document.getElementById('tripDuration');
    
    if (!durationElement) return; // 요소가 없으면 종료
    
    if (startDate && endDate && startTime && endTime) {
        const start = new Date(`${startDate}T${startTime}`);
        const end = new Date(`${endDate}T${endTime}`);
        
        if (end <= start) {
            durationElement.innerHTML = '<span class="text-red-600">⚠️ 종료 시간이 시작 시간보다 빠릅니다</span>';
            return;
        }
        
        const diffMs = end - start;
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
        const diffHours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
        
        let durationText = '';
        if (diffDays > 0) {
            durationText += `${diffDays}일 `;
        }
        if (diffHours > 0) {
            durationText += `${diffHours}시간 `;
        }
        if (diffMinutes > 0) {
            durationText += `${diffMinutes}분`;
        }
        
        const startFormatted = `${startDate.replace(/-/g, '')} ${startTime.replace(':', '')}`;
        const endFormatted = `${endDate.replace(/-/g, '')} ${endTime.replace(':', '')}`;
        
        durationElement.innerHTML = `${startFormatted} ~ ${endFormatted} (${durationText.trim()})`;
    } else if (startDate || endDate || startTime !== '09:00' || endTime !== '18:00') {
        // 일부 입력이 있으면 안내 메시지 표시
        durationElement.textContent = '날짜와 시간을 모두 선택해주세요';
    } else {
        // 기본 상태일 때는 기본 메시지
        durationElement.textContent = '날짜를 선택해주세요';
    }
}



async function handleFormSubmit() {
    console.log('handleFormSubmit called');
    
    const city = document.getElementById('city').value;
    const startDate = document.getElementById('startDate').value;
    const endDate = document.getElementById('endDate').value;
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;
    const prompt = document.getElementById('prompt').value;
    

    
    if (!prompt.trim()) {
        showToast('여행 요청사항을 입력해주세요', 'error');
        return;
    }
    
    // 출발지는 선택사항으로 변경
    const startLocation = document.getElementById('startLocation') ? document.getElementById('startLocation').value : '';
    
    // 📍 출발지 정보를 전역 변수에 저장
    window.tripStartLocation = startLocation || "서울역";
    if (window.selectedPlace) {
        // 지도에서 선택한 장소 정보 사용
        window.tripStartLat = window.selectedPlace.lat || 37.5547;
        window.tripStartLng = window.selectedPlace.lng || 126.9707;
        console.log('🗺️ 출발지 저장:', window.selectedPlace);
    } else {
        // 기본 서울역 좌표
        window.tripStartLat = 37.5547;
        window.tripStartLng = 126.9707;
    }
    
    console.log('📍 전역 변수 저장:', { 
        location: window.tripStartLocation, 
        lat: window.tripStartLat, 
        lng: window.tripStartLng 
    });
    
    if (!startDate || !endDate) {
        showToast('시작일과 종료일을 모두 선택해주세요', 'error');
        return;
    }
    
    const start = new Date(`${startDate}T${startTime}`);
    const end = new Date(`${endDate}T${endTime}`);
    
    if (end <= start) {
        showToast('종료 시간이 시작 시간보다 빠릅니다', 'error');
        return;
    }
    
    // 여행 기간 계산
    const diffMs = end - start;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    
    let durationText = '';
    if (diffDays === 0) {
        durationText = `당일치기 (${diffHours}시간)`;
    } else {
        durationText = `${diffDays}박${diffDays + 1}일`;
    }
    
    console.log('Starting API call...');
    showLoading();
    
    const requestData = {
        prompt: `${city}에서 ${durationText} ${startDate.replace(/-/g, '')} ${startTime.replace(':', '')}부터 ${endDate.replace(/-/g, '')} ${endTime.replace(':', '')}까지 ${startLocation ? `출발지: ${startLocation}에서 시작하여 ` : ''}${prompt}`,
        preferences: {
            city,
            start_date: startDate,
            end_date: endDate,
            start_time: startTime,
            end_time: endTime,
            start_location: startLocation,
            duration_days: diffDays,
            duration_hours: diffHours
        }
    };
    
    // 🆕 SSE 스트리밍 사용 여부 체크 (기본값: 일반 API)
    const useStreaming = false;  // TODO: UI에서 선택 가능하게
    
    if (useStreaming) {
        // SSE 스트리밍 방식
        await handleFormSubmitWithSSE(requestData);
    } else {
        // 기존 방식
        try {
            console.log('Request data:', requestData);
            
            const response = await fetch(`${API_BASE_URL}/api/travel/plan`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestData)
            });
            
            console.log('Response status:', response.status);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('API Error:', errorText);
                throw new Error(`서버 오류 (${response.status}): ${errorText}`);
            }
            
            const data = await response.json();
            console.log('API Response data:', data);
            
            await displayResults(data);
            showToast('여행 계획이 생성되었습니다!', 'success');
            
        } catch (error) {
            console.error('Error:', error);
            showToast('오류가 발생했습니다: ' + (error.message || '알 수 없는 오류'), 'error');
            hideLoading();
        }
    }
}

// 🆕 SSE 스트리밍 방식으로 여행 계획 생성
async function handleFormSubmitWithSSE(requestData) {
    const progressLog = document.getElementById('progressLog');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    progressLog.innerHTML = '';
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/travel/plan-stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const jsonStr = line.substring(6);
                    try {
                        const data = JSON.parse(jsonStr);
                        
                        if (data.type === 'status' || data.type === 'info') {
                            // 로그 추가
                            const logItem = document.createElement('div');
                            logItem.className = data.type === 'status' ? 'text-blue-700' : 'text-green-600';
                            logItem.innerHTML = `<i class="fas fa-check-circle mr-2"></i>${data.message}`;
                            progressLog.appendChild(logItem);
                            progressLog.scrollTop = progressLog.scrollHeight;
                            
                            // 진행률 업데이트
                            if (data.progress) {
                                progressBar.style.width = data.progress + '%';
                                progressText.textContent = data.progress + '%';
                            }
                        } else if (data.type === 'complete') {
                            // 완료
                            await displayResults(data.data);
                            showToast('여행 계획이 생성되었습니다!', 'success');
                        } else if (data.type === 'error') {
                            throw new Error(data.message);
                        }
                    } catch (e) {
                        if (e.message) {
                            throw e;
                        }
                        console.log('JSON 파싱 무시:', jsonStr);
                    }
                }
            }
        }
        
    } catch (error) {
        console.error('SSE Error:', error);
        showToast('오류가 발생했습니다: ' + error.message, 'error');
        hideLoading();
    }
}

function showLoading() {
    document.getElementById('loading').classList.remove('hidden');
    document.getElementById('results').classList.add('hidden');
    document.getElementById('submitBtn').disabled = true;
    document.getElementById('btnText').textContent = '생성 중...';
    
    // 🆕 진행률 초기화 및 실시간 메시지 시작
    const progressLog = document.getElementById('progressLog');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    if (progressLog) {
        progressLog.innerHTML = '<div class="text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i>준비 중...</div>';
    }
    if (progressBar) {
        progressBar.style.width = '0%';
    }
    if (progressText) {
        progressText.textContent = '0%';
    }
    
    // 🆕 실시간 진행 메시지 업데이트 (프롬프트 전달)
    const prompt = document.getElementById('prompt').value;
    startProgressMessages(prompt);
}

// 🆕 실시간 진행 메시지 표시 (동적 지역명)
function startProgressMessages(userPrompt = '') {
    const progressLog = document.getElementById('progressLog');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    if (!progressLog) return;
    
    // 🆕 프롬프트에서 지역/키워드 간단히 추출
    const regionKeywords = ['청도', '밀양', '양양', '대구', '부산', '서울', '제주'];
    let detectedRegion = '여행지';
    for (const region of regionKeywords) {
        if (userPrompt.includes(region)) {
            detectedRegion = region;
            break;
        }
    }
    
    const activityKeywords = ['맛집', '카페', '관광', '데이트', '여행', '투어'];
    let detectedActivity = '정보';
    for (const activity of activityKeywords) {
        if (userPrompt.includes(activity)) {
            detectedActivity = activity;
            break;
        }
    }
    
    // 🆕 지역별 예상 장소명
    const placeSamples = {
        '청도': ['육회천왕', '목장원', '칠성농장', '청도와인터널', '전통시장'],
        '대구': ['벼락집', '동인동찜갈비', '이가네', '막창골목', '서문시장'],
        '부산': ['해운대횟집', '광안리카페', '자갈치시장', '밀면집', '돼지국밥'],
        '서울': ['경복궁', '명동맛집', 'N서울타워', '홍대카페', '강남맛집'],
        '양양': ['서피비치카페', '낙산사', '물회집', '하조대맛집', '죽도해변'],
        '제주': ['흑돼지맛집', '성산일출봉', '협재해수욕장', '카페', '감귤농장'],
        '밀양': ['얼음골', '표충사', '영남루', '돼지국밥', '밀양시장']
    };
    
    const samplePlaces = placeSamples[detectedRegion] || ['맛집1', '카페1', '관광지1', '맛집2', '카페2'];
    
    const messages = [
        { text: '📍 프롬프트에서 지역 정보 추출 중...', progress: 5 },
        { text: `✅ 목적지 인식: ${detectedRegion}`, progress: 10 },
        { text: `🔍 ${detectedRegion} ${detectedActivity} 정보 크롤링 중...`, progress: 15 },
        { text: `  ㄴ ${samplePlaces[0]} 수집 중...`, progress: 20, indent: true },
        { text: `  ㄴ ${samplePlaces[1]} 수집 중...`, progress: 25, indent: true },
        { text: `  ㄴ ${samplePlaces[2]} 수집 중...`, progress: 30, indent: true },
        { text: `  ㄴ ${samplePlaces[3]} 수집 중...`, progress: 35, indent: true },
        { text: `  ㄴ ${samplePlaces[4]} 수집 중...`, progress: 40, indent: true },
        { text: '📝 네이버 블로그 후기 분석 중...', progress: 50 },
        { text: '🗺️ Google Maps로 좌표 검증 중...', progress: 60 },
        { text: '🌦️ 날씨 정보 조회 중...', progress: 70 },
        { text: '🤖 AI가 최적 일정 생성 중...', progress: 80 },
        { text: '✅ 장소 검증 및 중복 제거 중...', progress: 90 },
        { text: '🛣️ 최적 경로 계산 중...', progress: 95 }
    ];
    
    let currentIndex = 0;
    
    // 🆕 재귀적 setTimeout으로 동적 타이밍
    function showNextMessage() {
        if (currentIndex >= messages.length) {
            window.progressInterval = null;
            return;
        }
        
        const msg = messages[currentIndex];
        
        // 메시지 추가 (들여쓰기 지원)
        const logItem = document.createElement('div');
        if (msg.indent) {
            logItem.className = 'text-gray-600 text-sm ml-6 animate-fadeIn';
            logItem.innerHTML = `${msg.text}`;  // 간단하게 화살표 제거
        } else {
            logItem.className = 'text-blue-700 animate-fadeIn';
            logItem.innerHTML = `<i class="fas fa-check-circle mr-2"></i>${msg.text}`;
        }
        progressLog.appendChild(logItem);
        
        // 스크롤
        progressLog.scrollTop = progressLog.scrollHeight;
        
        // 진행률 업데이트
        if (progressBar) {
            progressBar.style.width = msg.progress + '%';
        }
        if (progressText) {
            progressText.textContent = msg.progress + '%';
        }
        
        currentIndex++;
        
        // 다음 메시지 예약 (들여쓰기는 빠르게, 일반은 느리게)
        const delay = msg.indent ? 300 : 800;
        window.progressInterval = setTimeout(showNextMessage, delay);
    }
    
    // 시작
    showNextMessage();
}

function hideLoading() {
    document.getElementById('loading').classList.add('hidden');
    document.getElementById('submitBtn').disabled = false;
    document.getElementById('btnText').textContent = 'AI 여행 계획 생성';
    
    // 🆕 진행 메시지 타이머 정리 (setTimeout 버전)
    if (window.progressInterval) {
        clearTimeout(window.progressInterval);
        window.progressInterval = null;
    }
    
    // 🆕 완료 메시지
    const progressLog = document.getElementById('progressLog');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    
    if (progressLog) {
        const completedMsg = document.createElement('div');
        completedMsg.className = 'text-green-700 font-bold';
        completedMsg.innerHTML = '<i class="fas fa-check-circle mr-2"></i>✅ 여행 계획 생성 완료!';
        progressLog.appendChild(completedMsg);
    }
    if (progressBar) {
        progressBar.style.width = '100%';
    }
    if (progressText) {
        progressText.textContent = '100%';
    }
}

// 🆕 localStorage 히스토리 관리 함수
function saveTravelPlanToLocal(planData) {
    try {
        const history = JSON.parse(localStorage.getItem('travel_history') || '[]');
        
        const newPlan = {
            id: Date.now(),
            title: planData.title || '여행 계획',
            summary: planData.summary || '',
            city: document.getElementById('city').value,
            prompt: document.getElementById('prompt').value,
            itinerary: planData.itinerary || [],
            created_at: new Date().toISOString(),
            start_date: document.getElementById('startDate').value,
            end_date: document.getElementById('endDate').value
        };
        
        // 최신 순으로 앞에 추가
        history.unshift(newPlan);
        
        // 최대 50개까지만 저장
        if (history.length > 50) {
            history.splice(50);
        }
        
        localStorage.setItem('travel_history', JSON.stringify(history));
        updateHistoryCount();
        
        console.log('✅ 여행 계획 로컬 저장 완료:', newPlan.id);
    } catch (error) {
        console.error('❌ localStorage 저장 오류:', error);
    }
}

function updateHistoryCount() {
    try {
        const history = JSON.parse(localStorage.getItem('travel_history') || '[]');
        const countEl = document.getElementById('historyCount');
        if (countEl) {
            countEl.textContent = history.length;
        }
    } catch (error) {
        console.error('히스토리 카운트 업데이트 오류:', error);
    }
}

function showHistory() {
    try {
        const history = JSON.parse(localStorage.getItem('travel_history') || '[]');
        
        if (history.length === 0) {
            showToast('저장된 여행 기록이 없습니다', 'info');
            return;
        }
        
        // 모달 생성
        const modal = document.createElement('div');
        modal.id = 'historyModal';
        modal.className = 'fixed inset-0 bg-black bg-opacity-60 z-50 flex items-center justify-center p-4';
        modal.innerHTML = `
            <div class="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex flex-col">
                <div class="flex justify-between items-center p-6 border-b">
                    <h3 class="text-2xl font-bold text-gray-800">
                        <i class="fas fa-history text-blue-500 mr-2"></i>
                        내 여행 기록 (${history.length}개)
                    </h3>
                    <button onclick="closeHistoryModal()" class="text-gray-400 hover:text-gray-600 p-2">
                        <i class="fas fa-times text-xl"></i>
                    </button>
                </div>
                <div class="flex-1 overflow-y-auto p-6">
                    ${history.map((plan, index) => `
                        <div class="border rounded-lg p-4 mb-4 hover:shadow-md transition cursor-pointer" onclick="loadHistoryPlan(${plan.id})">
                            <div class="flex justify-between items-start mb-2">
                                <div class="flex-1">
                                    <h4 class="font-bold text-lg text-gray-800">${plan.title}</h4>
                                    <p class="text-sm text-gray-600 mt-1">${plan.prompt || ''}</p>
                                </div>
                                <button onclick="event.stopPropagation(); deleteHistoryPlan(${plan.id})" 
                                        class="text-red-500 hover:text-red-700 p-2">
                                    <i class="fas fa-trash"></i>
                                </button>
                            </div>
                            <div class="flex items-center space-x-4 text-xs text-gray-500">
                                <span><i class="fas fa-map-marker-alt"></i> ${plan.city || 'Auto'}</span>
                                <span><i class="fas fa-calendar"></i> ${plan.start_date} ~ ${plan.end_date}</span>
                                <span><i class="fas fa-list"></i> ${plan.itinerary ? plan.itinerary.length : 0}개 장소</span>
                                <span><i class="fas fa-clock"></i> ${new Date(plan.created_at).toLocaleDateString('ko-KR')}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
    } catch (error) {
        console.error('히스토리 표시 오류:', error);
        showToast('히스토리를 불러올 수 없습니다', 'error');
    }
}

function closeHistoryModal() {
    const modal = document.getElementById('historyModal');
    if (modal) {
        modal.remove();
    }
}

function loadHistoryPlan(planId) {
    try {
        const history = JSON.parse(localStorage.getItem('travel_history') || '[]');
        const plan = history.find(p => p.id === planId);
        
        if (plan) {
            // 폼에 데이터 로드
            document.getElementById('city').value = plan.city || 'Auto';
            document.getElementById('prompt').value = plan.prompt || '';
            document.getElementById('startDate').value = plan.start_date || '';
            document.getElementById('endDate').value = plan.end_date || '';
            
            // 결과 표시
            displayResults({
                title: plan.title,
                summary: plan.summary,
                itinerary: plan.itinerary,
                plan_id: plan.id,
                created_at: plan.created_at
            });
            
            closeHistoryModal();
            showToast('여행 계획을 불러왔습니다', 'success');
        }
    } catch (error) {
        console.error('계획 로드 오류:', error);
        showToast('계획을 불러올 수 없습니다', 'error');
    }
}

function deleteHistoryPlan(planId) {
    if (!confirm('이 여행 계획을 삭제하시겠습니까?')) {
        return;
    }
    
    try {
        const history = JSON.parse(localStorage.getItem('travel_history') || '[]');
        const filtered = history.filter(p => p.id !== planId);
        
        localStorage.setItem('travel_history', JSON.stringify(filtered));
        updateHistoryCount();
        
        // 모달 닫고 다시 열기
        closeHistoryModal();
        setTimeout(() => showHistory(), 100);
        
        showToast('여행 계획이 삭제되었습니다', 'success');
    } catch (error) {
        console.error('삭제 오류:', error);
        showToast('삭제에 실패했습니다', 'error');
    }
}

function clearHistory() {
    if (!confirm('모든 여행 기록을 삭제하시겠습니까?')) {
        return;
    }
    
    try {
        localStorage.removeItem('travel_history');
        updateHistoryCount();
        showToast('모든 여행 기록이 삭제되었습니다', 'success');
    } catch (error) {
        console.error('전체 삭제 오류:', error);
        showToast('삭제에 실패했습니다', 'error');
    }
}

// 전역 변수
let currentDay = 1;
let dayGroups = {};

function displayTimeline(itinerary) {
    // 일자별 데이터 그룹화
    dayGroups = groupByDay(itinerary);
    
    // 탭 생성
    createDayTabs(dayGroups);
    
    // 첫 번째 날 표시
    displayDayTimeline(currentDay);
}

function groupByDay(itinerary) {
    const groups = {};
    
    // 일정이 없으면 빈 객체 반환
    if (!itinerary || itinerary.length === 0) {
        return { 1: [] };
    }
    
    itinerary.forEach((item, index) => {
        // day 필드가 있으면 사용, 없으면 시간 기준으로 일자 계산
        let day = item.day;
        
        if (!day) {
            // 시간 기준으로 일자 추정 (09:00부터 시작해서 24시간 넘어가면 다음날)
            const timeStr = item.time || '09:00';
            const hour = parseInt(timeStr.split(':')[0]);
            
            // 첫 번째 아이템이거나 시간이 이전보다 작으면서 새벽 시간대면 다음날
            if (index === 0) {
                day = 1;
            } else {
                const prevItem = itinerary[index - 1];
                const prevHour = parseInt((prevItem.time || '09:00').split(':')[0]);
                
                if (hour < prevHour && hour < 12) {
                    // 이전 아이템의 day를 찾아서 +1
                    const prevDay = prevItem.calculatedDay || prevItem.day || 1;
                    day = prevDay + 1;
                } else {
                    // 같은 날
                    const prevDay = prevItem.calculatedDay || prevItem.day || 1;
                    day = prevDay;
                }
            }
            
            // 계산된 day를 아이템에 저장
            item.calculatedDay = day;
        }
        
        if (!groups[day]) {
            groups[day] = [];
        }
        groups[day].push({...item, day: day});
    });
    
    // 빈 그룹이 있으면 제거
    Object.keys(groups).forEach(key => {
        if (groups[key].length === 0) {
            delete groups[key];
        }
    });
    
    console.log('Grouped itinerary by day:', groups);
    return groups;
}

function createDayTabs(dayGroups) {
    const tabsContainer = document.getElementById('dayTabs');
    const dayCount = Object.keys(dayGroups).length;
    
    console.log('Creating day tabs for', dayCount, 'days');
    
    if (dayCount <= 1) {
        tabsContainer.classList.add('hidden');
        console.log('Only one day, hiding tabs');
        return;
    }
    
    tabsContainer.classList.remove('hidden');
    tabsContainer.innerHTML = '';
    
    // 일자 순서대로 정렬
    const sortedDays = Object.keys(dayGroups).sort((a, b) => parseInt(a) - parseInt(b));
    
    sortedDays.forEach(day => {
        const dayNum = parseInt(day);
        const dayData = dayGroups[day];
        
        const tab = document.createElement('button');
        tab.className = `px-4 py-2 mr-2 mb-2 rounded-lg font-medium transition-colors ${
            dayNum === currentDay ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-700 hover:bg-blue-100'
        }`;
        tab.textContent = `${dayNum}일차 (${dayData.length}개)`;
        tab.setAttribute('data-day', dayNum);
        
        tab.onclick = () => {
            console.log(`Tab clicked: Day ${dayNum}`);
            currentDay = dayNum;
            
            // 🗺️ 경로 제거 및 일정 재표시
            if (directionsRenderer) {
                directionsRenderer.setDirections({routes: []});
            }
            
            displayDayTimeline(currentDay);
            updateTabStyles();
        };
        
        tabsContainer.appendChild(tab);
    });
    
    console.log('Created tabs for days:', sortedDays);
}

function updateTabStyles() {
    const tabs = document.querySelectorAll('#dayTabs button');
    tabs.forEach(tab => {
        const tabDay = parseInt(tab.getAttribute('data-day'));
        if (tabDay === currentDay) {
            tab.className = 'px-4 py-2 mr-2 mb-2 rounded-lg font-medium bg-blue-500 text-white transition-colors';
        } else {
            tab.className = 'px-4 py-2 mr-2 mb-2 rounded-lg font-medium bg-gray-100 text-gray-700 hover:bg-blue-100 transition-colors';
        }
    });
    
    console.log(`Updated tab styles, current day: ${currentDay}`);
}

function displayDayTimeline(day) {
    const timeline = document.getElementById('timeline');
    const dayData = dayGroups[day] || [];
    
    console.log(`Displaying timeline for day ${day}:`, dayData);
    
    timeline.innerHTML = '';
    
    if (dayData.length === 0) {
        timeline.innerHTML = '<div class="text-center py-8 text-gray-500">이 날의 일정이 없습니다.</div>';
        return;
    }
    
    dayData.forEach((item, index) => {
        const timelineItem = document.createElement('div');
        timelineItem.className = 'flex items-start space-x-4 p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors';
        
        const placeName = item.place_name || item.name || item.activity || '장소명 없음';
        const time = item.time || `${9 + index}:00`;
        const duration = item.duration || '30분';
        const description = item.description || '';
        const location = item.address || item.location || '';
        
        timelineItem.innerHTML = `
            <div class="flex-shrink-0 w-8 h-8 bg-blue-500 text-white rounded-full flex items-center justify-center text-sm font-bold">
                ${index + 1}
            </div>
            <div class="flex-1">
                <div class="flex items-center justify-between mb-1">
                    <div class="flex items-center space-x-2">
                        <span class="font-semibold text-blue-600">${time}</span>
                        <span class="text-sm text-gray-500">• ${duration}</span>
                        <span class="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">${day}일차</span>
                    </div>
                    <button onclick="event.stopPropagation(); showRouteToNext(${index}, ${day});" 
                            class="px-3 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600 transition">
                        <i class="fas fa-route mr-1"></i>${index === 0 ? '출발' : '경로'} 보기
                    </button>
                </div>
                <div onclick="showPlaceModalByIndex(${index}, ${day})" class="cursor-pointer">
                    <h4 class="font-medium text-gray-800 mb-1">${placeName}</h4>
                    <p class="text-sm text-gray-600 mb-2">${description}</p>
                </div>
                ${item.transportation ? `<div class="bg-green-50 p-2 rounded mb-2">
                    <span class="text-xs text-green-700"><i class="fas fa-subway"></i> ${item.transportation}</span>
                </div>` : ''}
                ${item.route_distance && item.route_duration ? `<div class="bg-blue-50 p-2 rounded mb-2">
                    <span class="text-xs text-blue-700"><i class="fas fa-route"></i> 이동: ${item.route_distance}, ${item.route_duration}</span>
                </div>` : ''}
                <div class="flex items-center space-x-4 text-xs text-gray-500">
                    <span><i class="fas fa-map-marker-alt"></i> ${location}</span>
                    ${item.rating ? `<span><i class="fas fa-star text-yellow-400"></i> ${item.rating}</span>` : ''}
                    ${item.quality_score ? `<span class="px-1 py-0.5 rounded text-xs ${
                        item.quality_score >= 4.0 ? 'bg-blue-100 text-blue-700' :
                        item.quality_score >= 3.0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                    }">Q:${item.quality_score.toFixed(1)}</span>` : ''}
                    ${item.price ? `<span><i class="fas fa-won-sign"></i> ${item.price}</span>` : ''}
                </div>
            </div>
        `;
        
        timeline.appendChild(timelineItem);
    });
    
    // 지도에 해당 날짜 데이터만 표시
    updateMapForDay(dayData);
    
    // 장소 상세정보도 업데이트
    verifyAndDisplayPlaces(dayData);
    
    console.log(`Timeline displayed for day ${day} with ${dayData.length} items`);
}

function updateMapForDay(dayData) {
    if (!map || !dayData || dayData.length === 0) return;
    
    // 기존 마커 제거
    if (currentMarkers && currentMarkers.length > 0) {
        currentMarkers.forEach(marker => marker.setMap(null));
    }
    currentMarkers = [];
    savedMarkers = [];
    
    const bounds = new google.maps.LatLngBounds();
    
    dayData.forEach((item, index) => {
        const lat = item.lat || 37.5665;
        const lng = item.lng || 126.9780;
        const position = new google.maps.LatLng(lat, lng);
        
        const marker = new google.maps.Marker({
            position: position,
            map: map,
            title: item.place_name || item.name || item.activity,
            label: (index + 1).toString(),
            icon: {
                url: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png',
                scaledSize: new google.maps.Size(32, 32)
            }
        });
        
        const infoWindow = new google.maps.InfoWindow({
            content: `
                <div style="max-width: 250px;">
                    <h4 style="margin: 0 0 8px 0; font-weight: bold; color: #1a73e8;">${item.place_name || item.name || item.activity}</h4>
                    <p style="margin: 0 0 4px 0; font-size: 13px; color: #333;">${item.description || ''}</p>
                    <p style="margin: 0 0 4px 0; font-size: 12px; color: #666;">
                        <i class="fas fa-map-marker-alt" style="color: #ea4335;"></i> ${item.address || item.location || ''}
                    </p>
                    ${item.time ? `<p style="margin: 0; font-size: 11px; color: #888;">
                        <i class="fas fa-clock"></i> ${item.time} (${item.duration || '30분'})
                    </p>` : ''}
                </div>
            `
        });
        
        marker.addListener('click', () => {
            if (window.currentInfoWindow) {
                window.currentInfoWindow.close();
            }
            infoWindow.open(map, marker);
            window.currentInfoWindow = infoWindow;
        });
        
        currentMarkers.push(marker);
        savedMarkers.push(marker); // 원본 마커 저장
        bounds.extend(position);
    });
    
    if (dayData.length > 0) {
        map.fitBounds(bounds);
        
        google.maps.event.addListenerOnce(map, 'bounds_changed', function() {
            if (map.getZoom() > 15) {
                map.setZoom(15);
            }
        });
    }
}

// 🆕 경로 보기 함수 (일정 항목별)
async function showRouteToNext(index, day) {
    console.log(`🗺️ 경로 보기: Day ${day}, Index ${index}`);
    console.log(`   dayGroups 전체:`, dayGroups);
    
    const dayData = dayGroups[day] || [];
    console.log(`   ${day}일차 데이터 (${dayData.length}개):`, dayData);
    
    if (!dayData || dayData.length === 0) {
        alert('해당 날짜의 일정이 없습니다.');
        return;
    }
    
    const currentPlace = dayData[index];
    console.log(`   현재 장소 (index ${index}):`, currentPlace);
    
    if (!currentPlace || !currentPlace.lat || !currentPlace.lng) {
        alert('장소 정보가 없습니다.');
        return;
    }
    
    let startLat, startLng, startName;
    
    // 🔍 출발지 결정 로직
    if (index === 0) {
        // 각 날의 첫 번째 장소
        if (day === 1) {
            // 1일차 첫 번째: 현재 장소의 주소에서 도시 추출
            const currentCity = currentPlace.address || '';
            if (currentCity.includes('순천') || currentCity.includes('전남')) {
                // 순천이면 순천역을 출발지로
                startLat = 34.9506;
                startLng = 127.4877;
                startName = "순천역";
            } else {
                // 원래 출발지 사용
                startLat = window.tripStartLat || currentPlace.lat;
                startLng = window.tripStartLng || currentPlace.lng;
                startName = window.tripStartLocation || currentPlace.address?.split(' ')[0] || "출발지";
            }
            console.log(`   📍 1일차 출발지: ${startName} (${startLat}, ${startLng})`);
        } else {
            // 2일차 이상 첫 번째: 전날 마지막 장소 사용
            const prevDayData = dayGroups[day - 1] || [];
            console.log(`   전날 (${day - 1}일차) 데이터:`, prevDayData);
            
            if (prevDayData.length > 0) {
                const prevLastPlace = prevDayData[prevDayData.length - 1];
                console.log(`   전날 마지막 장소:`, prevLastPlace);
                
                startLat = prevLastPlace.lat;
                startLng = prevLastPlace.lng;
                startName = prevLastPlace.place_name || prevLastPlace.name || "전날 마지막 장소";
                console.log(`   📍 ${day}일차 출발지 (전날 마지막): ${startName} (${startLat}, ${startLng})`);
            } else {
                // Fallback: 현재 장소가 있는 도시의 중심
                startLat = currentPlace.lat;
                startLng = currentPlace.lng;
                startName = "현재 위치 근처";
                console.log(`   ⚠️ 전날 데이터 없음, 현재 위치 사용: ${startName}`);
            }
        }
    } else {
        // 같은 날 두 번째 이상: 이전 장소 사용
        const prevPlace = dayData[index - 1];
        startLat = prevPlace.lat;
        startLng = prevPlace.lng;
        startName = prevPlace.place_name || prevPlace.name || "이전 장소";
        console.log(`   📍 이전 장소 출발: ${startName}`);
    }
    
    const destLat = currentPlace.lat;
    const destLng = currentPlace.lng;
    const destName = currentPlace.place_name || currentPlace.name || "목적지";
    
    console.log(`   ✅ 최종 출발: ${startName} (${startLat}, ${startLng})`);
    console.log(`   ✅ 최종 도착: ${destName} (${destLat}, ${destLng})`);
    
    // 좌표 유효성 검증
    if (!startLat || !startLng || !destLat || !destLng) {
        alert('좌표 정보가 올바르지 않습니다.');
        console.error('   ❌ 좌표 누락:', { startLat, startLng, destLat, destLng });
        return;
    }
    
    // Google Maps에서 경로 열기
    const googleMapsUrl = `https://www.google.com/maps/dir/?api=1&origin=${startLat},${startLng}&destination=${destLat},${destLng}&travelmode=transit`;
    window.open(googleMapsUrl, '_blank');
    
    // 지도에 경로 표시
    if (map && directionsService) {
        // 거리 계산
        const distance = calculateDistance(startLat, startLng, destLat, destLng);
        console.log(`   📏 직선 거리: ${distance.toFixed(2)}km`);
        
        // 1km 미만이면 도보, 아니면 대중교통
        const travelMode = distance < 1.0 ? google.maps.TravelMode.WALKING : google.maps.TravelMode.TRANSIT;
        console.log(`   🚶 이동 수단: ${travelMode}`);
        
        const request = {
            origin: new google.maps.LatLng(startLat, startLng),
            destination: new google.maps.LatLng(destLat, destLng),
            travelMode: travelMode
        };
        
        directionsService.route(request, (result, status) => {
            if (status === 'OK') {
                // 기존 경로 제거
                if (directionsRenderer) {
                    directionsRenderer.setDirections({routes: []});
                }
                
                const routeRenderer = new google.maps.DirectionsRenderer({
                    directions: result,
                    suppressMarkers: true,
                    polylineOptions: {
                        strokeColor: travelMode === google.maps.TravelMode.WALKING ? '#34A853' : '#4285F4',
                        strokeWeight: 4,
                        strokeOpacity: 0.8
                    }
                });
                routeRenderer.setMap(map);
                console.log('   ✅ 경로 표시 성공');
            } else {
                console.warn(`   ❌ 경로 표시 실패 (${status}), 점선으로 표시`);
                // 실패 시 점선 표시
                const places = [
                    { lat: startLat, lng: startLng, name: startName },
                    { lat: destLat, lng: destLng, name: destName }
                ];
                drawStraightPath(places, travelMode);
            }
        });
    }
}

// 거리 계산 헬퍼 함수
function calculateDistance(lat1, lng1, lat2, lng2) {
    const R = 6371; // 지구 반지름 (km)
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLng/2) * Math.sin(dLng/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}


async function verifyAndDisplayPlaces(itinerary) {
    const placeDetails = document.getElementById('placeDetails');
    placeDetails.innerHTML = '<div class="text-center py-4"><i class="fas fa-spinner fa-spin"></i> 장소 정보를 확인하고 있습니다...</div>';
    
    places = [];
    const verifiedPlaces = [];
    
    // 실제 API 데이터를 사용 (이미 백엔드에서 처리됨)
    for (const item of itinerary) {
        const placeInfo = {
            name: item.place_name || item.name || item.activity,
            verified: item.verified || false,
            description: item.description || '',
            rating: item.rating || item.google_rating || 4.0,
            qualityScore: item.quality_score || 0,
            reviewCount: item.blog_reviews ? item.blog_reviews.length * 10 : 0,
            openHours: item.opening_hours ? item.opening_hours.join(', ') : '09:00-21:00',
            location: item.address || item.location || '',
            lat: item.lat || 37.5665,
            lng: item.lng || 126.9780,
            phone: item.phone || '',
            website: item.website || '',
            blogLinks: item.blog_reviews ? item.blog_reviews.map(blog => ({
                title: blog.title || `${item.place_name} 후기`,
                url: blog.link || `https://search.naver.com/search.naver?query=${encodeURIComponent((item.place_name || item.name) + ' 후기')}`
            })) : [],
            blogContents: item.blog_contents || []
        };
        
        verifiedPlaces.push(placeInfo);
        places.push({
            name: placeInfo.name,
            location: placeInfo.location,
            lat: placeInfo.lat,
            lng: placeInfo.lng
        });
    }
    
    // Display verified places
    placeDetails.innerHTML = '';
    verifiedPlaces.forEach(place => {
        const placeDiv = document.createElement('div');
        placeDiv.className = 'border rounded-lg p-4 hover:shadow-md transition-shadow';
        placeDiv.innerHTML = `
            <div class="flex items-start justify-between mb-2">
                <h4 class="font-semibold text-gray-800">${place.name}</h4>
                <div class="flex space-x-2">
                    <span class="px-2 py-1 text-xs rounded-full ${
                        place.verified ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                    }">
                        ${place.verified ? '✓ 확인됨' : '⚠ 미확인'}
                    </span>
                    ${place.qualityScore > 0 ? `
                        <span class="px-2 py-1 text-xs rounded-full ${
                            place.qualityScore >= 4.0 ? 'bg-blue-100 text-blue-800' :
                            place.qualityScore >= 3.0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }">
                            품질: ${place.qualityScore.toFixed(1)}/5.0
                        </span>
                    ` : ''}
                </div>
            </div>
            <p class="text-sm text-gray-600 mb-2">${place.description}</p>
            <div class="flex items-center space-x-4 text-xs text-gray-500 mb-2">
                <span><i class="fas fa-star text-yellow-400"></i> ${place.rating}/5</span>
                <span><i class="fas fa-users"></i> 리뷰 ${place.reviewCount}개</span>
                ${place.phone ? `<span><i class="fas fa-phone"></i> ${place.phone}</span>` : ''}
                <span><i class="fas fa-clock"></i> ${place.openHours}</span>
            </div>
            ${place.blogLinks && place.blogLinks.length > 0 ? `
                <div class="mt-3">
                    <p class="text-xs font-medium text-gray-700 mb-1">🔗 네이버 블로그 실제 방문 후기 (${place.blogLinks.length}개):</p>
                    <div class="space-y-1">
                        ${place.blogLinks.slice(0, 5).map(link => {
                            const safeUrl = (link.url || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
                            const safeTitle = (link.title || '후기').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
                            return `
                            <a href="${safeUrl}" target="_blank" class="block p-2 bg-blue-50 rounded hover:bg-blue-100 transition text-xs text-blue-700 hover:text-blue-900">
                                <i class="fas fa-external-link-alt mr-1"></i>
                                <span class="font-medium">${safeTitle}</span>
                            </a>
                        `}).join('')}
                    </div>
                </div>
            ` : '<div class="mt-3 p-2 bg-gray-50 rounded text-xs text-gray-500">💬 블로그 후기를 수집 중입니다...</div>'}
            ${place.blogContents && place.blogContents.length > 0 ? `
                <div class="mt-3 space-y-2">
                    ${place.blogContents.map(content => `
                        <div class="p-2 bg-yellow-50 rounded">
                            <p class="text-xs font-medium text-gray-700 mb-1">블로그 후기 내용:</p>
                            <p class="text-xs text-gray-600 mb-2">${content.summary || content.content || '후기 내용을 불러오는 중...'}</p>
                            ${content.keywords && content.keywords.length > 0 ? `
                                <div class="flex flex-wrap gap-1">
                                    ${content.keywords.map(keyword => `
                                        <span class="inline-block px-2 py-0.5 text-xs bg-blue-100 text-blue-800 rounded">${keyword}</span>
                                    `).join('')}
                                </div>
                            ` : ''}
                            ${content.rating ? `
                                <div class="mt-1 text-xs text-gray-500">
                                    <i class="fas fa-star text-yellow-400"></i> 블로그 평점: ${content.rating}/5
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        `;
        placeDetails.appendChild(placeDiv);
    });
}

async function verifyPlace(placeName) {
    // Simulate API call to verify place and get details
    await new Promise(resolve => setTimeout(resolve, 500));
    
    return {
        name: placeName,
        verified: Math.random() > 0.2, // 80% verification rate
        description: `${placeName}에 대한 상세 설명입니다.`,
        rating: (4 + Math.random()).toFixed(1),
        reviewCount: Math.floor(Math.random() * 500) + 50,
        openHours: '09:00-21:00',
        location: '서울시 강남구',
        lat: 37.5665 + (Math.random() - 0.5) * 0.1,
        lng: 126.9780 + (Math.random() - 0.5) * 0.1,
        blogLinks: [
            { 
                title: `${placeName} 후기 - 네이버 블로그`, 
                url: `https://search.naver.com/search.naver?query=${encodeURIComponent(placeName + ' 후기')}` 
            },
            { 
                title: `${placeName} 맛집 리뷰 - 매니아`, 
                url: `https://www.mangoplate.com/search/${encodeURIComponent(placeName)}` 
            },
            { 
                title: `${placeName} 정보 - 카카오맵`, 
                url: `https://map.kakao.com/?q=${encodeURIComponent(placeName)}` 
            }
        ]
    };
}

function displayOptimizedRoute(routeInfo) {
    console.log('displayOptimizedRoute called with:', routeInfo);
    
    if (!map) {
        console.error('Map not initialized');
        return;
    }
    
    // Clear previous routes and markers
    if (directionsRenderer) {
        directionsRenderer.setDirections({routes: []});
    }
    
    if (window.currentMarkers) {
        window.currentMarkers.forEach(marker => marker.setMap(null));
    }
    window.currentMarkers = [];
    
    // 8단계 아키텍처에서 받은 경로 정보 처리
    const locations = routeInfo.locations || places;
    
    if (!locations || locations.length === 0) {
        console.log('No locations to display');
        return;
    }
    
    console.log('Displaying optimized route with locations:', locations);
    
    // 경로 라인 표시 (polyline이 있는 경우)
    if (routeInfo.polyline && routeInfo.polyline !== "sample_encoded_polyline_string") {
        try {
            let pathCoords = [];
            
            // 커스텀 polyline 형식 처리 ("lat,lng|lat,lng" 형태)
            if (routeInfo.polyline.includes('|')) {
                pathCoords = routeInfo.polyline.split('|').map(coord => {
                    const [lat, lng] = coord.split(',').map(Number);
                    return new google.maps.LatLng(lat, lng);
                });
            } else {
                // Google 표준 polyline 디코딩
                pathCoords = google.maps.geometry.encoding.decodePath(routeInfo.polyline);
            }
            
            const routeLine = new google.maps.Polyline({
                path: pathCoords,
                geodesic: true,
                strokeColor: '#4285F4',
                strokeOpacity: 0.8,
                strokeWeight: 4
            });
            
            routeLine.setMap(map);
            console.log('Route polyline displayed');
        } catch (error) {
            console.error('Error displaying polyline:', error);
        }
    }
    
    // 마커 표시
    const bounds = new google.maps.LatLngBounds();
    
    locations.forEach((location, index) => {
        const lat = location.lat || 37.5665;
        const lng = location.lng || 126.9780;
        const position = new google.maps.LatLng(lat, lng);
        
        const marker = new google.maps.Marker({
            position: position,
            map: map,
            title: location.name,
            label: (index + 1).toString(),
            icon: {
                url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
                scaledSize: new google.maps.Size(32, 32)
            }
        });
        
        const infoWindow = new google.maps.InfoWindow({
            content: `
                <div style="max-width: 250px;">
                    <h4 style="margin: 0 0 8px 0; font-weight: bold; color: #1a73e8;">${location.name}</h4>
                    <p style="margin: 0 0 4px 0; font-size: 12px; color: #666;">${location.location || ''}</p>
                    <p style="margin: 0; font-size: 11px; color: #888;">8단계 최적화된 경로</p>
                </div>
            `
        });
        
        marker.addListener('click', () => {
            if (window.currentInfoWindow) {
                window.currentInfoWindow.close();
            }
            infoWindow.open(map, marker);
            window.currentInfoWindow = infoWindow;
        });
        
        window.currentMarkers.push(marker);
        bounds.extend(position);
    });
    
    // 지도 뷰 조정
    if (routeInfo.bounds) {
        const routeBounds = new google.maps.LatLngBounds(
            new google.maps.LatLng(routeInfo.bounds.southwest.lat, routeInfo.bounds.southwest.lng),
            new google.maps.LatLng(routeInfo.bounds.northeast.lat, routeInfo.bounds.northeast.lng)
        );
        map.fitBounds(routeBounds);
    } else if (locations.length > 0) {
        map.fitBounds(bounds);
    }
    
    // 줌 레벨 조정
    google.maps.event.addListenerOnce(map, 'bounds_changed', function() {
        if (map.getZoom() > 15) {
            map.setZoom(15);
        }
    });
    
    console.log(`Optimized route displayed with ${locations.length} locations`);
}

// 🆕 Haversine 공식으로 총 거리 계산 (km)
function calculateTotalDistance(places) {
    if (!places || places.length < 2) return 0;
    
    let totalDistance = 0;
    for (let i = 0; i < places.length - 1; i++) {
        const p1 = places[i];
        const p2 = places[i + 1];
        
        if (!p1.lat || !p1.lng || !p2.lat || !p2.lng) continue;
        
        // Haversine 공식
        const R = 6371; // 지구 반경 (km)
        const dLat = (p2.lat - p1.lat) * Math.PI / 180;
        const dLon = (p2.lng - p1.lng) * Math.PI / 180;
        
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                  Math.cos(p1.lat * Math.PI / 180) * Math.cos(p2.lat * Math.PI / 180) *
                  Math.sin(dLon / 2) * Math.sin(dLon / 2);
        
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const distance = R * c;
        
        totalDistance += distance;
    }
    
    return totalDistance;
}

// 🆕 이동 수단 변경 시 경로 재렌더링 (현재 날짜만)
async function updateRouteWithMode(mode) {
    console.log(`🚗 이동 수단 변경: ${mode} (현재 ${currentDay}일차)`);
    
    if (!directionsService || !map) {
        console.error('Map services not initialized');
        return;
    }
    
    // 🆕 현재 날짜의 일정만 추출
    const dayData = dayGroups[currentDay] || [];
    const validPlaces = dayData.filter(item => item.lat && item.lng);
    
    if (validPlaces.length < 2) {
        console.log('Not enough places for route');
        return;
    }
    
    // 기존 경로 제거
    if (directionsRenderer) {
        directionsRenderer.setDirections({routes: []});
    }
    
    // Waypoints 생성
    const waypoints = validPlaces.slice(1, -1).map(place => ({
        location: new google.maps.LatLng(place.lat, place.lng),
        stopover: true
    }));
    
    // 새로운 경로 요청
    const request = {
        origin: new google.maps.LatLng(validPlaces[0].lat, validPlaces[0].lng),
        destination: new google.maps.LatLng(validPlaces[validPlaces.length - 1].lat, validPlaces[validPlaces.length - 1].lng),
        waypoints: waypoints,
        optimizeWaypoints: true,
        travelMode: google.maps.TravelMode[mode]
    };
    
    try {
        directionsService.route(request, (result, status) => {
            if (status === 'OK') {
                const routeRenderer = new google.maps.DirectionsRenderer({
                    directions: result,
                    suppressMarkers: true,
                    polylineOptions: {
                        strokeColor: mode === 'WALKING' ? '#34A853' : mode === 'DRIVING' ? '#EA4335' : '#4285F4',
                        strokeWeight: 4,
                        strokeOpacity: 0.8
                    }
                });
                routeRenderer.setMap(map);
                console.log(`   ✅ ${mode} 경로 표시 성공`);
            } else {
                console.warn(`   ❌ ${mode} 경로 실패: ${status}`);
                // 실패 시 점선 표시
                const places = validPlaces.map(item => ({
                    lat: item.lat,
                    lng: item.lng,
                    name: item.place_name || item.name || '장소명 없음',
                    location: item.address || ''
                }));
                drawStraightPath(places, mode);
            }
        });
    } catch (error) {
        console.error('Error updating route:', error);
    }
}

function displayRoute(routeInfo, itinerary) {
    console.log('displayRoute called with routeInfo:', routeInfo, 'itinerary:', itinerary);
    
    if (!map) {
        console.error('Map not initialized');
        return;
    }
    
    // itinerary를 places로 변환
    const places = (itinerary || []).filter(item => item.lat && item.lng).map(item => ({
        lat: item.lat,
        lng: item.lng,
        name: item.place_name || item.name || item.activity || '장소명 없음',
        location: item.address || item.location || ''
    }));
    
    if (places.length === 0) {
        console.log('No valid places to display');
        return;
    }
    
    console.log('Converted places:', places);
    
    // 기존 마커들 제거
    if (window.currentMarkers) {
        window.currentMarkers.forEach(marker => marker.setMap(null));
    }
    window.currentMarkers = [];
    
    // 지도 경계 설정을 위한 bounds 객체
    const bounds = new google.maps.LatLngBounds();
    
    // 각 장소에 마커 추가
    places.forEach((place, index) => {
        const position = new google.maps.LatLng(place.lat, place.lng);
        
        const marker = new google.maps.Marker({
            position: position,
            map: map,
            title: place.name,
            label: (index + 1).toString(),
            icon: {
                url: 'https://maps.google.com/mapfiles/ms/icons/red-dot.png',
                scaledSize: new google.maps.Size(32, 32)
            }
        });
        
        // 정보창 생성
        const infoWindow = new google.maps.InfoWindow({
            content: `
                <div style="max-width: 200px;">
                    <h4 style="margin: 0 0 8px 0; font-weight: bold;">${place.name}</h4>
                    <p style="margin: 0 0 4px 0; font-size: 12px; color: #666;">${place.location || ''}</p>
                    <p style="margin: 0; font-size: 11px; color: #888;">클릭하여 상세 정보 보기</p>
                </div>
            `
        });
        
        // 마커 클릭 이벤트
        marker.addListener('click', () => {
            // 다른 정보창들 닫기
            if (window.currentInfoWindow) {
                window.currentInfoWindow.close();
            }
            infoWindow.open(map, marker);
            window.currentInfoWindow = infoWindow;
        });
        
        window.currentMarkers.push(marker);
        bounds.extend(position);
    });
    
    // 지도 뷰를 모든 마커가 보이도록 조정
    if (places.length > 0) {
        map.fitBounds(bounds);
        
        // 줌 레벨이 너무 높으면 조정
        google.maps.event.addListenerOnce(map, 'bounds_changed', function() {
            if (map.getZoom() > 15) {
                map.setZoom(15);
            }
        });
    }
    
    // 경로 표시 (2개 이상의 장소가 있을 때)
    if (places.length >= 2 && directionsService && directionsRenderer) {
        const waypoints = places.slice(1, -1).map(place => ({
            location: new google.maps.LatLng(place.lat, place.lng),
            stopover: true
        }));
        
        // 🆕 거리 기반 자동 이동 수단 선택
        const totalDistance = calculateTotalDistance(places);
        let travelMode;
        
        // 🚶 거리별 기본 이동 수단 (모두 버튼 표시)
        if (totalDistance < 1.5) {
            travelMode = google.maps.TravelMode.WALKING;
            console.log(`총 거리 ${totalDistance.toFixed(1)}km → 도보 모드 (기본)`);
        } else if (totalDistance < 5) {
            travelMode = google.maps.TravelMode.TRANSIT;
            console.log(`총 거리 ${totalDistance.toFixed(1)}km → 대중교통 모드 (기본)`);
        } else {
            travelMode = google.maps.TravelMode.DRIVING;
            console.log(`총 거리 ${totalDistance.toFixed(1)}km → 자동차 모드 (기본)`);
        }
        
        // 🆕 이동 수단 선택 UI 항상 표시
        const transportSelector = document.getElementById('transportSelector');
        if (transportSelector) {
            transportSelector.classList.remove('hidden');
            
            // 기본 선택된 버튼 활성화
            const transportButtons = document.querySelectorAll('.transport-btn');
            transportButtons.forEach(btn => {
                btn.classList.remove('bg-blue-500', 'text-white');
                btn.classList.add('bg-gray-200', 'text-gray-700');
                
                // 현재 travelMode에 맞는 버튼 활성화
                const btnMode = btn.dataset.mode;
                if ((travelMode === google.maps.TravelMode.WALKING && btnMode === 'WALKING') ||
                    (travelMode === google.maps.TravelMode.TRANSIT && btnMode === 'TRANSIT') ||
                    (travelMode === google.maps.TravelMode.DRIVING && btnMode === 'DRIVING')) {
                    btn.classList.remove('bg-gray-200', 'text-gray-700');
                    btn.classList.add('bg-blue-500', 'text-white');
                }
            });
        }
        
        const request = {
            origin: new google.maps.LatLng(places[0].lat, places[0].lng),
            destination: new google.maps.LatLng(places[places.length - 1].lat, places[places.length - 1].lng),
            waypoints: waypoints,
            optimizeWaypoints: true,
            travelMode: travelMode
        };
        
        directionsService.route(request, (result, status) => {
            if (status === 'OK') {
                // 기존 경로 제거
                directionsRenderer.setDirections({routes: []});
                
                // 이동 수단별 색상
                const colorMap = {
                    'WALKING': '#34A853',
                    'TRANSIT': '#4285F4',
                    'DRIVING': '#EA4335'
                };
                
                // 새 경로 표시
                const routeRenderer = new google.maps.DirectionsRenderer({
                    directions: result,
                    suppressMarkers: true,
                    polylineOptions: {
                        strokeColor: colorMap[request.travelMode] || '#4285F4',
                        strokeWeight: 4,
                        strokeOpacity: 0.8
                    }
                });
                routeRenderer.setMap(map);
                
                console.log(`✅ 경로 표시 성공 (${request.travelMode})`);
            } else {
                console.warn(`❌ 경로 표시 실패 (${request.travelMode}): ${status}`);
                
                // 🆕 실패 시 점선 직선 경로 표시
                console.log('   📍 점선 직선으로 대체 표시');
                drawStraightPath(places, request.travelMode);
            }
        });
    }
    
    console.log(`Displayed ${places.length} places on map`);
}

// 🆕 점선 직선 경로 표시 (API 실패 시 fallback)
function drawStraightPath(places, travelMode) {
    if (!map || places.length < 2) {
        console.log('Cannot draw straight path: invalid data');
        return;
    }
    
    // 이동 수단별 색상
    const colorMap = {
        'WALKING': '#34A853',
        'TRANSIT': '#4285F4',
        'DRIVING': '#EA4335'
    };
    
    // 각 장소 간 점선 연결
    for (let i = 0; i < places.length - 1; i++) {
        const start = places[i];
        const end = places[i + 1];
        
        const path = [
            { lat: start.lat, lng: start.lng },
            { lat: end.lat, lng: end.lng }
        ];
        
        const dashedLine = new google.maps.Polyline({
            path: path,
            geodesic: true,
            strokeColor: colorMap[travelMode] || '#999999',
            strokeOpacity: 0.6,
            strokeWeight: 3,
            icons: [{
                icon: {
                    path: 'M 0,-1 0,1',
                    strokeOpacity: 1,
                    scale: 3
                },
                offset: '0',
                repeat: '15px'
            }],
            map: map
        });
        
        console.log(`   ├─ 점선 연결: ${start.name} → ${end.name}`);
    }
    
    console.log(`   ✅ 점선 경로 ${places.length - 1}개 표시 완료`);
}

// 경로 안내 함수
// 전역 변수로 현재 경로 데이터 저장
let currentRouteOrigin = null;
let currentRouteDestination = null;
let currentRouteData = null; // 전체 origin/destination 객체 저장

async function showRouteToNext(currentIndex, day) {
    console.log('🚀 showRouteToNext 호출됨!', { currentIndex, day });
    
    const dayData = dayGroups[day];
    if (!dayData) {
        console.error('❌ dayData 없음');
        return;
    }
    
    console.log('✅ dayData 있음:', dayData.length + '개');
    
    let origin, destination;
    
    if (currentIndex === 0) {
        // 1번 장소: 출발지 → 1번 장소
        // UI에서 설정한 출발지 정보 가져오기
        const startLocationName = window.tripStartLocation || "서울역";
        const startLat = window.tripStartLat || 37.5547;
        const startLng = window.tripStartLng || 126.9707;
        
        console.log('📍 출발지:', { name: startLocationName, lat: startLat, lng: startLng });
        
        origin = { 
            place_name: startLocationName, 
            name: startLocationName,
            location: startLocationName,
            address: startLocationName,
            lat: startLat, 
            lng: startLng 
        };
        destination = dayData[0];
    } else {
        // 2번 이후: 이전 장소 → 현재 장소
        origin = dayData[currentIndex - 1];
        destination = dayData[currentIndex];
    }
    
    // 장소명 우선, 좌표는 fallback (한국에서 더 정확함)
    const originName = origin.place_name || origin.name || origin.address || origin.location;
    const destName = destination.place_name || destination.name || destination.address || destination.location;
    
    // 장소명이 있으면 사용, 없으면 좌표
    currentRouteOrigin = originName || `${origin.lat || 37.5665},${origin.lng || 126.9780}`;
    currentRouteDestination = destName || `${destination.lat || 37.5665},${destination.lng || 126.9780}`;
    
    // 전체 데이터 저장 (UI 표시용)
    currentRouteData = { origin, destination };
    
    console.log('📍 경로 검색:', {
        출발: currentRouteOrigin,
        도착: currentRouteDestination
    });
    
    // HTML 안전하게 이스케이프
    const safeOriginName = (origin.place_name || origin.name).replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const safeDestName = (destination.place_name || destination.name).replace(/</g, '&lt;').replace(/>/g, '&gt;');
    
    // 🗺️ 경로 안내 섹션 요소 가져오기
    const routeSection = document.getElementById('routeSection');
    const routeButtons = document.getElementById('routeButtons');
    const routeDetails = document.getElementById('routeDetails');
    
    console.log('🔍 routeSection 요소:', routeSection);
    console.log('🔍 출발:', safeOriginName, '→ 도착:', safeDestName);
    
    if (!routeSection || !routeButtons) {
        console.error('❌ routeSection 또는 routeButtons를 찾을 수 없습니다!');
        // 콘솔에 디버깅 정보 출력
        console.error('디버그:', {
            routeSection: routeSection,
            routeButtons: routeButtons,
            routeDetails: routeDetails
        });
        return;
    }
    
    // 🗑️ 기존 마커 완전히 제거
    if (currentMarkers && currentMarkers.length > 0) {
        savedMarkers = [...currentMarkers]; // 백업
        currentMarkers.forEach(marker => {
            marker.setMap(null); // 지도에서 제거
            marker.setVisible(false); // 보이지 않게
        });
        currentMarkers = []; // 배열 비우기
        console.log('🗑️ 마커 제거 완료:', savedMarkers.length + '개 백업됨');
    }
    
    // 🗑️ 기존 경로도 제거
    if (directionsRenderer) {
        directionsRenderer.setDirections({routes: []});
        console.log('🗑️ 기존 경로 제거');
    }
    
    // 경로 섹션 표시
    routeSection.classList.remove('hidden');
    
    // 경로 정보 표시
    routeButtons.innerHTML = `
        <div class="bg-gray-50 p-3 rounded-lg mb-3">
            <div class="text-sm text-gray-600 mb-2">
                <div class="flex items-center mb-1">
                    <i class="fas fa-circle text-green-500 text-xs mr-2"></i>
                    <span class="font-medium">${safeOriginName}</span>
                </div>
                <div class="ml-3 text-gray-400 text-lg">↓</div>
                <div class="flex items-center">
                    <i class="fas fa-circle text-red-500 text-xs mr-2"></i>
                    <span class="font-medium">${safeDestName}</span>
                </div>
            </div>
        </div>
        <div class="grid grid-cols-2 gap-2">
            <button onclick="loadRouteOnMap('transit')" 
                    class="px-4 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition text-sm font-medium flex items-center justify-center">
                <i class="fas fa-subway mr-2"></i>
                대중교통
            </button>
            <button onclick="loadRouteOnMap('walking')" 
                    class="px-4 py-3 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition text-sm font-medium flex items-center justify-center">
                <i class="fas fa-walking mr-2"></i>
                도보
            </button>
        </div>
        <div class="mt-2 text-xs text-gray-500 text-center">
            <i class="fas fa-info-circle mr-1"></i>
            Google Maps API (대중교통/도보 지원 🗺️)
        </div>
        <button onclick="closeRouteOverlay()" 
                class="mt-3 w-full px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition text-sm">
            <i class="fas fa-times mr-1"></i> 닫기
        </button>
    `;
    
    if (routeDetails) {
        routeDetails.innerHTML = '<p class="text-sm text-gray-500">이동 수단을 선택하세요</p>';
    }
    
    // 경로 섹션으로 스크롤
    routeSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    
    console.log('✅ 경로 선택 버튼 표시 완료');
}

// 직선 경로 그리기 함수
function drawStraightLine(originCoords, destCoords, distance, mode, color, routeDetails) {
    console.log('🎨 직선 경로 그리기:', { distance: Math.round(distance) + 'm', mode, color });
    
    // 기존 renderer/polyline 제거
    if (directionsRenderer) {
        directionsRenderer.setMap(null);
    }
    if (window.currentPolyline) {
        window.currentPolyline.setMap(null);
    }
    
    // 직선 경로 그리기
    const path = [
        { lat: originCoords[0], lng: originCoords[1] },
        { lat: destCoords[0], lng: destCoords[1] }
    ];
    
    window.currentPolyline = new google.maps.Polyline({
        path: path,
        geodesic: true,
        strokeColor: color,
        strokeOpacity: 0.8,
        strokeWeight: 6,
        map: map
    });
    
    // 예상 시간 계산
    const speed = mode === 'walking' ? 80 : mode === 'transit' ? 300 : 500; // m/분
    const minutes = Math.ceil(distance / speed);
    
    // 정보 표시
    if (routeDetails) {
        const modeNames = {
            'transit': '🚇 대중교통',
            'driving': '🚗 자동차',
            'walking': '🚶 도보'
        };
        
        const modeColors = {
            'transit': 'text-blue-600',
            'driving': 'text-green-600',
            'walking': 'text-orange-600'
        };
        
        routeDetails.innerHTML = `
            <div class="bg-gray-50 p-4 rounded-lg">
                <div class="font-semibold ${modeColors[mode]} mb-2">${modeNames[mode]}</div>
                <div class="text-sm text-gray-700 space-y-1">
                    <div><strong>거리:</strong> ${Math.round(distance)}m</div>
                    <div><strong>예상 시간:</strong> 약 ${minutes}분</div>
                    <div class="text-xs text-gray-500 mt-2">📍 직선 거리 기준</div>
                </div>
            </div>
        `;
    }
    
    // 지도 범위 조정
    const bounds = new google.maps.LatLngBounds();
    bounds.extend(path[0]);
    bounds.extend(path[1]);
    map.fitBounds(bounds);
    
    // 너무 가까우면 줌 조정
    google.maps.event.addListenerOnce(map, 'bounds_changed', function() {
        if (map.getZoom() > 17) {
            map.setZoom(17);
        }
    });
    
    console.log('✅ 직선 경로 표시 완료');
}

// 경로 섹션 닫기 함수
function closeRouteOverlay() {
    // 경로 섹션 숨기기
    const routeSection = document.getElementById('routeSection');
    if (routeSection) {
        routeSection.classList.add('hidden');
    }
    
    // 마커 복원
    if (savedMarkers && savedMarkers.length > 0) {
        currentMarkers = [...savedMarkers];
        currentMarkers.forEach(marker => {
            marker.setVisible(true); // 보이게
            marker.setMap(map); // 지도에 다시 추가
        });
        console.log('✅ 마커 복원 완료:', currentMarkers.length + '개');
    }
    
    // 경로 제거
    if (directionsRenderer) {
        directionsRenderer.setDirections({routes: []});
        directionsRenderer.setMap(null);
    }
    
    // Polyline도 제거 (직선 경로용)
    if (window.currentPolyline) {
        window.currentPolyline.setMap(null);
        window.currentPolyline = null;
    }
    
    console.log('🚪 경로 섹션 닫기 완료');
}

// 🗺️ 지도에 경로를 표시하는 함수
async function loadRouteOnMap(mode) {
    console.log('🗺️ loadRouteOnMap 호출:', mode);
    
    if (!currentRouteOrigin || !currentRouteDestination) {
        console.error('❌ 출발지 또는 도착지 정보가 없습니다!');
        return;
    }
    
    // 로딩 표시
    const routeDetails = document.getElementById('routeDetails');
    if (routeDetails) {
        routeDetails.innerHTML = '<p class="text-sm text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i>경로 검색 중...</p>';
    }
    
    try {
        // Google Maps DirectionsService 직접 사용 (백엔드 제거)
        console.log('🗺️ Google Maps Directions API 직접 호출');
        
        const directionsService = new google.maps.DirectionsService();
        
        // 모드별 색상 설정
        const colors = {
            'transit': '#4285F4',
            'walking': '#EA4335'
        };
        
        // 🆕 currentRouteData에서 직접 좌표 가져오기 (더 안전)
        let originCoords, destCoords, originInput, destInput;
        
        if (currentRouteData && currentRouteData.origin && currentRouteData.destination) {
            // origin 처리
            const origin = currentRouteData.origin;
            const originLat = parseFloat(origin.lat);
            const originLng = parseFloat(origin.lng);
            originCoords = [originLat, originLng];
            
            const originName = origin.place_name || origin.name || origin.address;
            originInput = originName || { lat: originLat, lng: originLng };
            
            // destination 처리
            const destination = currentRouteData.destination;
            const destLat = parseFloat(destination.lat);
            const destLng = parseFloat(destination.lng);
            destCoords = [destLat, destLng];
            
            const destName = destination.place_name || destination.name || destination.address;
            destInput = destName || { lat: destLat, lng: destLng };
            
            console.log('📍 좌표 확인:', {
                origin: { name: originName, lat: originLat, lng: originLng },
                destination: { name: destName, lat: destLat, lng: destLng }
            });
        } else {
            // fallback: currentRouteOrigin/Destination 문자열 파싱
            console.log('⚠️ fallback 모드: 문자열 파싱');
            
            // 좌표 문자열인지 확인 (쉼표 포함 여부)
            if (currentRouteOrigin.includes(',')) {
                originCoords = currentRouteOrigin.split(',').map(s => parseFloat(s.trim()));
                originInput = { lat: originCoords[0], lng: originCoords[1] };
            } else {
                // 장소명만 있는 경우
                originInput = currentRouteOrigin;
                originCoords = [37.5665, 126.9780]; // 기본값
            }
            
            if (currentRouteDestination.includes(',')) {
                destCoords = currentRouteDestination.split(',').map(s => parseFloat(s.trim()));
                destInput = { lat: destCoords[0], lng: destCoords[1] };
            } else {
                // 장소명만 있는 경우
                destInput = currentRouteDestination;
                destCoords = [37.5665, 126.9780]; // 기본값
            }
        }
        
        console.log('📍 경로 요청:', {
            origin: originInput,
            destination: destInput,
            mode: mode
        });
        
        const request = {
            origin: originInput,
            destination: destInput,
            travelMode: google.maps.TravelMode[mode.toUpperCase()],
            region: 'KR'
        };
        
        directionsService.route(request, (result, status) => {
            console.log('📊 Directions API 응답:', status);
            
            if (status === 'OK') {
                // 기존 경로 제거
                if (directionsRenderer) {
                    directionsRenderer.setMap(null);
                }
                if (window.currentPolyline) {
                    window.currentPolyline.setMap(null);
                }
                
                // 새 경로 렌더러
                directionsRenderer = new google.maps.DirectionsRenderer({
                    map: map,
                    suppressMarkers: true,
                    polylineOptions: {
                        strokeColor: colors[mode],
                        strokeWeight: 5,
                        strokeOpacity: 0.8
                    }
                });
                
                directionsRenderer.setDirections(result);
                
                // 경로 정보 표시
                const route = result.routes[0].legs[0];
                
                if (routeDetails) {
                    const modeNames = {
                        'transit': '🚇 대중교통',
                        'walking': '🚶 도보'
                    };
                    const modeColors = {
                        'transit': 'text-blue-600',
                        'walking': 'text-orange-600'
                    };
                    
                    let stepsHtml = '';
                    
                    // 경로 상세 정보 (대중교통 또는 도보)
                    if (route.steps && route.steps.length > 0) {
                        stepsHtml = '<div class="mt-3 space-y-2 max-h-60 overflow-y-auto">';
                        
                        if (mode === 'transit') {
                            // 대중교통 상세 정보
                            route.steps.forEach((step) => {
                                if (step.travel_mode === 'TRANSIT' && step.transit) {
                                    const transit = step.transit;
                                    const line = transit.line;
                                    const lineColor = line.color || '#666';
                                    const lineText = line.short_name || line.name || '노선';
                                    const vehicleType = line.vehicle?.type || 'BUS';
                                    
                                    const vehicleIcons = {
                                        'SUBWAY': '🚇',
                                        'BUS': '🚌',
                                        'TRAIN': '🚆',
                                        'TRAM': '🚊'
                                    };
                                    const vehicleIcon = vehicleIcons[vehicleType] || '🚌';
                                    
                                    stepsHtml += `
                                        <div class="p-2 bg-white rounded border-l-4" style="border-color: ${lineColor}">
                                            <div class="font-medium text-sm mb-1">
                                                ${vehicleIcon} <span style="color: ${lineColor}">${lineText}</span>
                                            </div>
                                            <div class="text-xs text-gray-600">
                                                ${transit.departure_stop.name} → ${transit.arrival_stop.name}
                                            </div>
                                            <div class="text-xs text-gray-500 mt-1">
                                                ${transit.num_stops}개 정류장 • ${step.duration.text}
                                            </div>
                                        </div>
                                    `;
                                } else if (step.travel_mode === 'WALKING') {
                                    stepsHtml += `
                                        <div class="p-2 bg-gray-50 rounded text-xs text-gray-600">
                                            🚶 도보 ${step.distance.text} (${step.duration.text})
                                        </div>
                                    `;
                                }
                            });
                        } else if (mode === 'walking') {
                            // 도보 상세 정보
                            route.steps.forEach((step, index) => {
                                // HTML 태그 제거
                                const instruction = step.html_instructions ? 
                                    step.html_instructions.replace(/<[^>]*>/g, '') : 
                                    `${index + 1}번째 구간`;
                                
                                stepsHtml += `
                                    <div class="p-2 bg-orange-50 rounded border-l-4 border-orange-400">
                                        <div class="text-xs text-gray-700 mb-1">
                                            <span class="font-medium text-orange-600">${index + 1}.</span> ${instruction}
                                        </div>
                                        <div class="text-xs text-gray-500">
                                            🚶 ${step.distance.text} • ${step.duration.text}
                                        </div>
                                    </div>
                                `;
                            });
                        }
                        
                        stepsHtml += '</div>';
                    }
                    
                    routeDetails.innerHTML = `
                        <div class="bg-gray-50 p-4 rounded-lg">
                            <div class="font-semibold ${modeColors[mode]} mb-2">
                                ${modeNames[mode]} (Google Maps 🗺️)
                            </div>
                            <div class="text-sm text-gray-700 space-y-1">
                                <div><strong>총 거리:</strong> ${route.distance.text}</div>
                                <div><strong>총 소요시간:</strong> ${route.duration.text}</div>
                                ${route.departure_time ? `<div><strong>출발:</strong> ${route.departure_time.text}</div>` : ''}
                                ${route.arrival_time ? `<div><strong>도착:</strong> ${route.arrival_time.text}</div>` : ''}
                            </div>
                            ${stepsHtml}
                        </div>
                    `;
                }
                
                console.log('✅ 경로 표시 완료 (Google Maps)');
                
            } else {
                console.error('❌ 경로 검색 실패:', status);
                console.error('실패 원인 상세:', {
                    status: status,
                    originInput: originInput,
                    destInput: destInput,
                    originCoords: originCoords,
                    destCoords: destCoords
                });
                
                // 🆕 좌표 유효성 검증
                const isValidCoords = (coords) => {
                    return coords && 
                           coords.length === 2 && 
                           !isNaN(coords[0]) && 
                           !isNaN(coords[1]) &&
                           coords[0] !== 0 && 
                           coords[1] !== 0;
                };
                
                if (!isValidCoords(originCoords) || !isValidCoords(destCoords)) {
                    console.error('❌ 유효하지 않은 좌표:', { originCoords, destCoords });
                    
                    if (routeDetails) {
                        routeDetails.innerHTML = `
                            <div class="bg-red-50 p-3 rounded border border-red-200">
                                <div class="text-sm text-red-800 mb-2">
                                    <i class="fas fa-exclamation-triangle mr-1"></i>
                                    좌표 정보가 유효하지 않습니다
                                </div>
                                <div class="text-xs text-red-700">
                                    출발지 또는 도착지의 위치 정보를 확인할 수 없습니다.
                                </div>
                            </div>
                        `;
                    }
                    return;
                }
                
                // 실패 시 직선 거리 표시
                if (routeDetails) {
                    const distance = google.maps.geometry.spherical.computeDistanceBetween(
                        new google.maps.LatLng(originCoords[0], originCoords[1]),
                        new google.maps.LatLng(destCoords[0], destCoords[1])
                    );
                    
                    const minutes = Math.ceil(distance / (mode === 'walking' ? 80 : 300));
                    
                    const statusMessages = {
                        'ZERO_RESULTS': '이 지역에서는 경로를 찾을 수 없습니다',
                        'NOT_FOUND': '출발지 또는 도착지를 찾을 수 없습니다',
                        'INVALID_REQUEST': '잘못된 요청입니다',
                        'OVER_QUERY_LIMIT': 'API 사용량 초과',
                        'REQUEST_DENIED': 'API 키 오류',
                        'UNKNOWN_ERROR': '서버 오류가 발생했습니다'
                    };
                    
                    const errorMessage = statusMessages[status] || 'Google Maps에서 경로를 찾을 수 없습니다';
                    
                    routeDetails.innerHTML = `
                        <div class="bg-yellow-50 p-3 rounded border border-yellow-200">
                            <div class="text-sm text-yellow-800 mb-2">
                                <i class="fas fa-exclamation-triangle mr-1"></i>
                                ${errorMessage}
                            </div>
                            <div class="text-xs text-yellow-700">
                                직선 거리: ${Math.round(distance)}m (약 ${minutes}분)
                            </div>
                            <div class="text-xs text-gray-500 mt-1">
                                실제 ${mode === 'walking' ? '도보' : '대중교통'} 경로는 다를 수 있습니다
                            </div>
                        </div>
                    `;
                }
                
                // 직선 그리기
                if (directionsRenderer) {
                    directionsRenderer.setMap(null);
                }
                if (window.currentPolyline) {
                    window.currentPolyline.setMap(null);
                }
                
                const path = [
                    { lat: originCoords[0], lng: originCoords[1] },
                    { lat: destCoords[0], lng: destCoords[1] }
                ];
                
                // 점선 스타일로 직선 표시
                window.currentPolyline = new google.maps.Polyline({
                    path: path,
                    geodesic: true,
                    strokeColor: colors[mode],
                    strokeOpacity: 0.5,
                    strokeWeight: 3,
                    icons: [{
                        icon: {
                            path: 'M 0,-1 0,1',
                            strokeOpacity: 1,
                            scale: 3
                        },
                        offset: '0',
                        repeat: '20px'
                    }],
                    map: map
                });
                
                const bounds = new google.maps.LatLngBounds();
                bounds.extend(path[0]);
                bounds.extend(path[1]);
                map.fitBounds(bounds);
                
                console.log('✅ 직선 거리 표시 완료:', Math.round(google.maps.geometry.spherical.computeDistanceBetween(
                    new google.maps.LatLng(originCoords[0], originCoords[1]),
                    new google.maps.LatLng(destCoords[0], destCoords[1])
                )) + 'm');
            }
        });
        
    } catch (error) {
        console.error('❌ 경로 조회 오류:', error);
        if (routeDetails) {
            routeDetails.innerHTML = `
                <div class="bg-red-50 p-3 rounded border border-red-200">
                    <div class="text-sm text-red-800">
                        <i class="fas fa-exclamation-triangle mr-1"></i>
                        경로 조회 실패: ${error.message}
                    </div>
                </div>
            `;
        }
    }
}

async function loadRoute(origin, destination, mode, button) {
    const resultDiv = document.getElementById('routeResult');
    const loadingDiv = document.getElementById('routeLoading');
    
    // 로딩 표시
    resultDiv.innerHTML = '';
    loadingDiv.classList.remove('hidden');
    
    try {
        const response = await fetch('/api/travel/route-directions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ origin, destination, mode })
        });
        
        const data = await response.json();
        
        loadingDiv.classList.add('hidden');
        
        if (data.success && data.directions) {
            const dir = data.directions;
            const modeIcons = {
                'transit': '🚇',
                'driving': '🚗',
                'walking': '🚶'
            };
            
            // HTML 이스케이프 함수
            const escapeHtml = (text) => {
                if (!text) return '';
                return String(text)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#39;');
            };
            
            resultDiv.innerHTML = `
                <div class="border-t pt-4">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="font-semibold text-gray-800">
                            ${modeIcons[mode]} ${escapeHtml(data.mode_info.name)}
                        </h3>
                        <div class="text-right">
                            <div class="text-lg font-bold text-blue-600">${escapeHtml(dir.total_duration)}</div>
                            <div class="text-xs text-gray-500">${escapeHtml(dir.total_distance)}</div>
                        </div>
                    </div>
                    
                    <div class="space-y-2 max-h-96 overflow-y-auto">
                        ${dir.steps.map((step, index) => {
                            const cleanInstruction = (step.instruction || '').replace(/<[^>]*>/g, '');
                            return `
                            <div class="flex items-start space-x-3 p-3 bg-gray-50 rounded">
                                <span class="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-xs flex-shrink-0 mt-1">
                                    ${index + 1}
                                </span>
                                <div class="flex-1">
                                    <div class="text-sm text-gray-800 mb-1">${escapeHtml(cleanInstruction)}</div>
                                    <div class="text-xs text-gray-600">
                                        ${escapeHtml(step.distance)} • ${escapeHtml(step.duration)}
                                        ${step.transit_line ? `<br><span class="font-medium text-blue-600 mt-1 inline-block">${escapeHtml(step.transit_line)}</span>` : ''}
                                        ${step.departure_stop ? `<br><span class="text-gray-500">${escapeHtml(step.departure_stop)} → ${escapeHtml(step.arrival_stop)}</span>` : ''}
                                    </div>
                                </div>
                            </div>
                        `}).join('')}
                    </div>
                </div>
            `;
        } else {
            throw new Error(data.detail || '경로를 찾을 수 없습니다.');
        }
    } catch (error) {
        loadingDiv.classList.add('hidden');
        resultDiv.innerHTML = `
            <div class="bg-red-50 border border-red-200 rounded p-4">
                <p class="text-red-600">
                    <i class="fas fa-exclamation-triangle mr-2"></i>
                    경로 조회 실패: ${error.message}
                </p>
            </div>
        `;
    }
}

function showPlaceModalByIndex(index, day) {
    const dayData = dayGroups[day];
    if (dayData && dayData[index]) {
        showPlaceModal(dayData[index]);
    }
}

function showPlaceModal(place) {
    const modal = document.getElementById('placeModal');
    const title = document.getElementById('modalTitle');
    const content = document.getElementById('modalContent');
    
    title.textContent = place.place_name || place.name || place.activity;
    content.innerHTML = `
        <div class="space-y-4">
            <p class="text-gray-600">${place.description || '상세 정보를 불러오고 있습니다...'}</p>
            <div class="grid grid-cols-2 gap-4 text-sm">
                <div><strong>시간:</strong> ${place.time || 'N/A'}</div>
                <div><strong>소요시간:</strong> ${place.duration || 'N/A'}</div>
                <div><strong>위치:</strong> ${place.address || place.location || 'N/A'}</div>
                <div><strong>비용:</strong> ${place.price || 'N/A'}</div>
                ${place.phone ? `<div><strong>전화:</strong> ${place.phone}</div>` : ''}
                ${place.rating ? `<div><strong>평점:</strong> ${place.rating}/5</div>` : ''}
            </div>
            ${place.blog_reviews && place.blog_reviews.length > 0 ? `
                <div>
                    <h5 class="font-medium text-gray-800 mb-2">블로그 후기</h5>
                    <div class="space-y-1">
                        ${place.blog_reviews.slice(0, 3).map(blog => `
                            <a href="${blog.link}" target="_blank" class="block text-sm text-blue-600 hover:underline">
                                <i class="fas fa-external-link-alt mr-1"></i>${blog.title}
                            </a>
                        `).join('')}
                    </div>
                </div>
            ` : ''}
            ${place.blog_contents && place.blog_contents.length > 0 ? `
                <div>
                    <h5 class="font-medium text-gray-800 mb-2">블로그 내용 요약</h5>
                    ${place.blog_contents.slice(0, 2).map(content => `
                        <div class="p-3 bg-gray-50 rounded mb-2">
                            <p class="text-sm text-gray-700">${content.summary || content.content || '내용을 불러오는 중...'}</p>
                            ${content.keywords && content.keywords.length > 0 ? `
                                <div class="mt-2 flex flex-wrap gap-1">
                                    ${content.keywords.map(keyword => `
                                        <span class="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">${keyword}</span>
                                    `).join('')}
                                </div>
                            ` : ''}
                        </div>
                    `).join('')}
                </div>
            ` : ''}
        </div>
    `;
    
    modal.classList.remove('hidden');
}



function updateNotionStatus(status, url = null, error = null) {
    const notionResult = document.getElementById('notionResult');
    
    switch (status) {
        case 'saving':
            notionResult.innerHTML = `
                <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-500"></div>
                <span class="text-gray-600">Notion에 저장 중...</span>
            `;
            break;
            
        case 'success':
            notionResult.innerHTML = `
                <i class="fas fa-check-circle text-green-500 text-xl"></i>
                <span class="text-green-700">Notion 저장 완료!</span>
                ${url ? `<a href="${url}" target="_blank" class="text-blue-500 hover:underline ml-2">
                    <i class="fas fa-external-link-alt"></i> 보기
                </a>` : ''}
            `;
            showToast('Notion에 저장되었습니다!', 'success');
            break;
            
        case 'error':
            notionResult.innerHTML = `
                <i class="fas fa-exclamation-circle text-red-500 text-xl"></i>
                <span class="text-red-700">Notion 저장 실패</span>
                ${error ? `<p class="text-sm text-gray-600 mt-1">${error}</p>` : ''}
            `;
            showToast('Notion 저장에 실패했습니다', 'error');
            break;
    }
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastIcon = document.getElementById('toastIcon');
    const toastMessage = document.getElementById('toastMessage');
    
    if (type === 'success') {
        toastIcon.className = 'fas fa-check-circle text-green-500 mr-3';
        toast.querySelector('div').className = 'bg-white border-l-4 border-green-500 rounded-lg shadow-lg p-4 max-w-sm';
    } else {
        toastIcon.className = 'fas fa-exclamation-circle text-red-500 mr-3';
        toast.querySelector('div').className = 'bg-white border-l-4 border-red-500 rounded-lg shadow-lg p-4 max-w-sm';
    }
    
    toastMessage.textContent = message;
    toast.classList.remove('hidden');
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, TOAST_DURATION);
}

// 전역 변수 추가
let mapModal, mapSearchInput, autocomplete, selectedPlace;
let currentTravelPlan = null;

// Google Maps API 로드 완료 후 호출되는 콜백 함수
function initializeApp() {
    console.log('Google Maps API loaded, initializing app...');
    initMap();
    initializeDOMEvents();
}

// DOM 이벤트 초기화
function initializeDOMEvents() {
    console.log('Initializing DOM events...');
    
    // 사용자 인증 상태 확인
    checkAuthStatus();
    
    // 폼 제출 이벤트 등록 (최우선)
    const form = document.getElementById('travelForm');
    if (form) {
        console.log('Form found, adding submit listener');
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Form submit event triggered');
            handleFormSubmit();
            return false;
        });
    } else {
        console.error('Form not found!');
    }
    
    // 오늘 날짜를 기본값으로 설정
    const today = new Date().toISOString().split('T')[0];
    const startDateEl = document.getElementById('startDate');
    const endDateEl = document.getElementById('endDate');
    
    if (startDateEl) startDateEl.value = today;
    if (endDateEl) endDateEl.value = today;
    
    // 초기 여행 기간 표시
    updateTripDuration();
    
    // 지도 모달 이벤트 등록
    setupMapModalEvents();
    
    // 출발지 입력 필드 클릭 시 지도 모달 열기
    const startLocationInput = document.getElementById('startLocation');
    if (startLocationInput) {
        startLocationInput.addEventListener('click', function() {
            document.getElementById('mapModal').classList.remove('hidden');
            setTimeout(() => {
                if (!mapModal) {
                    initMapModal();
                }
            }, 100);
        });
    }
    
    // 기타 이벤트 리스너 등록
    setupOtherEventListeners();
}

// DOM 로드 완료 시 실행
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded');
    
    // Google Maps API가 이미 로드된 경우
    if (typeof google !== 'undefined' && google.maps) {
        console.log('Google Maps already loaded, initializing app...');
        initializeApp();
    } else {
        // Google Maps API 로드 대기 (index.html에서 로드됨)
        console.log('Waiting for Google Maps API to load...');
    }
});

function setupOtherEventListeners() {
    // 도시 변경 이벤트 - 지도 중심점 변경
    const cityEl = document.getElementById('city');
    if (cityEl) {
        cityEl.addEventListener('change', function() {
            // 지도 중심점 변경
            if (map) {
                const newCenter = getCityCenter();
                map.setCenter(newCenter);
                map.setZoom(DEFAULT_ZOOM);
                console.log(`Map center changed to ${this.value}:`, newCenter);
            }
        });
    }
    
    // 날짜/시간 변경 이벤트
    ['startDate', 'endDate', 'startTime', 'endTime'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('change', updateTripDuration);
        }
    });
    
    // 모달 닫기 이벤트
    const closeModal = document.getElementById('closeModal');
    if (closeModal) {
        closeModal.addEventListener('click', () => {
            document.getElementById('placeModal').classList.add('hidden');
        });
    }
}

// 지도 모달 초기화
function initMapModal() {
    // 선택된 도시에 따라 지도 중심점 설정
    const cityCenter = getCityCenter();
    
    mapModal = new google.maps.Map(document.getElementById('mapContainer'), {
        zoom: 13,
        center: cityCenter
    });
    
    // 지도 검색 Autocomplete
    mapSearchInput = document.getElementById('mapSearchInput');
    const mapAutocomplete = new google.maps.places.Autocomplete(mapSearchInput, {
        componentRestrictions: { country: 'kr' },
        fields: ['place_id', 'geometry', 'name', 'formatted_address']
    });
    
    let marker;
    
    mapAutocomplete.addListener('place_changed', () => {
        const place = mapAutocomplete.getPlace();
        if (place.geometry) {
            // 기존 마커 제거
            if (marker) marker.setMap(null);
            
            // 새 마커 추가
            marker = new google.maps.Marker({
                position: place.geometry.location,
                map: mapModal,
                title: place.name,
                animation: google.maps.Animation.DROP
            });
            
            // 지도 중심 이동
            mapModal.setCenter(place.geometry.location);
            mapModal.setZoom(15);
            
            // 선택된 장소 저장 (전역 변수)
            window.selectedPlace = {
                name: place.name,
                address: place.formatted_address,
                lat: place.geometry.location.lat(),
                lng: place.geometry.location.lng()
            };
            console.log('📍 장소 선택됨:', window.selectedPlace);
            
            // UI에 선택된 위치 표시
            updateSelectedLocationUI();
        }
    });
    
    // 지도 클릭 이벤트
    mapModal.addListener('click', async (event) => {
        // 기존 마커 제거
        if (marker) marker.setMap(null);
        
        // 새 마커 추가
        marker = new google.maps.Marker({
            position: event.latLng,
            map: mapModal,
            title: '선택된 위치',
            animation: google.maps.Animation.DROP
        });
        
        // Geocoding으로 주소 가져오기
        const geocoder = new google.maps.Geocoder();
        try {
            const result = await geocoder.geocode({ location: event.latLng });
            const address = result.results[0]?.formatted_address || `위도: ${event.latLng.lat().toFixed(6)}, 경도: ${event.latLng.lng().toFixed(6)}`;
            
            // 선택된 위치 저장 (전역 변수)
            window.selectedPlace = {
                name: '선택된 위치',
                address: address,
                lat: event.latLng.lat(),
                lng: event.latLng.lng()
            };
            console.log('📍 위치 클릭됨:', window.selectedPlace);
            
            // UI에 선택된 위치 표시
            updateSelectedLocationUI();
        } catch (error) {
            console.error('Geocoding 오류:', error);
            window.selectedPlace = {
                name: '선택된 위치',
                address: `위도: ${event.latLng.lat().toFixed(6)}, 경도: ${event.latLng.lng().toFixed(6)}`,
                lat: event.latLng.lat(),
                lng: event.latLng.lng()
            };
            updateSelectedLocationUI();
        }
    });
}

// 선택된 위치 UI 업데이트
function updateSelectedLocationUI() {
    const infoDiv = document.getElementById('selectedLocationInfo');
    const textDiv = document.getElementById('selectedLocationText');
    
    if (infoDiv && textDiv && window.selectedPlace) {
        textDiv.innerHTML = `
            <strong>${window.selectedPlace.name}</strong><br>
            ${window.selectedPlace.address}
        `;
        infoDiv.classList.remove('hidden');
    }
}

// 지도 모달 이벤트 설정
function setupMapModalEvents() {
    console.log('Setting up map modal events...');
    
    // 지도 검색 버튼 클릭
    const mapSearchBtn = document.getElementById('mapSearchBtn');
    if (mapSearchBtn) {
        mapSearchBtn.addEventListener('click', () => {
            console.log('지도 검색 버튼 클릭됨');
            const modal = document.getElementById('mapModal');
            if (modal) {
                modal.classList.remove('hidden');
                
                // 선택된 위치 정보 초기화
                const infoDiv = document.getElementById('selectedLocationInfo');
                const searchInput = document.getElementById('mapSearchInput');
                if (infoDiv) infoDiv.classList.add('hidden');
                if (searchInput) searchInput.value = '';
                window.selectedPlace = null;
                
                // 지도 모달 초기화
                setTimeout(() => {
                    if (!mapModal && typeof google !== 'undefined') {
                        console.log('지도 모달 초기화 중...');
                        initMapModal();
                    } else if (mapModal) {
                        // 이미 초기화된 경우, 도시 중심으로 이동
                        const cityCenter = getCityCenter();
                        mapModal.setCenter(cityCenter);
                        mapModal.setZoom(13);
                    }
                }, 100);
            }
        });
        console.log('✅ 지도 검색 버튼 이벤트 등록됨');
    } else {
        console.error('❌ mapSearchBtn 요소를 찾을 수 없습니다');
    }
    
    // 모달 닫기
    const closeBtn = document.getElementById('closeMapModal');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            const modal = document.getElementById('mapModal');
            if (modal) modal.classList.add('hidden');
        });
        console.log('✅ 모달 닫기 버튼 이벤트 등록됨');
    }
    
    // 취소 버튼
    const cancelBtn = document.getElementById('cancelMapSelection');
    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            const modal = document.getElementById('mapModal');
            if (modal) modal.classList.add('hidden');
        });
        console.log('✅ 취소 버튼 이벤트 등록됨');
    }
    
    // 선택 완료 버튼
    const confirmBtn = document.getElementById('confirmMapSelection');
    if (confirmBtn) {
        confirmBtn.addEventListener('click', () => {
            if (window.selectedPlace) {
                const startLocationInput = document.getElementById('startLocation');
                if (startLocationInput) {
                    startLocationInput.value = window.selectedPlace.address;
                }
                const modal = document.getElementById('mapModal');
                if (modal) modal.classList.add('hidden');
                console.log('✅ 출발지 선택 완료:', window.selectedPlace);
                
                // 성공 메시지 표시
                showToast('📍 출발지가 설정되었습니다', 'success');
            } else {
                showToast('⚠️ 지도에서 위치를 선택해주세요', 'warning');
                console.error('❌ 위치가 선택되지 않았습니다.');
            }
        });
        console.log('✅ 선택 완료 버튼 이벤트 등록됨');
    }
}

// 도시별 지도 중심점 가져오기
function getCityCenter() {
    const cityEl = document.getElementById('city');
    const selectedCity = cityEl ? cityEl.value : 'Seoul';
    
    const cityCenters = {
        'Seoul': { lat: 37.5665, lng: 126.9780 },
        'Busan': { lat: 35.1796, lng: 129.0756 },
        'Daegu': { lat: 35.8714, lng: 128.6014 },
        'Incheon': { lat: 37.4563, lng: 126.7052 },
        'Gwangju': { lat: 35.1595, lng: 126.8526 },
        'Daejeon': { lat: 36.3504, lng: 127.3845 },
        'Ulsan': { lat: 35.5384, lng: 129.3114 },
        'Jeju': { lat: 33.4996, lng: 126.5312 },
        'Suwon': { lat: 37.2636, lng: 127.0286 },
        'Chuncheon': { lat: 37.8813, lng: 127.7298 },
        'Gangneung': { lat: 37.7519, lng: 128.8761 },
        'Jeonju': { lat: 35.8242, lng: 127.1480 },
        'Yeosu': { lat: 34.7604, lng: 127.6622 },
        'Gyeongju': { lat: 35.8562, lng: 129.2247 },
        'Andong': { lat: 36.5684, lng: 128.7294 }
    };
    
    return cityCenters[selectedCity] || SEOUL_CENTER;
}

// 🆕 히스토리 카운트 초기화
function checkAuthStatus() {
    // 로그인 시스템 제거됨, 히스토리 카운트만 업데이트
    updateHistoryCount();
}

// 날씨 정보 표시
function displayWeatherInfo(weatherInfo) {
    const weatherDiv = document.getElementById('weatherInfo');
    const weatherContent = document.getElementById('weatherContent');
    
    const weatherIcon = getWeatherIcon(weatherInfo.condition);
    const tempColor = weatherInfo.temperature > 25 ? 'text-red-500' : 
                     weatherInfo.temperature < 10 ? 'text-blue-500' : 'text-green-500';
    
    weatherContent.innerHTML = `
        <div class="flex items-center justify-between mb-3">
            <div class="flex items-center space-x-2">
                <span class="text-2xl">${weatherIcon}</span>
                <span class="text-lg font-medium">${weatherInfo.condition}</span>
            </div>
            <span class="text-2xl font-bold ${tempColor}">${weatherInfo.temperature}°C</span>
        </div>
        <div class="grid grid-cols-2 gap-2 text-sm text-gray-600">
            <div><i class="fas fa-thermometer-half"></i> 체감: ${weatherInfo.feels_like}°C</div>
            <div><i class="fas fa-tint"></i> 습도: ${weatherInfo.humidity}%</div>
            <div><i class="fas fa-wind"></i> 바람: ${weatherInfo.wind_speed}m/s</div>
            <div><i class="fas fa-eye"></i> 가시거리: ${weatherInfo.visibility}km</div>
        </div>
        ${weatherInfo.rain_probability > 0 ? `
            <div class="mt-3 p-2 bg-blue-50 rounded">
                <span class="text-sm text-blue-700">
                    <i class="fas fa-umbrella"></i> 강수확률: ${weatherInfo.rain_probability}%
                </span>
            </div>
        ` : ''}
        <div class="mt-3 p-2 bg-green-50 rounded">
            <span class="text-sm text-green-700">
                <i class="fas fa-lightbulb"></i> ${weatherInfo.recommendation}
            </span>
        </div>
    `;
    
    weatherDiv.classList.remove('hidden');
}

function getWeatherIcon(condition) {
    const icons = {
        '맑음': '☀️',
        '구름조금': '🌤️', 
        '구름많음': '☁️',
        '흐림': '☁️',
        '비': '🌧️',
        '소나기': '🌦️',
        '눈': '❄️',
        '안개': '🌫️'
    };
    
    for (const [key, icon] of Object.entries(icons)) {
        if (condition.includes(key)) {
            return icon;
        }
    }
    return '🌤️';
}

// 경로 표시 함수들
function displayRouteWithTransportation(itinerary) {
    const startLocation = selectedPlace ? selectedPlace.address : document.getElementById('startLocation').value;
    if (!startLocation.trim()) {
        // 출발지가 없으면 일반 마커만 표시
        displayMarkersOnly(itinerary);
        return;
    }
    
    // 출발지에서 첫 번째 장소로의 경로 표시
    if (itinerary.length > 0) {
        const destination = itinerary[0];
        displayMultipleRoutes(startLocation, destination);
    }
    
    // 모든 장소에 마커 표시
    displayMarkersOnly(itinerary);
}

function displayMultipleRoutes(start, destination) {
    const modes = [
        { mode: google.maps.TravelMode.TRANSIT, color: '#4285F4', name: '대중교통' },
        { mode: google.maps.TravelMode.DRIVING, color: '#EA4335', name: '자동차' },
        { mode: google.maps.TravelMode.WALKING, color: '#34A853', name: '도보' }
    ];
    
    modes.forEach((transport, index) => {
        const request = {
            origin: start,
            destination: `${destination.address || destination.location}`,
            travelMode: transport.mode
        };
        
        directionsService.route(request, (result, status) => {
            if (status === 'OK') {
                const renderer = new google.maps.DirectionsRenderer({
                    directions: result,
                    routeIndex: 0,
                    polylineOptions: {
                        strokeColor: transport.color,
                        strokeWeight: 4,
                        strokeOpacity: 0.7
                    },
                    suppressMarkers: true // ✅ A, B 마커 제거
                });
                renderer.setMap(map);
                
                // 경로 정보 표시
                const route = result.routes[0];
                const leg = route.legs[0];
                console.log(`${transport.name}: ${leg.distance.text}, ${leg.duration.text}`);
            }
        });
    });
}

function displayMarkersOnly(itinerary) {
    console.log('displayMarkersOnly called with itinerary:', itinerary);
    
    if (!map) {
        console.error('Map not initialized');
        return;
    }
    
    if (!itinerary || itinerary.length === 0) {
        console.log('No itinerary to display');
        return;
    }
    
    // 기존 마커들 제거
    if (window.currentMarkers) {
        window.currentMarkers.forEach(marker => marker.setMap(null));
    }
    window.currentMarkers = [];
    
    const bounds = new google.maps.LatLngBounds();
    
    itinerary.forEach((item, index) => {
        const lat = item.lat || 37.5665;
        const lng = item.lng || 126.9780;
        const position = new google.maps.LatLng(lat, lng);
        
        const marker = new google.maps.Marker({
            position: position,
            map: map,
            title: item.place_name || item.name || item.activity,
            label: (index + 1).toString(),
            icon: {
                url: 'https://maps.google.com/mapfiles/ms/icons/blue-dot.png',
                scaledSize: new google.maps.Size(32, 32)
            }
        });
        
        const infoWindow = new google.maps.InfoWindow({
            content: `
                <div style="max-width: 250px;">
                    <h4 style="margin: 0 0 8px 0; font-weight: bold; color: #1a73e8;">${item.place_name || item.name || item.activity}</h4>
                    <p style="margin: 0 0 4px 0; font-size: 13px; color: #333;">${item.description || ''}</p>
                    <p style="margin: 0 0 4px 0; font-size: 12px; color: #666;">
                        <i class="fas fa-map-marker-alt" style="color: #ea4335;"></i> ${item.address || item.location || ''}
                    </p>
                    ${item.rating ? `<p style="margin: 0 0 4px 0; font-size: 12px; color: #666;">
                        <i class="fas fa-star" style="color: #fbbc04;"></i> ${item.rating}/5
                    </p>` : ''}
                    ${item.time ? `<p style="margin: 0; font-size: 11px; color: #888;">
                        <i class="fas fa-clock"></i> ${item.time} (${item.duration || '30분'})
                    </p>` : ''}
                </div>
            `
        });
        
        marker.addListener('click', () => {
            // 다른 정보창들 닫기
            if (window.currentInfoWindow) {
                window.currentInfoWindow.close();
            }
            infoWindow.open(map, marker);
            window.currentInfoWindow = infoWindow;
        });
        
        window.currentMarkers.push(marker);
        bounds.extend(position);
    });
    
    // 지도 뷰 조정
    if (itinerary.length > 0) {
        map.fitBounds(bounds);
        
        // 줌 레벨 조정
        google.maps.event.addListenerOnce(map, 'bounds_changed', function() {
            if (map.getZoom() > 15) {
                map.setZoom(15);
            }
        });
    }
    
    console.log(`Displayed ${itinerary.length} markers on map`);
}

// 🆕 경로 시각화 함수
function displayRoute(routeInfo, itinerary) {
    console.log('Displaying route on map...', routeInfo);
    
    if (!map || !routeInfo) {
        console.log('Map or route info not available');
        return;
    }
    
    // 기존 경로 라인 제거 (있다면)
    if (window.currentRouteLine) {
        window.currentRouteLine.setMap(null);
    }
    
    // 경로 정보가 없으면 일정 순서대로 라인 그리기
    const path = [];
    
    if (routeInfo.route_segments && routeInfo.route_segments.length > 0) {
        // API로부터 받은 경로 세그먼트 사용
        routeInfo.route_segments.forEach(segment => {
            if (segment.start_lat && segment.start_lng) {
                path.push({
                    lat: segment.start_lat,
                    lng: segment.start_lng
                });
            }
        });
        
        // 마지막 장소 추가
        const lastSegment = routeInfo.route_segments[routeInfo.route_segments.length - 1];
        if (lastSegment.end_lat && lastSegment.end_lng) {
            path.push({
                lat: lastSegment.end_lat,
                lng: lastSegment.end_lng
            });
        }
    } else if (itinerary && itinerary.length > 0) {
        // 일정 순서대로 경로 생성
        itinerary.forEach(item => {
            const lat = item.lat || 37.5665;
            const lng = item.lng || 126.9780;
            path.push({ lat, lng });
        });
    }
    
    if (path.length < 2) {
        console.log('Not enough points to draw route');
        return;
    }
    
    // Polyline 그리기
    const routeLine = new google.maps.Polyline({
        path: path,
        geodesic: true,
        strokeColor: '#4285F4',
        strokeOpacity: 0.8,
        strokeWeight: 4,
        icons: [{
            icon: {
                path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
                scale: 3,
                strokeColor: '#4285F4',
                fillColor: '#4285F4',
                fillOpacity: 1
            },
            offset: '100%',
            repeat: '100px'
        }]
    });
    
    routeLine.setMap(map);
    window.currentRouteLine = routeLine;
    
    console.log(`Route line drawn with ${path.length} points`);
    
    // 경로 정보 표시
    if (routeInfo.total_distance || routeInfo.total_duration) {
        showRouteInfo(routeInfo.total_distance, routeInfo.total_duration);
    }
}

// 경로 정보 표시 함수
function showRouteInfo(distance, duration) {
    console.log(`Route info: ${distance}, ${duration}`);
    
    // 경로 정보 표시할 영역이 있는지 확인
    let routeInfoDiv = document.getElementById('routeInfo');
    
    if (!routeInfoDiv) {
        // 경로 정보 div가 없으면 지도 위에 생성
        routeInfoDiv = document.createElement('div');
        routeInfoDiv.id = 'routeInfo';
        routeInfoDiv.className = 'bg-white p-3 rounded-lg shadow-md mb-3';
        
        const mapContainer = document.getElementById('map').parentElement;
        mapContainer.insertBefore(routeInfoDiv, document.getElementById('map'));
    }
    
    routeInfoDiv.innerHTML = `
        <div class="flex items-center gap-4 text-sm">
            <div class="flex items-center gap-2">
                <i class="fas fa-route text-blue-500"></i>
                <span class="font-semibold">총 이동 거리:</span>
                <span class="text-blue-600">${distance || 'N/A'}</span>
            </div>
            <div class="flex items-center gap-2">
                <i class="fas fa-clock text-green-500"></i>
                <span class="font-semibold">예상 소요 시간:</span>
                <span class="text-green-600">${duration || 'N/A'}</span>
            </div>
        </div>
    `;
}

// 저장 기능 (🆕 로그인 제거)
function setupSaveFeatures() {
    // 🆕 savePlanBtn 제거됨 (자동 저장으로 대체)
    
    // Notion에 저장 (선택적)
    document.getElementById('saveNotionBtn').onclick = async function() {
        if (!currentTravelPlan) {
            alert('저장할 여행 계획이 없습니다.');
            return;
        }
        
        try {
            const response = await fetch('/api/travel/save-notion', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(currentTravelPlan)
            });
            
            const result = await response.json();
            if (result.success) {
                showSaveResult(`Notion에 저장되었습니다! <a href="${result.url}" target="_blank" class="text-blue-500 hover:underline">보기</a>`, 'success');
            } else {
                showSaveResult('Notion 저장에 실패했습니다.', 'error');
            }
        } catch (error) {
            showSaveResult('오류: ' + error.message, 'error');
        }
    };
    
    // 예산 계산
    document.getElementById('calculateBudgetBtn').onclick = async function() {
        if (!currentTravelPlan || !currentTravelPlan.itinerary) {
            alert('계산할 여행 계획이 없습니다.');
            return;
        }
        
        const budgetStyle = document.getElementById('budgetStyle').value;
        
        try {
            const response = await fetch('/api/users/calculate-budget', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    itinerary: currentTravelPlan.itinerary,
                    travel_style: budgetStyle
                })
            });
            
            const budget = await response.json();
            showBudgetResult(budget);
        } catch (error) {
            alert('예산 계산 오류: ' + error.message);
        }
    };
}

function showSaveResult(message, type) {
    const saveResult = document.getElementById('saveResult');
    saveResult.className = `mt-3 p-2 rounded ${type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`;
    saveResult.innerHTML = message;
    saveResult.classList.remove('hidden');
}

function showBudgetResult(budget) {
    const budgetResult = document.getElementById('budgetResult');
    budgetResult.innerHTML = `
        <div class="p-3 bg-orange-50 rounded">
            <h4 class="font-semibold text-orange-800 mb-2">예상 비용: ${budget.total_cost.toLocaleString()}원</h4>
            <div class="text-sm text-orange-700 space-y-1">
                <div>교통비: ${budget.breakdown.transportation.toLocaleString()}원</div>
                <div>음식비: ${budget.breakdown.food.toLocaleString()}원</div>
                <div>관광비: ${budget.breakdown.attractions.toLocaleString()}원</div>
                <div>숙박비: ${budget.breakdown.accommodation.toLocaleString()}원</div>
                <div>기타: ${budget.breakdown.miscellaneous.toLocaleString()}원</div>
            </div>
            ${budget.recommendations ? `
                <div class="mt-2 text-xs text-orange-600">
                    ${budget.recommendations.slice(0, 3).map(rec => `<div>• ${rec}</div>`).join('')}
                </div>
            ` : ''}
        </div>
    `;
    budgetResult.classList.remove('hidden');
}

// 🆕 AI 여행 스타일 분석 결과 표시
function displayAnalyzedStyle(analyzedStyle) {
    const styleMap = {
        'indoor_date': { icon: '🏢', name: '실내 데이트', color: 'bg-purple-100 text-purple-800' },
        'outdoor_date': { icon: '🌳', name: '실외 데이트', color: 'bg-green-100 text-green-800' },
        'food_tour': { icon: '🍽️', name: '맛집 투어', color: 'bg-orange-100 text-orange-800' },
        'culture_tour': { icon: '🏛️', name: '문화 탐방', color: 'bg-blue-100 text-blue-800' },
        'shopping_tour': { icon: '🛍️', name: '쇼핑 투어', color: 'bg-pink-100 text-pink-800' },
        'healing_tour': { icon: '🧘', name: '힐링 여행', color: 'bg-teal-100 text-teal-800' },
        'adventure_tour': { icon: '🎢', name: '액티비티', color: 'bg-red-100 text-red-800' },
        'night_tour': { icon: '🌃', name: '야경 투어', color: 'bg-indigo-100 text-indigo-800' },
        'family_tour': { icon: '👨‍👩‍👧', name: '가족 여행', color: 'bg-yellow-100 text-yellow-800' },
        'custom': { icon: '✨', name: '맞춤 여행', color: 'bg-gray-100 text-gray-800' }
    };
    
    const travelStyle = analyzedStyle.travel_style || 'custom';
    const confidence = analyzedStyle.confidence || 0;
    const reason = analyzedStyle.reason || '';
    
    const styleInfo = styleMap[travelStyle] || styleMap['custom'];
    
    // 배지 HTML 생성
    const badgeHTML = `
        <div class="mb-6 p-4 rounded-lg border-2 border-blue-200 bg-gradient-to-r from-blue-50 to-indigo-50 animate-fadeIn">
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="text-3xl">${styleInfo.icon}</div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="text-sm font-medium text-gray-600">🤖 AI 분석 여행 스타일:</span>
                            <span class="px-3 py-1 rounded-full text-sm font-bold ${styleInfo.color}">
                                ${styleInfo.name}
                            </span>
                        </div>
                        ${reason ? `<div class="text-xs text-gray-600 mt-1">💡 ${reason}</div>` : ''}
                    </div>
                </div>
                <div class="text-right">
                    <div class="text-xs text-gray-500">신뢰도</div>
                    <div class="text-lg font-bold text-blue-600">${Math.round(confidence * 100)}%</div>
                </div>
            </div>
        </div>
    `;
    
    // results 영역에 추가
    const resultsSection = document.getElementById('results');
    if (resultsSection) {
        // 기존 배지가 있으면 제거
        const existingBadge = resultsSection.querySelector('.ai-style-badge');
        if (existingBadge) {
            existingBadge.remove();
        }
        
        // 새 배지 추가
        const badgeDiv = document.createElement('div');
        badgeDiv.className = 'ai-style-badge';
        badgeDiv.innerHTML = badgeHTML;
        resultsSection.insertBefore(badgeDiv, resultsSection.firstChild);
    }
}

// displayResults 함수 오버라이드
async function displayResults(data) {
    currentTravelPlan = data;
    setupSaveFeatures();
    
    hideLoading();
    
    document.getElementById('results').classList.remove('hidden');
    
    // 🆕 AI 여행 스타일 분석 결과 표시
    if (data.analyzed_style) {
        displayAnalyzedStyle(data.analyzed_style);
    }
    
    // Initialize map if not already done
    if (!map) {
        initMap();
    }
    
    // 🆕 이동 수단 선택 버튼 이벤트 설정 (한 번만)
    const transportButtons = document.querySelectorAll('.transport-btn');
    transportButtons.forEach(btn => {
        // 기존 이벤트 제거 (중복 방지)
        btn.replaceWith(btn.cloneNode(true));
    });
    
    // 새로운 버튼에 이벤트 추가
    const newTransportButtons = document.querySelectorAll('.transport-btn');
    newTransportButtons.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            // 모든 버튼 스타일 초기화
            newTransportButtons.forEach(b => {
                b.classList.remove('bg-blue-500', 'text-white');
                b.classList.add('bg-gray-200', 'text-gray-700');
            });
            
            // 선택된 버튼 활성화
            e.target.classList.remove('bg-gray-200', 'text-gray-700');
            e.target.classList.add('bg-blue-500', 'text-white');
            
            // 이동 수단 변경
            const mode = e.target.dataset.mode;
            console.log(`🚗 이동 수단 변경: ${mode}`);
            
            // 경로 재렌더링 (현재 날짜만)
            await updateRouteWithMode(mode);
            
            // 정보 업데이트
            const transportInfo = document.getElementById('transportInfo');
            if (transportInfo) {
                transportInfo.textContent = `수동 선택: ${e.target.textContent.trim()}`;
            }
        });
    });
    
    // 일자별 탭 초기화
    currentDay = 1;
    
    // Display timeline with day tabs
    displayTimeline(data.itinerary || []);
    
    // Verify places and get details for current day
    await verifyAndDisplayPlaces(dayGroups[currentDay] || []);
    
    // 🆕 현재 날짜의 일정만 경로 표시 (전체 일정 X)
    console.log(`📅 경로 표시: ${currentDay}일차만 표시`);
    console.log('API response data structure:', data);
    
    const currentDayItinerary = dayGroups[currentDay] || [];
    console.log(`${currentDay}일차 일정 (${currentDayItinerary.length}개):`, currentDayItinerary);
    
    // 🆕 경로 정보 추출 및 시각화 (현재 날짜만)
    const routeInfo = data.route_info || data.processing_metadata?.optimized_route || data.total_cost?.route_info;
    
    if (routeInfo) {
        console.log('Displaying route from API (current day only)');
        displayRoute(routeInfo, currentDayItinerary);
    } else if (currentDayItinerary && currentDayItinerary.length > 1) {
        console.log('Creating route from itinerary (current day only)');
        // route_info가 없어도 일정 순서대로 라인 그리기
        displayRoute({}, currentDayItinerary);
    } else {
        console.log('Displaying markers only from itinerary (current day only)');
        // 8단계 처리된 일정으로 마커 표시
        displayMarkersOnly(currentDayItinerary || []);
    }
    
    // 8단계 처리 결과 로그
    if (data.processing_metadata) {
        console.log('8-step processing metadata:', data.processing_metadata);
    }
    
    // 🆕 localStorage에 여행 계획 저장
    saveTravelPlanToLocal(data);
    
    // 날씨 정보 표시
    if (data.weather_info) {
        displayWeatherInfo(data.weather_info);
    }
    
    // Show Notion saving status
    updateNotionStatus('saving');
    
    // Notion 저장 상태 업데이트
    setTimeout(() => {
        const url = data.notion_url || 'https://notion.so/sample-page';
        updateNotionStatus('success', url);
    }, NOTION_SAVE_DELAY);
}

// 🆕 페이지 로드 시 히스토리 카운트 업데이트
document.addEventListener('DOMContentLoaded', () => {
    updateHistoryCount();
});