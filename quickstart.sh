#!/bin/bash

# 🇰🇷 한국 여행 플래너 빠른 시작 스크립트

echo "🚀 한국 여행 플래너 설정을 시작합니다..."

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. 필수 도구 확인
echo -e "${BLUE}📋 필수 도구 확인 중...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker가 설치되지 않았습니다. 설치 후 다시 실행해주세요.${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose가 설치되지 않았습니다. 설치 후 다시 실행해주세요.${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3가 설치되지 않았습니다. 설치 후 다시 실행해주세요.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ 필수 도구 확인 완료${NC}"

# 2. 가상환경 확인
echo -e "${BLUE}📦 가상환경 확인 중...${NC}"
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}⚠️  가상환경을 활성화하세요: source ../bin/activate${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 가상환경 활성화됨${NC}"

# 3. 환경변수 파일 생성
echo -e "${BLUE}⚙️  환경변수 설정 중...${NC}"
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# =============================================================================
# 스마트 한국 여행 플래너 - 환경변수 설정
# =============================================================================

# 개발 환경 설정
DEBUG=True
ENVIRONMENT=development
LOG_LEVEL=INFO

# Redis 캐시 설정 (AI 응답 캐싱용)
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_TTL=3600

# OpenAI API (필수 - 실제 키로 교체 필요)
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4-1106-preview
OPENAI_MAX_TOKENS=2000

# Naver API (필수 - 실제 키로 교체 필요)
NAVER_CLIENT_ID=your-naver-client-id
NAVER_CLIENT_SECRET=your-naver-client-secret

# Google Maps API (필수 - 실제 키로 교체 필요)
GOOGLE_MAPS_API_KEY=your-google-maps-api-key

# OpenWeatherMap API (필수 - 실제 키로 교체 필요)
OPENWEATHER_API_KEY=your-openweather-api-key

# Notion API (필수 - 실제 키로 교체 필요)
NOTION_TOKEN=your-notion-integration-token
NOTION_DATABASE_ID=

# 기본 설정
DEFAULT_CITY=Seoul
DEFAULT_LANGUAGE=ko
DEFAULT_CURRENCY=KRW
DEFAULT_DURATION_HOURS=6
DEFAULT_BUDGET_PER_PERSON=50000

# 개발용 설정 (API 키가 없을 때 임시로 사용)
USE_MOCK_DATA=True
IGNORE_CACHE=False
VERBOSE_LOGGING=True
EOF

    echo -e "${GREEN}✅ .env 파일 생성 완료${NC}"
    echo -e "${YELLOW}⚠️  .env 파일에서 실제 API 키들을 설정해주세요!${NC}"
else
    echo -e "${GREEN}✅ .env 파일이 이미 존재합니다${NC}"
fi

# 4. Docker 서비스 시작 (Redis만 사용, PostgreSQL 제거)
echo -e "${BLUE}🐳 Redis 서비스 시작 중...${NC}"
docker-compose up -d redis

# 잠시 대기 (서비스 시작 시간)
echo -e "${YELLOW}⏳ Redis 시작 대기 중...${NC}"
sleep 5

# 5. Python 의존성 설치
echo -e "${BLUE}📚 Python 의존성 설치 중...${NC}"
pip install -r requirements.txt

# 6. 서비스 상태 확인
echo -e "${BLUE}🔍 Redis 서비스 상태 확인 중...${NC}"

# Redis 연결 테스트
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis 연결 성공${NC}"
else
    echo -e "${RED}❌ Redis 연결 실패${NC}"
    echo -e "${YELLOW}⚠️  Redis 없이도 작동하지만 (메모리 캐시 폴백), 성능을 위해 Redis 사용을 권장합니다.${NC}"
fi

# 8. 완료 메시지
echo -e "\n${GREEN}🎉 설정 완료! 이제 여행 플래너를 시작할 수 있습니다.${NC}\n"

echo -e "${BLUE}📋 다음 단계:${NC}"
echo -e "1. ${YELLOW}.env 파일에서 API 키들을 실제 값으로 교체${NC}"
echo -e "2. ${YELLOW}서버 시작: python -m uvicorn app.main:app --reload${NC}"
echo -e "3. ${YELLOW}브라우저에서 http://localhost:8000 접속${NC}"
echo -e "4. ${YELLOW}API 문서 확인: http://localhost:8000/docs${NC}"

echo -e "\n${BLUE}💡 API 키 발급 링크:${NC}"
echo -e "• OpenAI: https://platform.openai.com/api-keys"
echo -e "• Naver: https://developers.naver.com/apps/"
echo -e "• Google Maps: https://console.cloud.google.com/"
echo -e "• OpenWeatherMap: https://openweathermap.org/api"
echo -e "• Notion: https://developers.notion.com/"

echo -e "\n${BLUE}🆘 도움이 필요하면:${NC}"
echo -e "• README_REVISED.md 문서 참고"
echo -e "• IMPLEMENTATION_GUIDE.md 구현 가이드 참고"
echo -e "• 문제 발생시 docker-compose logs 명령어로 로그 확인"

echo -e "\n${GREEN}🚀 즐거운 개발 되세요!${NC}"
