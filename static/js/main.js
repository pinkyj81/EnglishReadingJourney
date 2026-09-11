// My Reading Journey - Main JavaScript

let currentWritingChapterId = null;
let currentVocabChapterId = null;
let currentVocabPlanId = null;
let currentVocabChapterNumber = null;

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function splitLegacyChapterWritingText(text) {
    const raw = (text || '').trim();
    if (!raw) {
        return { main: '', scene: '', thought: '' };
    }

    const lines = raw.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    return {
        main: lines[0] || raw,
        scene: lines[1] || '',
        thought: lines[2] || ''
    };
}

function updateProgressUI() {
    const progressText = document.querySelector('.progress-text');
    const progressBar = document.querySelector('.progress-bar');
    if (!progressText || !progressBar) {
        return;
    }

    const totalPart = progressText.textContent.split('/')[1];
    const total = Number((totalPart || '0').trim());
    if (!total) {
        progressText.textContent = '0 / 0';
        progressBar.style.width = '0%';
        return;
    }

    const completed = document.querySelectorAll('.chapter-item.completed').length;
    progressText.textContent = `${completed} / ${total}`;
    progressBar.style.width = `${(completed / total) * 100}%`;
}

// 보카 모달 열기
async function openVocabModal(chapterId, chapterNumber) {
    try {
        currentVocabChapterId = chapterId;
        currentVocabChapterNumber = chapterNumber;
        currentVocabPlanId = document.getElementById('selected_plan_id')?.value || '';
        const modal = document.getElementById('vocabModal');
        const overlay = document.getElementById('vocabModalOverlay');
        const title = document.getElementById('modalChapterTitle');
        const vocabList = document.getElementById('modalVocabList');
        const vocabEmpty = document.getElementById('modalVocabEmpty');
        const addFormWrap = document.getElementById('vocabAddFormWrap');
        const selectedChapterInput = document.getElementById('selected_chapter_id');
        const selectedPlanInput = document.getElementById('selected_plan_id');

        title.textContent = `Chapter ${chapterNumber} - Vocabulary`;
        if (selectedChapterInput) {
            selectedChapterInput.value = String(chapterId);
        }
        if (selectedPlanInput && currentVocabPlanId) {
            selectedPlanInput.value = String(currentVocabPlanId);
        }
        if (addFormWrap) {
            addFormWrap.style.display = 'none';
        }

        // API에서 해당 챕터의 보카 조회
        const response = await fetch(`/api/chapter-vocabulary/${chapterId}`);
        
        if (!response.ok) {
            throw new Error('보카를 불러올 수 없습니다.');
        }

        const result = await response.json();
        const vocabs = result.vocabulary || [];

        // 보카 리스트 렌더링
        if (vocabs.length === 0) {
            vocabList.style.display = 'none';
            vocabEmpty.style.display = 'block';
        } else {
            vocabList.style.display = 'block';
            vocabEmpty.style.display = 'none';

            vocabList.innerHTML = vocabs.map((vocab, idx) => {
                const word = escapeHtml(vocab.word || '');
                const definition = escapeHtml(vocab.definition || '');
                const example = escapeHtml(vocab.example || '');
                return `
                    <div class="vocab-item">
                        <div class="modal-vocab-line">
                            <button type="button" class="vocab-word-button" data-word="${word}" aria-label="${word} 발음 듣기">
                                <span class="vocab-index">${idx + 1}.</span>
                                <span class="vocab-word-text">${word}</span>
                                <i class="bi bi-volume-up speaker-icon" aria-hidden="true"></i>
                            </button>
                            <div class="modal-vocab-definition">${definition}</div>
                        </div>
                        ${example ? `<div class="vocab-example">${example}</div>` : ''}
                    </div>
                `;
            }).join('');

            vocabList.querySelectorAll('.vocab-word-button').forEach((button) => {
                button.addEventListener('click', () => {
                    speakWord(button.dataset.word);
                });
            });
        }

        // 모달 표시
        modal.style.display = 'block';
        overlay.style.display = 'block';
    } catch (error) {
        console.error('Error:', error);
        alert('보카를 불러올 수 없습니다.');
    }
}

// 보카 모달 닫기
function closeVocabModal() {
    const modal = document.getElementById('vocabModal');
    const overlay = document.getElementById('vocabModalOverlay');
    const addFormWrap = document.getElementById('vocabAddFormWrap');
    modal.style.display = 'none';
    overlay.style.display = 'none';
    if (addFormWrap) {
        addFormWrap.style.display = 'none';
    }
}

function toggleVocabAddForm() {
    const wrap = document.getElementById('vocabAddFormWrap');
    if (!wrap) return;
    wrap.style.display = wrap.style.display === 'none' ? 'block' : 'none';
    if (wrap.style.display === 'block') {
        document.getElementById('vocab_word')?.focus();
    }
}

function closeVocabAddForm() {
    const wrap = document.getElementById('vocabAddFormWrap');
    if (wrap) {
        wrap.style.display = 'none';
    }
}

function printVocabularyList() {
    closeVocabAddForm();
    window.print();
}

// 챕터 완료 토글
async function toggleChapterComplete(chapterId) {
    try {
        const response = await fetch(`/api/mark-chapter-complete/${chapterId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const error = await response.json();
            alert('오류: ' + error.error);
            return;
        }

        const result = await response.json();
        
        // UI 업데이트
        const chapterElement = document.querySelector(`[data-chapter-id="${chapterId}"]`);
        if (chapterElement) {
            chapterElement.classList.toggle('completed', !!result.completed);
            const icon = chapterElement.querySelector('.btn-chapter-action i');
            if (icon) {
                icon.className = result.completed ? 'bi bi-check-square-fill' : 'bi bi-square';
            }
            updateProgressUI();
        }

        alert(result.message);
    } catch (error) {
        console.error('Error:', error);
        alert('챕터 완료 표시에 실패했습니다.');
    }
}

async function openChapterWritingModal(chapterId, chapterNumber) {
    try {
        currentWritingChapterId = chapterId;
        const modal = document.getElementById('chapterWritingModal');
        const overlay = document.getElementById('chapterWritingModalOverlay');
        const title = document.getElementById('chapterWritingModalTitle');
        const mainInput = document.getElementById('chapterWritingMain');
        const sceneInput = document.getElementById('chapterWritingScene');
        const thoughtInput = document.getElementById('chapterWritingThought');

        if (title) {
            title.textContent = `Chapter ${chapterNumber} 라이팅`;
        }
        if (mainInput) mainInput.value = '';
        if (sceneInput) sceneInput.value = '';
        if (thoughtInput) thoughtInput.value = '';

        const response = await fetch(`/api/chapter-writing/${chapterId}`);
        const result = await response.json();
        if (!response.ok || !result.success) {
            throw new Error(result.error || '라이팅을 불러오지 못했습니다.');
        }

        const hasStructured = result.summary_main || result.summary_scene || result.summary_thought;
        if (hasStructured) {
            if (mainInput) mainInput.value = result.summary_main || '';
            if (sceneInput) sceneInput.value = result.summary_scene || '';
            if (thoughtInput) thoughtInput.value = result.summary_thought || '';
        } else {
            const legacy = splitLegacyChapterWritingText(result.writing_text || '');
            if (mainInput) mainInput.value = legacy.main;
            if (sceneInput) sceneInput.value = legacy.scene;
            if (thoughtInput) thoughtInput.value = legacy.thought;
        }

        if (modal) {
            modal.style.display = 'block';
        }
        if (overlay) {
            overlay.style.display = 'block';
        }
    } catch (error) {
        console.error('Error:', error);
        alert('챕터 라이팅을 불러오지 못했습니다.');
    }
}

function closeChapterWritingModal() {
    const modal = document.getElementById('chapterWritingModal');
    const overlay = document.getElementById('chapterWritingModalOverlay');
    if (modal) {
        modal.style.display = 'none';
    }
    if (overlay) {
        overlay.style.display = 'none';
    }
}

async function saveChapterWriting() {
    if (!currentWritingChapterId) {
        alert('챕터를 먼저 선택해주세요.');
        return;
    }

    const mainInput = document.getElementById('chapterWritingMain');
    const sceneInput = document.getElementById('chapterWritingScene');
    const thoughtInput = document.getElementById('chapterWritingThought');

    const summaryMain = mainInput ? mainInput.value.trim() : '';
    const summaryScene = sceneInput ? sceneInput.value.trim() : '';
    const summaryThought = thoughtInput ? thoughtInput.value.trim() : '';

    if (!summaryMain && !summaryScene && !summaryThought) {
        alert('최소 하나 이상의 내용을 작성해주세요.');
        return;
    }

    try {
        const response = await fetch(`/api/chapter-writing/${currentWritingChapterId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                summary_main: summaryMain,
                summary_scene: summaryScene,
                summary_thought: summaryThought
            })
        });

        const result = await response.json();
        if (!response.ok || !result.success) {
            alert('오류: ' + (result.error || '저장 실패'));
            return;
        }

        alert(result.message);
        closeChapterWritingModal();
    } catch (error) {
        console.error('Error:', error);
        alert('챕터 라이팅 저장에 실패했습니다.');
    }
}

// 보카 추가
async function addVocabulary(event) {
    event.preventDefault();

    const word = document.getElementById('vocab_word').value.trim();
    const definition = document.getElementById('vocab_definition').value.trim();
    const example = document.getElementById('vocab_example').value.trim();
    const selectedChapterId = document.getElementById('selected_chapter_id')?.value || currentVocabChapterId || '';
    const planId = document.getElementById('selected_plan_id')?.value || currentVocabPlanId || '';

    if (!word || !definition) {
        alert('단어와 뜻은 필수입니다.');
        return;
    }

    try {
        const response = await fetch('/api/add-vocabulary', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                word: word,
                definition: definition,
                example: example || null,
                chapter_id: selectedChapterId || null,
                plan_id: planId || null
            })
        });

        if (!response.ok) {
            const error = await response.json();
            alert('오류: ' + error.error);
            return;
        }

        const result = await response.json();
        alert(result.message);
        
        // 폼 초기화
        document.getElementById('vocab_word').value = '';
        document.getElementById('vocab_definition').value = '';
        document.getElementById('vocab_example').value = '';
        closeVocabAddForm();
        if (currentVocabChapterId && currentVocabChapterNumber) {
            await openVocabModal(currentVocabChapterId, currentVocabChapterNumber);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('단어 추가에 실패했습니다.');
    }
}

function parseTsvRows(rawText) {
    return rawText
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(line => line.length > 0)
        .map(line => {
            const cells = line.split('\t').map(cell => cell.trim());
            if (cells.length >= 3) {
                const [word, pos, meaning, ...rest] = cells;
                return {
                    word,
                    pos,
                    meaning,
                    example: rest.join(' ') || ''
                };
            }
            if (cells.length === 2) {
                const [word, meaning] = cells;
                return { word, pos: '', meaning };
            }
            return null;
        })
        .filter(Boolean);
}

async function addVocabularyFromTsv(event) {
    event.preventDefault();

    const rawText = document.getElementById('vocab_tsv_input')?.value || '';
    const selectedChapterId = document.getElementById('selected_chapter_id')?.value || '';
    const planId = document.getElementById('selected_plan_id')?.value || '';
    const rows = parseTsvRows(rawText);

    if (!rows.length) {
        alert('저장할 TSV 데이터를 입력해주세요.');
        return;
    }

    try {
        const response = await fetch('/api/add-vocabulary-bulk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                rows: rows,
                chapter_id: selectedChapterId || null,
                plan_id: planId || null
            })
        });

        const result = await response.json();
        if (!response.ok) {
            alert('오류: ' + result.error);
            return;
        }

        alert(result.message);
        document.getElementById('vocab_tsv_input').value = '';
        location.reload();
    } catch (error) {
        console.error('Error:', error);
        alert('TSV 단어 저장에 실패했습니다.');
    }
}

// 서머리 라이팅 제출
function submitSummaryWriting() {
    const summaryMain = document.querySelector('[name="summary_main"]')?.value.trim();
    const summaryScene = document.querySelector('[name="summary_scene"]')?.value.trim();
    const summaryThought = document.querySelector('[name="summary_thought"]')?.value.trim();

    // 입력 값 검증
    if (!summaryMain && !summaryScene && !summaryThought) {
        alert('최소 하나 이상의 내용을 작성해주세요.');
        return;
    }

    // 저장 로직 (현재는 alert만 표시)
    alert(`✅ 서머리가 저장되었습니다!\n\n1. ${summaryMain || '(미입력)'}\n2. ${summaryScene || '(미입력)'}\n3. ${summaryThought || '(미입력)'}`);
}

// 스피커 아이콘 클릭 - 단어 발음
function speakWord(word) {
    if (!word) {
        return;
    }

    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(word);
        utterance.lang = 'en-US';
        utterance.rate = 0.9;
        utterance.pitch = 1;
        window.speechSynthesis.speak(utterance);
    } else {
        alert('이 브라우저에서는 음성 재생을 지원하지 않습니다.');
    }
}

// DOM 로드 완료 후 이벤트 리스너 설정
document.addEventListener('DOMContentLoaded', function() {
    const chapterItems = document.querySelectorAll('.chapter-item');
    const vocabTableRows = document.querySelectorAll('.vocab-table-row');
    const emptyState = document.getElementById('vocab-empty-state');
    const selectedChapterInput = document.getElementById('selected_chapter_id');

    function updateSelectedChapter(chapterId) {
        const chapterIdNum = Number(chapterId);

        chapterItems.forEach(item => {
            const isActive = Number(item.dataset.chapterId) === chapterIdNum;
            item.classList.toggle('active', isActive);
        });

        let visibleCount = 0;
        vocabTableRows.forEach(row => {
            const rowChapterId = Number(row.dataset.chapterId);
            const isVisible = rowChapterId === chapterIdNum;
            row.style.display = isVisible ? 'table-row' : 'none';
            if (isVisible) visibleCount += 1;
        });

        if (emptyState) {
            emptyState.style.display = visibleCount === 0 ? 'block' : 'none';
        }

        if (selectedChapterInput) {
            selectedChapterInput.value = chapterIdNum || '';
        }
    }

    chapterItems.forEach(item => {
        item.addEventListener('click', function() {
            updateSelectedChapter(this.dataset.chapterId);
        });
    });

    const initialChapterId = selectedChapterInput && selectedChapterInput.value
        ? Number(selectedChapterInput.value)
        : (chapterItems.length ? Number(chapterItems[0].dataset.chapterId) : null);

    if (initialChapterId) {
        updateSelectedChapter(initialChapterId);
    }

    // Collapse 토글 기능
    const sectionHeaders = document.querySelectorAll('.section-header');
    sectionHeaders.forEach(header => {
        const parent = header.closest('.card');
        if (parent && parent.classList.contains('vocabulary-section')) {
            header.addEventListener('click', function() {
                const content = parent.querySelector('.vocabulary-content');
                if (content) {
                    content.style.display = content.style.display === 'none' ? 'block' : 'none';
                    const icon = this.querySelector('.collapse-icon');
                    if (icon) {
                        icon.textContent = content.style.display === 'none' ? '←' : '→';
                    }
                }
            });
        }
    });
});

// Strftime 필터 구현 (Flask에서 템플릿 필터 사용)
// 이 부분은 Flask 백엔드에서 처리됩니다.
