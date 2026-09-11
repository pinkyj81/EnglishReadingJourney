// Admin Page JavaScript

let currentPlanId = null;
let chapterCount = 0;
let parsedVocabRows = [];
let isEditMode = false;
let currentVocabPlanId = null;
let currentVocabChapterNumber = null;
let bookshelfBooks = [];

async function loadBookshelfBooksForAutocomplete() {
    try {
        const response = await fetch('/api/books');
        const result = await response.json();
        if (!response.ok || !result.success) {
            return;
        }

        bookshelfBooks = result.books || [];
        populateBookshelfDatalists();
    } catch (error) {
        console.error('Error loading bookshelf books:', error);
    }
}

function populateBookshelfDatalists() {
    const titleList = document.getElementById('bookshelfTitleOptions');
    const authorList = document.getElementById('bookshelfAuthorOptions');
    if (!titleList || !authorList) {
        return;
    }

    const uniqueTitles = [...new Set(bookshelfBooks.map(book => (book.book_title || '').trim()).filter(Boolean))].sort();
    const uniqueAuthors = [...new Set(bookshelfBooks.map(book => (book.author || '').trim()).filter(Boolean))].sort();

    titleList.innerHTML = uniqueTitles.map(title => `<option value="${title}"></option>`).join('');
    authorList.innerHTML = uniqueAuthors.map(author => `<option value="${author}"></option>`).join('');
}

function autoFillBookMetaFromTitle() {
    const titleInput = document.getElementById('book_title');
    const authorInput = document.getElementById('author');
    const coverInput = document.getElementById('book_cover_url');
    if (!titleInput || !authorInput) {
        return;
    }

    const enteredTitle = (titleInput.value || '').trim().toLowerCase();
    if (!enteredTitle) {
        return;
    }

    const selectedBook = bookshelfBooks.find(book => (book.book_title || '').trim().toLowerCase() === enteredTitle);
    if (!selectedBook) {
        return;
    }

    if (selectedBook.author) {
        authorInput.value = selectedBook.author;
    }

    if (coverInput && !coverInput.value && selectedBook.book_image_url) {
        coverInput.value = selectedBook.book_image_url;
    }
}

function syncModalOpenState() {
    const hasActiveModal = document.querySelector('#planModal.active, #vocabModal.active, #alertModal.active') !== null;
    document.body.classList.toggle('modal-open', hasActiveModal);
}

function closeAllModals() {
    document.getElementById('planModal')?.classList.remove('active');
    document.getElementById('vocabModal')?.classList.remove('active');
    document.getElementById('alertModal')?.classList.remove('active');
    syncModalOpenState();
}

function openPlanModal() {
    closeAllModals();
    const modal = document.getElementById('planModal');
    if (!modal) return;
    modal.classList.add('active');

    const modalBody = modal.querySelector('.plan-modal-body');
    if (modalBody) {
        modalBody.scrollTop = 0;
    }

    const modalContent = modal.querySelector('.modal-content');
    if (modalContent) {
        modalContent.scrollTop = 0;
    }

    syncModalOpenState();
}

function closePlanModal() {
    const modal = document.getElementById('planModal');
    if (!modal) return;
    modal.classList.remove('active');
    syncModalOpenState();
}

function startNewPlanRegistration() {
    resetPlanForm();
    const title = document.getElementById('planModalTitle');
    if (title) title.textContent = '새 플랜 추가';
    openPlanModal();
}


// 날짜 형식 변환 함수
function formatDateToDisplay(dateStr) {
    /**
     * YYYY-MM-DD 또는 YYYY/MM/DD 형식을 YYYY/MM/DD로 변환
     * 예: "2026-09-02" → "2026/09/02"
     */
    if (!dateStr) return '';
    
    // 이미 YYYY/MM/DD 형식이면 그대로 반환
    if (dateStr.includes('/')) return dateStr;
    
    // YYYY-MM-DD를 YYYY/MM/DD로 변환
    if (dateStr.includes('-')) {
        return dateStr.replace(/-/g, '/');
    }
    
    return dateStr;
}

function formatDateForServer(dateStr) {
    /**
     * YYYY/MM/DD를 YYYY-MM-DD로 변환 (서버 전송용)
     * 예: "2026/09/02" → "2026-09-02"
     */
    if (!dateStr) return '';
    
    // YYYY/MM/DD를 YYYY-MM-DD로 변환
    if (dateStr.includes('/')) {
        return dateStr.replace(/\//g, '-');
    }
    
    return dateStr;
}

function parseTsvRows(rawText) {
    const lines = rawText
        .split(/\r?\n/)
        .map(line => line.trim())
        .filter(line => line.length > 0);

    const rows = [];
    const invalid = [];

    // 마크다운 테이블 형식 감지
    const isMarkdownTable = lines.some(line => line.startsWith('|') && line.endsWith('|'));
    
    // 마크다운 테이블인 경우 헤더와 구분선 제거
    let processLines = lines;
    if (isMarkdownTable) {
        processLines = lines.filter((line, idx) => {
            // 헤더 또는 구분선 행인지 확인
            if (idx === 0) return false; // 첫 번째 행(헤더) 제거
            if (line.match(/^\|\s*-+\s*\|/) || line.match(/^\|\s*-+\s*:\s*\|/)) return false; // 구분선 제거
            return true;
        });
    }

    processLines.forEach((line, index) => {
        // 파이프 또는 탭으로 분리
        let cells;
        if (line.startsWith('|') && line.endsWith('|')) {
            // 마크다운 테이블 형식: 양쪽 파이프 제거 후 분리
            cells = line
                .slice(1, -1) // 첫번째와 마지막 파이프 제거
                .split('|')
                .map(cell => cell.trim())
                .filter(cell => cell.length > 0);
        } else {
            // 탭 또는 파이프로 분리
            cells = (line.includes('|') ? line.split('|') : line.split('\t'))
                .map(cell => cell.trim())
                .filter(cell => cell.length > 0);
        }

        // 첫번째 요소가 순번(숫자)이면 제거
        if (cells.length && cells[0].replace(/\./g, '').match(/^\d+$/)) {
            cells.shift();
        }

        if (cells.length >= 3) {
            const [word, pos, meaning, ...rest] = cells;
            if (!word || !meaning) {
                invalid.push({ line: index + 1, text: line, reason: 'word와 뜻이 필요합니다.' });
                return;
            }
            rows.push({
                word,
                pos,
                meaning,
                example: rest.join(' ') || ''
            });
            return;
        }

        if (cells.length === 2) {
            const [word, meaning] = cells;
            if (!word || !meaning) {
                invalid.push({ line: index + 1, text: line, reason: 'word와 뜻이 필요합니다.' });
                return;
            }
            rows.push({ word, pos: '', meaning, example: '' });
            return;
        }

        invalid.push({
            line: index + 1,
            text: line,
            reason: '형식이 올바르지 않습니다. word + 품사 + 뜻 또는 word + 뜻 형식이어야 합니다.'
        });
    });

    return { rows, invalid };
}

function renderVocabPreview(rows, previewId = 'vocabPreview') {
    const preview = document.getElementById(previewId);
    if (!preview) {
        return;
    }

    if (!rows.length) {
        preview.innerHTML = '<div class="preview-empty">파싱된 보카가 없습니다.</div>';
        return;
    }

    const maxRows = rows.slice(0, 10);
    preview.innerHTML = `
        <div class="preview-header">
            <strong>미리보기</strong>
            <span>${rows.length}개</span>
        </div>
        <div class="preview-table">
            ${maxRows.map((row, index) => `
                <div class="preview-row">
                    <span class="preview-index">${index + 1}</span>
                    <span class="preview-word">${row.word.replace(/\*\*/g, '')}</span>
                    <span class="preview-pos">${(row.pos || '-').replace(/\*\*/g, '')}</span>
                    <span class="preview-meaning">${row.meaning.replace(/\*\*/g, '')}</span>
                    <span class="preview-example">${(row.example || '-').replace(/\*\*/g, '')}</span>
                </div>
            `).join('')}
        </div>
    `;
}

function showVocabTsvForm() {
    const container = document.getElementById('vocabularyTsvContainer');
    if (container) {
        container.style.display = 'block';
        container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

function openVocabRegistration() {
    if (!currentPlanId) {
        showAlert('먼저 플랜을 등록해주세요.');
        return;
    }
    showVocabTsvForm();
}

function openChapterVocabModal(button) {
    if (!currentPlanId) {
        showAlert('먼저 플랜을 저장해주세요.');
        return;
    }

    const row = button.closest('.chapter-input-group');
    const chapterNumber = row?.querySelector('.chapter-number')?.value;
    if (!chapterNumber) {
        showAlert('챕터 정보를 확인해주세요.');
        return;
    }

    // 선택된 챕터 번호를 저장
    currentVocabChapterNumber = parseInt(chapterNumber);
    
    // 챕터별 보카 TSV 등록 섹션을 보여주기
    const vocabContainer = document.getElementById('vocabularyTsvContainer');
    if (vocabContainer) {
        vocabContainer.style.display = 'block';
    }
    
    // combobox에 현재 챕터 선택
    const vocabSelect = document.getElementById('vocabChapterSelect');
    if (vocabSelect) {
        vocabSelect.value = currentVocabChapterNumber;
    }
    
    // textarea 초기화 및 포커스
    const vocabInput = document.getElementById('vocabTsvInput');
    if (vocabInput) {
        vocabInput.value = '';
        vocabInput.focus();
    }
    
    // preview 초기화
    const vocabPreview = document.getElementById('vocabPreview');
    if (vocabPreview) {
        vocabPreview.innerHTML = '';
    }
    
    // 저장 버튼 비활성화
    const saveBtn = document.getElementById('saveVocabTsvBtn');
    if (saveBtn) {
        saveBtn.disabled = true;
    }
    
    // 섹션으로 스크롤
    vocabContainer?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function populateVocabChapterSelect(chapters, selectId = 'vocabChapterSelect') {
    const select = document.getElementById(selectId);
    if (!select) {
        return;
    }

    const values = Array.isArray(chapters) && chapters.length ? chapters : [];
    select.innerHTML = '<option value="">챕터를 선택하세요</option>' +
        values.map(ch => `<option value="${ch.chapter_number}">Chapter ${ch.chapter_number}</option>`).join('');
}

async function parseVocabTsv() {
    const rawText = document.getElementById('vocabTsvInput').value.trim();
    if (!rawText) {
        showAlert('TSV 데이터를 입력해주세요.');
        return;
    }

    const { rows, invalid } = parseTsvRows(rawText);
    if (!rows.length) {
        renderVocabPreview([]);
        showAlert(invalid[0]?.reason || '유효한 TSV 데이터가 없습니다.');
        return;
    }

    parsedVocabRows = rows;
    renderVocabPreview(rows);

    const saveButton = document.getElementById('saveVocabTsvBtn');
    saveButton.disabled = false;

    if (invalid.length) {
        showAlert(`일부 행은 건너뛰고 ${rows.length}개만 저장됩니다.\n${invalid.slice(0, 2).map(item => `행 ${item.line}: ${item.reason}`).join('\n')}`);
    }
}

async function saveVocabTsv() {
    if (!currentPlanId) {
        showAlert('먼저 플랜을 저장해주세요.');
        return;
    }

    if (!currentVocabChapterNumber) {
        showAlert('등록 버튼을 눌러서 챕터를 선택한 후 저장해주세요.');
        return;
    }

    if (!parsedVocabRows.length) {
        showAlert('먼저 파싱하기를 눌러 보카를 확인해주세요.');
        return;
    }

    try {
        const response = await fetch('/api/add-vocabulary-bulk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                plan_id: currentPlanId,
                chapter_number: currentVocabChapterNumber,
                rows: parsedVocabRows
            })
        });

        const result = await response.json();
        if (!response.ok) {
            showAlert('오류: ' + result.error);
            return;
        }

        showAlert(result.message);
        document.getElementById('vocabTsvInput').value = '';
        parsedVocabRows = [];
        renderVocabPreview([], 'vocabPreview');
        document.getElementById('saveVocabTsvBtn').disabled = true;
    } catch (error) {
        console.error('Error:', error);
        showAlert('보카 저장에 실패했습니다.');
    }
}

async function openVocabModal(planId) {
    try {
        const response = await fetch(`/api/plan/${planId}`);
        const result = await response.json();

        if (!response.ok || !result.success) {
            showAlert(result.error || '플랜 정보를 불러오지 못했습니다.');
            return;
        }

        currentPlanId = planId;
        currentVocabPlanId = planId;
        document.getElementById('modalVocabTsvInput').value = '';
        renderVocabPreview([], 'modalVocabPreview');
        document.getElementById('modalSaveVocabTsvBtn').disabled = true;

        const modal = document.getElementById('vocabModal');
        if (modal) {
            closeAllModals();
            modal.classList.add('active');
            syncModalOpenState();
        }
    } catch (error) {
        console.error('Error:', error);
        showAlert('보카 등록 팝업을 열지 못했습니다.');
    }
}

function closeVocabModal() {
    const modal = document.getElementById('vocabModal');
    if (modal) {
        modal.classList.remove('active');
        syncModalOpenState();
    }
}

async function parseModalVocabTsv() {
    const rawText = document.getElementById('modalVocabTsvInput').value.trim();
    if (!rawText) {
        showAlert('TSV 데이터를 입력해주세요.');
        return;
    }

    const { rows, invalid } = parseTsvRows(rawText);
    if (!rows.length) {
        renderVocabPreview([], 'modalVocabPreview');
        showAlert(invalid[0]?.reason || '유효한 TSV 데이터가 없습니다.');
        return;
    }

    parsedVocabRows = rows;
    renderVocabPreview(rows, 'modalVocabPreview');
    document.getElementById('modalSaveVocabTsvBtn').disabled = false;

    if (invalid.length) {
        showAlert(`일부 행은 건너뛰고 ${rows.length}개만 저장됩니다.\n${invalid.slice(0, 2).map(item => `행 ${item.line}: ${item.reason}`).join('\n')}`);
    }
}

async function saveModalVocabTsv() {
    if (!currentPlanId) {
        showAlert('먼저 플랜을 선택해주세요.');
        return;
    }

    if (!currentVocabChapterNumber) {
        showAlert('저장할 챕터를 선택해주세요.');
        return;
    }

    if (!parsedVocabRows.length) {
        showAlert('먼저 파싱하기를 눌러 보카를 확인해주세요.');
        return;
    }

    try {
        const response = await fetch('/api/add-vocabulary-bulk', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                plan_id: currentPlanId,
                chapter_number: currentVocabChapterNumber,
                rows: parsedVocabRows
            })
        });

        const result = await response.json();
        if (!response.ok) {
            showAlert('오류: ' + result.error);
            return;
        }

        document.getElementById('modalVocabTsvInput').value = '';
        parsedVocabRows = [];
        renderVocabPreview([], 'modalVocabPreview');
        document.getElementById('modalSaveVocabTsvBtn').disabled = true;
        closeVocabModal();
        showAlert(result.message);
    } catch (error) {
        console.error('Error:', error);
        showAlert('보카 저장에 실패했습니다.');
    }
}

// 플랜 추가 폼 제출
document.getElementById('planForm').addEventListener('submit', async function(event) {
    event.preventDefault();

    const book_title = document.getElementById('book_title').value.trim();
    const author = document.getElementById('author').value.trim();
    const week_start = document.getElementById('week_start').value;
    const week_end = document.getElementById('week_end').value;
    const total_chapters = document.getElementById('total_chapters').value;
    const book_cover_url = document.getElementById('book_cover_url').value.trim();

    if (!book_title || !author || !week_start || !week_end || !total_chapters) {
        showAlert('필수 항목을 모두 입력해주세요.');
        return;
    }

    try {
        let method = 'POST';
        let url = '/api/add-plan';
        let payload = {
            book_title: book_title,
            author: author,
            week_start: formatDateForServer(week_start),
            week_end: formatDateForServer(week_end),
            total_chapters: parseInt(total_chapters),
            book_cover_url: book_cover_url
        };

        if (isEditMode && currentPlanId) {
            method = 'PUT';
            url = `/api/update-plan/${currentPlanId}`;
        }

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const error = await response.json();
            showAlert('오류: ' + error.error);
            return;
        }

        const result = await response.json();
        const planId = isEditMode ? currentPlanId : result.plan_id;
        currentPlanId = planId;

        if (isEditMode) {
            await fetch('/api/add-chapters', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    plan_id: currentPlanId,
                    chapters: collectChapterInputs(),
                    replace_existing: true
                })
            });
            showAlert('플랜이 수정되었습니다.');
            resetPlanForm();
            setTimeout(() => location.reload(), 800);
            return;
        }

        showChaptersForm(parseInt(total_chapters));
        showVocabTsvForm();
        showAlert(result.message);
        
        // 폼 리셋을 위해 start_chapter 기본값 설정
        document.getElementById('start_chapter').value = 1;
    } catch (error) {
        console.error('Error:', error);
        showAlert('플랜 저장에 실패했습니다.');
    }
}
);

// 챕터 입력 폼 표시
function showChaptersForm(totalChapters, existingChapters = []) {
    const container = document.getElementById('chaptersContainer');
    const chaptersList = document.getElementById('chaptersList');
    
    chaptersList.innerHTML = '';
    chapterCount = totalChapters;

    // 시작 챕터 번호 가져오기 (기본값: 1)
    const startChapter = parseInt(document.getElementById('start_chapter')?.value || 1);

    const chapterRows = existingChapters.length ? existingChapters : Array.from({ length: totalChapters }, (_, i) => ({
        chapter_number: startChapter + i,
        page_start: '',
        page_end: ''
    }));

    chapterRows.forEach((chapter, index) => {
        addChapterInput(chapter.chapter_number || startChapter + index, chapter.page_start || '', chapter.page_end || '');
    });

    container.style.display = 'block';
    
    // 모든 챕터 생성 후 첫 번째 챕터 변경 이벤트 설정
    setupChapterNumberAutoUpdate();
}

// 챕터 입력 필드 추가
function addChapterInput(chapterNum = null, pageStart = '', pageEnd = '') {
    const chaptersList = document.getElementById('chaptersList');
    const newIndex = chaptersList.children.length + 1;

    const div = document.createElement('div');
    div.className = 'chapter-input-group';
    div.innerHTML = `
        <input type="number" class="chapter-number" placeholder="Ch." value="${chapterNum || newIndex}" required>
        <input type="number" class="page-start" placeholder="시작 페이지" value="${pageStart}" required>
        <input type="number" class="page-end" placeholder="종료 페이지" value="${pageEnd}" required>
        <button type="button" class="btn-register-chapter" onclick="openChapterVocabModal(this)">등록</button>
        <button type="button" class="btn-remove-chapter" onclick="this.parentElement.remove()">✕</button>
    `;

    chaptersList.appendChild(div);
}

// 첫 번째 챕터 변경 시 나머지 자동 조정
function setupChapterNumberAutoUpdate() {
    const firstChapterInput = document.querySelector('.chapter-input-group .chapter-number');
    
    if (firstChapterInput) {
        // blur 이벤트: 포커스를 잃을 때 (다른 필드로 이동할 때)
        firstChapterInput.addEventListener('blur', autoAdjustChapterNumbers);
    }
}

function collectChapterInputs() {
    const chapterGroups = document.querySelectorAll('.chapter-input-group');
    const chapters = [];

    chapterGroups.forEach(group => {
        const chapterNumber = parseInt(group.querySelector('.chapter-number')?.value || '', 10);
        const pageStart = parseInt(group.querySelector('.page-start')?.value || '', 10);
        const pageEnd = parseInt(group.querySelector('.page-end')?.value || '', 10);

        if (!chapterNumber || !pageStart || !pageEnd) {
            return;
        }

        chapters.push({
            chapter_number: chapterNumber,
            page_start: pageStart,
            page_end: pageEnd
        });
    });

    return chapters;
}

// 첫 번째 챕터를 기준으로 모든 챕터 번호 자동 조정
function autoAdjustChapterNumbers() {
    const chapterInputs = document.querySelectorAll('.chapter-input-group .chapter-number');
    if (chapterInputs.length === 0) return;
    
    const firstChapter = parseInt(chapterInputs[0].value) || 1;
    console.log('첫 번째 챕터:', firstChapter, '기준으로 자동 조정 시작');
    
    chapterInputs.forEach((input, index) => {
        const newValue = firstChapter + index;
        input.value = newValue;
        console.log(`챕터 ${index + 1}: ${newValue}`);
    });
}

// 챕터 정보 제출
async function submitChapters() {
    if (!currentPlanId) {
        showAlert('먼저 플랜을 추가해주세요.');
        return;
    }

    // 첫 번째 챕터 번호를 기준으로 모든 챕터 번호 자동 조정
    autoAdjustChapterNumbers();

    const chapterGroups = document.querySelectorAll('.chapter-input-group');
    const chapters = [];

    let isValid = true;
    chapterGroups.forEach(group => {
        const chapterNumber = parseInt(group.querySelector('.chapter-number').value);
        const pageStart = parseInt(group.querySelector('.page-start').value);
        const pageEnd = parseInt(group.querySelector('.page-end').value);

        if (!chapterNumber || !pageStart || !pageEnd) {
            isValid = false;
            return;
        }

        if (pageEnd <= pageStart) {
            showAlert('종료 페이지는 시작 페이지보다 커야 합니다.');
            isValid = false;
            return;
        }

        chapters.push({
            chapter_number: chapterNumber,
            page_start: pageStart,
            page_end: pageEnd
        });
    });

    if (!isValid || chapters.length === 0) {
        showAlert('모든 챕터 정보를 올바르게 입력해주세요.');
        return;
    }

    try {
        const response = await fetch('/api/add-chapters', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                plan_id: currentPlanId,
                chapters: chapters,
                replace_existing: true
            })
        });

        if (!response.ok) {
            const error = await response.json();
            showAlert('오류: ' + error.error);
            return;
        }

        const result = await response.json();
        populateVocabChapterSelect(chapters);
        showAlert(`${result.message}\n이제 보카 등록 버튼을 눌러 챕터별 TSV를 저장하세요.`);
    } catch (error) {
        console.error('Error:', error);
        showAlert('챕터 저장에 실패했습니다.');
    }
}

document.getElementById('parseVocabTsvBtn')?.addEventListener('click', parseVocabTsv);
document.getElementById('saveVocabTsvBtn')?.addEventListener('click', saveVocabTsv);
document.getElementById('openVocabTsvBtn')?.addEventListener('click', openVocabRegistration);
document.getElementById('modalParseVocabTsvBtn')?.addEventListener('click', parseModalVocabTsv);
document.getElementById('modalSaveVocabTsvBtn')?.addEventListener('click', saveModalVocabTsv);

// 플랜 삭제
async function deletePlan(planId) {
    if (!confirm('정말로 이 플랜을 삭제하시겠습니까?\n관련된 모든 챕터와 보카도 삭제됩니다.')) {
        return;
    }

    try {
        const response = await fetch(`/api/delete-plan/${planId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            const error = await response.json();
            showAlert('오류: ' + error.error);
            return;
        }

        const result = await response.json();
        showAlert(result.message);
        
        // 페이지 새로고침
        setTimeout(() => {
            location.reload();
        }, 1500);
    } catch (error) {
        console.error('Error:', error);
        showAlert('플랜 삭제에 실패했습니다.');
    }
}

// 플랜 보기 (메인 페이지로 이동)
function viewPlan(planId) {
    window.location.href = '/';
}

async function editPlan(planId) {
    try {
        const response = await fetch(`/api/plan/${planId}`);
        const result = await response.json();

        if (!response.ok || !result.success) {
            showAlert(result.error || '플랜 정보를 불러오지 못했습니다.');
            return;
        }

        const plan = result.plan;
        currentPlanId = plan.plan_id;
        isEditMode = true;
        openPlanModal();
        const title = document.getElementById('planModalTitle');
        if (title) title.textContent = '플랜 수정';

        document.getElementById('book_title').value = plan.book_title || '';
        document.getElementById('author').value = plan.author || '';
        document.getElementById('week_start').value = formatDateToDisplay(plan.week_start) || '';
        document.getElementById('week_end').value = formatDateToDisplay(plan.week_end) || '';
        document.getElementById('total_chapters').value = plan.total_chapters || 0;
        document.getElementById('book_cover_url').value = plan.book_cover_url || '';
        
        // 시작 챕터 번호 설정 (기존 챕터의 최소값)
        const chapters = plan.chapters || [];
        if (chapters.length > 0) {
            const minChapterNumber = Math.min(...chapters.map(c => c.chapter_number));
            document.getElementById('start_chapter').value = minChapterNumber;
        } else {
            document.getElementById('start_chapter').value = 1;
        }

        showChaptersForm(parseInt(plan.total_chapters || 0), plan.chapters || []);
        populateVocabChapterSelect(plan.chapters || []);
        showVocabTsvForm();

        const form = document.getElementById('planForm');
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) submitButton.textContent = '수정 완료';
    } catch (error) {
        console.error('Error:', error);
        showAlert('플랜을 불러오지 못했습니다.');
    }
}

// Alert 표시
function showAlert(message) {
    const modal = document.getElementById('alertModal');
    const alertMessage = document.getElementById('alertMessage');
    alertMessage.textContent = message;
    modal.classList.add('active');
    syncModalOpenState();
}

// Alert 닫기
function closeAlert() {
    const modal = document.getElementById('alertModal');
    modal.classList.remove('active');
    syncModalOpenState();
}

// 플랜 폼 리셋 함수
function resetPlanForm() {
    const form = document.getElementById('planForm');
    if (form) {
        form.reset();
    }
    
    // 편집 모드 종료
    isEditMode = false;
    currentPlanId = null;
    
    // 버튼 텍스트 복원
    const submitButton = form?.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.textContent = '플랜 추가';
    }
    
    // 시작 챕터 기본값
    const startChapterInput = document.getElementById('start_chapter');
    if (startChapterInput) {
        startChapterInput.value = 1;
    }
    
    // 챕터 폼 숨김
    const chaptersContainer = document.getElementById('chaptersContainer');
    if (chaptersContainer) {
        chaptersContainer.style.display = 'none';
    }
    
    // 보카 폼 숨김
    const vocabContainer = document.getElementById('vocabularyTsvContainer');
    if (vocabContainer) {
        vocabContainer.style.display = 'none';
    }
}

// 모달 외부 클릭 시 닫기
document.addEventListener('click', function(event) {
    const alertModal = document.getElementById('alertModal');
    const vocabModal = document.getElementById('vocabModal');
    const planModal = document.getElementById('planModal');

    if (event.target === alertModal) {
        alertModal.classList.remove('active');
    }
    if (event.target === vocabModal) {
        closeVocabModal();
    }
    if (event.target === planModal) {
        closePlanModal();
    }
});

// 날짜 입력 기본값 설정
document.addEventListener('DOMContentLoaded', function() {
    const today = new Date();
    const weekStart = new Date(today);
    weekStart.setDate(today.getDate() - today.getDay());
    
    const weekEnd = new Date(weekStart);
    weekEnd.setDate(weekStart.getDate() + 6);

    // YYYY/MM/DD 형식으로 변환
    const formatDate = (date) => {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}/${month}/${day}`;
    };

    // 현재 또는 다음주 기본값
    const startInput = document.getElementById('week_start');
    const endInput = document.getElementById('week_end');
    
    if (startInput) {
        // 기존 값이 있으면 포맷 변환, 없으면 기본값 설정
        if (startInput.value) {
            startInput.value = formatDateToDisplay(startInput.value);
        } else {
            startInput.value = formatDate(weekStart);
        }
    }
    if (endInput) {
        // 기존 값이 있으면 포맷 변환, 없으면 기본값 설정
        if (endInput.value) {
            endInput.value = formatDateToDisplay(endInput.value);
        } else {
            endInput.value = formatDate(weekEnd);
        }
    }

    const titleInput = document.getElementById('book_title');
    if (titleInput) {
        titleInput.addEventListener('change', autoFillBookMetaFromTitle);
        titleInput.addEventListener('blur', autoFillBookMetaFromTitle);
    }

    loadBookshelfBooksForAutocomplete();
});
