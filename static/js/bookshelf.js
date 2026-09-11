// Bookshelf Management JavaScript

let currentEditingBook = null;
let allBooks = [];
const dirtyBookIds = new Set();

// 페이지 로드 시 책 목록 조회
document.addEventListener('DOMContentLoaded', function() {
    loadBooks();
    setupFormHandlers();
    setupFilterHandlers();
});

function setupFormHandlers() {
    document.getElementById('bookForm').addEventListener('submit', async function(event) {
        event.preventDefault();
        await addBook();
    });

    document.getElementById('editBookForm').addEventListener('submit', async function(event) {
        event.preventDefault();
        await updateBook();
    });
}

function setupFilterHandlers() {
    document.getElementById('searchInput').addEventListener('input', filterBooks);
    document.getElementById('typeFilter').addEventListener('change', filterBooks);
    document.getElementById('categoryFilter').addEventListener('change', filterBooks);
    document.getElementById('seriesFilter').addEventListener('change', filterBooks);
}

async function loadBooks() {
    try {
        const response = await fetch('/api/books');
        const result = await response.json();

        if (!response.ok || !result.success) {
            showAlert('책 목록을 불러오지 못했습니다.');
            return;
        }

        allBooks = result.books || [];
        populateCategoryFilter();
        populateSeriesFilter();
        renderBooksTable(allBooks);
        document.getElementById('bookCount').textContent = allBooks.length;
    } catch (error) {
        console.error('Error:', error);
        showAlert('책 목록 로드에 실패했습니다.');
    }
}

function populateCategoryFilter() {
    const categories = [...new Set(allBooks
        .map(b => b.category)
        .filter(c => c))];
    
    const select = document.getElementById('categoryFilter');
    const currentValue = select.value;
    
    select.innerHTML = '<option value="">전체</option>' +
        categories.map(cat => `<option value="${cat}">${cat}</option>`).join('');
    
    select.value = currentValue;
}

function populateSeriesFilter() {
    const seriesList = [...new Set(allBooks
        .map(b => b.series)
        .filter(s => s))];

    const select = document.getElementById('seriesFilter');
    const currentValue = select.value;

    select.innerHTML = '<option value="">전체</option>' +
        seriesList.map(series => `<option value="${series}">${series}</option>`).join('');

    select.value = currentValue;
}

function renderBooksTable(books) {
    const container = document.getElementById('booksContainer');

    if (!books || books.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon"><i class="bi bi-inbox"></i></div>
                <p>등록된 책이 없습니다.</p>
            </div>
        `;
        return;
    }

    dirtyBookIds.clear();
    updateSaveAllButton();

    const tableHTML = `
        <table class="books-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>책 제목</th>
                    <th>저자</th>
                    <th>시리즈</th>
                    <th>유형</th>
                    <th>AR (ATOS)</th>
                    <th>Point</th>
                    <th>Lexile</th>
                    <th>ISBN</th>
                    <th>이미지 링크</th>
                    <th>관심</th>
                    <th>작업</th>
                </tr>
            </thead>
            <tbody>
                ${books.map((book, index) => `
                    <tr data-book-id="${book.id}">
                        <td class="cell-index">${index + 1}</td>
                        <td class="cell-title">
                            <input type="text" class="inline-edit-input" data-field="book_title" value="${escapeAttr(book.book_title)}" />
                        </td>
                        <td>
                            <input type="text" class="inline-edit-input" data-field="author" value="${escapeAttr(book.author)}" />
                        </td>
                        <td>
                            <input type="text" class="inline-edit-input" data-field="series" value="${escapeAttr(book.series)}" />
                        </td>
                        <td>
                            <select class="inline-edit-select" data-field="type">
                                <option value="" ${book.type ? '' : 'selected'}>선택</option>
                                <option value="F" ${book.type === 'F' ? 'selected' : ''}>Fiction</option>
                                <option value="NF" ${book.type === 'NF' ? 'selected' : ''}>Non-Fiction</option>
                            </select>
                        </td>
                        <td class="cell-stat">
                            <input type="text" class="inline-edit-input" data-field="atos" value="${escapeAttr(book.atos)}" />
                        </td>
                        <td class="cell-stat">
                            <input type="number" min="0" class="inline-edit-input" data-field="point" value="${escapeAttr(book.point)}" />
                        </td>
                        <td class="cell-stat">
                            <input type="text" class="inline-edit-input" data-field="lexile" value="${escapeAttr(book.lexile)}" />
                        </td>
                        <td>
                            <input type="text" class="inline-edit-input" data-field="isbn" value="${escapeAttr(book.isbn)}" />
                        </td>
                        <td>
                            <input type="url" class="inline-edit-input" data-field="book_image_url" value="${escapeAttr(book.book_image_url)}" placeholder="이미지 URL" />
                        </td>
                        <td>
                            <input type="text" class="inline-edit-input" data-field="category" value="${escapeAttr(book.category)}" />
                        </td>
                        <td class="cell-actions">
                            <button class="btn-icon-sm btn-delete" onclick="deleteBook(${book.id})" title="삭제">
                                <i class="bi bi-trash-fill"></i>
                            </button>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = tableHTML;
    setupInlineTableEvents();
}

function escapeAttr(value) {
    const text = value === null || value === undefined ? '' : String(value);
    return text
        .replace(/&/g, '&amp;')
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
}

function setupInlineTableEvents() {
    const table = document.querySelector('.books-table');
    if (!table) return;

    const markDirty = (event) => {
        const target = event.target;
        if (!target.classList.contains('inline-edit-input') && !target.classList.contains('inline-edit-select')) {
            return;
        }

        const row = target.closest('tr[data-book-id]');
        if (!row) return;
        const id = Number(row.getAttribute('data-book-id'));
        if (!id) return;

        row.classList.add('row-dirty');
        dirtyBookIds.add(id);
        updateSaveAllButton();
    };

    table.addEventListener('input', markDirty);
    table.addEventListener('change', markDirty);
}

function updateSaveAllButton() {
    const btn = document.getElementById('saveAllBtn');
    if (!btn) return;
    const count = dirtyBookIds.size;
    btn.disabled = count === 0;
    btn.innerHTML = `<i class="bi bi-save2"></i> 전체 저장${count > 0 ? ` (${count})` : ''}`;
}

async function saveAllRows() {
    const btn = document.getElementById('saveAllBtn');
    if (dirtyBookIds.size === 0) {
        showAlert('저장할 변경사항이 없습니다.');
        return;
    }

    const rows = Array.from(document.querySelectorAll('tr.row-dirty[data-book-id]'));
    const books = rows.map((row) => {
        const pointValue = row.querySelector('[data-field="point"]')?.value;
        return {
            id: Number(row.getAttribute('data-book-id')),
            book_title: row.querySelector('[data-field="book_title"]')?.value || '',
            author: row.querySelector('[data-field="author"]')?.value || '',
            series: row.querySelector('[data-field="series"]')?.value || '',
            type: row.querySelector('[data-field="type"]')?.value || '',
            atos: row.querySelector('[data-field="atos"]')?.value || '',
            point: pointValue === '' || pointValue === undefined ? null : Number(pointValue),
            lexile: row.querySelector('[data-field="lexile"]')?.value || '',
            isbn: row.querySelector('[data-field="isbn"]')?.value || '',
            category: row.querySelector('[data-field="category"]')?.value || '',
            book_image_url: row.querySelector('[data-field="book_image_url"]')?.value || '',
        };
    });

    try {
        if (btn) btn.disabled = true;

        const response = await fetch('/api/update-books-bulk', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ books })
        });

        const result = await response.json();
        if (!response.ok || !result.success) {
            showAlert('오류: ' + (result.error || '일괄 저장에 실패했습니다.'));
            updateSaveAllButton();
            return;
        }

        showAlert(result.message || '전체 저장이 완료되었습니다.');
        await loadBooks();
    } catch (error) {
        console.error('Error:', error);
        showAlert('전체 저장에 실패했습니다.');
        updateSaveAllButton();
    }
}

function filterBooks() {
    const searchText = document.getElementById('searchInput').value.toLowerCase();
    const typeFilter = document.getElementById('typeFilter').value;
    const categoryFilter = document.getElementById('categoryFilter').value;
    const seriesFilter = document.getElementById('seriesFilter').value;

    const filtered = allBooks.filter(book => {
        const matchSearch = !searchText || 
            (book.book_title && book.book_title.toLowerCase().includes(searchText)) ||
            (book.author && book.author.toLowerCase().includes(searchText)) ||
            (book.series && book.series.toLowerCase().includes(searchText)) ||
            (book.subtitle && book.subtitle.toLowerCase().includes(searchText)) ||
            (book.isbn && book.isbn.toLowerCase().includes(searchText));
        
        const matchType = !typeFilter || book.type === typeFilter;
        const matchCategory = !categoryFilter || book.category === categoryFilter;
        const matchSeries = !seriesFilter || book.series === seriesFilter;

        return matchSearch && matchType && matchCategory && matchSeries;
    });

    renderBooksTable(filtered);
}

function resetFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('typeFilter').value = '';
    document.getElementById('categoryFilter').value = '';
    document.getElementById('seriesFilter').value = '';
    renderBooksTable(allBooks);
}

async function addBook() {
    const form = document.getElementById('bookForm');
    const formData = new FormData(form);

    const data = {
        book_title: formData.get('book_title'),
        author: formData.get('author'),
        subtitle: formData.get('subtitle'),
        series: formData.get('series'),
        type: formData.get('type'),
        atos: formData.get('atos'),
        point: formData.get('point') ? parseInt(formData.get('point')) : null,
        category: formData.get('category'),
        priority: formData.get('priority'),
        isbn: formData.get('isbn'),
        book_image_url: formData.get('book_image_url'),
    };

    try {
        const response = await fetch('/api/add-book', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        if (!response.ok) {
            showAlert('오류: ' + result.error);
            return;
        }

        showAlert(result.message);
        form.reset();
        closeAddModal();
        await loadBooks();
    } catch (error) {
        console.error('Error:', error);
        showAlert('책 추가에 실패했습니다.');
    }
}

function openAddModal() {
    const modal = document.getElementById('addModal');
    if (!modal) return;
    modal.classList.add('active');
    const titleInput = document.getElementById('book_title');
    if (titleInput) {
        titleInput.focus();
    }
}

function closeAddModal() {
    const modal = document.getElementById('addModal');
    if (!modal) return;
    modal.classList.remove('active');
}

async function openEditModal(bookId) {
    try {
        const response = await fetch('/api/books');
        const result = await response.json();

        if (!response.ok || !result.success) {
            showAlert('책 정보를 불러오지 못했습니다.');
            return;
        }

        const book = result.books.find(b => b.id === bookId);
        if (!book) {
            showAlert('책을 찾을 수 없습니다.');
            return;
        }

        currentEditingBook = book;

        // 폼에 데이터 채우기
        document.getElementById('edit_book_title').value = book.book_title || '';
        document.getElementById('edit_author').value = book.author || '';
        document.getElementById('edit_subtitle').value = book.subtitle || '';
        document.getElementById('edit_series').value = book.series || '';
        document.getElementById('edit_type').value = book.type || '';
        document.getElementById('edit_atos').value = book.atos || '';
        document.getElementById('edit_point').value = book.point || '';
        document.getElementById('edit_lexile').value = book.lexile || '';
        document.getElementById('edit_category').value = book.category || '';
        document.getElementById('edit_priority').value = book.priority || '';
        document.getElementById('edit_isbn').value = book.isbn || '';
        document.getElementById('edit_book_image_url').value = book.book_image_url || '';

        const modal = document.getElementById('editModal');
        modal.classList.add('active');
    } catch (error) {
        console.error('Error:', error);
        showAlert('책 정보 로드에 실패했습니다.');
    }
}

function closeEditModal() {
    const modal = document.getElementById('editModal');
    modal.classList.remove('active');
    currentEditingBook = null;
}

async function updateBook() {
    if (!currentEditingBook) return;

    const form = document.getElementById('editBookForm');
    const formData = new FormData(form);

    const data = {
        book_title: formData.get('book_title'),
        author: formData.get('author'),
        subtitle: formData.get('subtitle'),
        series: formData.get('series'),
        type: formData.get('type'),
        atos: formData.get('atos'),
        point: formData.get('point') ? parseInt(formData.get('point')) : null,
        category: formData.get('category'),
        priority: formData.get('priority'),
        isbn: formData.get('isbn'),
        book_image_url: formData.get('book_image_url'),
    };

    try {
        const response = await fetch(`/api/update-book/${currentEditingBook.id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        if (!response.ok) {
            showAlert('오류: ' + result.error);
            return;
        }

        showAlert(result.message);
        closeEditModal();
        await loadBooks();
    } catch (error) {
        console.error('Error:', error);
        showAlert('책 수정에 실패했습니다.');
    }
}

async function deleteBook(bookId) {
    if (!confirm('정말로 이 책을 삭제하시겠습니까?')) {
        return;
    }

    try {
        const response = await fetch(`/api/delete-book/${bookId}`, {
            method: 'DELETE'
        });

        const result = await response.json();
        if (!response.ok) {
            showAlert('오류: ' + result.error);
            return;
        }

        showAlert(result.message);
        await loadBooks();
    } catch (error) {
        console.error('Error:', error);
        showAlert('책 삭제에 실패했습니다.');
    }
}

function showAlert(message) {
    const modal = document.getElementById('alertModal');
    document.getElementById('alertMessage').textContent = message;
    modal.classList.add('active');
}

function closeAlert() {
    const modal = document.getElementById('alertModal');
    modal.classList.remove('active');
}

// 모달 외부 클릭 시 닫기
document.addEventListener('click', function(event) {
    const addModal = document.getElementById('addModal');
    const editModal = document.getElementById('editModal');
    const alertModal = document.getElementById('alertModal');

    if (event.target === addModal) {
        closeAddModal();
    }
    if (event.target === editModal) {
        closeEditModal();
    }
    if (event.target === alertModal) {
        closeAlert();
    }
});

document.addEventListener('keydown', function(event) {
    if (event.key !== 'Escape') return;
    closeAddModal();
    closeEditModal();
    closeAlert();
});
