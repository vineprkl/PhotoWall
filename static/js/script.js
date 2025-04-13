// JavaScript code for Photo Wall

document.addEventListener('DOMContentLoaded', () => {
    // 检查当前页面路径，决定初始化哪个页面的功能
    if (document.getElementById('admin-image-list')) {
        loadAdminImages('All'); // Load initial admin view ('All' visible)
        setupAdminFilters(); // Setup admin filters
        setupUploadFormListener(); // 设置上传表单监听
    } else if (document.getElementById('photo-grid')) {
        loadPublicPhotos('游戏'); // Load initial photos (游戏)
        setupCategoryFilters(); // Setup filter button listeners
        startHeaderTimer(); // Start the timer
    }
});

// --- Timer Function ---
function updateTimer(startTime, elementId) {
    const timerElement = document.getElementById(elementId);
    if (!timerElement) return;

    const now = new Date();
    const diff = now - startTime; // Difference in milliseconds

    if (diff < 0) {
        timerElement.textContent = "Timer hasn't started yet.";
        return;
    }

    const secondsTotal = Math.floor(diff / 1000);
    const days = Math.floor(secondsTotal / (3600 * 24));
    const secondsRemainingAfterDays = secondsTotal % (3600 * 24);
    const hours = Math.floor(secondsRemainingAfterDays / 3600);
    const secondsRemainingAfterHours = secondsRemainingAfterDays % 3600;
    const minutes = Math.floor(secondsRemainingAfterHours / 60);
    const seconds = secondsRemainingAfterHours % 60;

    // Format the output string - Changed prefix and added more units
    let timerString = "我们❤ "; // Changed prefix
    if (days > 0) timerString += `${days}天 `;
    timerString += `${String(hours).padStart(2, '0')}小时 `; // Added unit
    timerString += `${String(minutes).padStart(2, '0')}分钟 `; // Added unit
    timerString += `${String(seconds).padStart(2, '0')}秒`; // Added unit

    timerElement.textContent = timerString;
}

function startHeaderTimer() {
    const startTime = new Date('2025-02-14T20:00:00'); 
    const timerElementId = 'header-title';
    updateTimer(startTime, timerElementId); // Initial call
    setInterval(() => updateTimer(startTime, timerElementId), 1000); // Update every second
}

// --- Admin Page Functions ---

function setupUploadFormListener() {
    const form = document.getElementById('upload-form');
    const statusP = document.getElementById('upload-status');
    if (form && statusP) {
        form.addEventListener('submit', (event) => {
            // 可以在这里添加一个简单的加载指示
            statusP.textContent = '正在上传，请稍候...';
            // 默认的表单提交会处理跳转，如果需要 AJAX 提交则需阻止默认行为
            // event.preventDefault();
            // 然后使用 fetch 发送表单数据
        });
    }
}

function setupAdminFilters() {
    const filterButtons = document.querySelectorAll('.admin-filter-btn');
    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const filter = button.getAttribute('data-filter');
            loadAdminImages(filter); // Reload images with the selected filter
        });
    });
}

// Modified loadAdminImages to handle filtering
async function loadAdminImages(filter = 'All') { // Default filter is 'All'
    const imageListDiv = document.getElementById('admin-image-list');
    if (!imageListDiv) return;

    imageListDiv.innerHTML = '<p>正在加载图片...</p>'; // Show loading message

    try {
        const response = await fetch('/admin/api/images'); // Always fetch all images for admin
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const allImages = await response.json(); // Get all images

        // --- Client-side Filtering Logic ---
        let filteredImages = [];
        if (filter === '已隐藏') {
            filteredImages = allImages.filter(img => !img.is_visible);
        } else if (filter === '游戏' || filter === '活动') { // Check for new categories
            filteredImages = allImages.filter(img => img.category === filter);
        } else { // filter === 'All' or unknown
            filteredImages = allImages; // Show everything for Admin 'All'
        }
        // --- End Filtering Logic ---

        imageListDiv.innerHTML = ''; // Clear loading/previous content

        if (filteredImages.length === 0) {
            imageListDiv.innerHTML = `<p>没有找到符合条件的图片 (${filter}).</p>`;
            return;
        }

        const table = document.createElement('table');
        table.className = 'admin-table';
        table.innerHTML = `
            <thead>
                <tr>
                    <th>缩略图</th>
                    <th>文件名</th>
                    <th>时间戳</th>
                    <th>上传时间</th>
                    <th>分类</th>
                    <th>状态</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
            </tbody>
        `;
        const tbody = table.querySelector('tbody');

        // Use filteredImages to populate the table
        filteredImages.forEach(img => {
            const tr = document.createElement('tr');
            tr.setAttribute('data-id', img.id);
            // Add class if hidden for potential styling
            if (!img.is_visible) {
                tr.classList.add('image-hidden');
            }
            tr.innerHTML = `
                <td><img src="${img.thumbnail_url}" alt="Thumbnail" class="admin-thumbnail"></td>
                <td>${escapeHTML(img.original_filename)}</td>
                <td>${escapeHTML(img.timestamp)}</td>
                <td>${escapeHTML(img.uploaded_at)}</td>
                <td>${escapeHTML(img.category)}</td>
                <td class="visibility-status">${img.is_visible ? '显示中' : '已隐藏'}</td>
                <td>
                    <div class="action-buttons">
                        <button class="btn-toggle" onclick="toggleVisibility(${img.id})">${img.is_visible ? '隐藏' : '显示'}</button>
                        <button class="btn-delete" onclick="deleteImage(${img.id})">删除</button>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });

        imageListDiv.appendChild(table);

    } catch (error) {
        console.error('Error loading admin images:', error);
        imageListDiv.innerHTML = '<p>加载图片列表失败，请稍后重试。</p>';
    }
}

async function deleteImage(imageId) {
    if (!confirm('确定要删除这张图片吗？此操作不可恢复。')) {
        return;
    }

    try {
        const response = await fetch(`/admin/api/images/${imageId}/delete`, {
            method: 'POST' // 或者 'DELETE'，取决于后端路由如何定义
        });
        const result = await response.json();

        if (result.success) {
            // alert('图片删除成功！');
            loadAdminImages(); // 刷新列表
        } else {
            alert('删除失败: ' + result.message);
        }
    } catch (error) {
        console.error('Error deleting image:', error);
        alert('删除过程中发生错误。');
    }
}

async function toggleVisibility(imageId) {
    try {
        const response = await fetch(`/admin/api/images/${imageId}/toggle_visibility`, {
            method: 'POST'
        });
        const result = await response.json();

        if (result.success) {
            // 更新 UI
            const row = document.querySelector(`tr[data-id="${imageId}"]`);
            if(row) {
                const statusCell = row.querySelector('.visibility-status');
                const toggleButton = row.querySelector('.btn-toggle');
                if (statusCell && toggleButton) {
                    statusCell.textContent = result.is_visible ? '显示中' : '已隐藏';
                    toggleButton.textContent = result.is_visible ? '隐藏' : '显示';
                }
            }
            // 或者直接调用 loadAdminImages() 刷新整个列表
            // loadAdminImages(); 
        } else {
            alert('切换状态失败: ' + result.message);
        }
    } catch (error) {
        console.error('Error toggling visibility:', error);
        alert('切换可见性时发生错误。');
    }
}

// --- Public Gallery Page Functions ---

function setupCategoryFilters() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    // No need to set active here, done in HTML

    filterButtons.forEach(button => {
        button.addEventListener('click', () => {
            filterButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const category = button.getAttribute('data-category');
            loadPublicPhotos(category); 
        });
    });
}

// Modified to accept category
async function loadPublicPhotos(category = 'All') { 
    const grid = document.getElementById('photo-grid');
    if (!grid) return;

    grid.innerHTML = '<p>正在加载照片...</p>'; // Show loading message

    let apiUrl = '/api/photos';
    if (category && category !== 'All') {
        apiUrl += `?category=${encodeURIComponent(category)}`;
    }

    try {
        const response = await fetch(apiUrl);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const photos = await response.json();

        grid.innerHTML = ''; // Clear loading/previous content

        if (photos.length === 0) {
            grid.innerHTML = '<p>此分类下还没有照片哦。</p>';
            return;
        }

        photos.forEach(photo => {
            // Create the main wrapper for this gallery entry
            const galleryEntry = document.createElement('div');
            galleryEntry.className = 'gallery-entry';
            
            // Create the item div for the image container
            const item = document.createElement('div');
            item.className = 'photo-item';
            
            const imgElement = document.createElement('img');
            imgElement.src = photo.thumbnail_url;
            imgElement.alt = `Photo (Category: ${escapeHTML(photo.category)}, Time: ${escapeHTML(photo.timestamp)})`; 
            imgElement.loading = 'lazy';
            imgElement.onclick = () => showLightbox(photo.original_url, escapeHTML(photo.timestamp));
            imgElement.onload = () => {
                imgElement.classList.add('loaded');
            };
            imgElement.onerror = () => {
                item.innerHTML = '<p style="color: red; font-size: 0.8em;">无法加载图片</p>'; 
            };
            
            // Append the image to the item div
            item.appendChild(imgElement);
            
            // Append the item div (image container) to the gallery entry
            galleryEntry.appendChild(item);
            
            // Create and append the timestamp div AFTER the item div
            const timestampDiv = document.createElement('div');
            timestampDiv.className = 'photo-timestamp';
            timestampDiv.textContent = escapeHTML(photo.timestamp);
            galleryEntry.appendChild(timestampDiv);
            
            // Append the complete gallery entry to the grid
            grid.appendChild(galleryEntry);
        });

    } catch (error) {
        console.error('Error loading public photos:', error);
        grid.innerHTML = '<p>加载照片失败，请稍后重试。</p>';
    }
}

function showLightbox(originalUrl, timestamp) {
    const lightbox = document.getElementById('lightbox');
    const lightboxImg = document.getElementById('lightbox-img');
    const lightboxTimestamp = document.getElementById('lightbox-timestamp');
    const downloadLink = document.getElementById('download-link');

    if (lightbox && lightboxImg && lightboxTimestamp && downloadLink) {
        lightboxImg.src = originalUrl;
        lightboxTimestamp.textContent = timestamp || '未知时间'; // 显示时间戳
        downloadLink.href = originalUrl;
        lightbox.style.display = 'flex'; // 使用 flex 居中
    }
}

function closeLightbox() {
    const lightbox = document.getElementById('lightbox');
    if (lightbox) {
        lightbox.style.display = 'none';
        // 可选：关闭时清除图片 src，避免占用内存
        // const lightboxImg = document.getElementById('lightbox-img');
        // if(lightboxImg) lightboxImg.src = '';
    }
}

// 添加点击 lightbox 背景关闭的功能 (可选)
document.addEventListener('click', function(event) {
    const lightbox = document.getElementById('lightbox');
    // 如果点击的是 lightbox 本身 (背景) 而不是内容区域
    if (lightbox && event.target === lightbox) {
        closeLightbox();
    }
});

// 简单的 HTML 转义函数，防止 XSS
function escapeHTML(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, 
      tag => ({
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '\'': '&#39;',
          '"': '&quot;'
      }[tag] || tag));
} 