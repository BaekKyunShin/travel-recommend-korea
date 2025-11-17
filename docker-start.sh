#!/bin/bash

# 🐳 Docker로 한국 여행 플래너 실행

echo "🐳 Docker 컨테이너로 한국 여행 플래너를 시작합니다..."

# 색상 정의
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Docker 설치 확인
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker가 설치되지 않았습니다.${NC}"
    echo "Docker Desktop을 설치하세요: https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Docker Compose 확인
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose가 설치되지 않았습니다.${NC}"
    exit 1
fi

# .env 파일 확인
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env 파일이 없습니다. 생성 중...${NC}"
    cp .env.example .env 2>/dev/null || cat > .env << 'EOF'
# 🐳 Docker 환경변수

# Redis 캐시 (Docker 내부 연결)
REDIS_URL=redis://redis:6379/0
CACHE_TTL=3600

# API 키 (실제 값으로 교체 필요)
OPENAI_API_KEY=your-openai-api-key-here
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
NAVER_CLIENT_ID=your-naver-client-id
NAVER_CLIENT_SECRET=your-naver-client-secret
OPENWEATHER_API_KEY=your-openweather-api-key
NOTION_TOKEN=your-notion-token

# 설정
DEBUG=True
ENVIRONMENT=development
LOG_LEVEL=INFO
USE_MOCK_DATA=False
EOF
    echo -e "${GREEN}✅ .env 파일 생성 완료${NC}"
    echo -e "${YELLOW}⚠️  .env 파일에서 API 키들을 실제 값으로 교체해주세요!${NC}"
fi

# 기존 컨테이너 정리 (선택사항)
read -p "기존 컨테이너를 정리하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🧹 기존 컨테이너 정리 중...${NC}"
    docker-compose down -v
fi

# Docker 이미지 빌드 및 실행
echo -e "${BLUE}🔨 Docker 이미지 빌드 중...${NC}"
docker-compose build

echo -e "${BLUE}🚀 컨테이너 시작 중...${NC}"
docker-compose up -d

# 서비스 시작 대기
echo -e "${YELLOW}⏳ 서비스 준비 중... (약 30초)${NC}"
sleep 5

# 상태 확인
echo -e "\n${BLUE}📊 서비스 상태:${NC}"
docker-compose ps

# 헬스체크
echo -e "\n${BLUE}🔍 서비스 헬스체크:${NC}"
sleep 10

if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ API 서버 정상 실행 중${NC}"
else
    echo -e "${YELLOW}⏳ API 서버 시작 중... (로그 확인: docker-compose logs app)${NC}"
fi

# 완료 메시지
echo -e "\n${GREEN}🎉 Docker 컨테이너 시작 완료!${NC}\n"

echo -e "${BLUE}📋 접속 정보:${NC}"
echo -e "  🌐 웹 UI:      ${GREEN}http://localhost:8000${NC}"
echo -e "  📚 API 문서:   ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  💾 Redis 캐시: ${GREEN}localhost:6379${NC}"

echo -e "\n${BLUE}🔧 유용한 명령어:${NC}"
echo -e "  • 로그 확인:        ${YELLOW}docker-compose logs -f app${NC}"
echo -e "  • 모든 로그:        ${YELLOW}docker-compose logs -f${NC}"
echo -e "  • 컨테이너 재시작:  ${YELLOW}docker-compose restart app${NC}"
echo -e "  • 컨테이너 중지:    ${YELLOW}docker-compose down${NC}"
echo -e "  • 완전 삭제:        ${YELLOW}docker-compose down -v${NC}"

echo -e "\n${BLUE}💡 다음 단계:${NC}"
echo -e "  1. ${YELLOW}.env 파일에서 API 키들을 실제 값으로 교체${NC}"
echo -e "  2. ${YELLOW}브라우저에서 http://localhost:8000 접속${NC}"
echo -e "  3. ${YELLOW}여행 계획 생성 시작! 🎉${NC}"

echo -e "\n${GREEN}🚀 즐거운 개발 되세요!${NC}"

