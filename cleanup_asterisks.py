#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Chapter 9, 10의 vocabulary에서 ** 기호를 제거하는 클린업 스크립트
"""

import os
import pyodbc
from dotenv import load_dotenv

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

def cleanup_asterisks():
    """모든 vocabulary에서 ** 제거"""
    try:
        conn = get_db_conn()
        cursor = conn.cursor()
        
        # 먼저 ** 를 포함하는 모든 데이터를 확인
        print("Checking vocabulary with ** symbols in entire database...")
        cursor.execute("""
            SELECT vocab_id, word, definition, example, chapter_id, plan_id
            FROM En_book_Vocabulary
            WHERE (word LIKE '%**%' OR definition LIKE '%**%' OR example LIKE '%**%')
            ORDER BY plan_id, chapter_id, vocab_id
        """)
        
        rows = cursor.fetchall()
        
        if not rows:
            print("No vocabulary with ** symbols found in entire database")
            cursor.close()
            conn.close()
            return 0
        
        print(f"\nFound {len(rows)} records with ** symbols:")
        for row in rows:
            vocab_id, word, definition, example, chapter_id, plan_id = row
            print(f"  Plan {plan_id}, Chapter {chapter_id}, ID {vocab_id}: '{word}' -> '{definition}'")
        
        # ** 제거
        print("\nRemoving ** symbols...")
        
        update_count = 0
        for row in rows:
            vocab_id = row[0]
            word = row[1]
            definition = row[2]
            example = row[3]
            
            # ** 제거
            word_clean = word.replace('**', '') if word else word
            definition_clean = definition.replace('**', '') if definition else definition
            example_clean = example.replace('**', '') if example else example
            
            # 변경이 있는 경우만 업데이트
            if word_clean != word or definition_clean != definition or example_clean != example:
                cursor.execute("""
                    UPDATE En_book_Vocabulary
                    SET word = ?, definition = ?, example = ?
                    WHERE vocab_id = ?
                """, (word_clean, definition_clean, example_clean, vocab_id))
                update_count += 1
                print(f"  Updated ID {vocab_id}: '{word}' -> '{word_clean}'")
        
        conn.commit()
        print(f"\n✓ Successfully cleaned {update_count} records")
        
        cursor.close()
        conn.close()
        
        return update_count
        
    except Exception as e:
        print(f"Error: {e}")
        return -1

if __name__ == '__main__':
    result = cleanup_asterisks()
    if result >= 0:
        print(f"\nCleanup completed: {result} records updated")
    else:
        print("Cleanup failed")
