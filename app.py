import os
import pyodbc
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, redirect, url_for
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'secret-key-for-dev')


def format_date_for_input(date_obj):
    """날짜 객체나 문자열을 HTML input[type="date"]가 인식할 수 있는 YYYY-MM-DD 형식으로 변환"""
    if not date_obj:
        return ''
    
    try:
        # datetime 객체인 경우
        if isinstance(date_obj, datetime):
            return date_obj.strftime('%Y-%m-%d')
        
        # 문자열인 경우
        if isinstance(date_obj, str):
            # 이미 YYYY-MM-DD 형식이면 그대로 반환
            if len(date_obj) == 10 and date_obj[4] == '-' and date_obj[7] == '-':
                return date_obj
            
            # 다른 형식을 시도해서 변환
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y']:
                try:
                    dt = datetime.strptime(date_obj, fmt)
                    return dt.strftime('%Y-%m-%d')
                except ValueError:
                    continue
        
        return str(date_obj) if date_obj else ''
    except Exception as e:
        print(f"Error formatting date {date_obj}: {e}")
        return str(date_obj) if date_obj else ''


def format_date_for_display(date_obj):
    """날짜 객체나 문자열을 화면 표시용 YYYY/MM/DD 형식으로 변환"""
    if not date_obj:
        return ''
    
    try:
        # datetime 객체인 경우
        if isinstance(date_obj, datetime):
            return date_obj.strftime('%Y/%m/%d')
        
        # 문자열인 경우
        if isinstance(date_obj, str):
            # YYYY/MM/DD 형식이면 그대로 반환
            if len(date_obj) == 10 and date_obj[4] == '/' and date_obj[7] == '/':
                return date_obj
            
            # 다른 형식을 시도해서 변환
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d']:
                try:
                    dt = datetime.strptime(date_obj, fmt)
                    return dt.strftime('%Y/%m/%d')
                except ValueError:
                    continue
        
        return str(date_obj) if date_obj else ''
    except Exception as e:
        print(f"Error formatting date {date_obj}: {e}")
        return str(date_obj) if date_obj else ''


def parse_vocab_tsv_line(line):
    """TSV 한 줄을 보카 dict로 변환한다. 앞의 연번호를 무시한다."""
    raw_line = line.strip()
    if not raw_line:
        return None

    if '|' in raw_line:
        cells = [cell.strip() for cell in raw_line.split('|') if cell.strip()]
    elif '\t' in raw_line:
        cells = [cell.strip() for cell in raw_line.split('\t') if cell.strip()]
    else:
        cells = [cell.strip() for cell in raw_line.split() if cell.strip()]

    if not cells:
        return None

    if cells[0].replace('.', '').isdigit():
        cells = cells[1:]

    if len(cells) >= 3:
        word, pos, meaning = cells[0], cells[1], cells[2]
        example = ' '.join(cells[3:]) if len(cells) > 3 else ''
        if not word or not meaning:
            return None
        return {
            'word': word,
            'pos': pos,
            'meaning': meaning,
            'example': example
        }

    if len(cells) == 2:
        word, meaning = cells[0], cells[1]
        if not word or not meaning:
            return None
        return {
            'word': word,
            'pos': '',
            'meaning': meaning,
            'example': ''
        }

    return None

# Jinja2 필터 등록
@app.template_filter('strftime')
def strftime_filter(date_obj, fmt='%m.%d'):
    """날짜를 지정된 형식으로 포맷"""
    if isinstance(date_obj, str):
        # 문자열이면 datetime으로 변환
        try:
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
        except:
            return date_obj
    if date_obj:
        return date_obj.strftime(fmt)
    return ''


@app.template_filter('dateformat')
def dateformat_filter(date_obj):
    """날짜를 YYYY/MM/DD 형식으로 포맷"""
    return format_date_for_display(date_obj)

# DB 설정
DB_SERVER = os.getenv('DB_SERVER', 'ms1901.gabiadb.com')
DB_DATABASE = os.getenv('DB_DATABASE', 'yujincast')
DB_USERNAME = os.getenv('DB_USERNAME', '')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')
DB_DRIVER = os.getenv('DB_DRIVER', 'ODBC Driver 18 for SQL Server')

def get_db_conn():
    conn_str = (
        f'DRIVER={{{DB_DRIVER}}};'
        f'SERVER={DB_SERVER};'
        f'DATABASE={DB_DATABASE};'
        f'UID={DB_USERNAME};'
        f'PWD={DB_PASSWORD};'
        'Encrypt=yes;TrustServerCertificate=yes;'
    )
    return pyodbc.connect(conn_str)


def table_has_column(table_name, column_name):
    """테이블에 특정 컬럼이 있는지 확인"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 1
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
            """,
            (table_name, column_name),
        )
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    except Exception:
        return False


def ensure_en_book_list_image_url_column():
    """EN_book_list에 book_image_url 컬럼이 없으면 추가"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'EN_book_list' AND COLUMN_NAME = 'book_image_url'
            )
            BEGIN
                ALTER TABLE EN_book_list
                ADD book_image_url NVARCHAR(500) NULL
            END
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to ensure EN_book_list.book_image_url column: {e}")


def ensure_chapter_writing_table():
    """챕터별 라이팅 저장 테이블이 없으면 생성"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = 'En_book_Chapter_Writing'
            )
            BEGIN
                CREATE TABLE En_book_Chapter_Writing (
                    writing_id INT IDENTITY(1,1) PRIMARY KEY,
                    plan_id INT NOT NULL,
                    chapter_id INT NOT NULL UNIQUE,
                    summary_main NVARCHAR(MAX) NULL,
                    summary_scene NVARCHAR(MAX) NULL,
                    summary_thought NVARCHAR(MAX) NULL,
                    writing_text NVARCHAR(MAX) NULL,
                    created_date DATETIME NOT NULL DEFAULT GETDATE(),
                    updated_date DATETIME NOT NULL DEFAULT GETDATE()
                )
            END

            IF NOT EXISTS (
                SELECT 1
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'En_book_Chapter_Writing' AND COLUMN_NAME = 'summary_main'
            )
            BEGIN
                ALTER TABLE En_book_Chapter_Writing
                ADD summary_main NVARCHAR(MAX) NULL
            END

            IF NOT EXISTS (
                SELECT 1
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'En_book_Chapter_Writing' AND COLUMN_NAME = 'summary_scene'
            )
            BEGIN
                ALTER TABLE En_book_Chapter_Writing
                ADD summary_scene NVARCHAR(MAX) NULL
            END

            IF NOT EXISTS (
                SELECT 1
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'En_book_Chapter_Writing' AND COLUMN_NAME = 'summary_thought'
            )
            BEGIN
                ALTER TABLE En_book_Chapter_Writing
                ADD summary_thought NVARCHAR(MAX) NULL
            END
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to ensure chapter writing table: {e}")


def ensure_chapter_completion_log_table():
    """챕터 완료 이력 및 포인트 누적 테이블이 없으면 생성한다."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            IF NOT EXISTS (
                SELECT 1
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_NAME = 'En_book_Chapter_Completion_Log'
            )
            BEGIN
                CREATE TABLE En_book_Chapter_Completion_Log (
                    log_id INT IDENTITY(1,1) PRIMARY KEY,
                    plan_id INT NOT NULL,
                    chapter_id INT NOT NULL,
                    chapter_number INT NULL,
                    completed_at DATETIME NOT NULL DEFAULT GETDATE(),
                    earned_points INT NOT NULL DEFAULT 0,
                    cancelled_at DATETIME NULL,
                    cancelled_reason NVARCHAR(255) NULL,
                    created_date DATETIME NOT NULL DEFAULT GETDATE()
                )
            END

            IF COL_LENGTH('En_book_Chapter_Completion_Log', 'chapter_number') IS NULL
            BEGIN
                ALTER TABLE En_book_Chapter_Completion_Log
                ADD chapter_number INT NULL
            END

            IF COL_LENGTH('En_book_Chapter_Completion_Log', 'earned_points') IS NULL
            BEGIN
                ALTER TABLE En_book_Chapter_Completion_Log
                ADD earned_points INT NOT NULL DEFAULT 0
            END

            IF COL_LENGTH('En_book_Chapter_Completion_Log', 'cancelled_at') IS NULL
            BEGIN
                ALTER TABLE En_book_Chapter_Completion_Log
                ADD cancelled_at DATETIME NULL
            END

            IF COL_LENGTH('En_book_Chapter_Completion_Log', 'cancelled_reason') IS NULL
            BEGIN
                ALTER TABLE En_book_Chapter_Completion_Log
                ADD cancelled_reason NVARCHAR(255) NULL
            END
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to ensure chapter completion log table: {e}")


def get_total_earned_points(plan_id):
    """해당 계획의 누적 포인트 합계를 반환한다."""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT ISNULL(SUM(earned_points), 0)
            FROM En_book_Chapter_Completion_Log
            WHERE plan_id = ? AND cancelled_at IS NULL
            """,
            (plan_id,),
        )
        total = cursor.fetchone()[0]
        conn.close()
        return int(total or 0)
    except Exception:
        return 0


def get_chapter_completion_points(chapter_number):
    """완료 보상 포인트 계산. 챕터당 5점으로 통일한다."""
    try:
        return 5
    except Exception:
        return 5


def get_table_columns(table_name):
    """테이블의 컬럼명을 set으로 반환"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = ?
            """,
            (table_name,),
        )
        columns = {row[0] for row in cursor.fetchall()}
        conn.close()
        return columns
    except Exception:
        return set()


def resolve_existing_column(existing_columns, candidates):
    """후보 컬럼명 중 실제 존재하는 첫 컬럼 반환"""
    for name in candidates:
        if name in existing_columns:
            return name
    return None


def quote_sql_column(column_name):
    """SQL Server 컬럼명 안전 quoting"""
    return f"[{column_name.replace(']', ']]')}]"


def get_first_value(book_dict, candidates):
    """dict에서 후보 키 중 첫 값을 반환"""
    for name in candidates:
        if name in book_dict:
            return book_dict.get(name)
    return None


def resolve_plan_id_from_chapter_id(cursor, chapter_id):
    """chapter_id로부터 plan_id를 조회"""
    cursor.execute(
        "SELECT plan_id FROM En_book_Plan_Chapters WHERE chapter_id = ?",
        (chapter_id,),
    )
    row = cursor.fetchone()
    return row.plan_id if row else None


def get_home_book_metadata(cursor):
    """EN_book_list에서 책 메타데이터를 조회하고, 없으면 None을 반환한다."""
    try:
        cursor.execute("SELECT TOP 1 * FROM EN_book_list")
        row = cursor.fetchone()
        if row is None:
            return None

        columns = [desc[0] for desc in cursor.description]
        return {column: row[idx] for idx, column in enumerate(columns)}
    except Exception:
        return None


@app.route('/')
def index():
    """메인 페이지 - 읽기 계획 (주간 네비게이션 가능)"""
    try:
        # URL 파라미터에서 주 오프셋 가져오기 (기본값: 0 = 이번주)
        week_offset = request.args.get('week_offset', 0, type=int)
        requested_plan_id = request.args.get('plan_id', type=int)
        requested_chapter_id = request.args.get('chapter_id', type=int)

        # 조회 날짜 계산
        target_date = datetime.now() + timedelta(weeks=week_offset)
        week_start_date = target_date - timedelta(days=target_date.weekday())
        week_end_date = week_start_date + timedelta(days=6)

        conn = get_db_conn()
        cursor = conn.cursor()
        has_cover_url = table_has_column('En_book_Plan', 'book_cover_url')

        plan = None
        if requested_plan_id:
            query = """
            SELECT TOP 1
                p.plan_id,
                p.book_title,
                p.author,
                p.week_start,
                p.week_end,
                p.current_progress,
                p.total_chapters,
                """ + ('p.book_cover_url,' if has_cover_url else '') + """
                b.[AR (ATOS)],
                b.Point,
                b.Lexile
            FROM En_book_Plan p
            LEFT JOIN EN_book_list b ON p.book_title = b.책_제목
            WHERE p.plan_id = ?
            """
            cursor.execute(query, (requested_plan_id,))
            plan = cursor.fetchone()

        if plan is None:
            # 지정된 주에 해당하는 플랜 가져오기 (EN_book_list와 LEFT JOIN)
            query = """
            SELECT TOP 1 
                p.plan_id,
                p.book_title,
                p.author,
                p.week_start,
                p.week_end,
                p.current_progress,
                p.total_chapters,
                """ + ('p.book_cover_url,' if has_cover_url else '') + """
                b.[AR (ATOS)],
                b.Point,
                b.Lexile
            FROM En_book_Plan p
            LEFT JOIN EN_book_list b ON p.book_title = b.책_제목
            WHERE p.week_start <= CAST(? AS DATE)
              AND p.week_end >= CAST(? AS DATE)
            ORDER BY p.plan_id DESC
            """
            cursor.execute(query, (target_date, target_date))
            plan = cursor.fetchone()

        # 현재 주의 챕터 목록
        chapters = []
        selected_chapter_id = None
        if plan:
            chapter_query = """
            SELECT 
                chapter_id,
                chapter_number,
                page_start,
                page_end,
                completed
            FROM En_book_Plan_Chapters
            WHERE plan_id = ?
            ORDER BY chapter_number
            """
            cursor.execute(chapter_query, (plan.plan_id,))
            chapters = cursor.fetchall()

            if requested_chapter_id:
                selected_chapter_id = next(
                    (ch.chapter_id for ch in chapters if ch.chapter_id == requested_chapter_id),
                    chapters[0].chapter_id if chapters else None,
                )
            else:
                selected_chapter_id = chapters[0].chapter_id if chapters else None

            # 실제 완료된 챕터 수 계산
            completed_count = sum(1 for ch in chapters if ch.completed)
            # plan_data에서 사용하기 위해 임시 저장
            plan.current_progress = completed_count

        # 보카 리스트 - 모든 단어 조회
        vocab_query = """
        SELECT
            vocab_id,
            chapter_id,
            word,
            definition,
            example
        FROM En_book_Vocabulary
        WHERE plan_id = ?
        ORDER BY chapter_id, vocab_id
        """
        if plan:
            cursor.execute(vocab_query, (plan.plan_id,))
            vocabulary = cursor.fetchall()
        else:
            vocabulary = []

        conn.close()
        
        plan_data = {
            'plan_id': plan.plan_id if plan else None,
            'book_title': plan.book_title if plan else '',
            'author': plan.author if plan else '',
            'week_start': format_date_for_display(plan.week_start) if plan else '',
            'week_end': format_date_for_display(plan.week_end) if plan else '',
            'current_progress': plan.current_progress if plan else 0,
            'total_chapters': plan.total_chapters if plan else 0,
            'book_cover_url': getattr(plan, 'book_cover_url', None) if plan else None,
            'atos': getattr(plan, 'AR (ATOS)', None) if plan else None,
            'ar_point': getattr(plan, 'Point', None) if plan else None,
            'lexile': getattr(plan, 'Lexile', None) if plan else None,
        } if plan else None

        nav_week_start = format_date_for_display(plan.week_start) if plan else format_date_for_display(week_start_date)
        nav_week_end = format_date_for_display(plan.week_end) if plan else format_date_for_display(week_end_date)
        
        return render_template('index.html', 
                             plan=plan_data, 
                             chapters=chapters, 
                             vocabulary=vocabulary,
                             selected_chapter_id=selected_chapter_id,
                             week_offset=week_offset,
                             nav_week_start=nav_week_start,
                             nav_week_end=nav_week_end)
    except Exception as e:
        print(f"Error: {e}")
        return render_template(
            'index.html',
            error=str(e),
            week_offset=0,
            nav_week_start='',
            nav_week_end=''
        )

@app.route('/api/mark-chapter-complete/<int:chapter_id>', methods=['POST'])
def mark_chapter_complete(chapter_id):
    """챕터 완료 상태를 토글한다. 완료 이력과 포인트 누적도 함께 관리한다."""
    try:
        ensure_chapter_completion_log_table()
        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT plan_id, chapter_number, completed
            FROM En_book_Plan_Chapters
            WHERE chapter_id = ?
            """,
            (chapter_id,),
        )
        row = cursor.fetchone()

        if row is None:
            conn.close()
            return jsonify({'success': False, 'error': '존재하지 않는 챕터입니다.'}), 404

        plan_id, chapter_number, completed_value = row
        is_completed = bool(completed_value)

        if is_completed:
            cursor.execute(
                "UPDATE En_book_Plan_Chapters SET completed = 0, completed_date = NULL WHERE chapter_id = ?",
                (chapter_id,)
            )
            cursor.execute(
                """
                UPDATE En_book_Chapter_Completion_Log
                SET cancelled_at = GETDATE(), cancelled_reason = 'toggle_off'
                WHERE chapter_id = ? AND plan_id = ? AND cancelled_at IS NULL
                """,
                (chapter_id, plan_id),
            )
            message = '챕터 완료가 취소되었습니다.'
            earned_points = 0
        else:
            cursor.execute(
                "UPDATE En_book_Plan_Chapters SET completed = 1, completed_date = GETDATE() WHERE chapter_id = ?",
                (chapter_id,)
            )
            earned_points = get_chapter_completion_points(chapter_number)
            cursor.execute(
                """
                INSERT INTO En_book_Chapter_Completion_Log (
                    plan_id, chapter_id, chapter_number, completed_at, earned_points, cancelled_at, cancelled_reason
                )
                VALUES (?, ?, ?, GETDATE(), ?, NULL, NULL)
                """,
                (plan_id, chapter_id, chapter_number, earned_points),
            )
            message = '챕터가 완료되었습니다.'

        conn.commit()
        conn.close()

        total_points = get_total_earned_points(plan_id)
        return jsonify({
            'success': True,
            'message': message,
            'completed': not is_completed,
            'earned_points': earned_points,
            'total_points': total_points,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/chapter-vocabulary/<int:chapter_id>', methods=['GET'])
def get_chapter_vocabulary(chapter_id):
    """특정 챕터의 보카 조회"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        query = """
        SELECT vocab_id, word, definition, example
        FROM En_book_Vocabulary
        WHERE chapter_id = ?
        ORDER BY vocab_id ASC
        """
        cursor.execute(query, (chapter_id,))
        vocabs = cursor.fetchall()
        conn.close()
        
        vocabulary = [
            {
                'vocab_id': vocab.vocab_id,
                'word': vocab.word,
                'definition': vocab.definition,
                'example': vocab.example
            }
            for vocab in vocabs
        ]
        
        return jsonify({'success': True, 'vocabulary': vocabulary})
    except Exception as e:
        print(f"Error fetching vocabulary: {e}")  # 디버깅용 로그
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/chapter-writing/<int:chapter_id>', methods=['GET'])
def get_chapter_writing(chapter_id):
    """특정 챕터의 라이팅 조회"""
    try:
        ensure_chapter_writing_table()
        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT summary_main, summary_scene, summary_thought, writing_text
            FROM En_book_Chapter_Writing
            WHERE chapter_id = ?
            """,
            (chapter_id,),
        )
        row = cursor.fetchone()
        conn.close()

        return jsonify({
            'success': True,
            'chapter_id': chapter_id,
            'summary_main': row.summary_main if row else '',
            'summary_scene': row.summary_scene if row else '',
            'summary_thought': row.summary_thought if row else '',
            'writing_text': row.writing_text if row else ''
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/chapter-writing/<int:chapter_id>', methods=['POST'])
def save_chapter_writing(chapter_id):
    """특정 챕터의 라이팅 저장"""
    try:
        ensure_chapter_writing_table()
        data = request.json or {}
        summary_main = (data.get('summary_main') or '').strip()
        summary_scene = (data.get('summary_scene') or '').strip()
        summary_thought = (data.get('summary_thought') or '').strip()
        writing_text = '\n'.join([part for part in [summary_main, summary_scene, summary_thought] if part])

        conn = get_db_conn()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT plan_id
            FROM En_book_Plan_Chapters
            WHERE chapter_id = ?
            """,
            (chapter_id,),
        )
        chapter_row = cursor.fetchone()

        if chapter_row is None:
            conn.close()
            return jsonify({'success': False, 'error': '존재하지 않는 챕터입니다.'}), 404

        plan_id = chapter_row.plan_id

        cursor.execute(
            """
            SELECT writing_id
            FROM En_book_Chapter_Writing
            WHERE chapter_id = ?
            """,
            (chapter_id,),
        )
        existing = cursor.fetchone()

        if existing:
            cursor.execute(
                """
                UPDATE En_book_Chapter_Writing
                SET summary_main = ?, summary_scene = ?, summary_thought = ?, writing_text = ?, updated_date = GETDATE()
                WHERE chapter_id = ?
                """,
                (summary_main, summary_scene, summary_thought, writing_text, chapter_id),
            )
        else:
            cursor.execute(
                """
                INSERT INTO En_book_Chapter_Writing (plan_id, chapter_id, summary_main, summary_scene, summary_thought, writing_text, created_date, updated_date)
                VALUES (?, ?, ?, ?, ?, ?, GETDATE(), GETDATE())
                """,
                (plan_id, chapter_id, summary_main, summary_scene, summary_thought, writing_text),
            )

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': '챕터 라이팅이 저장되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/add-vocabulary', methods=['POST'])
def add_vocabulary():
    """보카 추가"""
    try:
        data = request.json
        word = data.get('word')
        definition = data.get('definition')
        example = data.get('example', '')
        plan_id = data.get('plan_id')
        chapter_id = data.get('chapter_id')
        
        if not word or not definition:
            return jsonify({'success': False, 'error': '단어와 뜻은 필수입니다.'}), 400
        
        conn = get_db_conn()
        cursor = conn.cursor()

        if chapter_id is not None and chapter_id != '':
            chapter_id = int(chapter_id)
            if not plan_id:
                plan_id = resolve_plan_id_from_chapter_id(cursor, chapter_id)

        if chapter_id is not None and chapter_id != '':
            query = """
            INSERT INTO En_book_Vocabulary (word, definition, example, plan_id, chapter_id, created_date)
            VALUES (?, ?, ?, ?, ?, GETDATE())
            """
            cursor.execute(query, (word, definition, example, plan_id, chapter_id))
        else:
            query = """
            INSERT INTO En_book_Vocabulary (word, definition, example, plan_id, created_date)
            VALUES (?, ?, ?, ?, GETDATE())
            """
            cursor.execute(query, (word, definition, example, plan_id))
        conn.commit()
        
        # 방금 삽입한 ID 가져오기
        cursor.execute("SELECT IDENT_CURRENT('En_book_Vocabulary') as vocab_id")
        new_vocab_id = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True, 
            'vocab_id': new_vocab_id,
            'message': '단어가 추가되었습니다.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/preview-vocabulary-tsv', methods=['POST'])
def preview_vocabulary_tsv():
    """파싱 전 미리보기: TSV가 어떤 구조로 저장될지 확인"""
    try:
        data = request.json or {}
        raw_text = (data.get('tsv_text') or '').strip()

        if not raw_text:
            return jsonify({'success': False, 'error': 'TSV 데이터를 입력해주세요.'}), 400

        rows = []
        invalid_rows = []
        for line_number, line in enumerate(raw_text.splitlines(), start=1):
            clean_line = line.strip()
            if not clean_line:
                continue

            parsed = parse_vocab_tsv_line(clean_line)
            if parsed is None:
                invalid_rows.append({
                    'line': line_number,
                    'text': clean_line,
                    'reason': '형식이 올바르지 않습니다. word + 뜻 또는 word + 품사 + 뜻 형식이어야 합니다.'
                })
                continue
            rows.append(parsed)

        if not rows:
            return jsonify({
                'success': False,
                'error': '유효한 TSV 행이 없습니다.',
                'invalid_rows': invalid_rows
            }), 400

        return jsonify({
            'success': True,
            'rows': rows,
            'invalid_rows': invalid_rows,
            'message': f'{len(rows)}개의 단어를 저장할 수 있습니다.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/add-vocabulary-bulk', methods=['POST'])
def add_vocabulary_bulk():
    """TSV 형식의 단어 묶음 추가"""
    try:
        data = request.json or {}
        rows = data.get('rows', [])
        plan_id = data.get('plan_id')
        chapter_id = data.get('chapter_id')
        chapter_number = data.get('chapter_number')

        if not rows:
            return jsonify({'success': False, 'error': '추가할 단어가 없습니다.'}), 400

        conn = get_db_conn()
        cursor = conn.cursor()

        if not chapter_id and chapter_number not in (None, ''):
            cursor.execute(
                "SELECT chapter_id FROM En_book_Plan_Chapters WHERE plan_id = ? AND chapter_number = ?",
                (plan_id, int(chapter_number)),
            )
            chapter_row = cursor.fetchone()
            if chapter_row:
                chapter_id = chapter_row[0]

        if chapter_id not in (None, ''):
            chapter_id = int(chapter_id)
            if not plan_id:
                plan_id = resolve_plan_id_from_chapter_id(cursor, chapter_id)

        inserted = 0

        for row in rows:
            if not isinstance(row, dict):
                continue

            word = (row.get('word') or '').strip().replace('**', '')
            meaning = (row.get('meaning') or '').strip().replace('**', '')
            pos = (row.get('pos') or '').strip().replace('**', '')
            example = (row.get('example') or '').strip().replace('**', '')

            if not word or not meaning:
                continue

            definition = meaning if not pos else f"{pos} / {meaning}"

            if chapter_id not in (None, ''):
                cursor.execute(
                    """
                    INSERT INTO En_book_Vocabulary (word, definition, example, plan_id, chapter_id, created_date)
                    VALUES (?, ?, ?, ?, ?, GETDATE())
                    """,
                    (word, definition, example, plan_id, chapter_id),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO En_book_Vocabulary (word, definition, example, plan_id, created_date)
                    VALUES (?, ?, ?, ?, GETDATE())
                    """,
                    (word, definition, example, plan_id),
                )
            inserted += 1

        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'inserted': inserted,
            'message': f'{inserted}개의 단어가 추가되었습니다.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/admin')
def admin():
    """플랜 관리 페이지"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        has_cover_url = table_has_column('En_book_Plan', 'book_cover_url')

        # 모든 플랜 조회 (EN_book_list와 LEFT JOIN)
        query = """
        SELECT 
            p.plan_id,
            p.book_title,
            p.author,
            p.week_start,
            p.week_end,
            p.current_progress,
            p.total_chapters,
            p.created_date,
            """ + ('p.book_cover_url,' if has_cover_url else '') + """
            ch.start_chapter,
            ch.end_chapter,
            b.[AR (ATOS)],
            b.Point,
            b.Lexile
        FROM En_book_Plan p
        LEFT JOIN (
            SELECT
                plan_id,
                MIN(chapter_number) AS start_chapter,
                MAX(chapter_number) AS end_chapter
            FROM En_book_Plan_Chapters
            GROUP BY plan_id
        ) ch ON p.plan_id = ch.plan_id
        LEFT JOIN EN_book_list b ON p.book_title = b.책_제목
        ORDER BY p.week_start ASC, p.plan_id ASC
        """
        cursor.execute(query)
        plans = cursor.fetchall()
        conn.close()
        
        plans_data = []
        for plan in plans:
            plans_data.append({
                'plan_id': plan.plan_id,
                'book_title': plan.book_title,
                'author': plan.author,
                'week_start': plan.week_start,
                'week_end': plan.week_end,
                'current_progress': plan.current_progress,
                'total_chapters': plan.total_chapters,
                'start_chapter': getattr(plan, 'start_chapter', None),
                'end_chapter': getattr(plan, 'end_chapter', None),
                'created_date': plan.created_date,
                'book_cover_url': getattr(plan, 'book_cover_url', None),
                'atos': getattr(plan, 'AR (ATOS)', None),
                'ar_point': getattr(plan, 'Point', None),
                'lexile': getattr(plan, 'Lexile', None),
            })
        
        return render_template('admin.html', plans=plans_data)
    except Exception as e:
        print(f"Error: {e}")
        return render_template('admin.html', error=str(e), plans=[])

@app.route('/api/add-plan', methods=['POST'])
def add_plan():
    """새 읽기 계획 추가"""
    try:
        data = request.json
        book_title = data.get('book_title', '').strip()
        author = data.get('author', '').strip()
        week_start = data.get('week_start')
        week_end = data.get('week_end')
        total_chapters = data.get('total_chapters', 0)
        
        # 검증
        if not book_title or not author or not week_start or not week_end:
            return jsonify({'success': False, 'error': '필수 항목을 모두 입력해주세요.'}), 400
        
        if int(total_chapters) <= 0:
            return jsonify({'success': False, 'error': '챕터 수는 1 이상이어야 합니다.'}), 400
        
        conn = get_db_conn()
        cursor = conn.cursor()
        has_cover_url = table_has_column('En_book_Plan', 'book_cover_url')
        book_cover_url = request.json.get('book_cover_url', '').strip()

        if has_cover_url:
            query = """
            INSERT INTO En_book_Plan (book_title, author, week_start, week_end, total_chapters, current_progress, book_cover_url, created_date, updated_date)
            VALUES (?, ?, ?, ?, ?, 0, ?, GETDATE(), GETDATE())
            """
            params = (book_title, author, week_start, week_end, int(total_chapters), book_cover_url if book_cover_url else None)
        else:
            query = """
            INSERT INTO En_book_Plan (book_title, author, week_start, week_end, total_chapters, current_progress, created_date, updated_date)
            VALUES (?, ?, ?, ?, ?, 0, GETDATE(), GETDATE())
            """
            params = (book_title, author, week_start, week_end, int(total_chapters))

        cursor.execute(query, params)
        conn.commit()
        
        # 방금 삽입한 plan_id 가져오기
        cursor.execute("SELECT IDENT_CURRENT('En_book_Plan') as plan_id")
        new_plan_id = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'plan_id': new_plan_id,
            'message': '읽기 계획이 추가되었습니다.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/plan/<int:plan_id>')
def get_plan_detail(plan_id):
    """수정용 플랜 상세 조회"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        has_cover_url = table_has_column('En_book_Plan', 'book_cover_url')

        # EN_book_list와 LEFT JOIN해서 추가 정보 가져오기
        query = """
        SELECT 
            p.plan_id,
            p.book_title,
            p.author,
            p.week_start,
            p.week_end,
            p.total_chapters,
            p.current_progress,
            """ + ('p.book_cover_url,' if has_cover_url else '') + """
            b.[AR (ATOS)],
            b.Point,
            b.Lexile
        FROM En_book_Plan p
        LEFT JOIN EN_book_list b ON p.book_title = b.책_제목
        WHERE p.plan_id = ?
        """
        cursor.execute(query, (plan_id,))
        plan = cursor.fetchone()

        chapter_query = """
            SELECT chapter_id, chapter_number, page_start, page_end, completed
            FROM En_book_Plan_Chapters
            WHERE plan_id = ?
            ORDER BY chapter_number
        """
        cursor.execute(chapter_query, (plan_id,))
        chapters = cursor.fetchall()
        conn.close()

        if not plan:
            return jsonify({'success': False, 'error': '플랜을 찾을 수 없습니다.'}), 404

        plan_data = {
            'plan_id': plan.plan_id,
            'book_title': plan.book_title,
            'author': plan.author,
            'week_start': format_date_for_input(plan.week_start),
            'week_end': format_date_for_input(plan.week_end),
            'total_chapters': plan.total_chapters,
            'current_progress': plan.current_progress,
            'book_cover_url': getattr(plan, 'book_cover_url', None),
            'atos': getattr(plan, 'AR (ATOS)', None),
            'ar_point': getattr(plan, 'Point', None),
            'lexile': getattr(plan, 'Lexile', None),
            'chapters': [
                {
                    'chapter_id': chapter.chapter_id,
                    'chapter_number': chapter.chapter_number,
                    'page_start': chapter.page_start,
                    'page_end': chapter.page_end,
                    'completed': chapter.completed,
                }
                for chapter in chapters
            ]
        }

        return jsonify({'success': True, 'plan': plan_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/update-plan/<int:plan_id>', methods=['PUT'])
def update_plan(plan_id):
    """플랜 수정"""
    try:
        data = request.json or {}
        book_title = (data.get('book_title') or '').strip()
        author = (data.get('author') or '').strip()
        week_start = data.get('week_start')
        week_end = data.get('week_end')
        total_chapters = data.get('total_chapters', 0)
        book_cover_url = (data.get('book_cover_url') or '').strip()

        if not book_title or not author or not week_start or not week_end:
            return jsonify({'success': False, 'error': '필수 항목을 모두 입력해주세요.'}), 400

        if int(total_chapters) <= 0:
            return jsonify({'success': False, 'error': '챕터 수는 1 이상이어야 합니다.'}), 400

        conn = get_db_conn()
        cursor = conn.cursor()
        has_cover_url = table_has_column('En_book_Plan', 'book_cover_url')

        if has_cover_url:
            cursor.execute(
                """
                UPDATE En_book_Plan
                SET book_title = ?, author = ?, week_start = ?, week_end = ?, total_chapters = ?,
                    book_cover_url = ?, updated_date = GETDATE()
                WHERE plan_id = ?
                """,
                (book_title, author, week_start, week_end, int(total_chapters), book_cover_url if book_cover_url else None, plan_id),
            )
        else:
            cursor.execute(
                """
                UPDATE En_book_Plan
                SET book_title = ?, author = ?, week_start = ?, week_end = ?, total_chapters = ?, updated_date = GETDATE()
                WHERE plan_id = ?
                """,
                (book_title, author, week_start, week_end, int(total_chapters), plan_id),
            )

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'plan_id': plan_id, 'message': '읽기 계획이 수정되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/delete-plan/<int:plan_id>', methods=['DELETE'])
def delete_plan(plan_id):
    """읽기 계획 삭제"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        # 관련 챕터 및 보카 먼저 삭제 (ON DELETE CASCADE 때문에 자동)
        query = "DELETE FROM En_book_Plan WHERE plan_id = ?"
        cursor.execute(query, (plan_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': '읽기 계획이 삭제되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/add-chapters', methods=['POST'])
def add_chapters():
    """플랜에 챕터 추가"""
    try:
        data = request.json
        plan_id = data.get('plan_id')
        chapters = data.get('chapters', [])  # [{chapter_number, page_start, page_end}, ...]
        replace_existing = data.get('replace_existing', False)
        
        if not plan_id or not chapters:
            return jsonify({'success': False, 'error': '플랜 ID와 챕터 정보가 필요합니다.'}), 400
        
        conn = get_db_conn()
        cursor = conn.cursor()

        existing_by_number = {}
        if replace_existing:
            cursor.execute(
                """
                SELECT chapter_id, chapter_number
                FROM En_book_Plan_Chapters
                WHERE plan_id = ?
                """,
                (plan_id,),
            )
            existing_by_number = {row.chapter_number: row.chapter_id for row in cursor.fetchall()}

        incoming_numbers = set()
        for chapter in chapters:
            chapter_number = int(chapter['chapter_number'])
            page_start = int(chapter['page_start'])
            page_end = int(chapter['page_end'])
            incoming_numbers.add(chapter_number)

            existing_chapter_id = existing_by_number.get(chapter_number)
            if existing_chapter_id:
                cursor.execute(
                    """
                    UPDATE En_book_Plan_Chapters
                    SET page_start = ?, page_end = ?
                    WHERE chapter_id = ?
                    """,
                    (page_start, page_end, existing_chapter_id),
                )
                continue

            query = """
            INSERT INTO En_book_Plan_Chapters (plan_id, chapter_number, page_start, page_end, completed)
            VALUES (?, ?, ?, ?, 0)
            """
            cursor.execute(query, (plan_id, chapter_number, page_start, page_end))

        if replace_existing and existing_by_number:
            obsolete_numbers = [number for number in existing_by_number.keys() if number not in incoming_numbers]
            if obsolete_numbers:
                placeholders = ','.join(['?'] * len(obsolete_numbers))
                cursor.execute(
                    f"DELETE FROM En_book_Plan_Chapters WHERE plan_id = ? AND chapter_number IN ({placeholders})",
                    [plan_id, *obsolete_numbers],
                )
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'{len(chapters)}개의 챕터가 추가되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/points')
def points_dashboard():
    """포인트 관리 페이지"""
    try:
        ensure_chapter_completion_log_table()
        conn = get_db_conn()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT p.plan_id, p.book_title, p.author,
                   ISNULL(SUM(CASE WHEN l.cancelled_at IS NULL THEN l.earned_points ELSE 0 END), 0) AS total_points,
                   COUNT(CASE WHEN l.cancelled_at IS NULL THEN 1 END) AS completed_chapters,
                   MAX(l.completed_at) AS last_completed_at
            FROM En_book_Plan p
            LEFT JOIN En_book_Chapter_Completion_Log l ON p.plan_id = l.plan_id
            GROUP BY p.plan_id, p.book_title, p.author
            ORDER BY last_completed_at DESC, p.plan_id DESC
            """
        )
        plan_points = cursor.fetchall()

        cursor.execute(
            """
            SELECT l.plan_id, p.book_title, p.author, l.chapter_id, l.chapter_number,
                   l.completed_at, l.earned_points, l.cancelled_at, l.cancelled_reason
            FROM En_book_Chapter_Completion_Log l
            INNER JOIN En_book_Plan p ON p.plan_id = l.plan_id
            ORDER BY l.completed_at DESC, l.log_id DESC
            """
        )
        logs = cursor.fetchall()
        conn.close()

        point_rows = []
        for row in plan_points:
            point_rows.append({
                'plan_id': row[0],
                'book_title': row[1],
                'author': row[2],
                'total_points': int(row[3] or 0),
                'completed_chapters': int(row[4] or 0),
                'last_completed_at': row[5],
            })

        history = []
        for row in logs:
            history.append({
                'plan_id': row[0],
                'book_title': row[1],
                'author': row[2],
                'chapter_id': row[3],
                'chapter_number': row[4],
                'completed_at': row[5],
                'earned_points': int(row[6] or 0),
                'cancelled_at': row[7],
                'cancelled_reason': row[8],
            })

        overall_total = sum(item['total_points'] for item in point_rows)
        return render_template(
            'points.html',
            plan_points=point_rows,
            history=history,
            overall_total=overall_total,
            total_plans=len(point_rows),
        )
    except Exception as e:
        print(f"Error loading points dashboard: {e}")
        return render_template(
            'points.html',
            plan_points=[],
            history=[],
            overall_total=0,
            total_plans=0,
            error=str(e),
        )


# ===== 책장 관리 (My Bookshelf) =====

@app.route('/bookshelf')
def bookshelf():
    """책장 관리 페이지"""
    return render_template('bookshelf.html')


@app.route('/api/books', methods=['GET'])
def get_books():
    """모든 책 조회"""
    try:
        ensure_en_book_list_image_url_column()
        conn = get_db_conn()
        cursor = conn.cursor()
        
        # 모든 책을 조회 (제한 없음)
        query = """
        SELECT * FROM EN_book_list ORDER BY 책_제목
        """
        cursor.execute(query)
        books = cursor.fetchall()
        conn.close()
        
        if not books:
            return jsonify({'success': True, 'books': []})
        
        books_data = []
        for book in books:
            # 컬럼 이름들을 동적으로 가져오기
            columns = [desc[0] for desc in cursor.description]
            
            book_dict = {col: book[i] for i, col in enumerate(columns)}
            
            books_data.append({
                'id': book_dict.get('id'),
                'book_title': book_dict.get('책_제목'),
                'subtitle': get_first_value(book_dict, ['작은_제목']),
                'author': book_dict.get('저자'),
                'series': get_first_value(book_dict, ['시리즈명', '시리즈']),
                'type': book_dict.get('F_NF'),
                'atos': get_first_value(book_dict, ['AR (ATOS)', 'AR']),
                'point': book_dict.get('Point'),
                'category': get_first_value(book_dict, ['관심수제', '관심주제']),
                'priority': book_dict.get('우선'),
                'isbn': book_dict.get('ISBN'),
                'book_image_url': book_dict.get('book_image_url'),
                'viewed_date': format_date_for_display(book_dict.get('조회일시')) if book_dict.get('조회일시') else None,
                'ar_points': get_first_value(book_dict, ['AR인증점']),
                'lexile': book_dict.get('Lexile')
            })
        
        return jsonify({'success': True, 'books': books_data})
    except Exception as e:
        print(f"Error in get_books: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/add-book', methods=['POST'])
def add_book():
    """새 책 추가"""
    try:
        data = request.json or {}
        book_title = (data.get('book_title') or '').strip()
        
        if not book_title:
            return jsonify({'success': False, 'error': '책 제목은 필수입니다.'}), 400

        ensure_en_book_list_image_url_column()
        existing_columns = get_table_columns('EN_book_list')

        title_col = resolve_existing_column(existing_columns, ['책_제목'])
        if not title_col:
            return jsonify({'success': False, 'error': 'EN_book_list에 책 제목 컬럼(책_제목)이 없습니다.'}), 400

        field_candidates = [
            ('subtitle', ['작은_제목']),
            ('author', ['저자']),
            ('series', ['시리즈명', '시리즈']),
            ('type', ['F_NF']),
            ('atos', ['AR (ATOS)', 'AR']),
            ('point', ['Point']),
            ('category', ['관심수제', '관심주제']),
            ('priority', ['우선']),
            ('isbn', ['ISBN']),
            ('book_image_url', ['book_image_url']),
            ('ar_points', ['AR인증점']),
            ('lexile', ['Lexile']),
        ]

        column_values = {
            'subtitle': (data.get('subtitle') or '').strip(),
            'author': (data.get('author') or '').strip(),
            'series': (data.get('series') or '').strip(),
            'type': (data.get('type') or '').strip(),
            'atos': (data.get('atos') or '').strip(),
            'point': data.get('point', None),
            'category': (data.get('category') or '').strip(),
            'priority': (data.get('priority') or '').strip(),
            'isbn': (data.get('isbn') or '').strip(),
            'book_image_url': (data.get('book_image_url') or '').strip(),
            'ar_points': data.get('ar_points', None),
            'lexile': (data.get('lexile') or '').strip(),
        }
        
        conn = get_db_conn()
        cursor = conn.cursor()

        insert_columns = [quote_sql_column(title_col)]
        insert_values_sql = ['?']
        params = [book_title]

        for logical_name, candidates in field_candidates:
            existing_col = resolve_existing_column(existing_columns, candidates)
            if not existing_col:
                continue
            insert_columns.append(quote_sql_column(existing_col))
            insert_values_sql.append('?')
            params.append(column_values[logical_name])

        viewed_date_col = resolve_existing_column(existing_columns, ['조회일시'])
        if viewed_date_col:
            insert_columns.append(quote_sql_column(viewed_date_col))
            insert_values_sql.append('GETDATE()')

        query = f"INSERT INTO EN_book_list ({', '.join(insert_columns)}) VALUES ({', '.join(insert_values_sql)})"
        
        cursor.execute(query, params)
        conn.commit()
        
        cursor.execute("SELECT IDENT_CURRENT('EN_book_list') as id")
        new_id = cursor.fetchone()[0]
        conn.close()
        
        return jsonify({'success': True, 'id': new_id, 'message': '책이 추가되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/update-book/<int:book_id>', methods=['PUT'])
def update_book(book_id):
    """책 정보 수정"""
    try:
        data = request.json or {}
        book_title = (data.get('book_title') or '').strip()
        
        if not book_title:
            return jsonify({'success': False, 'error': '책 제목은 필수입니다.'}), 400

        ensure_en_book_list_image_url_column()
        existing_columns = get_table_columns('EN_book_list')

        title_col = resolve_existing_column(existing_columns, ['책_제목'])
        if not title_col:
            return jsonify({'success': False, 'error': 'EN_book_list에 책 제목 컬럼(책_제목)이 없습니다.'}), 400

        field_candidates = [
            ('subtitle', ['작은_제목']),
            ('author', ['저자']),
            ('series', ['시리즈명', '시리즈']),
            ('type', ['F_NF']),
            ('atos', ['AR (ATOS)', 'AR']),
            ('point', ['Point']),
            ('category', ['관심수제', '관심주제']),
            ('priority', ['우선']),
            ('isbn', ['ISBN']),
            ('book_image_url', ['book_image_url']),
            ('ar_points', ['AR인증점']),
            ('lexile', ['Lexile']),
        ]

        column_values = {
            'subtitle': (data.get('subtitle') or '').strip(),
            'author': (data.get('author') or '').strip(),
            'series': (data.get('series') or '').strip(),
            'type': (data.get('type') or '').strip(),
            'atos': (data.get('atos') or '').strip(),
            'point': data.get('point', None),
            'category': (data.get('category') or '').strip(),
            'priority': (data.get('priority') or '').strip(),
            'isbn': (data.get('isbn') or '').strip(),
            'book_image_url': (data.get('book_image_url') or '').strip(),
            'ar_points': data.get('ar_points', None),
            'lexile': (data.get('lexile') or '').strip(),
        }
        
        conn = get_db_conn()
        cursor = conn.cursor()

        set_clauses = [f"{quote_sql_column(title_col)} = ?"]
        params = [book_title]

        for logical_name, candidates in field_candidates:
            existing_col = resolve_existing_column(existing_columns, candidates)
            if not existing_col:
                continue
            set_clauses.append(f"{quote_sql_column(existing_col)} = ?")
            params.append(column_values[logical_name])

        query = f"UPDATE EN_book_list SET {', '.join(set_clauses)} WHERE id = ?"
        params.append(book_id)
        
        cursor.execute(query, params)
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': '책 정보가 수정되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/update-books-bulk', methods=['PUT'])
def update_books_bulk():
    """책 정보 일괄 수정"""
    try:
        data = request.json or {}
        books = data.get('books', [])

        if not isinstance(books, list) or not books:
            return jsonify({'success': False, 'error': '수정할 책 데이터가 없습니다.'}), 400

        ensure_en_book_list_image_url_column()
        existing_columns = get_table_columns('EN_book_list')

        title_col = resolve_existing_column(existing_columns, ['책_제목'])
        if not title_col:
            return jsonify({'success': False, 'error': 'EN_book_list에 책 제목 컬럼(책_제목)이 없습니다.'}), 400

        field_candidates = [
            ('author', ['저자']),
            ('series', ['시리즈명', '시리즈']),
            ('type', ['F_NF']),
            ('atos', ['AR (ATOS)', 'AR']),
            ('point', ['Point']),
            ('category', ['관심수제', '관심주제']),
            ('isbn', ['ISBN']),
            ('book_image_url', ['book_image_url']),
            ('lexile', ['Lexile']),
        ]

        conn = get_db_conn()
        cursor = conn.cursor()

        updated_count = 0

        try:
            for item in books:
                book_id = item.get('id')
                if book_id is None:
                    raise ValueError('id가 없는 항목이 포함되어 있습니다.')

                book_title = (item.get('book_title') or '').strip()
                if not book_title:
                    raise ValueError(f'id {book_id}: 책 제목은 필수입니다.')

                set_clauses = [f"{quote_sql_column(title_col)} = ?"]
                params = [book_title]

                for logical_name, candidates in field_candidates:
                    if logical_name not in item:
                        continue
                    existing_col = resolve_existing_column(existing_columns, candidates)
                    if not existing_col:
                        continue

                    value = item.get(logical_name)
                    if isinstance(value, str):
                        value = value.strip()
                    if logical_name == 'point':
                        if value in ('', None):
                            value = None
                        else:
                            value = int(value)

                    set_clauses.append(f"{quote_sql_column(existing_col)} = ?")
                    params.append(value)

                query = f"UPDATE EN_book_list SET {', '.join(set_clauses)} WHERE id = ?"
                params.append(int(book_id))
                cursor.execute(query, params)
                updated_count += 1

            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

        return jsonify({'success': True, 'updated': updated_count, 'message': f'{updated_count}권이 저장되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/delete-book/<int:book_id>', methods=['DELETE'])
def delete_book(book_id):
    """책 삭제"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM EN_book_list WHERE id = ?", (book_id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': '책이 삭제되었습니다.'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/fix-chapter-vocab-mapping/<int:plan_id>', methods=['POST'])
def fix_chapter_vocab_mapping(plan_id):
    """임시: 보카 chapter_id 매핑 수정 (53→58, 54→59, 55→60, 56→61, 57→62)"""
    try:
        mapping = {
            53: 58,
            54: 59,
            55: 60,
            56: 61,
            57: 62,
        }
        
        conn = get_db_conn()
        cursor = conn.cursor()
        
        updated_count = 0
        for old_chapter_id, new_chapter_id in mapping.items():
            cursor.execute(
                "UPDATE En_book_Vocabulary SET chapter_id = ? WHERE plan_id = ? AND chapter_id = ?",
                (new_chapter_id, plan_id, old_chapter_id)
            )
            updated_count += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True, 
            'updated': updated_count,
            'message': f'✓ {updated_count}개 단어의 chapter_id가 수정되었습니다.'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


if __name__ == '__main__':
    app.run(
        debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true',
        host='0.0.0.0',
        port=int(os.getenv('PORT', '5003')),
    )
