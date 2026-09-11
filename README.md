# My Reading Journey - 영어독서 관리 프로그램

영어 읽기 실력을 향상시키기 위한 주간 독서 계획 관리 및 보카 학습 플랫폼입니다.

## 기능

### 1. 주간 읽기 계획 (Weekly Reading Plan)
- 이번주 읽을 책 정보 표시
- 읽어야 할 챕터 목록 및 페이지 범위
- 챕터별 완료/미완료 추적
- 주간 목표 진행도 표시

### 2. 보카 관리 (Vocabulary)
- 책에서 배운 새로운 단어 등록
- 단어의 뜻, 예문 저장
- 단어 발음 듣기 (TTS)
- 주간 보카 리스트 조회

### 3. 서머리 라이팅 (Summary Writing)
- 모든 챕터 완료 후 내용 정리
- 핵심 내용, 인상 깊은 장면, 개인 의견 작성
- (추후 확장 예정)

## 기술 스택

- **백엔드**: Flask
- **데이터베이스**: Microsoft SQL Server (ms1901.gabiadb.com / yujincast)
- **프론트엔드**: HTML, CSS, JavaScript
- **데이터베이스 접근**: pyodbc

## 설치 및 실행

### 1. 환경 설정

```bash
# 프로젝트 폴더로 이동
cd EnglishReadingJourney

# 가상환경 생성 (선택사항)
python -m venv venv
venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 정보를 입력합니다:

```env
FLASK_SECRET_KEY=your-secret-key-here
FLASK_DEBUG=true

DB_SERVER=ms1901.gabiadb.com
DB_DATABASE=yujincast
DB_USERNAME=your_username
DB_PASSWORD=your_password
DB_DRIVER=ODBC Driver 18 for SQL Server
```

### 3. 데이터베이스 테이블 생성

SQL Server Management Studio 또는 sqlcmd에서 `db_schema.sql` 실행:

```bash
# SQL Server에 연결하여 스크립트 실행
sqlcmd -S ms1901.gabiadb.com -U your_username -P your_password -d yujincast -i db_schema.sql
```

또는 SSMS에서 `db_schema.sql` 파일을 열어 실행합니다.

### 4. 앱 실행

```bash
python app.py
```

브라우저에서 `http://localhost:5003` 접속

## 데이터베이스 테이블 구조

### En_book_Plan (읽기 계획)
- `plan_id`: 계획 ID (Primary Key)
- `book_title`: 책 제목
- `author`: 저자
- `week_start`: 주간 시작일
- `week_end`: 주간 종료일
- `total_chapters`: 총 챕터 수
- `current_progress`: 현재 완료 챕터 수
- `created_date`: 생성 날짜
- `updated_date`: 수정 날짜

### En_book_Plan_Chapters (챕터 목록)
- `chapter_id`: 챕터 ID (Primary Key)
- `plan_id`: 계획 ID (Foreign Key)
- `chapter_number`: 챕터 번호
- `page_start`: 시작 페이지
- `page_end`: 종료 페이지
- `completed`: 완료 여부
- `completed_date`: 완료 날짜
- `created_date`: 생성 날짜

### En_book_Vocabulary (보카 테이블)
- `vocab_id`: 단어 ID (Primary Key)
- `word`: 단어
- `definition`: 뜻
- `example`: 예문 (선택사항)
- `plan_id`: 연관 계획 ID (Foreign Key, 선택사항)
- `chapter_id`: 연관 챕터 ID (Foreign Key, 선택사항)
- `created_date`: 생성 날짜

## API 엔드포인트

### GET /
메인 페이지 - 이번주 읽기 계획 조회

### POST /api/mark-chapter-complete/<chapter_id>
특정 챕터를 완료로 표시

**응답 예시:**
```json
{
    "success": true,
    "message": "챕터가 완료되었습니다."
}
```

### POST /api/add-vocabulary
새 단어 추가

**요청 바디:**
```json
{
    "word": "injustice",
    "definition": "부당함; 불의",
    "example": "This injustice must be stopped."
}
```

**응답 예시:**
```json
{
    "success": true,
    "vocab_id": 1,
    "message": "단어가 추가되었습니다."
}
```

## 샘플 데이터 입력

다음 SQL을 실행하여 테스트 데이터를 삽입합니다:

```sql
-- 플랜 추가
DECLARE @plan_id INT;
INSERT INTO En_book_Plan (book_title, author, week_start, week_end, total_chapters)
VALUES ('The Hate U Give', 'Angie Thomas', '2025-05-20', '2025-05-26', 5);

SET @plan_id = SCOPE_IDENTITY();

-- 챕터 추가
INSERT INTO En_book_Plan_Chapters (plan_id, chapter_number, page_start, page_end)
VALUES 
    (@plan_id, 16, 153, 168),
    (@plan_id, 17, 169, 188),
    (@plan_id, 18, 189, 205),
    (@plan_id, 19, 206, 223),
    (@plan_id, 20, 224, 241);

-- 보카 추가
INSERT INTO En_book_Vocabulary (word, definition, example, plan_id)
VALUES 
    (@plan_id, 'injustice', '부당함; 불의', 'This injustice must be stopped.'),
    (@plan_id, 'identity', '정체성', 'Finding your identity is important.'),
    (@plan_id, 'resilience', '회복력', 'Her resilience helped her overcome challenges.'),
    (@plan_id, 'empower', '권하을 부여하다', 'Education will empower you.');
```

## 앞으로의 기능 확장

- [ ] 사용자 인증 및 회원 관리
- [ ] 다중 책 관리 (과거 책 기록)
- [ ] 서머리 라이팅 저장 및 조회
- [ ] 진행도 통계 및 그래프
- [ ] 모바일 앱 (React Native)
- [ ] 음성 인식을 통한 발음 평가
- [ ] 스터디 그룹 기능

## 주의사항

- 초기 설정: `.env` 파일 생성 필수
- DB 연결: ms1901.gabiadb.com 서버에 접근 가능해야 함
- ODBC Driver 설치: 시스템에 "ODBC Driver 18 for SQL Server" 또는 "SQL Server" 드라이버 필요

## 라이선스

프로젝트 개인용 (학습용)

## 연락처

issues 또는 피드백은 프로젝트 관리자에게 문의하시기 바랍니다.
