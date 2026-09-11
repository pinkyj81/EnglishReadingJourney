#!/usr/bin/env python3
"""
현재 active plan의 chapter 1 보카 확인
"""
import os
import sys
import pyodbc
from dotenv import load_dotenv
from datetime import datetime, date

load_dotenv()

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

try:
    conn = get_db_conn()
    cursor = conn.cursor()
    
    # 현재 active plan 조회
    today = date.today()
    print(f"Today: {today}")
    
    query = """
    SELECT TOP 1 plan_id, book_title, author, week_start, week_end
    FROM En_book_Plan
    WHERE CAST(week_start AS DATE) <= CAST(GETDATE() AS DATE)
      AND CAST(week_end AS DATE) >= CAST(GETDATE() AS DATE)
    ORDER BY plan_id DESC
    """
    
    cursor.execute(query)
    plan = cursor.fetchone()
    
    if not plan:
        print("❌ No active plan found for today")
        sys.exit(1)
    
    plan_id = plan.plan_id
    print(f"\n✅ Active Plan Found:")
    print(f"   Plan ID: {plan_id}")
    print(f"   Title: {plan.book_title}")
    print(f"   Author: {plan.author}")
    print(f"   Week: {plan.week_start} ~ {plan.week_end}")
    
    # Chapter 1 조회
    chapter_query = """
    SELECT chapter_id, chapter_number, page_start, page_end
    FROM En_book_Plan_Chapters
    WHERE plan_id = ? AND chapter_number = 1
    """
    
    cursor.execute(chapter_query, (plan_id,))
    chapter = cursor.fetchone()
    
    if not chapter:
        print(f"\n❌ Chapter 1 not found for plan {plan_id}")
        sys.exit(1)
    
    chapter_id = chapter.chapter_id
    print(f"\n✅ Chapter 1 Found:")
    print(f"   Chapter ID: {chapter_id}")
    print(f"   Pages: {chapter.page_start} - {chapter.page_end}")
    
    # Chapter 1의 보카 조회
    vocab_query = """
    SELECT vocab_id, word, pos, definition, example, created_date
    FROM En_book_Vocabulary
    WHERE plan_id = ? AND chapter_id = ?
    ORDER BY created_date DESC
    """
    
    cursor.execute(vocab_query, (plan_id, chapter_id))
    vocabs = cursor.fetchall()
    
    if not vocabs:
        print(f"\n❌ No vocabulary found for Chapter 1")
        print(f"   (plan_id={plan_id}, chapter_id={chapter_id})")
    else:
        print(f"\n✅ {len(vocabs)} vocabulary items found in Chapter 1:")
        for vocab in vocabs:
            print(f"   - {vocab.word} ({vocab.pos}): {vocab.definition}")
            if vocab.example:
                print(f"     Example: {vocab.example}")
    
    conn.close()

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
